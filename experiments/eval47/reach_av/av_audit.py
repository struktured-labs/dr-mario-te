#!/usr/bin/env python3
"""A_v pre-flight audit on REAL champion decision boards:

  1. TERM MASS -- how much of `rdy_ext` is credit for windows no straight drop can
     fill.  (Sizes the defect; also the number the scale-matched control needs.)
  2. SCALE-MATCH FACTOR -- the w_rdyext the reach=OFF control must run at so its
     mean term CONTRIBUTION equals A_v-at-dose-W's.  Without this control, any A_v
     win is attributable to the scalar, which coefficient optimisation already
     searched and closed.
  3. ARGMAX-FLIP RATE per dose -- the share of real decisions where the full
     depth-3 champion decider changes its committed action.  Below ~2% the arm is
     untestable and a null would mean nothing.

Every row carries the kernel hash.
Usage: av_audit.py --real tmp/boards_clean.npz tmp/boards_bursty.npz --out results/av_audit.json
"""
from __future__ import annotations

import argparse
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

import numpy as np

import reach_leaf as RL
import fast_rtl_x as FX
import pressure_rig as PR
from av_gate import load_real_corpus

DOSES = [8, 16, 24, 32, 48]
CHAMPION_W_RDYEXT = 8.0


def term_mass(real):
    """Per-board rdy_ext with and without the reach correction."""
    off = np.empty(len(real), dtype=np.int64)
    on = np.empty(len(real), dtype=np.int64)
    nvir = np.empty(len(real), dtype=np.int64)
    for i, (col, vir, _p) in enumerate(real):
        a = RL._rdyext_only(col, vir, 0)
        b = RL._rdyext_only(col, vir, 1)
        off[i] = a[0]
        on[i] = b[0]
        nvir[i] = a[3]
    return off, on, nvir


def summarise_mass(off, on, label):
    tot_off = int(off.sum())
    tot_on = int(on.sum())
    removed = tot_off - tot_on
    frac = removed / tot_off if tot_off else float("nan")
    per_board = (off - on)
    n_touched = int((per_board > 0).sum())
    print(f"  {label:>10s}: n={len(off)}  mean rdy_ext {off.mean():7.3f} -> {on.mean():7.3f}"
          f"   unreachable share {frac:6.1%}   boards touched {n_touched}/{len(off)} "
          f"({n_touched / len(off):5.1%})", flush=True)
    return {"label": label, "n": len(off), "mean_off": float(off.mean()),
            "mean_on": float(on.mean()), "total_off": tot_off, "total_on": tot_on,
            "unreachable_share": float(frac), "boards_touched": n_touched}


_W = {}


def _flip_init(paths, limit, ws, wt):
    RL.warmup()
    _W["rows"] = load_real_corpus(paths)[:limit]
    _W["ws"] = ws
    _W["wt"] = wt


def _flip_chunk(args):
    """(reach, w_rdyext, lo, hi) -> flips in rows[lo:hi] vs the champion's action."""
    reach, wv, lo, hi = args
    rows = _W["rows"][lo:hi]
    ws, wt = _W["ws"], _W["wt"]
    w_champ, fl = RL.weights_for(CHAMPION_W_RDYEXT)
    w, fl2 = RL.weights_for(wv)
    flips = 0
    for col, vir, (ca, cb, na, nb) in rows:
        b, _ = PR._choose_base(col, vir, ca, cb, na, nb, w_champ, fl, wt, ws)
        a, _ = RL.choose_base_rx(col, vir, ca, cb, na, nb, w, fl2, wt, ws, reach)
        if a != b:
            flips += 1
    return (reach, wv, flips, len(rows))


def flip_probe(paths, jobs, limit, workers=6, ws=20, wt=0, chunk=100):
    """jobs = [(reach, w_rdyext), ...].  Returns {(reach, w): (flips, n)}."""
    from concurrent.futures import ProcessPoolExecutor
    n = min(limit, len(load_real_corpus(paths)))
    tasks = [(r, wv, lo, min(lo + chunk, n))
             for (r, wv) in jobs for lo in range(0, n, chunk)]
    acc = {}
    with ProcessPoolExecutor(max_workers=workers, initializer=_flip_init,
                             initargs=(paths, limit, ws, wt)) as ex:
        for reach, wv, f, k in ex.map(_flip_chunk, tasks):
            a, b = acc.get((reach, wv), (0, 0))
            acc[(reach, wv)] = (a + f, b + k)
    for (reach, wv), (f, k) in sorted(acc.items()):
        tag = f"A_v         w_rdyext={wv:7.3f}" if reach else f"scalar-only w_rdyext={wv:7.3f}"
        print(f"  {tag}: argmax flips {f}/{k} = {f / k:.2%}", flush=True)
    return acc


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--real", nargs="+", required=True)
    ap.add_argument("--flip-limit", type=int, default=1200)
    ap.add_argument("--workers", type=int, default=6)
    ap.add_argument("--out", type=str, default=None)
    a = ap.parse_args()

    RL.warmup()
    kh = RL.kernel_hash()
    print(f"=== A_v PRE-FLIGHT AUDIT  kernel_hash={kh} ===", flush=True)

    per_file = {}
    all_off, all_on = [], []
    for p in a.real:
        real = load_real_corpus([p])
        off, on, _nv = term_mass(real)
        per_file[os.path.basename(p)] = summarise_mass(off, on, os.path.basename(p)[7:-4])
        all_off.append(off); all_on.append(on)
    off = np.concatenate(all_off); on = np.concatenate(all_on)
    combined = summarise_mass(off, on, "COMBINED")

    # ---- scale-match: same mean term contribution, unreachable credit restored
    ratio = float(on.mean() / off.mean())
    print(f"\n  scale-match ratio E[rdy_ext | reach] / E[rdy_ext | no reach] = {ratio:.4f}")
    ctrl_w = {d: d * ratio for d in DOSES}
    for d in DOSES:
        print(f"    A_v at w={d:3d}  <->  reach-OFF control at w={ctrl_w[d]:7.3f} "
              f"(mean contribution {d * on.mean():9.2f} both)")

    print(f"\n=== ARGMAX-FLIP (full depth-3, ws=20, n={min(a.flip_limit, len(off))} "
          f"real decisions, workers={a.workers}) ===", flush=True)
    jobs = [(1, float(d)) for d in DOSES]
    jobs += [(0, round(ctrl_w[d], 3)) for d in DOSES]
    acc = flip_probe(a.real, jobs, a.flip_limit, workers=a.workers)

    if a.out:
        with open(a.out, "w") as fh:
            json.dump({"kernel_hash": kh, "per_file": per_file, "combined": combined,
                       "scale_match_ratio": ratio,
                       "control_weight_for_dose": ctrl_w,
                       "argmax_flips": {f"reach{r}_w{wv}": v for (r, wv), v in acc.items()},
                       "flip_limit": a.flip_limit}, fh, indent=1)
        print(f"\nwrote {a.out}")


if __name__ == "__main__":
    main()
