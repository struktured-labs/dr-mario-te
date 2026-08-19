#!/usr/bin/env python3
"""Decompose the reach correction's mass three ways, because "% of rdy_ext that is
unreachable credit" has at least three defensible denominators and they differ by
a factor of ~3.  A prior audit reported 54-80%; this file makes explicit which
quantity that is and which one A_v actually moves.

  (1) VERTICAL-AXIS mass   sum(vq) -- the axis A_v corrects, measured alone
  (2) rdy_ext mass         sum(max(hq, vq)) -- what the eval actually adds up.
                           A_v's effect is MASKED here whenever hq >= vq.
  (3) per-virus incidence   share of viruses whose vertical credit is reduced

(2) is the number that governs the arm's effect size; (1) is the number that
describes the defect.  Reporting (1) as if it were (2) overstates the lever.

Usage: av_mass_decomp.py --real tmp/boards_clean.npz tmp/boards_bursty.npz
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
from numba import njit, int8, int64

import reach_leaf as RL
from fast_sim_x import COLS, ROWS
from av_gate import load_real_corpus


@njit(int64[:](int8[:], int8[:]), cache=True, fastmath=False)
def _decomp(col, vir):
    """[vq_off, vq_on, rdy_off, rdy_on, nvir, nvir_vq_cut, nvir_rdy_cut]."""
    topocc = int64(0)
    for c in range(COLS):
        first_r = ROWS
        for r in range(ROWS):
            if col[r * COLS + c] != 0:
                first_r = r
                break
        topocc |= int64(first_r) << int64(5 * c)
    out = np.zeros(7, dtype=int64)
    for vr in range(ROWS):
        for vc in range(COLS):
            if not vir[vr * COLS + vc]:
                continue
            vcol = col[vr * COLS + vc]
            run_h = 1; p = vc
            while p != 0 and col[vr * COLS + (p - 1)] == vcol:
                run_h += 1; p -= 1
            lo = p
            while lo != 0 and ((col[vr * COLS + (lo - 1)] == 0) or col[vr * COLS + (lo - 1)] == vcol):
                lo -= 1
            p = vc
            while p != 7 and col[vr * COLS + (p + 1)] == vcol:
                run_h += 1; p += 1
            hi = p
            while hi != 7 and ((col[vr * COLS + (hi + 1)] == 0) or col[vr * COLS + (hi + 1)] == vcol):
                hi += 1
            hq = run_h * run_h if (hi - lo + 1) >= 4 else 0
            top_c = (topocc >> int64(5 * vc)) & int64(31)
            run_v = 1; p = vr
            while p != 0 and col[(p - 1) * COLS + vc] == vcol:
                run_v += 1; p -= 1
            base_lo = p
            p = vr
            while p != 15 and col[(p + 1) * COLS + vc] == vcol:
                run_v += 1; p += 1
            base_hi = p
            vqs = np.zeros(2, dtype=int64)
            for mode in range(2):
                vlo = base_lo
                while vlo != 0:
                    nb = col[(vlo - 1) * COLS + vc]
                    if nb == vcol:
                        vlo -= 1; continue
                    if nb == 0:
                        if mode == 1 and (vlo - 1) >= top_c:
                            break
                        vlo -= 1; continue
                    break
                vhi = base_hi
                while vhi != 15:
                    nb = col[(vhi + 1) * COLS + vc]
                    if nb == vcol:
                        vhi += 1; continue
                    if nb == 0:
                        if mode == 1 and (vhi + 1) >= top_c:
                            break
                        vhi += 1; continue
                    break
                vqs[mode] = run_v * run_v if (vhi - vlo + 1) >= 4 else 0
            out[0] += vqs[0]; out[1] += vqs[1]
            r_off = hq if hq > vqs[0] else vqs[0]
            r_on = hq if hq > vqs[1] else vqs[1]
            out[2] += r_off; out[3] += r_on
            out[4] += 1
            if vqs[1] < vqs[0]:
                out[5] += 1
            if r_on < r_off:
                out[6] += 1
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--real", nargs="+", required=True)
    ap.add_argument("--out", type=str, default=None)
    a = ap.parse_args()
    RL.warmup()
    print(f"=== A_v MASS DECOMPOSITION  kernel_hash={RL.kernel_hash()} ===")
    rows = {}
    tot = np.zeros(7, dtype=np.int64)
    for p in a.real:
        real = load_real_corpus([p])
        acc = np.zeros(7, dtype=np.int64)
        for col, vir, _ in real:
            acc += _decomp(col, vir)
        tot += acc
        rows[os.path.basename(p)] = acc.tolist()
    for label, acc in list(rows.items()) + [("COMBINED", tot.tolist())]:
        vq0, vq1, r0, r1, nv, cut_vq, cut_rdy = acc
        print(f"\n  {label}")
        print(f"    (1) vertical-axis mass  sum(vq)      {vq0:9d} -> {vq1:9d}   "
              f"unreachable share {1 - vq1 / vq0:6.1%}")
        print(f"    (2) rdy_ext mass        sum(max)     {r0:9d} -> {r1:9d}   "
              f"unreachable share {1 - r1 / r0:6.1%}   <-- what the eval adds up")
        print(f"    (3) per-virus incidence              {cut_vq:9d}/{nv} viruses lose "
              f"vertical credit = {cut_vq / nv:5.1%}; of those, {cut_rdy}/{cut_vq} "
              f"= {cut_rdy / max(1, cut_vq):5.1%} actually change rdy_ext "
              f"(the rest are masked by hq)")
    if a.out:
        with open(a.out, "w") as fh:
            json.dump({"kernel_hash": RL.kernel_hash(), "per_file": rows,
                       "combined": tot.tolist(),
                       "fields": ["vq_off", "vq_on", "rdy_off", "rdy_on", "nvir",
                                  "nvir_vq_cut", "nvir_rdy_cut"]}, fh, indent=1)


if __name__ == "__main__":
    main()
