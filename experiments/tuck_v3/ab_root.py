#!/usr/bin/env python3
"""Paired A/B: shipped depth-3 search vs shipped + GENERALISED ROOT-ACTION TUCKS (v3),
on the REAL NES capsule stream only (per house rule -- tucks are capsule-dependent, so a
uniform stream is exactly the class of thing that inflates them; see tuck_ab.py's own
docstring for the same argument, independently re-derived here).

Arm OFF: choose_root_with_tucks() with tuck_cands forced to [] -- proven byte-identical
to the untouched FastShipD3DeciderEH by root_search.equivalence_selftest().
Arm ON : choose_root_with_tucks() with the executor-motion-legal tuck candidates included
in the SAME 32-slot depth-3 argmax (the surviving design from dr-mario-tuck-executor-gap's
"ROOT-ACTION SPEC REFINEMENTS" -- NOT the refuted leaf-gated post-search override).

Reports, per level:
  1. paired pills-to-clear delta on seeds where BOTH arms cleared (primary metric, per
     the virus-tempo house rule), bootstrap 95% CI, clustered by seed (each seed is one
     paired observation, which is already the clustering unit here).
  2. clear rate + discordant pairs + exact two-sided sign test (robustness axis).
  3. tuck diagnostics: fires/game, candidates seen/game, and an EXECUTABILITY count --
     every fired tuck is re-verified against the executor's reach model at fire time;
     any placement that fails is a DESIGN BUG and is counted, not silently dropped.

Usage: ab_root.py --seeds 120 --level 11 --workers 6
"""
from __future__ import annotations

import sys
import os
import json
import random
import argparse
import statistics as st
from concurrent.futures import ProcessPoolExecutor, as_completed

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = "/home/struktured/projects/dr_mario_rl"
QA = "/home/struktured/projects/dr-mario-qa-wt/experiments"
for _p in (HERE, ROOT + "/tmp/combo_term", ROOT + "/tmp/endgame", ROOT + "/tmp/tuck",
           ROOT + "/tmp/pillrng", ROOT + "/.claude/worktrees/faithful-sim/src", QA):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import fast_rtl_x as FX
from fb import FB
import root_search as RS

_C = {}


def _init(level, tuck, P, exec_only, theta=0.0, log_decisions=False):
    FX.warmup_ship_eh(topk2=8)
    w, fl = FX.variant("winner")
    _C.update(level=level, tuck=tuck, P=P, exec_only=exec_only, w=w, fl=fl, theta=theta,
              log_decisions=log_decisions)


def play(seed):
    from drmario.faithful_env import FaithfulDrMarioEnv
    from drmario.faithful_game import LINK_LEFT, LINK_RIGHT, LINK_UP, LINK_DOWN
    from nes_pills import NesPillSource

    w, fl = _C["w"], _C["fl"]
    env = FaithfulDrMarioEnv(level=_C["level"], seed=seed, max_pills=300)
    env.reset()
    NesPillSource(seed=seed).attach(env)
    env.cur = env._rand_pill()
    env.nxt = env._rand_pill()

    seg = {"open": [0, 0], "mid": [0, 0], "end": [0, 0]}
    fired = 0
    fired_by_regime = {"open": 0, "mid": 0, "end": 0}
    cands_seen = 0
    unexecutable = 0
    margins = []
    decisions = []   # per-decision (n_cands, virus_count, fill_height), only when logging
    res = "stall"

    while True:
        fb = FB.from_board(env.board)
        vc = env.board.virus_count()

        if _C["tuck"]:
            tuck_cands = RS.tuck_root_candidates(fb, env.cur.a, env.cur.b,
                                                 frames_per_row=_C["P"],
                                                 exec_only=_C["exec_only"])
            cands_seen += len(tuck_cands)
            if _C.get("log_decisions"):
                decisions.append({"n": len(tuck_cands), "vc": vc,
                                  "fill": RS.fill_height(fb)})
        else:
            tuck_cands = []

        pick = RS.choose_root_with_tucks(fb, env.cur, env.nxt, w, fl, topk2=8,
                                         frames_per_row=_C["P"],
                                         exec_only=_C["exec_only"],
                                         tuck_cands=tuck_cands,
                                         theta=_C.get("theta", 0.0))

        k = "open" if vc > 32 else ("mid" if vc > 8 else "end")

        if pick["kind"] == "tuck":
            p = pick["placement"]
            r0, c0, r1, c1 = p["cells"]
            # RE-VERIFY executability at fire time, on THIS board, independent of the
            # candidate-generation filter -- an unexecutable fire is a design bug, not a
            # thing to silently trust because the generator claimed it was legal.
            if _C["exec_only"]:
                reach = RS._exec_reach_cells(fb)
                deep = (r0, c0) if r0 >= r1 else (r1, c1)
                if deep not in reach:
                    unexecutable += 1
            b = env.board
            b.color[r0, c0] = pick["ca"]
            b.color[r1, c1] = pick["cb"]
            if r0 == r1:
                b.link[r0, c0] = LINK_RIGHT
                b.link[r1, c1] = LINK_LEFT
            else:
                b.link[r0, c0] = LINK_DOWN
                b.link[r1, c1] = LINK_UP
            b.is_virus[r0, c0] = False
            b.is_virus[r1, c1] = False
            b.resolve()
            env.pills_placed += 1
            env.cur = env.nxt
            env.nxt = env._rand_pill()
            fired += 1
            fired_by_regime[k] += 1
            if pick.get("margin") is not None:
                margins.append(float(pick["margin"]))
            seg[k][0] += 1
            seg[k][1] += vc - b.virus_count()
            if b.virus_count() == 0:
                res = "clear"
                break
            if b.spawn_blocked():
                res = "topout"
                break
            if env.pills_placed >= 300:
                break
            continue

        a = pick["action"]
        _, _, term, trunc, info = env.step(int(a))
        seg[k][0] += 1
        seg[k][1] += vc - env.board.virus_count()
        if term:
            res = "clear" if info["won"] else "topout"
            break
        if trunc:
            break

    return {"seed": seed, "won": int(res == "clear"), "pills": env.pills_placed,
            "fired": fired, "fired_by_regime": fired_by_regime,
            "cands_seen": cands_seen, "unexecutable": unexecutable,
            "margins": margins, "seg": seg, "decisions": decisions}


def boot_ci(xs, stat=st.mean, n=10000, seed=12345):
    if not xs:
        return (float("nan"), float("nan"))
    rng = random.Random(seed)
    k = len(xs)
    reps = [stat([xs[rng.randrange(k)] for _ in range(k)]) for _ in range(n)]
    reps.sort()
    return reps[int(0.025 * n)], reps[int(0.975 * n)]


def sign_test_p(better, worse):
    """Exact two-sided binomial sign test, p=0.5 null. n small in practice; brute force."""
    from math import comb
    n = better + worse
    if n == 0:
        return 1.0
    k = min(better, worse)
    p = sum(comb(n, i) for i in range(0, k + 1)) * (0.5 ** n) * 2
    return min(1.0, p)


def run_level(level, seeds, workers, P, exec_only):
    R = {}
    for tuck in (0, 1):
        rows = []
        with ProcessPoolExecutor(max_workers=workers, initializer=_init,
                                 initargs=(level, tuck, P, exec_only)) as ex:
            for f in as_completed([ex.submit(play, s) for s in range(seeds)]):
                rows.append(f.result())
        R[tuck] = {r["seed"]: r for r in rows}
        print(f"  L{level} arm tuck={tuck} done ({len(rows)} games)", flush=True)

    off, on = R[0], R[1]
    all_seeds = sorted(set(off) & set(on))

    both = [s for s in all_seeds if off[s]["won"] and on[s]["won"]]
    d = [on[s]["pills"] - off[s]["pills"] for s in both]
    lo, hi = boot_ci(d)
    better = sum(1 for x in d if x < 0)
    worse = sum(1 for x in d if x > 0)

    c_off = sum(off[s]["won"] for s in all_seeds) / len(all_seeds)
    c_on = sum(on[s]["won"] for s in all_seeds) / len(all_seeds)
    disc = [(off[s]["won"], on[s]["won"]) for s in all_seeds if off[s]["won"] != on[s]["won"]]
    won_only_on = sum(1 for o, n in disc if n)
    won_only_off = len(disc) - won_only_on
    p_clear = sign_test_p(won_only_on, won_only_off)

    fires = [on[s]["fired"] for s in all_seeds]
    cands = [on[s]["cands_seen"] for s in all_seeds]
    unexec = sum(on[s]["unexecutable"] for s in all_seeds)

    out = {
        "level": level, "seeds": len(all_seeds), "P": P, "exec_only": exec_only,
        "paired_pills_delta_mean": st.mean(d) if d else float("nan"),
        "paired_pills_ci": [lo, hi],
        "paired_n": len(both), "better": better, "worse": worse, "tie": len(d) - better - worse,
        "clear_off": c_off, "clear_on": c_on,
        "discordant": len(disc), "tuck_only_wins": won_only_on, "tuck_only_losses": won_only_off,
        "sign_test_p": p_clear,
        "fires_per_game": st.mean(fires) if fires else 0.0,
        "cands_per_game": st.mean(cands) if cands else 0.0,
        "unexecutable_total": unexec,
    }

    verdict = "REAL (CI excludes 0)" if (hi < 0 or lo > 0) else "WASH (CI spans 0)"
    print(f"\n=== ROOT-ACTION TUCKS v3, L{level}, n={len(all_seeds)} paired seeds, "
          f"P={P}, exec_only={exec_only} ===")
    print(f"1. PAIRED PILLS (both cleared, n={len(both)}/{len(all_seeds)})")
    print(f"   mean delta {out['paired_pills_delta_mean']:+.2f}   95% CI [{lo:+.2f}, {hi:+.2f}]")
    print(f"   better {better} / worse {worse} / tie {out['tie']}   => {verdict}")
    print(f"2. CLEAR RATE  off {c_off:.1%} -> on {c_on:.1%}   discordant {len(disc)} "
          f"(tuck-only wins {won_only_on}, tuck-only losses {won_only_off}, "
          f"sign-test p={p_clear:.4f})")
    print(f"3. TUCK DIAGNOSTICS  fires/game {out['fires_per_game']:.2f}   "
          f"candidates seen/game {out['cands_per_game']:.2f}   "
          f"UNEXECUTABLE fired (design bug if >0): {unexec}")

    return out, R


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--seeds", type=int, default=120)
    ap.add_argument("--levels", type=int, nargs="+", default=[11])
    ap.add_argument("--workers", type=int, default=6)
    ap.add_argument("--P", type=int, default=12)
    ap.add_argument("--exec-only", type=int, default=1)
    ap.add_argument("--out", type=str, default=None)
    a = ap.parse_args()

    results = {}
    for level in a.levels:
        out, R = run_level(level, a.seeds, a.workers, a.P, bool(a.exec_only))
        results[level] = out
        if a.out:
            fn = f"{a.out}_L{level}.json"
            with open(fn, "w") as fh:
                json.dump({"summary": out,
                          "off": [R[0][s] for s in sorted(R[0])],
                          "on": [R[1][s] for s in sorted(R[1])]}, fh)
            print(f"wrote {fn}")

    print("\n=== SUMMARY ===")
    for level, out in results.items():
        lo, hi = out["paired_pills_ci"]
        verdict = "REAL" if (hi < 0 or lo > 0) else "WASH"
        print(f"L{level}: paired pills {out['paired_pills_delta_mean']:+.2f} "
              f"[{lo:+.2f},{hi:+.2f}] {verdict}   clear {out['clear_off']:.1%}->"
              f"{out['clear_on']:.1%}   fires/g {out['fires_per_game']:.2f}   "
              f"unexecutable {out['unexecutable_total']}")


if __name__ == "__main__":
    main()
