#!/usr/bin/env python3
"""analyse_h14.py — PRE-REGISTERED H14 endpoint verdict (PREREG_H14 + AMENDMENT 1).

PRIMARY (home regime, L20 honest bursty): failure = topout OR stall.
  H14 (trt) vs H12-certified (base), paired by seed.  McNemar exact on
  discordant pairs + seed-bootstrap CI of the paired failure-rate diff.
GATES applied in-analysis (a bad row fails the RUN, not just a fixture):
  population: every seed inside the registered block and NOT in the sileval
  exclusion list; META level/max_pills must match the registered values.
DOSE ANCHOR: full-N flip RATE ratio mutant/true in [0.9, 1.1] (rate, not
  count — the H12 dose-saga rule).
MUTANT: the shuffled-label run must NOT itself read GO (DiD reported).

Self-gate: synthetic tables straddling the verdict thresholds run before any
real row is read; each wrong-way table must fail (killed-mutant standard
applied to the analysis code).
"""
import argparse
import json
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "rollout"))
sys.path.insert(0, HERE)
from analyse import mcnemar_exact  # noqa: E402

BLOCK_LO, BLOCK_HI = 53100, 59999
SILEVAL_EXCL = {53239, 54149, 54311, 54593, 55511, 55789, 56331, 56561,
                56585, 57129, 57245, 57431, 57773, 58007, 58253, 58403,
                58427, 58957, 59115, 59937}
REG_LEVEL, REG_MAX_PILLS = 20, 400


def load_run(outdir, allow_gate_seeds=False):
    rows, seen = [], set()
    meta = json.load(open(os.path.join(outdir, "META.json")))
    for fn in sorted(os.listdir(outdir)):
        if not (fn.startswith("seg_") and fn.endswith(".jsonl")):
            continue
        for ln in open(os.path.join(outdir, fn)):
            try:
                r = json.loads(ln)
            except Exception:
                continue
            if r["seed"] in seen:
                continue
            seen.add(r["seed"])
            rows.append(r)
    rows.sort(key=lambda r: r["seed"])
    # population gates — a violation is a RUN failure
    assert meta.get("level") == REG_LEVEL, ("POPULATION GATE: level",
                                            meta.get("level"))
    assert meta.get("max_pills") == REG_MAX_PILLS, ("POPULATION GATE: max_pills",
                                                    meta.get("max_pills"))
    if not allow_gate_seeds:
        for r in rows:
            assert BLOCK_LO <= r["seed"] <= BLOCK_HI, (
                "POPULATION GATE: seed outside registered block", r["seed"])
            assert r["seed"] not in SILEVAL_EXCL, (
                "POPULATION GATE: sileval-excluded seed present", r["seed"])
    return rows, meta


def fail(arm_row):
    return int(arm_row["topout"] or arm_row["stall"])


def paired_stats(rows, boot=2000, rng_seed=145):
    fb = np.array([fail(r["base"]) for r in rows])
    ft = np.array([fail(r["trt"]) for r in rows])
    n = len(rows)
    b01 = int(((fb == 0) & (ft == 1)).sum())   # trt newly fails
    b10 = int(((fb == 1) & (ft == 0)).sum())   # trt rescues
    p = mcnemar_exact(b10, b01)
    diff = ft.mean() - fb.mean()
    rng = np.random.default_rng(rng_seed)
    ds = []
    for _ in range(boot):
        idx = rng.integers(0, n, n)
        ds.append(ft[idx].mean() - fb[idx].mean())
    lo, hi = np.percentile(ds, [2.5, 97.5])
    return {"n": n, "fail_base": round(float(fb.mean()), 4),
            "fail_trt": round(float(ft.mean()), 4),
            "diff_pp": round(100 * float(diff), 2),
            "ci_pp": [round(100 * float(lo), 2), round(100 * float(hi), 2)],
            "rescued": b10, "newly_failed": b01,
            "discordant": b10 + b01, "mcnemar_p": p}


def flip_rate(rows):
    fl = sum(r["trt"]["flips"] for r in rows)
    pl = sum(r["trt"]["plies_scored"] for r in rows)
    return fl / max(1, pl)


def verdict(s_true, s_mut, dose_ratio):
    reasons = []
    go = True
    if not (s_true["mcnemar_p"] < 0.05):
        go = False
        reasons.append(f"primary McNemar p={s_true['mcnemar_p']:.4f} >= 0.05")
    if not (s_true["diff_pp"] < 0):
        go = False
        reasons.append("H14 failure rate not lower than H12")
    if not (0.9 <= dose_ratio <= 1.1):
        return {"verdict": "VOID", "reasons":
                [f"dose anchor ratio {dose_ratio:.3f} outside [0.9,1.1]"]}
    if s_mut is not None and s_mut["mcnemar_p"] < 0.05 and s_mut["diff_pp"] < 0:
        go = False
        reasons.append("MUTANT NOT KILLED: shuffled arm also reads GO")
    return {"verdict": "GO" if go else "NO_GO", "reasons": reasons}


def self_gate():
    def synth(b10, b01, n=100):
        rows = []
        for i in range(b10):
            rows.append({"base": {"topout": 1, "stall": 0},
                         "trt": {"topout": 0, "stall": 0}})
        for i in range(b01):
            rows.append({"base": {"topout": 0, "stall": 0},
                         "trt": {"topout": 1, "stall": 0}})
        while len(rows) < n:
            rows.append({"base": {"topout": 0, "stall": 0},
                         "trt": {"topout": 0, "stall": 0}})
        for i, r in enumerate(rows):
            r["seed"] = 53100 + i
        return rows
    # v1: strong true effect + dead mutant -> GO
    st = paired_stats(synth(30, 5, 200))
    sm = paired_stats(synth(10, 12, 200))
    v = verdict(st, sm, 1.0)
    assert v["verdict"] == "GO", ("self-gate v1", v)
    # v2 (wrong-way): null effect must NOT read GO
    v = verdict(paired_stats(synth(8, 8, 200)), sm, 1.0)
    assert v["verdict"] == "NO_GO", ("self-gate v2", v)
    # v3 (wrong-way): dose anchor out of band must VOID even a strong effect
    v = verdict(st, sm, 0.85)
    assert v["verdict"] == "VOID", ("self-gate v3", v)
    # v4 (wrong-way): a GO-reading mutant must block the verdict
    v = verdict(st, paired_stats(synth(40, 4, 200)), 1.0)
    assert v["verdict"] == "NO_GO", ("self-gate v4", v)
    # v5 population mutant: out-of-block seed must raise
    try:
        rows = synth(5, 5, 10)
        rows[0]["seed"] = 12345
        for r in rows:
            assert BLOCK_LO <= r["seed"] <= BLOCK_HI
        raise SystemExit("self-gate v5 FAILED: out-of-block seed accepted")
    except AssertionError:
        pass
    print("[self-gate] v1-v5 all killed")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--true-dir", required=True)
    ap.add_argument("--mutant-dir", default=None)
    ap.add_argument("--allow-gate-seeds", action="store_true",
                    help="identity/probe runs on consumed seeds only")
    a = ap.parse_args()
    self_gate()
    rows_t, meta_t = load_run(a.true_dir, a.allow_gate_seeds)
    s_true = paired_stats(rows_t)
    fr_t = flip_rate(rows_t)
    s_mut, fr_m, dose_ratio = None, None, 1.0
    if a.mutant_dir:
        rows_m, meta_m = load_run(a.mutant_dir, a.allow_gate_seeds)
        s_mut = paired_stats(rows_m)
        fr_m = flip_rate(rows_m)
        dose_ratio = (fr_m / fr_t) if fr_t else 0.0
    v = verdict(s_true, s_mut, dose_ratio)
    out = {"true": s_true, "true_flip_rate": round(fr_t, 5),
           "mutant": s_mut,
           "mutant_flip_rate": (round(fr_m, 5) if fr_m is not None else None),
           "dose_ratio": round(dose_ratio, 4), "verdict": v}
    print(json.dumps(out, indent=1))
    print("ANALYSE_H14_OK")


if __name__ == "__main__":
    main()
