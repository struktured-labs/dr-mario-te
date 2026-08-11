#!/usr/bin/env python3
"""E1--E5 gates for PREREG_EXOGENOUS_PRESSURE.md.

The registered full dose block is seeds 50000..50059.  `--seeds` exists only
for a quick implementation smoke and is stamped NON_REGISTERED when not 60.
"""
from __future__ import annotations

import argparse
import copy
import hashlib
import json
import os
import sys
from concurrent.futures import ProcessPoolExecutor

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import exogenous_pressure as X  # noqa: E402
import oracle_arm as O  # noqa: E402

SEED_START = 50_000
REGISTERED_N = 60
_W = {}


def _sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def blank_board():
    from drmario.faithful_env import FaithfulDrMarioEnv
    e = FaithfulDrMarioEnv(level=0, seed=1, max_pills=10)
    e.reset()
    e.board.color[:] = 0
    e.board.is_virus[:] = False
    e.board.link[:] = 0
    return e.board


def e1(model):
    deterministic = True
    for seed in range(SEED_START, SEED_START + 10):
        for pill in range(25, 80):
            a = X.pressure_offer(model, seed, pill)
            deterministic &= a == X.pressure_offer(model, seed, pill)

    witness = None
    for seed in range(SEED_START, SEED_START + 1000):
        for pill in range(25, 80):
            v = {c: X.coupled_fire_mutant(model, seed, pill, c)
                 for c in (4, 7, 11)}
            if len(set(v.values())) > 1:
                witness = {"seed": seed, "pill": pill, "fires_by_clear": v}
                break
        if witness:
            break
    return {"deterministic_and_receiver_free": bool(deterministic),
            "coupled_clear_mutant_killed": witness is not None,
            "mutant_witness": witness,
            "pass": bool(deterministic and witness is not None)}


def e2(model):
    witness = None
    for seed in range(SEED_START, SEED_START + 5000):
        q = X.pressure_offer(model, seed, 25)
        if q.fires and len(q.columns) >= 2:
            witness = q
            break
    if witness is None:
        return {"pass": False, "error": "no multi-column offer found"}
    c0, c1 = witness.columns[:2]
    clean = blank_board()
    blocked = copy.deepcopy(clean)
    blocked.color[:, c0] = np.resize(np.array([1, 2, 3], dtype=np.int8), 16)
    X.apply_offer(clean, witness)
    X.apply_offer(blocked, witness)
    precommit_ok = np.array_equal(clean.color[:, c1], blocked.color[:, c1])

    mutant_witness = None
    for colour_seed in range(1, 1000):
        a = blank_board()
        b = copy.deepcopy(a)
        b.color[:, c0] = np.resize(np.array([1, 2, 3], dtype=np.int8), 16)
        aa = X.apply_time_colour_mutant(a, witness.n_cells,
                                        witness.columns, colour_seed)
        bb = X.apply_time_colour_mutant(b, witness.n_cells,
                                        witness.columns, colour_seed)
        ac = tuple(x for c, x in aa if c == c1)
        bc = tuple(x for c, x in bb if c == c1)
        if ac != bc:
            mutant_witness = {"colour_seed": colour_seed,
                               "clean_other": ac, "blocked_other": bc}
            break
    ok = precommit_ok and mutant_witness is not None
    return {"offer": {"seed": witness.seed, "pill": witness.pills_placed,
                       "columns": witness.columns, "cells": witness.cells},
            "other_column_unchanged": bool(precommit_ok),
            "apply_time_colour_mutant_killed": mutant_witness is not None,
            "mutant_witness": mutant_witness, "pass": bool(ok)}


def e3(model, C):
    repeats = 0
    wrong_broke = 0
    detail = []
    for seed in range(SEED_START, SEED_START + 3):
        a = O.play_one(seed, O.OracleArm(label_mode="const"), C, model)
        b = O.play_one(seed, O.OracleArm(label_mode="const"), C, model)
        m = O.play_one(seed, O.OracleArm(label_mode="const", order_flip=True),
                       C, model)
        same = (a["_actions"] == b["_actions"] and a["res"] == b["res"]
                and a["pills"] == b["pills"] and a["garbage"] == b["garbage"])
        broke = (a["_actions"] != m["_actions"] or a["res"] != m["res"]
                 or a["pills"] != m["pills"])
        repeats += int(same)
        wrong_broke += int(broke)
        detail.append({"seed": seed, "repeat_identity": same,
                       "wrong_order_broke": broke,
                       "base": f"{a['res']}/{a['pills']}",
                       "wrong": f"{m['res']}/{m['pills']}"})
    ok = repeats == 3 and wrong_broke > 0
    return {"repeat_identity": f"{repeats}/3",
            "wrong_order_mutant_broke": f"{wrong_broke}/3",
            "detail": detail, "pass": bool(ok)}


def e5(model):
    same = all(X.pressure_offer(model, SEED_START, p).digest()
               == X.pressure_offer(model, SEED_START, p).digest()
               for p in range(25, 300))
    mutant_broke = any(
        X.pressure_offer(model, SEED_START, p).digest()
        != X.pressure_offer(model, SEED_START ^ 0xA5A5A5A5, p).digest()
        for p in range(25, 300))
    return {"base_treatment_offer_hashes_match": bool(same),
            "arm_keyed_mutant_killed": bool(mutant_broke),
            "pass": bool(same and mutant_broke)}


def _dose_init(fit):
    if fit:
        os.environ["DR_LULU_FIT"] = fit
    Cc, model = O.init_rig("lulu")
    Ce = dict(Cc)
    Ce["pressure_mode"] = "exogenous"
    _W.update(Cc=Cc, Ce=Ce, model=model)


def _dose_one(seed):
    model = _W["model"]
    rc = O.play_one(seed, O.OracleArm(label_mode="const"), _W["Cc"], model)
    re = O.play_one(seed, O.OracleArm(label_mode="const"), _W["Ce"], model)
    for r in (rc, re):
        r.pop("_actions", None)
    return {"seed": seed, "coupled": rc, "exogenous": re}


def e4(fit, n, workers):
    seeds = list(range(SEED_START, SEED_START + n))
    with ProcessPoolExecutor(max_workers=workers, initializer=_dose_init,
                             initargs=(fit,)) as ex:
        rows = list(ex.map(_dose_one, seeds, chunksize=1))
    eligible_c = sum(max(0, r["coupled"]["pills"] - 24) for r in rows)
    eligible_e = sum(max(0, r["exogenous"]["pills"] - 24) for r in rows)
    landed_c = sum(r["coupled"]["garbage"] for r in rows)
    landed_e = sum(r["exogenous"]["garbage"] for r in rows)
    offers_e = sum(r["exogenous"]["pressure_offers"] for r in rows)
    offered_cells_e = sum(r["exogenous"]["offered_cells"] for r in rows)
    rate_c = landed_c / max(1, eligible_c)
    rate_e = landed_e / max(1, eligible_e)
    ratio = rate_e / max(1e-12, rate_c)
    registered = n == REGISTERED_N
    dose_ok = 0.90 <= ratio <= 1.10
    return {"seed_start": SEED_START, "n": n,
            "authority": "REGISTERED" if registered else "NON_REGISTERED_SMOKE",
            "eligible_plies": {"coupled": eligible_c, "exogenous": eligible_e},
            "landed_cells": {"coupled": landed_c, "exogenous": landed_e},
            "landed_cells_per_eligible_ply": {"coupled": rate_c,
                                                "exogenous": rate_e},
            "exo_offers_per_eligible_ply": offers_e / max(1, eligible_e),
            "exo_offered_cells_per_eligible_ply": (
                offered_cells_e / max(1, eligible_e)),
            "exo_to_coupled_landed_dose_ratio": ratio,
            "dose_band": [0.90, 1.10],
            "dose_valid": bool(dose_ok),
            "pass": bool(registered and dose_ok), "rows": rows}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--fit", default=os.environ.get("DR_LULU_FIT"))
    ap.add_argument("--seeds", type=int, default=REGISTERED_N)
    ap.add_argument("--workers", type=int, default=4)
    ap.add_argument("--out", default=os.path.join(HERE, "out",
                                                   "gate_exogenous_pressure.json"))
    a = ap.parse_args()
    if not a.fit:
        raise SystemExit("--fit or DR_LULU_FIT is required")
    a.fit = os.path.abspath(a.fit)
    os.environ["DR_LULU_FIT"] = a.fit
    C, model = O.init_rig("exo_lulu")

    result = {"prereg": "PREREG_EXOGENOUS_PRESSURE.md @ c3bea64",
              "fit": {"path": a.fit, "sha256": _sha256(a.fit)},
              "E1": e1(model), "E2": e2(model), "E3": e3(model, C),
              "E5": e5(model)}
    result["E4"] = e4(a.fit, a.seeds, a.workers)
    result["ALL_GATES_PASS"] = all(result[f"E{i}"]["pass"]
                                      for i in range(1, 6))
    os.makedirs(os.path.dirname(a.out), exist_ok=True)
    with open(a.out, "w") as f:
        json.dump(result, f, indent=1)
    for i in range(1, 6):
        print(f"E{i}: {'PASS' if result[f'E{i}']['pass'] else 'FAIL'}")
    print("ALL GATES:", "PASS" if result["ALL_GATES_PASS"] else "FAIL")
    print(f"result: {a.out}")
    return 0 if result["ALL_GATES_PASS"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
