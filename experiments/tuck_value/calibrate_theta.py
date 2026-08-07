#!/usr/bin/env python3
"""How loose is the firmware's theta gate in THIS rig's eval units?

The problem, in the firmware's own words (fpga/copro/tuck_v3.py:70-72): a
tuck-margin threshold of 150 "is a LOOSER gate in shipped-eval units than in
the offline coef-opt units" -- the firmware fired 4.38 tucks/game at theta=150
where the offline rig fired 2.80 at the same number. The two eval chains do
not share a scale, so copying the constant across does NOT copy the behaviour.
Any offline arm claiming to represent the tier-3 firmware has to say which it
matched: the NUMBER or the FIRE RATE.

This calibrates against RTL ground truth at zero RTL cost. The co-sim farm's
decide_compare artifact records, for each of 20 real L11 boards, whether the
verilated s20t3 firmware published a tuck at all. That publish RATE is the
target; this sweeps theta in this rig's units and reports the rate it
produces on the SAME boards with the SAME pills.

WHAT THIS CAN AND CANNOT SAY: the fast sim and the RTL disagree on most
individual moves (38% full-move agreement, co-sim README), so the SET of
boards that fire will differ even at a perfectly matched theta. The RATE is
therefore the only honest calibration target, and "matched fire rate" is a
weaker claim than "matched decisions". It is still much better than assuming
150 means the same thing on both sides, which is the assumption every offline
tier sweep to date has made.

BOARD DECODE (NES playfield byte -> fast-sim planes): 0xFF = empty; otherwise
low nibble = colour (0-based on the firmware side, +1 for the sim's 1-based
plane) and high nibble = link direction, with 0xD marking a virus. Pill
colours in the hostdata header are 0-based for the same reason
(gen_corpus_l11.py writes "cA cB nA nB 0 0" from rng.randint(0, 2)).

Usage: calibrate_theta.py [--thetas 0,50,100,150,250]
"""
from __future__ import annotations

import argparse
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
EXPERIMENTS = os.path.dirname(HERE)
EVAL47 = os.path.join(EXPERIMENTS, "eval47")
for _p in (HERE, EXPERIMENTS, EVAL47):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import run_2x2 as R2          # noqa: E402
import reach_root as RR       # noqa: E402

DEFAULT_DECIDE = "/mnt/data/drmario_cosim/results/decide_compare_l11_20.json"
NES_EMPTY = 0xFF
VIRUS_NIBBLE = 0xD


def read_hostdata_full(path):
    """-> [(cA, cB, nA, nB, board128)] with pill colours mapped to the sim's
    1-based convention."""
    toks = open(path).read().split()
    i = 0
    n = int(toks[i]); i += 1
    out = []
    for _ in range(n):
        cA, cB, nA, nB = (int(toks[i + k]) for k in range(4))
        i += 6
        board = [int(toks[i + k], 16) for k in range(128)]
        i += 128
        out.append((cA + 1, cB + 1, nA + 1, nB + 1, board))
    return out


def planes(board):
    import numpy as np
    col = np.zeros(128, dtype=np.int8)
    vir = np.zeros(128, dtype=np.int8)
    for i, b in enumerate(board):
        if b == NES_EMPTY:
            continue
        col[i] = (b & 0x0F) + 1
        if (b >> 4) == VIRUS_NIBBLE:
            vir[i] = 1
    return col, vir


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--decide", default=DEFAULT_DECIDE)
    ap.add_argument("--thetas", default="0,25,50,100,150,250")
    a = ap.parse_args()

    if not os.path.exists(a.decide):
        print(f"decide_compare artifact not present: {a.decide}")
        return 2
    d = json.load(open(a.decide))
    cases = read_hostdata_full(d["hostdata"])
    rtl_pub = d["tuck_published"]

    RR._lazy()
    from fb import FB

    print("=== theta calibration vs RTL publish rate ===")
    print(f"boards {len(cases)} from {os.path.basename(d['hostdata'])}")
    for arm, cnt in rtl_pub.items():
        md5 = d["arms"][arm]["fw_md5"][:8]
        print(f"  RTL {arm:<12} {md5}  published {cnt}/{len(cases)} "
              f"({cnt / len(cases):.0%} of decisions)")
    print()

    # ---- v1: publish rate is directly comparable, and gate-free -----------
    # v1 has NO value gate at all (tuck_scan.py picks the deepest rest and
    # publishes it), so "descriptor published" is the same event on both
    # sides and this is a true like-for-like check.
    import tuck_scan
    v1_pub = sum(1 for _cA, _cB, _nA, _nB, b in cases
                 if tuck_scan.ref_tuck_scan(b)[0] != 0xFF)
    print(f"v1 publish rate   this rig {v1_pub}/{len(cases)}   "
          f"RTL {rtl_pub.get('s20b')}/{len(cases)}   "
          f"{'MATCH' if v1_pub == rtl_pub.get('s20b') else 'DIFFER'}")

    # ---- tier-3: two DIFFERENT events, reported separately ---------------
    # The RTL's `tuck_published` counts TUCK_COL != 0xFF, i.e. a descriptor
    # was emitted -- confirmed by the v1 line above matching exactly, since
    # v1 publishes unconditionally. Whether the tuck ALSO won the theta gate
    # and overwrote D_BC/D_BO is a separate, stricter event that the artifact
    # does not distinguish. Comparing the RTL's publish rate against this
    # rig's WIN rate would be comparing two different things, so both are
    # printed and only the first is comparable.
    thetas = [float(x) for x in a.thetas.split(",")]
    print(f"\n{'theta':>7}  {'tuck AVAILABLE':>16}  {'tuck WINS gate':>16}")
    avail = None
    for th in thetas:
        wins = 0
        av = 0
        for cA, cB, nA, nB, board in cases:
            col, vir = planes(board)
            fb = FB.from_lists(col.tolist(), vir.tolist(), [0] * 128)
            pick, _base = R2.choose_with_base(fb, col, vir, cA, cB, nA, nB,
                                              "t3", th)
            wins += int(pick["kind"] == "tuck")
            av += int(pick.get("n_tuck_cands", 0) > 0)
        avail = av
        print(f"{th:>7.0f}  {av:>10}/{len(cases):<4} {av / len(cases):>4.0%}  "
              f"{wins:>10}/{len(cases):<4} {wins / len(cases):>4.0%}")

    t3 = rtl_pub.get("s20t3")
    print(f"\ntier-3 publish rate   this rig {avail}/{len(cases)} "
          f"({avail / len(cases):.0%})   RTL {t3}/{len(cases)} ({t3 / len(cases):.0%})")
    print("The AVAILABLE column is the one comparable to the RTL publish rate; "
          "the WINS column is the stricter event this rig's arms actually act on.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
