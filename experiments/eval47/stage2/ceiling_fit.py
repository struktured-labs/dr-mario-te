#!/usr/bin/env python3
"""STAGE 2 CEILING — unconstrained model. PLAN FROZEN IN THIS DOCSTRING BEFORE FITTING.

Subordinate to PREREG_STAGE2.md @ b9725fc; nothing here relaxes it. This measures the
CEILING only (PREREG §5 / S4): the model is deliberately OUT of the shippable class and
is NOT a silicon candidate.

MANDATORY CAVEAT on every number produced here:
  Corpus s2lulu: generating policy = shipped champion (bit-exact), environment = dr. lulu
  fitted bursty pressure, clear rate 79.80% -- BELOW the 96.9% label-quality screen.
  Labels are game outcomes broadcast onto decisions; no counterfactual attribution.

1. CONTRAST / SPLIT
   y==1 rows of s2lulu_fail (target class = dies_ahead AND end_kind==garbage_topout,
   192,611) vs ALL s2lulu_ctrl rows (168,233). Split = the shipped `hold` column
   (seed%10 in {7,8,9}), BY GAME. Hyperparameters, iteration count and every ablation are
   selected on TRAIN ONLY via an INNER by-seed fold (seed%10 in {5,6}). The holdout is
   scored ONCE per arm; the arms are declared below before fitting.

2. ARMS (declared before fitting)
   CHAMP_EVAL       comparator, never a model input: cand_vals[i, action[i]]
   GBM_ALL26        all 26 features, unconstrained GBM               <- THE CEILING
   GBM_MINUS_DSH    25 features, d_spawn_h dropped
   GBM_BASE11       the 11 champion terms only
   GBM_BASE11_DSH   11 + d_spawn_h
   DSH_ALONE        d_spawn_h alone, sign fitted on TRAIN
   GBM_FREE16       FREE_IN_COLWALK features only (no OFF_BUDGET)
   GBM_SHUF         all 26 refit on y_shuf                            <- SHUFFLED CONTROL
   GBM_LEAK_TTE     all 26 + t_to_end                       <- FUTURE-LEAK KILLED MUTANT

3. ENDPOINTS
   Primary: pooled holdout AUC(GBM_ALL26) next to AUC(CHAMP_EVAL) and the shuffled
   control, with a 95% SEED-CLUSTERED bootstrap CI (B=400, positive games and control
   games resampled separately) on the PAIRED difference.
   d_spawn_h share, both framings, neither chosen after seeing the other:
     share_alone = (AUC(DSH_ALONE)     - AUC(CHAMP_EVAL)) / (AUC(GBM_ALL26) - AUC(CHAMP_EVAL))
     share_incr  = (AUC(GBM_BASE11_DSH)- AUC(GBM_BASE11)) / (AUC(GBM_ALL26) - AUC(GBM_BASE11))
   Plus holdout permutation importance (AUC drop, 5 repeats) for all 26.
   Regime: reported at EVERY band, never pooled-only (PREREG §3.2) --
     t_to_end {<=2, 3-9, 10-30, 31-90, >90}; max_height {<=9,10-12,13-14,15-16};
     since_last_garbage deciles; viruses terciles; plus the stage-1 stratum-matched AUC
     on key (max_height, min(viruses,30)//3, min(garbage_cum,48)//8).

4. LEAK INTERROGATION -- each with the wrong input that makes it FAIL
   L1 no future-encoding inputs. KILLED MUTANT: GBM_LEAK_TTE injects t_to_end; if the
      instrument cannot see that, the instrument is vacuous.
   L2 shuffled-label floor (game-level, prereg seed 20260810, NOT re-rolled). Contrast
      against a decision-level shuffle, which is anti-conservative (stage 1 used one).
   L3 mechanism transfer (PREREG B4): score on the T_PLACE slice (end_kind==step_topout,
      0.0% BROAD-addressable, never pooled) and the stall slice.
   L4 since_last_garbage deciles (PREREG B4). Reported, not thresholded.
   L5 DIFFERENT-GENERATION CORPUS: stage-1 vocab2, pressured_drip regime, last-K=10 +
      stratum-matched extraction, restricted to seeds > 12001 so seeds are disjoint from
      s2lulu (2..12001). NO refitting.
   L6 WITHIN-DECISION sibling ranking (PREREG B3): argmax-flip vs the champion on the
      32-sibling layer, target-class holdout decisions. <2% => arm untestable (S3).

5. WHAT THIS CANNOT CONCLUDE
   AUC is a proxy; proxies rule OUT only. Nothing here is a GO. The lane's deliverable
   remains the §6.3 paired rollout.
"""
from __future__ import annotations

import json
import os
import sys
import time

import numpy as np

os.environ.setdefault("OMP_NUM_THREADS", "6")
os.environ.setdefault("OPENBLAS_NUM_THREADS", "6")

from sklearn.ensemble import HistGradientBoostingClassifier  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
QA = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
RES = os.path.join(HERE, "results")
VOC = os.path.join(HERE, "..", "vocab2")
OUT = os.path.join(QA, "tmp", "stage2_ceiling")
os.makedirs(OUT, exist_ok=True)

SEED = 20260810
B_BOOT = 400
HOLD_MOD = (7, 8, 9)
INNER_MOD = (5, 6)

NAMES11 = ["MAXH", "HOLES", "TOPRISK", "SPAWN", "SETUP", "MATCHED", "BURIED",
           "RDYEXT", "VRDY", "CROSS", "POLL"]
FREE_IN_COLWALK = ["HOLES", "MAXH", "SPAWN", "TOPRISK", "a_d_maxh", "a_topout_dist",
                   "b_spawn_prox", "b_spawn_prox_strict", "c_d_nlegal", "c_nlegal_probe",
                   "d_crit_cols", "d_gvuln_mass", "d_spawn_h", "e_escape_routes",
                   "x_hvar", "x_jagged"]

GBM_KW = dict(max_iter=500, learning_rate=0.06, max_leaf_nodes=31, min_samples_leaf=50,
              l2_regularization=1.0, max_bins=255, early_stopping=False,
              random_state=SEED)


# ---------------------------------------------------------------- AUC utilities
def auc_fast(y, s, w=None):
    """Weighted AUC by rank; ties get 0.5 credit. w = per-row nonneg weights."""
    y = np.asarray(y, bool)
    s = np.asarray(s, np.float64)
    if w is None:
        w = np.ones(len(s))
    o = np.argsort(s, kind="mergesort")
    s, y, w = s[o], y[o], w[o]
    # dense rank groups over equal scores
    newg = np.empty(len(s), bool)
    newg[0] = True
    newg[1:] = s[1:] != s[:-1]
    gid = np.cumsum(newg) - 1
    pw = np.bincount(gid, weights=w * y)
    nw = np.bincount(gid, weights=w * (~y))
    ncum = np.concatenate(([0.0], np.cumsum(nw)[:-1]))
    P, N = pw.sum(), nw.sum()
    if P <= 0 or N <= 0:
        return float("nan")
    return float(np.sum(pw * (ncum + 0.5 * nw)) / (P * N))


def strat_auc(strata, y, s):
    """Positive-weight-weighted mean of within-stratum AUC (stage-1 machinery, w=1)."""
    y = np.asarray(y, bool)
    order = np.lexsort((s, strata))
    st, x, yy = strata[order], s[order], y[order]
    newg = np.empty(len(st), bool)
    newg[0] = True
    newg[1:] = (st[1:] != st[:-1]) | (x[1:] != x[:-1])
    uid = np.cumsum(newg) - 1
    su = st[newg]
    news = np.empty(len(su), bool)
    news[0] = True
    news[1:] = su[1:] != su[:-1]
    sid = np.cumsum(news) - 1
    pw = np.bincount(uid, weights=yy.astype(float))
    nw = np.bincount(uid, weights=(~yy).astype(float))
    ccum = np.cumsum(nw)
    below = np.concatenate(([0.0], ccum[:-1]))
    below = below - below[news][sid]
    num = np.bincount(sid, weights=pw * (below + 0.5 * nw))
    P = np.bincount(sid, weights=pw)
    N = np.bincount(sid, weights=nw)
    use = (P > 0) & (N > 0)
    if not use.any():
        return float("nan"), 0
    a = num[use] / (P[use] * N[use])
    return float(np.sum(P[use] * a) / np.sum(P[use])), int(use.sum())


def boot_paired(y, seeds, sa, sb, B=B_BOOT, seed=SEED):
    """Cluster bootstrap on the PAIRED AUC difference; positives and negatives resampled
    separately (stage-1 boot_weights, unchanged in spirit)."""
    rng = np.random.default_rng(seed)
    y = np.asarray(y, bool)
    idxs = {}
    for cls in (True, False):
        m = np.flatnonzero(y == cls)
        uq, inv = np.unique(seeds[m], return_inverse=True)
        idxs[cls] = (m, uq, inv)
    d = np.empty(B)
    aa = np.empty(B)
    bb = np.empty(B)
    for b in range(B):
        w = np.zeros(len(y))
        for cls in (True, False):
            m, uq, inv = idxs[cls]
            draw = rng.integers(0, len(uq), len(uq))
            cnt = np.bincount(draw, minlength=len(uq)).astype(np.float64)
            w[m] = cnt[inv]
        A = auc_fast(y, sa, w)
        Bv = auc_fast(y, sb, w)
        aa[b], bb[b], d[b] = A, Bv, A - Bv
    return (float(d.mean()), float(np.percentile(d, 2.5)), float(np.percentile(d, 97.5)),
            float((d > 0).mean()), float(aa.mean()), float(bb.mean()))


# ---------------------------------------------------------------- data
def load():
    F = np.load(os.path.join(RES, "s2lulu_fail_local.npz"))
    C = np.load(os.path.join(RES, "s2lulu_ctrl_local.npz"))
    S = np.load(os.path.join(RES, "s2feat_local.npz"))
    T = np.load(os.path.join(RES, "s2lulu_stall_local.npz"))
    names = [str(x) for x in S["feat_names"]]
    d = {}
    mf = F["y"] == 1                       # target class only
    d["names"] = names
    d["X"] = np.vstack([S["fail_feat"][mf], S["ctrl_feat"]]).astype(np.float32)
    d["y"] = np.concatenate([np.ones(mf.sum(), np.int8), np.zeros(len(C["y"]), np.int8)])
    d["yshuf"] = np.concatenate([F["y_shuf"][mf], C["y_shuf"]]).astype(np.int8)
    d["seed"] = np.concatenate([F["seed"][mf], C["seed"]])
    d["hold"] = np.concatenate([F["hold"][mf], C["hold"]]).astype(bool)
    d["champ"] = np.concatenate([S["fail_champ_eval"][mf], S["ctrl_champ_eval"]]).astype(np.float64)
    for k in ("t_to_end", "max_height", "viruses", "garbage_cum", "since_last_garbage",
              "pill_idx", "occ", "n_legal"):
        d[k] = np.concatenate([F[k][mf], C[k]]).astype(np.int32)
    # T_PLACE slice (never pooled into the primary contrast)
    mp = (F["y"] == -1) & (F["end_kind"] == 3) & (F["dies_ahead"] == 1)
    d["tplace"] = dict(X=S["fail_feat"][mp].astype(np.float32), seed=F["seed"][mp],
                       hold=F["hold"][mp].astype(bool),
                       champ=S["fail_champ_eval"][mp].astype(np.float64),
                       t_to_end=F["t_to_end"][mp].astype(np.int32),
                       max_height=F["max_height"][mp].astype(np.int32),
                       viruses=F["viruses"][mp].astype(np.int32),
                       garbage_cum=F["garbage_cum"][mp].astype(np.int32))
    Sst = np.load(os.path.join(RES, "s2feat_local.npz"))
    d["stall"] = dict(X=Sst["stall_feat"].astype(np.float32), seed=T["seed"],
                      hold=T["hold"].astype(bool),
                      champ=Sst["stall_champ_eval"].astype(np.float64),
                      t_to_end=T["t_to_end"].astype(np.int32),
                      max_height=T["max_height"].astype(np.int32),
                      viruses=T["viruses"].astype(np.int32),
                      garbage_cum=T["garbage_cum"].astype(np.int32))
    d["ctrl_only"] = dict(X=S["ctrl_feat"].astype(np.float32), seed=C["seed"],
                          hold=C["hold"].astype(bool),
                          champ=S["ctrl_champ_eval"].astype(np.float64),
                          t_to_end=C["t_to_end"].astype(np.int32),
                          max_height=C["max_height"].astype(np.int32),
                          viruses=C["viruses"].astype(np.int32),
                          garbage_cum=C["garbage_cum"].astype(np.int32))
    d["S"] = S
    d["F"] = F
    return d


def fit_arm(X, y, cols, n_iter, kw=None):
    kw = dict(GBM_KW if kw is None else kw)
    kw["max_iter"] = n_iter
    m = HistGradientBoostingClassifier(**kw)
    m.fit(X[:, cols], y)
    return m


def pick_iters(Xtr, ytr, inner, cols, grid=(100, 200, 300, 500, 800)):
    """Iteration count chosen on the INNER by-seed fold, never on holdout."""
    best, best_a = grid[0], -1.0
    m = HistGradientBoostingClassifier(**{**GBM_KW, "max_iter": max(grid)})
    m.fit(Xtr[~inner][:, cols], ytr[~inner])
    stages = list(m.staged_decision_function(Xtr[inner][:, cols]))
    for g in grid:
        a = auc_fast(ytr[inner], stages[g - 1].ravel())
        if a > best_a:
            best_a, best = a, g
    return best, best_a


def main():
    t0 = time.time()
    d = load()
    names = d["names"]
    X, y, seeds, hold = d["X"], d["y"].astype(int), d["seed"], d["hold"]
    tr, ho = ~hold, hold
    inner = np.isin(seeds[tr] % 10, INNER_MOD)
    assert not (set(np.unique(seeds[tr])) & set(np.unique(seeds[ho]))), "SEED LEAK"
    out = {"caveat": ("Corpus s2lulu: generating policy = shipped champion (bit-exact), "
                      "environment = dr. lulu fitted bursty pressure, clear rate 79.80% "
                      "-- BELOW the 96.9% label-quality screen. Labels are game outcomes "
                      "broadcast onto decisions; no counterfactual attribution."),
           "prereg": "PREREG_STAGE2.md @ b9725fc", "plan": "ceiling_fit.py docstring"}
    out["n"] = dict(rows=int(len(y)), train=int(tr.sum()), holdout=int(ho.sum()),
                    pos=int(y.sum()), neg=int((y == 0).sum()),
                    train_games=int(len(np.unique(seeds[tr]))),
                    holdout_games=int(len(np.unique(seeds[ho]))),
                    holdout_pos_games=int(len(np.unique(seeds[ho & (y == 1)]))),
                    holdout_neg_games=int(len(np.unique(seeds[ho & (y == 0)]))))
    print("rows", out["n"], flush=True)

    ALL = list(range(26))
    IDX = {n: i for i, n in enumerate(names)}
    sets = {
        "GBM_ALL26": ALL,
        "GBM_MINUS_DSH": [i for i in ALL if names[i] != "d_spawn_h"],
        "GBM_BASE11": [IDX[n] for n in NAMES11],
        "GBM_BASE11_DSH": [IDX[n] for n in NAMES11] + [IDX["d_spawn_h"]],
        "GBM_FREE16": [IDX[n] for n in FREE_IN_COLWALK],
    }

    models, res = {}, {}
    ytr = y[tr]
    Xtr = X[tr]
    for k, cols in sets.items():
        it, ia = pick_iters(Xtr, ytr, inner, cols)
        m = fit_arm(Xtr, ytr, cols, it)
        sc = m.decision_function(X[ho][:, cols])
        models[k] = (m, cols)
        res[k] = dict(n_iter=it, inner_auc=ia,
                      holdout_auc=auc_fast(y[ho], sc),
                      train_auc=auc_fast(ytr, m.decision_function(Xtr[:, cols])))
        res[k]["score"] = sc
        print(f"{k:16s} iters={it:4d} inner={ia:.4f} hold={res[k]['holdout_auc']:.4f}",
              flush=True)

    # CHAMP_EVAL comparator: orient sign on TRAIN only (higher champ value => safer)
    sgn = 1.0 if auc_fast(ytr, d["champ"][tr]) >= 0.5 else -1.0
    champ_sc = sgn * d["champ"]
    res["CHAMP_EVAL"] = dict(sign=sgn, holdout_auc=auc_fast(y[ho], champ_sc[ho]),
                             train_auc=auc_fast(ytr, champ_sc[tr]), score=champ_sc[ho])

    # DSH_ALONE: sign fitted on TRAIN
    dsh = X[:, IDX["d_spawn_h"]].astype(np.float64)
    sd = 1.0 if auc_fast(ytr, dsh[tr]) >= 0.5 else -1.0
    res["DSH_ALONE"] = dict(sign=sd, holdout_auc=auc_fast(y[ho], sd * dsh[ho]),
                            train_auc=auc_fast(ytr, sd * dsh[tr]), score=sd * dsh[ho])
    # SPAWN alone (the champion's clipped sensor), for the same comparison stage 1 made
    sp = X[:, IDX["SPAWN"]].astype(np.float64)
    ss = 1.0 if auc_fast(ytr, sp[tr]) >= 0.5 else -1.0
    res["SPAWN_ALONE"] = dict(sign=ss, holdout_auc=auc_fast(y[ho], ss * sp[ho]),
                              score=ss * sp[ho])

    # SHUFFLED CONTROL (game-level, prereg seed, NOT re-rolled)
    ysh = d["yshuf"].astype(int)
    it, ia = pick_iters(Xtr, ysh[tr], inner, ALL)
    msh = fit_arm(Xtr, ysh[tr], ALL, it)
    ssh = msh.decision_function(X[ho][:, ALL])
    res["GBM_SHUF"] = dict(n_iter=it, inner_auc=ia,
                           holdout_auc_vs_yshuf=auc_fast(ysh[ho], ssh),
                           holdout_auc_vs_y=auc_fast(y[ho], ssh),
                           train_auc_vs_yshuf=auc_fast(ysh[tr], msh.decision_function(Xtr)))
    print("GBM_SHUF", {k: v for k, v in res["GBM_SHUF"].items()}, flush=True)

    # decision-level shuffle (anti-conservative; reported for contrast, stage 1 used one)
    rngd = np.random.default_rng(SEED + 1)
    ydec = y.copy()
    ydec[tr] = rngd.permutation(ydec[tr])
    ydec[ho] = rngd.permutation(ydec[ho])
    mdec = fit_arm(Xtr, ydec[tr], ALL, 300)
    res["GBM_SHUF_DECISIONLEVEL"] = dict(
        holdout_auc_vs_ydec=auc_fast(ydec[ho], mdec.decision_function(X[ho])),
        holdout_auc_vs_y=auc_fast(y[ho], mdec.decision_function(X[ho])))

    # FUTURE-LEAK KILLED MUTANT: t_to_end injected as a 27th feature
    Xl = np.column_stack([X, d["t_to_end"].astype(np.float32)])
    itl, ial = pick_iters(Xl[tr], ytr, inner, list(range(27)))
    ml = fit_arm(Xl[tr], ytr, list(range(27)), itl)
    sl = ml.decision_function(Xl[ho])
    res["GBM_LEAK_TTE"] = dict(n_iter=itl, holdout_auc=auc_fast(y[ho], sl),
                               tte_alone_auc=auc_fast(y[ho], -d["t_to_end"][ho].astype(float)))
    print("GBM_LEAK_TTE", res["GBM_LEAK_TTE"], flush=True)

    # ------------------------------------------------ primary paired bootstrap
    main_sc = res["GBM_ALL26"]["score"]
    bp = boot_paired(y[ho], seeds[ho], main_sc, res["CHAMP_EVAL"]["score"])
    out["primary"] = dict(
        auc_model=res["GBM_ALL26"]["holdout_auc"],
        auc_champ=res["CHAMP_EVAL"]["holdout_auc"],
        auc_shuffled_vs_yshuf=res["GBM_SHUF"]["holdout_auc_vs_yshuf"],
        auc_shuffled_vs_y=res["GBM_SHUF"]["holdout_auc_vs_y"],
        paired_diff_mean=bp[0], ci_lo=bp[1], ci_hi=bp[2], frac_reps_positive=bp[3],
        B=B_BOOT)
    print("PRIMARY", out["primary"], flush=True)

    # d_spawn_h vs champ, paired
    bd = boot_paired(y[ho], seeds[ho], res["DSH_ALONE"]["score"], res["CHAMP_EVAL"]["score"])
    out["dsh_vs_champ"] = dict(diff=bd[0], ci_lo=bd[1], ci_hi=bd[2], frac_pos=bd[3])
    bm = boot_paired(y[ho], seeds[ho], main_sc, res["DSH_ALONE"]["score"])
    out["model_vs_dsh"] = dict(diff=bm[0], ci_lo=bm[1], ci_hi=bm[2], frac_pos=bm[3])
    bb11 = boot_paired(y[ho], seeds[ho], res["GBM_BASE11_DSH"]["score"],
                       res["GBM_BASE11"]["score"])
    out["base11dsh_vs_base11"] = dict(diff=bb11[0], ci_lo=bb11[1], ci_hi=bb11[2],
                                      frac_pos=bb11[3])
    bmd = boot_paired(y[ho], seeds[ho], main_sc, res["GBM_MINUS_DSH"]["score"])
    out["all26_vs_minusdsh"] = dict(diff=bmd[0], ci_lo=bmd[1], ci_hi=bmd[2],
                                    frac_pos=bmd[3])

    A = {k: (res[k]["holdout_auc"] if "holdout_auc" in res[k] else None) for k in res}
    out["arms"] = {k: {kk: vv for kk, vv in v.items() if kk != "score"} for k, v in res.items()}
    g_tot = A["GBM_ALL26"] - A["CHAMP_EVAL"]
    out["dsh_share"] = dict(
        share_alone=(A["DSH_ALONE"] - A["CHAMP_EVAL"]) / g_tot,
        share_incr=((A["GBM_BASE11_DSH"] - A["GBM_BASE11"]) /
                    (A["GBM_ALL26"] - A["GBM_BASE11"])),
        share_dropcol=((A["GBM_ALL26"] - A["GBM_MINUS_DSH"]) / g_tot),
        gain_total=g_tot,
        auc_dsh=A["DSH_ALONE"], auc_spawn=res["SPAWN_ALONE"]["holdout_auc"],
        auc_champ=A["CHAMP_EVAL"], auc_all26=A["GBM_ALL26"],
        auc_base11=A["GBM_BASE11"], auc_base11_dsh=A["GBM_BASE11_DSH"],
        auc_minus_dsh=A["GBM_MINUS_DSH"], auc_free16=A["GBM_FREE16"])
    print("DSH SHARE", out["dsh_share"], flush=True)

    # ------------------------------------------------ permutation importance (holdout)
    m26, c26 = models["GBM_ALL26"]
    base = A["GBM_ALL26"]
    rng = np.random.default_rng(SEED + 7)
    Xho = X[ho].copy()
    imp = {}
    for j, nm in enumerate(names):
        drops = []
        col = Xho[:, j].copy()
        for r in range(5):
            Xho[:, j] = col[rng.permutation(len(col))]
            drops.append(base - auc_fast(y[ho], m26.decision_function(Xho)))
        Xho[:, j] = col
        imp[nm] = dict(mean_auc_drop=float(np.mean(drops)), sd=float(np.std(drops)))
    out["perm_importance"] = imp
    print("PERM IMP top:", sorted(imp.items(), key=lambda kv: -kv[1]["mean_auc_drop"])[:8],
          flush=True)

    # ------------------------------------------------ regime breakdown
    def bands(vals, edges, labels):
        b = np.digitize(vals, edges)
        return [(labels[i], b == i) for i in range(len(labels))]

    reg = {}
    tte = d["t_to_end"][ho]
    mh = d["max_height"][ho]
    slg = d["since_last_garbage"][ho]
    vir = d["viruses"][ho]
    yh = y[ho]
    chh = res["CHAMP_EVAL"]["score"]
    dsh_h = res["DSH_ALONE"]["score"]

    def cell(mask):
        if mask.sum() < 50 or yh[mask].sum() == 0 or (yh[mask] == 0).sum() == 0:
            return None
        return dict(n=int(mask.sum()), npos=int(yh[mask].sum()),
                    auc_model=auc_fast(yh[mask], main_sc[mask]),
                    auc_champ=auc_fast(yh[mask], chh[mask]),
                    auc_dsh=auc_fast(yh[mask], dsh_h[mask]),
                    auc_base11=auc_fast(yh[mask], res["GBM_BASE11"]["score"][mask]))

    reg["t_to_end"] = {}
    for lab, m in [("<=2", tte <= 2), ("3-9", (tte >= 3) & (tte <= 9)),
                   ("10-30", (tte >= 10) & (tte <= 30)),
                   ("31-90", (tte >= 31) & (tte <= 90)), (">90", tte > 90)]:
        reg["t_to_end"][lab] = cell(m)
    reg["max_height"] = {}
    for lab, m in [("h<=9", mh <= 9), ("h10-12", (mh >= 10) & (mh <= 12)),
                   ("h13-14", (mh >= 13) & (mh <= 14)), ("h15-16", mh >= 15)]:
        reg["max_height"][lab] = cell(m)
    reg["viruses"] = {}
    for lab, m in [("v<=8", vir <= 8), ("v9-24", (vir >= 9) & (vir <= 24)),
                   ("v>24", vir > 24)]:
        reg["viruses"][lab] = cell(m)
    # pressured vs clean
    reg["pressure"] = {}
    for lab, m in [("clean(no garbage yet)", d["garbage_cum"][ho] == 0),
                   ("pressured(garbage seen)", d["garbage_cum"][ho] > 0),
                   ("fresh volley slg<=3", slg <= 3),
                   ("slg 4-12", (slg >= 4) & (slg <= 12)),
                   ("slg>12", slg > 12)]:
        reg["pressure"][lab] = cell(m)
    # since_last_garbage deciles (B4)
    q = np.quantile(slg, np.linspace(0, 1, 11))
    reg["slg_deciles"] = {}
    for i in range(10):
        lo, hi = q[i], q[i + 1]
        m = (slg >= lo) & (slg <= hi) if i == 9 else (slg >= lo) & (slg < hi)
        reg["slg_deciles"][f"d{i+1}[{lo:.0f},{hi:.0f}]"] = cell(m)
    out["regime"] = reg

    # stratum-matched AUC (stage-1 key)
    key = (mh.astype(np.int64) * 10000
           + np.minimum(vir, 30) // 3 * 100
           + np.minimum(d["garbage_cum"][ho], 48) // 8)
    sm, ns = strat_auc(key, yh, main_sc)
    sc_, _ = strat_auc(key, yh, chh)
    sdh_, _ = strat_auc(key, yh, dsh_h)
    out["stratified"] = dict(key="(max_height, min(vir,30)//3, min(gcum,48)//8)",
                             n_strata=ns, auc_model=sm, auc_champ=sc_, auc_dsh=sdh_)
    print("STRAT", out["stratified"], flush=True)

    # ------------------------------------------------ L3 mechanism transfer
    def other_vs_ctrl(slice_d, label):
        C = d["ctrl_only"]
        hm = slice_d["hold"]
        hc = C["hold"]
        Xs = np.vstack([slice_d["X"][hm], C["X"][hc]])
        ys = np.concatenate([np.ones(hm.sum(), int), np.zeros(hc.sum(), int)])
        ch = np.concatenate([slice_d["champ"][hm], C["champ"][hc]]) * sgn
        sc = m26.decision_function(Xs)
        sd_ = sd * Xs[:, IDX["d_spawn_h"]].astype(np.float64)
        sds = np.concatenate([slice_d["seed"][hm], C["seed"][hc]])
        bpx = boot_paired(ys.astype(bool), sds, sc, ch, B=200, seed=SEED + 3)
        return dict(label=label, n=int(len(ys)), npos=int(ys.sum()),
                    auc_model=auc_fast(ys, sc), auc_champ=auc_fast(ys, ch),
                    auc_dsh=auc_fast(ys, sd_), paired_diff=bpx[0],
                    ci_lo=bpx[1], ci_hi=bpx[2])

    out["mechanism_transfer"] = dict(
        T_PLACE=other_vs_ctrl(d["tplace"], "step_topout dies-ahead vs cleared"),
        STALL=other_vs_ctrl(d["stall"], "stall (T_TRUNC) vs cleared -- provably vacuous target"))
    print("MECH", out["mechanism_transfer"], flush=True)

    # ------------------------------------------------ L6 within-decision sibling flip
    S = d["S"]
    fl = {}
    for part in ("fail", "ctrl"):
        Xa = S[f"all32_{part}_feat"].astype(np.float32)
        ok = S[f"all32_{part}_ok"].astype(bool)
        act = S[f"all32_{part}_action"].astype(int)
        hb = S[f"all32_{part}_hold"].astype(bool)
        ridx = S[f"all32_{part}_rowidx"]
        n, k, p = Xa.shape
        flat = Xa.reshape(n * k, p)
        sc = m26.decision_function(flat).reshape(n, k)
        dshv = sd * flat[:, IDX["d_spawn_h"]].astype(np.float64).reshape(n, k)
        sc[~ok] = -np.inf
        dshv[~ok] = -np.inf
        # model prefers LOW risk => model score is P(fatal); pick argmin of risk
        pick = np.argmin(np.where(ok, m26.decision_function(flat).reshape(n, k), np.inf), axis=1)
        pick_dsh = np.argmin(np.where(ok, -dshv, np.inf), axis=1)
        sub = hb if part == "ctrl" else hb
        # target-class subset for the fail part
        if part == "fail":
            yr = d["F"]["y"][ridx] == 1
            sub = hb & yr
        fl[part] = dict(n=int(sub.sum()),
                        argmax_flip_model=float((pick[sub] != act[sub]).mean()),
                        argmax_flip_dsh=float((pick_dsh[sub] != act[sub]).mean()))
    out["within_decision"] = fl
    print("WITHIN", fl, flush=True)

    np.savez_compressed(os.path.join(OUT, "ceiling_scores.npz"),
                        y=y[ho], seeds=seeds[ho], model=main_sc,
                        champ=res["CHAMP_EVAL"]["score"], dsh=res["DSH_ALONE"]["score"],
                        base11=res["GBM_BASE11"]["score"], tte=tte, mh=mh, slg=slg,
                        vir=vir)
    import pickle
    with open(os.path.join(OUT, "m26.pkl"), "wb") as f:
        pickle.dump(dict(model=m26, names=names, sign_champ=sgn, sign_dsh=sd), f)
    out["seconds"] = time.time() - t0
    with open(os.path.join(OUT, "ceiling_result.json"), "w") as f:
        json.dump(out, f, indent=1, default=float)
    print("wrote", os.path.join(OUT, "ceiling_result.json"), out["seconds"], flush=True)


if __name__ == "__main__":
    main()
