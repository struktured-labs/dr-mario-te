#!/usr/bin/env python3
"""L1a -- champion tempo under pressure, recovered from artifacts already on disk.

ZERO NEW COMPUTE. This reads per-seed rows that existing runs already wrote; it does not
execute the simulator. Every number it prints is a re-reading of a stored artifact.

Per PREREG_L1.md:
  G0  outcome-plausibility gate -- recovered rows must reproduce the PUBLISHED headline
      for each file before any distribution is read (rule 7: a structural gate cannot see
      a fault applied to both sides; an outcome assertion can). FAILURE BLOCKS THE RUN.
  (1) pills-to-clear distribution + seed-clustered bootstrap CI on the median
  (2) the same conditioned on LOSING (viruses_left_at_end)
  (3) BLOCKED -- see check_l1a3_feasible(); the stored rows are per-GAME aggregates
  (4) survivorship correction: naive (wins-only) vs Kaplan-Meier with losses censored

Unit of analysis = the seed. One stored row == one seed, so bootstrapping rows IS
seed-clustered.
"""
import json, os, random, statistics as st

RESULTS = "/home/struktured/projects/dr-mario-qa-wt/experiments/eval47/results"
SEC_PER_PILL = 2.5   # project constant, L11 (lulu_proxy/striker_model.py:59). NOT measured here.
B = 10000
random.seed(20260821)

STREAMS = [
    ("clean (blunder corpus)", "blunder_battery.json", None),
    ("canonical drip",         "n120_wt0_ws20.json",   "arm"),
    ("bursty v1.1",            "bursty_v1_1_n120_wt0_ws20.json", "arm"),
    ("lulu-fitted (POOLED)",   "dr_lulu_20260808_rig_n120_wt0_ws20.json", "arm"),
]

# ---------- G0: published headlines these files must reproduce ----------
G0 = [
    ("n120_wt0_ws20.json",  "ctrl", "won",  115),
    ("n120_wt0_ws20.json",  "arm",  "won",  119),
    ("bursty_v1_1_n120_wt0_ws20.json", "arm", "dies_ahead", 9),   # published 7.5%
    ("dr_lulu_20260808_rig_n120_wt0_ws20.json", "arm", "won", 90),        # summary clear1 0.75
    ("dr_lulu_20260808_rig_n120_wt0_ws20.json", "arm", "dies_ahead", 17), # summary dies_ahead1
    ("dr_lulu_20260808_rig_n120_wt0_ws20.json", "ctrl","dies_ahead", 41),
]

def load(fn):
    with open(os.path.join(RESULTS, fn)) as f:
        return json.load(f)

def rows(fn, arm):
    d = load(fn)
    if arm is None:                      # blunder_battery has a different schema
        return d["ai"]["per_game"]
    return d[arm]

def gate_g0():
    print("=" * 74)
    print("G0  OUTCOME-PLAUSIBILITY GATE (rule 7) -- blocks the run on failure")
    print("=" * 74)
    ok = True
    for fn, arm, field, expect in G0:
        got = sum(1 for r in rows(fn, arm) if r.get(field))
        mark = "PASS" if got == expect else "**FAIL**"
        if got != expect:
            ok = False
        print(f"  {mark:9s} {fn:42s} {arm:5s} sum({field}) = {got:4d}  expect {expect}")
    # summary cross-check: the derived clear rate must equal the stored summary field
    d = load("dr_lulu_20260808_rig_n120_wt0_ws20.json")
    got = sum(1 for r in d["arm"] if r["won"]) / len(d["arm"])
    exp = d["summary"]["clear1"]
    mark = "PASS" if abs(got - exp) < 1e-9 else "**FAIL**"
    ok &= (mark == "PASS")
    print(f"  {mark:9s} lulu arm clear rate derived {got:.4f} == stored summary {exp:.4f}")
    print()
    return ok

def qs(xs, p):
    xs = sorted(xs)
    i = (len(xs) - 1) * p
    lo = int(i); hi = min(lo + 1, len(xs) - 1)
    return xs[lo] * (1 - (i - lo)) + xs[hi] * (i - lo)

def boot_median_ci(xs, b=B):
    n = len(xs)
    meds = sorted(st.median(random.choices(xs, k=n)) for _ in range(b))
    return meds[int(.025 * b)], meds[int(.975 * b)]

def km_median(rws):
    """Kaplan-Meier median pills-to-clear, treating a loss as RIGHT-CENSORED at its pill
    count (the game ended before clearing, so a clear would have needed >= that many).
    Returns None when survival never crosses 0.5 -- i.e. censoring is too heavy for the
    median to be identified, which is itself the finding."""
    ev = sorted((r["pills"], 1 if r["won"] else 0) for r in rws)
    n_at_risk = len(ev); S = 1.0; i = 0
    while i < len(ev):
        t = ev[i][0]
        d = sum(1 for x in ev if x[0] == t and x[1] == 1)
        c = sum(1 for x in ev if x[0] == t)
        if d and n_at_risk:
            S *= (1 - d / n_at_risk)
            if S <= 0.5:
                return t
        n_at_risk -= c
        i += c
    return None

def check_l1a3_feasible():
    print("=" * 74)
    print("L1a(3)  BLUNDER-UNDER-VOLLEY HAZARD -- FEASIBILITY CHECK (rule 8)")
    print("=" * 74)
    r = load("dr_lulu_20260808_rig_n120_wt0_ws20.json")["arm"][0]
    print("  stored row schema:", sorted(r.keys()))
    need = "a per-PLACEMENT volley timeline (placement index of each volley received)"
    have = "garbage_injected = a per-GAME TOTAL (%r in this row)" % r["garbage_injected"]
    print(f"  needs: {need}")
    print(f"  has  : {have}")
    print("  => NOT COMPUTABLE from stored artifacts. The rig emits per-GAME aggregates;")
    print("     the volley timeline is never serialized. L1a(3) requires a rig")
    print("     instrumentation change AND a re-run == COMPUTE. It is therefore")
    print("     DEFERRED, not answered, and prediction P3 is UNTESTED.")
    print()

def main():
    if not gate_g0():
        raise SystemExit("G0 FAILED -- artifacts are not what they claim. Nothing published.")

    print("=" * 74)
    print("L1a(1)  PILLS-TO-CLEAR DISTRIBUTION, WINS ONLY  (n=120/arm unless noted)")
    print("        naive/wins-only => a FLOOR on the tempo tax (survivorship)")
    print("=" * 74)
    print(f"  {'stream':24s} {'won':>8s} {'p10':>5s} {'p25':>5s} {'MED':>5s} "
          f"{'[95% CI]':>14s} {'p75':>5s} {'p90':>5s} {'min':>7s}")
    base = None
    for name, fn, arm in STREAMS:
        rws = rows(fn, arm)
        w = [r for r in rws if r.get("won")]
        p = [r["pills"] for r in w]
        lo, hi = boot_median_ci(p)
        med = qs(p, .5)
        if name == "canonical drip":
            base = med
        print(f"  {name:24s} {len(w):4d}/{len(rws):<3d} {qs(p,.1):5.0f} {qs(p,.25):5.0f} "
              f"{med:5.0f} [{lo:5.0f},{hi:5.0f}] {qs(p,.75):5.0f} {qs(p,.9):5.0f} "
              f"{med*SEC_PER_PILL/60:6.1f}m")
    print()
    print("=" * 74)
    print("L1a(4)  SURVIVORSHIP CORRECTION -- naive vs Kaplan-Meier (losses censored)")
    print("=" * 74)
    print(f"  {'stream':24s} {'naive MED':>10s} {'KM MED':>8s}   note")
    for name, fn, arm in STREAMS:
        rws = rows(fn, arm)
        p = [r["pills"] for r in rws if r.get("won")]
        naive = qs(p, .5)
        km = km_median(rws)
        note = "agree" if km is not None and abs(km - naive) <= 4 else (
               "KM undefined (censoring too heavy)" if km is None else "DIVERGE -- quote KM only")
        print(f"  {name:24s} {naive:10.0f} {str(km) if km is not None else 'n/a':>8s}   {note}")
    print()
    print("=" * 74)
    print("L1a(4b) ASSUMPTION-FREE ALL-GAMES QUANTILES -- no censoring model needed")
    print("        'pills by which X% of ALL games have cleared'. Well defined whenever")
    print("        the clear rate exceeds X. This is the number to QUOTE: it needs no")
    print("        claim that a topped-out game 'would have' cleared later.")
    print("=" * 74)
    print(f"  {'stream':24s} {'cleared':>9s} {'ALL-GAMES MED':>14s} {'min':>7s} {'ALL p75':>9s}")
    for name, fn, arm in STREAMS:
        rws = rows(fn, arm)
        n = len(rws)
        cl = sorted(r["pills"] for r in rws if r.get("won"))
        def by(k):
            need = int(k * n)
            return cl[need - 1] if len(cl) >= need else None
        m, p75 = by(.50), by(.75)
        p75s = str(p75) if p75 else "NEVER (>25% never clear)"
        print(f"  {name:24s} {len(cl):4d}/{n:<4d} {m:14d} {m*SEC_PER_PILL/60:6.1f}m {p75s:>9s}")
    print()
    print("=" * 74)
    print("L1a(2)  CONDITIONED ON LOSING -- how close was it when it died?")
    print("=" * 74)
    print(f"  {'stream':24s} {'lost':>5s} {'dies_ahead':>10s} {'med vir left':>13s} {'med pills':>10s}")
    for name, fn, arm in STREAMS:
        rws = rows(fn, arm)
        L = [r for r in rws if not r.get("won")]
        if not L:
            print(f"  {name:24s} {0:5d} {'--':>10s} {'--':>13s} {'--':>10s}   (never lost)")
            continue
        da = sum(1 for r in L if r.get("dies_ahead"))
        vl = [r["viruses_left_at_end"] for r in L if "viruses_left_at_end" in r]
        pl = [r["pills"] for r in L]
        to = sum(1 for r in L if r.get("topout")); sl = sum(1 for r in L if r.get("stall"))
        print(f"  {name:24s} {len(L):5d} {da:10d} "
              f"{(qs(vl,.5) if vl else float('nan')):13.1f} {qs(pl,.5):10.0f}"
              f"   topout={to} stall={sl}")
    print()
    check_l1a3_feasible()
    print("SCOPE (PREREG_L1 sec.5): these are SOLO pressure-rig numbers. There is no race and")
    print("no opponent here. They license tempo claims ONLY -- never a win rate against")
    print("dr. lulu, and never a claim that the champion 'would' win a race.")

if __name__ == "__main__":
    main()
