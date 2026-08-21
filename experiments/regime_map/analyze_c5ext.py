#!/usr/bin/env python3
"""c5 precision-extension analysis (hetzfarm-143).

Reads the extension JSONL, validates EVERY row against the registered spec
(PREREG_C5_PRECISION_EXT.md sec 2-3 — the POPULATION gate), and emits the
estimate: failure rate with exact Clopper-Pearson CI plus a game-clustered
bootstrap CI (registered reading rule, sec 4).

  --selftest : rule-7 mutants M-a..M-f must all be rejected (exits nonzero on
               any surviving mutant). No rows file needed.
"""
from __future__ import annotations

import argparse
import json
import sys
import os

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

from analyze_regime import cp_ci, load_rows  # noqa: E402  (registered map code)

ARM = "c5ext_L20_bursty"
VARIANT = "bursty"
LEVEL = 20
MAX_PILLS = 400
SEED_LO, SEED_HI = 34000, 35998          # even block, stride 2 (prereg sec 3)
FW_MD5 = "e970e9ab0208cdbce1d39ed33e2f51ee"   # champion s20b
FAIL_RESULTS = ("topout", "stall")
BOOT_SEED = 20260821
BOOT_N = 10000


def validate(rows):
    """POPULATION gate: every row must belong to the registered extension."""
    problems = []
    seen = set()
    for r in rows:
        s = r.get("seed")
        if r.get("arm") != ARM:
            problems.append(f"seed={s}: arm {r.get('arm')!r} != {ARM!r}")
            continue
        s = int(s)
        if s % 2:
            problems.append(f"seed {s} is ODD (low bit dead; aliased stream)")
        if not (SEED_LO <= s <= SEED_HI):
            problems.append(f"seed {s} outside registered even block "
                            f"[{SEED_LO},{SEED_HI}]")
        if r.get("level") != LEVEL:
            problems.append(f"seed {s}: level={r.get('level')} != {LEVEL}")
        if r.get("pressure_model") != VARIANT:
            problems.append(f"seed {s}: pressure_model="
                            f"{r.get('pressure_model')!r} != {VARIANT!r}")
        if r.get("fw_md5") != FW_MD5:
            problems.append(f"seed {s}: fw_md5={r.get('fw_md5')} != champion")
        key = (r["arm"], s)
        if key in seen:
            problems.append(f"DUPLICATE row for seed {s}")
        seen.add(key)
    return problems


def boot_ci(fail_bits, n_boot=BOOT_N, seed=BOOT_SEED, alpha=0.05):
    """Game-clustered bootstrap: resample games (each game IS the cluster)."""
    import numpy as np
    bits = np.asarray(fail_bits, dtype=np.int8)
    rng = np.random.default_rng(seed)
    idx = rng.integers(0, len(bits), size=(n_boot, len(bits)))
    rates = bits[idx].mean(axis=1)
    return (float(np.quantile(rates, alpha / 2)),
            float(np.quantile(rates, 1 - alpha / 2)))


def summarize(rows, n_error):
    import statistics
    n = len(rows)
    bits = [1 if r["result"] in FAIL_RESULTS else 0 for r in rows]
    k = sum(bits)
    lo, hi = cp_ci(k, n)
    blo, bhi = boot_ci(bits) if n else (0.0, 1.0)
    clears = [r["pills"] for r in rows if r["result"] == "clear"]
    med_clear = statistics.median(clears) if clears else None
    out = {
        "arm": ARM, "n": n, "failures": k,
        "rate": (k / n if n else None),
        "ci95_exact_cp": [lo, hi],
        "ci95_boot_game_clustered": [blo, bhi],
        "topout": sum(1 for r in rows if r["result"] == "topout"),
        "stall": sum(1 for r in rows if r["result"] == "stall"),
        "dies_ahead": sum(1 for r in rows if r.get("dies_ahead")),
        "garbage_cells_per_game": (sum(r.get("garbage", 0) for r in rows) / n
                                   if n else None),
        "median_pills_to_clear": med_clear,
        "censoring_suspect": bool(med_clear and med_clear > (2 / 3) * MAX_PILLS),
        "error_rows": n_error,
        "error_rate": (n_error / (n + n_error) if (n + n_error) else 0.0),
    }
    return out


def selftest():
    base = {"arm": ARM, "seed": 34000, "result": "clear", "level": LEVEL,
            "pressure_model": VARIANT, "fw_md5": FW_MD5, "pills": 150}
    def mut(**kw):
        r = dict(base); r.update(kw); return r
    mutants = {
        "M-a out-of-block seed": [mut(seed=52100)],
        "M-b odd seed":          [mut(seed=34001)],
        "M-c mislabeled pressure": [mut(pressure_model="bursty_x2")],
        "M-d wrong firmware":    [mut(fw_md5="deadbeef")],
        "M-e duplicate row":     [mut(), mut()],
        "M-f wrong level":       [mut(level=11)],
    }
    ok = validate([mut()]) == []
    print(f"clean baseline accepted: {'PASS' if ok else 'FAIL'}")
    dead = 0
    for name, rows in mutants.items():
        killed = validate(rows) != []
        dead += killed
        print(f"{name}: {'KILLED' if killed else 'SURVIVED'}")
    if ok and dead == len(mutants):
        print("ANALYZE_C5EXT_SELFTEST_PASS")
        return 0
    print("ANALYZE_C5EXT_SELFTEST_FAIL")
    return 1


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--rows")
    ap.add_argument("--out")
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args()
    if a.selftest:
        sys.exit(selftest())
    if not a.rows:
        ap.error("--rows required unless --selftest")
    rows, errors, bad = load_rows(a.rows)
    if bad:
        print(f"WARNING: {len(bad)} unparseable lines (partial writes?)")
    problems = validate(rows)
    if problems:
        for p in problems[:40]:
            print("POPULATION GATE:", p)
        print(f"ANALYZE_C5EXT_FAIL ({len(problems)} problems)")
        sys.exit(1)
    out = summarize(rows, len(errors))
    if out["error_rate"] > 0.02:
        print(f"ANALYZE_C5EXT_FAIL error rows {out['error_rate']:.1%} > 2%")
        sys.exit(1)
    txt = (f"{ARM}: n={out['n']} failures={out['failures']} "
           f"rate={out['rate']:.3f} " if out['n'] else f"{ARM}: n=0 ")
    if out["n"]:
        txt += (f"CP95=[{out['ci95_exact_cp'][0]:.3f},{out['ci95_exact_cp'][1]:.3f}] "
                f"boot95=[{out['ci95_boot_game_clustered'][0]:.3f},"
                f"{out['ci95_boot_game_clustered'][1]:.3f}] "
                f"topout={out['topout']} stall={out['stall']} "
                f"med_clear_pills={out['median_pills_to_clear']} "
                f"censoring_suspect={out['censoring_suspect']} "
                f"errors={out['error_rows']}")
    print(txt)
    if a.out:
        with open(a.out, "w") as f:
            json.dump(out, f, indent=1)
    print("ANALYZE_C5EXT_OK")


if __name__ == "__main__":
    main()
