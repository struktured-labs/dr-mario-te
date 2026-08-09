#!/usr/bin/env python3
"""vocab2 Phase 2 ADDENDUM (exploratory, does not alter the pre-registered
verdict): (1) paired-difference bootstrap of each candidate's |AUC-0.5| minus
SPAWN's on identical resamples; (2) BEYOND-VOCAB test -- re-match with the
strongest existing feature added to the stratum key (h, v-bin, g-bin,
SPAWN_pre) so any remaining separation is information the champion's
vocabulary does NOT already express at the state level. Re-binning was
pre-licensed in phase 1 ("raw covariates stored so phase 2 can re-bin").
"""
import sys, os, json
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import feature_battery as FB

RNG = 20260811
B = 200


def key4(h, v, g, sp):
    return (h.astype(np.int64) * 1000000 + v.astype(np.int64) * 10000
            + g.astype(np.int64) * 100 + sp.astype(np.int64))


def main():
    fat, ctl, featF, featC = FB.load_all_features()
    z = np.load(os.path.join(HERE, "features.npz"))
    # pre-board SPAWN term (index 3 of the 11) -- the champion's own strongest
    spF = z["fatal_prefeats"][:, 3]
    spC = z["ctrl_prefeats"][:, 3]
    m = fat["outcome"] == 1

    out = {"rng": RNG, "B": B}

    # ---------- (1) paired-difference bootstrap on the PRIMARY contrast ----
    con = FB.make_contrast(fat, ctl, featF, featC, m)
    names = ["d_spawn_h", "b_spawn_prox", "d_gvuln_mass", "e_escape_routes",
             "x_hvar", "c_nlegal_probe", "c_das_reach"]
    machs = {n: FB.stratified_auc_machinery(con["strata"], con["X"][n],
                                            con["isf"]) for n in names + ["SPAWN"]}
    rng = np.random.default_rng(RNG)
    diffs = {n: [] for n in names}
    for b in range(B):
        w = FB.boot_weights(con["seeds"], con["isf"], rng)
        es = abs(machs["SPAWN"](w)[0] - 0.5)
        for n in names:
            diffs[n].append(abs(machs[n](w)[0] - 0.5) - es)
    ones = np.ones(len(con["isf"]))
    pd = {}
    for n in names:
        d = np.array(diffs[n])
        pd[n] = {"point": float(abs(machs[n](ones)[0] - 0.5)
                                - abs(machs["SPAWN"](ones)[0] - 0.5)),
                 "ci95": [float(np.percentile(d, 2.5)),
                          float(np.percentile(d, 97.5))],
                 "frac_pos": float((d > 0).mean())}
    out["paired_diff_vs_SPAWN"] = pd

    # ---------- (2) beyond-vocab: match on (h, v, g, SPAWN_pre) ------------
    kF = key4(fat["stratum_h"][m], fat["stratum_v"][m], fat["stratum_g"][m],
              spF[m])
    kC = key4(ctl["stratum_h"], ctl["stratum_v"], ctl["stratum_g"], spC)
    common = np.intersect1d(np.unique(kF), np.unique(kC))
    inF = np.isin(kF, common)
    inC = np.isin(kC, common)
    strata = np.concatenate([kF[inF], kC[inC]])
    isf = np.concatenate([np.ones(inF.sum(), bool), np.zeros(inC.sum(), bool)])
    seeds = np.concatenate([fat["seed"][m][inF], ctl["seed"][inC]])
    cov = {"n_fatal": int(inF.sum()), "n_fatal_excluded": int((~inF).sum()),
           "n_ctrl": int(inC.sum())}
    print(f"[beyond] SPAWN-matched: {cov}", flush=True)
    all_names = FB.NAMES11 + FB.CAND_NAMES
    X = {n: np.concatenate([featF[n][m][inF].astype(float),
                            featC[n][inC].astype(float)]) for n in all_names}
    res = {}
    machs2 = {n: FB.stratified_auc_machinery(strata, X[n], isf)
              for n in all_names}
    for n in all_names:
        a, ns = machs2[n](np.ones(len(isf)))
        res[n] = {"auc": a, "n_strata": ns}
    boots = {n: [] for n in all_names}
    for b in range(B):
        w = FB.boot_weights(seeds, isf, rng)
        for n in all_names:
            a, _ = machs2[n](w)
            if not np.isnan(a):
                boots[n].append(a)
    for n in all_names:
        bs = np.array(boots[n])
        res[n]["ci95"] = [float(np.percentile(bs, 2.5)),
                          float(np.percentile(bs, 97.5))]
    # family permutation band under the new key
    fam = []
    for p in range(200):
        yp = FB.perm_labels_within_stratum(strata, isf, rng)
        mx = 0.0
        for n in all_names:
            a, _ = FB.stratified_auc_machinery(strata, X[n], yp)(
                np.ones(len(isf)))
            mx = max(mx, abs(a - 0.5))
        fam.append(mx)
    out["beyond_vocab_spawn_matched"] = {
        "coverage": cov, "auc": res,
        "family_perm_p95": float(np.percentile(fam, 95)),
        "SPAWN_self_check": res["SPAWN"]["auc"]}

    with open(os.path.join(HERE, "addendum_result.json"), "w") as f:
        json.dump(out, f, indent=1, default=str)
    print(json.dumps(pd, indent=1))
    print(f"[beyond] family perm p95 = {np.percentile(fam,95):.4f}; "
          f"SPAWN self-check AUC = {res['SPAWN']['auc']:.4f}")
    for n in all_names:
        print(f"  {n:<22}{res[n]['auc']:>8.4f}  "
              f"[{res[n]['ci95'][0]:.4f},{res[n]['ci95'][1]:.4f}]")


if __name__ == "__main__":
    main()
