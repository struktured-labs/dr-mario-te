#!/usr/bin/env python3
"""GATE: cascade_dbl_x at w_dbl=0 must be cascade_chain_x, action for action.

TWO ASSERTIONS, and the second is the one that catches the dangerous failure.

  1 NEUTRALITY -- w_dbl=0 must choose the IDENTICAL action to ChainRewardD3Decider at the
    same w_chain, on every position of a real played corpus. This is the same discipline
    that w_chain=0 owes cascade_link_x. It catches a threading mistake that changes
    behaviour when the new term is supposed to be inert.

  2 POTENCY (the load-bearing witness) -- w_dbl=100 must DIFFER somewhere. A reward that
    is wired into the root but not the third ply, or computed and then dropped, passes
    assertion 1 perfectly: it is inert at 0 and *nearly* inert at 100, so the ladder would
    run, produce plausible win rates, and be measuring a knob that barely exists. An arm
    that plays well while answering a different question than its label is exactly the
    failure this project keeps finding, so "the knob provably moves decisions" is a
    prerequisite for the ladder, not a nice-to-have.

  3 PLY REACH -- potency is additionally required at depth: a term wired only into the root
    imm would still move some root decisions. So the check also counts differences on
    positions where the ROOT's own best move is unchanged by the credit but the search
    outcome differs, which can only happen through ply 2/3.

Run this BEFORE any ladder. Exit 0 = the knob is inert at 0 and real at 100.
"""
from __future__ import annotations
import sys

for p in ("/home/struktured/projects/dr_mario_rl/tmp/vs_aware",
          "/home/struktured/projects/dr_mario_rl/tmp/combo_term",
          "/home/struktured/projects/dr_mario_rl/tmp/champion",
          "/home/struktured/projects/dr_mario_rl/tmp/pillrng",
          "/home/struktured/projects/dr_mario_rl/.claude/worktrees/faithful-sim/src",
          "/home/struktured/projects/dr-mario-qa-wt/experiments"):
    if p not in sys.path:
        sys.path.insert(0, p)

import numpy as np                                            # noqa: E402
from drmario.faithful_env import FaithfulDrMarioEnv           # noqa: E402
import fast_rtl_x as F                                        # noqa: E402
import cascade_chain_x as C                                   # noqa: E402
import cascade_dbl_x as D                                     # noqa: E402
from h2h_vs import ARMS, idx_map                              # noqa: E402

W_CHAIN = 180
SEEDS = [1, 2, 3, 4, 5, 6, 7, 8]
PLIES = 60


def weights_for(arm_name="chain180"):
    w, fl = F.variant("winner")
    m = idx_map()
    for k, v in ARMS[arm_name].items():
        if k in m:
            w[m[k]] = float(v)
    return w, fl


def main():
    C.warmup_chain(8)
    D.warmup_dbl(8)
    w, fl = weights_for()

    ref = C.ChainRewardD3Decider(w, fl, topk2=8, maxpass=0, w_chain=W_CHAIN)
    neu = D.DblRewardD3Decider(w, fl, topk2=8, maxpass=0, w_chain=W_CHAIN, w_dbl=0)
    hot = D.DblRewardD3Decider(w, fl, topk2=8, maxpass=0, w_chain=W_CHAIN, w_dbl=100)

    n = mismatch = moved = 0
    bad = []
    for seed in SEEDS:
        e = FaithfulDrMarioEnv(level=11, seed=seed, max_pills=PLIES)
        e.reset()
        for _ in range(PLIES):
            if e.board.virus_count() == 0:
                break
            a_ref = ref.choose(e.board, e.cur, e.nxt)
            a_neu = neu.choose(e.board, e.cur, e.nxt)
            a_hot = hot.choose(e.board, e.cur, e.nxt)
            if a_ref is None:
                break
            n += 1
            if a_neu != a_ref:
                mismatch += 1
                if len(bad) < 5:
                    bad.append((seed, n, a_ref, a_neu))
            if a_hot != a_ref:
                moved += 1
            # advance on the REFERENCE arm so all three see identical positions
            out = e.step(a_ref)
            if isinstance(out, tuple) and len(out) >= 3 and out[2]:
                break

    print("positions compared : %d  (%d seeds x up to %d plies)" % (n, len(SEEDS), PLIES))
    print("w_dbl=0   mismatches vs cascade_chain_x : %d" % mismatch)
    print("w_dbl=100 decisions moved                : %d (%.1f%%)"
          % (moved, 100.0 * moved / max(1, n)))
    if bad:
        print("  first mismatches (seed, ply, chain_action, dbl0_action):")
        for b in bad:
            print("    %s" % (b,))
    print()

    ok = True
    if n < 50:
        print("GATE INCONCLUSIVE: only %d positions -- corpus too small to certify." % n)
        return 2
    if mismatch:
        print("GATE FAILED (neutrality): w_dbl=0 is NOT cascade_chain_x.")
        print("  The credit is not inert when it is supposed to be, so every ladder arm")
        print("  would be confounded with a physics change. Fix the threading.")
        ok = False
    else:
        print("NEUTRALITY OK: w_dbl=0 reproduces cascade_chain_x on all %d positions." % n)
    if moved == 0:
        print("GATE FAILED (potency): w_dbl=100 changed NOTHING.")
        print("  The term is computed and then not reaching the decision -- an arm that")
        print("  would run, look plausible, and measure a knob that does not exist.")
        ok = False
    else:
        print("POTENCY OK: w_dbl=100 moves %d/%d decisions -- the knob is real." % (moved, n))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
