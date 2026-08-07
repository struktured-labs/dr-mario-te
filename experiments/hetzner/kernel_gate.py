#!/usr/bin/env python3
"""kernel_gate.py -- can the fused champion kernel replace choose_base32 in the
census, and is it actually faster?

sp_engine.champ_root claims to reproduce ab47._choose_base action-for-action,
validated on 200 real-trajectory POSITIONS. That is a weaker claim than the one
the census needs. Position-level agreement and 300-move TRAJECTORY agreement are
different: one tie broken differently at move 40 diverges the rest of the game
while every individual position still "matched" when scored independently.
Errors compound along a trajectory; they don't compound across a shuffled
position corpus.

So this gate plays WHOLE GAMES both ways from identical seeds and compares the
full move trace, then times both. Same standard the local/remote node gate uses.

⚠ sp_engine puts `dr-mario-main-wt/experiments` on sys.path, a DIFFERENT worktree
from the one the census runs (`dr-mario-qa-wt`). If those trees have drifted, the
kernel is a different champion regardless of how faithful its arithmetic is --
exactly the code-skew hazard that already bit this project once. The gate reports
which files each side resolved so a mismatch is visible rather than inferred.

Usage: kernel_gate.py [--seeds 12]
"""
from __future__ import annotations

import sys
import time
import argparse

QA = "/home/struktured/projects/dr-mario-qa-wt/experiments"
SP = "/home/struktured/projects/dr-mario-selfplay-wt/experiments/selfplay"
sys.path.insert(0, QA + "/adversary")

import adversary_harness as AH  # noqa: E402


def play_with_kernel(seed, champ, max_pills=300):
    """adversary_harness.play_seed, but the decision comes from champ.choose()."""
    L = AH._lazy()
    FaithfulDrMarioEnv, NesPillSource, FB, RS = (
        L["FaithfulDrMarioEnv"], L["NesPillSource"], L["FB"], L["RS"])

    env = FaithfulDrMarioEnv(level=AH.LEVEL, seed=seed, max_pills=max_pills)
    env.reset()
    NesPillSource(seed=seed).attach(env)
    env.cur = env._rand_pill()
    env.nxt = env._rand_pill()

    res, trace = "stall", []
    for i in range(max_pills):
        if env.board.virus_count() == 0:
            res = "clear"
            break
        fb = FB.from_board(env.board)
        col, vir = RS.board_flat_from_fb(fb)
        a = champ.choose(col, vir, int(env.cur.a), int(env.cur.b),
                         int(env.nxt.a), int(env.nxt.b))
        if a < 0:                      # kernel's "no legal action" == choose_base32's None
            res = "topout"
            break
        trace.append((i, int(a)))
        _, _, term, trunc, info = env.step(int(a))
        if term:
            res = "clear" if info["won"] else "topout"
            break
        if trunc:
            res = "stall"
            break
    return {"seed": seed, "result": res, "pills": env.pills_placed,
            "viruses_left": int(env.board.virus_count()), "trace": trace}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--seeds", type=int, default=12)
    a = ap.parse_args()

    AH._lazy()
    sys.path.insert(0, SP)
    import sp_engine  # noqa: E402

    # Provenance: which tree did each side actually resolve?
    import reach_root as RR
    import root_search as RS_now
    print("PROVENANCE")
    print(f"  census reach_root : {RR.__file__}")
    print(f"  census root_search: {RS_now.__file__}")
    print(f"  kernel sp_engine  : {sp_engine.__file__}")
    print(f"  kernel WS_CHAMP   : {sp_engine.WS_CHAMP}  (census WS = {AH.WS})")
    if int(sp_engine.WS_CHAMP) != int(AH.WS):
        print("  ⚠ DOSE MISMATCH -- kernel is not the census champion")
    print()

    champ = sp_engine.Champion()
    seeds = [1000 + 37 * i for i in range(a.seeds // 2)] + \
            [32768 + 1009 * i for i in range(a.seeds - a.seeds // 2)]

    # warm both paths (numba compile) before timing anything
    AH.play_seed(seeds[0])
    play_with_kernel(seeds[0], champ)

    mismatches, t_ref, t_ker, n_moves = [], 0.0, 0.0, 0
    for s in seeds:
        t0 = time.monotonic(); ref = AH.play_seed(s); t_ref += time.monotonic() - t0
        t0 = time.monotonic(); ker = play_with_kernel(s, champ); t_ker += time.monotonic() - t0

        rt = [list(t) for t in ref["trace"]]
        kt = [list(t) for t in ker["trace"]]
        same = (ref["result"] == ker["result"] and ref["pills"] == ker["pills"]
                and ref["viruses_left"] == ker["viruses_left"] and rt == kt)
        n_moves += len(rt)
        if not same:
            first = next((i for i, (x, y) in enumerate(zip(rt, kt)) if x != y), None)
            mismatches.append((s, first, len(rt), len(kt)))
        print(f"  seed {s:6d} {'MATCH' if same else 'DIVERGED'}  "
              f"ref={ref['result']}/{ref['pills']} ker={ker['result']}/{ker['pills']}",
              flush=True)

    print()
    if mismatches:
        print(f"GATE FAIL -- {len(mismatches)}/{len(seeds)} games diverged")
        for s, first, lr, lk in mismatches[:5]:
            print(f"  seed {s}: first differing move index {first} "
                  f"(ref {lr} moves, kernel {lk})")
    else:
        print(f"GATE PASS -- {len(seeds)}/{len(seeds)} whole games identical "
              f"({n_moves} moves compared)")
    print(f"\nTIMING  reference {t_ref:.1f}s   kernel {t_ker:.1f}s   "
          f"speedup {t_ref / t_ker:.2f}x" if t_ker > 0 else "")


if __name__ == "__main__":
    main()
