#!/usr/bin/env python3
"""spawn_lane_gate_probe.py -- CAN a gated spawn-lane penalty ever fire?
Measured before anyone builds it, on boards we already have.

WHY THIS EXISTS. The selfseal lane ran a 4-dose sweep at n=200 and got a flat
null -- and its own instrumentation showed why: at 10x the smallest dose the
term still changed 95/15,145 = 0.63% of decisions. That experiment could not
distinguish "the idea is wrong" from "the term never fired", and ~35,000 games
bought an uninterpretable result. Task #78's spawn-lane guard is the same shape
(a root-only penalty, gated on recent garbage), so measure the gate FIRST.

TWO RATES, REPORTED SEPARATELY, because they are different failure modes:
  GATE-OPEN  -- how often the gate condition holds at all. If this is tiny the
                design is wrong (the trigger is too narrow).
  ARGMAX-FLIP -- how often applying the penalty actually changes the champion's
                choice. A gate that opens but never flips means the dose is too
                small, or the alternatives were already equivalent.
Only the second one moves a win rate. A term can be "active" on 30% of
decisions and still be worth exactly nothing.

REUSE, NOT REBUILD. `adversary_t3/instrumented_champion.py::all_candidates`
already returns every legal candidate with its value AND `spawnh` -- the max
stack height in columns 3/4 of the RESULTING board, i.e. precisely the feature
#78 would penalise. And `gen_pressure_deaths.py::play()` is the loop that
produced the death corpus. This composes the two rather than writing a third
copy of either.

⚠ WHICH CHAMPION. These numbers are for `StrandedChainD3Decider`
(chain180 + ws20) -- the decider the pressure-death corpus was generated with,
so the replay is faithful. That is the Combo-Stomper lineage, NOT
`reach_root.choose_base32`. Flip rates are decider-specific; gate-open rates
are essentially a board statistic and transfer more readily.

NO NEW GAMES: every trajectory is replayed from a stored (seed, actions) pair,
and the bursty injection is keyed on (seed, pills_placed, clear_size), so
forcing the recorded actions reproduces the recorded garbage exactly.

Usage: spawn_lane_gate_probe.py --corpus <deaths.jsonl> --out results/gate_probe.json
"""
from __future__ import annotations

import os
import sys
import json
import argparse
import numpy as np

QA = "/home/struktured/projects/dr-mario-qa-wt/experiments"
ROOT = "/home/struktured/projects/dr_mario_rl"
for _p in (QA + "/adversary_t3", QA + "/eval47", QA + "/tuck_v3", QA,
           ROOT + "/tmp/combo_term", ROOT + "/tmp/endgame", ROOT + "/tmp/tuck",
           ROOT + "/tmp/pillrng", ROOT + "/.claude/worktrees/faithful-sim/src"):
    if _p not in sys.path:
        sys.path.insert(0, _p)

GARBAGE_MIN_PILLS = 25          # gen_pressure_deaths.py / pressure_rig.py


def build_v1_1():
    import bursty_model as BM
    import fit_ensemble_source as FE
    m_v1 = BM.fit_struktured_20260804()
    raw = m_v1.meta["raw_events"]
    v, c = [], []
    for _mid, res in raw.items():
        v.extend(res["volleys"]); c.extend(res["clears"])
    return FE.fit_per_player(v, c, m_v1.n_matches, "P1", dict(BM.DEFAULT_OPPONENT_OF))


def replay_and_probe(seed, actions, model, level=11, max_pills=300):
    """Replay one recorded game, recording per-decision candidate sets.

    Returns list of {ply, plies_since_garbage, cands:[{action,val,spawnh}]}.
    Asserts the replay reproduces the recorded action at every ply -- if the
    champion's own choice ever differs from what was recorded, the replay is
    not the game the corpus describes and its numbers are meaningless.
    """
    from drmario.faithful_env import FaithfulDrMarioEnv
    from nes_pills import NesPillSource
    from bursty_model import inject_bursty_garbage
    from instrumented_champion import all_candidates

    env = FaithfulDrMarioEnv(level=level, seed=seed, max_pills=max_pills)
    env.reset()
    NesPillSource(seed=seed).attach(env)
    env.cur = env._rand_pill()
    env.nxt = env._rand_pill()

    out = []
    last_garbage_ply = -10**6
    for ply, rec_a in enumerate(actions):
        if env.board.virus_count() == 0:
            break
        cands = all_candidates(env.board, env.cur, env.nxt)
        if not cands:
            break
        if int(cands[0]["action"]) != int(rec_a):
            raise AssertionError(
                f"replay diverged at seed {seed} ply {ply}: champion chose "
                f"{cands[0]['action']}, corpus recorded {rec_a}")
        out.append({"ply": ply,
                    "since_garbage": ply - last_garbage_ply,
                    "cands": [{"a": int(c["action"]), "v": int(c["val"]),
                               "sh": int(c["spawnh"])} for c in cands]})

        occ_before = int(np.count_nonzero(env.board.color))
        _, _, term, trunc, info = env.step(int(rec_a))
        if term or trunc:
            break
        if env.pills_placed >= GARBAGE_MIN_PILLS:
            occ_after = int(np.count_nonzero(env.board.color))
            clear_size = max(0, occ_before + 2 - occ_after)
            if clear_size > 0:
                if inject_bursty_garbage(env.board, model, seed, env.pills_placed,
                                         clear_size) > 0:
                    last_garbage_ply = ply
            if env.board.virus_count() == 0 or env.board.spawn_blocked():
                break
    return out


def evaluate(decisions, k, h, dose):
    """Gate-open / term-active / argmax-flip counts for one (k, h, dose).

    Penalty is root-only and linear above the threshold:
        pen(cand) = dose * max(0, cand.spawnh - h)   when the gate is open
    which is the cheapest shape #78 could take -- if even this cannot flip a
    choice, a subtler shape will not either.
    """
    n = len(decisions)
    gate_open = term_active = flips = 0
    for d in decisions:
        if d["since_garbage"] > k:
            continue
        gate_open += 1
        cands = d["cands"]
        if max(c["sh"] for c in cands) <= h:
            continue                      # penalty is identically zero
        term_active += 1
        base_best = max(cands, key=lambda c: c["v"])["a"]
        new_best = max(cands, key=lambda c: c["v"] - dose * max(0, c["sh"] - h))["a"]
        if new_best != base_best:
            flips += 1
    return {"n": n, "gate_open": gate_open, "term_active": term_active,
            "flips": flips,
            "gate_open_pct": 100.0 * gate_open / n if n else 0.0,
            "term_active_pct": 100.0 * term_active / n if n else 0.0,
            "flip_pct": 100.0 * flips / n if n else 0.0}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--corpus", required=True)
    ap.add_argument("--limit", type=int, default=0, help="0 = all games")
    ap.add_argument("--k", type=int, nargs="+", default=[1, 3, 6, 12, 10**6])
    ap.add_argument("--h", type=int, nargs="+", default=[4, 6, 8, 10])
    ap.add_argument("--dose", type=int, nargs="+", default=[10, 40, 160, 640])
    ap.add_argument("--out", required=True)
    a = ap.parse_args()

    games = [json.loads(l) for l in open(a.corpus) if l.strip()]
    if a.limit:
        games = games[:a.limit]
    print(f"[probe] {len(games)} recorded games from {a.corpus}", flush=True)

    model = build_v1_1()
    decisions, diverged = [], []
    for i, g in enumerate(games):
        try:
            d = replay_and_probe(g["seed"], g["actions"], model, level=g.get("level", 11))
        except AssertionError as e:
            diverged.append(str(e))
            continue
        decisions.extend(d)
        if (i + 1) % 10 == 0:
            print(f"  {i + 1}/{len(games)} games, {len(decisions)} decisions",
                  flush=True)

    print(f"[probe] {len(decisions)} decisions; replay divergences: {len(diverged)}")
    for m in diverged[:3]:
        print("   ", m)
    if not decisions:
        sys.exit("no decisions collected")

    rows = []
    print(f"\n{'k':>8} {'h':>3} {'dose':>5} {'gate-open':>10} {'term-act':>10} {'FLIP':>10}")
    print("-" * 52)
    for k in a.k:
        for h in a.h:
            for dose in a.dose:
                r = evaluate(decisions, k, h, dose)
                r.update(k=k, h=h, dose=dose)
                rows.append(r)
                ks = "any" if k >= 10**5 else str(k)
                print(f"{ks:>8} {h:>3} {dose:>5} "
                      f"{r['gate_open_pct']:>9.1f}% {r['term_active_pct']:>9.1f}% "
                      f"{r['flip_pct']:>9.2f}%")

    best = max(rows, key=lambda r: r["flip_pct"])
    print(f"\nBEST FLIP RATE: {best['flip_pct']:.2f}% at k={best['k']} h={best['h']} "
          f"dose={best['dose']} ({best['flips']}/{best['n']} decisions)")
    TESTABLE = 2.0
    if best["flip_pct"] < TESTABLE:
        print(f"VERDICT: NOT TESTABLE. Below the ~{TESTABLE}% flip floor at every "
              f"gate/dose tried, so an n=200-400 arm would return a null that "
              f"cannot be distinguished from 'the term never fired'. Do NOT run "
              f"it; either widen the gate, change the penalty shape, or conclude "
              f"the lever is not a root-only penalty.")
    else:
        print(f"VERDICT: TESTABLE at k={best['k']} h={best['h']} dose={best['dose']} "
              f"-- {best['flip_pct']:.2f}% of decisions change. Use those "
              f"parameters; a null there would be a real null.")

    os.makedirs(os.path.dirname(os.path.abspath(a.out)), exist_ok=True)
    with open(a.out, "w") as f:
        json.dump({"corpus": a.corpus, "n_games": len(games),
                   "n_decisions": len(decisions), "n_diverged": len(diverged),
                   "decider": "StrandedChainD3Decider(chain180, ws20)",
                   "testable_floor_pct": TESTABLE, "rows": rows}, f, indent=2)
    print(f"\nwrote {a.out}")


if __name__ == "__main__":
    main()
