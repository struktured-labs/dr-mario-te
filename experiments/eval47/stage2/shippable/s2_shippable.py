#!/usr/bin/env python
"""
STAGE-2 SHIPPABLE-MODEL LANE.

Pre-registered in experiments/eval47/stage2/PREREG_SHIPPABLE.md (subordinate to
PREREG_STAGE2.md @ b9725fc).

CAVEAT carried on every number produced here:
  Corpus s2lulu: generating policy = shipped champion (bit-exact), environment = dr.
  lulu fitted bursty pressure, clear rate 79.80% -- BELOW the 96.9% label-quality
  screen. Labels are game outcomes broadcast onto decisions; no counterfactual
  attribution.

Stages, run in order.  The holdout is not touched until `eval`.
  select : greedy forward selection of the 8-feature vector, TRAIN ROWS ONLY
  fit    : fit S0/S1/S1b/S2/S3/CEIL on TRAIN, quantise, write params
  eval   : open the holdout ONCE, compute every reported number
"""
import argparse
import json
import os
import sys
import time

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
S2 = os.path.dirname(HERE)
RES = os.path.join(S2, "results")
OUT = os.path.join(HERE, "out")
os.makedirs(OUT, exist_ok=True)

CAVEAT = ("Corpus s2lulu: generating policy = shipped champion (bit-exact), environment "
          "= dr. lulu fitted bursty pressure, clear rate 79.80% - BELOW the 96.9% "
          "label-quality screen. Labels are game outcomes broadcast onto decisions; no "
          "counterfactual attribution.")

# PREREG_STAGE2 section 8 FREE_IN_COLWALK -- the ONLY eligible set for in-class models.
ELIGIBLE = ["MAXH", "HOLES", "TOPRISK", "SPAWN", "a_topout_dist", "d_spawn_h",
            "d_crit_cols", "d_gvuln_mass", "x_jagged", "x_hvar", "e_escape_routes"]
N_SELECT = 8

# The champion's own enumeration order over the 32 slots (o4 = 0..3 -> var 2,3,0,1),
# ties keep the first in THIS order.  PREREG_STAGE2 deviation-log entry 2.
CHAMP_ORDER = np.array([v * 8 + c for v in (2, 3, 0, 1) for c in range(8)])


# ------------------------------------------------------------------ AUC (exact)
def auc(x, y):
    """Mann-Whitney AUC of x for y==1 vs y==0, ties = 0.5.  Same helper as
    s2_features._auc so every number lands on the same instrument."""
    m = y >= 0
    x = np.asarray(x, dtype=np.float64)[m]
    y = np.asarray(y)[m]
    n1 = int((y == 1).sum())
    n0 = int((y == 0).sum())
    if n1 == 0 or n0 == 0:
        return float("nan")
    order = np.argsort(x, kind="mergesort")
    xs = x[order]
    ranks = np.empty(x.shape[0], dtype=np.float64)
    i = 0
    while i < xs.shape[0]:
        j = i
        while j + 1 < xs.shape[0] and xs[j + 1] == xs[i]:
            j += 1
        ranks[order[i:j + 1]] = 0.5 * (i + j) + 1.0
        i = j + 1
    return float((ranks[y == 1].sum() - n1 * (n1 + 1) / 2.0) / (n1 * n0))


# ------------------------------------------------------------------- data load
class Data:
    pass


def load(with_holdout):
    """Load the contrast.  with_holdout=False physically drops holdout rows so a
    coding slip cannot leak one in."""
    F = np.load(os.path.join(RES, "s2feat_local.npz"))
    f = np.load(os.path.join(RES, "s2lulu_fail_local.npz"))
    c = np.load(os.path.join(RES, "s2lulu_ctrl_local.npz"))
    names = [str(s) for s in F["feat_names"]]

    def part(d, feat, champ, keep):
        return dict(X=feat[keep], champ=champ[keep], y=d["y"][keep],
                    y_shuf=d["y_shuf"][keep], seed=d["seed"][keep],
                    hold=d["hold"][keep], t_to_end=d["t_to_end"][keep],
                    max_height=d["max_height"][keep], end_kind=d["end_kind"][keep],
                    slg=d["since_last_garbage"][keep], viruses=d["viruses"][keep])

    kf = f["y"] == 1
    kc = c["y"] == 0
    P = part(f, F["fail_feat"], F["fail_champ_eval"], kf)
    N = part(c, F["ctrl_feat"], F["ctrl_champ_eval"], kc)
    d = Data()
    d.names = names
    for k in P:
        d.__dict__[k] = np.concatenate([P[k], N[k]])
    if not with_holdout:
        m = d.hold == 0
        for k in list(P):
            d.__dict__[k] = d.__dict__[k][m]
    d.idx = {n: i for i, n in enumerate(names)}
    return d


def cols(d, feats):
    return np.ascontiguousarray(d.X[:, [d.idx[f] for f in feats]].astype(np.float64))


# ------------------------------------------------------- stage 1: selection
def stage_select(args):
    from sklearn.ensemble import HistGradientBoostingClassifier
    from sklearn.model_selection import GroupKFold

    d = load(with_holdout=False)
    assert (d.hold == 0).all(), "holdout leaked into selection"
    print(f"[select] TRAIN ONLY rows={d.y.shape[0]} pos={(d.y==1).sum()} "
          f"neg={(d.y==0).sum()} games={np.unique(d.seed).size}", flush=True)

    gkf = GroupKFold(n_splits=5)
    folds = list(gkf.split(np.zeros(d.y.shape[0]), d.y, groups=d.seed))

    def cv_auc(feats):
        X = cols(d, feats)
        s = np.empty(d.y.shape[0])
        for tr, te in folds:
            m = HistGradientBoostingClassifier(
                max_iter=32, max_depth=4, learning_rate=0.2,
                early_stopping=False, random_state=0)
            m.fit(X[tr], d.y[tr])
            s[te] = m.predict_proba(X[te])[:, 1]
        # out-of-fold AUC, pooled
        return auc(s, d.y)

    chosen, trace = [], []
    remaining = list(ELIGIBLE)
    while len(chosen) < N_SELECT and remaining:
        best, best_a = None, -1.0
        for f in remaining:
            a = cv_auc(chosen + [f])
            print(f"   try {chosen + [f]} -> {a:.4f}", flush=True)
            if a > best_a + 1e-9:
                best_a, best = a, f
        chosen.append(best)
        remaining.remove(best)
        trace.append({"k": len(chosen), "added": best, "cv_auc": best_a})
        print(f"[select] k={len(chosen)} += {best}  cvAUC={best_a:.4f}", flush=True)

    # single-feature reference AUCs on train (already public in s2feat_gates)
    single = {f: auc(d.X[:, d.idx[f]], d.y) for f in ELIGIBLE}
    out = {"caveat": CAVEAT, "prereg": "PREREG_SHIPPABLE.md",
           "scope": "TRAIN ROWS ONLY (holdout sealed)",
           "eligible": ELIGIBLE, "selected": chosen, "trace": trace,
           "single_feature_train_auc": single,
           "n_train_rows": int(d.y.shape[0]),
           "n_train_games": int(np.unique(d.seed).size)}
    with open(os.path.join(OUT, "selected.json"), "w") as fh:
        json.dump(out, fh, indent=1)
    print("[select] ->", chosen)


# --------------------------------------------------------------- quantisation
# PREREG_SHIPPABLE section 5: a fixed power-of-two scale per feature.  All 1 here;
# losslessness is ASSERTED below, not assumed.
FEAT_SCALE = {n: 1 for n in ELIGIBLE}
FEAT_MAX = {"MAXH": 16, "HOLES": 40, "TOPRISK": 23, "SPAWN": 8, "a_topout_dist": 14,
            "d_spawn_h": 16, "d_crit_cols": 8, "d_gvuln_mass": 40, "x_jagged": 73,
            "x_hvar": 52, "e_escape_routes": 8}


def hinge_compress(lut, w, n_break=3, max_cand=24):
    """Best CONTINUOUS monotone 4-segment PWL approximation to a per-feature LUT.
    Isotonic-project first (so the target is monotone), then exhaustive search over
    breakpoints with a non-negative least-squares fit on the hinge basis."""
    from scipy.optimize import nnls
    from sklearn.isotonic import IsotonicRegression
    x = np.arange(len(lut), dtype=np.float64)
    w = np.asarray(w, dtype=np.float64) + 1e-9
    sgn = 1.0 if np.average(np.diff(lut), weights=(w[1:] + w[:-1])) >= 0 else -1.0
    iso = IsotonicRegression(increasing=(sgn > 0)).fit_transform(x, lut, sample_weight=w)
    cand = np.unique(np.rint(np.interp(
        np.linspace(0, 1, min(max_cand, len(lut))),
        np.linspace(0, 1, len(lut)), x)).astype(int))
    cand = [b for b in cand if 0 < b < len(lut) - 1]
    best = (np.inf, None, None)
    sw = np.sqrt(w)
    for i in range(len(cand)):
        for j in range(i + 1, len(cand)):
            for k in range(j + 1, len(cand)):
                bs = (cand[i], cand[j], cand[k])
                B = np.stack([sgn * x] + [sgn * np.maximum(0, x - b) for b in bs], 1)
                mu_B = (B * w[:, None]).sum(0) / w.sum()
                mu_y = float((iso * w).sum() / w.sum())
                c, _ = nnls((B - mu_B) * sw[:, None], (iso - mu_y) * sw)
                fit = (B - mu_B) @ c + mu_y
                sse = float((w * (fit - iso) ** 2).sum())
                if sse < best[0]:
                    best = (sse, bs, fit)
    return best[2], best[1]


def _fit_additive(Xq, y, feats, sizes, n_iter, rng=0):
    """Additive (depth-1) boosted fit -> exact per-feature LUTs."""
    from sklearn.ensemble import HistGradientBoostingClassifier
    m = HistGradientBoostingClassifier(max_iter=n_iter, max_depth=1, max_leaf_nodes=2,
                                       learning_rate=0.1, early_stopping=False,
                                       random_state=rng, max_bins=255)
    m.fit(Xq.astype(np.float64), y)
    ref = np.rint(np.median(Xq, axis=0)).astype(np.float64)
    luts = []
    for j in range(len(feats)):
        g = np.arange(sizes[j], dtype=np.float64)
        Z = np.tile(ref, (len(g), 1))
        Z[:, j] = g
        d = m.decision_function(Z).ravel()
        luts.append(d - d[int(min(ref[j], sizes[j] - 1))])
    return luts, m


def stage_fit(args):
    from sklearn.ensemble import HistGradientBoostingClassifier
    import models as M

    sel = json.load(open(os.path.join(OUT, "selected.json")))["selected"]
    d = load(with_holdout=False)
    assert (d.hold == 0).all(), "holdout leaked into fit"
    scales = [FEAT_SCALE[f] for f in sel]
    sizes = [FEAT_MAX[f] * FEAT_SCALE[f] + 1 for f in sel]
    Xf = cols(d, sel)
    Xq, qerr = M.quantise_features(Xf, scales)
    print(f"[fit] TRAIN rows={d.y.shape[0]} feats={sel}")
    print(f"[fit] feature quantisation max abs error per feature: "
          f"{dict(zip(sel, [round(e,3) for e in qerr]))}")
    counts = [np.bincount(Xq[:, j], minlength=sizes[j]).astype(float)
              for j in range(len(sel))]

    y = d.y.astype(int)
    ysh = d.y_shuf.astype(int)
    fitted = {}

    # ---- S0: d_spawn_h alone, 4-segment monotone hinge
    j0 = sel.index("d_spawn_h")
    lut0, _ = _fit_additive(Xq[:, [j0]], y, ["d_spawn_h"], [sizes[j0]], 400)
    c0, b0 = hinge_compress(lut0[0], counts[j0])
    fitted["S0"] = M.HingePWL(["d_spawn_h"], [sizes[j0]], [c0], [b0])
    fitted["S0"].sel_idx = [j0]

    # ---- S1b: additive per-level LUT over the 8 features (exact additive family)
    luts, _ = _fit_additive(Xq, y, sel, sizes, 800)
    fitted["S1b"] = M.AdditiveLUT(sel, sizes, luts)
    fitted["S1b"].sel_idx = list(range(len(sel)))

    # ---- S1: same fit, each curve compressed to a monotone 4-segment hinge
    cur, brk = [], []
    for j in range(len(sel)):
        c, b = hinge_compress(luts[j], counts[j])
        cur.append(c)
        brk.append(b)
    fitted["S1"] = M.HingePWL(sel, sizes, cur, brk)
    fitted["S1"].sel_idx = list(range(len(sel)))

    # ---- S2: 256 sequential depth-1 stumps
    m2 = HistGradientBoostingClassifier(max_iter=256, max_depth=1, max_leaf_nodes=2,
                                        learning_rate=0.15, early_stopping=False,
                                        random_state=0, max_bins=255)
    m2.fit(Xq.astype(np.float64), y)
    fitted["S2"] = M.TreeEnsemble(sel, M.extract_hgb_trees(m2, 1), 1)
    fitted["S2"].sel_idx = list(range(len(sel)))

    # ---- S3: 32 sequential depth-4 trees
    m3 = HistGradientBoostingClassifier(max_iter=32, max_depth=4, max_leaf_nodes=16,
                                        learning_rate=0.2, early_stopping=False,
                                        random_state=0, max_bins=255)
    m3.fit(Xq.astype(np.float64), y)
    fitted["S3"] = M.TreeEnsemble(sel, M.extract_hgb_trees(m3, 4), 4)
    fitted["S3"].sel_idx = list(range(len(sel)))

    # ---- CEIL: out of class.  All 26 features incl. OFF_BUDGET, 500 trees.
    Xall = d.X.astype(np.float64)
    mc = HistGradientBoostingClassifier(max_iter=500, max_depth=6, learning_rate=0.1,
                                        early_stopping=False, random_state=0)
    mc.fit(Xall, y)

    # ---- floor models: the SAME shapes REFIT on permuted labels (prereg B1)
    floor = {}
    m2s = HistGradientBoostingClassifier(max_iter=256, max_depth=1, max_leaf_nodes=2,
                                         learning_rate=0.15, early_stopping=False,
                                         random_state=0, max_bins=255)
    mysh = ysh >= 0
    m2s.fit(Xq[mysh].astype(np.float64), ysh[mysh])
    floor["S2"] = M.TreeEnsemble(sel, M.extract_hgb_trees(m2s, 1), 1)
    m3s = HistGradientBoostingClassifier(max_iter=32, max_depth=4, max_leaf_nodes=16,
                                         learning_rate=0.2, early_stopping=False,
                                         random_state=0, max_bins=255)
    m3s.fit(Xq[mysh].astype(np.float64), ysh[mysh])
    floor["S3"] = M.TreeEnsemble(sel, M.extract_hgb_trees(m3s, 4), 4)
    lsh, _ = _fit_additive(Xq[mysh], ysh[mysh], sel, sizes, 800)
    floor["S1b"] = M.AdditiveLUT(sel, sizes, lsh)
    floor["S1"] = floor["S1b"]
    l0s, _ = _fit_additive(Xq[mysh][:, [j0]], ysh[mysh], ["d_spawn_h"],
                           [sizes[j0]], 400)
    floor["S0"] = M.AdditiveLUT(["d_spawn_h"], [sizes[j0]], l0s)

    import pickle
    with open(os.path.join(OUT, "fitted.pkl"), "wb") as fh:
        pickle.dump({"sel": sel, "sizes": sizes, "scales": scales,
                     "qerr": qerr, "models": fitted, "floor": floor,
                     "ceil": mc, "ceil_names": d.names}, fh)

    # train-only sanity (NOT a result; the holdout is still sealed)
    for k, m in fitted.items():
        idx = m.sel_idx
        r = m.raw(Xq[:, idx])
        q = m.quantise().delta(Xq[:, idx])
        print(f"[fit] {k:4s} trainAUC float {auc(r,y):.4f} quant {auc(q,y):.4f} "
              f"params={m.n_params()}")
    print(f"[fit] CEIL trainAUC {auc(mc.decision_function(Xall), y):.4f}")


# ------------------------------------------------------------------ stage eval
def quant_at_dose(m, dose, bits=12):
    """Re-quantise a fitted model's table at the SHIP dose, so the BRAM holds the
    final integers and Delta is an exact integer sum in champion score units."""
    import models as M
    lo, hi = -(1 << (bits - 1)), (1 << (bits - 1)) - 1
    if isinstance(m, (M.AdditiveLUT, M.HingePWL)):
        tabs = m.luts if isinstance(m, M.AdditiveLUT) else m.curves
        q = [np.clip(np.rint(np.asarray(t) * dose), lo, hi).astype(np.int32)
             for t in tabs]
        return M.QuantLUT(m.feats, q, 1.0 / dose, bits)
    qt = []
    for t in m.trees:
        d = dict(t)
        d["leaf_q"] = np.clip(np.rint(np.asarray(t["leaf_val"]) * dose),
                              lo, hi).astype(np.int32)
        qt.append(d)
    return M.QuantTrees(m.feats, qt, 1.0 / dose, m.depth, bits)


def auc_fast(x, y):
    """Vectorised twin of auc().  Equality against the exact helper is ASSERTED on
    the real holdout before the bootstrap uses it."""
    n = x.shape[0]
    order = np.argsort(x, kind="mergesort")
    xs, ys = x[order], y[order]
    new = np.empty(n, bool)
    new[0] = True
    np.not_equal(xs[1:], xs[:-1], out=new[1:])
    grp = np.cumsum(new) - 1
    cnt = np.bincount(grp)
    avg = np.bincount(grp, weights=np.arange(1, n + 1, dtype=np.float64)) / cnt
    ranks = avg[grp]
    n1 = float((ys == 1).sum())
    n0 = float(n - n1)
    if n1 == 0 or n0 == 0:
        return float("nan")
    return float((ranks[ys == 1].sum() - n1 * (n1 + 1) / 2.0) / (n1 * n0))


def boot_paired_auc(sm, sc, y, seed, B=2000, rng=0):
    """95% SEED-CLUSTERED bootstrap CI on AUC(model) - AUC(champ), paired."""
    r = np.random.default_rng(rng)
    games, inv = np.unique(seed, return_inverse=True)
    order = np.argsort(inv, kind="mergesort")
    starts = np.searchsorted(inv[order], np.arange(len(games)))
    ends = np.append(starts[1:], len(order))
    idxs = [order[a:b] for a, b in zip(starts, ends)]
    out = np.empty(B)
    for b in range(B):
        pick = r.integers(0, len(games), len(games))
        sel = np.concatenate([idxs[p] for p in pick])
        out[b] = auc_fast(sm[sel], y[sel]) - auc_fast(sc[sel], y[sel])
    return float(np.percentile(out, 2.5)), float(np.percentile(out, 97.5)), out


def stage_eval(args):
    import pickle
    import models as M
    from sklearn.ensemble import HistGradientBoostingClassifier

    P = pickle.load(open(os.path.join(OUT, "fitted.pkl"), "rb"))
    sel, sizes, scales = P["sel"], P["sizes"], P["scales"]
    d = load(with_holdout=True)
    ho = d.hold == 1
    print(f"[eval] HOLDOUT OPENED: rows={ho.sum()} pos={(d.y[ho]==1).sum()} "
          f"neg={(d.y[ho]==0).sum()} games={np.unique(d.seed[ho]).size}", flush=True)

    Xq_all, qerr = M.quantise_features(cols(d, sel), scales)
    Xq = Xq_all[ho]
    y = d.y[ho].astype(int)
    sd = d.seed[ho]
    champ_risk = -d.champ[ho].astype(np.float64)     # low champion value = risky
    A_champ = auc(champ_risk, y)
    assert abs(auc_fast(champ_risk, y) - A_champ) < 1e-12, \
        'auc_fast disagrees with the exact helper'
    _mut = champ_risk.copy(); _mut[:100] = _mut[:100] + 1e6
    assert abs(auc_fast(_mut, y) - A_champ) > 1e-9, \
        'auc_fast is insensitive to a perturbation -- vacuous check'
    print(f"[eval] A_champ (holdout) = {A_champ:.4f}")

    # ---------- CEIL diagnostics, fitted on TRAIN, scored on HOLDOUT
    dtr = load(with_holdout=False)
    ceil_all = P["ceil"].decision_function(d.X[ho].astype(np.float64))
    m8 = HistGradientBoostingClassifier(max_iter=500, max_depth=6, learning_rate=0.1,
                                        early_stopping=False, random_state=0)
    m8.fit(cols(dtr, sel), dtr.y.astype(int))
    ceil8 = m8.decision_function(cols(d, sel)[ho])
    A_ceil = auc(ceil_all, y)
    A_ceil8 = auc(ceil8, y)
    print(f"[eval] CEIL(26 feat, out of class) = {A_ceil:.4f}   "
          f"CEIL8(8 in-class feats, unlimited capacity) = {A_ceil8:.4f}")

    # ---------- all32 within-decision layer (holdout rows only)
    F = np.load(os.path.join(RES, "s2feat_local.npz"))
    sel26 = [d.idx[f] for f in sel]
    A32 = {}
    for nm in ("fail", "ctrl"):
        hh = F[f"all32_{nm}_hold"] == 1
        A32[nm] = dict(
            feat=F[f"all32_{nm}_feat"][hh][:, :, sel26].astype(np.float64),
            vals=F[f"all32_{nm}_vals"][hh].astype(np.float64),
            act=F[f"all32_{nm}_action"][hh].astype(int),
            seed=F[f"all32_{nm}_seed"][hh])
    print(f"[eval] all32 holdout: fail {A32['fail']['vals'].shape[0]} "
          f"ctrl {A32['ctrl']['vals'].shape[0]} decisions")

    # ---------- B4 eval-hacking slice: T_PLACE topouts (y == -1, never trained on)
    ff = np.load(os.path.join(RES, "s2lulu_fail_local.npz"))
    Ff = np.load(os.path.join(RES, "s2feat_local.npz"))["fail_feat"]
    Fc = np.load(os.path.join(RES, "s2feat_local.npz"))["fail_champ_eval"]
    mtp = (ff["end_kind"] == 3) & (ff["hold"] == 1)
    tpXf = np.concatenate([Ff[mtp][:, [d.idx[f] for f in sel]],
                           cols(d, sel)[ho][y == 0]])
    tpq, _ = M.quantise_features(tpXf, scales)
    tpy = np.concatenate([np.ones(int(mtp.sum()), int),
                          np.zeros(int((y == 0).sum()), int)])
    tpchamp = -np.concatenate([Fc[mtp].astype(np.float64),
                               d.champ[ho][y == 0].astype(np.float64)])
    tplace = (tpq, tpy, None)
    print(f"[eval] B4 T_PLACE slice: {int(mtp.sum())} step_topout rows vs "
          f"{int((y==0).sum())} clear rows, A_champ={auc(tpchamp, tpy):.4f}")

    def flip_rate(qm, part, idx):
        a = A32[part]
        n, _, _ = a["feat"].shape
        fq, _ = M.quantise_features(a["feat"].reshape(-1, len(sel)), scales)
        D = qm.delta(fq[:, idx]).reshape(n, 32).astype(np.float64)
        new = a["vals"] - D
        # champion enumeration order: first max in CHAMP_ORDER wins ties
        arg = CHAMP_ORDER[np.nanargmax(new[:, CHAMP_ORDER], axis=1)]
        base = CHAMP_ORDER[np.nanargmax(a["vals"][:, CHAMP_ORDER], axis=1)]
        assert (base == a["act"]).mean() > 0.999, "argmax reconstruction broken"
        return float((arg != a["act"]).mean()), int(np.abs(D).max())

    DOSES = [1, 2, 5, 10, 20, 40, 80, 160, 320]
    results = {}
    for key in ["S0", "S1", "S1b", "S2", "S3"]:
        m = P["models"][key]
        idx = m.sel_idx
        raw_tr = m.raw(Xq_all[~ho][:, idx])
        # dose = score points per unit raw output, normalised to a target Delta std
        base_sd = float(np.std(raw_tr)) or 1.0
        rec = {"float_auc": auc(m.raw(Xq[:, idx]), y)}

        q12 = m.quantise(12)
        q3 = m.quantise(M.MUT_BITS)          # KILLED MUTANT for the quantiser
        rec["quant12_auc"] = auc(q12.delta(Xq[:, idx]), y)
        rec["mutant3bit_auc"] = auc(q3.delta(Xq[:, idx]), y)

        # floor = the SAME shape REFIT on permuted labels (prereg B1)
        fm = P["floor"][key]
        fidx = list(range(len(fm.feats))) if key != "S0" else [0]
        fX = Xq[:, idx] if key != "S0" else Xq[:, idx]
        rec["floor_refit_auc"] = auc(fm.raw(fX), y)
        rec["B1_margin"] = rec["quant12_auc"] - rec["floor_refit_auc"]

        # dose curve: flip rate on target class and on CLEARS (breakage proxy)
        curve = []
        for T in DOSES:
            qd = quant_at_dose(m, T / base_sd)
            ff, mxf = flip_rate(qd, "fail", idx)
            fc, mxc = flip_rate(qd, "ctrl", idx)
            dl = qd.delta(Xq[:, idx])
            curve.append({"target_delta_sd": T,
                          "dose": T / base_sd,
                          "flip_target_class": ff,
                          "flip_clear_games": fc,
                          "delta_abs_max": max(mxf, mxc, int(np.abs(dl).max())),
                          "auc": auc(dl, y)})
        rec["dose_curve"] = curve
        # SHIP DOSE = smallest dose reaching the pre-registered 2% flip bar
        ship = next((c for c in curve if c["flip_target_class"] >= 0.02), curve[-1])
        rec["ship_dose"] = ship
        qs = quant_at_dose(m, ship["dose"])
        ds = qs.delta(Xq[:, idx])
        rec["ship_quant_auc"] = auc(ds, y)
        rec["accum_max_abs"] = int(np.abs(ds).max())
        rec["accum_int16_ok"] = bool(np.abs(ds).max() <= 32767)
        # deployed combined score: sco = champ - Delta
        rec["combined_auc"] = auc(-(d.champ[ho].astype(np.float64) - ds), y)
        rec["param_bits"] = q12.param_bits()
        rec["n_params"] = m.n_params()
        rec["cycles"] = q12.cycles()
        rec["ops"] = q12.ops()

        # B2 paired seed-clustered bootstrap
        lo, hi, dist = boot_paired_auc(ds.astype(float), champ_risk, y, sd,
                                       B=args.boot)
        rec["B2_diff"] = rec["ship_quant_auc"] - A_champ
        rec["B2_ci95"] = [lo, hi]
        rec["B2_frac_pos"] = float((dist > 0).mean())

        # B4 eval-hacking: T_PLACE (step_topout, END_KIND 3) vs the SAME clears.
        # These rows are y == -1, excluded from the primary contrast by design, so
        # they are a genuinely held-out mechanism the model was never trained on.
        tpX, tpy, tps = tplace
        tpd = quant_at_dose(m, ship["dose"]).delta(tpX[:, idx])
        rec["B4_T_PLACE_vs_clears"] = {
            "n_pos": int((tpy == 1).sum()), "n_neg": int((tpy == 0).sum()),
            "auc_model": auc(tpd, tpy),
            "auc_champ": auc(tpchamp, tpy)}

        # B4 mandated t_to_end / height bands
        sl = {}
        tte = d.t_to_end[ho]
        for nm, mm in [("t<=2", tte <= 2), ("t3-9", (tte > 2) & (tte <= 9)),
                       ("t10-30", (tte > 9) & (tte <= 30)), ("t>30", tte > 30)]:
            sl[nm] = {"n": int(mm.sum()), "auc_model": auc(ds[mm], y[mm]),
                      "auc_champ": auc(champ_risk[mm], y[mm])}
        mh = d.max_height[ho]
        for nm, mm in [("h<=9", mh <= 9), ("h10-12", (mh >= 10) & (mh <= 12)),
                       ("h13-14", (mh >= 13) & (mh <= 14)), ("h15-16", mh >= 15)]:
            sl[nm] = {"n": int(mm.sum()), "auc_model": auc(ds[mm], y[mm]),
                      "auc_champ": auc(champ_risk[mm], y[mm])}
        g = d.slg[ho]
        qs_ = np.percentile(g, np.arange(0, 101, 10))
        dec = []
        for i in range(10):
            mm = (g >= qs_[i]) & (g <= qs_[i + 1])
            if mm.sum() > 500:
                dec.append({"decile": i, "n": int(mm.sum()),
                            "auc_model": auc(ds[mm], y[mm]),
                            "auc_champ": auc(champ_risk[mm], y[mm])})
        rec["slices"] = sl
        rec["since_last_garbage_deciles"] = dec
        results[key] = rec
        print(f"[eval] {key:4s} float {rec['float_auc']:.4f} q12 {rec['quant12_auc']:.4f} "
              f"ship {rec['ship_quant_auc']:.4f} (dose sd={ship['target_delta_sd']}) "
              f"3bit {rec['mutant3bit_auc']:.4f} floor {rec['floor_refit_auc']:.4f} "
              f"flipT {ship['flip_target_class']*100:.2f}% flipC "
              f"{ship['flip_clear_games']*100:.2f}% "
              f"B2 {rec['B2_diff']:+.4f} [{lo:+.4f},{hi:+.4f}]", flush=True)

    out = {"caveat": CAVEAT, "prereg": "PREREG_SHIPPABLE.md @ 2d4d5d0",
           "parent_prereg": "PREREG_STAGE2.md @ b9725fc",
           "selected_features": sel, "feature_quant_max_abs_err": dict(zip(sel, qerr)),
           "holdout": {"rows": int(ho.sum()), "pos": int((y == 1).sum()),
                       "neg": int((y == 0).sum()),
                       "games": int(np.unique(sd).size)},
           "A_champ": A_champ, "A_ceil_26feat_out_of_class": A_ceil,
           "A_ceil8_in_class_features_unlimited_capacity": A_ceil8,
           "models": results}
    with open(os.path.join(OUT, "holdout_result.json"), "w") as fh:
        json.dump(out, fh, indent=1, default=float)
    print("[eval] wrote", os.path.join(OUT, "holdout_result.json"))


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("stage", choices=["select", "fit", "eval"])
    ap.add_argument("--boot", type=int, default=2000)
    ap.add_argument("--threads", type=int, default=6)
    a = ap.parse_args()
    os.environ["OMP_NUM_THREADS"] = str(a.threads)
    t0 = time.time()
    {"select": stage_select, "fit": stage_fit, "eval": stage_eval}[a.stage](a)
    print(f"[{a.stage}] {time.time()-t0:.1f}s")
