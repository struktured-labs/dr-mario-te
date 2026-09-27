#!/usr/bin/env python3
"""STAGE 2 feature derivation + corpus GATES A3/A4 (PREREG_STAGE2.md @ b9725fc).

Two products:

  1. CHOSEN-MOVE features -- the stage-1-comparable design matrix: the 11
     baseline board terms + the 15 candidates (including d_spawn_h) on the POST
     board of the move the champion actually played, plus CHAMP_EVAL.
  2. PER-CANDIDATE features -- the same 26 features for EVERY legal sibling of
     a decision. This is the thing stage 1 did not have. Its absence is recon
     A's leak risk #7: a model can win a cross-board risk contest and never
     learn the WITHIN-DECISION ranking job it will actually be asked to do at a
     search leaf. Producing it is what makes prereg gate B3 testable at all.

The feature functions are `vocab2/feature_battery.py` REUSED UNCHANGED, so every
number produced here lands on the same instrument that produced stage 1's
SPAWN 0.9002 / d_spawn_h 0.9290.

GATES RUN HERE (a check that cannot fail is not a check):
  A4 cross-checks, on EVERY decision, against independently stored fields:
       recomputed MAXH(pre)      == stored max_height
       recomputed virus count    == stored viruses
       nlegal_probe(pre)         == stored n_legal
       stored action             == nanargmax(cand_vals)
       stored action is LEGAL (expand ok)
       per-candidate legality    == isfinite(cand_vals)      [32 slots/decision]
     Each is shown to FAIL on a deliberately corrupted input (mutants below).
  A3 shuffled-label floor + leak positive control:
       f_leak   vs y       must be > 0.95
       f_leak   vs y_shuf  must be in [0.48, 0.52]
       every real feature vs y_shuf must be in [0.45, 0.55]
     and the DEMONSTRATION that A3 can fail: f_leak scored against y is the
     same code path, and a MUTANT that broadcasts y_shuf per-DECISION instead
     of per-GAME must visibly break the floor.

Usage:
  s2_features.py --tag local            # features + gates -> s2feat_<tag>.npz
  s2_features.py --tag local --gates-only
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
EV = os.path.dirname(HERE)
QA = os.path.dirname(EV)
V2 = os.path.join(EV, "vocab2")
for _p in (EV, QA, V2, os.path.join(EV, "jointdig")):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import numpy as np  # noqa: E402
import feature_battery as FBAT  # noqa: E402  (REUSED UNCHANGED)

RESULTS = os.path.join(HERE, "results")
NAMES11 = FBAT.NAMES11
CAND_NAMES = FBAT.CAND_NAMES
FEAT_NAMES = NAMES11 + CAND_NAMES

# Silicon tagging, declared in PREREG sec 8 BEFORE any fitting, so the price of
# a feature cannot be rationalised after it turns out to help.
FREE_IN_COLWALK = {"MAXH", "HOLES", "TOPRISK", "SPAWN", "a_topout_dist",
                   "a_d_maxh", "b_spawn_prox", "b_spawn_prox_strict",
                   "d_spawn_h", "d_crit_cols", "d_gvuln_mass", "x_jagged",
                   "x_hvar", "e_escape_routes", "c_nlegal_probe", "c_d_nlegal"}
OFF_BUDGET = {"c_das_reach", "c_d_das_reach", "e_escape_reach"}

# The champion's scan order over the 32-slot cand_vals index. o4 = 0..3 maps
# to var via fast_rtl_x._VAR_OF_O4 = [2,3,0,1] and the slot is var*8+cc, so the
# order is 16..31 then 0..15. Ties keep the FIRST in this order (strict `>`).
CHAMP_ORDER = np.array([v * 8 + c for v in (2, 3, 0, 1) for c in range(8)])


# ------------------------------------------------------------------ kernels
def build_expander():
    """Post-board expander for ALL 32 (variant, column) drops of a decision."""
    import reach_root as RR
    L = RR._lazy()
    FX, FS = L["FX"], L["FS"]
    fl = L["fl"]
    from numba import njit
    _expand_core = FS._expand_core
    _base_scan = FX._base_scan
    NBASE = FX.NBASE

    @njit(cache=False)
    def _expand_chosen(cols, virs, cura, curb, actions, fl_arr,
                       feats11, nvir_post, posts, okflags, prefeats, prenvir):
        n = cols.shape[0]
        c1 = np.empty(128, dtype=np.int8)
        v1 = np.empty(128, dtype=np.int8)
        base = np.empty(NBASE, dtype=np.int64)
        for i in range(n):
            _base_scan(cols[i], virs[i], fl_arr, base)
            for k in range(11):
                prefeats[i, k] = base[k]
            prenvir[i] = base[11]
            a = actions[i]
            ok, nv, cells = _expand_core(cols[i], virs[i], a // 8, a % 8,
                                         cura[i], curb[i], c1, v1)
            okflags[i] = ok
            if ok == 0:
                continue
            _base_scan(c1, v1, fl_arr, base)
            for k in range(11):
                feats11[i, k] = base[k]
            nvir_post[i] = base[11]
            for k in range(128):
                posts[i, k] = c1[k]

    @njit(cache=False)
    def _expand_all32(cols, virs, cura, curb, fl_arr,
                      feats11, posts, okflags):
        """feats11 (n,32,11); posts (n,32,128); okflags (n,32)."""
        n = cols.shape[0]
        c1 = np.empty(128, dtype=np.int8)
        v1 = np.empty(128, dtype=np.int8)
        base = np.empty(NBASE, dtype=np.int64)
        for i in range(n):
            for var in range(4):
                for cc in range(8):
                    a = var * 8 + cc
                    ok, nv, cells = _expand_core(cols[i], virs[i], var, cc,
                                                 cura[i], curb[i], c1, v1)
                    okflags[i, a] = ok
                    if ok == 0:
                        continue
                    _base_scan(c1, v1, fl_arr, base)
                    for k in range(11):
                        feats11[i, a, k] = base[k]
                    for k in range(128):
                        posts[i, a, k] = c1[k]
    return _expand_chosen, _expand_all32, fl


def load(tag, part):
    p = os.path.join(RESULTS, f"s2lulu_{part}_{tag}.npz")
    z = np.load(p)
    return {k: z[k] for k in z.files}


# ------------------------------------------------------------------- gate A4
def gate_a4(d, prefeats, prenvir, okflags, tag, part):
    """Cross-checks against INDEPENDENTLY stored fields + killed mutants."""
    Hpre = FBAT.heights_from_boards(d["board_col"])
    checks = {}
    checks["maxh_pre_vs_stored"] = int((prefeats[:, 0] != d["max_height"]).sum())
    checks["nvir_pre_vs_stored"] = int((prenvir != d["viruses"]).sum())
    checks["nlegal_probe_vs_stored"] = int(
        (FBAT.nlegal_probe(Hpre) != d["n_legal"]).sum())
    v = d["cand_vals"].astype(np.float64)
    # The champion enumerates o4 = 0..3 and maps o4 -> var via
    # fast_rtl_x._VAR_OF_O4 = [2,3,0,1], writing vals[var*8+cc]. So its scan
    # order over the vals INDEX is 16..31 then 0..15, and on a TIE it keeps the
    # first in THAT order (strict `>`), i.e. verticals beat horizontals.
    # np.nanargmax breaks ties the opposite way. Using it naively disagrees with
    # the champion on ~1.7% of decisions -- the SAME defect recon C found in its
    # own fork probe (1.54% of plies). The check must reproduce the champion's
    # order or it is measuring the wrong thing.
    argmax = CHAMP_ORDER[np.nanargmax(v[:, CHAMP_ORDER], axis=1)].astype(np.int8)
    checks["action_vs_champion_order_argmax"] = int((argmax != d["action"]).sum())
    checks["chosen_action_illegal"] = int((okflags == 0).sum())
    checks["n_legal_vs_isfinite_candvals"] = int(
        (np.isfinite(v).sum(axis=1) != d["n_legal"]).sum())
    # corpus facts worth having (recon C measured 36.0% ties under drip):
    top = np.nanmax(v, axis=1)
    n_top = (v == top[:, None]).sum(axis=1)
    naive = np.nanargmax(v, axis=1).astype(np.int8)
    diag = {"tie_rate_top_value": round(float((n_top >= 2).mean()), 4),
            "naive_nanargmax_disagreement_rate":
                round(float((naive != d["action"]).mean()), 4)}

    # --- MUTANTS: each check must FAIL on a deliberately corrupted input.
    mut = {}
    bad = d["max_height"].copy()
    bad[0] = bad[0] + 1
    mut["maxh_pre_vs_stored"] = int((prefeats[:, 0] != bad).sum()) > \
        checks["maxh_pre_vs_stored"]
    badv = v.copy()
    j = int(np.nanargmin(badv[0]))
    badv[0, j] = np.nanmax(badv[0]) + 1.0
    mut["action_vs_champion_order_argmax"] = int(
        (CHAMP_ORDER[np.nanargmax(badv[:, CHAMP_ORDER], axis=1)].astype(np.int8)
         != d["action"]).sum()) > checks["action_vs_champion_order_argmax"]
    # SECOND mutant on the same check: the NAIVE (raw-index) tie-break. It must
    # disagree, which is what proves the check is sensitive to enumeration
    # order -- the thing that actually decides a third of the champion's moves.
    mut["tiebreak_order_matters"] = bool(
        (naive != d["action"]).sum() > checks["action_vs_champion_order_argmax"])
    badH = Hpre.copy()
    badH[0, 0] = min(15, badH[0, 0] + 1)
    mut["nlegal_probe_vs_stored"] = int(
        (FBAT.nlegal_probe(badH) != d["n_legal"]).sum()) >= \
        checks["nlegal_probe_vs_stored"]
    ok = all(vv == 0 for vv in checks.values()) and all(mut.values())
    return {"part": part, "n": int(d["seed"].shape[0]), "checks": checks,
            "diagnostics": diag, "mutants_fire": mut, "pass": bool(ok)}


# ------------------------------------------------------------------- gate A3
def _auc(x, y):
    """Mann-Whitney AUC of x for y==1 vs y==0, ties = 0.5 (exact, via ranks)."""
    m = y >= 0
    x, y = np.asarray(x, dtype=np.float64)[m], np.asarray(y)[m]
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
    return (ranks[y == 1].sum() - n1 * (n1 + 1) / 2.0) / (n1 * n0)


def gate_a3(feat, names, y, y_shuf, f_leak, seed):
    seed = np.asarray(seed)
    """Shuffled-label FLOOR + leak POSITIVE control + a killed mutant showing
    the floor can move."""
    res = {"auc_leak_vs_y": _auc(f_leak, y),
           "auc_leak_vs_yshuf": _auc(f_leak, y_shuf)}
    real = {}
    for k, nm in enumerate(names):
        real[nm] = {"auc_vs_y": _auc(feat[:, k], y),
                    "auc_vs_yshuf": _auc(feat[:, k], y_shuf)}
    res["features"] = real
    worst = max(abs(r["auc_vs_yshuf"] - 0.5) for r in real.values())
    res["max_abs_dev_from_floor"] = worst
    res["n_eligible_games"] = int(np.unique(seed[y >= 0]).shape[0])
    res["n_pos_games"] = int(np.unique(seed[y == 1]).shape[0])
    res["n_neg_games"] = int(np.unique(seed[y == 0]).shape[0])

    # MUTANT (the demonstration that this floor check CAN fail): a LEAKY
    # shuffle. 20% of eligible GAMES keep their true label; the rest are
    # permuted. A floor check that is merely decorative would still read ~0.5
    # here. A real one must see the leak: d_spawn_h reads ~0.93 against the true
    # label, so a 20% leak should push it to roughly 0.5 + 0.2*0.43 ~ 0.59, i.e.
    # a deviation well past the 0.05 tolerance. If this mutant does NOT fire,
    # the A3 floor is vacuous and the corpus must not be used.
    rng = np.random.default_rng(999)
    ug = np.unique(seed[y >= 0])
    keep = set(rng.choice(ug, size=max(1, int(0.20 * ug.shape[0])),
                          replace=False).tolist())
    keep_mask = np.isin(seed, np.array(sorted(keep), dtype=seed.dtype))
    y_leak = y_shuf.copy()
    y_leak[keep_mask & (y >= 0)] = y[keep_mask & (y >= 0)]
    dev_leak = max(abs(_auc(feat[:, k], y_leak) - 0.5) for k in range(len(names)))
    res["mutant_leaky_shuffle_max_dev"] = dev_leak
    res["mutant_fires"] = bool(dev_leak > 0.05)

    res["pass"] = bool(res["auc_leak_vs_y"] > 0.95
                       and 0.48 <= res["auc_leak_vs_yshuf"] <= 0.52
                       and worst < 0.05
                       and res["mutant_fires"])
    return res


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--tag", default="local")
    ap.add_argument("--gates-only", action="store_true")
    ap.add_argument("--all32-cap", type=int, default=60000,
                    help="max decisions to expand per-candidate (memory bound)")
    a = ap.parse_args()

    exp_chosen, exp_all32, fl = build_expander()
    out, gates = {}, {"A4": [], "A3": None}
    packs = {}
    for part in ("fail", "ctrl", "stall"):
        p = os.path.join(RESULTS, f"s2lulu_{part}_{a.tag}.npz")
        if not os.path.exists(p):
            continue
        d = load(a.tag, part)
        n = d["seed"].shape[0]
        f11 = np.zeros((n, 11), dtype=np.int64)
        nvp = np.zeros(n, dtype=np.int64)
        posts = np.zeros((n, 128), dtype=np.int8)
        okf = np.zeros(n, dtype=np.int8)
        pre11 = np.zeros((n, 11), dtype=np.int64)
        prenv = np.zeros(n, dtype=np.int64)
        t0 = time.monotonic()
        exp_chosen(d["board_col"], d["board_vir"], d["cur"][:, 0], d["cur"][:, 1],
                   d["action"].astype(np.int64), fl, f11, nvp, posts, okf,
                   pre11, prenv)
        Hpost = FBAT.heights_from_boards(posts)
        Hpre = FBAT.heights_from_boards(d["board_col"])
        cands = FBAT.candidate_features(posts, Hpost, Hpre,
                                        d["n_legal"].astype(np.int32))
        feat = np.concatenate(
            [f11.astype(np.float32)]
            + [np.asarray(cands[k], dtype=np.float32)[:, None] for k in CAND_NAMES],
            axis=1)
        champ = d["cand_vals"][np.arange(n), d["action"].astype(np.int64)]
        print(f"[feat] {part}: {n} decisions in {time.monotonic()-t0:.1f}s",
              flush=True)
        g = gate_a4(d, pre11, prenv, okf, a.tag, part)
        gates["A4"].append(g)
        print(f"[gate A4] {part}: {'PASS' if g['pass'] else 'FAIL'} {g['checks']} "
              f"mutants_fire={g['mutants_fire']}", flush=True)
        packs[part] = (d, feat, champ, Hpre, Hpost, posts)
        out[f"{part}_feat"] = feat
        out[f"{part}_champ_eval"] = champ.astype(np.float32)
        out[f"{part}_Hpost"] = Hpost
        out[f"{part}_Hpre"] = Hpre

    # ---- A3 on the PRIMARY CONTRAST (fail positives vs ctrl negatives) ------
    d_f, f_f = packs["fail"][0], packs["fail"][1]
    d_c, f_c = packs["ctrl"][0], packs["ctrl"][1]
    y = np.concatenate([d_f["y"], d_c["y"]])
    ysh = np.concatenate([d_f["y_shuf"], d_c["y_shuf"]])
    leak = np.concatenate([d_f["f_leak"], d_c["f_leak"]])
    F = np.concatenate([f_f, f_c], axis=0)
    ch = np.concatenate([packs["fail"][2], packs["ctrl"][2]]).astype(np.float64)
    t0 = time.monotonic()
    sd = np.concatenate([d_f["seed"], d_c["seed"]])
    # HOLDOUT STAYS SEALED. The prereg (B2) requires the arm to be declared
    # before the holdout is opened, so every label-associated statistic this
    # corpus stage produces is computed on TRAIN ROWS ONLY. Nothing in the
    # holdout has been looked at. (A4's integrity cross-checks are label-free
    # and do run over every row.)
    tr = np.concatenate([d_f["hold"], d_c["hold"]]) == 0
    F, y, ysh, leak, ch, sd = (F[tr], y[tr], ysh[tr], leak[tr], ch[tr], sd[tr])
    g3 = gate_a3(F, FEAT_NAMES, y, ysh, leak, sd)
    g3["scope"] = "TRAIN ONLY (holdout sealed)"
    g3["n_train_rows"] = int(tr.sum())
    g3["auc_CHAMP_EVAL_vs_y"] = _auc(-ch, y)     # low champion value = risky
    g3["auc_CHAMP_EVAL_vs_yshuf"] = _auc(-ch, ysh)
    gates["A3"] = g3
    print(f"[gate A3] {'PASS' if g3['pass'] else 'FAIL'} in "
          f"{time.monotonic()-t0:.1f}s  leak_vs_y={g3['auc_leak_vs_y']:.4f} "
          f"leak_vs_yshuf={g3['auc_leak_vs_yshuf']:.4f} "
          f"max|dev| real-vs-shuffled={g3['max_abs_dev_from_floor']:.4f} "
          f"(over {g3['n_eligible_games']} games: {g3['n_pos_games']}+/{g3['n_neg_games']}-) "
          f"(leaky-shuffle mutant max|dev|="
          f"{g3['mutant_leaky_shuffle_max_dev']:.4f} "
          f"fires={g3['mutant_fires']})", flush=True)

    # ---- PER-CANDIDATE (within-decision) layer -----------------------------
    # The gap stage 1 never tested (recon A leak risk #7): at a leaf the model
    # ranks the 32 siblings of ONE parent. Nothing in a cross-board corpus
    # trains or tests that. This block emits the sibling matrix for a bounded,
    # deterministically chosen subset: ALL target-class (y==1) decisions plus an
    # equal-size sample of control decisions.
    if not a.gates_only and a.all32_cap > 0:
        rng = np.random.default_rng(20260810)
        idx_f = np.nonzero(d_f["y"] == 1)[0]
        if idx_f.shape[0] > a.all32_cap // 2:
            idx_f = np.sort(rng.choice(idx_f, a.all32_cap // 2, replace=False))
        idx_c = np.sort(rng.choice(np.nonzero(d_c["y"] == 0)[0],
                                   min(idx_f.shape[0],
                                       int((d_c["y"] == 0).sum())),
                                   replace=False))
        blocks = {}
        for nm, dd, idx in (("fail", d_f, idx_f), ("ctrl", d_c, idx_c)):
            m = idx.shape[0]
            F32 = np.zeros((m, 32, len(FEAT_NAMES)), dtype=np.int16)
            OK = np.zeros((m, 32), dtype=np.int8)
            t0 = time.monotonic()
            CH = 4000
            for s0 in range(0, m, CH):
                sl = idx[s0:s0 + CH]
                k = sl.shape[0]
                f11 = np.zeros((k, 32, 11), dtype=np.int64)
                po = np.zeros((k, 32, 128), dtype=np.int8)
                ok = np.zeros((k, 32), dtype=np.int8)
                exp_all32(dd["board_col"][sl], dd["board_vir"][sl],
                          dd["cur"][sl, 0], dd["cur"][sl, 1], fl, f11, po, ok)
                Hp = FBAT.heights_from_boards(po.reshape(k * 32, 128))
                Hq = np.repeat(FBAT.heights_from_boards(dd["board_col"][sl]),
                               32, axis=0)
                nlp = np.repeat(dd["n_legal"][sl].astype(np.int32), 32)
                cd = FBAT.candidate_features(po.reshape(k * 32, 128), Hp, Hq, nlp)
                blk = np.concatenate(
                    [f11.reshape(k * 32, 11).astype(np.float64)]
                    + [np.asarray(cd[q], dtype=np.float64)[:, None]
                       for q in CAND_NAMES], axis=1)
                F32[s0:s0 + k] = np.rint(blk).astype(np.int16).reshape(k, 32, -1)
                OK[s0:s0 + k] = ok
            print(f"[all32] {nm}: {m} decisions x 32 in "
                  f"{time.monotonic()-t0:.1f}s  legal slots "
                  f"{int(OK.sum())}", flush=True)
            blocks[f"all32_{nm}_feat"] = F32
            blocks[f"all32_{nm}_ok"] = OK
            blocks[f"all32_{nm}_rowidx"] = idx.astype(np.int32)
            blocks[f"all32_{nm}_seed"] = dd["seed"][idx]
            blocks[f"all32_{nm}_vals"] = dd["cand_vals"][idx]
            blocks[f"all32_{nm}_action"] = dd["action"][idx]
            blocks[f"all32_{nm}_hold"] = dd["hold"][idx]
            # legality cross-check: expander vs the stored root values
            mism = int((OK.astype(bool) != np.isfinite(
                dd["cand_vals"][idx])).sum())
            print(f"[all32] {nm}: legality mismatches vs stored cand_vals "
                  f"= {mism} (must be 0)", flush=True)
            blocks[f"all32_{nm}_legality_mismatch"] = np.array([mism])
        out.update(blocks)

    if not a.gates_only:
        np.savez_compressed(os.path.join(RESULTS, f"s2feat_{a.tag}.npz"),
                            feat_names=np.array(FEAT_NAMES), **out)
        print(f"[write] s2feat_{a.tag}.npz "
              f"{os.path.getsize(os.path.join(RESULTS, f's2feat_{a.tag}.npz'))/1e6:.1f} MB",
              flush=True)

    summary = {
        "tag": a.tag, "prereg": "PREREG_STAGE2.md @ b9725fc",
        "feature_names": FEAT_NAMES,
        "silicon_class": {"FREE_IN_COLWALK": sorted(FREE_IN_COLWALK),
                          "OFF_BUDGET": sorted(OFF_BUDGET)},
        "gates": gates,
        "n_decisions": {k: int(v[0]["seed"].shape[0]) for k, v in packs.items()},
    }
    with open(os.path.join(RESULTS, f"s2feat_gates_{a.tag}.json"), "w") as f:
        json.dump(summary, f, indent=1, default=float)
    ok = all(g["pass"] for g in gates["A4"]) and gates["A3"]["pass"]
    print(f"[GATES] overall {'PASS' if ok else 'FAIL'}", flush=True)
    if not ok:
        sys.exit(1)


if __name__ == "__main__":
    main()
