#!/usr/bin/env python3
"""G1g — FORK LEAKAGE GATE.  Do the forks mutate the live game?

WHY THIS EXISTS, AND WHY G1a DOES NOT COVER IT.
-----------------------------------------------
The OFF-identity gate G1a runs `label_mode="const"`, which short-circuits before
`_fork_label` is ever called:

    if self.label_mode == "const":
        labels.append((1, 0))          # <-- no fork is run
    else:
        labels.append(_fork_label(...))

So G1a proves "the SELECTION rule is a no-op when labels are equal". It proves
NOTHING about whether running the forks perturbs the live environment. If a fork
mutated the parent's board, the parent's capsule cursor, or the parent's
`pills_placed`, the oracle would effectively be granted free practice moves and
the arm's headline effect would be an artifact — and every gate in the sealed
prereg would still have passed.

THE GATE.  `ForkedConstArm` computes the REAL forks — same gate, same top-4, same
15-pill rollouts, same cost — and then **throws the labels away** and plays the
champion's action anyway. If forks are side-effect free, this must reproduce the
base arm EXACTLY: same result, same pill count, same dies-ahead, and the same
per-ply action sequence.

    forks run + selection forced to champion  ==  champion, byte for byte

ITS OWN KILLED MUTANT.  `LeakyConstArm` deliberately forks on the LIVE env
instead of a clone (one line: `copy.deepcopy(env)` -> `env`). That is precisely
the defect being screened for, and it MUST break the gate. A gate that has not
been shown to fail on the defect it screens for is not a gate.

This file imports `oracle_arm` and subclasses it; it does not modify it, so it is
safe to add while a run is in flight.
"""
import argparse
import copy
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import numpy as np  # noqa: E402

import oracle_arm as O  # noqa: E402


class ForkedConstArm(O.OracleArm):
    """Runs the real forks, then discards them and plays the champion."""

    def __init__(self, **kw):
        super().__init__(label_mode="true", **kw)
        self.forks_run = 0

    def choose(self, env, seed, C, bmodel, w, fl, wt, ws, ply):
        from fb import FB
        import root_search as RS

        fb = FB.from_board(env.board)
        col, vir = RS.board_flat_from_fb(fb)
        vals = O._champ_values(col, vir, int(env.cur.a), int(env.cur.b),
                               int(env.nxt.a), int(env.nxt.b), w, fl, wt, ws)
        base_a = O._champ_action(vals, O.CHAMP_ORDER)
        if base_a is None:
            return None, None
        self.stats["plies"] += 1
        fires, _d, _v = O.gate_fires(env)
        if not fires:
            return base_a, base_a
        self.stats["gated_plies"] += 1
        legal = [int(s) for s in O.CHAMP_ORDER if np.isfinite(vals[int(s)])]
        ranked = sorted(range(len(legal)),
                        key=lambda i: (-vals[legal[i]], i))[:self.topk]
        for a in (legal[i] for i in ranked):
            self._fork(env, a, C, seed, bmodel, w, fl, wt, ws)
            self.forks_run += 1
        return base_a, base_a          # labels DISCARDED on purpose

    def _fork(self, env, a, C, seed, bmodel, w, fl, wt, ws):
        return O._fork_label(env, a, C, seed, bmodel, w, fl, wt, ws,
                             self.horizon)


class LeakyConstArm(ForkedConstArm):
    """KILLED MUTANT: forks on the LIVE env instead of a clone."""

    def _fork(self, env, a, C, seed, bmodel, w, fl, wt, ws):
        import root_search as RS
        from fb import FB
        e = env                                   # <-- THE DEFECT
        v0 = int(e.board.virus_count())
        res, v_end = O._advance(e, a, C, seed, bmodel)
        n = 1
        while res is None and n < self.horizon:
            if e.board.virus_count() == 0:
                break
            fb = FB.from_board(e.board)
            col, vir = RS.board_flat_from_fb(fb)
            vals = O._champ_values(col, vir, int(e.cur.a), int(e.cur.b),
                                   int(e.nxt.a), int(e.nxt.b), w, fl, wt, ws)
            act = O._champ_action(vals, O.CHAMP_ORDER)
            if act is None:
                break
            res, v_end = O._advance(e, act, C, seed, bmodel)
            n += 1
        return (1, v0)


def run(seed, arm, C, bmodel):
    r = O.play_one(seed, arm, C, bmodel)
    return r, r["_actions"]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--seeds", type=int, default=6)
    ap.add_argument("--seed-start", type=int, default=41000)
    ap.add_argument("--model", default="lulu", choices=["lulu", "drip"])
    ap.add_argument("--out", default=os.path.join(HERE, "out",
                                                  "gate_forkleak.json"))
    a = ap.parse_args()

    C, bmodel = O.init_rig(a.model)
    seeds = list(range(a.seed_start, a.seed_start + a.seeds))
    res = {"model": a.model, "seeds": seeds, "per_seed": []}

    clean_ok = leak_broke = 0
    for s in seeds:
        base = O.OracleArm(label_mode="const")
        rb, ab = run(s, base, C, bmodel)

        fk = ForkedConstArm()
        rf, af = run(s, fk, C, bmodel)
        same = (rf["won"] == rb["won"] and rf["topout"] == rb["topout"]
                and rf["stall"] == rb["stall"] and rf["pills"] == rb["pills"]
                and rf["dies_ahead"] == rb["dies_ahead"] and af == ab)
        clean_ok += bool(same)

        lk = LeakyConstArm()
        rl, al = run(s, lk, C, bmodel)
        broke = not (rl["won"] == rb["won"] and rl["pills"] == rb["pills"]
                     and al == ab)
        leak_broke += bool(broke)

        row = {"seed": s, "base": f"{rb['res']}/{rb['pills']}",
               "forked_const": f"{rf['res']}/{rf['pills']}",
               "leaky": f"{rl['res']}/{rl['pills']}",
               "forks_run": fk.forks_run,
               "clean_matches_base": bool(same),
               "leaky_breaks_base": bool(broke)}
        res["per_seed"].append(row)
        print(f"  seed {s}: base {row['base']:>12s} | forks-run-then-discard "
              f"{row['forked_const']:>12s} match={same} (forks={fk.forks_run}) "
              f"| LEAKY MUTANT {row['leaky']:>12s} broke={broke}", flush=True)

    ok = (clean_ok == len(seeds)) and (leak_broke >= len(seeds) - 1)
    res["G1g_forks_are_side_effect_free"] = f"{clean_ok}/{len(seeds)}"
    res["G1g_mutant_leaky_fork_MUST_break"] = f"{leak_broke}/{len(seeds)}"
    res["ALL_GATES_PASS"] = bool(ok)
    os.makedirs(os.path.dirname(a.out), exist_ok=True)
    json.dump(res, open(a.out, "w"), indent=1)
    print(f"\nG1g forks side-effect free : {clean_ok}/{len(seeds)} (must be all)")
    print(f"G1g MUTANT leaky fork broke: {leak_broke}/{len(seeds)} (must break)")
    print("G1g", "PASS" if ok else "FAIL")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
