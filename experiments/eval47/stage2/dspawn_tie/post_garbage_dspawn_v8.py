#!/usr/bin/env python3
"""Engineering prototype for the exact-v8 post-garbage K4/wq60 arm.

This module is pre-endpoint infrastructure for NEXT_EXACT_REGIME_DESIGN.md.
It deliberately exposes base-trajectory calibration and synthetic gates only;
it does not assign endpoint seeds or verdict rules.
"""
from __future__ import annotations

import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ORACLE = os.path.dirname(HERE) + "/oracle"
for path in (HERE, ORACLE):
    if path not in sys.path:
        sys.path.insert(0, path)

import dspawn_tie_v8 as D  # noqa: E402
import firmware_v8_policy as V8  # noqa: E402
import oracle_arm as O  # noqa: E402

K = 4
WQ = 60
HINGE = 10
PERMUTE_SALT = 0x4B3477513630
THIN_SALT = 0xD1571C7B04AD


def post_root(col, vir, lnk, ca, cb, action):
    """Return the exact linked-fixpoint root state and expansion metadata."""
    c = np.empty(V8.CH.NCELL, dtype=np.int8)
    v = np.empty(V8.CH.NCELL, dtype=np.int8)
    l = np.empty(V8.CH.NCELL, dtype=np.int8)
    mask = np.empty(V8.CH.NCELL, dtype=np.int8)
    action = int(action)
    ok, nv, cells, chain = V8.CH._expand_chain(
        col, vir, lnk, action // 8, action % 8, int(ca), int(cb),
        c, v, l, mask, 0)
    if not ok:
        return None
    return (c.copy(), v.copy(), l.copy(),
            (int(nv), int(cells), int(chain)))


def root_key(root):
    """Collision-free key for the exact state dose used by this experiment."""
    if root is None:
        return None
    col, vir, lnk, meta = root
    return (col.tobytes(), vir.tobytes(), lnk.tobytes(), tuple(meta))


def exact_alias(left, right):
    return root_key(left) == root_key(right)


def root_lane_height(root):
    col = root[0]
    height = 0
    for lane in (3, 4):
        for row in range(16):
            if col[row * 8 + lane] != 0:
                height = max(height, 16 - row)
                break
    return int(height)


def all_roots(col, vir, lnk, ca, cb):
    roots = [None] * 32
    for action in range(32):
        roots[action] = post_root(col, vir, lnk, ca, cb, action)
    return roots


def sensor_and_penalty(roots, wq=WQ, hinge=HINGE):
    sensor = np.full(32, -1, dtype=np.int16)
    penalty = np.full(32, np.nan, dtype=np.float64)
    for action, root in enumerate(roots):
        if root is None:
            continue
        height = root_lane_height(root)
        sensor[action] = height
        penalty[action] = int(wq) * max(0, height - int(hinge))
    return sensor, penalty


def legal_actions(vals):
    return [int(a) for a in V8.CHAMP_ORDER if np.isfinite(vals[int(a)])]


def shuffled_penalty(penalty, vals, seed, ply):
    """Permute the exact legal penalty multiset without its action association."""
    legal = legal_actions(vals)
    out = np.full(32, np.nan, dtype=np.float64)
    destinations = sorted(
        legal,
        key=lambda a: (D.mix64((int(seed) << 32) ^ (int(ply) << 8)
                               ^ int(a) ^ PERMUTE_SALT), a))
    # Sorting the multiset before assigning it is essential: the null may read
    # the magnitudes, but it must not retain their real action association.
    magnitudes = sorted(float(penalty[action]) for action in legal)
    for magnitude, destination in zip(magnitudes, destinations):
        out[destination] = magnitude
    return out


def scored_choice(vals, penalty, tie_seed):
    adjusted = np.asarray(vals, dtype=np.float64) - np.asarray(penalty)
    return V8.choose_from_values(V8.jittered_values(adjusted, tie_seed))


def normalize_alias(base, chosen, roots):
    """Different action IDs with the same exact successor are zero dose."""
    if base is None or chosen is None or int(base) == int(chosen):
        return base if chosen is None else int(chosen)
    return int(base) if exact_alias(roots[int(base)], roots[int(chosen)]) else int(chosen)


def state_distance(left, right):
    """Plane-wise Hamming distance plus expansion-metadata equality."""
    return {
        "color": int(np.count_nonzero(left[0] != right[0])),
        "virus": int(np.count_nonzero(left[1] != right[1])),
        "link": int(np.count_nonzero(left[2] != right[2])),
        "metadata_equal": bool(left[3] == right[3]),
    }


def matching_cell_from_metrics(total_hamming, ply, base_value_gap):
    """Frozen 5 x 2 x 4 null-matching cell from the validated contracts."""
    h = int(total_hamming)
    h_bin = 0 if h <= 4 else 1 if h <= 7 else 2 if h <= 11 else 3 if h <= 19 else 4
    time_bin = int(int(ply) > 70)
    gap = float(base_value_gap)
    gap_bin = 0 if gap <= 10 else 1 if gap <= 30 else 2 if gap <= 60 else 3
    return (h_bin * 2 + time_bin) * 4 + gap_bin


def matching_cell(base, chosen, vals, roots, ply):
    distance = state_distance(roots[int(base)], roots[int(chosen)])
    total = distance["color"] + distance["virus"] + distance["link"]
    gap = float(vals[int(base)] - vals[int(chosen)])
    return matching_cell_from_metrics(total, ply, gap)


def cutoff_accepts(seed, ply, cutoff_u64):
    cutoff = int(cutoff_u64)
    if not 0 <= cutoff <= 1 << 64:
        raise ValueError("invalid uint64 cutoff")
    key = D.mix64((int(seed) << 32) ^ int(ply) ^ THIN_SALT)
    return key < cutoff


class LandedPulseGate:
    """Exactly K subsequent decisions after a placement lands garbage."""

    def __init__(self, k=K):
        if int(k) < 0:
            raise ValueError("k must be nonnegative")
        self.k = int(k)
        self.remaining = 0

    def consume_decision(self):
        active = self.remaining > 0
        if active:
            self.remaining -= 1
        return active

    def note_landed(self, landed):
        if int(landed) > 0:
            self.remaining = self.k


def thin_accepts(seed, ply, keep_num, keep_den):
    keep_num, keep_den = int(keep_num), int(keep_den)
    if keep_den <= 0 or not 0 <= keep_num <= keep_den:
        raise ValueError("invalid thinning fraction")
    key = D.mix64((int(seed) << 32) ^ int(ply) ^ THIN_SALT)
    return key % keep_den < keep_num


class PostGarbageArm:
    """Base, treatment, null, or base-trajectory calibration policy."""

    def __init__(self, mode, keep_num=1, keep_den=1, provenance=False,
                 cell_cutoffs=None):
        if mode not in ("base", "treatment", "null", "calibration"):
            raise ValueError(mode)
        self.mode = mode
        self.keep_num, self.keep_den = int(keep_num), int(keep_den)
        self.cell_cutoffs = (None if cell_cutoffs is None
                             else tuple(int(v) for v in cell_cutoffs))
        if self.cell_cutoffs is not None:
            if len(self.cell_cutoffs) != 40:
                raise ValueError("cell_cutoffs must contain all 40 cells")
            if any(not 0 <= v <= 1 << 64 for v in self.cell_cutoffs):
                raise ValueError("cell cutoff outside uint64 probability range")
        self.provenance = bool(provenance)
        self.gate = LandedPulseGate()
        self.stats = {
            "plies": 0, "active_plies": 0, "landed_pulses": 0,
            "treatment_distinct_flips": 0,
            "null_distinct_opportunities": 0,
            "null_distinct_flips": 0, "raw_action_flips": 0,
            "alias_normalizations": 0,
        }
        self.calibration_log = []
        self.flip_log = []

    def note_advance(self, landed):
        if int(landed) > 0:
            self.stats["landed_pulses"] += 1
        self.gate.note_landed(landed)

    @staticmethod
    def _record(seed, ply, gate_offset, base, chosen, vals, sensor, roots, kind):
        distance = state_distance(roots[int(base)], roots[int(chosen)])
        total_hamming = distance["color"] + distance["virus"] + distance["link"]
        value_gap = float(vals[int(base)] - vals[int(chosen)])
        return {
            "seed": int(seed), "ply": int(ply), "gate_offset": int(gate_offset),
            "kind": kind,
            "base_action": int(base), "chosen_action": int(chosen),
            "base_raw_value": float(vals[int(base)]),
            "chosen_raw_value": float(vals[int(chosen)]),
            "base_value_gap": value_gap,
            "base_sensor": int(sensor[int(base)]),
            "chosen_sensor": int(sensor[int(chosen)]),
            "color_hamming": distance["color"],
            "virus_hamming": distance["virus"],
            "link_hamming": distance["link"],
            "metadata_equal": distance["metadata_equal"],
            "matching_cell": matching_cell_from_metrics(
                total_hamming, ply, value_gap),
            "thin_hash": int(D.mix64((int(seed) << 32) ^ int(ply) ^ THIN_SALT)),
        }

    def choose(self, env, seed, C, bmodel, w, fl, wt, ws, ply):
        del C, bmodel
        if wt != 0 or ws != 20:
            raise ValueError("exact-v8 post-garbage arm requires wt=0, ws=20")
        active = self.gate.consume_decision()
        gate_offset = (self.gate.k - self.gate.remaining - 1) if active else -1
        self.stats["plies"] += 1
        col, vir, lnk = D.board_inputs(env)
        vals = V8.candidate_values(
            col, vir, lnk, int(env.cur.a), int(env.cur.b),
            int(env.nxt.a), int(env.nxt.b), w, fl)
        tie_seed = O.policy_tie_seed(seed, "p2_surrogate")
        base = V8.choose_seeded(vals, tie_seed)
        if active and base is not None:
            self.stats["active_plies"] += 1
        if base is None or not active or self.mode == "base":
            return base

        roots = all_roots(col, vir, lnk, int(env.cur.a), int(env.cur.b))
        if [r is not None for r in roots] != list(np.isfinite(vals)):
            raise RuntimeError("linked roots / exact-v8 legal mask mismatch")
        sensor, penalty = sensor_and_penalty(roots)
        treatment_raw = scored_choice(vals, penalty, tie_seed)
        treatment = normalize_alias(base, treatment_raw, roots)
        null_penalty = shuffled_penalty(penalty, vals, seed, ply)
        null_raw = scored_choice(vals, null_penalty, tie_seed)
        null_candidate = normalize_alias(base, null_raw, roots)

        if treatment_raw != base and treatment == base:
            self.stats["alias_normalizations"] += 1
        if treatment != base:
            self.stats["treatment_distinct_flips"] += 1
            if self.mode == "calibration":
                self.calibration_log.append(self._record(
                    seed, ply, gate_offset, base, treatment, vals, sensor,
                    roots, "treatment"))
        if null_raw != base and null_candidate == base:
            self.stats["alias_normalizations"] += 1
        if null_candidate != base:
            self.stats["null_distinct_opportunities"] += 1
            if self.mode == "calibration":
                self.calibration_log.append(self._record(
                    seed, ply, gate_offset, base, null_candidate, vals, sensor,
                    roots, "null"))

        if self.mode == "calibration":
            return base
        if self.mode == "treatment":
            chosen = treatment
        else:
            accept = False
            if null_candidate != base:
                if self.cell_cutoffs is None:
                    accept = thin_accepts(
                        seed, ply, self.keep_num, self.keep_den)
                else:
                    match_cell = matching_cell(
                        base, null_candidate, vals, roots, ply)
                    accept = cutoff_accepts(
                        seed, ply, self.cell_cutoffs[match_cell])
            chosen = null_candidate if accept else base
            if chosen != base:
                self.stats["null_distinct_flips"] += 1
        if chosen != base:
            self.stats["raw_action_flips"] += 1
            if self.provenance:
                kind = "treatment" if self.mode == "treatment" else "null"
                record = self._record(
                    seed, ply, gate_offset, base, chosen, vals, sensor, roots,
                    kind)
                heights = O.heights(env.board.color)
                jittered = V8.jittered_values(vals, tie_seed)
                legal_rank = sorted(
                    legal_actions(vals),
                    key=lambda action: (
                        -float(jittered[action]),
                        list(V8.CHAMP_ORDER).index(action)))
                record.update({
                    "arm": self.mode,
                    "viruses": int(env.board.virus_count()),
                    "maxh": int(heights.max()),
                    "d_spawn_h": int(max(heights[3], heights[4])),
                    "base_post_d_spawn_h": int(sensor[int(base)]),
                    "chosen_post_d_spawn_h": int(sensor[int(chosen)]),
                    "champ_rank_chosen": legal_rank.index(int(chosen)) + 1,
                })
                self.flip_log.append(record)
        return chosen


def play_one(seed, arm, C, bmodel):
    """Play one game while arming only from garbage that actually landed."""
    import pressure_rig as PR
    env = O.make_env(seed, C["level"])
    result, v_at_topout = "stall", None
    actions = []
    for ply in range(300):
        if env.board.virus_count() == 0:
            result = "clear"
            break
        action = arm.choose(
            env, seed, C, bmodel, C["w"], C["fl"], C["wt"], C["ws"], ply)
        if action is None:
            result = "topout"
            v_at_topout = int(env.board.virus_count())
            break
        actions.append(int(action))
        before = int(env._oracle_garbage)
        out, vir = O._advance(env, action, C, seed, bmodel)
        arm.note_advance(int(env._oracle_garbage) - before)
        if out is not None:
            result, v_at_topout = out, vir
            break
    for row in arm.flip_log:
        row["t_to_end"] = len(actions) - 1 - row["ply"]
        row["res"] = result
    return {
        "seed": int(seed), "res": result, "won": int(result == "clear"),
        "topout": int(result == "topout"), "stall": int(result == "stall"),
        "pills": int(env.pills_placed),
        "dies_ahead": int(result == "topout" and v_at_topout is not None
                          and int(v_at_topout) <= PR.DIES_AHEAD_VIRUS_THRESHOLD),
        "viruses_left": int(v_at_topout) if v_at_topout is not None else -1,
        "n_plies": len(actions), "garbage": int(env._oracle_garbage),
        "_actions": actions,
        "calibration_log": arm.calibration_log, "flip_log": arm.flip_log,
        **{key: int(value) for key, value in arm.stats.items()},
    }
