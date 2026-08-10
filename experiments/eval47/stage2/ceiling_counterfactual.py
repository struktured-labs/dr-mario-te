#!/usr/bin/env python3
"""L7 COUNTERFACTUAL WITHIN-DECISION TEST, with the PROGRESS GATE recon C's N3 demands.

recon C: naive survival rescue 0.972 collapses to 0.556 once virus progress is required.
A "rescue" that survives by declining to clear is NOT a rescue -- and this rig makes that
exploit free, because the opponent's volley is gated on `clear_size > 0`
(pressure_rig.py:241), so a fork that never clears is garbage-IMMUNE. The fork file
records `viruses_at_end` (ve) and `cleared` (cl) per action precisely so the gate can be
applied without a re-run.

THREE survival definitions, all reported (the middle one is the one that counts):
  RAW      out in {clear, alive, budget}
  PROGRESS RAW and ve < vir0            (viruses actually went down)
  CLEARING RAW and cl >= 1              (at least one clearing ply happened)

ENDPOINT: within-decision AUC of "this action survives" against each ranker, over plies
where the label is DISCRIMINATIVE (>=1 survivor and >=1 non-survivor), with a seed-
clustered bootstrap on paired differences. Join validated against the corpus's stored
`action` (852/864; the 12 drops are the documented enumeration-order defect).
"""
from __future__ import annotations

import json
import os
import pickle
import sys
import time

import numpy as np

os.environ.setdefault("OMP_NUM_THREADS", "6")
HERE = os.path.dirname(os.path.abspath(__file__))
EV = os.path.dirname(HERE)
QA = os.path.dirname(os.path.dirname(EV))
V2 = os.path.join(EV, "vocab2")
for _p in (HERE, EV, QA, V2, os.path.join(EV, "jointdig")):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import feature_battery as FBAT  # noqa: E402
from ceiling_fit import load, SEED, OUT  # noqa: E402

FORK_FILES = ["fork_main.jsonl", "fork_final_uninstrumented.jsonl", "fork_ctl.jsonl"]
SURVIVE = {"clear", "alive", "budget"}


def within_auc(risk, surv):
    r_s, r_f = risk[surv], risk[~surv]
    if len(r_s) == 0 or len(r_f) == 0:
        return np.nan
    gt = (r_f[:, None] > r_s[None, :]).sum()
    eq = (r_f[:, None] == r_s[None, :]).sum()
    return (gt + 0.5 * eq) / (len(r_s) * len(r_f))


def clustered_ci(vals_a, vals_b, seeds_d, B=2000, seed=SEED + 31):
    rng = np.random.default_rng(seed)
    uqs = np.unique(seeds_d)
    idx = {s: np.flatnonzero(seeds_d == s) for s in uqs}
    d = np.empty(B)
    for b in range(B):
        draw = rng.choice(uqs, len(uqs), replace=True)
        sel = np.concatenate([idx[s] for s in draw])
        d[b] = np.nanmean(vals_a[sel]) - np.nanmean(vals_b[sel])
    return dict(mean=float(d.mean()), ci=[float(np.percentile(d, 2.5)),
                                          float(np.percentile(d, 97.5))],
                frac_pos=float((d > 0).mean()))


def main():
    t0 = time.time()
    d = load()
    names = d["names"]
    IDX = {n: i for i, n in enumerate(names)}
    with open(os.path.join(OUT, "ceiling_best.pkl"), "rb") as f:
        pk = pickle.load(f)
    m, sd = pk["model"], pk["sd"]
    F = d["F"]
    keymap = {(int(s), int(p)): i for i, (s, p) in
              enumerate(zip(F["seed"], F["pill_idx"]))}
    recs = []
    for fn in FORK_FILES:
        pth = os.path.join(QA, "tmp", "reconC", fn)
        if os.path.exists(pth):
            for line in open(pth):
                if line.strip():
                    recs.append(json.loads(line))
    rows, plies = [], []
    bad = 0
    for r in recs:
        for p in r.get("plies", []):
            k = (int(r["seed"]), int(p["t"]))
            if k not in keymap:
                continue
            i = keymap[k]
            if int(F["action"][i]) != int(p["a_ch"]):
                bad += 1
                continue
            rows.append(i)
            plies.append(p)
    rows = np.array(rows, dtype=np.int64)
    print(f"join verified {len(rows)}, dropped {bad}", flush=True)

    import s2_features as S2F
    _, exp_all32, fl = S2F.build_expander()
    k = len(rows)
    f11 = np.zeros((k, 32, 11), dtype=np.int64)
    po = np.zeros((k, 32, 128), dtype=np.int8)
    ok32 = np.zeros((k, 32), dtype=np.int8)
    exp_all32(F["board_col"][rows], F["board_vir"][rows], F["cur"][rows, 0],
              F["cur"][rows, 1], fl, f11, po, ok32)
    Hp = FBAT.heights_from_boards(po.reshape(k * 32, 128))
    Hq = np.repeat(FBAT.heights_from_boards(F["board_col"][rows]), 32, axis=0)
    nlp = np.repeat(F["n_legal"][rows].astype(np.int32), 32)
    cd = FBAT.candidate_features(po.reshape(k * 32, 128), Hp, Hq, nlp)
    blk = np.concatenate([f11.reshape(k * 32, 11).astype(np.float64)]
                         + [np.asarray(cd[q], dtype=np.float64)[:, None]
                            for q in FBAT.CAND_NAMES], axis=1).astype(np.float32)
    risk_all = m.decision_function(blk).reshape(k, 32)
    dsh_all = (sd * blk[:, IDX["d_spawn_h"]].astype(np.float64)).reshape(k, 32)
    maxh_all = (blk[:, IDX["MAXH"]].astype(np.float64)).reshape(k, 32)
    spawn_all = (blk[:, IDX["SPAWN"]].astype(np.float64)).reshape(k, 32)
    cv = F["cand_vals"][rows]
    assert int((ok32.astype(bool) != np.isfinite(cv)).sum()) == 0, "legality mismatch"

    out = {"n_joined": int(k), "dropped_enum_order": int(bad),
           "legality_mismatch": 0,
           "caveat": ("fork windows are the last W=6/12 plies of TOPOUT games with an "
                      "S=15/30-pill continuation budget; 76 seeds. NEAR-DEATH ONLY.")}

    # fork_final_uninstrumented.jsonl uses the OLDER 5-tuple act format
    # [a, rank, psh, out, used] and stores no vir0, so the progress gate cannot be
    # applied to it. Gates are therefore run on the 8-tuple subset, and RAW is ALSO
    # reported restricted to that same subset so the gate effect is measured on
    # IDENTICAL plies rather than on a different sample.
    has_prog = np.array([len(p["acts"][0]) == 8 and "vir0" in p for p in plies])
    out["n_plies_with_progress_fields"] = int(has_prog.sum())

    RANKERS = ["model", "champ", "d_spawn_h", "MAXH", "SPAWN"]
    for gate in ("RAW", "RAW_matched_subset", "PROGRESS", "CLEARING"):
        per = {r: [] for r in RANKERS}
        top1 = {r: 0 for r in RANKERS}
        top1["champ_actual"] = 0
        seeds_d, nd = [], 0
        resc = {r: 0 for r in RANKERS}
        resc["n"] = 0
        for j, p in enumerate(plies):
            if gate != "RAW" and not has_prog[j]:
                continue
            acts = p["acts"]
            legal = np.array([a[0] for a in acts], dtype=int)
            if legal.size == 0:
                continue
            vir0 = int(p.get("vir0", 10 ** 9))
            surv = []
            for a in acts:
                o = a[3]
                ok = o in SURVIVE
                if gate == "PROGRESS":
                    ok = ok and (int(a[6]) < vir0)
                elif gate == "CLEARING":
                    ok = ok and (int(a[7]) >= 1)
                surv.append(ok)
            surv = np.array(surv, dtype=bool)
            if surv.all() or (~surv).all():
                continue
            nd += 1
            seeds_d.append(int(F["seed"][rows[j]]))
            r_ = dict(model=risk_all[j, legal], champ=-cv[j, legal].astype(np.float64),
                      d_spawn_h=dsh_all[j, legal], MAXH=maxh_all[j, legal],
                      SPAWN=-spawn_all[j, legal])
            for nm in RANKERS:
                per[nm].append(within_auc(r_[nm], surv))
                top1[nm] += int(surv[np.argmin(r_[nm])])
            ach = int(F["action"][rows[j]])
            surv_of = dict(zip(legal.tolist(), surv.tolist()))
            top1["champ_actual"] += int(surv_of.get(ach, False))
            if not surv_of.get(ach, False):
                resc["n"] += 1
                for nm in RANKERS:
                    resc[nm] += int(surv[np.argmin(r_[nm])])
        seeds_d = np.array(seeds_d)
        blockres = dict(n_discriminative=nd, n_seeds=int(len(np.unique(seeds_d))))
        arr = {nm: np.array(per[nm], dtype=float) for nm in RANKERS}
        for nm in RANKERS:
            blockres[f"within_auc_{nm}"] = float(np.nanmean(arr[nm]))
        if nd > 0:
            blockres["model_minus_champ"] = clustered_ci(arr["model"], arr["champ"], seeds_d)
            blockres["dsh_minus_champ"] = clustered_ci(arr["d_spawn_h"], arr["champ"], seeds_d)
            blockres["dsh_minus_model"] = clustered_ci(arr["d_spawn_h"], arr["model"], seeds_d)
            blockres["top1_survives"] = {nm: top1[nm] / nd for nm in RANKERS}
            blockres["top1_survives"]["champ_actual"] = top1["champ_actual"] / nd
            blockres["rescue_set"] = dict(
                n=resc["n"],
                **{nm: (resc[nm] / resc["n"] if resc["n"] else None) for nm in RANKERS})
        out[gate] = blockres
        print(gate, json.dumps(blockres, indent=1, default=float), flush=True)

    with open(os.path.join(OUT, "ceiling_counterfactual.json"), "w") as f:
        json.dump(out, f, indent=1, default=float)
    print("wrote", time.time() - t0, flush=True)


if __name__ == "__main__":
    main()
