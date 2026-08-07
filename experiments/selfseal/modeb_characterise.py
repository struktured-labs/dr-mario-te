#!/usr/bin/env python3
"""MODE-B CHARACTERISATION: what is true of the board at a Mode-B point of no
return that is not true otherwise?

CONTEXT. adversary_t3's PONR backward search split the champion's pressure
deaths in two, with a real hole in the middle (nothing between gap 16 and 26):
  MODE A  gap 5-15 plies   -- late, local, plausibly reachable by search
  MODE B  gap >=27 plies   -- the fatal decision is ~30 placements before death
This asks what distinguishes Mode B, using only board features a decider could
compute at decision time. CHARACTERISATION ONLY -- no eval term is proposed.

THE CONTROL, and why this one. The lead asked for "same ply index, from games
that did NOT die". gen_pressure_deaths.py wrote ONLY topout rows
(`if row["result"]=="topout"`), so no survivor trajectory exists in the corpus
and none can be reconstructed from it. Rather than generate new games, the
control here is the strictly-available one that preserves the matched-index
discipline the lead actually wanted:

  For a Mode-B case whose PONR is ply P, the controls are the MODE-A games'
  boards AT THE SAME PLY INDEX P, taken only from games whose own PONR is
  LATER than P.

Those control boards are, at ply P, *demonstrably not yet doomed* -- the PONR
search proved a real choice still mattered there -- while the Mode-B board at
the same ply index is already lost. Same decider, same pressure model, same ply
depth, opposite doom status. What it CANNOT rule out is a feature that marks
"this game dies eventually", since every game in the corpus dies; it isolates
"doomed NOW vs doomed LATER", which is the Mode-A/Mode-B question. Stated
plainly so nobody reads more into it. See LIMITS at the bottom of the output.

POWER. Mode B is n=6 (+2 right-censored). Only very large effects are
detectable; a non-significant feature here is NOT evidence of no effect. Cliff's
delta (nonparametric, tiny-n robust) is reported with every p, and every
Mode-B case's raw value is printed so a single-game artefact is visible.
"""
from __future__ import annotations

import sys
import os
import json
import argparse
import random
import statistics as st
from itertools import combinations

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = "/home/struktured/projects/dr_mario_rl"
QA = "/home/struktured/projects/dr-mario-qa-wt/experiments"
T3 = QA + "/adversary_t3"
for _p in (HERE, T3, ROOT + "/tmp/combo_term", ROOT + "/tmp/endgame", ROOT + "/tmp/tuck",
           ROOT + "/tmp/pillrng", ROOT + "/.claude/worktrees/faithful-sim/src", QA,
           QA + "/tuck_v3", QA + "/eval47"):
    if _p not in sys.path:
        sys.path.insert(0, _p)

MODE_A_MAX = 15
MODE_B_MIN = 27


def board_flat(board):
    from fb import FB
    import root_search as RS
    return RS.board_flat_from_fb(FB.from_board(board))


def mannwhitney_u_p(a, b):
    """Exact two-sided Mann-Whitney U via permutation over label assignments.
    Exact while C(n,k) is small (it is: n<=6 vs <=40 -> we permute the pooled
    ranks by sampling when the exact count is large)."""
    na, nb = len(a), len(b)
    if na == 0 or nb == 0:
        return float("nan"), float("nan")

    def U(x, y):
        u = 0.0
        for xi in x:
            for yj in y:
                u += 1.0 if xi > yj else (0.5 if xi == yj else 0.0)
        return u

    u_obs = U(a, b)
    pooled = list(a) + list(b)
    n = len(pooled)
    total = 1
    for i in range(na):
        total = total * (n - i) // (i + 1)
    centre = na * nb / 2.0
    dev = abs(u_obs - centre)
    if total <= 200000:
        cnt = hit = 0
        for idx in combinations(range(n), na):
            s = set(idx)
            x = [pooled[i] for i in idx]
            y = [pooled[i] for i in range(n) if i not in s]
            cnt += 1
            if abs(U(x, y) - centre) >= dev - 1e-9:
                hit += 1
        return u_obs, hit / cnt
    rng = random.Random(20260807)
    cnt = hit = 0
    for _ in range(20000):
        p = pooled[:]
        rng.shuffle(p)
        cnt += 1
        if abs(U(p[:na], p[na:]) - centre) >= dev - 1e-9:
            hit += 1
    return u_obs, hit / cnt


def cliffs_delta(a, b):
    """(#a>b - #a<b) / (na*nb). +1 = a strictly above b, -1 = strictly below."""
    if not a or not b:
        return float("nan")
    gt = sum(1 for x in a for y in b if x > y)
    lt = sum(1 for x in a for y in b if x < y)
    return (gt - lt) / (len(a) * len(b))


def magnitude(d):
    ad = abs(d)
    return "negligible" if ad < 0.147 else "small" if ad < 0.33 else \
           "medium" if ad < 0.474 else "LARGE"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--ponr", default=T3 + "/pressure_deaths/ponr_results.jsonl")
    ap.add_argument("--deaths", default=T3 + "/pressure_deaths/deaths.jsonl")
    ap.add_argument("--out", default=HERE + "/results/modeb_features.json")
    a = ap.parse_args()

    import modeb_features as MF
    from seal_terms import warmup
    warmup()
    import point_of_no_return as PNR
    from point_of_no_return import replay_trajectory

    # PERF TRAP in point_of_no_return.replay_trajectory: it does
    #   _CACHE.setdefault("model", build_v1_1())
    # and dict.setdefault evaluates its default EAGERLY *even when the key is
    # already present*, so the ~80s bursty-v1.1 footage refit runs on EVERY
    # call. Pre-seeding _CACHE does NOT help (the assignment is skipped, the
    # computation is not). replay_trajectory does `from gen_pressure_deaths
    # import build_v1_1` INSIDE the function, so the name is resolved off that
    # module at call time -- patching the module attribute is what actually
    # works. Same model object either way, so replays are bit-identical.
    import gen_pressure_deaths as GPD
    _model = GPD.build_v1_1()
    s = _model.fit_summary()
    print(f"bursty v1.1 model built ONCE: n_volleys={s['n_volleys']} "
          f"n_clears={s['n_clears']} (refit-per-call trap patched)", flush=True)
    GPD.build_v1_1 = lambda *a, **k: _model
    PNR._CACHE["model"] = _model

    ponr = [json.loads(l) for l in open(a.ponr)]
    deaths = {r["seed"]: r for r in (json.loads(l) for l in open(a.deaths))}

    cases = []
    for r in ponr:
        if r["seed"] not in deaths:
            continue
        gap = r.get("gap_plies")
        if gap is None:
            mode = "CENSORED"
        elif gap <= MODE_A_MAX:
            mode = "A"
        elif gap >= MODE_B_MIN:
            mode = "B"
        else:
            mode = "MID"
        cases.append({**r, "mode": mode, "actions": deaths[r["seed"]]["actions"]})

    print("=" * 78)
    print("MODE-B CHARACTERISATION -- champion pressure deaths, bursty v1.1, L11")
    print("=" * 78)
    n_by = {}
    for c in cases:
        n_by[c["mode"]] = n_by.get(c["mode"], 0) + 1
    print(f"\ncases: {n_by}  (total {len(cases)})")
    gaps = sorted(c["gap_plies"] for c in cases if c["gap_plies"] is not None)
    print(f"gap_plies (n={len(gaps)}): {gaps}")
    # DO NOT assert the hole -- MEASURE it. The two-disease framing rests on
    # the 16..26 band being empty, and this corpus is still being appended to
    # by the adversary_t3 lane, so the claim has to be re-checked every run.
    mid = [g for g in gaps if MODE_A_MAX < g < MODE_B_MIN]
    if mid:
        print(f"  *** THE 16-26 HOLE IS NOT EMPTY IN THIS CORPUS: {mid}")
        print(f"  *** The 'two distinct diseases' split was established when the")
        print(f"  *** band was empty at n=17. At n={len(gaps)} it contains "
              f"{len(mid)} case(s).")
        print(f"  *** Treat MODE A / MODE B as TAILS OF ONE DISTRIBUTION unless")
        print(f"  *** re-established; the features below still describe the tails.")
    else:
        print(f"  -> band {MODE_A_MAX+1}..{MODE_B_MIN-1} is empty at n={len(gaps)} "
              f"(hole reproduces)")
    cen = [c for c in cases if c["mode"] == "CENSORED"]
    if cen:
        print(f"\n*** {len(cen)} RIGHT-CENSORED cases the mode split omits: seeds "
              f"{[c['seed'] for c in cen]}")
        for c in cen:
            w0 = c["searched_window"][0]
            print(f"      seed {c['seed']}: doomed at EVERY ply searched back to {w0} "
                  f"(death {c['death_ply']}) => gap >= {c['death_ply']-w0}, "
                  f"i.e. MORE extreme than Mode B, not missing data")

    # ---- replay every game once, feature every ply -----------------------
    print("\nreplaying trajectories...", flush=True)
    per_game = {}
    for c in cases:
        snaps = replay_trajectory(c["seed"], c["actions"])
        feats = {}
        for s in snaps:
            col, vir = board_flat(s["board_before"])
            feats[s["pills_placed"]] = MF.extract(col, vir)
        per_game[c["seed"]] = feats
        print(f"  seed {c['seed']:6d} mode {c['mode']:8s} plies {len(snaps):4d} "
              f"ponr {c['ponr_ply']}", flush=True)

    modeB = [c for c in cases if c["mode"] == "B"]
    modeA = [c for c in cases if c["mode"] == "A"]

    # ---- matched-index control -------------------------------------------
    print("\n" + "=" * 78)
    print("MATCHED-INDEX CONTROL: Mode-B board at its PONR ply P, vs Mode-A")
    print("boards at the SAME ply P from games whose own PONR is LATER than P")
    print("(so the control board is provably NOT yet doomed at ply P)")
    print("=" * 78)

    treat, ctrl = {f: [] for f in MF.FEATURES}, {f: [] for f in MF.FEATURES}
    treat_rows, ctrl_rows = [], []      # per-board records, for conditional analysis
    pairing = []
    for c in modeB:
        P = c["ponr_ply"]
        fb_ = per_game[c["seed"]].get(P)
        if fb_ is None:
            pairing.append((c["seed"], P, 0, "no board at PONR ply"))
            continue
        ctrls = []
        for d in modeA:
            if d["ponr_ply"] is not None and P < d["ponr_ply"] and P in per_game[d["seed"]]:
                ctrls.append(per_game[d["seed"]][P])
        pairing.append((c["seed"], P, len(ctrls), ""))
        if not ctrls:
            continue
        treat_rows.append({**fb_, "seed": c["seed"], "ply": P})
        ctrl_rows.extend({**x, "ply": P} for x in ctrls)
        for f in MF.FEATURES:
            treat[f].append(fb_[f])
            ctrl[f].extend(x[f] for x in ctrls)

    print(f"\n  {'seed':>7} {'ponr_ply':>9} {'#controls':>10}  note")
    for s, P, n, note in pairing:
        print(f"  {s:>7} {P if P is not None else '--':>9} {n:>10}  {note}")
    nT = len(treat[MF.FEATURES[0]])
    nC = len(ctrl[MF.FEATURES[0]])
    print(f"\n  usable Mode-B cases: {nT}   pooled control boards: {nC}")
    if nT < 2:
        print("  *** too few usable Mode-B cases to compare -- stopping here")
        return

    rows = []
    for f in MF.FEATURES:
        t, k = treat[f], ctrl[f]
        _, p = mannwhitney_u_p(t, k)
        d = cliffs_delta(t, k)
        rows.append((f, st.median(t), st.median(k), d, p))
    rows.sort(key=lambda r: -abs(r[3]))

    print(f"\n  {'feature':<24}{'ModeB med':>10}{'ctrl med':>10}"
          f"{'Cliff d':>9}{'|d|':>12}{'p':>9}")
    print("  " + "-" * 74)
    for f, mt, mc, d, p in rows:
        star = " *" if p < 0.05 else ""
        print(f"  {f:<24}{mt:>10.2f}{mc:>10.2f}{d:>9.2f}{magnitude(d):>12}"
              f"{p:>9.3f}{star}")

    print(f"\n  per-case Mode-B values (watch for a single game driving a result):")
    top = [r[0] for r in rows[:6]]
    print(f"  {'seed':>7} " + "".join(f"{f[:11]:>12}" for f in top))
    for c in modeB:
        P = c["ponr_ply"]
        fb_ = per_game[c["seed"]].get(P)
        if fb_ is None:
            continue
        print(f"  {c['seed']:>7} " + "".join(f"{fb_[f]:>12.1f}" for f in top))
    print(f"  {'CTRL med':>7} " + "".join(f"{st.median(ctrl[f]):>12.1f}" for f in top))

    # ---- CIRCULARITY CHECK ------------------------------------------------
    # point_of_no_return.py defines doom (tier 1) as "EVERY candidate has
    # spawn-lane height >= H_DANGER". So a Mode-B board AT its PONR is
    # near-guaranteed a high spawn_h BY CONSTRUCTION, and "spawn_h separates
    # Mode B" partly re-discovers the label definition rather than finding a
    # feature. The honest test: keep only control boards ALREADY in the danger
    # zone (spawn_h >= H_DANGER-1), so both sides are height-matched, and ask
    # what -- if anything -- still separates.
    H_DANGER = getattr(PNR, "H_DANGER", 13)
    print("\n" + "=" * 78)
    print(f"CIRCULARITY CHECK: PONR doom is DEFINED by spawn-lane height >= "
          f"{H_DANGER}\n(point_of_no_return.H_DANGER), so re-run against only "
          f"controls that are\nALREADY at spawn_h >= {H_DANGER-1} -- height-matched "
          f"on the defining axis")
    print("=" * 78)
    cmatch = [x for x in ctrl_rows if x["spawn_h"] >= H_DANGER - 1]
    print(f"\n  height-matched control boards: {len(cmatch)} of {len(ctrl_rows)}")
    cond_rows = []
    if len(cmatch) >= 8:
        for f in MF.FEATURES:
            t = [x[f] for x in treat_rows]
            k = [x[f] for x in cmatch]
            _, p = mannwhitney_u_p(t, k)
            d = cliffs_delta(t, k)
            cond_rows.append((f, st.median(t), st.median(k), d, p))
        cond_rows.sort(key=lambda r: -abs(r[3]))
        print(f"\n  {'feature':<24}{'ModeB med':>10}{'ctrl med':>10}"
              f"{'Cliff d':>9}{'|d|':>12}{'p':>9}")
        print("  " + "-" * 74)
        for f, mt, mc, d, p in cond_rows:
            star = " *" if p < 0.05 else ""
            print(f"  {f:<24}{mt:>10.2f}{mc:>10.2f}{d:>9.2f}{magnitude(d):>12}"
                  f"{p:>9.3f}{star}")
        surv = [r for r in cond_rows if r[4] < 0.05]
        print(f"\n  -> {len(surv)} feature(s) survive height-matching: "
              f"{[r[0] for r in surv] or 'NONE'}")
    else:
        print("  too few height-matched controls to test -- reporting as untestable")

    with open(a.out, "w") as fh:
        json.dump({"cases": [{k: v for k, v in c.items() if k != "actions"} for c in cases],
                   "treat": treat, "ctrl": ctrl,
                   "treat_rows": treat_rows, "ctrl_rows": ctrl_rows,
                   "h_danger": H_DANGER,
                   "table": [{"feature": f, "modeb_median": mt, "ctrl_median": mc,
                              "cliffs_delta": d, "p": p} for f, mt, mc, d, p in rows],
                   "table_height_matched": [
                       {"feature": f, "modeb_median": mt, "ctrl_median": mc,
                        "cliffs_delta": d, "p": p} for f, mt, mc, d, p in cond_rows],
                   }, fh)
    print(f"\nwrote {a.out}")

    print("\n" + "=" * 78)
    print("LIMITS -- read before citing any line above")
    print("=" * 78)
    print(f"  * Mode B is n={nT}. Only very large effects are detectable; a")
    print("    non-significant feature is NOT evidence of no effect.")
    print("  * Controls are OTHER DEATH GAMES at a not-yet-doomed ply, because the")
    print("    corpus contains no survivor trajectories (gen_pressure_deaths.py")
    print("    wrote topouts only). This isolates 'doomed NOW vs doomed LATER',")
    print("    not 'dies vs survives'.")
    print("  * Control boards are pooled across Mode-A games, so they are not")
    print("    independent of each other within a game; p-values are optimistic.")
    print("  * All features are pure board functions -- no lookahead -- so any")
    print("    separator here is in principle computable by a decider.")


if __name__ == "__main__":
    main()
