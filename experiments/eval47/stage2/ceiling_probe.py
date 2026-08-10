#!/usr/bin/env python3
"""STAGE 2 CEILING, part 2: hyperparameter sweep for the TRUE ceiling + the
interrogations declared in ceiling_fit.py's frozen docstring (L1-L6).

Everything selected on TRAIN / INNER fold. Holdout scored once per declared arm.
Caveat from ceiling_fit.py applies to every number here.

NEW vs part 1:
  * HP sweep (GBM families + ExtraTrees) on the inner by-seed fold -> the ceiling arm.
  * L6 argmax-flip with TIE HANDLING (part 1's np.argmin overstated d_spawn_h's flip rate
    to 99% because the feature is a small integer with massive ties and argmin keeps the
    lowest raw index, which is NOT the champion's enumeration order -- the same defect the
    corpus builder's deviation-log entry 2 fixed for gate A4).
  * BADNESS-DETECTOR TEST: target class vs STALL games. Both are "bad games"; only one
    tops out. If AUC ~ 0.5 the model learned "about to die"; if AUC >> 0.5 in the same
    direction as the primary contrast, it learned "this game is going badly", which is the
    label-broadcast defect, not a survival ruler.
  * GAME-LEVEL AUC: labels are per GAME, so the honest unit is the game (657 holdout).
  * L5 cross-generation transfer: vocab2 / pressured_drip, seeds > 12001 (disjoint from
    s2lulu's 2..12001), NO refitting.
  * future-encoding audit: |Spearman(feature, t_to_end)| within positive games.
"""
from __future__ import annotations

import json
import os
import pickle
import sys
import time

import numpy as np

os.environ.setdefault("OMP_NUM_THREADS", "6")
from sklearn.ensemble import HistGradientBoostingClassifier, ExtraTreesClassifier  # noqa

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from ceiling_fit import (auc_fast, strat_auc, boot_paired, load, NAMES11,  # noqa: E402
                         FREE_IN_COLWALK, SEED, HOLD_MOD, INNER_MOD, OUT, RES)

VOC = os.path.abspath(os.path.join(HERE, "..", "vocab2"))
CAND_NAMES = ["a_topout_dist", "a_d_maxh", "b_spawn_prox", "b_spawn_prox_strict",
              "c_das_reach", "c_d_das_reach", "c_nlegal_probe", "c_d_nlegal",
              "d_gvuln_mass", "d_crit_cols", "d_spawn_h",
              "e_escape_routes", "e_escape_reach", "x_hvar", "x_jagged"]

SWEEP = [
    dict(kind="gbm", learning_rate=0.06, max_leaf_nodes=31, min_samples_leaf=50, l2_regularization=1.0),
    dict(kind="gbm", learning_rate=0.06, max_leaf_nodes=63, min_samples_leaf=50, l2_regularization=1.0),
    dict(kind="gbm", learning_rate=0.06, max_leaf_nodes=127, min_samples_leaf=100, l2_regularization=1.0),
    dict(kind="gbm", learning_rate=0.03, max_leaf_nodes=63, min_samples_leaf=100, l2_regularization=1.0),
    dict(kind="gbm", learning_rate=0.03, max_leaf_nodes=127, min_samples_leaf=200, l2_regularization=5.0),
    dict(kind="gbm", learning_rate=0.10, max_leaf_nodes=31, min_samples_leaf=20, l2_regularization=0.0),
    dict(kind="gbm", learning_rate=0.02, max_leaf_nodes=255, min_samples_leaf=200, l2_regularization=10.0),
    dict(kind="gbm", learning_rate=0.05, max_leaf_nodes=15, min_samples_leaf=50, l2_regularization=1.0),
]
GRID = (25, 50, 75, 100, 150, 200, 300, 500, 800)


def sweep(Xtr, ytr, inner, cols, tag=""):
    best = None
    rows = []
    for cfg in SWEEP:
        kw = {k: v for k, v in cfg.items() if k != "kind"}
        m = HistGradientBoostingClassifier(max_iter=max(GRID), max_bins=255,
                                           early_stopping=False, random_state=SEED, **kw)
        m.fit(Xtr[~inner][:, cols], ytr[~inner])
        st = list(m.staged_decision_function(Xtr[inner][:, cols]))
        for g in GRID:
            a = auc_fast(ytr[inner], st[g - 1].ravel())
            rows.append(dict(cfg=cfg, n_iter=g, inner_auc=a))
            if best is None or a > best["inner_auc"]:
                best = dict(cfg=cfg, n_iter=g, inner_auc=a)
        print(f"  [{tag}] lr={cfg['learning_rate']} leaves={cfg['max_leaf_nodes']} "
              f"best={max(r['inner_auc'] for r in rows[-len(GRID):]):.4f}", flush=True)
    # second family: ExtraTrees
    et = ExtraTreesClassifier(n_estimators=300, min_samples_leaf=20, n_jobs=6,
                              random_state=SEED)
    et.fit(Xtr[~inner][:, cols], ytr[~inner])
    a_et = auc_fast(ytr[inner], et.predict_proba(Xtr[inner][:, cols])[:, 1])
    rows.append(dict(cfg=dict(kind="extratrees", n_estimators=300, min_samples_leaf=20),
                     n_iter=300, inner_auc=a_et))
    print(f"  [{tag}] extratrees inner={a_et:.4f}", flush=True)
    if a_et > best["inner_auc"]:
        best = rows[-1]
    return best, rows


def build_final(Xtr, ytr, cols, best):
    if best["cfg"].get("kind") == "extratrees":
        m = ExtraTreesClassifier(n_estimators=300, min_samples_leaf=20, n_jobs=6,
                                 random_state=SEED)
        m.fit(Xtr[:, cols], ytr)
        return m, (lambda M, Z: M.predict_proba(Z)[:, 1])
    kw = {k: v for k, v in best["cfg"].items() if k != "kind"}
    m = HistGradientBoostingClassifier(max_iter=best["n_iter"], max_bins=255,
                                       early_stopping=False, random_state=SEED, **kw)
    m.fit(Xtr[:, cols], ytr)
    return m, (lambda M, Z: M.decision_function(Z))


def flip_rates(S, F, m26, score_fn, IDX, sd, part, tclass_only):
    """argmax-flip vs the champion, WITH TIES. A flip is counted only when the champion's
    chosen slot is STRICTLY worse than the model's best legal slot."""
    Xa = S[f"all32_{part}_feat"].astype(np.float32)
    ok = S[f"all32_{part}_ok"].astype(bool)
    act = S[f"all32_{part}_action"].astype(int)
    hb = S[f"all32_{part}_hold"].astype(bool)
    ridx = S[f"all32_{part}_rowidx"]
    n, k, p = Xa.shape
    flat = Xa.reshape(n * k, p)
    r = score_fn(m26, flat).reshape(n, k)          # higher = more fatal = worse
    dv = flat[:, IDX["d_spawn_h"]].astype(np.float64).reshape(n, k) * sd  # higher=worse
    big = np.inf
    rm = np.where(ok, r, big)
    dm = np.where(ok, dv, big)
    bestr = rm.min(axis=1)
    bestd = dm.min(axis=1)
    ar = r[np.arange(n), act]
    ad = dv[np.arange(n), act]
    sub = hb
    if tclass_only:
        sub = hb & (F["y"][ridx] == 1)
    eps = 1e-9
    out = dict(n=int(sub.sum()),
               flip_model=float((ar[sub] > bestr[sub] + eps).mean()),
               flip_dsh=float((ad[sub] > bestd[sub] + eps).mean()),
               dsh_tie_at_best=float((np.abs(ad[sub] - bestd[sub]) <= eps).mean()),
               model_tie_at_best=float((np.abs(ar[sub] - bestr[sub]) <= eps).mean()))
    # by t_to_end band
    tte = F["t_to_end"][ridx] if part == "fail" else None
    if tte is not None:
        out["by_t_to_end"] = {}
        for lab, mm in [("<=2", tte <= 2), ("3-9", (tte >= 3) & (tte <= 9)),
                        ("10-30", (tte >= 10) & (tte <= 30)), (">30", tte > 30)]:
            s2 = sub & mm
            if s2.sum() >= 50:
                out["by_t_to_end"][lab] = dict(
                    n=int(s2.sum()),
                    flip_model=float((ar[s2] > bestr[s2] + eps).mean()),
                    flip_dsh=float((ad[s2] > bestd[s2] + eps).mean()))
    return out


def vocab2_transfer(m, score_fn, names, sgn_champ, sd, IDX):
    fw = np.load(os.path.join(VOC, "fatal_windows.npz"))
    ct = np.load(os.path.join(VOC, "controls.npz"))
    fz = np.load(os.path.join(VOC, "features.npz"))

    def mat(pref, n):
        cols = []
        for i, nm in enumerate(NAMES11):
            cols.append(fz[f"{pref}_feats11"][:, i])
        for nm in CAND_NAMES:
            cols.append(fz[f"{pref}_cand_{nm}"])
        M = np.column_stack(cols).astype(np.float32)
        assert M.shape[1] == 26 and n == M.shape[0]
        return M

    XF = mat("fatal", len(fw["seed"]))
    XC = mat("ctrl", len(ct["seed"]))
    # vocab2 end_kind_code: garbage_topout = 3 ; outcome 1 = topout
    mF = (fw["outcome"] == 1) & (fw["dies_ahead"] == 1) & (fw["end_kind"] == 3) \
        & (fw["seed"] > 12001)
    mC = (ct["outcome"] == 0) & (ct["seed"] > 12001)
    X = np.vstack([XF[mF], XC[mC]])
    y = np.concatenate([np.ones(mF.sum(), int), np.zeros(mC.sum(), int)])
    seeds = np.concatenate([fw["seed"][mF], ct["seed"][mC]])
    cvF = fw["cand_vals"][np.arange(len(fw["action"])), fw["action"]][mF]
    cvC = ct["cand_vals"][np.arange(len(ct["action"])), ct["action"]][mC]
    champ = sgn_champ * np.concatenate([cvF, cvC]).astype(np.float64)
    sc = score_fn(m, X)
    dshv = sd * X[:, IDX["d_spawn_h"]].astype(np.float64)
    bp = boot_paired(y.astype(bool), seeds, sc, champ, B=200, seed=SEED + 11)
    mh = np.concatenate([fw["max_height"][mF], ct["max_height"][mC]]).astype(np.int64)
    vir = np.concatenate([fw["viruses"][mF], ct["viruses"][mC]]).astype(np.int64)
    gc = np.concatenate([fw["garbage_cum"][mF], ct["garbage_cum"][mC]]).astype(np.int64)
    key = mh * 10000 + np.minimum(vir, 30) // 3 * 100 + np.minimum(gc, 48) // 8
    sm, ns = strat_auc(key, y.astype(bool), sc)
    sc2, _ = strat_auc(key, y.astype(bool), champ)
    return dict(regime="pressured_drip (DIFFERENT pressure model + different extraction)",
                extraction="last-K=10 windows, stratum-matched; seeds>12001 only",
                n=int(len(y)), npos=int(y.sum()),
                n_pos_games=int(len(np.unique(seeds[y == 1]))),
                n_neg_games=int(len(np.unique(seeds[y == 0]))),
                auc_model=auc_fast(y, sc), auc_champ=auc_fast(y, champ),
                auc_dsh=auc_fast(y, dshv),
                paired_diff=bp[0], ci_lo=bp[1], ci_hi=bp[2], frac_pos=bp[3],
                strat_auc_model=sm, strat_auc_champ=sc2, n_strata=ns)


def main():
    t0 = time.time()
    d = load()
    names = d["names"]
    IDX = {n: i for i, n in enumerate(names)}
    X, y, seeds, hold = d["X"], d["y"].astype(int), d["seed"], d["hold"]
    tr, ho = ~hold, hold
    Xtr, ytr = X[tr], y[tr]
    inner = np.isin(seeds[tr] % 10, INNER_MOD)
    out = {"prereg": "PREREG_STAGE2.md @ b9725fc", "plan": "ceiling_fit.py docstring"}

    print("HP SWEEP (inner fold, holdout untouched)", flush=True)
    best, rows = sweep(Xtr, ytr, inner, list(range(26)), "all26")
    print("BEST", best, flush=True)
    m, sfn = build_final(Xtr, ytr, list(range(26)), best)
    sc_ho = sfn(m, X[ho])
    sgn = 1.0 if auc_fast(ytr, d["champ"][tr]) >= 0.5 else -1.0
    champ_ho = sgn * d["champ"][ho]
    sd = 1.0 if auc_fast(ytr, X[tr, IDX["d_spawn_h"]].astype(float)) >= 0.5 else -1.0

    a_model = auc_fast(y[ho], sc_ho)
    a_champ = auc_fast(y[ho], champ_ho)
    bp = boot_paired(y[ho], seeds[ho], sc_ho, champ_ho)
    out["ceiling"] = dict(best_cfg=best, auc_model=a_model, auc_champ=a_champ,
                          paired_diff=bp[0], ci_lo=bp[1], ci_hi=bp[2],
                          frac_reps_positive=bp[3])
    out["sweep"] = rows
    print("CEILING", out["ceiling"], flush=True)

    # ---- ablation ladder re-run under the SWEPT config (declared arms)
    lad = {}
    for tag, cols in [("ALL26", list(range(26))),
                      ("MINUS_DSH", [i for i in range(26) if names[i] != "d_spawn_h"]),
                      ("BASE11", [IDX[n] for n in NAMES11]),
                      ("BASE11_DSH", [IDX[n] for n in NAMES11] + [IDX["d_spawn_h"]]),
                      ("FREE16", [IDX[n] for n in FREE_IN_COLWALK]),
                      ("DSH_ONLY", [IDX["d_spawn_h"]]),
                      ("CAND15", [IDX[n] for n in CAND_NAMES])]:
        mm, ff = build_final(Xtr, ytr, cols, best)
        s = ff(mm, X[ho][:, cols])
        lad[tag] = dict(auc=auc_fast(y[ho], s), n_feat=len(cols))
        lad[tag]["score"] = s
        print(f"  ladder {tag:12s} {lad[tag]['auc']:.4f}", flush=True)
    out["ladder"] = {k: dict(auc=v["auc"], n_feat=v["n_feat"]) for k, v in lad.items()}
    g_tot = a_model - a_champ
    out["dsh_share"] = dict(
        gain_total_over_champ=g_tot,
        share_alone=(lad["DSH_ONLY"]["auc"] - a_champ) / g_tot,
        share_incremental_over_base11=((lad["BASE11_DSH"]["auc"] - lad["BASE11"]["auc"]) /
                                       (lad["ALL26"]["auc"] - lad["BASE11"]["auc"])),
        share_dropcolumn=(lad["ALL26"]["auc"] - lad["MINUS_DSH"]["auc"]) / g_tot,
        share_base11dsh_vs_champ=(lad["BASE11_DSH"]["auc"] - a_champ) / g_tot)
    for k in ("BASE11_DSH", "MINUS_DSH", "BASE11", "DSH_ONLY", "FREE16"):
        b = boot_paired(y[ho], seeds[ho], lad[k]["score"], champ_ho, B=200, seed=SEED + 5)
        out["dsh_share"][f"{k}_vs_champ_ci"] = [b[0], b[1], b[2]]
    print("DSH SHARE", {k: v for k, v in out["dsh_share"].items()}, flush=True)

    # ---- GAME-LEVEL AUC (the honest unit: the label is per game)
    def game_auc(score, yy, sds):
        uq, inv = np.unique(sds, return_inverse=True)
        msum = np.bincount(inv, weights=score)
        cnt = np.bincount(inv)
        gy = np.bincount(inv, weights=yy) / cnt
        assert np.all((gy == 0) | (gy == 1))
        return auc_fast(gy > 0.5, msum / cnt), len(uq)
    ga_m, ng = game_auc(sc_ho, y[ho].astype(float), seeds[ho])
    ga_c, _ = game_auc(champ_ho, y[ho].astype(float), seeds[ho])
    ga_d, _ = game_auc(sd * X[ho][:, IDX["d_spawn_h"]].astype(float), y[ho].astype(float),
                       seeds[ho])
    out["game_level"] = dict(n_games=ng, auc_model=ga_m, auc_champ=ga_c, auc_dsh=ga_d,
                             note="mean decision score per game; label is per game")
    print("GAME LEVEL", out["game_level"], flush=True)

    # ---- BADNESS-DETECTOR TEST: target class vs STALL (both bad; only one tops out)
    st = d["stall"]
    hs = st["hold"]
    pos = ho & (y == 1)
    Xb = np.vstack([X[pos], st["X"][hs]])
    yb = np.concatenate([np.ones(pos.sum(), int), np.zeros(hs.sum(), int)])
    sb = np.concatenate([seeds[pos], st["seed"][hs]])
    scb = sfn(m, Xb)
    chb = sgn * np.concatenate([d["champ"][pos], st["champ"][hs]])
    out["badness_test"] = dict(
        n=int(len(yb)), npos=int(yb.sum()),
        auc_target_vs_stall_model=auc_fast(yb, scb),
        auc_target_vs_stall_champ=auc_fast(yb, chb),
        interpretation=("0.5 => the model separates ABOUT-TO-TOP-OUT from merely-bad; "
                        ">0.5 => it also ranks topout above stall; <0.5 => it ranks "
                        "STALL games as MORE fatal than the target class, i.e. it is a "
                        "generic board-badness detector, not a survival ruler."))
    print("BADNESS", out["badness_test"], flush=True)

    # ---- L6 within-decision flip WITH TIES
    S = d["S"]
    F = d["F"]
    out["within_decision"] = dict(
        target_class=flip_rates(S, F, m, sfn, IDX, sd, "fail", True),
        control=flip_rates(S, F, m, sfn, IDX, sd, "ctrl", False))
    print("FLIP", out["within_decision"], flush=True)

    # ---- L5 cross-generation transfer
    out["cross_generation"] = vocab2_transfer(m, sfn, names, sgn, sd, IDX)
    print("XGEN", out["cross_generation"], flush=True)

    # ---- future-encoding audit
    from scipy.stats import spearmanr
    posm = (y == 1)
    fe = {}
    for j, nm in enumerate(names):
        r = spearmanr(X[posm, j].astype(float), d["t_to_end"][posm].astype(float)).statistic
        fe[nm] = float(r)
    fe["_model_score_vs_tte_holdout"] = float(
        spearmanr(sc_ho, d["t_to_end"][ho].astype(float)).statistic)
    fe["_champ_vs_tte_holdout"] = float(
        spearmanr(champ_ho, d["t_to_end"][ho].astype(float)).statistic)
    out["future_encoding"] = fe

    with open(os.path.join(OUT, "ceiling_probe.json"), "w") as f:
        json.dump(out, f, indent=1, default=float)
    with open(os.path.join(OUT, "ceiling_best.pkl"), "wb") as f:
        pickle.dump(dict(model=m, cfg=best, names=names, sgn=sgn, sd=sd), f)
    np.savez_compressed(os.path.join(OUT, "ceiling_probe_scores.npz"),
                        y=y[ho], seeds=seeds[ho], model=sc_ho, champ=champ_ho)
    print("wrote ceiling_probe.json", time.time() - t0, flush=True)


if __name__ == "__main__":
    main()
