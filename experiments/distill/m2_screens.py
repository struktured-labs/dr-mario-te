"""m2_screens.py — M2 offline distillation screens (REGISTRATION_M2_SCREENS.md).

Stage `instruments` (this file's first deliverable): measure the FLOOR and
CEILING that every M2 bar is a fraction of (R38), per stratum, before any fit
exists.

Statistic (confirm-halves only — the screen forks chose the shortlist, so
including them would re-import selection; the vacuous-control and
range-restriction lessons of M1 apply):
  dec-half  = sum(s2[0:3])  per shortlist candidate  (0..3)
  eval-half = sum(s2[3:6])  per shortlist candidate  (0..3)
  A decider D maps a state to a shortlist candidate or STAND (champion pick).
  capture(D) = mean over states of eval_half(D(state)) - eval_half(champ).
  (STAND contributes 0 by construction; capture is in eval-half survival
  points, 0..3 scale.)

CEILING = the tribunal itself decided from the dec-half at the half-scaled
promoted rule (override iff champ_dec <= 1 AND best_dec - champ_dec >= 2,
pick argmax (dec_half, champ value)), scored on the eval-half. This is what
perfect imitation of the teacher's verdict could earn under label noise.
FLOOR = the same decision procedure with dec-half sums permuted across
candidates within state (val tiebreak intact), scored on the true eval-half;
20 draws, mean +/- sd (R38a).

Populations: all non-degenerate states; the danger subset (champ_s2 <= 3)
reported alongside (M2's effective-n rider). Strata never pooled.
"""
import glob
import gzip
import json
import os
import random
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "out", "labels_m1")


def load(stratum, include_smoke=False):
    out = []
    for f in sorted(glob.glob(os.path.join(OUT, stratum, "seed_*.json.gz"))):
        r = json.load(gzip.open(f, "rt"))
        assert r.get("schema") == "m1v1", f
        if r["smoke"] and not include_smoke:
            continue
        out.append(r)
    return out


def state_view(adj):
    """(shortlist dec/eval/val arrays, champ index in shortlist) or None."""
    sh = [c for c in adj["cands"] if "s2" in c]
    champ_i = None
    for i, c in enumerate(sh):
        if c["rep_slot"] == adj["champ_rep"]:
            champ_i = i
    if champ_i is None or len(sh) < 2:
        return None
    dec = np.array([sum(c["s2"][0:3]) for c in sh], float)
    ev = np.array([sum(c["s2"][3:6]) for c in sh], float)
    val = np.array([c["val"] for c in sh], float)
    return dec, ev, val, champ_i


def decide(dec, val, champ_i):
    """Half-scaled promoted rule on the dec-half. Returns chosen index."""
    order = sorted(range(len(dec)), key=lambda i: (-dec[i], -val[i]))
    best = order[0]
    if dec[champ_i] <= 1 and dec[best] - dec[champ_i] >= 2 \
            and best != champ_i:
        return best
    return champ_i


def capture(states, permute_rng=None):
    gains = []
    fired = 0
    for dec, ev, val, ci in states:
        d = dec
        if permute_rng is not None:
            idx = permute_rng.sample(range(len(dec)), len(dec))
            d = dec[np.array(idx)]
        pick = decide(d, val, ci)
        if pick != ci:
            fired += 1
        gains.append(ev[pick] - ev[ci])
    return float(np.mean(gains)), fired / max(len(states), 1)


def seed_cluster_ci(recs, fn, b=2000, rng=None):
    """Bootstrap over seeds (games) of a per-state statistic."""
    rng = rng or random.Random(11)
    per_seed = [fn(r) for r in recs]
    per_seed = [p for p in per_seed if p is not None]
    means = []
    for _ in range(b):
        draw = [per_seed[rng.randrange(len(per_seed))] for _ in per_seed]
        num = sum(g for g, n in draw)
        den = sum(n for g, n in draw)
        if den:
            means.append(num / den)
    return (float(np.percentile(means, 2.5)),
            float(np.percentile(means, 97.5)))


def stage_instruments():
    for stratum in ("L20", "L11M"):
        recs = load(stratum)
        views = {}
        for r in recs:
            vs = []
            for a in r["adjudications"]:
                if a["degenerate"]:
                    continue
                v = state_view(a)
                if v is not None:
                    vs.append((v, a["champ_s2"] <= 3))
            views[r["seed"]] = vs
        allv = [v for vs in views.values() for v, _ in vs]
        dangv = [v for vs in views.values() for v, d in vs if d]

        def per_seed_gain(r, danger=False):
            vs = [(v, d) for v, d in views[r["seed"]] if (d or not danger)]
            if not vs:
                return None
            g = 0.0
            for v, _ in vs:
                dec, ev, val, ci = v
                pick = decide(dec, val, ci)
                g += ev[pick] - ev[ci]
            return (g, len(vs))

        ceil_all, dose_all = capture(allv)
        lo, hi = seed_cluster_ci(recs, per_seed_gain)
        ceil_d, dose_d = capture(dangv) if dangv else (float("nan"), 0)
        floors = [capture(allv, permute_rng=random.Random(3000 + i))[0]
                  for i in range(20)]
        floors_d = [capture(dangv, permute_rng=random.Random(3000 + i))[0]
                    for i in range(20)] if dangv else [float("nan")]
        print(f"[m2-instr] {stratum} states={len(allv)} danger={len(dangv)}")
        print(f"[m2-instr] {stratum} CEILING all-states capture="
              f"{ceil_all:.4f} CI[{lo:.4f},{hi:.4f}] dose={dose_all:.4f}")
        print(f"[m2-instr] {stratum} CEILING danger-subset capture="
              f"{ceil_d:.4f} dose={dose_d:.4f}")
        print(f"[m2-instr] {stratum} FLOOR (20 draws) all-states "
              f"mean={np.mean(floors):.4f} sd={np.std(floors):.4f} | "
              f"danger mean={np.mean(floors_d):.4f} "
              f"sd={np.std(floors_d):.4f}")
        hr = ceil_all - np.mean(floors)
        print(f"[m2-instr] {stratum} HEADROOM all-states = {hr:.4f} "
              f"({'usable' if hr > 0.005 else 'NO HEADROOM — M2 cannot '
                 'screen on this stratum'})", flush=True)
    json_path = os.path.join(HERE, "out", "m2_instruments.json")
    print(f"[m2-instr] (numbers above are the R38 anchors; bars get filled "
          f"in REGISTRATION_M2 from these + team-lead sign-off)")




# ===================================================================== fit
# Stage `fit` (REGISTRATION_M2 sec 2, bars signed off 2026-08-28):
#   family = { g_feat1 (single-feature veto rules — ALSO the forbidden-
#              prediction comparator), g_rule2 (2-term conjunction),
#              g_lin (int-quantized linear) }.
#   Decision shape (H16's, rule-25 veto): OVERRIDE iff ghat(champ) <= tau AND
#   max ghat - ghat(champ) >= m; pick argmax (ghat, champ value).
#   Train on TRAIN seeds' full s2 (0..6); score HELD-OUT on the instrument's
#   eval-half ruler (bars: danger GO >= 0.129 CI-LB > 0.099; KILL UB < 0.099).
#   Scope limit (stated): M2 measures g restricted to the tribunal's
#   shortlist (labels exist there); unrestricted deployment is M3's question.
import binascii
import gzip as _gzip

FEATS = ("wide_post", "relief", "dsh_post", "maxh_post", "throat_occ",
         "ridge", "lane_vir", "vir_left", "topdist")
FOUT = os.path.join(HERE, "out", "m2_features")


def held(seed):
    return binascii.crc32(str(seed).encode()) % 4 == 0


def assemble(stratum):
    feats = {}
    for f in glob.glob(os.path.join(FOUT, stratum, "seed_*.json.gz")):
        r = json.load(_gzip.open(f, "rt"))
        if r["replay_gate"] == "PASS":
            feats[r["seed"]] = r["feats"]
    rows = []
    for f in sorted(glob.glob(os.path.join(OUT, stratum, "seed_*.json.gz"))):
        r = json.load(_gzip.open(f, "rt"))
        if r["smoke"] or r["seed"] not in feats:
            continue
        for a in r["adjudications"]:
            if a["degenerate"]:
                continue
            fmap = feats[r["seed"]].get(str(a["ply"]))
            if fmap is None:
                continue
            sh = [c for c in a["cands"] if "s2" in c]
            ci = None
            for i, c in enumerate(sh):
                if c["rep_slot"] == a["champ_rep"]:
                    ci = i
            if ci is None or len(sh) < 2:
                continue
            X = np.array([[fmap[str(c["rep_slot"])][k] for k in FEATS]
                          for c in sh], float)
            rows.append({
                "seed": r["seed"], "ply": a["ply"], "ci": ci, "X": X,
                "s2full": np.array([sum(c["s2"]) for c in sh], float),
                "dec": np.array([sum(c["s2"][0:3]) for c in sh], float),
                "ev": np.array([sum(c["s2"][3:6]) for c in sh], float),
                "val": np.array([c["val"] for c in sh], float),
                "danger": a["champ_s2"] <= 3})
    return rows


def g_capture(rows, score_fn, tau, m, ruler="ev"):
    gains, fired = [], 0
    for r in rows:
        g = score_fn(r["X"])
        order = sorted(range(len(g)), key=lambda i: (-g[i], -r["val"][i]))
        best = order[0]
        pick = r["ci"]
        if g[r["ci"]] <= tau and g[best] - g[r["ci"]] >= m \
                and best != r["ci"]:
            pick = best
            fired += 1
        gains.append(r[ruler][pick] - r[ruler][r["ci"]])
    return float(np.mean(gains)) if gains else float("nan"), \
        fired / max(len(rows), 1)


def seed_ci(rows, score_fn, tau, m, ruler="ev", b=2000):
    per = {}
    for r in rows:
        g = score_fn(r["X"])
        order = sorted(range(len(g)), key=lambda i: (-g[i], -r["val"][i]))
        best = order[0]
        pick = r["ci"]
        if g[r["ci"]] <= tau and g[best] - g[r["ci"]] >= m \
                and best != r["ci"]:
            pick = best
        gn, n = per.get(r["seed"], (0.0, 0))
        per[r["seed"]] = (gn + r[ruler][pick] - r[ruler][r["ci"]], n + 1)
    vals = list(per.values())
    rng = random.Random(23)
    means = []
    for _ in range(b):
        d = [vals[rng.randrange(len(vals))] for _ in vals]
        den = sum(n for _, n in d)
        if den:
            means.append(sum(g for g, _ in d) / den)
    return (float(np.percentile(means, 2.5)),
            float(np.percentile(means, 97.5)))


def fit_grid(rows_tr, score_fn):
    """(tau, m) maximizing TRAIN danger capture on the full-s2 ruler."""
    dang = [r for r in rows_tr if r["danger"]]
    best = (0, 0, -1e9)
    for tau_q in (20, 35, 50):
        for m_q in (10, 20, 35):
            gs = np.concatenate([score_fn(r["X"]) for r in rows_tr])
            tau = float(np.percentile(gs, tau_q))
            m = float(np.percentile(gs, 75)) - float(np.percentile(gs, 75 - m_q))
            cap, _ = g_capture(dang, score_fn, tau, m, ruler="s2full")
            if cap > best[2]:
                best = (tau, m, cap)
    return best[0], best[1]


def stage_fit():
    rows = assemble("L20")
    tr = [r for r in rows if not held(r["seed"])]
    ho = [r for r in rows if held(r["seed"])]
    ho_d = [r for r in ho if r["danger"]]
    print(f"[m2-fit] L20 rows train={len(tr)} held={len(ho)} "
          f"held-danger={len(ho_d)} "
          f"(train-danger={sum(r['danger'] for r in tr)})", flush=True)
    y = np.concatenate([r["s2full"] for r in tr])
    Xall = np.vstack([r["X"] for r in tr])
    mu, sd = Xall.mean(0), Xall.std(0) + 1e-9

    # --- g_lin: ridge on full-s2, then int8 quantization (deployable form)
    Xz = (Xall - mu) / sd
    w = np.linalg.solve(Xz.T @ Xz + 10.0 * np.eye(len(FEATS)), Xz.T @ y)
    wq = np.round(w / np.abs(w).max() * 63).astype(int)

    def g_lin(X):
        return ((X - mu) / sd) @ wq

    # --- g_feat1: best single-feature rule on TRAIN (the S3 comparator)
    best1 = None
    dang_tr = [r for r in tr if r["danger"]]
    for j, name in enumerate(FEATS):
        for sgn in (1, -1):
            def sf(X, j=j, sgn=sgn):
                return sgn * X[:, j]
            tau, m = fit_grid(tr, sf)
            cap, _ = g_capture(dang_tr, sf, tau, m, ruler="s2full")
            if best1 is None or cap > best1[4]:
                best1 = (name, sgn, tau, m, cap)
    n1, s1_, t1, m1, _ = best1

    def g_f1(X, j=FEATS.index(n1), sgn=s1_):
        return sgn * X[:, j]

    tau_l, m_l = fit_grid(tr, g_lin)
    print(f"[m2-fit] g_lin int8 weights: "
          f"{dict(zip(FEATS, [int(x) for x in wq]))} tau={tau_l:.1f} "
          f"m={m_l:.1f}", flush=True)
    print(f"[m2-fit] g_feat1 comparator: {('-' if s1_ < 0 else '')}{n1} "
          f"tau={t1:.1f} m={m1:.1f}", flush=True)

    floor, go_bar, lb_bar = 0.069, 0.129, 0.099
    for label, fn, tau, m in (("g_lin", g_lin, tau_l, m_l),
                              ("g_feat1", g_f1, t1, m1)):
        cap, dose = g_capture(ho_d, fn, tau, m, ruler="ev")
        lo, hi = seed_ci(ho_d, fn, tau, m, ruler="ev")
        cap_all, dose_all = g_capture(ho, fn, tau, m, ruler="ev")
        cap_f, _ = g_capture(ho_d, fn, tau, m, ruler="s2full")
        verdict = ("GO" if cap >= go_bar and lo > lb_bar else
                   "KILL" if hi < lb_bar else "BETWEEN")
        print(f"[m2-fit] HELD-OUT {label}: danger-capture={cap:.4f} "
              f"CI[{lo:.4f},{hi:.4f}] dose={dose:.3f} | all={cap_all:.4f} "
              f"dose={dose_all:.3f} | full-s2 danger={cap_f:.4f} | "
              f"bars GO>={go_bar} LB>{lb_bar} floor={floor} -> {verdict}",
              flush=True)


if __name__ == "__main__":
    stage = sys.argv[1] if len(sys.argv) > 1 else "instruments"
    {"instruments": stage_instruments, "fit": stage_fit}[stage]()
