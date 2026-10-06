"""STEER11 step 1: calibrate the vs_race clock against the couch AI's per-pill timings (silicon, FAIR family).

  python steer11_clockcal.py extract   per-pill table -> steer11/clockcal_pills.jsonl (banked cases, R101)
  python steer11_clockcal.py fit       models + game-level cross-validation -> steer11/clockcal.txt,
                                       chosen parameters -> steer11/clock_couch11.json

SOURCES (AI seat = P2, L11 MED, real-time HDMI captures, hidden-spawn tracker + clear-pop repair):
  10/04  owner vs FAIR (dbbb5007) / FAIR2 (b1b57638; same main search, tucks/root order differ): 10 games
         couch_forensics/fair_20261004.py windows (summary_fair_20261004.json), scan ~/dr_mario_rl/tmp/fair_20261004/scan
  10/05  dr. lulu vs ANTIBODY_DIST_FAIR (dbbb5007 + rbf 318607aa): 9 games, couch_forensics/lulu_20261005.py
The per-pill rows are rebuilt with the forensics' own loaders (FA.load_raw + FA.ai_attacks, RS.volleys rule) and
checked against the banked cases_*_ai_pills.jsonl (t_spawn, chain, runs) before use.

PER PILL i (interval dt = t_spawn[i+1] - t_spawn[i], seconds; the last pill of a game has no interval):
  fall      max(0, 15 - hmax): hmax = tallest TARGET column of the observed landing on S_i -- the vs_race feature
  nsteps    cascade steps of the pill's own clear (faithful resolve of S_i + landing)
  cfall     sum over those steps of the gravity fall rows (passes of FaithfulBoard._apply_gravity that moved)
  vol       1 if garbage landed between S_i's placement and S_{i+1} (RS.volleys rule: new cells vs after_pill)
  gsize     garbage cells (RS.volleys size; 'explained' volleys via mech_check.explain)
  gfall     max over the garbage columns of the rows a row-0 tile falls onto after_pill's stack (ROM drop)
  gclear    1 if the garbage set off a clear (cells of after_pill missing in S_{i+1})
VALIDATION (fit):
  * leave-one-GAME-out: predicted vs observed time from the first to the last spawn, per game
  * HOLD-OUT: fit on the 15 games that are NOT the 10/05 AI clear games; predict the 4 AI clear games (M1 G5, M2 G1,
    M2 G2, M2 G4): (A) re-timing their silicon pills, (B) brain-only replay pills (steer10/mech/rep_base_<g>) +
    the measured execution overhead (silicon - brain-only pills) at the game's mean predicted s/pill.
"""
import json
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
CF = os.path.abspath(os.path.join(HERE, "..", "couch_forensics"))
OUT = os.path.join(HERE, "steer11")
PILLS = os.path.join(OUT, "clockcal_pills.jsonl")
FPS = 60.0988
ROWS, COLS = 16, 8
CLEAR4 = ("m1g5", "m2g1", "m2g2", "m2g4")          # 10/05 AI clear games (the validation hold-out)
DT_PAUSE = 15.0                                       # RS.DT_CAP: a > 15 s interval is a pause, not play


def _gravity_passes(b):
    """FaithfulBoard._apply_gravity, counting the passes that moved something (= max fall rows of this settle)."""
    n = 0
    while True:
        bodies = b._bodies()
        bodies.sort(key=lambda bd: max(r for r, _ in bd), reverse=True)
        moved = False
        for body in bodies:
            if b._can_fall(body):
                b._move_body_down(body)
                moved = True
        if not moved:
            return n
        n += 1


def cascade_timed(b):
    """Destructive resolve of a placed board: per step (cells, runs, fall rows). Same order as attack.lines_per_step."""
    sys.path.insert(0, CF)
    from fair_20261004 import count_runs
    steps = []
    while True:
        mask = b._find_clears()
        if not mask.any():
            return steps
        runs = count_runs(b.color)
        cells = int(mask.sum())
        b._apply_clear(mask)
        steps.append((cells, runs, _gravity_passes(b)))


def _target_hmax(S_color, landing):
    C = np.array([int(ch) for ch in S_color]).reshape(ROWS, COLS)
    o, orow, ocol, _ = landing
    cols = [ocol] if o == "V" else [ocol, min(ocol + 1, 7)]
    hm = 0
    for c in cols:
        top = next((r for r in range(ROWS) if C[r, c] > 0), ROWS)
        hm = max(hm, ROWS - top)
    return hm


def extract(only=None):
    """only = 'DAY:GAME' -> steer11/clockcal/pills_DAY_GAME.jsonl (parallel per-game units; `merge` joins them)."""
    sys.path.insert(0, CF)
    import fair_20261004 as FA
    import mech_check as MC
    rows = []
    days = []
    S4 = json.load(open(os.path.join(CF, "summary_fair_20261004.json")))
    days.append(("20261004", os.path.expanduser("~/projects/dr_mario_rl/tmp/fair_20261004/scan"),
                 [(g["game"], g["build"], g["t_round"], g["t_end"], g["t0_first_spawn"], g["dur_s"], g["log"]) for g in S4["games"]],
                 os.path.join(CF, "cases_fair_20261004_ai_pills.jsonl")))
    S5 = json.load(open(os.path.join(CF, "summary_lulu_20261005.json")))
    R5 = {r["game"]: r for r in S5["results"]}
    days.append(("20261005", "/home/struktured/projects/dr_mario_rl/tmp/lulu_20261005/fx/scan",
                 [(g["game"], "FAIR", R5[g["game"]]["t_round"], g["t_end"], g["t0"], g["dur_s"],
                   f"{g['winner']} {g['how']}") for g in S5["games"]],
                 os.path.join(CF, "cases_lulu_20261005_ai_pills.jsonl")))
    import refit_sends_202610 as RS
    nchk = nbad = 0
    for day, scan, games, banked in days:
        FA.SCAN = scan
        B = {}
        for l in open(banked):
            q = json.loads(l)
            B[(q["game"], q["k"])] = q
        for g, build, t_round, t_end, t0, dur, log in games:
            if only is not None and only != f"{day}:{g}":
                continue
            R = FA.load_raw(g, "p2", t_round, t_end)
            cases, _ = FA.ai_attacks(R, t0)
            for k, (r, c) in enumerate(zip(R, cases)):
                bq = B.get((g, k))
                nchk += 1
                if bq is None or abs(bq["t_spawn"] - c["t_spawn"]) > 1e-6 or bq["chain"] != c["chain"] or bq["runs"] != c["runs"]:
                    nbad += 1
                b = FA.placed(r)
                st = cascade_timed(b)
                assert len(st) == c["chain"] and sum(s[1] for s in st) == c["runs"], (day, g, k)
                hm = _target_hmax(r["S"]["color"], r["landing"])
                row = {"day": day, "game": g, "build": build, "k": k, "n": len(R), "t_spawn": r["t_spawn"],
                       "t0": t0, "t_end": t_end, "dur_s": dur, "log": log, "landing": r["landing"],
                       "hmax": hm, "fall": max(0, 15 - hm), "maxh_board": c["max_h_before"],
                       "nsteps": len(st), "runs": c["runs"], "cells": c["cells"], "steps": st,
                       "cfall": int(sum(s[2] for s in st)), "virus_count": c["virus_count"]}
                if k + 1 < len(R):
                    n_ = R[k + 1]
                    row["dt"] = round(n_["t_spawn"] - r["t_spawn"], 4)
                    P = MC.after_pill(r)
                    N = np.array([int(ch) for ch in n_["S"]["color"]]).reshape(ROWS, COLS)
                    extras = [(int(a), int(cc)) for a, cc in np.argwhere((N > 0) & (P.color == 0))]
                    missing = int(((P.color > 0) & (N != P.color)).sum())
                    vol = bool(extras or missing)
                    gsize, how = 0, "none"
                    if vol:
                        if missing == 0:
                            gsize, how = len(extras), "direct"
                        else:
                            s_ = MC.explain(r, n_)
                            gsize, how = (s_, "explained") if s_ not in (None, 0) else (len(extras), "unexplained")
                    gcols = sorted({cc for _, cc in extras})
                    gfall = 0
                    for cc in gcols:
                        top = next((rr for rr in range(ROWS) if P.color[rr, cc] > 0), ROWS)
                        gfall = max(gfall, top - 1)
                    row.update({"vol": int(vol), "gsize": int(gsize or 0), "ghow": how, "gcols": gcols, "gfall": int(gfall),
                                "gclear": int(missing > 0)})
                rows.append(row)
            print(f"{day} {g} {build}: {len(R)} pills, dur {dur:.1f} s, {log}", flush=True)
    os.makedirs(os.path.join(OUT, "clockcal"), exist_ok=True)
    dst = PILLS if only is None else os.path.join(OUT, "clockcal", "pills_%s_%s.jsonl" % tuple(only.split(":")))
    with open(dst, "w") as fh:
        for r in rows:
            fh.write(json.dumps(r) + "\n")
    print(f"banked-case check: {nchk - nbad}/{nchk} pills match cases_*_ai_pills.jsonl on (t_spawn, chain, runs)")
    print(f"-> {dst} ({len(rows)} rows)")
    if only is not None:
        open(dst + ".check", "w").write(json.dumps({"checked": nchk, "bad": nbad}) + "\n")


GAMES = [("20261004", g) for g in ("m1g1", "m1g2", "m2g1", "m2g2", "m2g3", "m3g1", "m3g2", "m3g3", "m4g1", "m4g2")] + \
        [("20261005", g) for g in ("m1g1", "m1g2", "m1g3", "m1g4", "m1g5", "m2g1", "m2g2", "m2g3", "m2g4")]


def merge():
    rows, nchk, nbad = [], 0, 0
    for d, g in GAMES:
        f = os.path.join(OUT, "clockcal", f"pills_{d}_{g}.jsonl")
        rows += [json.loads(l) for l in open(f)]
        c = json.load(open(f + ".check")); nchk += c["checked"]; nbad += c["bad"]
    with open(PILLS, "w") as fh:
        for r in rows:
            fh.write(json.dumps(r) + "\n")
    print(f"merged {len(GAMES)} games, {len(rows)} pills; banked-case check {nchk - nbad}/{nchk} -> {PILLS}")


# ------------------------------------------------------------------------------------------------ fitting
FEATS = {
    # name: (feature list, description)
    "legacy":  ([], "the CURRENT clock, not fitted: (39 + 2 fall + 40 nsteps) f, garbage 0"),
    "M1":      (["one", "fall", "nsteps", "vol"], "plain + per-row drop + per clear step + per volley"),
    "M2":      (["one", "fall", "nsteps", "vol", "gsize"], "M1 + per garbage cell"),
    "M3":      (["one", "fall", "nsteps", "cfall", "vol", "gfall"], "M1 + cascade fall rows + garbage fall rows"),
    "M4":      (["one", "fall", "nsteps", "cfall", "vol", "gfall", "gclear"], "M3 + garbage-set-off clear"),
    "M5":      (["one", "fall", "nsteps", "cfall", "vol", "gsize", "gfall", "gclear"], "M4 + per garbage cell"),
    "M6":      (["one", "fall", "nsteps", "cfall", "vol", "gsize", "gclear"], "M5 without garbage fall rows"),
    "M4d":     (["one", "fall", "nsteps", "cfall", "vol", "gfall", "gclear", "d1005"], "DIAGNOSTIC: M4 + a 10/05 day shift"),
}


def _x(r, f):
    if f == "d1005":
        return float(r["day"] == "20261005")
    return 1.0 if f == "one" else float(r.get(f, 0))


def legacy_s(r):
    return (39.0 + 2.0 * r["fall"] + 40.0 * r["nsteps"]) / FPS


def fit_ols(R, feats):
    X = np.array([[_x(r, f) for f in feats] for r in R]); y = np.array([r["dt"] for r in R])
    beta, *_ = np.linalg.lstsq(X, y, rcond=None)
    return beta


def pred(r, feats, beta):
    return float(sum(b * _x(r, f) for f, b in zip(feats, beta)))


def game_boot(R, feats, B=2000, seed=0):
    """game-cluster bootstrap of the coefficients"""
    rng = np.random.default_rng(seed)
    G = sorted({(r["day"], r["game"]) for r in R})
    by = {g: [r for r in R if (r["day"], r["game"]) == g] for g in G}
    out = []
    for _ in range(B):
        pick = rng.integers(0, len(G), len(G))
        RR = [r for i in pick for r in by[G[i]]]
        out.append(fit_ols(RR, feats))
    return np.percentile(np.array(out), [2.5, 97.5], axis=0)


def fit():
    rows = [json.loads(l) for l in open(PILLS)]
    out = []

    def pr(s=""):
        print(s); out.append(s)
    R = [r for r in rows if "dt" in r]
    paused = [r for r in R if r["dt"] > DT_PAUSE]
    pr(f"per-pill table: {len(rows)} pills, {len(R)} intervals, {len(paused)} > {DT_PAUSE} s excluded as pauses "
       f"{[(r['day'], r['game'], r['k'], r['dt']) for r in paused]}")
    R = [r for r in R if r["dt"] <= DT_PAUSE]
    G = sorted({(r["day"], r["game"]) for r in R})
    pr(f"games {len(G)}: " + ", ".join(f"{d[4:]}/{g}" for d, g in G))
    # ---- descriptive cells (seconds)
    def cell(lab, sel):
        a = np.array([r["dt"] for r in R if sel(r)])
        if len(a):
            pr(f"  {lab:44s} n={len(a):4d} mean {a.mean():.2f} median {np.median(a):.2f} p25/p75 "
               f"{np.percentile(a, 25):.2f}/{np.percentile(a, 75):.2f}  legacy clock mean "
               f"{np.mean([legacy_s(r) for r in R if sel(r)]):.2f}")
    pr("\nDESCRIPTIVE (interval after pill i, seconds):")
    cell("plain (no clear, no garbage)", lambda r: r["nsteps"] == 0 and not r["vol"])
    cell("  plain, fall 0-5", lambda r: r["nsteps"] == 0 and not r["vol"] and r["fall"] <= 5)
    cell("  plain, fall 6-10", lambda r: r["nsteps"] == 0 and not r["vol"] and 6 <= r["fall"] <= 10)
    cell("  plain, fall 11-15", lambda r: r["nsteps"] == 0 and not r["vol"] and r["fall"] >= 11)
    cell("1-step clear, no garbage", lambda r: r["nsteps"] == 1 and not r["vol"])
    cell("2-step clear, no garbage", lambda r: r["nsteps"] == 2 and not r["vol"])
    cell("3+-step clear, no garbage", lambda r: r["nsteps"] >= 3 and not r["vol"])
    cell("garbage after, no own clear", lambda r: r["nsteps"] == 0 and r["vol"])
    cell("garbage after, own clear", lambda r: r["nsteps"] > 0 and r["vol"])
    for s in (1, 2, 3, 4):
        cell(f"  garbage size {s}", lambda r, s=s: r["vol"] and r["gsize"] == s)
    cell("  garbage that set off a clear", lambda r: r["vol"] and r["gclear"])
    for d in ("20261004", "20261005"):
        cell(f"day {d} all", lambda r, d=d: r["day"] == d)
    # ---- models
    pr("\nMODELS (OLS on dt in seconds over all intervals; game-cluster bootstrap 95% CI; frames = s x 60.0988):")
    res = {}
    for name, (feats, desc) in FEATS.items():
        if name == "legacy":
            p = lambda r: legacy_s(r)
        else:
            beta = fit_ols(R, feats); ci = game_boot(R, feats, B=1000)
            res[name] = (feats, beta)
            pr(f"  {name}: {desc}")
            pr("     " + "  ".join(f"{f} {b:+.3f} s [{lo:+.3f}, {hi:+.3f}] ({b * FPS:+.1f} f)"
                                    for f, b, lo, hi in zip(feats, beta, ci[0], ci[1])))
            p = (lambda feats, beta: (lambda r: pred(r, feats, beta)))(feats, beta)
        e = np.array([r["dt"] - p(r) for r in R])
        # leave-one-game-out on per-game totals (first -> last spawn)
        tot = []
        for g in G:
            Rg = [r for r in R if (r["day"], r["game"]) == g]
            if name == "legacy":
                pg = sum(legacy_s(r) for r in Rg)
            else:
                b_ = fit_ols([r for r in R if (r["day"], r["game"]) != g], feats)
                pg = sum(pred(r, feats, b_) for r in Rg)
            tot.append((g, sum(r["dt"] for r in Rg), pg))
        rel = np.array([(o - p_) / o for _, o, p_ in tot])
        pr(f"     per-pill residual mean {e.mean():+.3f} s, rmse {np.sqrt((e ** 2).mean()):.3f} s | LOGO game totals: "
           f"mean rel err {100 * rel.mean():+.1f}%, mean |rel err| {100 * np.abs(rel).mean():.1f}%, "
           f"max |rel err| {100 * np.abs(rel).max():.1f}%")
    return R, res, out, G


# CHOSEN (declared after the model table, before any sim game on it): M4 -- best per-pill RMSE without over-
# parameterisation (M5's gsize drives `vol` negative), LOGO game-total |err| 3.1%, hold-out clear-game median resid
# -1.6 s; its two gravity rates (cascade 15.9 f/row, garbage 16.9 f/row) were fitted independently and agree, as one ROM
# falling routine predicts. Garbage cascades are charged as the gclear lump only (the sim's gstep = gcfall = 0), which is
# exactly M4's feature set.
CHOSEN = "M4"
BRAIN_ONLY = {"m1g5": 103, "m2g1": 101, "m2g2": 110, "m2g4": 76}     # steer10/pacegap_lulu10b_base.txt (rep_base p0 replays)


def validate(rows, feats, pr):
    """HOLD-OUT: fit on every game except the 4 10/05 AI clear games; predict those 4 games' clear times."""
    R = [r for r in rows if "dt" in r and r["dt"] <= DT_PAUSE]
    train = [r for r in R if not (r["day"] == "20261005" and r["game"] in CLEAR4)]
    beta = fit_ols(train, feats)
    pr(f"\nVALIDATION (hold-out: fitted on {len({(r['day'], r['game']) for r in train})} games / {len(train)} intervals, "
       f"NOT the 4 AI clear games): " + "  ".join(f"{f} {b * FPS:+.1f} f" for f, b in zip(feats, beta)))
    obs_a, pred_a, pred_b, leg_a = [], [], [], []
    for g in CLEAR4:
        P = sorted([r for r in rows if r["day"] == "20261005" and r["game"] == g], key=lambda r: r["k"])
        last = dict(P[-1], vol=0, gsize=0, gfall=0, gclear=0)
        off = P[0]["t_spawn"] - P[0]["t0"]                       # round start -> the AI's first spawn (observed)
        pa = off + sum(pred(r, feats, beta) for r in P[:-1]) + pred(last, feats, beta)
        la = off + sum(legacy_s(r) for r in P)
        obs = P[0]["dur_s"]
        spp = (pa - off) / len(P)
        pills_b = BRAIN_ONLY[g] + 22                             # brain-only pills + the median execution overhead (22)
        pb = off + pills_b * spp
        obs_a.append(obs); pred_a.append(pa); pred_b.append(pb); leg_a.append(la)
        pr(f"  {g}: observed {obs:.1f} s ({len(P)} silicon pills) | (A) corrected clock on the silicon pills "
           f"{pa:.1f} s (resid {obs - pa:+.1f} s, {100 * (obs - pa) / obs:+.1f}%) | legacy clock {la:.1f} s "
           f"({100 * (obs - la) / obs:+.1f}%) | (B) (brain-only {BRAIN_ONLY[g]} + 22) pills x {spp:.2f} s/pill = "
           f"{pb:.1f} s (resid {obs - pb:+.1f})")
    m = lambda a: float(np.median(a))
    pr(f"  MEDIAN of the 4: observed {m(obs_a):.1f} s | (A) {m(pred_a):.1f} s (resid {m(obs_a) - m(pred_a):+.1f} s; "
       f"per-game mean |resid| {np.mean(np.abs(np.array(obs_a) - pred_a)):.1f} s) | legacy {m(leg_a):.1f} s | "
       f"(B) {m(pred_b):.1f} s (resid {m(obs_a) - m(pred_b):+.1f} s)")
    return beta


if __name__ == "__main__":
    os.chdir(HERE)
    if sys.argv[1] == "extract":
        extract(sys.argv[2] if len(sys.argv) > 2 else None)
    elif sys.argv[1] == "merge":
        merge()
    elif sys.argv[1] == "fit":
        R, res, out, G = fit()
        from collections import Counter
        out.append(f"\nvolley classification (intervals): {dict(Counter(r.get('ghow') for r in R))}; sizes "
                   f"{dict(Counter(r['gsize'] for r in R if r['vol']))}")
        print(out[-1])
        rows = [json.loads(l) for l in open(PILLS)]
        for name in sys.argv[2:] or ["M1", "M3", "M4", "M5", "M6"]:
            pr = lambda s_: (print(s_), out.append(s_))
            pr(f"\n=== {name} ===")
            validate(rows, FEATS[name][0], pr)
        # ---- the CHOSEN model, refitted on ALL 19 games -> the sim clock (frames)
        feats = FEATS[CHOSEN][0]
        Rall = [r for r in rows if "dt" in r and r["dt"] <= DT_PAUSE]
        beta = fit_ols(Rall, feats)
        b = {f: float(v * FPS) for f, v in zip(feats, beta)}
        clock = {"name": "couch11", "base": b["one"], "fall": b["fall"], "step": b["nsteps"], "cfall": b["cfall"],
                 "vol": b["vol"], "gsize": 0.0, "gfall": b["gfall"], "gclear": b["gclear"], "gstep": 0.0, "gcfall": 0.0,
                 "model": CHOSEN, "feats": feats, "units": "NES frames (60.0988/s)", "n_intervals": len(Rall),
                 "n_games": len({(r["day"], r["game"]) for r in Rall}),
                 "source": "steer11/clockcal_pills.jsonl (10/04 owner vs FAIR/FAIR2 10 games + 10/05 lulu vs FAIR 9 games)"}
        json.dump(clock, open(os.path.join(OUT, "clock_couch11.json"), "w"), indent=1)
        out.append(f"\nCHOSEN {CHOSEN} (all 19 games) -> steer11/clock_couch11.json: " +
                   ", ".join(f"{k} {clock[k]:.1f} f" for k in ("base", "fall", "step", "cfall", "vol", "gfall", "gclear")))
        print(out[-1])
        open(os.path.join(OUT, "clockcal.txt"), "w").write("\n".join(out) + "\n")
