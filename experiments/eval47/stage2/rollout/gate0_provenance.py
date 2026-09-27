#!/usr/bin/env python3
"""GATE 0 - PROVENANCE / WIRING.

RECOMMENDED_lut64.json is the artifact this rollout deploys, and it was written
by a script that is not in the tree.  Before it is allowed to drive 6,000 games
it must reproduce, through THIS file's deployed integer pipeline, the numbers
the shippable lane reported for it on the sealed holdout:

    ship-dose quantised holdout AUC   0.7220   (round2 S1br2_lut, q64)
    argmax-flip, target class          2.12%
    argmax-flip, cleared games         1.65%
    A_champ                            0.6645

WHAT WRONG INPUT MAKES THIS FAIL (it is not a vacuous check):
  M1 sign-flipped tables     -> AUC must collapse below 0.5
  M2 row-shuffled tables     -> AUC must fall well below the real model
  M3 features permuted       -> AUC must fall
  M4 champion order replaced -> the base argmax must stop reproducing the
                                corpus's stored `action`
Each mutant is asserted to FIRE.
"""
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import numpy as np  # noqa: E402
from arm_lut import load_recommended, CHAMP_ORDER, MODEL_JSON  # noqa: E402

RES = os.path.join(os.path.dirname(HERE), "results")
OUT = os.path.join(HERE, "out")
FEAT_NAMES = ["MAXH", "HOLES", "TOPRISK", "SPAWN", "SETUP", "MATCHED", "BURIED",
              "RDYEXT", "VRDY", "CROSS", "POLL",
              "a_topout_dist", "a_d_maxh", "b_spawn_prox", "b_spawn_prox_strict",
              "c_das_reach", "c_d_das_reach", "c_nlegal_probe", "c_d_nlegal",
              "d_gvuln_mass", "d_crit_cols", "d_spawn_h",
              "e_escape_routes", "e_escape_reach", "x_hvar", "x_jagged"]


def auc(x, y):
    x = np.asarray(x, dtype=np.float64)
    y = np.asarray(y).astype(bool)
    r = np.empty(len(x))
    o = np.argsort(x, kind="mergesort")
    xs = x[o]
    i = 0
    rk = np.arange(1, len(x) + 1, dtype=np.float64)
    while i < len(x):
        j = i
        while j + 1 < len(x) and xs[j + 1] == xs[i]:
            j += 1
        rk[i:j + 1] = 0.5 * (i + j) + 1
        i = j + 1
    r[o] = rk
    n1 = int(y.sum())
    n0 = len(y) - n1
    return float((r[y].sum() - n1 * (n1 + 1) / 2.0) / (n1 * n0))


def main():
    lut = load_recommended()
    print(f"model {lut.name} feats={lut.feats}")
    print(f"  tables {lut.sizes} sum={sum(lut.sizes)} "
          f"bits={sum(lut.sizes)*12} Delta in [{lut.dmin},{lut.dmax}] "
          f"span={lut.span}")

    z = np.load(os.path.join(RES, "s2feat_local.npz"))
    dF = np.load(os.path.join(RES, "s2lulu_fail_local.npz"))
    dC = np.load(os.path.join(RES, "s2lulu_ctrl_local.npz"))
    sel26 = [FEAT_NAMES.index(f) for f in lut.feats]

    # ------ holdout rows of the PRIMARY CONTRAST (y==1 fail vs y==0 ctrl)
    Ff, Fc = z["fail_feat"], z["ctrl_feat"]
    yf, yc = dF["y"], dC["y"]
    hf, hc = dF["hold"] == 1, dC["hold"] == 1
    keep_f = hf & (yf == 1)
    keep_c = hc & (yc == 0)
    X = np.concatenate([Ff[keep_f][:, sel26], Fc[keep_c][:, sel26]]).astype(float)
    y = np.concatenate([np.ones(keep_f.sum()), np.zeros(keep_c.sum())])
    seeds = np.concatenate([dF["seed"][keep_f], dC["seed"][keep_c]])
    champ = np.concatenate([z["fail_champ_eval"][keep_f],
                            z["ctrl_champ_eval"][keep_c]]).astype(float)
    print(f"holdout rows {X.shape[0]} (pos {int(y.sum())} neg {int((1-y).sum())}) "
          f"games {len(np.unique(seeds))}")

    D = lut.delta_matrix(X)
    a_model = auc(D, y)
    a_champ = auc(-champ, y)
    print(f"  AUC(Delta)   = {a_model:.4f}   [lane reported 0.7220]")
    print(f"  AUC(-CHAMP)  = {a_champ:.4f}   [lane reported 0.6645]")
    print(f"  |Delta| max  = {int(np.abs(D).max())}  int16 ok "
          f"{bool(np.abs(D).max() <= 32767)}   sd {float(D.std()):.2f}")

    # ------ MUTANTS on the AUC pipeline
    mut = {}
    mut["M1_sign_flip"] = auc(lut.sign_flipped().delta_matrix(X), y)
    mut["M2_shuffled_tables"] = auc(lut.shuffled_tables().delta_matrix(X), y)
    perm = np.random.default_rng(7).permutation(X.shape[1])
    mut["M3_feature_permute"] = auc(lut.delta_matrix(X[:, perm]), y)
    for k, v in mut.items():
        print(f"  MUTANT {k:22s} AUC {v:.4f}")
    fires = {"M1_sign_flip": mut["M1_sign_flip"] < 0.5,
             "M2_shuffled_tables": mut["M2_shuffled_tables"] < a_model - 0.05,
             "M3_feature_permute": mut["M3_feature_permute"] < a_model - 0.05}

    # ------ within-decision argmax flip on the stored 32-sibling layer
    flips = {}
    for nm, dd in (("fail", dF), ("ctrl", dC)):
        hh = z[f"all32_{nm}_hold"] == 1
        v = z[f"all32_{nm}_vals"][hh].astype(np.float64)
        act = z[f"all32_{nm}_action"][hh].astype(int)
        F32 = z[f"all32_{nm}_feat"][hh][:, :, sel26].astype(np.float64)
        n = v.shape[0]
        Dm = lut.delta_matrix(F32.reshape(-1, len(sel26))).reshape(n, 32).astype(float)
        base = CHAMP_ORDER[np.nanargmax(v[:, CHAMP_ORDER], axis=1)]
        assert (base == act).mean() > 0.999, "argmax reconstruction broken"
        new = CHAMP_ORDER[np.nanargmax((v - Dm)[:, CHAMP_ORDER], axis=1)]
        flips[nm] = float((new != act).mean())
        # M4: a WRONG enumeration order must stop reproducing the stored action
        bad = CHAMP_ORDER[::-1]
        wrong = bad[np.nanargmax(v[:, bad], axis=1)]
        flips[f"{nm}_M4_wrong_order_disagreement"] = float((wrong != act).mean())
        print(f"  flip[{nm}] = {flips[nm]*100:.2f}%   "
              f"(M4 wrong-order base disagreement "
              f"{flips[f'{nm}_M4_wrong_order_disagreement']*100:.2f}%)")
    fires["M4_wrong_enum_order"] = flips["fail_M4_wrong_order_disagreement"] > 0.01

    ok = (abs(a_model - 0.7220) < 0.002 and abs(a_champ - 0.6645) < 0.002
          and abs(flips["fail"] - 0.0212) < 0.004
          and abs(flips["ctrl"] - 0.0165) < 0.004
          and all(fires.values()))
    res = {"model": lut.name, "model_json": MODEL_JSON,
           "auc_model": a_model, "auc_champ": a_champ,
           "reported_auc_model": 0.7220, "reported_auc_champ": 0.6645,
           "flip_target_class": flips["fail"], "reported_flip_target": 0.0212,
           "flip_cleared_games": flips["ctrl"], "reported_flip_clear": 0.0165,
           "delta_abs_max": int(np.abs(D).max()), "delta_sd": float(D.std()),
           "delta_span": lut.span, "param_bits": sum(lut.sizes) * 12,
           "mutant_aucs": mut, "mutants_fire": fires,
           "holdout_rows": int(X.shape[0]),
           "holdout_games": int(len(np.unique(seeds))),
           "pass": bool(ok)}
    os.makedirs(OUT, exist_ok=True)
    json.dump(res, open(os.path.join(OUT, "gate0_provenance.json"), "w"),
              indent=1, default=float)
    print(f"GATE 0: {'PASS' if ok else 'FAIL'}")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
