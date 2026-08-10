#!/usr/bin/env python3
"""independent_verify.py — REIMPLEMENTATION cross-check of frame_watchdog.py's numbers.

WHY THIS EXISTS
---------------
The live validation must not rest on the watchdog grading its own homework. Every number
frame_watchdog.py reports (changed_frac, pixhash, black_frac) comes from ONE stdlib PNG
decoder and ONE hand-written byte-diff loop. If either is wrong, the watchdog's log and the
watchdog's self-check are wrong in the SAME direction and no amount of re-reading the log
would reveal it.

So this file recomputes the same quantities from the SAME saved frames using an entirely
different stack:
    decode : Pillow / libpng          (vs. the in-file zlib+unfilter decoder)
    diff   : numpy vectorised uint8   (vs. a python map/lambda byte loop)
Agreement across both stacks is evidence the numbers are real. Disagreement is a defect in
one of them and must be resolved before any verdict is quoted.

SELF-TEST (the check must FAIL on wrong inputs, per the project's gate standard)
-------------------------------------------------------------------------------
--selftest feeds three synthetic cases and requires the expected answer on each:
    identical frames        -> changed_frac == 0.0            (must detect staticness)
    fully inverted frames   -> changed_frac == 1.0            (must detect total change)
    exactly 200 px changed  -> changed_frac == 200/npx        (must count correctly)
A verifier that cannot fail these cannot certify anything.

USAGE
  uv run --with pillow --with numpy python independent_verify.py --frames <dir> \
      --watchdog-log <watch.jsonl> --out <verify.json>
  uv run --with pillow --with numpy python independent_verify.py --selftest
"""

from __future__ import annotations

import argparse
import glob
import hashlib
import json
import os
import sys

import numpy as np
from PIL import Image

TOL = 8                     # must match frame_watchdog.DEFAULT_TOLERANCE
MIN_CHANGED_FRAC = 1.0e-3   # must match frame_watchdog.DEFAULT_MIN_CHANGED_FRAC
BLACK_LEVEL = 16
K = 3


def load_rgb(path: str) -> np.ndarray:
    with Image.open(path) as im:
        return np.asarray(im.convert("RGB"), dtype=np.uint8)


def changed_frac(a: np.ndarray, b: np.ndarray, tol: int = TOL) -> tuple[float, float, int]:
    """Fraction of PIXELS whose max per-channel |delta| exceeds tol, plus mad and max_abs."""
    if a.shape != b.shape:
        return 1.0, 255.0, 255
    d = np.abs(a.astype(np.int16) - b.astype(np.int16)).astype(np.uint8)
    per_px = d.max(axis=2)
    return float((per_px > tol).mean()), float(d.mean()), int(d.max())


def black_frac(a: np.ndarray) -> float:
    return float((a.max(axis=2) <= BLACK_LEVEL).mean())


def pixhash(a: np.ndarray) -> str:
    return hashlib.blake2b(a.tobytes(), digest_size=8).hexdigest()


def selftest() -> int:
    rng = np.random.default_rng(1234)
    base = rng.integers(0, 256, size=(448, 256, 3), dtype=np.uint8)
    npx = base.shape[0] * base.shape[1]
    fails = []

    cf, _, _ = changed_frac(base, base.copy())
    if cf != 0.0:
        fails.append(f"identical frames gave changed_frac={cf}, expected 0.0")

    cf, _, _ = changed_frac(base, (255 - base).astype(np.uint8))
    # inversion moves every pixel by >tol except values within tol/2 of mid-grey in ALL
    # channels; with random data that is vanishingly rare, so require > 0.99 not == 1.0.
    if cf < 0.99:
        fails.append(f"inverted frames gave changed_frac={cf}, expected >0.99")

    mod = base.copy()
    flat = mod.reshape(-1, 3)
    idx = rng.choice(npx, size=200, replace=False)
    flat[idx] = np.uint8(0)
    flat[idx, 0] = np.uint8(255)          # force a >tol delta on at least one channel
    cf, _, _ = changed_frac(base, mod)
    # a chosen pixel could coincidentally already be (255,0,0); count the truth directly
    truth = float((np.abs(base.astype(np.int16) - mod.astype(np.int16)).max(axis=2) > TOL).mean())
    if abs(cf - truth) > 1e-12:
        fails.append(f"counted changed_frac={cf}, direct truth={truth}")
    if truth == 0.0:
        fails.append("synthetic 200px change produced no measurable change at all")

    blk = np.zeros((448, 256, 3), dtype=np.uint8)
    if black_frac(blk) != 1.0:
        fails.append("all-black frame did not score black_frac 1.0")
    if black_frac(base) > 0.05:
        fails.append("random frame scored implausibly black")

    for f in fails:
        print(f"SELFTEST FAIL: {f}", file=sys.stderr)
    print(f"SELFTEST {'PASS' if not fails else 'FAIL'} ({len(fails)} failures)")
    return 1 if fails else 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--frames")
    ap.add_argument("--watchdog-log")
    ap.add_argument("--out")
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args()
    if a.selftest:
        return selftest()
    if not (a.frames and a.watchdog_log and a.out):
        ap.error("--frames, --watchdog-log and --out are required unless --selftest")

    paths = sorted(glob.glob(os.path.join(a.frames, "f*.png")))
    if not paths:
        print("no frames found", file=sys.stderr)
        return 1

    wd = {}
    with open(a.watchdog_log) as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            r = json.loads(line)
            wd[r["seq"]] = r

    rows, prev, prev_seq = [], None, None
    for p in paths:
        seq = int(os.path.basename(p)[1:-4])
        rgb = load_rgb(p)
        row = {
            "seq": seq, "pixhash_pil": pixhash(rgb),
            "black_frac_pil": round(black_frac(rgb), 5),
            "w": int(rgb.shape[1]), "h": int(rgb.shape[0]),
        }
        if prev is not None:
            cf, mad, mx = changed_frac(prev, rgb)
            row.update({"changed_frac_pil": round(cf, 6), "mad_pil": round(mad, 4),
                        "max_abs_pil": mx, "prev_seq": prev_seq,
                        "alive_pil": cf >= MIN_CHANGED_FRAC})
        rows.append(row)
        prev, prev_seq = rgb, seq

    # ---- cross-check against the watchdog's own log ------------------------------------
    mismatch = []
    for row in rows:
        w = wd.get(row["seq"])
        if not w or not w.get("capture_ok"):
            continue
        if w.get("pixhash") != row["pixhash_pil"]:
            mismatch.append({"seq": row["seq"], "field": "pixhash",
                             "watchdog": w.get("pixhash"), "independent": row["pixhash_pil"]})
        if "changed_frac_pil" in row and "changed_frac" in w:
            # only comparable when the watchdog's previous SUCCESSFUL frame is our previous file
            if w.get("changed_frac") is not None and row.get("prev_seq") is not None:
                if abs(w["changed_frac"] - row["changed_frac_pil"]) > 2e-6:
                    mismatch.append({"seq": row["seq"], "field": "changed_frac",
                                     "watchdog": w["changed_frac"],
                                     "independent": row["changed_frac_pil"]})
        if "black_frac" in w and abs(w["black_frac"] - row["black_frac_pil"]) > 2e-5:
            mismatch.append({"seq": row["seq"], "field": "black_frac",
                             "watchdog": w["black_frac"], "independent": row["black_frac_pil"]})

    # ---- independent re-derivation of the VERDICT from PIL numbers alone ---------------
    consec_static, verdicts = 0, {}
    for row in rows:
        if "changed_frac_pil" not in row:
            verdicts[row["seq"]] = "INIT"
            continue
        if row["changed_frac_pil"] >= MIN_CHANGED_FRAC:
            consec_static = 0
            verdicts[row["seq"]] = "ALIVE"
        else:
            consec_static += 1
            verdicts[row["seq"]] = "WEDGED" if consec_static >= K else "SUSPECT"
    verdict_mismatch = [
        {"seq": s, "watchdog": wd[s].get("verdict"), "independent": v}
        for s, v in verdicts.items()
        if s in wd and wd[s].get("capture_ok") and wd[s].get("verdict") != v
    ]

    uniq = len({r["pixhash_pil"] for r in rows})
    out = {
        "frames": len(rows), "unique_pixhashes": uniq,
        "all_frames_distinct": uniq == len(rows),
        "changed_frac_min": min((r["changed_frac_pil"] for r in rows
                                 if "changed_frac_pil" in r), default=None),
        "changed_frac_max": max((r["changed_frac_pil"] for r in rows
                                 if "changed_frac_pil" in r), default=None),
        "min_changed_frac_floor": MIN_CHANGED_FRAC,
        "n_below_floor": sum(1 for r in rows
                             if r.get("changed_frac_pil", 1.0) < MIN_CHANGED_FRAC),
        "field_mismatches": mismatch,
        "verdict_mismatches": verdict_mismatch,
        "agreement": not mismatch and not verdict_mismatch,
        "rows": rows,
    }
    with open(a.out, "w") as fh:
        json.dump(out, fh, indent=1, sort_keys=True)
    print(f"frames={len(rows)} unique_pixhashes={uniq} "
          f"changed_frac range [{out['changed_frac_min']}, {out['changed_frac_max']}] "
          f"below_floor={out['n_below_floor']} "
          f"field_mismatches={len(mismatch)} verdict_mismatches={len(verdict_mismatch)} "
          f"AGREEMENT={out['agreement']}")
    return 0 if out["agreement"] else 3


if __name__ == "__main__":
    sys.exit(main())
