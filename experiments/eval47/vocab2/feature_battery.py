#!/usr/bin/env python3
"""vocab2 Phase 2 -- feature battery on fatal vs matched-safe decisions.

Pre-registered in PREREG_PHASE2.md (committed before --stats ran). Stages:
  --features   compute per-decision feature matrix (11 baseline + candidates)
               for fatal_windows.npz + controls.npz -> features.npz
  --gates      G1-G4 (positive control, shuffle null, killed mutants, cross
               checks); writes gates_result.json; battery refuses to report
               without a PASS
  --stats      stratified AUC + cluster-bootstrap CI + permutation family band
               -> battery_result.json
"""
from __future__ import annotations

import sys, os, json, time, argparse

HERE = os.path.dirname(os.path.abspath(__file__))
QA = "/home/struktured/projects/dr-mario-qa-wt/experiments"
ROOT = "/home/struktured/projects/dr_mario_rl"
for _p in (QA + "/eval47", ROOT + "/tmp/combo_term", ROOT + "/tmp/endgame",
           ROOT + "/tmp/tuck", ROOT + "/tmp/pillrng",
           ROOT + "/.claude/worktrees/faithful-sim/src", QA, QA + "/tuck_v3"):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import numpy as np  # noqa: E402

RNG_STATS = 20260810
B_BOOT = 200
N_PERM = 200

NAMES11 = ["MAXH", "HOLES", "TOPRISK", "SPAWN", "SETUP", "MATCHED", "BURIED",
           "RDYEXT", "VRDY", "CROSS", "POLL"]
# champion-preferred direction: +1 means champion prefers HIGH values
PREF_SIGN = {"MAXH": -1, "HOLES": -1, "TOPRISK": -1, "SPAWN": -1, "SETUP": +1,
             "MATCHED": +1, "BURIED": -1, "RDYEXT": +1, "VRDY": +1,
             "CROSS": +1, "POLL": -1}

CAND_NAMES = ["a_topout_dist", "a_d_maxh", "b_spawn_prox", "b_spawn_prox_strict",
              "c_das_reach", "c_d_das_reach", "c_nlegal_probe", "c_d_nlegal",
              "d_gvuln_mass", "d_crit_cols", "d_spawn_h",
              "e_escape_routes", "e_escape_reach", "x_hvar", "x_jagged"]

ALLOW = np.array([15 - abs(c - 3) // 2 for c in range(8)])  # das proxy clearance


# --------------------------------------------------------------- geometry
def heights_from_boards(cols):
    """cols (n,128) int8 -> (n,8) column heights, row 0 = top."""
    b = cols.reshape(-1, 16, 8) != 0
    first = np.argmax(b, axis=1)               # first occupied row per column
    any_ = b.any(axis=1)
    return np.where(any_, 16 - first, 0).astype(np.int16)


def das_reach(H):
    """# columns path-reachable from col 3 under H[j] <= 15 - |j-3|//2."""
    ok = H <= ALLOW[None, :]
    R = np.zeros_like(ok)
    R[:, 3] = ok[:, 3]
    for c in range(2, -1, -1):
        R[:, c] = R[:, c + 1] & ok[:, c]
    for c in range(4, 8):
        R[:, c] = R[:, c - 1] & ok[:, c]
    return R


def nlegal_probe(H):
    """Engine-true legal placement count (color-independent legality)."""
    horiz = (np.maximum(H[:, :-1], H[:, 1:]) < 16).sum(axis=1)
    vert = (H <= 14).sum(axis=1)
    return 2 * horiz + 2 * vert


def candidate_features(post_cols, Hpost, Hpre, n_legal_pre):
    n = Hpost.shape[0]
    b = post_cols.reshape(n, 16, 8) != 0
    R = das_reach(Hpost)
    Rpre = das_reach(Hpre)
    out = {}
    out["a_topout_dist"] = 16 - Hpost.max(axis=1)
    out["a_d_maxh"] = Hpost.max(axis=1) - Hpre.max(axis=1)
    out["b_spawn_prox"] = b[:, 0:3, 2:6].sum(axis=(1, 2))
    out["b_spawn_prox_strict"] = b[:, 0:2, 3:5].sum(axis=(1, 2))
    out["c_das_reach"] = R.sum(axis=1)
    out["c_d_das_reach"] = R.sum(axis=1) - Rpre.sum(axis=1)
    out["c_nlegal_probe"] = nlegal_probe(Hpost)
    out["c_d_nlegal"] = nlegal_probe(Hpost) - n_legal_pre
    out["d_gvuln_mass"] = np.maximum(0, Hpost - 11).sum(axis=1)
    out["d_crit_cols"] = (Hpost >= 14).sum(axis=1)
    out["d_spawn_h"] = np.maximum(Hpost[:, 3], Hpost[:, 4])
    out["e_escape_routes"] = (Hpost <= 10).sum(axis=1)
    out["e_escape_reach"] = (R & (Hpost <= 10)).sum(axis=1)
    out["x_hvar"] = Hpost.astype(np.float64).var(axis=1)
    out["x_jagged"] = np.abs(np.diff(Hpost.astype(np.int32), axis=1)).sum(axis=1)
    return out


# --------------------------------------------------------------- extraction
def build_extractor():
    import reach_root as RR
    L = RR._lazy()
    FX, FS = L["FX"], L["FS"]
    fl = L["fl"]
    from numba import njit
    _expand_core = FS._expand_core
    _base_scan = FX._base_scan
    NBASE, NT = FX.NBASE, FX.NT

    @njit(cache=False)
    def _extract(cols, virs, cura, curb, actions, fl_arr, feats11, nvirs,
                 posts, postv, okflags, prefeats, prenvir):
        n = cols.shape[0]
        c1 = np.empty(128, dtype=np.int8)
        v1 = np.empty(128, dtype=np.int8)
        base = np.empty(NBASE, dtype=np.int64)
        for i in range(n):
            # pre-board terms (for G4 cross-checks)
            _base_scan(cols[i], virs[i], fl_arr, base)
            for k in range(11):
                prefeats[i, k] = base[k]
            prenvir[i] = base[11]
            a = actions[i]
            var = a // 8
            cc = a % 8
            ok, nv, cells = _expand_core(cols[i], virs[i], var, cc,
                                         cura[i], curb[i], c1, v1)
            okflags[i] = ok
            if ok == 0:
                continue
            _base_scan(c1, v1, fl_arr, base)
            for k in range(11):
                feats11[i, k] = base[k]
            nvirs[i] = base[11]
            for k in range(128):
                posts[i, k] = c1[k]
                postv[i, k] = v1[k]
    return _extract, fl


def load_npz(path):
    z = np.load(path)
    return {k: z[k] for k in z.files}


def run_features():
    fatal = load_npz(os.path.join(HERE, "fatal_windows.npz"))
    ctrl = load_npz(os.path.join(HERE, "controls.npz"))
    extract, fl = build_extractor()
    out = {}
    for tag, d in (("fatal", fatal), ("ctrl", ctrl)):
        n = d["seed"].shape[0]
        feats11 = np.zeros((n, 11), dtype=np.int64)
        nvirs = np.zeros(n, dtype=np.int64)
        posts = np.zeros((n, 128), dtype=np.int8)
        postv = np.zeros((n, 128), dtype=np.int8)
        okflags = np.zeros(n, dtype=np.int8)
        prefeats = np.zeros((n, 11), dtype=np.int64)
        prenvir = np.zeros(n, dtype=np.int64)
        t0 = time.monotonic()
        extract(d["board_col"], d["board_vir"], d["cur"][:, 0], d["cur"][:, 1],
                d["action"].astype(np.int64), fl, feats11, nvirs, posts, postv,
                okflags, prefeats, prenvir)
        print(f"[features] {tag}: {n} decisions in {time.monotonic()-t0:.1f}s "
              f"ok={int(okflags.sum())}", flush=True)
        assert okflags.all(), f"{tag}: chosen action illegal on some decision"
        Hpost = heights_from_boards(posts)
        Hpre = heights_from_boards(d["board_col"])
        cands = candidate_features(posts, Hpost, Hpre,
                                   d["n_legal"].astype(np.int32))
        out[tag] = dict(feats11=feats11, nvir_post=nvirs, prefeats=prefeats,
                        prenvir=prenvir, Hpre=Hpre, Hpost=Hpost,
                        **{"cand_" + k: v for k, v in cands.items()})
    np.savez_compressed(os.path.join(HERE, "features.npz"),
                        **{f"{tag}_{k}": v for tag, dd in out.items()
                           for k, v in dd.items()})
    print("[features] wrote features.npz", flush=True)


# --------------------------------------------------------------- stats core
def stratified_auc_machinery(strata, values, is_fatal):
    """Precompute sort/group structure for weighted stratified AUC.

    Returns a closure auc(w) -> (combined_auc, n_strata_used) where w is a
    per-decision weight vector (>=0). Combined = per-fatal-weight-weighted
    mean of within-stratum P(fatal > ctrl) + 0.5 ties.
    """
    order = np.lexsort((values, strata))
    s = strata[order]
    x = values[order]
    yf = is_fatal[order]
    new_group = np.empty(len(s), dtype=bool)
    new_group[0] = True
    new_group[1:] = (s[1:] != s[:-1]) | (x[1:] != x[:-1])
    uid = np.cumsum(new_group) - 1
    nuid = uid[-1] + 1
    su = s[new_group]                       # stratum of each uid
    new_str = np.empty(nuid, dtype=bool)
    new_str[0] = True
    new_str[1:] = su[1:] != su[:-1]
    sid_of_uid = np.cumsum(new_str) - 1      # dense stratum index per uid
    nstr = sid_of_uid[-1] + 1

    def auc(w):
        wo = w[order]
        cw = np.bincount(uid, weights=wo * (~yf), minlength=nuid)
        fw = np.bincount(uid, weights=wo * yf, minlength=nuid)
        ccum = np.cumsum(cw)
        below = np.concatenate(([0.0], ccum[:-1]))
        # subtract control weight accumulated before each stratum starts
        start_val = below[new_str]           # ccum just before stratum start
        below = below - start_val[sid_of_uid]
        num = np.bincount(sid_of_uid, weights=fw * (below + 0.5 * cw),
                          minlength=nstr)
        wf_s = np.bincount(sid_of_uid, weights=fw, minlength=nstr)
        wc_s = np.bincount(sid_of_uid, weights=cw, minlength=nstr)
        use = (wf_s > 0) & (wc_s > 0)
        if not use.any():
            return np.nan, 0
        auc_s = num[use] / (wf_s[use] * wc_s[use])
        comb = float(np.sum(wf_s[use] * auc_s) / np.sum(wf_s[use]))
        return comb, int(use.sum())
    return auc


def make_contrast(fat_d, ctl_d, featF, featC, fatal_mask):
    """Assemble combined arrays for one contrast. Returns dict."""
    key = lambda d, m: (d["stratum_h"][m].astype(np.int64) * 10000
                        + d["stratum_v"][m].astype(np.int64) * 100
                        + d["stratum_g"][m].astype(np.int64))
    mF = fatal_mask
    kF = key(fat_d, mF)
    kC = key(ctl_d, np.ones(len(ctl_d["seed"]), dtype=bool))
    # eligible strata: both classes present
    common = np.intersect1d(np.unique(kF), np.unique(kC))
    inF = np.isin(kF, common)
    inC = np.isin(kC, common)
    n_excl = int((~inF).sum())
    strata = np.concatenate([kF[inF], kC[inC]])
    isf = np.concatenate([np.ones(inF.sum(), bool), np.zeros(inC.sum(), bool)])
    seeds = np.concatenate([fat_d["seed"][mF][inF], ctl_d["seed"][inC]])
    X = {name: np.concatenate([featF[name][mF][inF].astype(np.float64),
                               featC[name][inC].astype(np.float64)])
         for name in featF}
    return dict(strata=strata, isf=isf, seeds=seeds, X=X,
                n_fatal=int(inF.sum()), n_ctrl=int(inC.sum()),
                n_fatal_excluded=n_excl)


def boot_weights(seeds, isf, rng):
    """Cluster bootstrap: resample fatal games and control games separately."""
    w = np.zeros(len(seeds))
    for cls in (True, False):
        m = isf == cls
        uq, inv = np.unique(seeds[m], return_inverse=True)
        draw = rng.integers(0, len(uq), len(uq))
        cnt = np.bincount(draw, minlength=len(uq)).astype(np.float64)
        w[m] = cnt[inv]
    return w


def perm_labels_within_stratum(strata, isf, rng):
    """Within-stratum permutation of fatal/control labels (pipeline G2 +
    family-wise band). Decision-level (declared in prereg)."""
    out = isf.copy()
    order = np.argsort(strata, kind="stable")
    s_sorted = strata[order]
    bounds = np.flatnonzero(np.concatenate(([1], np.diff(s_sorted) != 0, [1])))
    for i in range(len(bounds) - 1):
        seg = order[bounds[i]:bounds[i + 1]]
        out[seg] = out[seg][rng.permutation(len(seg))]
    return out


def run_battery(contrast, feat_names, rng, do_boot=True, do_perm=True):
    strata, isf, seeds = contrast["strata"], contrast["isf"], contrast["seeds"]
    X = contrast["X"]
    ones = np.ones(len(isf))
    res = {}
    machs = {}
    for name in feat_names:
        mach = stratified_auc_machinery(strata, X[name], isf)
        machs[name] = mach
        a, ns = mach(ones)
        res[name] = {"auc": a, "n_strata": ns}
    if do_boot:
        boots = {name: [] for name in feat_names}
        for b in range(B_BOOT):
            w = boot_weights(seeds, isf, rng)
            for name in feat_names:
                a, _ = machs[name](w)
                if not np.isnan(a):
                    boots[name].append(a)
        for name in feat_names:
            bs = np.array(boots[name])
            res[name]["ci95"] = [float(np.percentile(bs, 2.5)),
                                 float(np.percentile(bs, 97.5))]
            eff = np.abs(bs - 0.5)
            res[name]["eff_ci95"] = [float(np.percentile(eff, 2.5)),
                                     float(np.percentile(eff, 97.5))]
    perm_max = None
    if do_perm:
        fam = []
        per_feat = {name: [] for name in feat_names}
        for p in range(N_PERM):
            yp = perm_labels_within_stratum(strata, isf, rng)
            mx = 0.0
            for name in feat_names:
                mach = stratified_auc_machinery(strata, X[name], yp)
                a, _ = mach(ones)
                d = abs(a - 0.5)
                per_feat[name].append(a)
                if d > mx:
                    mx = d
            fam.append(mx)
        perm_max = {"family_p95": float(np.percentile(fam, 95)),
                    "family_p99": float(np.percentile(fam, 99)),
                    "per_feature_absdev_p95":
                        {n: float(np.percentile(np.abs(np.array(per_feat[n]) - 0.5), 95))
                         for n in feat_names}}
    return res, perm_max


# --------------------------------------------------------------- gates
def board_from_heights(H):
    col = np.zeros(128, dtype=np.int8)
    for c, h in enumerate(H):
        for r in range(16 - h, 16):
            col[r * 8 + c] = 1
    return col


def run_gates():
    gates = {}
    # ---- G3 killed mutants on synthetic boards -------------------------
    g3 = []
    H1 = np.array([[0, 0, 0, 0, 0, 15, 0, 0]], dtype=np.int16)
    v = int(das_reach(H1).sum())
    mut = (H1 <= (16 - np.abs(np.arange(8) - 3) // 2)[None, :])  # off-by-one mutant
    Rm = np.zeros_like(mut)
    Rm[:, 3] = mut[:, 3]
    for c in range(2, -1, -1):
        Rm[:, c] = Rm[:, c + 1] & mut[:, c]
    for c in range(4, 8):
        Rm[:, c] = Rm[:, c - 1] & mut[:, c]
    g3.append({"feature": "c_das_reach", "hand": 5, "got": v,
               "mutant_got": int(Rm.sum()), "killed": int(Rm.sum()) != v,
               "correct": v == 5})
    H2 = np.array([[0, 3, 10, 11, 12, 10, 2, 16]], dtype=np.int16)
    v = int((H2 <= 10).sum())
    vm = int((H2 <= 11).sum())
    g3.append({"feature": "e_escape_routes", "hand": 5, "got": v,
               "mutant_got": vm, "killed": vm != v, "correct": v == 5})
    col = np.zeros((1, 128), dtype=np.int8)
    for (r, c) in [(0, 2), (2, 5), (1, 3), (3, 4)]:
        col[0, r * 8 + c] = 1
    b = col.reshape(1, 16, 8) != 0
    v = int(b[:, 0:3, 2:6].sum())
    vm = int(b[:, 0:4, 2:6].sum())
    g3.append({"feature": "b_spawn_prox", "hand": 3, "got": v,
               "mutant_got": vm, "killed": vm != v, "correct": v == 3})
    H3 = np.array([[0, 0, 0, 0, 0, 0, 13, 12]], dtype=np.int16)
    v = int(np.maximum(0, H3 - 11).sum())
    vm = int(np.maximum(0, H3 - 12).sum())
    g3.append({"feature": "d_gvuln_mass", "hand": 3, "got": v,
               "mutant_got": vm, "killed": vm != v, "correct": v == 3})
    H4 = np.array([[2, 2, 2, 2, 4, 4, 4, 4]], dtype=np.float64)
    v = float(H4.var(axis=1)[0])
    vm = float(H4.var(axis=1, ddof=1)[0])
    g3.append({"feature": "x_hvar", "hand": 1.0, "got": v,
               "mutant_got": vm, "killed": abs(vm - v) > 1e-12,
               "correct": abs(v - 1.0) < 1e-12})
    H5 = np.array([[2, 4, 2, 2, 4, 4, 4, 2]], dtype=np.int32)
    v = int(np.abs(np.diff(H5, axis=1)).sum())
    vm = int(np.diff(H5, axis=1).sum())
    g3.append({"feature": "x_jagged", "hand": 8, "got": v,
               "mutant_got": vm, "killed": vm != v, "correct": v == 8})
    gates["G3"] = {"cases": g3,
                   "pass": all(c["killed"] and c["correct"] for c in g3)}

    # ---- G4 cross-checks vs stored covariates --------------------------
    z = np.load(os.path.join(HERE, "features.npz"))
    g4 = {}
    for tag in ("fatal", "ctrl"):
        d = load_npz(os.path.join(HERE, f"{'fatal_windows' if tag=='fatal' else 'controls'}.npz"))
        pre11 = z[f"{tag}_prefeats"]
        g4[f"{tag}_maxh_match"] = bool((pre11[:, 0] == d["max_height"]).all())
        g4[f"{tag}_nvir_match"] = bool((z[f"{tag}_prenvir"] == d["viruses"]).all())
        Hpre = z[f"{tag}_Hpre"]
        g4[f"{tag}_nlegal_match"] = bool(
            (nlegal_probe(Hpre) == d["n_legal"].astype(np.int32)).all())
        vals = d["cand_vals"]
        am = np.nanargmax(vals, axis=1)
        # chosen must achieve the max value (strict > tie-break = first best)
        chosen_val = vals[np.arange(len(am)), d["action"].astype(np.int64)]
        best_val = vals[np.arange(len(am)), am]
        g4[f"{tag}_action_is_argmax"] = bool((chosen_val == best_val).all())
    gates["G4"] = {"checks": g4, "pass": all(g4.values())}

    # ---- G1/G2 on the primary contrast ---------------------------------
    fat, ctl, featF, featC = load_all_features()
    fatal_mask = fat["outcome"] == 1
    con = make_contrast(fat, ctl, featF, featC, fatal_mask)
    rng = np.random.default_rng(RNG_STATS + 1)
    leak = con["isf"].astype(np.float64) + rng.normal(0, 0.1, len(con["isf"]))
    mach = stratified_auc_machinery(con["strata"], leak, con["isf"])
    a_leak, _ = mach(np.ones(len(con["isf"])))
    gates["G1"] = {"leak_auc": a_leak, "pass": a_leak > 0.95}

    names = list(featF.keys())
    sub = {"strata": con["strata"], "isf": con["isf"], "seeds": con["seeds"],
           "X": con["X"]}
    # G2: shuffled labels -> real features must sit inside the permutation band
    rng2 = np.random.default_rng(RNG_STATS + 2)
    devs = []
    for p in range(50):
        yp = perm_labels_within_stratum(con["strata"], con["isf"], rng2)
        for name in ("MAXH", "d_gvuln_mass", "x_hvar", "c_das_reach"):
            mach = stratified_auc_machinery(con["strata"], con["X"][name], yp)
            a, _ = mach(np.ones(len(yp)))
            devs.append(abs(a - 0.5))
    gates["G2"] = {"n_shuffles": 50, "max_absdev": float(max(devs)),
                   "pass": max(devs) < 0.03}
    ok = all(gates[g]["pass"] for g in ("G1", "G2", "G3", "G4"))
    gates["pass"] = ok
    with open(os.path.join(HERE, "gates_result.json"), "w") as f:
        json.dump(gates, f, indent=1, default=str)
    print(f"[gates] G1 leak_auc={a_leak:.3f} G2 max_absdev={max(devs):.4f} "
          f"G3 {'PASS' if gates['G3']['pass'] else 'FAIL'} "
          f"G4 {'PASS' if gates['G4']['pass'] else 'FAIL'} -> "
          f"{'PASS' if ok else 'FAIL'}", flush=True)
    return ok


def load_all_features():
    fat = load_npz(os.path.join(HERE, "fatal_windows.npz"))
    ctl = load_npz(os.path.join(HERE, "controls.npz"))
    z = np.load(os.path.join(HERE, "features.npz"))
    featF, featC = {}, {}
    for i, n in enumerate(NAMES11):
        featF[n] = z["fatal_feats11"][:, i]
        featC[n] = z["ctrl_feats11"][:, i]
    for n in CAND_NAMES:
        featF[n] = z[f"fatal_cand_{n}"]
        featC[n] = z[f"ctrl_cand_{n}"]
    return fat, ctl, featF, featC


def run_stats():
    gates = json.load(open(os.path.join(HERE, "gates_result.json")))
    assert gates["pass"], "gates FAILED -- refusing to report statistics"
    fat, ctl, featF, featC = load_all_features()
    names = NAMES11 + CAND_NAMES
    rng = np.random.default_rng(RNG_STATS)
    out = {"prereg": "PREREG_PHASE2.md", "B_boot": B_BOOT, "N_perm": N_PERM,
           "rng": RNG_STATS}

    # PRIMARY: topout decisions
    m_top = fat["outcome"] == 1
    con = make_contrast(fat, ctl, featF, featC, m_top)
    print(f"[stats] PRIMARY topout: {con['n_fatal']} fatal decisions eligible "
          f"({con['n_fatal_excluded']} excluded, no matched stratum), "
          f"{con['n_ctrl']} controls", flush=True)
    t0 = time.monotonic()
    res, perm = run_battery(con, names, rng, do_boot=True, do_perm=True)
    print(f"[stats] primary battery {time.monotonic()-t0:.0f}s", flush=True)
    out["primary_topout"] = {"n_fatal": con["n_fatal"], "n_ctrl": con["n_ctrl"],
                             "n_fatal_excluded": con["n_fatal_excluded"],
                             "auc": res, "perm": perm}

    # SECONDARY s1: stall decisions
    m_stall = fat["outcome"] == 2
    con_s = make_contrast(fat, ctl, featF, featC, m_stall)
    res_s, _ = run_battery(con_s, names, rng, do_boot=True, do_perm=False)
    out["secondary_stall"] = {"n_fatal": con_s["n_fatal"],
                              "n_ctrl": con_s["n_ctrl"],
                              "n_fatal_excluded": con_s["n_fatal_excluded"],
                              "auc": res_s}

    # SECONDARY s2: topout & t_to_end<=2
    m_last = m_top & (fat["t_to_end"] <= 2)
    con_l = make_contrast(fat, ctl, featF, featC, m_last)
    res_l, _ = run_battery(con_l, names, rng, do_boot=True, do_perm=False)
    out["secondary_t_to_end_le2"] = {"n_fatal": con_l["n_fatal"],
                                     "n_ctrl": con_l["n_ctrl"],
                                     "n_fatal_excluded": con_l["n_fatal_excluded"],
                                     "auc": res_l}

    # verdict per prereg
    floor11 = max(abs(res[n]["auc"] - 0.5) for n in NAMES11)
    fam95 = perm["family_p95"]
    verdicts = {}
    for n in CAND_NAMES:
        eff = abs(res[n]["auc"] - 0.5)
        eff_lo = res[n]["eff_ci95"][0]
        verdicts[n] = {"eff": eff, "eff_ci_lo": eff_lo,
                       "beats_floor_ci": bool(eff_lo > floor11),
                       "beats_perm_band": bool(eff > fam95),
                       "separates": bool(eff_lo > floor11 and eff > fam95)}
    out["baseline_floor_abs"] = floor11
    out["family_perm_p95"] = fam95
    out["verdicts"] = verdicts

    # SECONDARY s3: height bands for top-3 candidates by primary effect
    top3 = sorted(CAND_NAMES, key=lambda n: -abs(res[n]["auc"] - 0.5))[:3]
    bands = {"h_le9": (0, 9), "h_10_12": (10, 12), "h_ge13": (13, 16)}
    s3 = {}
    for bname, (lo, hi) in bands.items():
        mB = m_top & (fat["max_height"] >= lo) & (fat["max_height"] <= hi)
        if mB.sum() < 50:
            s3[bname] = {"n_fatal_raw": int(mB.sum()), "skipped": True}
            continue
        conB = make_contrast(fat, ctl, featF, featC, mB)
        resB, _ = run_battery(conB, top3 + ["MAXH", "SPAWN"], rng,
                              do_boot=True, do_perm=False)
        s3[bname] = {"n_fatal": conB["n_fatal"], "auc": resB}
    out["secondary_height_bands"] = {"top3": top3, "bands": s3}

    with open(os.path.join(HERE, "battery_result.json"), "w") as f:
        json.dump(out, f, indent=1, default=str)
    print(json.dumps({k: {"auc": round(res[k]["auc"], 4),
                          "ci": [round(c, 4) for c in res[k].get("ci95", [np.nan]*2)]}
                      for k in names}, indent=1))
    print(f"[stats] baseline floor |AUC-0.5| = {floor11:.4f}; "
          f"family perm p95 = {fam95:.4f}", flush=True)
    seps = [n for n in CAND_NAMES if verdicts[n]["separates"]]
    print(f"[stats] SEPARATES: {seps if seps else 'NONE'}", flush=True)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--features", action="store_true")
    ap.add_argument("--gates", action="store_true")
    ap.add_argument("--stats", action="store_true")
    a = ap.parse_args()
    if a.features:
        run_features()
    if a.gates:
        run_gates()
    if a.stats:
        run_stats()


if __name__ == "__main__":
    main()
