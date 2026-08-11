#!/usr/bin/env python3
"""Exact-v8 d_spawn_h tie resolver and its label-blind null."""
from __future__ import annotations

import os
import sys

import numpy as np
from numba import njit

HERE = os.path.dirname(os.path.abspath(__file__))
ORACLE = os.path.dirname(HERE) + "/oracle"
if ORACLE not in sys.path:
    sys.path.insert(0, ORACLE)

import firmware_v8_policy as V8  # noqa: E402
import oracle_arm as O  # noqa: E402

CHAMP_ORDER = V8.CHAMP_ORDER


@njit(cache=True, fastmath=False)
def _post_dspawn_linked(pcol, pvir, plnk, ca, cb):
    """Lane height after each legal root under v8's linked fixpoint physics."""
    out = np.full(32, -1, dtype=np.int16)
    c1 = np.empty(V8.CH.NCELL, dtype=np.int8)
    v1 = np.empty(V8.CH.NCELL, dtype=np.int8)
    l1 = np.empty(V8.CH.NCELL, dtype=np.int8)
    mask = np.empty(V8.CH.NCELL, dtype=np.int8)
    for o4 in range(4):
        var = V8.FX._VAR_OF_O4[o4]
        for col in range(8):
            ok, _nv, _cells, _chain = V8.CH._expand_chain(
                pcol, pvir, plnk, var, col, ca, cb, c1, v1, l1, mask, 0)
            if ok == 0:
                continue
            height = 0
            for lane in (3, 4):
                for row in range(16):
                    if c1[row * 8 + lane] != 0:
                        h = 16 - row
                        if h > height:
                            height = h
                        break
            out[var * 8 + col] = height
    return out


def post_dspawn_linked(col, vir, lnk, ca, cb):
    return _post_dspawn_linked(
        np.ascontiguousarray(col, dtype=np.int8),
        np.ascontiguousarray(vir, dtype=np.int8),
        np.ascontiguousarray(lnk, dtype=np.int8), int(ca), int(cb))


def raw_top_set(vals, gap=0):
    """Champion-ordered actions within `gap` of the raw maximum."""
    vals = np.asarray(vals)
    if not np.isfinite(vals).any():
        return []
    best = float(np.nanmax(vals))
    return [int(a) for a in CHAMP_ORDER
            if np.isfinite(vals[int(a)]) and best - float(vals[int(a)]) <= gap]


def treatment_choice(vals, sensor, base_action, *, gap_mutant=False):
    """Resolve only an exact raw-value tie using strictly lower lane height."""
    if base_action is None:
        return None
    tied = raw_top_set(vals, gap=1 if gap_mutant else 0)
    base = int(base_action)
    if len(tied) < 2 or base not in tied:
        return base
    best_h = min(int(sensor[a]) for a in tied)
    if best_h >= int(sensor[base]):
        return base
    # CHAMP_ORDER is already the final deterministic fallback.
    return next(a for a in tied if int(sensor[a]) == best_h)


def mix64(x):
    x = int(x) & ((1 << 64) - 1)
    x ^= x >> 30
    x = (x * 0xBF58476D1CE4E5B9) & ((1 << 64) - 1)
    x ^= x >> 27
    x = (x * 0x94D049BB133111EB) & ((1 << 64) - 1)
    return (x ^ (x >> 31)) & ((1 << 64) - 1)


def null_alternative(vals, base_action, seed, ply):
    """Label-blind candidate from the exact raw tie set, or the base."""
    if base_action is None:
        return None
    base = int(base_action)
    tied = raw_top_set(vals)
    alternatives = [a for a in tied if a != base]
    if base not in tied or not alternatives:
        return base
    key = mix64((int(seed) << 32) ^ int(ply) ^ 0xD5A9A11E)
    return alternatives[key % len(alternatives)]


def null_choice(vals, base_action, seed, ply, keep_num, keep_den):
    alt = null_alternative(vals, base_action, seed, ply)
    if alt == base_action:
        return base_action
    key = mix64((int(seed) << 32) ^ int(ply) ^ 0x9E3779B97F4A7C15)
    return alt if key % int(keep_den) < int(keep_num) else base_action


def board_inputs(env):
    from fb import FB
    import root_search as RS
    fb = FB.from_board(env.board)
    col, vir = RS.board_flat_from_fb(fb)
    lnk = np.ascontiguousarray(env.board.link, dtype=np.int8).reshape(-1)
    return col, vir, lnk


class TieArm:
    """Mode is base, treatment, null, or calibration (base trajectory)."""

    def __init__(self, mode, keep_num=0, keep_den=1, provenance=False):
        if mode not in ("base", "treatment", "null", "calibration"):
            raise ValueError(mode)
        self.mode = mode
        self.keep_num, self.keep_den = int(keep_num), int(keep_den)
        self.provenance = bool(provenance)
        self.stats = {"plies": 0, "raw_tie_plies": 0, "treatment_flips": 0,
                      "null_opportunities": 0, "flips": 0}
        self.flip_log = []

    def choose(self, env, seed, C, bmodel, w, fl, wt, ws, ply):
        del C, bmodel
        if wt != 0 or ws != 20:
            raise ValueError("exact-v8 tie arm requires wt=0, ws=20")
        col, vir, lnk = board_inputs(env)
        vals = V8.candidate_values(col, vir, lnk, int(env.cur.a), int(env.cur.b),
                                   int(env.nxt.a), int(env.nxt.b), w, fl)
        tie_seed = O.policy_tie_seed(seed, "p2_surrogate")
        ranked_vals = V8.jittered_values(vals, tie_seed)
        base = V8.choose_from_values(ranked_vals)
        self.stats["plies"] += 1
        if base is None or self.mode == "base":
            return base

        tied = raw_top_set(vals)
        if len(tied) >= 2 and base in tied:
            self.stats["raw_tie_plies"] += 1
        null_alt = null_alternative(vals, base, seed, ply)
        if null_alt != base:
            self.stats["null_opportunities"] += 1

        sensor = None
        trt = base
        if self.mode in ("treatment", "calibration"):
            sensor = post_dspawn_linked(col, vir, lnk, int(env.cur.a), int(env.cur.b))
            if not np.array_equal(sensor >= 0, np.isfinite(vals)):
                raise RuntimeError("linked sensor / exact-v8 legal mask mismatch")
            trt = treatment_choice(vals, sensor, base)
            if trt != base:
                self.stats["treatment_flips"] += 1

        if self.mode == "calibration":
            return base
        if self.mode == "treatment":
            chosen = trt
        else:
            chosen = null_choice(vals, base, seed, ply,
                                 self.keep_num, self.keep_den)
        if chosen != base:
            self.stats["flips"] += 1
            if self.provenance:
                if sensor is None:
                    sensor = post_dspawn_linked(
                        col, vir, lnk, int(env.cur.a), int(env.cur.b))
                h = O.heights(env.board.color)
                legal_rank = sorted(
                    [int(a) for a in CHAMP_ORDER if np.isfinite(ranked_vals[int(a)])],
                    key=lambda a: (-float(ranked_vals[a]),
                                   list(CHAMP_ORDER).index(a)))
                self.flip_log.append({
                    "seed": int(seed), "arm": self.mode, "ply": int(ply),
                    "viruses": int(env.board.virus_count()),
                    "maxh": int(h.max()), "d_spawn_h": int(max(h[3], h[4])),
                    "raw_tie_size": len(tied), "base_action": int(base),
                    "treatment_action": int(chosen),
                    "base_post_d_spawn_h": int(sensor[base]),
                    "chosen_post_d_spawn_h": int(sensor[chosen]),
                    "champ_rank_chosen": legal_rank.index(int(chosen)) + 1,
                })
        return chosen


def play_one(seed, arm, C, bmodel):
    import pressure_rig as PR
    env = O.make_env(seed, C["level"])
    w, fl, wt, ws = C["w"], C["fl"], C["wt"], C["ws"]
    result, v_at_topout = "stall", None
    actions = []
    for ply in range(300):
        if env.board.virus_count() == 0:
            result = "clear"
            break
        action = arm.choose(env, seed, C, bmodel, w, fl, wt, ws, ply)
        if action is None:
            result = "topout"
            v_at_topout = int(env.board.virus_count())
            break
        actions.append(int(action))
        out, vir = O._advance(env, action, C, seed, bmodel)
        if out is not None:
            result, v_at_topout = out, vir
            break
    n_plies = len(actions)
    for row in arm.flip_log:
        row["t_to_end"] = n_plies - 1 - row["ply"]
        row["res"] = result
    return {
        "seed": int(seed), "res": result, "won": int(result == "clear"),
        "topout": int(result == "topout"), "stall": int(result == "stall"),
        "pills": int(env.pills_placed),
        "dies_ahead": int(result == "topout" and v_at_topout is not None
                           and int(v_at_topout) <= PR.DIES_AHEAD_VIRUS_THRESHOLD),
        "viruses_left": int(v_at_topout) if v_at_topout is not None else -1,
        "n_plies": n_plies, "garbage": int(env._oracle_garbage),
        **{key: int(value) for key, value in arm.stats.items()},
        "flip_log": arm.flip_log,
        "_actions": actions,
    }
