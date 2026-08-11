#!/usr/bin/env python3
"""Calibrate and run the preregistered exact-v8 d_spawn tie experiment."""
from __future__ import annotations

import argparse
import hashlib
import importlib
import json
import os
import sys
import time
from concurrent.futures import ProcessPoolExecutor

HERE = os.path.dirname(os.path.abspath(__file__))
ORACLE = os.path.dirname(HERE) + "/oracle"
for path in (HERE, ORACLE):
    if path not in sys.path:
        sys.path.insert(0, path)

import dspawn_tie_v8 as D  # noqa: E402
import oracle_arm as O  # noqa: E402

FIT = ("/home/struktured/projects/dr-mario-te/source/experiments/eval47/results/"
       "dr_lulu_20260808_fit.json")
CAL_SEEDS = range(60000, 60240)
EVAL_START, EVAL_COUNT = 61000, 9000
_W = {}


def sha256(path):
    with open(path, "rb") as fh:
        return hashlib.sha256(fh.read()).hexdigest()


def manifest():
    O.init_rig("exo_lulu")
    names = ("dspawn_tie_v8", "firmware_v8_policy", "oracle_arm", "pressure_rig",
             "p0_ab", "bursty_model", "exogenous_pressure", "cascade_chain_x",
             "cascade_link_x", "cascade_stranded_x", "fast_rtl_x", "fast_sim_x",
             "nes_pills", "drmario.faithful_env", "drmario.faithful_game")
    files = {"runner": os.path.abspath(__file__), "fit": FIT}
    for name in names:
        files[name] = os.path.abspath(importlib.import_module(name).__file__)
    docs = {name: {"path": path, "sha256": sha256(path)}
            for name, path in files.items()}
    rolled = hashlib.sha256("".join(
        f"{name}:{doc['sha256']}" for name, doc in sorted(docs.items())).encode()).hexdigest()
    return {"rolled": rolled, "files": docs, "python": sys.version.split()[0]}


def init_worker(keep_num=0, keep_den=1):
    os.environ["DR_LULU_FIT"] = FIT
    C, model = O.init_rig("exo_lulu")
    _W.update(C=C, model=model, keep_num=int(keep_num), keep_den=int(keep_den))


def calibration_work(seed):
    arm = D.TieArm("calibration")
    row = D.play_one(seed, arm, _W["C"], _W["model"])
    row.pop("_actions", None)
    row.pop("flip_log", None)
    return row


def eval_work(seed):
    out = {}
    for name in ("base", "treatment", "null"):
        arm = D.TieArm(name, _W["keep_num"], _W["keep_den"], provenance=True)
        row = D.play_one(seed, arm, _W["C"], _W["model"])
        row.pop("_actions", None)
        out[name] = row
    return {"seed": int(seed), "base": out["base"],
            "treatment": out["treatment"], "null": out["null"]}


def require_gate():
    path = os.path.join(HERE, "out", "gate.json")
    if not os.path.exists(path):
        raise RuntimeError("run gate_dspawn_tie_v8.py first")
    gate = json.load(open(path))
    if not gate.get("pass"):
        raise RuntimeError("prospective gate did not pass")
    return path, sha256(path)


def run_calibration(workers):
    gate_path, gate_sha = require_gate()
    t0 = time.monotonic()
    with ProcessPoolExecutor(max_workers=workers, initializer=init_worker) as ex:
        rows = list(ex.map(calibration_work, CAL_SEEDS))
    plies = sum(r["plies"] for r in rows)
    flips = sum(r["treatment_flips"] for r in rows)
    opp = sum(r["null_opportunities"] for r in rows)
    dose = flips / max(1, plies)
    adequate = flips >= 100 and dose >= 0.0025 and opp >= flips
    den = 1_000_000
    num = min(den, max(0, round(den * flips / max(1, opp))))
    report = {
        "version": "dspawn-tie-v8-calibration-v1",
        "seeds": [min(CAL_SEEDS), max(CAL_SEEDS)], "n_seeds": len(rows),
        "policy_semantics": "firmware_v8/p2_surrogate",
        "pressure": "exo_lulu", "gate_path": gate_path, "gate_sha256": gate_sha,
        "plies": plies, "treatment_flips": flips,
        "null_flip_opportunities": opp, "treatment_dose": dose,
        "null_keep_num": num, "null_keep_den": den,
        "adequacy": {"min_flips": 100, "min_dose": 0.0025, "pass": adequate},
        "per_seed": rows, "seconds": round(time.monotonic() - t0, 2),
        "runtime_manifest": manifest(),
    }
    path = os.path.join(HERE, "out", "calibration.json")
    with open(path, "w") as fh:
        json.dump(report, fh, indent=1)
    print(json.dumps({k: v for k, v in report.items()
                      if k not in ("per_seed", "runtime_manifest")}, indent=1), flush=True)
    return adequate


def load_rows(outdir):
    rows = {}
    if not os.path.isdir(outdir):
        return rows
    for name in sorted(os.listdir(outdir)):
        if not (name.startswith("seg_") and name.endswith(".jsonl")):
            continue
        for line in open(os.path.join(outdir, name)):
            try:
                row = json.loads(line)
                rows.setdefault(int(row["seed"]), row)
            except Exception:
                pass
    return rows


def segment_summary(rows):
    n = len(rows)
    out = {"n_pairs": n}
    if not n:
        return out
    for arm in ("base", "treatment", "null"):
        out[arm] = {
            "clear": sum(r[arm]["won"] for r in rows) / n,
            "topout": sum(r[arm]["topout"] for r in rows) / n,
            "stall": sum(r[arm]["stall"] for r in rows) / n,
            "dies_ahead": sum(r[arm]["dies_ahead"] for r in rows) / n,
            "flips": sum(r[arm]["flips"] for r in rows),
            "plies": sum(r[arm]["plies"] for r in rows),
        }
    return out


def run_evaluation(workers, outdir, segment):
    gate_path, gate_sha = require_gate()
    cal_path = os.path.join(HERE, "out", "calibration.json")
    cal = json.load(open(cal_path))
    if not cal["adequacy"]["pass"]:
        raise RuntimeError("NOT_TESTABLE_LOW_DOSE: calibration failed")
    if cal["gate_sha256"] != gate_sha:
        raise RuntimeError("gate changed after calibration")
    keep_num, keep_den = cal["null_keep_num"], cal["null_keep_den"]
    os.makedirs(outdir, exist_ok=True)
    meta = {
        "version": "dspawn-tie-v8-eval-v1", "prereg_commit": "32bff12",
        "policy_semantics": "firmware_v8/p2_surrogate", "pressure": "exo_lulu",
        "seeds": [EVAL_START, EVAL_START + EVAL_COUNT - 1], "n_seeds": EVAL_COUNT,
        "segment": segment, "null_keep_num": keep_num, "null_keep_den": keep_den,
        "calibration_sha256": sha256(cal_path), "gate_sha256": gate_sha,
        "runtime_manifest": manifest(),
    }
    meta_path = os.path.join(outdir, "META.json")
    if os.path.exists(meta_path):
        if json.load(open(meta_path)) != meta:
            raise RuntimeError("refusing resume under changed META")
    else:
        with open(meta_path, "w") as fh:
            json.dump(meta, fh, indent=1)
    done = load_rows(outdir)
    seeds = list(range(EVAL_START, EVAL_START + EVAL_COUNT))
    todo = [s for s in seeds if s not in done]
    print(f"evaluation seeds={len(seeds)} done={len(done)} todo={len(todo)} "
          f"workers={workers} null_keep={keep_num}/{keep_den} "
          f"manifest={meta['runtime_manifest']['rolled']}", flush=True)
    todo_set = set(todo)
    with ProcessPoolExecutor(max_workers=workers, initializer=init_worker,
                             initargs=(keep_num, keep_den)) as ex:
        for offset in range(0, len(seeds), segment):
            block = [s for s in seeds[offset:offset + segment] if s in todo_set]
            if not block:
                continue
            tag = f"seg_{seeds[offset]:06d}"
            path = os.path.join(outdir, tag + ".jsonl")
            t0 = time.monotonic()
            with open(path, "a") as fh:
                for i, row in enumerate(ex.map(eval_work, block), 1):
                    fh.write(json.dumps(row) + "\n")
                    fh.flush()
                    if i % 25 == 0:
                        elapsed = time.monotonic() - t0
                        print(f"{tag} {i}/{len(block)} {elapsed/60:.1f}min "
                              f"{3*i/max(elapsed, 1e-9):.2f} games/s", flush=True)
            all_rows = load_rows(outdir)
            segrows = [all_rows[s] for s in seeds[offset:offset + segment]
                       if s in all_rows]
            summary = segment_summary(segrows)
            summary["tag"] = tag
            with open(os.path.join(outdir, tag + ".summary.json"), "w") as fh:
                json.dump(summary, fh, indent=1)
            print("SEGMENT " + json.dumps(summary), flush=True)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--phase", choices=("calibrate", "eval"), required=True)
    ap.add_argument("--workers", type=int, default=12)
    ap.add_argument("--segment", type=int, default=250)
    ap.add_argument("--outdir", default=os.path.join(HERE, "out", "evaluation"))
    args = ap.parse_args()
    if not 1 <= args.workers <= 16:
        raise SystemExit("workers must be 1..16")
    os.environ["DR_LULU_FIT"] = FIT
    if args.phase == "calibrate":
        if not run_calibration(args.workers):
            raise SystemExit("NOT_TESTABLE_LOW_DOSE")
    else:
        run_evaluation(args.workers, args.outdir, args.segment)


if __name__ == "__main__":
    main()
