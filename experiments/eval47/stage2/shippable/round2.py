#!/usr/bin/env python
"""
ROUND 2 -- CORRECTED ELIGIBLE SET.

WHY THIS EXISTS, stated plainly because it matters for how the numbers are read:
PREREG_SHIPPABLE section 3 fixed the eligible feature set to PREREG_STAGE2 section 8's
`FREE_IN_COLWALK` list.  That list names 11 features and omits SETUP, MATCHED, BURIED,
RDYEXT, VRDY and POLL.  Those six are the CHAMPION'S OWN COMBINE TERMS.  Verified
directly in fpga/copro/LeafEval.sv S_DONE2:

    sco <= 5000 - 12*maxh_p - 20*holes_p - 90*toprisk_p - 150*spawn_p + 32*setup_p
           + matched60_p - 48*buried_p + 8*rdy_ext_p + 8*vrdy_p - 6*pollution_p

Every one of those is an already-registered operand at the moment the combine runs.
Reading them as Delta inputs costs ZERO new board passes, ZERO new cycles and ZERO new
accumulators.  Section 8's list was a list about the CANDIDATE features; omitting the
champion's own terms from it was an oversight, not a budget tag.  (CROSS is excluded:
it exists in the Python feature battery but NOT in the RTL leaf -- grep finds it only in
a comment.)

THIS DOES NOT RE-WEIGHT ANYTHING.  The ten champion coefficients stay bit-identical;
Delta is still added on top and `Delta == 0` is still an exact-identity control.  Using
BURIED as an INPUT to a nonlinear added term is not the same operation as changing the
-48 coefficient, and the U-curve law (ws=20 is failure-optimal) is about the latter.

*** CONTAMINATION FLAG, carried on every round-2 number ***
The decision to correct the eligible set was taken AFTER a holdout-scored diagnostic
showed BURIED as the largest single addition (+0.023).  The FIT and the FEATURE
SELECTION below run on TRAIN ROWS ONLY, but the choice of which category to admit was
holdout-informed.  Round-2 holdout AUCs are therefore OPTIMISTICALLY BIASED and are
reported as INDICATIVE.  They must be re-established under a fresh pre-registration on
the population-scale corpus (Hetzner job 070) before any of them is used for a GO.
Round 1 (S0/S1/S1b/S2/S3) remains the clean, uncontaminated result.
"""
import json
import os
import pickle
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from s2_shippable import (OUT, RES, CHAMP_ORDER, auc, boot_paired_auc, cols,  # noqa
                          hinge_compress, load, quant_at_dose, _fit_additive)
import models as M
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.model_selection import GroupKFold

# 10 RTL combine operands (free: already registered) + height-derived free candidates
ELIGIBLE2 = ["MAXH", "HOLES", "TOPRISK", "SPAWN", "SETUP", "MATCHED", "BURIED",
             "RDYEXT", "VRDY", "POLL",
             "a_topout_dist", "d_spawn_h", "d_crit_cols", "d_gvuln_mass",
             "x_jagged", "x_hvar", "e_escape_routes"]
FMAX = {"MAXH": 16, "HOLES": 40, "TOPRISK": 23, "SPAWN": 8, "SETUP": 13,
        "MATCHED": 8, "BURIED": 118, "RDYEXT": 349, "VRDY": 192, "POLL": 160,
        "a_topout_dist": 14, "d_spawn_h": 16, "d_crit_cols": 8,
        "d_gvuln_mass": 40, "x_jagged": 73, "x_hvar": 52, "e_escape_routes": 8}
# uint8 grid: RDYEXT (max 349) needs a 2^-1 scale to fit; everything else is scale 1.
FSCALE = {n: (0.5 if FMAX[n] > 255 else 1) for n in ELIGIBLE2}
DOSES = [1, 2, 5, 10, 20, 40, 80, 160, 320]


def main():
    d = load(with_holdout=True)
    tr, ho = d.hold == 0, d.hold == 1
    ytr, yho = d.y[tr].astype(int), d.y[ho].astype(int)
    champ_risk = -d.champ[ho].astype(np.float64)
    A_champ = auc(champ_risk, yho)

    # ---- selection: TRAIN ROWS ONLY, GroupKFold by seed
    dtr = load(with_holdout=False)
    folds = list(GroupKFold(n_splits=5).split(np.zeros(dtr.y.shape[0]), dtr.y,
                                              groups=dtr.seed))

    def cv(feats):
        X = cols(dtr, feats)
        s = np.empty(dtr.y.shape[0])
        for a, b in folds:
            m = HistGradientBoostingClassifier(max_iter=32, max_depth=4,
                                               learning_rate=0.2,
                                               early_stopping=False,
                                               random_state=0).fit(X[a], dtr.y[a])
            s[b] = m.predict_proba(X[b])[:, 1]
        return auc(s, dtr.y)

    chosen, rem, trace = [], list(ELIGIBLE2), []
    while len(chosen) < 8:
        sc = [(cv(chosen + [f]), f) for f in rem]
        sc.sort(reverse=True)
        chosen.append(sc[0][1])
        rem.remove(sc[0][1])
        trace.append({"k": len(chosen), "added": sc[0][1], "cv_auc": sc[0][0]})
        print(f"[r2 select] k={len(chosen)} += {sc[0][1]:16s} cvAUC={sc[0][0]:.4f}",
              flush=True)

    sel = chosen
    scales = [FSCALE[f] for f in sel]
    sizes = [int(FMAX[f] * FSCALE[f]) + 1 for f in sel]
    Xq, qerr = M.quantise_features(cols(d, sel), scales)
    print(f"[r2] features {sel}")
    print(f"[r2] quant max abs err {dict(zip(sel,[round(e,3) for e in qerr]))}")
    counts = [np.bincount(Xq[tr][:, j], minlength=sizes[j]).astype(float)
              for j in range(8)]

    # ---- fit the two shapes round 1 recommended between
    luts, _ = _fit_additive(Xq[tr], ytr, sel, sizes, 800)
    S1b = M.AdditiveLUT(sel, sizes, luts)
    cur, brk = zip(*[hinge_compress(luts[j], counts[j]) for j in range(8)])
    S1 = M.HingePWL(sel, sizes, list(cur), list(brk))
    m3 = HistGradientBoostingClassifier(max_iter=32, max_depth=4, max_leaf_nodes=16,
                                        learning_rate=0.2, early_stopping=False,
                                        random_state=0, max_bins=255
                                        ).fit(Xq[tr].astype(np.float64), ytr)
    S3 = M.TreeEnsemble(sel, M.extract_hgb_trees(m3, 4), 4)

    # ---- all32 within-decision layer
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

    out = {"contamination_flag": __doc__.split("*** CONTAMINATION FLAG")[1].strip(),
           "eligible2": ELIGIBLE2, "selected": sel, "trace": trace,
           "A_champ": A_champ, "quant_err": dict(zip(sel, qerr)), "models": {}}

    for name, m in [("S1r2_hinge", S1), ("S1br2_lut", S1b), ("S3r2_trees", S3)]:
        idx = list(range(8))
        base_sd = float(np.std(m.raw(Xq[tr]))) or 1.0
        rec = {"float_auc": auc(m.raw(Xq[ho]), yho),
               "quant12_auc": auc(m.quantise(12).delta(Xq[ho]), yho),
               "mutant3bit_auc": auc(m.quantise(3).delta(Xq[ho]), yho)}
        curve = []
        for T in DOSES:
            qd = quant_at_dose(m, T / base_sd)
            r = {"delta_sd": T}
            for nm in ("fail", "ctrl"):
                a = A32[nm]
                D = qd.delta(a["fq"]).reshape(a["n"], 32).astype(np.float64)
                arg = CHAMP_ORDER[np.nanargmax((a["vals"] - D)[:, CHAMP_ORDER], axis=1)]
                fl = arg != a["act"]
                r[f"flip_{nm}"] = float(fl.mean())
                r[f"flip_{nm}_ties"] = float(fl[a["tied"]].mean())
                r[f"flip_{nm}_decided"] = float(fl[~a["tied"]].mean())
            r["T_over_C"] = r["flip_fail"] / max(1e-9, r["flip_ctrl"])
            r["auc"] = auc(qd.delta(Xq[ho]), yho)
            curve.append(r)
        ship = next((c for c in curve if c["flip_fail"] >= 0.02), curve[-1])
        qs = quant_at_dose(m, ship["delta_sd"] / base_sd)
        ds = qs.delta(Xq[ho])
        rec.update(ship_dose_sd=ship["delta_sd"], ship_quant_auc=auc(ds, yho),
                   flip_target=ship["flip_fail"], flip_clear=ship["flip_ctrl"],
                   T_over_C=ship["T_over_C"], dose_curve=curve,
                   accum_max_abs=int(np.abs(ds).max()),
                   accum_int16_ok=bool(np.abs(ds).max() <= 32767),
                   param_bits=m.quantise(12).param_bits(),
                   cycles=m.quantise(12).cycles(), ops=m.quantise(12).ops())
        lo, hi, dist = boot_paired_auc(ds.astype(float), champ_risk, yho,
                                       d.seed[ho], B=2000)
        rec.update(B2_diff=rec["ship_quant_auc"] - A_champ, B2_ci95=[lo, hi],
                   B2_frac_pos=float((dist > 0).mean()))
        out["models"][name] = rec
        print(f"[r2] {name:12s} q12 {rec['quant12_auc']:.4f} ship "
              f"{rec['ship_quant_auc']:.4f} 3bit {rec['mutant3bit_auc']:.4f} "
              f"B2 {rec['B2_diff']:+.4f} [{lo:+.4f},{hi:+.4f}] flipT "
              f"{ship['flip_fail']*100:.2f}% flipC {ship['flip_ctrl']*100:.2f}% "
              f"T/C {ship['T_over_C']:.2f} cyc {rec['cycles']} "
              f"bits {rec['param_bits']}", flush=True)

    with open(os.path.join(OUT, "round2_result.json"), "w") as fh:
        json.dump(out, fh, indent=1, default=float)
    pickle.dump({"sel": sel, "scales": scales, "sizes": sizes,
                 "models": {"S1r2_hinge": S1, "S1br2_lut": S1b, "S3r2_trees": S3}},
                open(os.path.join(OUT, "round2_fitted.pkl"), "wb"))


if __name__ == "__main__":
    main()
