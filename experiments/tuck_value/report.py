#!/usr/bin/env python3
"""Turn the raw run JSONs into the tables TUCK_VALUE_INDEPENDENT.md quotes.

Every rate is printed with its own n. Paired deltas get a bootstrap CI over
seed-level differences; rate comparisons get McNemar. Nothing here recomputes
a game -- it only aggregates rows the runners already wrote, so the report
cannot drift from the runs it cites.

Usage: report.py [--results results]
"""
from __future__ import annotations

import argparse
import glob
import json
import os
import statistics as st
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
EXPERIMENTS = os.path.dirname(HERE)
EVAL47 = os.path.join(EXPERIMENTS, "eval47")
for _p in (HERE, EXPERIMENTS, EVAL47):
    if _p not in sys.path:
        sys.path.insert(0, _p)

ARM_ORDER = ("v1_drop", "t3_drop", "v1_tuck", "t3_tuck")
ARM_NAME = {"v1_drop": "A  v1 x drop  (SHIPPED)", "t3_drop": "B  t3 x drop",
            "v1_tuck": "C  v1 x tuck", "t3_tuck": "D  t3 x tuck"}


def boot_ci(xs, n=20000, seed=12345):
    import random
    if not xs:
        return (float("nan"), float("nan"))
    rng = random.Random(seed)
    k = len(xs)
    reps = sorted(sum(xs[rng.randrange(k)] for _ in range(k)) / k for _ in range(n))
    return reps[int(0.025 * n)], reps[int(0.975 * n)]


def mcnemar_exact(b, c):
    """Two-sided exact binomial on the discordant pairs."""
    from math import comb
    n = b + c
    if n == 0:
        return 1.0
    k = min(b, c)
    p = sum(comb(n, i) for i in range(k + 1)) / (2 ** n) * 2
    return min(1.0, p)


def load(path):
    with open(path) as fh:
        d = json.load(fh)
    return d["config"], {k: {r["seed"]: r for r in v} for k, v in d["rows"].items()}


def arm_table(rows, title):
    print(f"\n### {title}")
    print(f"{'arm':<26} {'n':>4} {'clear':>7} {'bad ends':>10} {'dies-ahead':>12} "
          f"{'pills(mean)':>12} {'fires/g':>8} {'deeper/g':>9}")
    for arm in ARM_ORDER:
        if arm not in rows:
            continue
        r = list(rows[arm].values())
        n = len(r)
        print(f"{ARM_NAME[arm]:<26} {n:>4} "
              f"{sum(x['won'] for x in r) / n:>6.1%} "
              f"{sum(x['topout'] + x['stall'] for x in r):>5}/{n:<4} "
              f"{sum(x['dies_ahead'] for x in r):>6}/{n:<5} "
              f"{st.mean(x['pills'] for x in r):>12.1f} "
              f"{sum(x['fired_tuck'] for x in r) / n:>8.2f} "
              f"{sum(x['n_deeper'] for x in r) / n:>9.2f}")


def delta(rows, ctrl, on, label, fired_only=False):
    """`fired_only` restricts to seeds where the treatment arm's executor fired
    at least once.

    This is a legitimate subgroup, not a post-treatment filter: the two arms
    are bit-identical up to the FIRST fire, so whether a first fire happens at
    all is decided by the shared prefix both arms play. It is still a
    conditional estimate and is reported alongside the all-seeds one, never
    instead of it -- an executor that fires in a fifth of games dilutes an
    all-seeds average by 5x, and both facts matter to a ship decision."""
    if ctrl not in rows or on not in rows:
        return None
    A, B = rows[ctrl], rows[on]
    ss = sorted(set(A) & set(B))
    if fired_only:
        ss = [s for s in ss if B[s]["fired_tuck"] > 0]
        if not ss:
            return None
    n = len(ss)
    both = [s for s in ss if A[s]["won"] and B[s]["won"]]
    dp = [B[s]["pills"] - A[s]["pills"] for s in both]
    plo, phi = boot_ci(dp)
    # bad ends = topout or stall
    ba = [A[s]["topout"] + A[s]["stall"] for s in ss]
    bb = [B[s]["topout"] + B[s]["stall"] for s in ss]
    resc = sum(1 for i, s in enumerate(ss) if ba[i] and not bb[i])
    harm = sum(1 for i, s in enumerate(ss) if bb[i] and not ba[i])
    p = mcnemar_exact(resc, harm)
    db = [bb[i] - ba[i] for i in range(n)]
    blo, bhi = boot_ci(db)
    dda = [B[s]["dies_ahead"] - A[s]["dies_ahead"] for s in ss]
    dlo, dhi = boot_ci(dda)
    verdict = "REAL" if (blo > 0 or bhi < 0) else "WASH"
    print(f"\n{label}   (n={n} paired seeds)")
    print(f"    bad-end rate      {sum(ba) / n:6.1%} -> {sum(bb) / n:6.1%}   "
          f"delta {st.mean(db):+.4f} [{blo:+.4f},{bhi:+.4f}]  {verdict}")
    print(f"    McNemar           rescued={resc} harmed={harm} p={p:.4g}  "
          f"(moved {resc + harm}/{n} = {(resc + harm) / n:.1%} of seeds)")
    print(f"    dies-ahead rate   {sum(A[s]['dies_ahead'] for s in ss) / n:6.1%} -> "
          f"{sum(B[s]['dies_ahead'] for s in ss) / n:6.1%}   "
          f"delta {st.mean(dda):+.4f} [{dlo:+.4f},{dhi:+.4f}]")
    print(f"    pills-to-clear    {st.mean(dp) if dp else float('nan'):+.2f} "
          f"[{plo:+.2f},{phi:+.2f}]  (both cleared, n={len(both)})")
    return {"label": label, "n": n, "bad_end_delta": st.mean(db),
            "bad_end_ci": [blo, bhi], "verdict": verdict,
            "mcnemar_rescued": resc, "mcnemar_harmed": harm, "mcnemar_p": p,
            "dies_ahead_delta": st.mean(dda), "dies_ahead_ci": [dlo, dhi],
            "pills_delta": st.mean(dp) if dp else None, "pills_ci": [plo, phi],
            "n_both_cleared": len(both)}


def failure_decomposition(rows, pairs):
    """Split every bad-end comparison into STALLS and TOPOUTS.

    The two failure modes have different causes and a combined bad-end rate
    hides which one moved. A stall is the 300-pill cap with viruses still
    buried -- material the AI could not reach. A topout is the board reaching
    the spawn row. An arm that merely finishes SOONER absorbs less garbage and
    should relieve topouts; an arm that reaches under overhangs should relieve
    stalls. Which one moves therefore distinguishes a tempo artifact from the
    thing a tuck is actually for, and that distinction is not visible in the
    headline rate."""
    print("\n### Failure-mode decomposition (stalls vs topouts)")
    for ctrl, on, label in pairs:
        if ctrl not in rows or on not in rows:
            continue
        A, B = rows[ctrl], rows[on]
        ss = sorted(set(A) & set(B))
        for field in ("stall", "topout"):
            b = sum(1 for s in ss if A[s][field] and not B[s][field])
            c = sum(1 for s in ss if B[s][field] and not A[s][field])
            p = mcnemar_exact(b, c)
            print(f"  {label:<22} {field:<7} {sum(A[s][field] for s in ss):>3} -> "
                  f"{sum(B[s][field] for s in ss):>3}   rescued={b:>3} harmed={c:>3}  "
                  f"p={p:.4g}  {'REAL' if p < 0.05 else 'wash'}  (n={len(ss)})")


def executor_audit(rows):
    """The statistic directly comparable to the co-sim farm's
    descriptor_audit.py table -- measured here ON POLICY over whole games
    rather than over a fixed 50-board corpus, so the denominators differ in
    kind and only the RATES should be compared."""
    print("\n### Executor-action audit (on-policy, whole games)")
    print(f"{'arm':<26} {'published':>10} {'coherent':>18} {'lands deeper':>18}")
    for arm in ("v1_tuck", "t3_tuck"):
        if arm not in rows:
            continue
        r = list(rows[arm].values())
        pub = sum(x["n_published"] for x in r)
        coh = sum(x["n_coherent"] for x in r)
        deep = sum(x["n_deeper"] for x in r)
        print(f"{ARM_NAME[arm]:<26} {pub:>10} "
              f"{coh:>8} ({coh / max(1, pub):>5.1%})  "
              f"{deep:>8} ({deep / max(1, pub):>5.1%})")


def divergence_report(path):
    with open(path) as fh:
        d = json.load(fh)
    rows = d["rows"]
    f = [r for r in rows if r.get("forked")]
    n = len(rows)
    print(f"\n### Divergence horizon ({os.path.basename(path)})")
    print(f"forked {len(f)}/{n} seeds ({len(f) / max(1, n):.1%})")
    if not f:
        return
    for br, label in (("T", "TUCK executed"), ("C", "control: 2nd-best base drop")):
        hs = [r[f"horizon_{br}"] for r in f]
        never = sum(1 for h in hs if h is None)
        fin = [h for h in hs if h is not None]
        chg = sum(r[f"outcome_changed_{br}"] for r in f)
        print(f"  {label:<30} never reconverges {never:>4}/{len(f)} "
              f"({never / len(f):>5.1%})   outcome changed {chg:>4}/{len(f)} "
              f"({chg / len(f):>5.1%})"
              + (f"   median reconv {st.median(fin):.0f} pills (n={len(fin)})"
                 if fin else ""))
    dn = [(0 if f_[f"horizon_T"] is not None else 1)
          - (0 if f_[f"horizon_C"] is not None else 1) for f_ in f]
    lo, hi = boot_ci(dn)
    print(f"  paired never-reconverge difference TUCK - control: "
          f"{st.mean(dn):+.3f} [{lo:+.3f},{hi:+.3f}] "
          f"{'REAL' if (lo > 0 or hi < 0) else 'WASH'}")
    do = [f_["outcome_changed_T"] - f_["outcome_changed_C"] for f_ in f]
    lo2, hi2 = boot_ci(do)
    print(f"  paired outcome-change difference   TUCK - control: "
          f"{st.mean(do):+.3f} [{lo2:+.3f},{hi2:+.3f}] "
          f"{'REAL' if (lo2 > 0 or hi2 < 0) else 'WASH'}")
    b = sum(1 for x in do if x > 0)
    c = sum(1 for x in do if x < 0)
    print(f"  McNemar on outcome change: tuck-only={b} control-only={c} "
          f"p={mcnemar_exact(b, c):.4g}  (moved {b + c}/{len(f)})")
    washout_curve(f)


def washout_curve(forked, buckets=((0, 2), (3, 5), (6, 10), (11, 20), (21, 60))):
    """Does the tuck's advantage decay?

    Each fork's `gap_T` / `gap_C` trace records, per pill since divergence,
    that branch's virus count and max column height MINUS the reference's. A
    maneuver whose benefit washes out shows a gap that shrinks toward zero; one
    that compounds shows a gap that grows. Reported for the tuck AND the
    matched control, because a gap that persists equally in both is a property
    of the game's chaos, not of tucks."""
    print(f"  washout: mean signed gap vs the reference, by pills since divergence")
    print(f"    {'pills':>8}  {'virus gap T':>12} {'virus gap C':>12}  "
          f"{'height gap T':>13} {'height gap C':>13}  {'n obs':>7}")
    for lo, hi in buckets:
        vt, vc, ht, hc = [], [], [], []
        for r in forked:
            for (i, dv, dh) in r.get("gap_T", []):
                if lo <= i <= hi:
                    vt.append(dv); ht.append(dh)
            for (i, dv, dh) in r.get("gap_C", []):
                if lo <= i <= hi:
                    vc.append(dv); hc.append(dh)
        if not vt and not vc:
            continue
        print(f"    {lo:>3}-{hi:<4}  "
              f"{st.mean(vt) if vt else float('nan'):>12.2f} "
              f"{st.mean(vc) if vc else float('nan'):>12.2f}  "
              f"{st.mean(ht) if ht else float('nan'):>13.2f} "
              f"{st.mean(hc) if hc else float('nan'):>13.2f}  "
              f"{len(vt) + len(vc):>7}")


def control_analysis(results_dir, main_name, ctrl_name, label):
    """De-confound D - A with the A' control arm.

    Arms B and D take base candidates from the reachability-filtered pool
    while arm A is pure base32, so D - A mixes the tuck program with the
    reach32 fix. A' is the tier-3 decision path with theta so high no tuck can
    pass the gate -- reach-filtered base32 with no tucks. A' - A prices the
    filter alone; D - A' is the tuck program alone."""
    mp = os.path.join(results_dir, main_name)
    cp = os.path.join(results_dir, ctrl_name)
    if not (os.path.exists(mp) and os.path.exists(cp)):
        return
    main_d = json.load(open(mp))
    ctrl_d = json.load(open(cp))
    rows = {k: {x["seed"]: x for x in v} for k, v in main_d["rows"].items()}
    rows["ctrl"] = {x["seed"]: x for x in ctrl_d["rows"]["t3_drop"]}

    fires = sum(x["fired_tuck"] for x in rows["ctrl"].values())
    wins = sum(x["n_published"] for x in rows["ctrl"].values())
    print(f"\n### De-confounding control, {label}")
    print(f"control arm sanity: {fires} executor fires, {wins} tuck wins "
          f"(both must be 0 for A' to be 'no tucks')")
    if fires or wins:
        print("  CONTROL ARM IS NOT TUCK-FREE -- the theta gate did not hold. "
              "Do not read the numbers below.")
        return

    global ARM_ORDER
    saved = ARM_ORDER
    ARM_NAME["ctrl"] = "A' reach-base, no tucks"
    ARM_ORDER = ("v1_drop", "ctrl", "t3_tuck")
    arm_table(rows, f"A vs A' vs D ({label})")
    delta(rows, "v1_drop", "ctrl", "A' - A   the reachability filter ALONE")
    delta(rows, "ctrl", "t3_tuck", "D - A'   the tuck program ALONE (de-confounded)")
    failure_decomposition(rows, [("v1_drop", "ctrl", "A' - A filter"),
                                 ("ctrl", "t3_tuck", "D - A' tucks")])
    ARM_ORDER = saved


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--results", default=os.path.join(HERE, "results"))
    a = ap.parse_args()

    for path in sorted(glob.glob(os.path.join(a.results, "*.json"))):
        base = os.path.basename(path)
        if base.startswith("divergence"):
            divergence_report(path)
            continue
        with open(path) as fh:
            probe = json.load(fh)
        if "config" not in probe or "rows" not in probe:
            continue          # not a 2x2 run (e.g. tuck_profile), nothing to table
        cfg, rows = load(path)
        title = (f"{base}  L{cfg['level']} n={cfg['seeds']} "
                 f"pressure={cfg['pressure']} theta={cfg['theta']:g} "
                 f"on_blocked={cfg['on_blocked']}")
        arm_table(rows, title)
        executor_audit(rows)
        failure_decomposition(rows, [
            ("v1_drop", "t3_tuck", "D - A full program"),
            ("v1_drop", "v1_tuck", "C - A v1 executor"),
            ("v1_drop", "t3_drop", "B - A tier-3 today"),
            ("t3_drop", "t3_tuck", "D - B executor"),
        ])
        delta(rows, "t3_drop", "t3_tuck", "D - B   EXECUTOR VALUE, tier-3 firmware held fixed")
        delta(rows, "v1_drop", "v1_tuck", "C - A   executor value, v1 firmware held fixed")
        delta(rows, "v1_drop", "t3_drop", "B - A   ship tier-3 onto today's executor-less cart")
        delta(rows, "v1_drop", "t3_tuck", "D - A   the full program (cart rebuild + tier-3)")
        print("\n--- restricted to seeds where the executor actually fired ---")
        delta(rows, "t3_drop", "t3_tuck",
              "D - B   executor value, tier-3, FIRED-ONLY subgroup", fired_only=True)
        delta(rows, "v1_drop", "v1_tuck",
              "C - A   executor value, v1, FIRED-ONLY subgroup", fired_only=True)

    control_analysis(a.results, "bursty_theta150.json", "ctrl_bursty_notuck.json",
                     "bursty v1.1")
    control_analysis(a.results, "clean_theta150.json", "ctrl_clean_notuck.json",
                     "clean stream")
    print()


if __name__ == "__main__":
    main()
