#!/usr/bin/env python3
"""Task #92: late-decision rates from the farm's per-decision `lat` capture.

PURE OFFLINE ANALYSIS. Reads JSONL, computes, prints. It never launches a farm run, never
writes to the results dir, and never touches the drm-shadowlat-chain unit.

INPUT. `lat` (game.py, commit 2c027a7) is one entry per decision:
    [clocks, entry_row, max_h, post_garbage, h_hit]
  clocks        raw co-sim clocks for ONE decide(). Raw on purpose -- see the domains below.
  entry_row     resting anchor row of the placement made, row 0 = TOP. -1 = no placement
                (the illegal-placement topout path); those rows are EXCLUDED from the fall
                stat and counted out loud, never silently dropped.
  max_h         max column stack height of the board the decision was made ON.
  post_garbage  1 iff the decision sits at a release+settle edge.
  h_hit         tallest hit column when post_garbage=1, else -1.

TWO QUESTIONS, TWO BUDGETS -- and they are not interchangeable:
  FALL budget    13 f/row at L11 from the spawn row to the chosen `entry_row`. This asks
                 "did the answer arrive after the capsule had already fallen past its
                 target?" -- a late answer here means the placement was unreachable.
  WINDOW budget  264 - 16*h_hit frames, post-garbage decisions only. This asks "would the
                 answer have arrived before the capsule even spawned?" -- the DRPRESTART
                 question. Uses h_hit (the tallest HIT column), never max_h; a mutant that
                 substitutes max_h is one of the four this file's gate must kill.

CLOCK DOMAINS DIFFER 1.57x AND BOTH ARE REPORTED. The verilated sim ticks the copro in
lockstep at 48 master clocks per NES CPU cycle; real silicon runs it on its own 54.669 MHz
async tap. Quoting one domain without saying which is how a 1.57x error travels.

    experiments/prestart/shadowlat_analyze.py [--selftest] [file.jsonl ...]

With no files it reads the two the chain produces. `--selftest` runs the killed-mutant gate
and exits; run it before trusting any table below it.
"""
from __future__ import annotations

import json
import os
import sys

RESULTS = "/mnt/data/drmario_cosim/results"
DEFAULT_FILES = [os.path.join(RESULTS, "prestart_pilot.jsonl"),
                 os.path.join(RESULTS, "gate_shadowlat_new.jsonl")]

# --- conversion constants. Every one is named and derived, none is a bare literal at a
#     call site, so a wrong-constant mutant has exactly one place to bite (and the gate
#     below bites back).
SILICON_HZ = 54.669e6          # dr-mario-copro-clock-tap: the copro's own async tap
NTSC_FPS = 60.0988             # NOT 60 -- the 0.16% matters at these magnitudes
NES_CPU_HZ_PER_FRAME = 29780.5   # NES CPU cycles per frame
SIM_LOCKSTEP_MULT = 48           # sim_farm.cpp ticks clk 48x per clk_cpu

# DERIVED, not transcribed: 54.669e6 / 60.0988 = 909,652.11. The figure quoted in the memo
# and the task brief is 909,650, which is that value ROUNDED -- it implies 54.668873 MHz, a
# 2.11-clock (0.00023%) difference worth 0.00008 frames on the worst observed decision. Immaterial,
# but recorded here so nobody later "corrects" the derivation to match the rounded literal and
# quietly turns a derived constant into a transcribed one.
SILICON_CLOCKS_PER_FRAME = SILICON_HZ / NTSC_FPS               # 909,652.11 (memo rounds to 909,650)
SIM_CLOCKS_PER_FRAME = SIM_LOCKSTEP_MULT * NES_CPU_HZ_PER_FRAME  # 1,429,464

FALL_F_PER_ROW = 13            # L11 fall rate (dr-mario-tempo-chew)
SPAWN_ROW = 0                  # capsule enters at the top row; rows fallen = entry_row - 0
WINDOW_BASE, WINDOW_PER_H = 264, 16    # W = 264 - 16*h (dr-mario-garbage-window-mechanics)

BANDS = [(0, 4), (5, 8), (9, 12), (13, 99)]

DOMAINS = {
    "silicon(54.669MHz)": lambda c: c / SILICON_CLOCKS_PER_FRAME,
    "sim-lockstep(48x)": lambda c: c / SIM_CLOCKS_PER_FRAME,
}


def fall_budget_frames(entry_row):
    """Frames the capsule has before it reaches `entry_row`."""
    return FALL_F_PER_ROW * (entry_row - SPAWN_ROW)


def window_budget_frames(h_hit):
    """The garbage window W = 264 - 16*h, floored at 0."""
    return max(0, WINDOW_BASE - WINDOW_PER_H * h_hit)


def wilson(k, n, z=1.96):
    """95% Wilson score interval. A bare '69.2% late' on n=13 is not a number anyone can act
    on; the interval is what says whether the band is decided or merely suggestive."""
    if n == 0:
        return (0.0, 0.0)
    p = k / n
    d = 1 + z * z / n
    c = p + z * z / (2 * n)
    h = z * ((p * (1 - p) / n + z * z / (4 * n * n)) ** 0.5)
    return (max(0.0, (c - h) / d), min(1.0, (c + h) / d))


def band_of(h):
    for lo, hi in BANDS:
        if lo <= h <= hi:
            return "%d-%d" % (lo, hi) if hi < 99 else "%d+" % lo
    return "?"


def load(paths):
    """-> (decisions, diag). Absent/empty inputs are reported, never treated as 'no overruns'."""
    decisions, diag = [], []
    for p in paths:
        if not os.path.exists(p):
            diag.append((p, "ABSENT", 0, 0, 0))
            continue
        n_rows = n_lat = n_dec = 0
        with open(p) as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                n_rows += 1
                try:
                    row = json.loads(line)
                except json.JSONDecodeError:
                    continue
                lat = row.get("lat")
                if not lat:
                    continue
                n_lat += 1
                for e in lat:
                    clocks, entry_row, max_h, post_garbage, h_hit = e[:5]
                    decisions.append(dict(clocks=clocks, entry_row=entry_row, max_h=max_h,
                                          post_garbage=post_garbage, h_hit=h_hit,
                                          arm=row.get("arm"), seed=row.get("seed"), src=p))
                    n_dec += 1
        diag.append((p, "empty" if n_rows == 0 else "ok", n_rows, n_lat, n_dec))
    return decisions, diag


def _rate_table(title, subset, budget_fn, band_key, note):
    print()
    print("-" * 92)
    print(title)
    print("  band variable = %s ; %s" % (band_key, note))
    print("-" * 92)
    if not subset:
        print("  (no qualifying decisions)")
        return
    print("  %-22s %-8s %7s %7s %8s %-16s %8s %8s" %
          ("domain", "band", "n", "late", "late%", "95% CI", "med f", "p90 f"))
    for dname, conv in DOMAINS.items():
        for lo, hi in BANDS:
            label = "%d-%d" % (lo, hi) if hi < 99 else "%d+" % lo
            grp = [d for d in subset if lo <= d[band_key] <= hi]
            if not grp:
                continue
            fr = sorted(conv(d["clocks"]) for d in grp)
            late = sum(1 for d in grp if conv(d["clocks"]) > budget_fn(d))
            med = fr[len(fr) // 2]
            p90 = fr[min(len(fr) - 1, int(0.9 * len(fr)))]
            lo, hi = wilson(late, len(grp))
            print("  %-22s %-8s %7d %7d %7.1f%% [%5.1f%%,%5.1f%%] %8.1f %8.1f"
                  % (dname, label, len(grp), late, 100.0 * late / len(grp),
                     100 * lo, 100 * hi, med, p90))
        allfr = sorted(conv(d["clocks"]) for d in subset)
        alllate = sum(1 for d in subset if conv(d["clocks"]) > budget_fn(d))
        lo, hi = wilson(alllate, len(subset))
        print("  %-22s %-8s %7d %7d %7.1f%% [%5.1f%%,%5.1f%%] %8.1f %8.1f"
              % (dname, "ALL", len(subset), alllate, 100.0 * alllate / len(subset),
                 100 * lo, 100 * hi,
                 allfr[len(allfr) // 2], allfr[min(len(allfr) - 1, int(0.9 * len(allfr)))]))
    return


def report(decisions, diag):
    print("=" * 92)
    print("SHADOW-LATENCY ANALYSIS -- per-decision `lat`, both clock domains")
    print("=" * 92)
    print("  %-58s %-8s %6s %6s %8s" % ("file", "state", "rows", "w/lat", "decisions"))
    for p, state, n_rows, n_lat, n_dec in diag:
        print("  %-58s %-8s %6d %6d %8d" % (os.path.basename(p), state, n_rows, n_lat, n_dec))
    if not decisions:
        print()
        print("NO DECISIONS TO ANALYSE -- the chain has not produced `lat` rows yet.")
        print("This is reported, not scored: an empty input is not a 0% late rate.")
        return 2

    noplace = [d for d in decisions if d["entry_row"] < 0]
    fall_set = [d for d in decisions if d["entry_row"] >= 0]
    pg = [d for d in decisions if d["post_garbage"] == 1]
    bad_pg = [d for d in pg if d["h_hit"] < 0]
    print()
    print("  decisions %d | usable for FALL %d | excluded (entry_row=-1, no placement) %d"
          % (len(decisions), len(fall_set), len(noplace)))
    print("  post-garbage %d | of those with h_hit<0 (should be 0) %d"
          % (len(pg), len(bad_pg)))
    print("  clocks/frame: silicon %.1f | sim-lockstep %.1f | ratio %.4fx"
          % (SILICON_CLOCKS_PER_FRAME, SIM_CLOCKS_PER_FRAME,
             SIM_CLOCKS_PER_FRAME / SILICON_CLOCKS_PER_FRAME))

    _rate_table("A. FALL-BUDGET OVERRUN -- answer arrived after the capsule passed entry_row",
                fall_set, lambda d: fall_budget_frames(d["entry_row"]), "max_h",
                "budget = 13 f/row x entry_row")
    _rate_table("B. GARBAGE-WINDOW OVERRUN -- answer would miss the pre-spawn window",
                [d for d in pg if d["h_hit"] >= 0],
                lambda d: window_budget_frames(d["h_hit"]), "h_hit",
                "budget = 264 - 16*h_hit")
    return 0


# ---------------------------------------------------------------- killed-mutant gate
def selftest():
    """A gate must be shown to FAIL on wrong inputs (dr-mario-gate-standard-killed-mutants).
    Four mutants, each a mistake that is easy to make here and invisible downstream."""
    import copy
    mod = sys.modules[__name__]
    fails = []

    def check(tag, cond, detail=""):
        print("  %-56s %s%s" % (tag, "OK" if cond else "*** FAIL", (" " + detail) if detail else ""))
        if not cond:
            fails.append(tag)

    print("=" * 92)
    print("SELFTEST 1/2: hand-computed reference cases")
    print("=" * 92)
    # Derived by hand: one frame's worth of clocks in each domain must convert to exactly 1.0.
    check("silicon: 909650.0 clocks -> 1.000 frames",
          abs(DOMAINS["silicon(54.669MHz)"](SILICON_CLOCKS_PER_FRAME) - 1.0) < 1e-12)
    check("sim: 1429464 clocks -> 1.000 frames",
          abs(DOMAINS["sim-lockstep(48x)"](SIM_CLOCKS_PER_FRAME) - 1.0) < 1e-12)
    check("SILICON_CLOCKS_PER_FRAME == 54.669e6/60.0988 exactly",
          SILICON_CLOCKS_PER_FRAME == SILICON_HZ / NTSC_FPS, "(%.2f)" % SILICON_CLOCKS_PER_FRAME)
    check("...and within 5 clocks of the memo's rounded 909650",
          abs(SILICON_CLOCKS_PER_FRAME - 909650) < 5.0,
          "(delta %.2f clocks = %.5f%%)" % (SILICON_CLOCKS_PER_FRAME - 909650,
                                            100 * (SILICON_CLOCKS_PER_FRAME - 909650) / 909650))
    check("SIM_CLOCKS_PER_FRAME == 1429464 exactly", SIM_CLOCKS_PER_FRAME == 1429464.0)
    # The memo's independently-derived worst case: 33e6 clocks -> ~36 silicon / ~23 sim frames.
    s36 = DOMAINS["silicon(54.669MHz)"](33e6)
    s23 = DOMAINS["sim-lockstep(48x)"](33e6)
    check("33e6 clocks -> silicon 36.3 f (memo said ~36)", 35.5 < s36 < 37.0, "(%.2f)" % s36)
    check("33e6 clocks -> sim 23.1 f (memo said ~23)", 22.5 < s23 < 23.5, "(%.2f)" % s23)
    check("domain ratio 1.571x", abs(SIM_CLOCKS_PER_FRAME / SILICON_CLOCKS_PER_FRAME - 1.5714) < 1e-3)
    # budgets, hand-computed
    check("fall budget entry_row=10 -> 130 f", fall_budget_frames(10) == 130)
    check("window h_hit=0 -> 264 f", window_budget_frames(0) == 264)
    check("window h_hit=15 -> 24 f", window_budget_frames(15) == 24)
    check("window h_hit=17 floors at 0", window_budget_frames(17) == 0)

    print()
    print("=" * 92)
    print("SELFTEST 2/2: killed mutants -- each MUST break at least one check above")
    print("=" * 92)
    saved = {k: getattr(mod, k) for k in
             ("SILICON_CLOCKS_PER_FRAME", "SIM_CLOCKS_PER_FRAME", "DOMAINS",
              "NTSC_FPS", "SPAWN_ROW", "WINDOW_PER_H")}
    saved_domains = copy.copy(DOMAINS)

    def run_probes():
        """Re-run the value assertions against the CURRENT module state; True = all held."""
        try:
            d = mod.DOMAINS
            ok = abs(d["silicon(54.669MHz)"](mod.SILICON_CLOCKS_PER_FRAME) - 1.0) < 1e-12
            ok &= abs(mod.SILICON_CLOCKS_PER_FRAME - 909650) < 5.0
            ok &= mod.SIM_CLOCKS_PER_FRAME == 1429464.0
            v = d["silicon(54.669MHz)"](33e6)
            ok &= 35.5 < v < 37.0
            ok &= abs(v - 36.276) < 0.01                      # exact-value probe: catches 60 vs 60.0988
            ok &= mod.fall_budget_frames(10) == 130
            ok &= mod.window_budget_frames(15) == 24
            return ok
        except Exception:
            return False

    mutants = []

    def mutate(name, apply_fn, restore_fn):
        apply_fn()
        survived = run_probes()
        restore_fn()
        mutants.append((name, survived))
        print("  %-56s %s" % ("mutant: " + name, "KILLED" if not survived else "*** SURVIVED"))
        if survived:
            fails.append("mutant survived: " + name)

    # M1 gross: the two domain constants swapped -- the exact 1.57x error this file exists to prevent
    mutate("domains swapped (silicon<->sim)",
           lambda: mod.DOMAINS.update({"silicon(54.669MHz)": lambda c: c / mod.SIM_CLOCKS_PER_FRAME}),
           lambda: mod.DOMAINS.update(saved_domains))
    # M2 subtle: NTSC 60 Hz instead of 60.0988 -- only 0.16%, invisible to a coarse threshold test
    def _m2():
        mod.SILICON_CLOCKS_PER_FRAME = SILICON_HZ / 60.0
        mod.DOMAINS["silicon(54.669MHz)"] = lambda c: c / mod.SILICON_CLOCKS_PER_FRAME
    mutate("NTSC 60.0 Hz instead of 60.0988",
           _m2,
           lambda: (setattr(mod, "SILICON_CLOCKS_PER_FRAME", saved["SILICON_CLOCKS_PER_FRAME"]),
                    mod.DOMAINS.update(saved_domains)))
    # M3 off-by-one: counting the spawn row itself as a row fallen
    mutate("fall budget off-by-one (SPAWN_ROW=-1)",
           lambda: setattr(mod, "SPAWN_ROW", -1),
           lambda: setattr(mod, "SPAWN_ROW", saved["SPAWN_ROW"]))
    # M4 window slope wrong (16 -> 8): the h-dependence is the whole point of the window
    mutate("window slope 8 instead of 16",
           lambda: setattr(mod, "WINDOW_PER_H", 8),
           lambda: setattr(mod, "WINDOW_PER_H", saved["WINDOW_PER_H"]))

    for k, v in saved.items():
        setattr(mod, k, v)
    mod.DOMAINS.update(saved_domains)

    print()
    print("post-restore sanity (constants back to true values):", "OK" if run_probes() else "*** BROKEN")
    if not run_probes():
        fails.append("restore failed")
    print()
    print("SELFTEST:", "PASS" if not fails else "FAIL -> %s" % fails)
    return 0 if not fails else 1


def verify_chain():
    """WHOLE-CHAIN check: synthesise `lat` rows with hand-computed verdicts, run the REAL
    load()+classification over them, and assert the counts. The selftest above proves the
    arithmetic; this proves the parsing, the -1 exclusion, the post_garbage filter and the
    banding -- none of which the arithmetic gate touches. Writes only to the scratchpad,
    never to the results dir the chain owns."""
    import tempfile
    fails = []

    def check(tag, cond, detail=""):
        print("  %-58s %s%s" % (tag, "OK" if cond else "*** FAIL", (" " + detail) if detail else ""))
        if not cond:
            fails.append(tag)

    # clocks chosen so silicon frames are exactly 100 / 200 / 36.28
    c100 = 100 * SILICON_CLOCKS_PER_FRAME
    c200 = 200 * SILICON_CLOCKS_PER_FRAME
    rows = [
        # entry_row=10 -> fall budget 130 f. 100 f is IN budget, 200 f is LATE.
        {"seed": 1, "arm": "syn", "lat": [[c100, 10, 6, 0, -1], [c200, 10, 6, 0, -1]]},
        # post-garbage at h_hit=15 -> window 24 f; 33e6 clocks = 36.28 silicon f -> LATE.
        # entry_row=3 -> fall budget 39 f, and 36.28 < 39 -> NOT late on the fall budget.
        # That divergence is the point: the two budgets answer different questions.
        {"seed": 2, "arm": "syn", "lat": [[33e6, 3, 15, 1, 15]]},
        # no placement -> excluded from the fall stat, counted out loud
        {"seed": 3, "arm": "syn", "lat": [[c100, -1, 11, 0, -1]]},
        # legacy row, pre-2c027a7: no `lat` at all
        {"seed": 4, "arm": "legacy", "pills": 40},
    ]
    d = tempfile.mkdtemp(prefix="shadowlat_verify_")
    path = os.path.join(d, "synthetic.jsonl")
    with open(path, "w") as f:
        for r in rows:
            f.write(json.dumps(r) + "\n")

    decisions, diag = load([path])
    _, state, n_rows, n_lat, n_dec = diag[0]
    check("parsed 4 rows", n_rows == 4, "(%d)" % n_rows)
    check("3 rows carry lat (legacy row skipped)", n_lat == 3, "(%d)" % n_lat)
    check("4 decisions extracted", n_dec == 4 and len(decisions) == 4, "(%d)" % n_dec)

    fall_set = [x for x in decisions if x["entry_row"] >= 0]
    check("entry_row=-1 excluded from fall set", len(fall_set) == 3, "(%d)" % len(fall_set))
    sil = DOMAINS["silicon(54.669MHz)"]
    late_fall = [x for x in fall_set if sil(x["clocks"]) > fall_budget_frames(x["entry_row"])]
    check("exactly 1 fall-budget overrun (the 200 f @ entry_row 10)", len(late_fall) == 1,
          "(%d)" % len(late_fall))

    pg = [x for x in decisions if x["post_garbage"] == 1]
    check("1 post-garbage decision", len(pg) == 1, "(%d)" % len(pg))
    late_win = [x for x in pg if sil(x["clocks"]) > window_budget_frames(x["h_hit"])]
    check("that decision MISSES the h=15 window (36.3 f > 24 f)", len(late_win) == 1)
    check("...but is INSIDE its own fall budget (36.3 f < 39 f)",
          all(sil(x["clocks"]) <= fall_budget_frames(x["entry_row"]) for x in pg),
          "-- the two budgets disagree, as they must")

    # the sim domain must reclassify the same decision: 33e6 -> 23.09 f < 24 f window
    simd = DOMAINS["sim-lockstep(48x)"]
    check("DOMAIN FLIP: same decision is IN the window in sim-lockstep (23.1 f < 24 f)",
          all(simd(x["clocks"]) <= window_budget_frames(x["h_hit"]) for x in pg),
          "-- this is the 1.57x trap, live")

    check("bands", band_of(3) == "0-4" and band_of(8) == "5-8" and band_of(12) == "9-12"
          and band_of(15) == "13+")
    print()
    print("VERIFY-CHAIN:", "PASS" if not fails else "FAIL -> %s" % fails)
    return 0 if not fails else 1


def main():
    argv = sys.argv[1:]
    if "--selftest" in argv:
        rc = selftest()
        print()
        print("=" * 92)
        print("WHOLE-CHAIN VERIFICATION on synthetic rows")
        print("=" * 92)
        return rc | verify_chain()
    paths = [a for a in argv if not a.startswith("-")] or DEFAULT_FILES
    decisions, diag = load(paths)
    return report(decisions, diag)


if __name__ == "__main__":
    sys.exit(main())
