#!/usr/bin/env python
"""
ANATOMY OF THE ARGMAX FLIP -- the number that decides whether any of this is safe.

Three questions the AUC cannot answer:
 1. Does the flip land on TIED decisions (champion currently picking by enumeration
    order -- free to change) or on decisions the champion actually decided?
    PREREG_STAGE2 section 8: 36.0% of champion decisions have the top value TIED.
 2. What is the target-class flip vs the CLEAR-GAME flip at every dose?  At the
    population ratio breakage is ~6.4x as expensive as rescue, so the ratio, not the
    target-class rate, is what prices the arm.
 3. Does the champion's own AUC swing across `since_last_garbage` deciles as much as
    the model's?  A swing that both share is a property of the slice, not evidence of
    eval-hacking.
"""
import json
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from s2_shippable import (OUT, RES, CHAMP_ORDER, auc, cols, load, FEAT_SCALE,
                          quant_at_dose)
import models as M
import pickle

DOSES = [1, 2, 5, 10, 20, 40, 80, 160, 320]


def main():
    P = pickle.load(open(os.path.join(OUT, "fitted.pkl"), "rb"))
    sel, scales = P["sel"], P["scales"]
    d = load(with_holdout=True)
    ho = d.hold == 1
    y = d.y[ho].astype(int)
    champ_risk = -d.champ[ho].astype(np.float64)

    F = np.load(os.path.join(RES, "s2feat_local.npz"))
    sel26 = [d.idx[f] for f in sel]
    A32 = {}
    for nm in ("fail", "ctrl"):
        hh = F[f"all32_{nm}_hold"] == 1
        v = F[f"all32_{nm}_vals"][hh].astype(np.float64)
        fq, _ = M.quantise_features(
            F[f"all32_{nm}_feat"][hh][:, :, sel26].astype(np.float64
                                                          ).reshape(-1, len(sel)),
            scales)
        srt = np.sort(np.where(np.isfinite(v), v, -np.inf), axis=1)[:, ::-1]
        A32[nm] = dict(fq=fq, vals=v, n=v.shape[0],
                       act=F[f"all32_{nm}_action"][hh].astype(int),
                       tied=(srt[:, 0] == srt[:, 1]))
        print(f"[anat] {nm}: {v.shape[0]} holdout decisions, "
              f"top-value TIED on {A32[nm]['tied'].mean()*100:.1f}%")

    out = {"tie_rate": {k: float(A32[k]["tied"].mean()) for k in A32}, "models": {}}

    # champion's own decile swing -- the control for question 3
    g = d.slg[ho]
    qs = np.percentile(g, np.arange(0, 101, 10))
    ch = []
    for i in range(10):
        mm = (g >= qs[i]) & (g <= qs[i + 1])
        if mm.sum() > 500:
            ch.append(auc(champ_risk[mm], y[mm]))
    out["champ_slg_decile_auc"] = {"min": min(ch), "max": max(ch),
                                   "spread": max(ch) - min(ch)}
    print(f"[anat] CHAMPION slg-decile AUC min {min(ch):.3f} max {max(ch):.3f} "
          f"spread {max(ch)-min(ch):.3f}")

    for key in ["S0", "S1", "S1b", "S2", "S3"]:
        m = P["models"][key]
        idx = m.sel_idx
        base_sd = float(np.std(m.raw(M.quantise_features(
            cols(d, sel), scales)[0][~ho][:, idx]))) or 1.0
        curve = []
        for T in DOSES:
            qd = quant_at_dose(m, T / base_sd)
            row = {"delta_sd": T}
            for nm in ("fail", "ctrl"):
                a = A32[nm]
                D = qd.delta(a["fq"][:, idx]).reshape(a["n"], 32).astype(np.float64)
                new = a["vals"] - D
                arg = CHAMP_ORDER[np.nanargmax(new[:, CHAMP_ORDER], axis=1)]
                fl = arg != a["act"]
                row[f"flip_{nm}"] = float(fl.mean())
                row[f"flip_{nm}_on_ties"] = float(fl[a["tied"]].mean())
                row[f"flip_{nm}_on_decided"] = float(fl[~a["tied"]].mean())
                row[f"frac_of_flips_that_are_ties"] = float(
                    (fl & a["tied"]).sum() / max(1, fl.sum())) if nm == "fail" else \
                    row.get("frac_of_flips_that_are_ties")
            row["target_over_clear"] = (row["flip_fail"] /
                                        max(1e-9, row["flip_ctrl"]))
            curve.append(row)
        out["models"][key] = curve
        print(f"--- {key}")
        for r in curve:
            print(f"   sd={r['delta_sd']:>3}  flipT {r['flip_fail']*100:6.2f}% "
                  f"(ties {r['flip_fail_on_ties']*100:5.2f}% / decided "
                  f"{r['flip_fail_on_decided']*100:5.2f}%)  flipC "
                  f"{r['flip_ctrl']*100:6.2f}% (ties {r['flip_ctrl_on_ties']*100:5.2f}%"
                  f" / decided {r['flip_ctrl_on_decided']*100:5.2f}%)  T/C "
                  f"{r['target_over_clear']:.2f}")

    with open(os.path.join(OUT, "flip_anatomy.json"), "w") as fh:
        json.dump(out, fh, indent=1)


if __name__ == "__main__":
    main()
