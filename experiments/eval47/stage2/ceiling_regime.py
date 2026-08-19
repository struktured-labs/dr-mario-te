#!/usr/bin/env python3
"""STAGE 2 CEILING, part 3: regime decomposition, shuffled-control DISTRIBUTION,
and the COUNTERFACTUAL within-decision test.

Plan frozen in ceiling_fit.py's docstring; this file executes the parts of L1-L6 not
covered by ceiling_probe.py, plus one addition declared here BEFORE it was run:

  ** L7 COUNTERFACTUAL WITHIN-DECISION TEST (new, and the strongest test available). **
  The corpus label is a game outcome broadcast onto decisions with NO counterfactual
  (PREREG sec 3.2 names this as the corpus's biggest defect). recon C's FORK data
  (tmp/reconC/fork_*.jsonl) is a per-ply, per-ACTION forked rollout: for every legal
  action of a ply it records the fate of a continuation of S pills. That is a TRUE
  per-decision label, produced by a completely different procedure (forked rollouts,
  not game outcomes), on boards the model was trained on only through the broadcast
  label.
  JOIN VALIDATION (killed-mutant shaped): the fork's own champion choice `a_ch` must
  equal the corpus's stored `action` on the joined (seed, pill_idx) key. A wrong join
  breaks it. Measured before any scoring: 852/864. The 12 disagreements are the
  DOCUMENTED naive-vs-champion enumeration-order defect (corpus deviation log entry 2
  measured 1.71% naive disagreement; 12/864 = 1.39%), so the join is verified and the
  residual is a known, quantified instrument difference -- those plies are dropped.
  ENDPOINT: within-decision AUC of "this action survives" against each ranker, over the
  plies where survival is DISCRIMINATIVE (>=1 survivor AND >=1 fatal action). A ranker
  that cannot beat 0.5 here cannot rescue anything, whatever its cross-board AUC says.
"""
from __future__ import annotations

import json
import os
import pickle
import sys
import time

import numpy as np

os.environ.setdefault("OMP_NUM_THREADS", "6")
HERE = os.path.dirname(os.path.abspath(__file__))
EV = os.path.dirname(HERE)                       # experiments/eval47
QA = os.path.dirname(os.path.dirname(EV))        # worktree root (NOT experiments/)
V2 = os.path.join(EV, "vocab2")
for _p in (HERE, EV, QA, V2, os.path.join(EV, "jointdig")):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from sklearn.ensemble import HistGradientBoostingClassifier  # noqa: E402
import feature_battery as FBAT  # noqa: E402
from ceiling_fit import auc_fast, boot_paired, load, NAMES11, SEED, INNER_MOD, OUT, RES  # noqa

FORK_FILES = ["fork_main.jsonl", "fork_final_uninstrumented.jsonl", "fork_ctl.jsonl"]


def within_auc(risk, surv):
    """P(risk(fatal) > risk(survivor)) + 0.5*ties, one decision."""
    r_s = risk[surv]
    r_f = risk[~surv]
    if len(r_s) == 0 or len(r_f) == 0:
        return np.nan
    gt = (r_f[:, None] > r_s[None, :]).sum()
    eq = (r_f[:, None] == r_s[None, :]).sum()
    return (gt + 0.5 * eq) / (len(r_s) * len(r_f))


def main():
    t0 = time.time()
    d = load()
    names = d["names"]
    IDX = {n: i for i, n in enumerate(names)}
    X, y, seeds, hold = d["X"], d["y"].astype(int), d["seed"], d["hold"]
    tr, ho = ~hold, hold
    Xtr, ytr = X[tr], y[tr]
    inner = np.isin(seeds[tr] % 10, INNER_MOD)
    with open(os.path.join(OUT, "ceiling_best.pkl"), "rb") as f:
        pk = pickle.load(f)
    m, sgn, sd = pk["model"], pk["sgn"], pk["sd"]
    sfn = lambda M, Z: M.decision_function(Z)
    cfg = pk["cfg"]
    out = {"prereg": "PREREG_STAGE2.md @ b9725fc", "best_cfg": cfg}

    sc = sfn(m, X[ho])
    champ = sgn * d["champ"][ho]
    dshv = sd * X[ho][:, IDX["d_spawn_h"]].astype(np.float64)
    b11cols = [IDX[n] for n in NAMES11]
    kw = {k: v for k, v in cfg["cfg"].items() if k != "kind"}
    m11 = HistGradientBoostingClassifier(max_iter=cfg["n_iter"], max_bins=255,
                                         early_stopping=False, random_state=SEED, **kw)
    m11.fit(Xtr[:, b11cols], ytr)
    s11 = m11.decision_function(X[ho][:, b11cols])
    yh = y[ho]
    sdh = seeds[ho]

    # ---------------- SHUFFLED CONTROL as a DISTRIBUTION (prereg amendment: read
    # against the MEASURED null, not one guessed draw). K independent GAME-level
    # permutations, refit end-to-end each time.
    print("shuffled-control distribution", flush=True)
    uq = np.unique(seeds)
    gy = {}
    for s_, yy_ in zip(seeds, y):
        gy[int(s_)] = int(yy_)
    lab = np.array([gy[int(s_)] for s_ in uq])
    rng = np.random.default_rng(777)
    shuf = []
    for rep in range(10):
        perm = rng.permutation(lab)
        mp = {int(s_): int(v) for s_, v in zip(uq, perm)}
        ys = np.array([mp[int(s_)] for s_ in seeds])
        mm = HistGradientBoostingClassifier(max_iter=cfg["n_iter"], max_bins=255,
                                            early_stopping=False, random_state=SEED, **kw)
        mm.fit(Xtr, ys[tr])
        p = mm.decision_function(X[ho])
        shuf.append(dict(auc_vs_shuffled=auc_fast(ys[ho], p),
                         auc_vs_true_y=auc_fast(yh, p),
                         game_corr=float(np.corrcoef(lab, perm)[0, 1])))
        print("  rep", rep, shuf[-1], flush=True)
    a_s = np.array([r["auc_vs_shuffled"] for r in shuf])
    a_t = np.array([r["auc_vs_true_y"] for r in shuf])
    out["shuffled_control"] = dict(
        K=10, reps=shuf,
        auc_vs_shuffled_mean=float(a_s.mean()),
        auc_vs_shuffled_range=[float(a_s.min()), float(a_s.max())],
        auc_vs_true_y_mean=float(a_t.mean()),
        auc_vs_true_y_range=[float(a_t.min()), float(a_t.max())],
        prereg_single_draw_note=("The pre-registered single draw (seed 20260810, NOT "
                                 "re-rolled) has game-level corr(y,y_shuf)=0.0524 on "
                                 "2,255 games vs an expected |corr| ~ 0.021, and its "
                                 "refit reads 0.5497 against the TRUE label. That is "
                                 "draw noise in one permutation, which is exactly why "
                                 "the prereg was amended to read against a MEASURED "
                                 "null band rather than one draw."))

    # ---------------- regime decomposition with per-band paired CI
    tte, mh, slg, vir = d["t_to_end"][ho], d["max_height"][ho], \
        d["since_last_garbage"][ho], d["viruses"][ho]
    gcum = d["garbage_cum"][ho]

    def cell(mask, boot=True):
        if mask.sum() < 200 or yh[mask].sum() < 20 or (yh[mask] == 0).sum() < 20:
            return None
        r = dict(n=int(mask.sum()), npos=int(yh[mask].sum()),
                 auc_model=auc_fast(yh[mask], sc[mask]),
                 auc_champ=auc_fast(yh[mask], champ[mask]),
                 auc_dsh=auc_fast(yh[mask], dshv[mask]),
                 auc_base11gbm=auc_fast(yh[mask], s11[mask]))
        r["delta_model_minus_champ"] = r["auc_model"] - r["auc_champ"]
        r["delta_dsh_minus_champ"] = r["auc_dsh"] - r["auc_champ"]
        if boot:
            b = boot_paired(yh[mask], sdh[mask], sc[mask], champ[mask], B=200,
                            seed=SEED + 21)
            r["ci_model_minus_champ"] = [b[1], b[2]]
        return r

    reg = {}
    reg["t_to_end"] = {lab_: cell(mm_) for lab_, mm_ in [
        ("<=2", tte <= 2), ("3-9", (tte >= 3) & (tte <= 9)),
        ("10-30", (tte >= 10) & (tte <= 30)),
        ("31-90", (tte >= 31) & (tte <= 90)), (">90", tte > 90)]}
    reg["max_height"] = {lab_: cell(mm_) for lab_, mm_ in [
        ("h<=9", mh <= 9), ("h10-12", (mh >= 10) & (mh <= 12)),
        ("h13-14", (mh >= 13) & (mh <= 14)), ("h15-16", mh >= 15)]}
    reg["pressure"] = {lab_: cell(mm_) for lab_, mm_ in [
        ("clean: no garbage yet", gcum == 0),
        ("pressured: garbage seen", gcum > 0),
        ("fresh volley slg<=3", slg <= 3),
        ("slg 4-12", (slg >= 4) & (slg <= 12)),
        ("slg>12", slg > 12)]}
    reg["viruses_left"] = {lab_: cell(mm_) for lab_, mm_ in [
        ("v<=8", vir <= 8), ("v9-24", (vir >= 9) & (vir <= 24)), ("v>24", vir > 24)]}
    q = np.quantile(slg, np.linspace(0, 1, 11))
    reg["slg_deciles"] = {}
    for i in range(10):
        lo, hi = q[i], q[i + 1]
        mm_ = (slg >= lo) & (slg <= hi) if i == 9 else (slg >= lo) & (slg < hi)
        reg["slg_deciles"][f"d{i+1}[{lo:.0f},{hi:.0f}]"] = cell(mm_, boot=False)
    out["regime"] = reg
    for k, v in reg.items():
        print(k, {kk: (None if vv is None else
                       (round(vv["auc_model"], 4), round(vv["auc_champ"], 4)))
                  for kk, vv in v.items()}, flush=True)

    # ---------------- IMMINENCE test: within POSITIVE games only, does the score rank
    # near-death decisions above far-from-death ones? (generic badness vs a clock)
    pos = yh == 1
    imm = {}
    for nm, s_ in (("model", sc), ("champ", champ), ("d_spawn_h", dshv)):
        m2 = pos & ((tte <= 9) | (tte > 30))
        imm[nm] = auc_fast(tte[m2] <= 9, s_[m2])
    imm["n"] = int((pos & ((tte <= 9) | (tte > 30))).sum())
    imm["note"] = ("AUC of 'this decision is within 9 plies of the topout' vs the ranker, "
                   "positive games only. 0.5 = the ranker carries no proximity "
                   "information and is a board-badness reading, not a clock.")
    out["imminence"] = imm
    print("IMMINENCE", imm, flush=True)

    # ---------------- L7 COUNTERFACTUAL WITHIN-DECISION TEST
    print("counterfactual fork join", flush=True)
    import s2_features as S2F
    exp_chosen, exp_all32, fl = S2F.build_expander()
    F = d["F"]
    keymap = {}
    for i, (s_, p_) in enumerate(zip(F["seed"], F["pill_idx"])):
        keymap[(int(s_), int(p_))] = i
    recs = []
    for fn in FORK_FILES:
        pth = os.path.join(QA, "tmp", "reconC", fn)
        if not os.path.exists(pth):
            continue
        for line in open(pth):
            line = line.strip()
            if line:
                r = json.loads(line)
                r["_src"] = fn
                recs.append(r)
    rows, plies = [], []
    join_ok = join_bad = 0
    for r in recs:
        for p in r.get("plies", []):
            k = (int(r["seed"]), int(p["t"]))
            if k not in keymap:
                continue
            i = keymap[k]
            if int(F["action"][i]) != int(p["a_ch"]):
                join_bad += 1
                continue          # documented enumeration-order difference; drop
            join_ok += 1
            rows.append(i)
            plies.append(p)
    rows = np.array(rows, dtype=np.int64)
    print(f"  join: {join_ok} verified, {join_bad} dropped (enumeration-order)", flush=True)

    k = len(rows)
    f11 = np.zeros((k, 32, 11), dtype=np.int64)
    po = np.zeros((k, 32, 128), dtype=np.int8)
    ok32 = np.zeros((k, 32), dtype=np.int8)
    exp_all32(F["board_col"][rows], F["board_vir"][rows],
              F["cur"][rows, 0], F["cur"][rows, 1], fl, f11, po, ok32)
    Hp = FBAT.heights_from_boards(po.reshape(k * 32, 128))
    Hq = np.repeat(FBAT.heights_from_boards(F["board_col"][rows]), 32, axis=0)
    nlp = np.repeat(F["n_legal"][rows].astype(np.int32), 32)
    cd = FBAT.candidate_features(po.reshape(k * 32, 128), Hp, Hq, nlp)
    blk = np.concatenate([f11.reshape(k * 32, 11).astype(np.float64)]
                         + [np.asarray(cd[q_], dtype=np.float64)[:, None]
                            for q_ in FBAT.CAND_NAMES], axis=1).astype(np.float32)
    risk_all = sfn(m, blk).reshape(k, 32)
    dsh_all = sd * blk[:, IDX["d_spawn_h"]].astype(np.float64).reshape(k, 32)
    cv = F["cand_vals"][rows]
    # legality cross-check vs stored root values (must be 0) -- a killed-mutant-shaped
    # guard that the expander is aligned with the corpus
    mismatch = int((ok32.astype(bool) != np.isfinite(cv)).sum())

    res = {"n_plies_joined": int(k), "join_dropped_enum_order": int(join_bad),
           "legality_mismatch": mismatch, "S_budget_note":
           "survival set taken from the fork file's own `surv` list (its own S budget)"}
    per = {"model": [], "champ": [], "d_spawn_h": []}
    top1 = {"model": 0, "champ": 0, "d_spawn_h": 0, "champ_actual": 0}
    n_disc = 0
    seeds_d = []
    resc = {"model": 0, "d_spawn_h": 0, "n": 0}
    for j, p in enumerate(plies):
        legal = np.array([a[0] for a in p["acts"]], dtype=int)
        if legal.size == 0:
            continue
        survset = set(int(a[0]) for a in p["surv"])
        surv = np.array([a in survset for a in legal], dtype=bool)
        if surv.all() or (~surv).all():
            continue                     # non-discriminative
        n_disc += 1
        seeds_d.append(int(F["seed"][rows[j]]))
        rm = risk_all[j, legal]
        rc = -cv[j, legal].astype(np.float64)      # champion: high value = safe
        rd = dsh_all[j, legal]
        per["model"].append(within_auc(rm, surv))
        per["champ"].append(within_auc(rc, surv))
        per["d_spawn_h"].append(within_auc(rd, surv))
        top1["model"] += int(surv[np.argmin(rm)])
        top1["champ"] += int(surv[np.argmin(rc)])
        top1["d_spawn_h"] += int(surv[np.argmin(rd)])
        ach = int(F["action"][rows[j]])
        top1["champ_actual"] += int(ach in survset)
        # RESCUE SET: champion's actual move dies, but a survivor exists
        if ach not in survset:
            resc["n"] += 1
            resc["model"] += int(surv[np.argmin(rm)])
            resc["d_spawn_h"] += int(surv[np.argmin(rd)])
    seeds_d = np.array(seeds_d)
    res["n_discriminative"] = n_disc
    res["n_seeds"] = int(len(np.unique(seeds_d)))
    for nm in per:
        v = np.array(per[nm], dtype=float)
        res[f"within_auc_{nm}"] = float(np.nanmean(v))
    # seed-clustered bootstrap on the paired within-decision AUC difference
    vm = np.array(per["model"]); vc = np.array(per["champ"]); vd = np.array(per["d_spawn_h"])
    rng2 = np.random.default_rng(SEED + 31)
    uqs = np.unique(seeds_d)
    dif_mc, dif_dc = [], []
    for _ in range(2000):
        draw = rng2.choice(uqs, len(uqs), replace=True)
        sel = np.concatenate([np.flatnonzero(seeds_d == s_) for s_ in draw])
        dif_mc.append(np.nanmean(vm[sel]) - np.nanmean(vc[sel]))
        dif_dc.append(np.nanmean(vd[sel]) - np.nanmean(vc[sel]))
    res["model_minus_champ"] = dict(mean=float(np.mean(dif_mc)),
                                    ci=[float(np.percentile(dif_mc, 2.5)),
                                        float(np.percentile(dif_mc, 97.5))],
                                    frac_pos=float(np.mean(np.array(dif_mc) > 0)))
    res["dsh_minus_champ"] = dict(mean=float(np.mean(dif_dc)),
                                  ci=[float(np.percentile(dif_dc, 2.5)),
                                      float(np.percentile(dif_dc, 97.5))],
                                  frac_pos=float(np.mean(np.array(dif_dc) > 0)))
    res["top1_survives"] = {kk: (vv / n_disc if n_disc else None)
                            for kk, vv in top1.items()}
    res["rescue_set"] = dict(n=resc["n"],
                             model_top1_survives=(resc["model"] / resc["n"]
                                                  if resc["n"] else None),
                             dsh_top1_survives=(resc["d_spawn_h"] / resc["n"]
                                                if resc["n"] else None),
                             note=("plies where the champion's ACTUAL move dies within "
                                   "the fork budget but >=1 legal action survives -- the "
                                   "rescuable set"))
    out["counterfactual"] = res
    print("COUNTERFACTUAL", json.dumps(res, indent=1, default=float), flush=True)

    with open(os.path.join(OUT, "ceiling_regime.json"), "w") as f:
        json.dump(out, f, indent=1, default=float)
    print("wrote ceiling_regime.json", time.time() - t0, flush=True)


if __name__ == "__main__":
    main()
