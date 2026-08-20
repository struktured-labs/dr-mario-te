#!/usr/bin/env python3
"""Apply PREREG_136_PRESTART_LATENCY.md's registered reading rule. Nothing here
chooses a threshold: R1's bar (0.894), the minimum sample (300) and the interval
method (game-level cluster bootstrap) are all fixed by the prereg, which was
committed before the data existed.

Why a CLUSTER bootstrap and not Wilson. Releases are not independent: a game with a
tall board contributes a run of correlated releases, so Wilson -- which assumes n
independent Bernoulli draws -- understates the interval. The prereg makes the cluster
interval the decision instrument and Wilson a reported comparison, so the more
optimistic number can never be the one a verdict rests on.

Run: python3 verdict_136.py cur.jsonl leg.jsonl        (exit 0 always; read the text)
     python3 verdict_136.py --selftest                 (exit 1 on any failure)
"""
from __future__ import annotations

import argparse
import json
import math
import random
import sys

import analyze_shadowlat as A

BAR = 0.894              # #92's published spawn-ready share, registered as the bar
MIN_WINDOW_SCORED = 300  # below this: INDETERMINATE-BY-SAMPLE, per the prereg
BOOT = 10000
BOOT_SEED = 136          # fixed so the interval is reproducible, not resampled to taste


def load(path, arm):
    out = []
    with open(path) as fh:
        for ln in fh:
            ln = ln.strip()
            if not ln:
                continue
            r = json.loads(ln)
            if arm and r.get("arm") != arm:
                continue
            out.append(r)
    return out


def per_game_ontime(rows):
    """[(n_scored, n_ontime)] per game -- the clustering unit for the bootstrap."""
    out = []
    for r in rows:
        lat = r.get("lat")
        if lat is None:
            continue
        n = k = 0
        for clocks, _entry, _mh, pg, h in lat:
            if not pg or h < 0:
                continue
            n += 1
            if A.silicon_frames(clocks) <= A.garbage_window_frames(h):
                k += 1
        out.append((n, k))
    return out


def wilson(k, n, z=1.96):
    if n == 0:
        return (0.0, 1.0)
    p = k / n
    d = 1 + z * z / n
    c = p + z * z / (2 * n)
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n))
    return ((c - h) / d, (c + h) / d)


def cluster_boot(games, reps=BOOT, seed=BOOT_SEED):
    """Percentile interval for the pooled on-time SHARE, resampling GAMES.

    Games contributing zero scored releases are kept in the resample: dropping them
    would condition the denominator on the outcome (a game with no release is a real
    draw from the same distribution, it just carries no weight)."""
    live = [g for g in games if g[0] > 0]
    if not live:
        return (0.0, 1.0)
    rng = random.Random(seed)
    n_g = len(games)
    est = []
    for _ in range(reps):
        n = k = 0
        for _ in range(n_g):
            gn, gk = games[rng.randrange(n_g)]
            n += gn
            k += gk
        if n:
            est.append(k / n)
    est.sort()
    if not est:
        return (0.0, 1.0)
    return (est[int(0.025 * len(est))], est[min(len(est) - 1, int(0.975 * len(est)))])


def r1(games):
    n = sum(g[0] for g in games)
    k = sum(g[1] for g in games)
    p = k / n if n else float("nan")
    lo, hi = cluster_boot(games)
    wlo, whi = wilson(k, n)
    if n < MIN_WINDOW_SCORED:
        verdict = "INDETERMINATE-BY-SAMPLE"
    elif lo >= BAR:
        verdict = "SURVIVES"
    elif hi < BAR:
        verdict = "DEGRADED"
    else:
        verdict = "INDETERMINATE"
    return dict(n=n, k=k, p=p, lo=lo, hi=hi, wlo=wlo, whi=whi, verdict=verdict,
                n_games=len(games))


def r2(rep):
    """h* = largest h whose window exceeds the median silicon cost at that h, then
    the two registered shares around it."""
    tbl = rep["by_h_hit"]
    hstar = None
    for h_s, e in sorted(tbl.items(), key=lambda kv: int(kv[0])):
        if e["window_frames"] > e["median_frames_silicon"]:
            hstar = int(h_s)
    if hstar is None:
        return dict(hstar=None, below=None, above=None, reaffirmed=False,
                    n_below=0, n_above=0)
    nb = kb = na = ka = 0
    for h_s, e in tbl.items():
        h = int(h_s)
        if h <= hstar - 1:
            nb += e["n"]; kb += e["late"]["silicon"]
        elif h >= hstar + 1:
            na += e["n"]; ka += e["late"]["silicon"]
    below = kb / nb if nb else None
    above = ka / na if na else None
    ok = below is not None and below < 0.05 and above is not None and above > 0.50
    return dict(hstar=hstar, below=below, above=above, reaffirmed=ok,
                n_below=nb, n_above=na)


def median(xs):
    s = sorted(xs)
    n = len(s)
    if not n:
        return float("nan")
    m = n // 2
    return s[m] if n % 2 else 0.5 * (s[m - 1] + s[m])


def r3(cur_rows, leg_rows):
    """Median silicon frames per decision, paired BY SEED."""
    def per_seed(rows):
        d = {}
        for r in rows:
            lat = r.get("lat")
            if lat:
                d[r["seed"]] = median([A.silicon_frames(x[0]) for x in lat])
        return d
    c, l = per_seed(cur_rows), per_seed(leg_rows)
    seeds = sorted(set(c) & set(l))
    diffs = [c[s] - l[s] for s in seeds]
    if not diffs:
        return dict(n=0, mean=float("nan"), lo=float("nan"), hi=float("nan"))
    m = sum(diffs) / len(diffs)
    sd = math.sqrt(sum((x - m) ** 2 for x in diffs) / (len(diffs) - 1)) if len(diffs) > 1 else 0.0
    se = sd / math.sqrt(len(diffs))
    return dict(n=len(diffs), mean=m, lo=m - 1.96 * se, hi=m + 1.96 * se,
                med_cur=median(list(c.values())), med_leg=median(list(l.values())))


def r4(rows):
    """The #124 correction, measured PAIRED within release: h_legacy - h_corrected
    and the frames of window it was costing."""
    dh, dw = [], []
    for r in rows:
        for h_fix, h_leg in r.get("h_legacy", []):
            if h_fix < 0:
                continue
            dh.append(h_leg - h_fix)
            dw.append(A.garbage_window_frames(h_fix)
                      - A.GARBAGE_WINDOW_BASE + A.GARBAGE_WINDOW_PER_H * h_leg)
    if not dh:
        return dict(n=0)
    return dict(n=len(dh), med_dh=median(dh), med_dw=median(dw),
                frac_zero=sum(1 for x in dh if x == 0) / len(dh),
                min_dh=min(dh), max_dh=max(dh))


def population_gate(rep, r4res, rows):
    """G4, the rule-7 population check: is the corpus the one the prereg assumes?"""
    checks = []
    checks.append(("n_window_unscorable == 0", rep["n_window_unscorable"] == 0,
                   f"{rep['n_window_unscorable']}"))
    ok_nonzero = r4res.get("n", 0) > 0 and r4res.get("med_dh", 0) >= 1
    checks.append(("median(h_legacy - h_corrected) >= 1 -- the #124 defect is "
                   "EXERCISED on this corpus", ok_nonzero,
                   f"median {r4res.get('med_dh')} over n={r4res.get('n')}"))
    fw = {r.get("fw_md5_expected") for r in rows}
    man = {r.get("manifest") for r in rows}
    checks.append(("one firmware md5 across the arm", len(fw) == 1, str(fw)))
    checks.append(("one rolled code manifest across the arm", len(man) == 1, str(man)))
    errs = [r for r in rows if r.get("result") == "ERROR"]
    checks.append(("no ERROR games", not errs, f"{len(errs)} errors"))
    return checks


def report(cur_path, leg_path):
    cur = load(cur_path, "p136_cur")
    leg = load(leg_path, "p136_leg") if leg_path else []
    rep_cur = A.analyze(cur)
    games = per_game_ontime(cur)
    R1, R2 = r1(games), r2(rep_cur)
    R4 = r4(cur)

    print(f"=== #136 VERDICT (prereg 906787d) ===")
    print(f"arm p136_cur: {len(cur)} games, {rep_cur['n_decisions']} decisions, "
          f"{rep_cur['n_post_garbage']} releases")
    print("\n-- G4 population / provenance gate --")
    allok = True
    for name, ok, detail in population_gate(rep_cur, R4, cur):
        allok &= ok
        print(f"  [{'PASS' if ok else 'FAIL'}] {name}  ({detail})")

    print("\n-- R1 spawn-ready share (silicon domain) --")
    print(f"  on time {R1['k']}/{R1['n']} = {100*R1['p']:.2f}%  over {R1['n_games']} games")
    print(f"  cluster bootstrap 95% [{100*R1['lo']:.2f}, {100*R1['hi']:.2f}]  "
          f"(Wilson [{100*R1['wlo']:.2f}, {100*R1['whi']:.2f}], reported only)")
    print(f"  bar {100*BAR}%  =>  VERDICT: {R1['verdict']}")

    print("\n-- R2 mid-board re-affirmation --")
    if R2["hstar"] is None:
        print("  h* undefined: no h has a window exceeding its median cost")
    else:
        b = "n/a" if R2["below"] is None else f"{100*R2['below']:.2f}% (n={R2['n_below']})"
        a = "n/a" if R2["above"] is None else f"{100*R2['above']:.2f}% (n={R2['n_above']})"
        print(f"  h* = {R2['hstar']};  late at h<=h*-1: {b};  late at h>=h*+1: {a}")
        print(f"  registered bars <5% / >50%  =>  "
              f"{'RE-AFFIRMED' if R2['reaffirmed'] else 'NOT re-affirmed'}")

    print("\n-- by exact h_hit --")
    for h, e in rep_cur["by_h_hit"].items():
        print(f"  h={h:>2} n={e['n']:5d} W={e['window_frames']:4d}f "
              f"late={e['late']['silicon']:4d} median={e['median_frames_silicon']}f")

    print("\n-- R4 size of the #124 correction (paired, within release) --")
    if R4["n"]:
        print(f"  n={R4['n']}  median(h_legacy - h_corrected) = {R4['med_dh']}  "
              f"[{R4['min_dh']}, {R4['max_dh']}]  identical on {100*R4['frac_zero']:.1f}%")
        print(f"  median window understated by {R4['med_dw']} frames")

    if leg:
        rep_leg = A.analyze(leg)
        L1 = r1(per_game_ontime(leg))
        R3 = r3(cur, leg)
        print("\n-- LEGACY FIRMWARE ARM (e970e9ab, #92's firmware, corrected window) --")
        print(f"  {len(leg)} games, {rep_leg['n_post_garbage']} releases")
        print(f"  on time {L1['k']}/{L1['n']} = {100*L1['p']:.2f}%  "
              f"cluster 95% [{100*L1['lo']:.2f}, {100*L1['hi']:.2f}]")
        print("\n-- R3 generation delta (descriptive) --")
        print(f"  paired on {R3['n']} seeds; median cost cur {R3.get('med_cur'):.2f} f "
              f"vs leg {R3.get('med_leg'):.2f} f")
        print(f"  mean paired diff (cur - leg) = {R3['mean']:+.3f} f  "
              f"95% [{R3['lo']:+.3f}, {R3['hi']:+.3f}]")
    return allok


# --------------------------------------------------------------------------------
# SELFTEST -- the verdict script is gated too: it must produce the registered answer
# on hand-built tables that straddle every threshold, and must FAIL on wrong ones.
# --------------------------------------------------------------------------------
def selftest():
    fails = []

    def ck(name, cond):
        print(f"  {'ok  ' if cond else 'FAIL'}  {name}")
        if not cond:
            fails.append(name)

    # R1 routing, straddling the 0.894 bar and the n=300 floor.
    # 40 games x 10 releases, all on time -> p=1.0, interval degenerate at 1.0.
    ck("all-on-time, n=400 -> SURVIVES", r1([(10, 10)] * 40)["verdict"] == "SURVIVES")
    # Same shape but only 20 games = 200 releases: under the registered floor.
    ck("all-on-time, n=200 -> INDETERMINATE-BY-SAMPLE",
       r1([(10, 10)] * 20)["verdict"] == "INDETERMINATE-BY-SAMPLE")
    # 50% on time, plenty of data -> the upper bound is far below the bar.
    ck("half on time, n=400 -> DEGRADED", r1([(10, 5)] * 40)["verdict"] == "DEGRADED")
    # Sitting ON the bar: 894/1000 with real game-to-game spread must straddle.
    mixed = [(10, 9)] * 94 + [(10, 8)] * 6          # 894/1000, exactly on the bar
    v = r1(mixed)
    ck(f"p=89.4% with spread -> INDETERMINATE (got {v['verdict']}, p={v['p']:.3f})",
       abs(v["p"] - 0.894) < 1e-9 and v["verdict"] == "INDETERMINATE")
    # The cluster interval must be WIDER than Wilson when the OUTCOME CLUSTERS BY GAME
    # -- that is the entire reason the prereg picked it. Note this needs real
    # between-game variance to show: `mixed` above is nearly homogeneous (9 or 8 of 10
    # in every game) and there the two agree, which is correct behaviour, not a pass.
    lumpy = r1([(10, 10)] * 93 + [(10, 0)] * 7)      # whole games late together
    ck(f"cluster interval wider than Wilson when games cluster "
       f"({100*(lumpy['hi']-lumpy['lo']):.1f}pp vs {100*(lumpy['whi']-lumpy['wlo']):.1f}pp)",
       (lumpy["hi"] - lumpy["lo"]) > 2 * (lumpy["whi"] - lumpy["wlo"]))
    # ... and on that same data Wilson alone would have called it SURVIVES while the
    # registered instrument does not. This is the check earning its place.
    ck("clustered data: Wilson lower bound clears the bar but the cluster one does not",
       lumpy["wlo"] >= BAR and lumpy["lo"] < BAR
       and lumpy["verdict"] != "SURVIVES")
    # ... and a bootstrap that ignored clustering would be too narrow: a mutant check.
    flat = r1([(1, 1)] * 894 + [(1, 0)] * 106)
    ck("unclustered data: cluster interval ~= Wilson (no spurious widening)",
       abs((flat["hi"] - flat["lo"]) - (flat["whi"] - flat["wlo"])) < 0.02)

    # R2 routing on a hand table: cost flat at 45 f, so W>45 iff h <= 13 (W=56).
    def tbl(rows):
        return {"by_h_hit": {str(h): {"n": n, "window_frames": A.garbage_window_frames(h),
                                      "late": {"silicon": k, "sim_lockstep": 0},
                                      "median_frames_silicon": med}
                             for h, n, k, med in rows}}
    t = tbl([(10, 100, 0, 45.0), (13, 20, 1, 45.0), (15, 10, 9, 45.0)])
    g = r2(t)
    ck(f"h* = 13 on a flat-45 f table (got {g['hstar']})", g["hstar"] == 13)
    ck("mid-board RE-AFFIRMED when 0% late below and 90% late above", g["reaffirmed"])
    # Same h*, but lateness leaks below the crossover -> must NOT re-affirm.
    t2 = tbl([(10, 100, 20, 45.0), (13, 20, 1, 45.0), (15, 10, 9, 45.0)])
    ck("NOT re-affirmed when 20% late below the crossover",
       not r2(t2)["reaffirmed"])
    # h* exists but the near-death side is fine too -> also not the #92 shape.
    t3 = tbl([(10, 100, 0, 45.0), (13, 20, 0, 45.0), (15, 10, 1, 45.0)])
    ck("NOT re-affirmed when the near-death side is only 10% late",
       not r2(t3)["reaffirmed"])

    # R4 non-vacuity: identical legacy/corrected must be caught as the inert case.
    inert = [{"h_legacy": [[5, 5]] * 50}]
    ck("R4 median 0 on an inert corpus", r4(inert)["med_dh"] == 0)
    ck("population gate FAILS on the inert corpus",
       not all(ok for _n, ok, _d in population_gate(
           {"n_window_unscorable": 0}, r4(inert),
           [{"fw_md5_expected": "x", "manifest": "y", "result": "clear"}])))
    # diffs 13, 1, 9 -> median 9; the window it was costing is 16*9 = 144 frames.
    real = [{"h_legacy": [[3, 16], [7, 8], [1, 10]]}]
    ck("R4 median 9 on a corpus where the defect bites", r4(real)["med_dh"] == 9)
    ck("R4 median window understatement 144 f", r4(real)["med_dw"] == 144)

    if fails:
        print(f"\n{len(fails)} SELFTEST FAILURE(S): {fails}")
        return 1
    print("\nselftest: all checks pass")
    return 0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("cur", nargs="?")
    ap.add_argument("leg", nargs="?")
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args()
    if a.selftest:
        return selftest()
    if not a.cur:
        ap.error("need the cur jsonl (or --selftest)")
    report(a.cur, a.leg)
    return 0


if __name__ == "__main__":
    sys.exit(main())
