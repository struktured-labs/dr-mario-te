#!/usr/bin/env python3
"""Frozen census from PREREG_POLICY_SEMANTICS_CENSUS.md."""
from __future__ import annotations

import argparse
import json
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)
import firmware_r4_policy as CAP1  # noqa: E402
import firmware_v8_policy as V8  # noqa: E402
import oracle_arm as O  # noqa: E402

SEEDS = range(30640, 30680)
FIT = ("/home/struktured/projects/dr-mario-te/source/experiments/eval47/results/"
       "dr_lulu_20260808_fit.json")
MUTANTS = ("cap1_r4", "flat_hang", "zero_link", "full_child_eh", "linked_replay_eh")
DIFFS = ("hist_vs_actual_seed0", "hist_vs_actual_rep", "actual_seed0_vs_rep",
         "actual_vs_cap1_r4", "actual_vs_flat_hang", "actual_vs_zero_link",
         "actual_vs_full_child_eh", "actual_vs_linked_replay_eh")


def match_seed(game_seed):
    return ((((73 * int(game_seed) + 41) & 255) | 1) ^ 0xA4)


def rank(vals, tie_seed=0):
    scored = V8.jittered_values(vals, tie_seed)
    legal = [int(a) for a in O.CHAMP_ORDER if np.isfinite(scored[int(a)])]
    return sorted(legal, key=lambda a: (-float(scored[a]), legal.index(a)))


def differs(a, b):
    return not np.array_equal(np.nan_to_num(a, nan=999999.0),
                              np.nan_to_num(b, nan=999999.0))


def fresh_scope():
    return {"states": 0, "action_disagreements": {name: 0 for name in DIFFS},
            "top4_set_hist_vs_actual_seed0": 0,
            "top4_order_hist_vs_actual_seed0": 0,
            "top4_set_hist_vs_actual_rep": 0,
            "top4_order_hist_vs_actual_rep": 0,
            "actual_action_outside_historical_top4": 0,
            "historical_action_outside_actual_top4": 0,
            "historical_rank_of_actual_sum": 0,
            "historical_rank_of_actual_gt4": 0,
            "tie_seed_any_change": 0,
            "tie_seed_distinct_actions_sum": 0,
            "tie_seed_changed_draws": 0,
            "tie_seed_total_draws": 0}


def update(scope, hist, actual, vals, ts, choices):
    scope["states"] += 1
    for name, (left, right) in choices.items():
        scope["action_disagreements"][name] += int(left != right)
    hr = rank(hist, 0)
    ar0 = rank(actual, 0)
    arr = rank(actual, ts)
    h4, a40, a4r = hr[:4], ar0[:4], arr[:4]
    scope["top4_set_hist_vs_actual_seed0"] += int(set(h4) != set(a40))
    scope["top4_order_hist_vs_actual_seed0"] += int(h4 != a40)
    scope["top4_set_hist_vs_actual_rep"] += int(set(h4) != set(a4r))
    scope["top4_order_hist_vs_actual_rep"] += int(h4 != a4r)
    scope["actual_action_outside_historical_top4"] += int(choices["hist_vs_actual_rep"][1] not in h4)
    scope["historical_action_outside_actual_top4"] += int(choices["hist_vs_actual_rep"][0] not in a4r)
    hist_rank = hr.index(choices["hist_vs_actual_rep"][1]) + 1
    scope["historical_rank_of_actual_sum"] += hist_rank
    scope["historical_rank_of_actual_gt4"] += int(hist_rank > 4)
    a0 = choices["actual_seed0_vs_rep"][0]
    seed_actions = [V8.choose_seeded(actual, seed) for seed in range(1, 256)]
    changed = sum(a != a0 for a in seed_actions)
    distinct = len(set(seed_actions + [a0]))
    scope["tie_seed_any_change"] += int(changed > 0)
    scope["tie_seed_distinct_actions_sum"] += distinct
    scope["tie_seed_changed_draws"] += changed
    scope["tie_seed_total_draws"] += 255


def finalize(scope):
    n = scope["states"]
    out = dict(scope)
    out["rates"] = {name: count / n for name, count in scope["action_disagreements"].items()}
    for key in ("top4_set_hist_vs_actual_seed0", "top4_order_hist_vs_actual_seed0",
                "top4_set_hist_vs_actual_rep", "top4_order_hist_vs_actual_rep",
                "actual_action_outside_historical_top4",
                "historical_action_outside_actual_top4", "historical_rank_of_actual_gt4",
                "tie_seed_any_change"):
        out["rates"][key] = scope[key] / n
    out["mean_historical_rank_of_actual"] = scope["historical_rank_of_actual_sum"] / n
    out["mean_distinct_actions_across_tie_seeds"] = scope["tie_seed_distinct_actions_sum"] / n
    out["tie_seed_changed_draw_rate"] = (scope["tie_seed_changed_draws"]
                                          / scope["tie_seed_total_draws"])
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--json-out", default="")
    args = ap.parse_args()
    os.environ["DR_LULU_FIT"] = FIT
    config, model = O.init_rig("lulu")
    w, fl, wt, ws = config["w"], config["fl"], config["wt"], config["ws"]
    assert (wt, ws) == (0, 20)

    tie_test = np.full(32, np.nan)
    tie_test[O.CHAMP_ORDER[0]] = tie_test[O.CHAMP_ORDER[1]] = 0
    assert O._champ_action(tie_test, O.CHAMP_ORDER) != O._champ_action(tie_test, O.CHAMP_ORDER[::-1])

    scopes = {"all": fresh_scope(), "gated": fresh_scope()}
    exercised = {name: False for name in MUTANTS}
    outcomes = {"clear": 0, "topout": 0, "stall": 0, "other": 0}
    games = []
    from fb import FB
    import root_search as RS

    for game_seed in SEEDS:
        env = O.make_env(game_seed, config["level"])
        ts = match_seed(game_seed)
        result = None
        plies = 0
        while result is None and plies < 300:
            fb = FB.from_board(env.board)
            col, vir = RS.board_flat_from_fb(fb)
            lnk = np.ascontiguousarray(env.board.link, dtype=np.int8).reshape(-1)
            ca, cb, na, nb = map(int, (env.cur.a, env.cur.b, env.nxt.a, env.nxt.b))
            hist = O._champ_values(col, vir, ca, cb, na, nb, w, fl, wt, ws)
            actual = V8.candidate_values(col, vir, lnk, ca, cb, na, nb, w, fl)
            cap1 = CAP1.candidate_values(col, vir, ca, cb, na, nb, w, fl, wt=wt, ws=ws)
            flat = V8.candidate_values(col, vir, lnk, ca, cb, na, nb, w, fl, r4=False)
            nolink = V8.candidate_values(col, vir, np.zeros(128, np.int8),
                                         ca, cb, na, nb, w, fl)
            full_eh = V8.candidate_values(col, vir, lnk, ca, cb, na, nb, w, fl,
                                          full_child_eh=True)
            linked_eh = V8.candidate_values(col, vir, lnk, ca, cb, na, nb, w, fl,
                                            linked_replay_eh=True)
            vectors = {"cap1_r4": cap1, "flat_hang": flat, "zero_link": nolink,
                       "full_child_eh": full_eh, "linked_replay_eh": linked_eh}
            legal = np.isfinite(actual)
            assert np.array_equal(np.isfinite(hist), legal)
            for vec in vectors.values():
                assert np.array_equal(np.isfinite(vec), legal)
            for name, vec in vectors.items():
                exercised[name] |= differs(actual, vec)

            ha = O._champ_action(hist, O.CHAMP_ORDER)
            a0 = V8.choose_from_values(actual)
            ar = V8.choose_seeded(actual, ts)
            assert a0 == V8.choose_seeded(actual, 0)
            mutant_actions = {name: V8.choose_seeded(vec, ts) for name, vec in vectors.items()}
            choices = {"hist_vs_actual_seed0": (ha, a0),
                       "hist_vs_actual_rep": (ha, ar),
                       "actual_seed0_vs_rep": (a0, ar)}
            for name, action in mutant_actions.items():
                choices["actual_vs_" + name] = (ar, action)
            update(scopes["all"], hist, actual, vectors, ts, choices)
            fires, _dh, _vr = O.gate_fires(env)
            if fires:
                update(scopes["gated"], hist, actual, vectors, ts, choices)
            if ar is None:
                result = "topout"
                break
            result, _v = O._advance(env, ar, config, game_seed, model)
            plies += 1
        final = result or "other"
        outcomes[final if final in outcomes else "other"] += 1
        games.append({"seed": game_seed, "tie_seed": ts, "plies": plies, "result": final})
        print(f"seed={game_seed} plies={plies} result={final}", flush=True)

    report = {"version": "policy-semantics-census-v1", "seeds": [min(SEEDS), max(SEEDS)],
              "games": len(games), "outcomes": outcomes, "per_game": games,
              "mutants_exercised": exercised,
              "checks": {"legal_masks_exact": True, "seed0_selector_exact": True,
                         "representative_selector_exact": True,
                         "reverse_tie_mutant_killed": True,
                         "all_mutants_exercised": all(exercised.values())},
              "all": finalize(scopes["all"]), "gated": finalize(scopes["gated"])}
    print(json.dumps(report, indent=1))
    if args.json_out:
        with open(args.json_out, "w") as out:
            json.dump(report, out, indent=1)
    if not all(exercised.values()):
        raise SystemExit("one or more semantic mutants not exercised")


if __name__ == "__main__":
    main()
