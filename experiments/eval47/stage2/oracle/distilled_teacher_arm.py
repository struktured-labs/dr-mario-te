#!/usr/bin/env python3
"""Compact root re-ranker distilled from per-decision oracle choices.

The model is deliberately tiny (two depth-2 trees) and JSON-native.  One tree
decides whether to leave the champion action; the second chooses among champion
ranks 2--4.  The paired ``null`` model has the same training dose but was fit to
an exact-dose shuffled teacher.  Neither arm runs a forward fork.

This is an exploratory candidate, not a shipped policy.  Its historical labels
came from the disclosed, self-coupled ORACLE-CLAIR pilot; endpoint value must be
re-earned on unseen seeds with candidate-independent pressure.
"""
from __future__ import annotations

import json
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
STAGE2 = os.path.dirname(HERE)
EV = os.path.dirname(STAGE2)
QA = os.path.dirname(EV)
for _p in (HERE, STAGE2, EV, QA, os.path.join(EV, "jointdig"),
           os.path.join(EV, "vocab2")):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import feature_battery as FBAT  # noqa: E402
import oracle_arm as O  # noqa: E402
import s2_features as S2F  # noqa: E402

DEFAULT_POLICY = os.path.join(HERE, "oracle_teacher_dt2_v1.json")


def load_policy(path=DEFAULT_POLICY):
    doc = json.load(open(path))
    if doc.get("version") != "oracle-teacher-dt2-v1":
        raise ValueError(f"unknown distilled policy version in {path}")
    for arm in ("true", "null"):
        if doc[arm]["topk"] != O.TOPK:
            raise ValueError("policy top-k differs from runtime")
    return doc


def tree_score(tree, row):
    """Evaluate the frozen sklearn tree without importing sklearn."""
    nodes = tree["nodes"]
    node = 0
    while nodes[node]["feature"] >= 0:
        n = nodes[node]
        node = n["left"] if row[n["feature"]] <= n["threshold"] else n["right"]
    return float(nodes[node]["p1"])


def accepts(score, calibration, seed, ply):
    """Frozen score boundary plus deterministic tie thinning."""
    boundary = float(calibration["boundary_score"])
    if score > boundary:
        return True
    if score < boundary or int(calibration["hash_cutoff_u64"]) < 0:
        return False
    key = (((int(seed) << 32) | int(ply))
           ^ int(calibration["hash_salt"]))
    return O._mix64(key) <= int(calibration["hash_cutoff_u64"])


def decision_features(env, col, vir, cands, cand_vals, nlegal, expand, fl):
    """The exact stage-2 candidate matrix and decision-difference matrix."""
    topk = O.TOPK
    if len(cands) != topk:
        raise ValueError(f"distilled policy requires {topk} candidates")
    cols = np.repeat(np.asarray(col, dtype=np.int8)[None, :], topk, axis=0)
    virs = np.repeat(np.asarray(vir, dtype=np.int8)[None, :], topk, axis=0)
    cura = np.full(topk, int(env.cur.a), dtype=np.int8)
    curb = np.full(topk, int(env.cur.b), dtype=np.int8)
    actions = np.asarray(cands, dtype=np.int64)

    f11 = np.zeros((topk, 11), dtype=np.int64)
    nvir_post = np.zeros(topk, dtype=np.int64)
    posts = np.zeros((topk, 128), dtype=np.int8)
    ok = np.zeros(topk, dtype=np.int8)
    pre11 = np.zeros((topk, 11), dtype=np.int64)
    prenvir = np.zeros(topk, dtype=np.int64)
    expand(cols, virs, cura, curb, actions, fl, f11, nvir_post, posts,
           ok, pre11, prenvir)
    if not np.all(ok == 1):
        raise RuntimeError("champion top-4 unexpectedly contains an illegal action")

    hpost = FBAT.heights_from_boards(posts)
    hpre = FBAT.heights_from_boards(cols)
    cand = FBAT.candidate_features(
        posts, hpost, hpre, np.full(topk, int(nlegal), dtype=np.int32))
    post26 = np.concatenate(
        [f11.astype(np.float64)]
        + [np.asarray(cand[k], dtype=np.float64)[:, None]
           for k in S2F.CAND_NAMES], axis=1)

    occ_pre = np.count_nonzero(cols, axis=1)
    occ_post = np.count_nonzero(posts, axis=1)
    vals = np.asarray(cand_vals, dtype=np.float64)
    gap = np.maximum(0.0, vals[0] - vals)
    rank = np.arange(topk)
    act_var, act_col = actions // 8, actions % 8
    h = O.heights(env.board.color)
    state = np.column_stack([
        np.full(topk, int(env.board.virus_count())),
        np.full(topk, int(h.max())),
        np.full(topk, int(max(h[3], h[4]))),
    ]).astype(np.float64)
    extra = np.column_stack([
        f11 - pre11,
        prenvir - nvir_post,
        occ_pre + 2 - occ_post,
        np.log1p(gap), rank, act_var, act_col, state,
    ]).astype(np.float64)
    extra_names = (["delta_" + x for x in S2F.NAMES11]
                   + ["virus_progress_now", "cells_cleared_now",
                      "log1p_champ_gap", "champ_rank", "action_var",
                      "action_col", "viruses_pre", "maxh_pre",
                      "d_spawn_h_pre"])
    X = np.concatenate([post26, extra], axis=1)
    names = list(S2F.FEAT_NAMES) + extra_names
    blocks = [X[0]] + [X[r] - X[0] for r in range(1, topk)]
    Xd = np.concatenate(blocks)
    decision_names = (["base_" + n for n in names]
                      + [f"rank{r+1}_minus_base_{n}"
                         for r in range(1, topk) for n in names])
    return X, names, Xd, decision_names


class DistilledTeacherArm:
    def __init__(self, bundle, arm="true", provenance=False):
        if arm not in ("true", "null"):
            raise ValueError("arm must be true or null")
        self.bundle = bundle
        self.arm = arm
        self.doc = bundle[arm]
        self.provenance = provenance
        self.expand, _all32, self.fl_expand = S2F.build_expander()
        self._feature_contract_checked = False
        self.stats = {"plies": 0, "gated_plies": 0, "eligible": 0,
                      "flips": 0, "raw_flips": 0,
                      "null_rejected_flips": 0, "forks": 0}
        self.flip_log = []

    def _check_feature_contract(self, names, decision_names):
        if names != self.doc["candidate_feature_names"]:
            raise RuntimeError("candidate feature contract differs from artifact")
        if decision_names != self.doc["decision_feature_names"]:
            raise RuntimeError("decision feature contract differs from artifact")
        self._feature_contract_checked = True

    def choose(self, env, seed, C, bmodel, w, fl, wt, ws, ply):
        from fb import FB
        import root_search as RS

        fb = FB.from_board(env.board)
        col, vir = RS.board_flat_from_fb(fb)
        vals = O._champ_values(col, vir, int(env.cur.a), int(env.cur.b),
                               int(env.nxt.a), int(env.nxt.b), w, fl, wt, ws)
        base = O._champ_action(vals, O.CHAMP_ORDER)
        if base is None:
            return None, None
        self.stats["plies"] += 1
        fires, d_spawn_h, viruses = O.gate_fires(env)
        if not fires:
            return base, base
        self.stats["gated_plies"] += 1

        legal = [int(a) for a in O.CHAMP_ORDER if np.isfinite(vals[int(a)])]
        ranked_i = sorted(range(len(legal)),
                          key=lambda i: (-vals[legal[i]], i))[:O.TOPK]
        cands = [legal[i] for i in ranked_i]
        if len(cands) != O.TOPK:
            return base, base
        cand_vals = [float(vals[a]) for a in cands]
        X, names, Xd, decision_names = decision_features(
            env, col, vir, cands, cand_vals, len(legal), self.expand,
            self.fl_expand)
        if not self._feature_contract_checked:
            self._check_feature_contract(names, decision_names)

        trigger_score = tree_score(self.doc["flip_tree"], Xd)
        if not accepts(trigger_score, self.doc["dose_calibration"], seed, ply):
            return base, base
        self.stats["eligible"] += 1
        alt_scores = [tree_score(self.doc["alternative_tree"], X[r])
                      for r in range(1, O.TOPK)]
        chosen_rank = 1 + int(np.argmax(alt_scores))
        action = cands[chosen_rank]
        self.stats["flips"] += 1
        self.stats["raw_flips"] += 1

        if self.provenance:
            h = O.heights(env.board.color)
            self.flip_log.append({
                "seed": int(seed), "arm": f"distilled_{self.arm}",
                "pressure_mode": C.get("pressure_mode", "coupled"),
                "ply": int(ply), "viruses": int(viruses),
                "maxh": int(h.max()), "d_spawn_h": int(d_spawn_h),
                "base_action": int(base), "trt_action": int(action),
                "champ_rank_chosen": int(chosen_rank),
                "tie": bool(sum(float(vals[a]) == float(vals[base])
                                 for a in legal) > 1),
                "val_gap": round(float(vals[base]) - float(vals[action]), 3),
                "trigger_score": trigger_score,
                "alternative_scores": [float(x) for x in alt_scores],
            })
        return action, base
