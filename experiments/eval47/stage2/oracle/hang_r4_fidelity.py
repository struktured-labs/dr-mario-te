#!/usr/bin/env python3
"""Audit legacy Python hang scoring against the deployed R4 firmware semantics."""
from __future__ import annotations

import argparse
import collections
import copy
import hashlib
import json
import os
import sys
import time
from concurrent.futures import ProcessPoolExecutor

import numpy as np
from numba import njit, int8, int64

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)
REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(HERE))))
COPRO_TESTS = "/home/struktured/projects/dr-mario-mods/tests"

import oracle_arm as O  # noqa: E402

DEFAULT_PILOT = ("/home/struktured/projects/dr-mario-oracle-wt/experiments/"
                 "eval47/stage2/oracle/out/pilot_true/seg_030000.jsonl")


def _sha256(path):
    return hashlib.sha256(open(path, "rb").read()).hexdigest()


@njit(int64(int8[:], int8[:]), cache=True, fastmath=False)
def hang_r4_weighted(col, vir):
    """Firmware R4 hang credit: colour-aware, virus-column-only, depth-weighted."""
    total = int64(0)
    for r in range(15):
        for c in range(8):
            idx = r * 8 + c
            if col[idx] == 0 or vir[idx]:
                continue
            if col[(r + 1) * 8 + c] != 0:
                continue
            rr = r + 2
            while rr < 16 and col[rr * 8 + c] == 0:
                rr += 1
            if rr >= 16 or col[rr * 8 + c] != col[idx]:
                continue
            has_virus = False
            for vr in range(16):
                if vir[vr * 8 + c]:
                    has_virus = True
                    break
            if has_virus:
                total += 40 + 20 * (rr - r - 1)
    return total


def _hang_mutant(col, vir, skip_color=False, skip_virus=False, flat=False):
    total = 0
    for r in range(15):
        for c in range(8):
            idx = r * 8 + c
            if col[idx] == 0 or vir[idx] or col[(r + 1) * 8 + c] != 0:
                continue
            rr = r + 2
            while rr < 16 and col[rr * 8 + c] == 0:
                rr += 1
            if rr >= 16:
                continue
            if not skip_color and col[rr * 8 + c] != col[idx]:
                continue
            if not skip_virus and not any(vir[vr * 8 + c] for vr in range(16)):
                continue
            total += 40 if flat else 40 + 20 * (rr - r - 1)
    return total


def _to_nes(col, vir):
    return [0xFF if int(col[i]) == 0 else
            ((0xD0 if int(vir[i]) else 0x40) | (int(col[i]) - 1))
            for i in range(128)]


def mirror_gate():
    """Cross-check the mirror and prove three relevant wrong versions are rejected."""
    import random
    # Use the copro source tree that actually contains/emits R4. This clone's local
    # nes_d3_golden is explicitly weekend-era and has no R4 flags at all.
    if COPRO_TESTS not in sys.path:
        sys.path.insert(0, COPRO_TESTS)
    import nes_d3_golden as G

    old = (G.W_HANG, G.HANG_DEPTH_PROP, G.W_HANG_GAP, G.HANG_VIRUS_COL_ONLY)
    G.W_HANG = 40
    G.HANG_DEPTH_PROP = True
    G.W_HANG_GAP = 20
    G.HANG_VIRUS_COL_ONLY = True
    try:
        rnd = random.Random(0x5234)
        exact = True
        for _ in range(256):
            col = np.zeros(128, dtype=np.int8)
            vir = np.zeros(128, dtype=np.int8)
            for i in range(128):
                if rnd.random() < 0.42:
                    col[i] = rnd.randint(1, 3)
                    vir[i] = int(rnd.random() < 0.18)
            exact &= int(hang_r4_weighted(col, vir)) == int(G._hang_credit(_to_nes(col, vir)))

        # One fixture per omitted predicate so each mutant is independently killable.
        depth_c = np.zeros(128, dtype=np.int8); depth_v = np.zeros(128, dtype=np.int8)
        depth_c[2 * 8 + 2] = 1; depth_c[6 * 8 + 2] = 1; depth_v[12 * 8 + 2] = 1
        color_c = depth_c.copy(); color_v = depth_v.copy(); color_c[6 * 8 + 2] = 2
        novir_c = depth_c.copy(); novir_v = np.zeros(128, dtype=np.int8)
        truth_depth = int(hang_r4_weighted(depth_c, depth_v))
        truth_color = int(hang_r4_weighted(color_c, color_v))
        truth_novir = int(hang_r4_weighted(novir_c, novir_v))
        mutants = {
            "missing_color_match_rejected": (
                _hang_mutant(color_c, color_v, skip_color=True) != truth_color),
            "missing_virus_column_rejected": (
                _hang_mutant(novir_c, novir_v, skip_virus=True) != truth_novir),
            "flat_depth_rejected": (
                _hang_mutant(depth_c, depth_v, flat=True) != truth_depth),
        }
        return {"random_boards_exact": bool(exact), "random_boards": 256,
                "fixture_truth": {"depth": truth_depth, "color_mismatch": truth_color,
                                  "no_virus_column": truth_novir},
                "killed_mutants": mutants,
                "pass": bool(exact and all(mutants.values()))}
    finally:
        (G.W_HANG, G.HANG_DEPTH_PROP, G.W_HANG_GAP,
         G.HANG_VIRUS_COL_ONLY) = old


def root_value_r4(c1, v1, nv, cells, na, nb, w, fl):
    import fast_rtl_x as FX
    import root_search as RS
    base_without_hang = RS._root_value(c1, v1, nv, cells, na, nb, 8,
                                       FX._W_EXCAV_SHIP, 0, w, fl)
    return float(base_without_hang + int(hang_r4_weighted(c1, v1)))


def champ_values_r4(col, vir, ca, cb, na, nb, w, fl, wt, ws):
    import fast_rtl_x as FX
    import pressure_rig as PR
    from fast_sim_x import NCELL, _expand_core
    from terms47 import g_tower, g_stranded

    vals = np.full(32, np.nan)
    c1 = np.empty(NCELL, dtype=np.int8); v1 = np.empty(NCELL, dtype=np.int8)
    for o4 in range(4):
        var = int(FX._VAR_OF_O4[o4])
        for cc in range(8):
            ok, nv, cells = _expand_core(col, vir, var, cc, ca, cb, c1, v1)
            if ok == 0:
                continue
            val = root_value_r4(c1, v1, nv, cells, na, nb, w, fl)
            if wt:
                val -= wt * g_tower(c1, v1, PR.H0)
            if ws:
                val -= ws * g_stranded(c1, v1)
            vals[var * 8 + cc] = val
    return vals


def rank(vals):
    legal = [int(a) for a in O.CHAMP_ORDER if np.isfinite(vals[int(a)])]
    return sorted(legal, key=lambda a: (-float(vals[a]), legal.index(a)))


def blank_stats():
    return collections.Counter(plies=0, root_action_changed=0, top4_set_changed=0,
                               top4_order_changed=0, historic_action_outside_r4_top4=0)


def add_stats(s, old_rank, new_rank, historic_action=None):
    s["plies"] += 1
    s["root_action_changed"] += old_rank[0] != new_rank[0]
    s["top4_set_changed"] += set(old_rank[:4]) != set(new_rank[:4])
    s["top4_order_changed"] += old_rank[:4] != new_rank[:4]
    if historic_action is not None:
        s["historic_action_outside_r4_top4"] += historic_action not in new_rank[:4]


def finalize(s):
    n = int(s["plies"])
    out = {k: int(v) for k, v in s.items()}
    for k in ("root_action_changed", "top4_set_changed", "top4_order_changed",
              "historic_action_outside_r4_top4"):
        out[k + "_rate"] = float(out[k] / n) if n else 0.0
    return out


def logged_field_errors(f, expected_base, expected_top4):
    errors = []
    if int(f["base_action"]) != int(expected_base):
        errors.append("base mismatch")
    if [int(x) for x in f["cands"]] != [int(x) for x in expected_top4]:
        errors.append("candidate mismatch")
    return errors


def replay(rows, fit):
    from fb import FB
    import root_search as RS

    os.environ["DR_LULU_FIT"] = fit
    C, model = O.init_rig("lulu")
    w, fl, wt, ws = C["w"], C["fl"], C["wt"], C["ws"]
    stats = {"all": blank_stats(), "gated": blank_stats(), "flips": blank_stats()}
    errors, n_flips, abs_deltas = [], 0, []
    for row in rows:
        seed = int(row["seed"])
        logs = {int(f["ply"]): f for f in row["trt"].get("flip_log", [])}
        env = O.make_env(seed, C["level"])
        consumed = set(); actions = []; res = "stall"
        for ply in range(300):
            if env.board.virus_count() == 0:
                res = "clear"; break
            fb = FB.from_board(env.board)
            col, vir = RS.board_flat_from_fb(fb)
            args = (col, vir, int(env.cur.a), int(env.cur.b), int(env.nxt.a),
                    int(env.nxt.b), w, fl, wt, ws)
            old_vals = O._champ_values(*args)
            new_vals = champ_values_r4(*args)
            old_rank, new_rank = rank(old_vals), rank(new_vals)
            if not old_rank:
                break
            f = logs.get(ply)
            historic = int(f["trt_action"]) if f else None
            add_stats(stats["all"], old_rank, new_rank, historic)
            gated, _, _ = O.gate_fires(env)
            if gated:
                add_stats(stats["gated"], old_rank, new_rank, historic)
            if f:
                consumed.add(ply); n_flips += 1
                add_stats(stats["flips"], old_rank, new_rank, historic)
                errors.extend(f"seed {seed} ply {ply}: {e}" for e in
                              logged_field_errors(f, old_rank[0], old_rank[:4]))
            legal = np.isfinite(old_vals)
            abs_deltas.extend(np.abs(new_vals[legal] - old_vals[legal]).tolist())
            action = historic if f else old_rank[0]
            actions.append(action)
            r, _ = O._advance(env, action, C, seed, model)
            if r is not None:
                res = r; break
        if res != row["trt"]["res"] or len(actions) != int(row["trt"]["n_plies"]):
            errors.append(f"seed {seed}: endpoint {res}/{len(actions)} != "
                          f"{row['trt']['res']}/{row['trt']['n_plies']}")
        if set(logs) != consumed:
            errors.append(f"seed {seed}: unconsumed flips {sorted(set(logs) - consumed)}")
    return {"stats": {k: dict(v) for k, v in stats.items()},
            "flip_states": n_flips, "errors": errors,
            "_candidate_value_abs_deltas": abs_deltas}


def replay_chunk(job):
    return replay(*job)


def merge_replays(parts):
    stats = {"all": blank_stats(), "gated": blank_stats(), "flips": blank_stats()}
    errors, n_flips, deltas = [], 0, []
    for part in parts:
        for scope in stats:
            stats[scope].update(part["stats"][scope])
        errors.extend(part["errors"])
        n_flips += int(part["flip_states"])
        deltas.extend(part["_candidate_value_abs_deltas"])
    return {"stats": {k: finalize(v) for k, v in stats.items()},
            "flip_states": n_flips, "errors": errors,
            "candidate_value_abs_delta": {
                "n": len(deltas), "mean": float(np.mean(deltas)),
                "median": float(np.median(deltas)),
                "p95": float(np.percentile(deltas, 95)),
                "max": float(np.max(deltas))}}


def replay_mutants(rows):
    original = next(f for row in rows for f in row["trt"].get("flip_log", []))
    changed_base = copy.deepcopy(original)
    changed_base["base_action"] ^= 1
    changed_cands = copy.deepcopy(original)
    changed_cands["cands"][0] ^= 1
    return original, changed_base, changed_cands


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--pilot", default=DEFAULT_PILOT)
    ap.add_argument("--fit", default=os.environ.get("DR_LULU_FIT"))
    ap.add_argument("--workers", type=int, default=4)
    ap.add_argument("--out", default=os.path.join(HERE, "out", "hang_r4_fidelity.json"))
    a = ap.parse_args()
    if not a.fit:
        raise SystemExit("--fit or DR_LULU_FIT is required")
    a.pilot, a.fit = os.path.abspath(a.pilot), os.path.abspath(a.fit)
    rows = [json.loads(x) for x in open(a.pilot) if x.strip()]
    t0 = time.monotonic()
    mg = mirror_gate()
    if not mg["pass"]:
        raise SystemExit("R4 MIRROR/MUTANT GATE FAILED: " + json.dumps(mg))
    assert 1 <= a.workers <= 12
    chunks = [rows[i::a.workers] for i in range(a.workers)]
    if a.workers == 1:
        parts = [replay(rows, a.fit)]
    else:
        with ProcessPoolExecutor(max_workers=a.workers) as ex:
            parts = list(ex.map(replay_chunk, [(chunk, a.fit) for chunk in chunks]))
    rr = merge_replays(parts)
    if rr["errors"] or rr["flip_states"] != 489:
        raise SystemExit("REPLAY GATE FAILED: " + json.dumps(
            {"errors": rr["errors"][:5], "flip_states": rr["flip_states"]}))

    # The full replay is expensive; demonstrate the validators reject both malformed
    # fields directly on the first logged record after the exact replay passed.
    f0, bad_base, bad_cands = replay_mutants(rows)
    mutants = {
        "changed_logged_base_rejected":
            bool(logged_field_errors(bad_base, f0["base_action"], f0["cands"])),
        "changed_logged_candidates_rejected":
            bool(logged_field_errors(bad_cands, f0["base_action"], f0["cands"])),
    }
    if not all(mutants.values()):
        raise SystemExit("REPLAY MUTANT GATE FAILED")

    all_s, gate_s = rr["stats"]["all"], rr["stats"]["gated"]
    flip_s = rr["stats"]["flips"]
    verdict = {
        "semantic_mismatch": bool(all_s["root_action_changed"] or
                                  all_s["top4_set_changed"]),
        "material_for_policy": all_s["root_action_changed_rate"] >= 0.01,
        "material_for_oracle_eligibility": bool(
            gate_s["top4_set_changed_rate"] >= 0.05 or
            flip_s["historic_action_outside_r4_top4"] > 0),
        "strength_direction_decidable": False,
    }
    result = {
        "authority": "RETROSPECTIVE_IMPLEMENTATION_FIDELITY_ONLY",
        "prereg": "PREREG_HANG_R4_FIDELITY.md",
        "pilot": {"path": a.pilot, "sha256": _sha256(a.pilot), "games": len(rows)},
        "fit": {"path": a.fit, "sha256": _sha256(a.fit)},
        "mirror_gate": mg,
        "replay_gate": {"games_exact": len(rows), "flip_states_exact": 489,
                        "killed_mutants": mutants},
        **rr, "verdict": verdict, "seconds": round(time.monotonic() - t0, 1),
    }
    os.makedirs(os.path.dirname(a.out), exist_ok=True)
    with open(a.out, "w") as f:
        json.dump(result, f, indent=1)
    print(json.dumps(result, indent=1))
    print(f"wrote {a.out}")


if __name__ == "__main__":
    main()
