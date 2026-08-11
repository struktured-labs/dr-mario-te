#!/usr/bin/env python3
"""Recompute H1..H15 labels at the historical oracle's 489 flip states."""
from __future__ import annotations

import argparse
import collections
import copy
import hashlib
import json
import os
import random
import sys
import time
from concurrent.futures import ProcessPoolExecutor

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

import oracle_arm as O  # noqa: E402

HORIZONS = (1, 2, 3, 5, 8, 12, 15)
DEFAULT_PILOT = ("/home/struktured/projects/dr-mario-oracle-wt/experiments/"
                 "eval47/stage2/oracle/out/pilot_true/seg_030000.jsonl")
_W = {}


def _sha256(path):
    return hashlib.sha256(open(path, "rb").read()).hexdigest()


def _init(fit):
    os.environ["DR_LULU_FIT"] = fit
    C, model = O.init_rig("lulu")
    _W.update(C=C, model=model)


def _best(labels):
    best = 0
    for i in range(1, len(labels)):
        if labels[i] > labels[best]:
            best = i
    return best


def _one(row):
    from fb import FB
    import root_search as RS

    C, model = _W["C"], _W["model"]
    seed = int(row["seed"])
    logs = {int(f["ply"]): f for f in row["trt"].get("flip_log", [])}
    env = O.make_env(seed, C["level"])
    w, fl, wt, ws = C["w"], C["fl"], C["wt"], C["ws"]
    records, errors, consumed, actions = [], [], set(), []
    res, v_at_topout = "stall", None
    rescued = bool((row["base"]["topout"] or row["base"]["stall"])
                   and row["trt"]["res"] == "clear")

    for ply in range(300):
        if env.board.virus_count() == 0:
            res = "clear"
            break
        fb = FB.from_board(env.board)
        col, vir = RS.board_flat_from_fb(fb)
        vals = O._champ_values(col, vir, int(env.cur.a), int(env.cur.b),
                               int(env.nxt.a), int(env.nxt.b), w, fl, wt, ws)
        base = O._champ_action(vals, O.CHAMP_ORDER)
        if base is None:
            break
        legal = [int(a) for a in O.CHAMP_ORDER if np.isfinite(vals[int(a)])]
        ranked_i = sorted(range(len(legal)),
                          key=lambda i: (-vals[legal[i]], i))[:O.TOPK]
        cands = [legal[i] for i in ranked_i]
        f = logs.get(ply)
        action = int(f["trt_action"]) if f else int(base)
        if f:
            consumed.add(ply)
            if int(f["base_action"]) != int(base):
                errors.append(f"ply {ply}: base mismatch")
            if [int(x) for x in f["cands"]] != cands:
                errors.append(f"ply {ply}: candidate mismatch")
            labels = {}
            for horizon in HORIZONS:
                labels[horizon] = [tuple(int(x) for x in O._fork_label(
                    env, candidate, C, seed, model, w, fl, wt, ws, horizon))
                    for candidate in cands]
            teacher_rank = cands.index(action)
            records.append({
                "seed": seed, "ply": ply, "rescued_game": rescued,
                "teacher_rank": teacher_rank,
                "logged_labels": [tuple(int(v) for v in x)
                                  for x in f["labels"]],
                "labels": labels,
            })
        actions.append(action)
        r, v = O._advance(env, action, C, seed, model)
        if r is not None:
            res, v_at_topout = r, v
            break
    if res != row["trt"]["res"] or len(actions) != int(row["trt"]["n_plies"]):
        errors.append(f"endpoint {res}/{len(actions)} != "
                      f"{row['trt']['res']}/{row['trt']['n_plies']}")
    missing = sorted(set(logs) - consumed)
    if missing:
        errors.append(f"missing flip plies {missing}")
    return {"seed": seed, "records": records, "errors": errors}


def replay_errors(records):
    errors = []
    for r in records:
        if r["labels"][15] != r["logged_labels"]:
            errors.append(f"seed {r['seed']} ply {r['ply']}: H15 labels")
        if _best(r["labels"][15]) != int(r["teacher_rank"]):
            errors.append(f"seed {r['seed']} ply {r['ply']}: H15 action")
    return errors


def frozen_null_rank(r):
    return random.Random(((int(r["seed"]) << 16) ^ int(r["ply"])
                          ^ 0x4831354E)).choice((1, 2, 3))


def summarize(records, horizon=None, null=False):
    chosen = []
    for r in records:
        chosen.append(frozen_null_rank(r) if null else _best(r["labels"][horizon]))
    teacher = np.array([r["teacher_rank"] for r in records], dtype=np.int8)
    chosen = np.asarray(chosen, dtype=np.int8)
    h15 = [r["labels"][15] for r in records]
    equivalent, sreg, preg = [], [], []
    for i, r in enumerate(records):
        t, c = int(teacher[i]), int(chosen[i])
        equivalent.append(h15[i][c] == h15[i][t])
        sreg.append(h15[i][t][0] - h15[i][c][0])
        preg.append(h15[i][t][1] - h15[i][c][1])
    rank = collections.Counter(int(x) for x in chosen)
    return {
        "n": len(records),
        "exact_action_agreement": float(np.mean(chosen == teacher)),
        "chooses_champion_no_intervention": float(np.mean(chosen == 0)),
        "h15_label_equivalence": float(np.mean(equivalent)),
        "h15_survival_regret_mean": float(np.mean(sreg)),
        "h15_survival_regret_positive": float(np.mean(np.asarray(sreg) > 0)),
        "h15_progress_regret_mean": float(np.mean(preg)),
        "h15_progress_regret_median": float(np.median(preg)),
        "h15_progress_regret_positive": float(np.mean(np.asarray(preg) > 0)),
        "chosen_rank_1_based": {str(k + 1): rank.get(k, 0)
                                for k in range(O.TOPK)},
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--pilot", default=DEFAULT_PILOT)
    ap.add_argument("--fit", default=os.environ.get("DR_LULU_FIT"))
    ap.add_argument("--workers", type=int, default=4)
    ap.add_argument("--out", default=os.path.join(
        HERE, "out", "oracle_horizon_sensitivity.json"))
    a = ap.parse_args()
    if not a.fit:
        raise SystemExit("--fit or DR_LULU_FIT is required")
    a.pilot, a.fit = os.path.abspath(a.pilot), os.path.abspath(a.fit)
    rows = [json.loads(x) for x in open(a.pilot) if x.strip()]
    t0 = time.monotonic()
    with ProcessPoolExecutor(max_workers=a.workers, initializer=_init,
                             initargs=(a.fit,)) as ex:
        games = list(ex.map(_one, rows, chunksize=1))
    game_errors = [{"seed": g["seed"], "errors": g["errors"]}
                   for g in games if g["errors"]]
    records = [r for g in games for r in g["records"]]
    exact_errors = replay_errors(records)
    if game_errors or exact_errors or len(records) != 489:
        raise SystemExit("REPLAY GATE FAILED: " + json.dumps(
            {"games": game_errors[:3], "exact": exact_errors[:3],
             "records": len(records)}))

    # Demonstrate both exact checks fail on one deliberately wrong field.
    label_mut = copy.deepcopy(records)
    label_mut[0]["logged_labels"][0] = (
        label_mut[0]["logged_labels"][0][0],
        label_mut[0]["logged_labels"][0][1] + 1)
    action_mut = copy.deepcopy(records)
    action_mut[0]["teacher_rank"] = (action_mut[0]["teacher_rank"] % 3) + 1
    mutants = {
        "changed_logged_label_rejected": bool(replay_errors(label_mut)),
        "changed_teacher_action_rejected": bool(replay_errors(action_mut)),
    }
    if not all(mutants.values()):
        raise SystemExit("KILLED MUTANT GATE FAILED")

    rescued = [r for r in records if r["rescued_game"]]
    null_all = summarize(records, null=True)
    null_rescued = summarize(rescued, null=True)
    by_h = {}
    for h in HORIZONS:
        all_m = summarize(records, horizon=h)
        rescue_m = summarize(rescued, horizon=h)
        promising = (h < 12
                     and all_m["exact_action_agreement"]
                     > null_all["exact_action_agreement"]
                     and all_m["h15_label_equivalence"]
                     > null_all["h15_label_equivalence"]
                     and all_m["h15_progress_regret_median"] == 0
                     and rescue_m["exact_action_agreement"]
                     > null_rescued["exact_action_agreement"]
                     and rescue_m["h15_label_equivalence"]
                     > null_rescued["h15_label_equivalence"]
                     and rescue_m["h15_progress_regret_median"] == 0)
        by_h[str(h)] = {"all": all_m, "rescued_games": rescue_m,
                        "mechanistically_promising_below_H12": promising}
    result = {
        "authority": "EXPLORATORY_SEEN_SELF_COUPLED_PILOT",
        "prereg": "PREREG_ORACLE_HORIZON_SENSITIVITY.md",
        "pilot": {"path": a.pilot, "sha256": _sha256(a.pilot),
                  "games": len(rows)},
        "fit": {"path": a.fit, "sha256": _sha256(a.fit)},
        "code": {"path": os.path.abspath(__file__),
                 "sha256": _sha256(os.path.abspath(__file__))},
        "replay_gate": {"games_exact": len(games), "flip_states": len(records),
                        "H15_labels_and_actions_exact": True,
                        "killed_mutants": mutants},
        "rescued_game_flip_states": len(rescued),
        "dose_matched_random_alternative_null": {
            "all": null_all, "rescued_games": null_rescued},
        "horizons": by_h,
        "seconds": round(time.monotonic() - t0, 1),
    }
    os.makedirs(os.path.dirname(a.out), exist_ok=True)
    with open(a.out, "w") as f:
        json.dump(result, f, indent=1)
    print(json.dumps(result, indent=1))
    print(f"wrote {a.out}")


if __name__ == "__main__":
    main()

