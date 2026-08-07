#!/usr/bin/env python3
"""Does the FAST SIM's move agree with the REAL RTL's move? (the tier-ladder question)

The three-tier plan is: fast sim for breadth, co-sim to confirm survivors, hardware once.
That plan rests on an untested assumption -- that the fast sim is a good enough proxy to
RANK designs. This measures the proxy directly, at the only place it can be measured
without a hardware run: the move itself, on identical boards, against RTL ground truth.

Why this number is worth having even though it is not the whole story: move agreement is
a LOWER bound on ranking fidelity. Two deciders can disagree on individual moves and
still rank designs identically (the errors cancel, which is the team's own argument for
using the fast sim at all). So a low agreement rate does NOT by itself invalidate
fast-sim rankings -- but a HIGH agreement rate would strongly support them, and the gap
between this number and py65's known 13.3% (CANDIDATE_TIER3.md sec 10) tells us which
proxy to prefer for pre-screening co-sim work.

Costs nothing in RTL: the co-sim decisions were already recorded by decide_compare.py.

Usage: transfer_check.py <decide_compare.json> <hostdata.txt> [more pairs...]
"""
from __future__ import annotations

import json
import os
import sys
from collections import Counter

HERE = os.path.dirname(os.path.abspath(__file__))
RL = "/home/struktured/projects/dr_mario_rl"
QA = "/home/struktured/projects/dr-mario-qa-wt/experiments"
for _p in (HERE, RL + "/tmp/combo_term", RL + "/tmp/endgame",
           RL + "/.claude/worktrees/faithful-sim/src", QA, QA + "/eval47"):
    if _p not in sys.path:
        sys.path.insert(0, _p)

RING_NAME = ("H", "V", "RH", "RV")
RING_OF_O4 = (3, 1, 0, 2)
# inverse of cosim.VAR_OF_O4 = (2, 3, 0, 1): variant -> o4
VAR_OF_O4 = (2, 3, 0, 1)
O4_OF_VAR = tuple(VAR_OF_O4.index(v) for v in range(4))


def nes_to_board(nes):
    """Inverse of cosim.board_to_nes: rebuild a FaithfulBoard from the 128 NES bytes.

    Needed because the champion's decider takes a BOARD (it reads the link plane for the
    chain engine), not the flat bytes the base search takes. The link nibble is threaded
    back through -- dropping it would feed the chain reward a board of orphans and measure
    the wrong decider.
    """
    import numpy as np
    from drmario.faithful_game import (
        FaithfulBoard, LINK_UP, LINK_DOWN, LINK_LEFT, LINK_RIGHT,
    )
    link_of_hi = {0x4: LINK_DOWN, 0x5: LINK_UP, 0x6: LINK_RIGHT, 0x7: LINK_LEFT}
    b = FaithfulBoard(16, 8, rng=np.random.default_rng(0))
    b.color[:, :] = 0
    b.is_virus[:, :] = False
    b.link[:, :] = 0
    for i, v in enumerate(nes):
        if v == 0xFF:
            continue
        r, c = divmod(i, 8)
        hi = (v >> 4) & 0xF
        b.color[r, c] = (v & 0x3) + 1
        if hi == 0xD:
            b.is_virus[r, c] = True
        elif hi in link_of_hi:
            b.link[r, c] = link_of_hi[hi]
    return b


def read_hostdata_full(path):
    toks = open(path).read().split()
    i = 0
    n = int(toks[i]); i += 1
    out = []
    for _ in range(n):
        cA, cB, nA, nB = (int(toks[i + k]) for k in range(4))
        i += 6
        board = [int(toks[i + k], 16) for k in range(128)]
        i += 128
        out.append((board, cA, cB, nA, nB))
    return out


def main():
    args = sys.argv[1:]
    if len(args) < 2 or len(args) % 2:
        print(__doc__)
        return 1

    import fast_rtl_x as FX
    FX.warmup_ship_eh(topk2=8)

    # Which fast-sim decider to compare. "base" is FX.decide_ship_d3 -- the base search.
    # "champion" is StrandedChainD3Decider(w_chain=180, ws=20), what the shipped champion
    # and the adversary/VS lanes actually run. The distinction matters: a 68% figure
    # measured on the base search is an EXTRAPOLATION when applied to lanes running the
    # champion, and this project has been bitten by numbers travelling further than the
    # thing they measured.
    which = os.environ.get("TRANSFER_DECIDER", "base")
    champ = None
    if which == "champion":
        from cascade_stranded_x import StrandedChainD3Decider
        from drmario.faithful_game import Pill
        w, fl = FX.variant("winner")
        champ = (StrandedChainD3Decider(w, fl, topk2=8, maxpass=0, w_chain=180, ws=20),
                 Pill)
    print(f"decider under test: {which}")

    tot = agree = agree_col = agree_o4 = 0
    fast_none = 0
    per = []
    orient_fast, orient_rtl = Counter(), Counter()

    for k in range(0, len(args), 2):
        r = json.load(open(args[k]))
        cases = read_hostdata_full(args[k + 1])
        assert len(cases) == r["n_boards"]
        rtl_rows = r["rows"][r["base"]]        # the SHIPPED firmware is the ground truth
        n = a = ac = ao = 0
        for i, (board, cA, cB, nA, nB) in enumerate(cases):
            if champ is None:
                # decide_ship_d3 takes NES low-nibble colours (faithful colour minus 1);
                # the hostdata colours are already in that 0..2 convention.
                got = FX.decide_ship_d3(board, cA, cB, nA, nB, w_vrdy=24, topk2=8)
                if got is None:
                    fast_none += 1
                    continue
                fcol, fo4 = int(got[0]), int(got[1])
            else:
                # The champion decider takes a BOARD and 1-BASED Pill colours, and returns
                # an ACTION (variant*8 + col). Invert VAR_OF_O4 to get back to o4 space so
                # the comparison is like-for-like with the RTL's published (col, o4).
                dec, Pill = champ
                act = dec.choose(nes_to_board(board),
                                 Pill(cA + 1, cB + 1), Pill(nA + 1, nB + 1))
                if act is None:
                    fast_none += 1
                    continue
                variant, fcol = divmod(int(act), 8)
                fo4 = O4_OF_VAR[variant]
            rcol, ro4 = rtl_rows[i]["col"], rtl_rows[i]["o4"]
            n += 1
            orient_fast[RING_NAME[RING_OF_O4[fo4]]] += 1
            orient_rtl[RING_NAME[RING_OF_O4[ro4]]] += 1
            if fcol == rcol:
                ac += 1
            if fo4 == ro4:
                ao += 1
            if (fcol, fo4) == (rcol, ro4):
                a += 1
        per.append({"corpus": os.path.basename(args[k + 1]), "n": n,
                    "full": a, "col": ac, "orient": ao,
                    "full_frac": a / n if n else None})
        print(f"{os.path.basename(args[k+1]):<26} n={n:>3}  "
              f"full (col,orient) {a:>3}/{n} ({a/n:5.1%})   "
              f"col-only {ac:>3} ({ac/n:5.1%})   orient-only {ao:>3} ({ao/n:5.1%})")
        tot += n; agree += a; agree_col += ac; agree_o4 += ao

    print(f"\nCOMBINED  n={tot}  full {agree}/{tot} = {agree/tot:.1%}   "
          f"col {agree_col/tot:.1%}   orient {agree_o4/tot:.1%}")
    print(f"fast sim returned no legal move on {fast_none} boards")
    print(f"orientation mix  fast={dict(orient_fast)}  rtl={dict(orient_rtl)}")
    print("\nreference: py65 vs RTL on real-L11 boards = 13.3% full "
          "(CANDIDATE_TIER3.md sec 10, n=30)")
    print("NOTE: move agreement is a LOWER bound on RANKING fidelity -- two deciders can "
          "disagree per-move\n      and still rank designs identically. Read this as "
          "'how good a proxy', not 'is the fast sim wrong'.")

    out = {"combined": {"n": tot, "full": agree, "col": agree_col, "orient": agree_o4,
                        "full_frac": agree / tot if tot else None},
           "per_corpus": per,
           "fast_no_move": fast_none,
           "orient_fast": dict(orient_fast), "orient_rtl": dict(orient_rtl),
           "py65_reference_full_frac": 0.133,
           "decider": which}
    dst = "/mnt/data/drmario_cosim/results/transfer_check_%s.json" % which
    json.dump(out, open(dst, "w"), indent=1)
    print(f"wrote {dst}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
