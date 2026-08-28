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


def assemble(stratum, src=None):
    """src defaults to the base bank dir; pass '<S>_backfill' for A5 segments.
    Rows carry `origin` and `to_end` (= n_plies - ply), the A5 amendment's
    stratification variable."""
    src = src or stratum
    feats = {}
    for f in glob.glob(os.path.join(FOUT, src, "seed_*.json.gz")):
        r = json.load(_gzip.open(f, "rt"))
        if r["replay_gate"] == "PASS":
            feats[r["seed"]] = r["feats"]
    rows = []
    for f in sorted(glob.glob(os.path.join(OUT, src, "seed_*.json.gz"))):
        r = json.load(_gzip.open(f, "rt"))
        if r["smoke"] or r["seed"] not in feats:
            continue
        n_plies = r["game"]["n_plies"]
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
                "danger": a["champ_s2"] <= 3, "classes": list(a["classes"]),
                "origin": src, "to_end": n_plies - a["ply"]})
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
    # Composition of the two populations, printed BESIDE the verdict rather
    # than asserted in a report (#24's mechanism: the gap travels with the
    # number). PHASE 1's census covers TRIGGER plies only; the base bank also
    # carries band/healthy/random quota states. Measured 2026-08-28: 100% of
    # held-danger is trigger-class, because `band` is dsh in [10,12] (below
    # the trigger) and `healthy` is defined non-danger — so the danger
    # population IS the trigger population and the two arms are the same
    # class. If that ever stops being true, this line says so.
    cls = {}
    for r in base:
        if r["danger"] and held(r["seed"]):
            k = ("trigger" if "trigger" in r["classes"]
                 else "+".join(sorted(r["classes"])) or "unclassed")
            cls[k] = cls.get(k, 0) + 1
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
    # Freeze the fitted artifacts so the PRE-A5 guard can be re-evaluated
    # unchanged on the enlarged held-out set (A5 amendment sec 5.1 arm F).
    # Written only if absent: the frozen reference must be the pre-A5 one,
    # and a later re-run must not silently overwrite it (R29 — a swap is
    # visible only against history).
    frz = os.path.join(HERE, "out", "m2_fit_frozen.json")
    if not os.path.exists(frz):
        json.dump({"note": "PRE-A5 L20 fit; frozen reference for arm F",
                   "feats": list(FEATS), "mu": mu.tolist(), "sd": sd.tolist(),
                   "wq": [int(x) for x in wq], "tau": float(tau_l),
                   "m": float(m_l), "n_train": len(tr), "n_held": len(ho),
                   "n_held_danger": len(ho_d),
                   "feat1": {"name": n1, "sgn": int(s1_), "tau": float(t1),
                             "m": float(m1)}},
                  open(frz, "w"), indent=1)
        print(f"[m2-fit] froze pre-A5 artifacts -> {frz}", flush=True)
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




# ============================================================ A5 re-fit (fit2)
# REGISTRATION_A5_BACKFILL.md sec 5. Bars UNCHANGED: danger GO >= 0.129 with
# clustered CI LB > 0.099; KILL if UB < 0.099. Statistic, ruler (eval-half
# s2[3:6]), decision shape and seed-clustered bootstrap are stage_fit's.
#
# Five arms, all emitted together, verdict gated by P and S1 jointly so the
# oversampling cannot manufacture either outcome:
#   P  post-stratified pooled (PRIMARY, gates)   S1 pooled unweighted (co-gates)
#   S2 base-only (continuity, does NOT gate)     D  backfill-only (diagnostic)
#   F  frozen PRE-A5 g_lin on the enlarged held set (isolates added evaluation
#      precision from added training data — sec 4's confound)
BUCKETS = ((0, 10), (10, 20), (20, 30), (30, 10 ** 9))


def bucket(to_end):
    for i, (lo, hi) in enumerate(BUCKETS):
        if lo <= to_end < hi:
            return i
    raise ValueError(to_end)


def dedup(base_rows, bf_rows):
    """Base and backfill re-adjudicate the SAME (seed, ply) states: backfill
    covers every trigger ply in the final 30, and the base bank's surviving
    (unthinned) trigger states in that window are a subset. Fork seeds are
    dist_seed(seed, ply, s) — identical inputs, so the duplicates are EXACT.
    Pooling without dedup would double-weight exactly the death-window states
    A5 is adding, which is the opposite of the density correction.

    Returns (rows, report). Duplicates are ALSO the strongest available
    format/label-identity check (sec 3): the two producers' s2 vectors must
    agree bit-for-bit, which the height-trace replay gate cannot see."""
    seen = {(r["seed"], r["ply"]): r for r in base_rows}
    kept, dup, mismatch = [], 0, []
    for r in bf_rows:
        k = (r["seed"], r["ply"])
        b = seen.get(k)
        if b is None:
            kept.append(r)
            continue
        dup += 1
        if not (np.array_equal(b["s2full"], r["s2full"])
                and np.array_equal(b["ev"], r["ev"])
                and b["ci"] == r["ci"] and b["danger"] == r["danger"]):
            mismatch.append(k)
    return base_rows + kept, {"dup": dup, "mismatch": mismatch,
                              "bf_new": len(kept), "bf_total": len(bf_rows)}


def _gain(r, score_fn, tau, m, ruler="ev"):
    g = score_fn(r["X"])
    order = sorted(range(len(g)), key=lambda i: (-g[i], -r["val"][i]))
    best = order[0]
    pick = r["ci"]
    fired = 0
    if g[r["ci"]] <= tau and g[best] - g[r["ci"]] >= m and best != r["ci"]:
        pick, fired = best, 1
    return r[ruler][pick] - r[ruler][r["ci"]], fired


def poststrat(rows, score_fn, tau, m, dens, ruler="ev"):
    """sum_b P_base(b) * mean_rows_in_b(gain), renormalised over occupied
    buckets. `dens` is the BASE bank's danger-state position density — a
    design property (position, not outcome), so estimating it on the full
    base bank rather than its held-out slice leaks nothing."""
    acc = {}
    for r in rows:
        g, _ = _gain(r, score_fn, tau, m, ruler)
        acc.setdefault(bucket(r["to_end"]), []).append(g)
    num = den = 0.0
    for b, gs in acc.items():
        num += dens[b] * float(np.mean(gs))
        den += dens[b]
    return num / den if den else float("nan")


def plain(rows, score_fn, tau, m, ruler="ev"):
    gs = [_gain(r, score_fn, tau, m, ruler) for r in rows]
    if not gs:
        return float("nan"), 0.0
    return (float(np.mean([g for g, _ in gs])),
            float(np.mean([f for _, f in gs])))


def boot_ci(rows, est, b=2000, seed=23):
    """Seed-clustered bootstrap of `est` (a callable over a row list)."""
    by = {}
    for r in rows:
        by.setdefault(r["seed"], []).append(r)
    keys = list(by)
    if len(keys) < 2:
        return float("nan"), float("nan")
    rng = random.Random(seed)
    out = []
    for _ in range(b):
        draw = []
        for _ in keys:
            draw.extend(by[keys[rng.randrange(len(keys))]])
        v = est(draw)
        if v == v:
            out.append(v)
    if not out:
        return float("nan"), float("nan")
    return float(np.percentile(out, 2.5)), float(np.percentile(out, 97.5))


GO_BAR, LB_BAR, FLOOR = 0.129, 0.099, 0.069


def _verdict(cap, lo, hi):
    if cap >= GO_BAR and lo > LB_BAR:
        return "GO"
    if hi < LB_BAR:
        return "KILL"
    return "BETWEEN"


def stage_fit2(srcs=None):
    """srcs: A5 segment dirs to pool in (default the PHASE 1 census).
    Named explicitly rather than globbed: which segments enter the fit is a
    registration fact, not a directory-listing accident."""
    stratum = "L20"
    srcs = srcs or ["L20_unthin_held"]
    base = assemble(stratum)
    bf = []
    for sd in srcs:
        got = assemble(stratum, sd)
        print(f"[fit2] segment {sd}: {len(got)} rows", flush=True)
        bf += got
    rows, rep = dedup(base, bf)
    print(f"[fit2] base={len(base)} backfill={rep['bf_total']} "
          f"dup=(seed,ply) {rep['dup']} new={rep['bf_new']} "
          f"pooled={len(rows)}", flush=True)
    if rep["mismatch"]:
        print(f"[fit2] ⚠⚠ LABEL-IDENTITY GATE FAIL on {len(rep['mismatch'])} "
              f"duplicate states, e.g. {rep['mismatch'][:5]} — the two "
              f"producers disagree; STOP", flush=True)
        return 3
    if rep["dup"]:
        print(f"[fit2] LABEL-IDENTITY GATE PASS: {rep['dup']} duplicate "
              f"(seed,ply) states agree bit-for-bit across producers",
              flush=True)

    # base danger position density (design property; full base bank)
    dens = {i: 0.0 for i in range(len(BUCKETS))}
    for r in base:
        if r["danger"]:
            dens[bucket(r["to_end"])] += 1
    tot = sum(dens.values())
    dens = {k: v / tot for k, v in dens.items()}
    print(f"[fit2] base danger position density (plies-to-end "
          f"{[b[0] for b in BUCKETS]}): "
          f"{ {k: round(v, 3) for k, v in dens.items()} }", flush=True)

    # Composition of the two populations, printed BESIDE the verdict rather
    # than asserted in a report (#24's mechanism: the gap travels with the
    # number). PHASE 1's census covers TRIGGER plies only; the base bank also
    # carries band/healthy/random quota states. Measured 2026-08-28: 100% of
    # held-danger is trigger-class, because `band` is dsh in [10,12] (below
    # the trigger) and `healthy` is defined non-danger — so the danger
    # population IS the trigger population and the two arms are the same
    # class. If that ever stops being true, this line says so.
    cls = {}
    for r in base:
        if r["danger"] and held(r["seed"]):
            k = ("trigger" if "trigger" in r["classes"]
                 else "+".join(sorted(r["classes"])) or "unclassed")
            cls[k] = cls.get(k, 0) + 1
    tr = [r for r in rows if not held(r["seed"])]
    ho = [r for r in rows if held(r["seed"])]
    ho_d = [r for r in ho if r["danger"]]
    base_hod = [r for r in base if held(r["seed"]) and r["danger"]]
    bf_hod = [r for r in ho_d if r["origin"].endswith("_backfill")]
    print(f"[fit2] train={len(tr)} (danger {sum(r['danger'] for r in tr)}) "
          f"held={len(ho)} HELD-DANGER={len(ho_d)} "
          f"(base {len(base_hod)} + census-new {len(bf_hod)})", flush=True)
    print(f"[fit2] SCOPE: the census enumerates TRIGGER plies; base also holds "
          f"band/healthy/random quota states. Base held-danger by class: "
          f"{cls} — if non-trigger is nonzero the two arms are NOT the same "
          f"population and base-only stops being a subsample.", flush=True)

    # ---- re-fit g_lin on the pooled TRAIN rows (same recipe as stage_fit)
    y = np.concatenate([r["s2full"] for r in tr])
    Xall = np.vstack([r["X"] for r in tr])
    mu, sd = Xall.mean(0), Xall.std(0) + 1e-9
    Xz = (Xall - mu) / sd
    w = np.linalg.solve(Xz.T @ Xz + 10.0 * np.eye(len(FEATS)), Xz.T @ y)
    wq = np.round(w / np.abs(w).max() * 63).astype(int)

    def g_lin(X):
        return ((X - mu) / sd) @ wq
    tau_l, m_l = fit_grid(tr, g_lin)
    print(f"[fit2] g_lin(A5) int8: "
          f"{dict(zip(FEATS, [int(x) for x in wq]))} tau={tau_l:.1f} "
          f"m={m_l:.1f}", flush=True)

    # ---- arm F: the FROZEN pre-A5 guard, unchanged
    frz = json.load(open(os.path.join(HERE, "out", "m2_fit_frozen.json")))
    fmu = np.array(frz["mu"]); fsd = np.array(frz["sd"])
    fwq = np.array(frz["wq"])
    assert frz["feats"] == list(FEATS), "frozen fit used a different menu"

    def g_frozen(X):
        return ((X - fmu) / fsd) @ fwq
    print(f"[fit2] arm F uses FROZEN pre-A5 weights (n_held_danger at "
          f"freeze={frz['n_held_danger']}) tau={frz['tau']:.1f} "
          f"m={frz['m']:.1f}", flush=True)

    verdicts = {}
    for gname, fn, tau, m in (("g_lin(A5)", g_lin, tau_l, m_l),
                              ("g_lin(FROZEN)", g_frozen, frz["tau"],
                               frz["m"])):
        for arm, rws, weighted in (
                ("P  poststrat-pooled", ho_d, True),
                ("S1 pooled-unweighted", ho_d, False),
                ("S2 base-only", base_hod, False),
                ("D  backfill-only", bf_hod, False)):
            if not rws:
                print(f"[fit2] {gname:14s} {arm:22s} VOID (n=0)", flush=True)
                continue
            if weighted:
                est = lambda rr, fn=fn, tau=tau, m=m: poststrat(
                    rr, fn, tau, m, dens)
                cap = est(rws)
                dose = plain(rws, fn, tau, m)[1]
            else:
                est = lambda rr, fn=fn, tau=tau, m=m: plain(
                    rr, fn, tau, m)[0]
                cap, dose = plain(rws, fn, tau, m)
            lo, hi = boot_ci(rws, est)
            v = _verdict(cap, lo, hi)
            verdicts[(gname, arm[:2].strip())] = v
            print(f"[fit2] {gname:14s} {arm:22s} n={len(rws):4d} "
                  f"capture={cap:+.4f} CI[{lo:+.4f},{hi:+.4f}] "
                  f"dose={dose:.3f} -> {v}", flush=True)

    p = verdicts.get(("g_lin(A5)", "P")); s1 = verdicts.get(("g_lin(A5)", "S1"))
    final = p if p == s1 else "BETWEEN"
    print(f"[fit2] === REGISTERED VERDICT (sec 5.2: P and S1 must agree) === "
          f"P={p} S1={s1} -> {final}", flush=True)
    if p != s1:
        print(f"[fit2] P and S1 DISAGREE — the density weighting is "
              f"load-bearing; that disagreement IS the finding, no verdict "
              f"is claimed (sec 5.2)", flush=True)
    if final == "BETWEEN":
        print(f"[fit2] sec 5.2 pre-registered consequence: a BETWEEN at the "
              f"enlarged n is a STOP on M2's fit question, NOT a third "
              f"back-fill — n was not the binding constraint.", flush=True)
    return 0


# ================================================= A5 instrument re-measure
# `stage_instruments` above produced the SIGNED bars and is left byte-untouched
# (R29: freeze the reference; a swap is only visible against history). This is
# a separate stage for the A5-enlarged bank — its job is the L11M question the
# M2 instruments memo left open: is "the teacher's verdict is not distillable
# at L11M" a program finding, or an n=55 artifact?
def merge_records(base_recs, bf_recs):
    """Union adjudications per seed, deduped by ply. Base and back-fill
    re-adjudicate shared (seed, ply) states with identical fork seeds, so the
    duplicates must agree exactly — checked, not assumed."""
    by = {r["seed"]: dict(r, adjudications=list(r["adjudications"]))
          for r in base_recs}
    dup = 0
    mism = []
    for r in bf_recs:
        tgt = by.get(r["seed"])
        if tgt is None:
            by[r["seed"]] = dict(r, adjudications=list(r["adjudications"]))
            continue
        have = {a["ply"]: a for a in tgt["adjudications"]}
        for a in r["adjudications"]:
            b = have.get(a["ply"])
            if b is None:
                tgt["adjudications"].append(a)
            else:
                dup += 1
                strip = lambda d: {k: v for k, v in d.items()
                                   if k != "classes"}
                if strip(a) != strip(b):
                    mism.append((r["seed"], a["ply"]))
    return list(by.values()), dup, mism


def _instr_report(tag, recs):
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
    if not allv:
        print(f"[instr2] {tag}: VOID (no states)", flush=True)
        return
    ceil_all, dose_all = capture(allv)
    ceil_d, dose_d = capture(dangv) if dangv else (float("nan"), 0.0)
    fl = [capture(allv, permute_rng=random.Random(3000 + i))[0]
          for i in range(20)]
    fld = ([capture(dangv, permute_rng=random.Random(3000 + i))[0]
            for i in range(20)] if dangv else [float("nan")])
    hr_a = ceil_all - np.mean(fl)
    hr_d = ceil_d - np.mean(fld)
    print(f"[instr2] {tag}: states={len(allv)} danger={len(dangv)}", flush=True)
    print(f"[instr2] {tag}: ALL     ceiling={ceil_all:+.4f} "
          f"floor={np.mean(fl):+.4f}+/-{np.std(fl):.4f} "
          f"HEADROOM={hr_a:+.4f} dose={dose_all:.3f}", flush=True)
    print(f"[instr2] {tag}: DANGER  ceiling={ceil_d:+.4f} "
          f"floor={np.mean(fld):+.4f}+/-{np.std(fld):.4f} "
          f"HEADROOM={hr_d:+.4f} dose={dose_d:.3f}", flush=True)
    # R19: state the n beside the direction, and refuse a direction when the
    # headroom is inside the floor's own spread
    verdict = ("USABLE" if hr_d > 2 * np.std(fld) else
               "NO MEASURED HEADROOM" if hr_d <= 0 else
               "INSIDE THE FLOOR'S OWN SPREAD — no direction claimed")
    print(f"[instr2] {tag}: DANGER verdict -> {verdict} "
          f"(n={len(dangv)})", flush=True)


def stage_instruments2(argv):
    stratum = argv[0] if argv else "L11M"
    srcs = argv[1:] or [f"{stratum}_backfill"]
    base = load(stratum)
    bf = []
    for sd in srcs:
        got = load(sd)
        print(f"[instr2] segment {sd}: {len(got)} games", flush=True)
        bf += got
    merged, dup, mism = merge_records(base, bf)
    print(f"[instr2] {stratum} base_games={len(base)} +bf_games={len(bf)} "
          f"-> merged={len(merged)} shared_states={dup} diverged={len(mism)}",
          flush=True)
    if mism:
        print(f"[instr2] ⚠⚠ LABEL DIVERGENCE {mism[:5]} — STOP", flush=True)
        return 3
    _instr_report(f"{stratum} BASE-ONLY (reference, unchanged)", base)
    _instr_report(f"{stratum} POOLED (base + A5)", merged)
    print(f"[instr2] ⚠ the pooled population OVERSAMPLES the death window by "
          f"design; the two readings are reported side by side and the "
          f"BASE-ONLY row is the one comparable to the signed M2 instruments.",
          flush=True)
    return 0


# NOTE: keep this dispatch LAST. Appending a new stage after it makes the
# block reference a name defined below it -> NameError at import (hit twice).
if __name__ == "__main__":
    stage = sys.argv[1] if len(sys.argv) > 1 else "instruments"
    if stage == "fit2":
        stage_fit2(sys.argv[2:] or None)
    elif stage == "instruments2":
        sys.exit(stage_instruments2(sys.argv[2:]))
    else:
        {"instruments": stage_instruments, "fit": stage_fit}[stage]()
