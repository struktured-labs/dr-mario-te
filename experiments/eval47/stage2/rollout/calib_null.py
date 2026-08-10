#!/usr/bin/env python3
"""Calibrate a DOSE-MATCHED label-blind null.

The first null (row-permuted tables) preserves the |Delta| value multiset but
NOT the argmax-flip rate: it flips 7.28% of rollout plies against the fitted
arm's 1.78%, i.e. it is a 4.1x more aggressive intervention.  That makes the
difference-in-differences biased IN FAVOUR of the fitted arm, which is stated in
the report - but a dose-matched null is the actual control.

This scales the shuffled tables by k and picks the k whose TARGET-CLASS
argmax-flip on the sealed holdout's 32-sibling layer matches the fitted model's
2.12% - the identical instrument and identical statistic used to set the fitted
model's ship dose (PREREG_SHIPPABLE deviation entry 4).  Offline, seconds, no
rollout compute.
"""
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import numpy as np  # noqa: E402
from arm_lut import load_recommended, CHAMP_ORDER, LutDelta  # noqa: E402

RES = os.path.join(os.path.dirname(HERE), "results")
FEAT_NAMES = ["MAXH", "HOLES", "TOPRISK", "SPAWN", "SETUP", "MATCHED", "BURIED",
              "RDYEXT", "VRDY", "CROSS", "POLL",
              "a_topout_dist", "a_d_maxh", "b_spawn_prox", "b_spawn_prox_strict",
              "c_das_reach", "c_d_das_reach", "c_nlegal_probe", "c_d_nlegal",
              "d_gvuln_mass", "d_crit_cols", "d_spawn_h",
              "e_escape_routes", "e_escape_reach", "x_hvar", "x_jagged"]


def flip_rate(lut, z, sel26, nm):
    hh = z[f"all32_{nm}_hold"] == 1
    v = z[f"all32_{nm}_vals"][hh].astype(np.float64)
    act = z[f"all32_{nm}_action"][hh].astype(int)
    F = z[f"all32_{nm}_feat"][hh][:, :, sel26].astype(np.float64)
    n = v.shape[0]
    D = lut.delta_matrix(F.reshape(-1, len(sel26))).reshape(n, 32).astype(float)
    new = CHAMP_ORDER[np.nanargmax((v - D)[:, CHAMP_ORDER], axis=1)]
    return float((new != act).mean())


def main():
    fit = load_recommended()
    shuf = fit.shuffled_tables(20260810)
    z = np.load(os.path.join(RES, "s2feat_local.npz"))
    sel26 = [FEAT_NAMES.index(f) for f in fit.feats]
    tgt = flip_rate(fit, z, sel26, "fail")
    tgt_c = flip_rate(fit, z, sel26, "ctrl")
    print(f"fitted arm: flip target-class {tgt*100:.2f}%  cleared {tgt_c*100:.2f}%")
    rows = []
    best = None
    for k in (0.05, 0.08, 0.1, 0.125, 0.15, 0.2, 0.25, 0.3, 0.4, 0.5, 0.75, 1.0):
        sc = LutDelta(shuf.feats, shuf.scales,
                      [np.rint(np.asarray(t) * k).astype(np.int64)
                       for t in shuf.tables], name=f"shuf_k{k}")
        f = flip_rate(sc, z, sel26, "fail")
        fc = flip_rate(sc, z, sel26, "ctrl")
        rows.append({"k": k, "flip_target": f, "flip_clear": fc,
                     "delta_span": sc.span})
        print(f"  k={k:<6} flip_target {f*100:6.2f}%  clear {fc*100:6.2f}%  "
              f"span {sc.span}")
        if best is None or abs(f - tgt) < abs(best[1] - tgt):
            best = (k, f, fc)
    print(f"CHOSEN k={best[0]} -> flip_target {best[1]*100:.2f}% "
          f"(fitted {tgt*100:.2f}%), cleared {best[2]*100:.2f}%")
    out = {"fitted_flip_target": tgt, "fitted_flip_clear": tgt_c,
           "grid": rows, "chosen_k": best[0],
           "chosen_flip_target": best[1], "chosen_flip_clear": best[2]}
    json.dump(out, open(os.path.join(HERE, "out", "calib_null.json"), "w"),
              indent=1, default=float)


if __name__ == "__main__":
    main()
