"""Analyse the DRPROPH CvC A/B: round records per arm, tally, and a rate test."""
import csv, math, os, sys
import rounds, reloads

BASE = os.path.dirname(os.path.abspath(__file__))
# ---- SEGMENT POOLING RULE (written 2026-09-01T01:30Z, POST-LEAK per Amendment 4) ----
# The controller died on the 01:13Z freeze and was restarted, splitting the L20 series
# into ab_samples_L20_seg1.csv (pre-outage) and ab_samples_L20.csv (post). Rule, written
# rather than decided in the moment:
#   * segments are POOLED PER ARM -- they are the same cart, core and level, and the
#     outage is an interruption in observation, not a change in condition;
#   * a segment boundary is treated as a BLOCK boundary, so no round is ever inferred
#     across it. This is automatic: the restart begins a fresh (arm, block) key, and the
#     transition detector only ever joins samples within one key;
#   * the outage-spanning round is excluded by Amendment 3's reload rule, unchanged.
# Labelled post-leak because it was written after the R49 glance. It is an accounting
# rule about an interruption and does not touch the contrast.
SEGMENTS = ["ab_samples_L20_seg1.csv", "ab_samples_L20.csv"]
rows = []
for _i, _f in enumerate(SEGMENTS):
    _p = os.path.join(BASE, _f)
    if not os.path.exists(_p):
        continue
    for _r in csv.DictReader(open(_p)):
        _r["block"] = "s%d_%s" % (_i, _r["block"])      # segment-qualified block key
        rows.append(_r)
print("samples: %d" % len(rows))
if not rows:
    raise SystemExit(0)

# split into contiguous blocks -- a block boundary is an arm reload, so a round
# straddling it is not a real round and must not be counted.
blocks = {}
for r in rows:
    blocks.setdefault((r["arm"], r["block"]), []).append(
        (float(r["t_epoch"]),
         int(r["p1"]) if r["p1"] not in ("", "None") else None,
         int(r["p2"]) if r["p2"] not in ("", "None") else None,
         float(r["fill_p1"]), float(r["fill_p2"]),
         int(r["throat_p1"]), int(r["throat_p2"]),
         int(r["topcells_p1"]), int(r["topcells_p2"])))

RELOADS = reloads.reload_epochs()
print("reload events known: %d (excluded structurally from freeze_watch.log)\n" % len(RELOADS))
per_arm = {}
excl_by_arm = {}
for (arm, b), series in sorted(blocks.items(), key=lambda kv: (kv[0][1], kv[0][0])):
    recs_all = rounds.transitions(series)
    recs, dropped = reloads.drop_reload_rounds(recs_all, RELOADS)
    excl_by_arm[arm] = excl_by_arm.get(arm, 0) + len(dropped)
    for dd in dropped:
        print("      ⚠ EXCLUDED round end t=%.0f  dur=%5.1fs  %s" % (dd["end"], dd["dur_s"], dd["excluded"]))
    per_arm.setdefault(arm, {"rounds": [], "secs": 0.0, "samples": 0})
    per_arm[arm]["rounds"] += recs
    per_arm[arm]["secs"] += series[-1][0] - series[0][0]
    per_arm[arm]["samples"] += len(series)
    # ⚠ BLINDED: the per-block tally and the per-round outcome lines are per-ARM
    # outcome counts -- exactly the endpoint numerator. Below the floor they print
    # transitions only, with no outcome breakdown.
    if "--unblind" in sys.argv:
        print("  block %-6s %-8s samples=%-4d span=%5.1f min  transitions=%d %s"
              % (b, arm, len(series), (series[-1][0] - series[0][0]) / 60, len(recs),
                 rounds.tally(recs) or ""))
        for rr in recs:
            print("      round end t=%.0f  dur=%5.1fs  last %s/%s  ->  %s"
                  % (rr["end"], rr["dur_s"], rr["last_p1"], rr["last_p2"], rr["outcome"]))
    else:
        print("  block %-6s %-8s samples=%-4d span=%5.1f min  rounds=%d"
              % (b, arm, len(series), (series[-1][0] - series[0][0]) / 60, len(recs)))

print("\nreload events per arm (reported secondary -- unequal freeze rates make the")
print("denominators non-comparable, and that asymmetry is itself a finding):")
for arm in sorted(per_arm):
    n = sum(1 for e in RELOADS
            for (a, b), ser in blocks.items() if a == arm and ser[0][0] <= e <= ser[-1][0])
    print("   %-9s reloads=%d  rounds excluded=%d" % (arm, n, excl_by_arm.get(arm, 0)))
FLOOR = 120
UNBLIND = "--unblind" in sys.argv
_n_rounds = {a: len(d["rounds"]) for a, d in per_arm.items()}
_below = [a for a, n in _n_rounds.items() if n < FLOOR]

if UNBLIND:
    with open(os.path.join(BASE, "UNBLIND_LOG.txt"), "a") as _f:
        _f.write("%s  --unblind used; rounds=%s\n" % (
            __import__("datetime").datetime.now(__import__("datetime").timezone.utc)
            .strftime("%Y-%m-%dT%H:%M:%SZ"), _n_rounds))
    print("\n⚠ --unblind USED. Stamped into UNBLIND_LOG.txt.")

if _below and not UNBLIND:
    # ---- BLINDED REPORT -----------------------------------------------------------
    # ⚠ WHY THIS IS SHAPED LIKE THIS: the previous "gate" printed each arm's endpoint
    # rate on adjacent lines under a WITHHELD heading. Two per-arm rates side by side
    # IS the contrast -- subtraction is not a barrier -- and it leaked twice, the second
    # time to the team lead. A gate that withholds a LABEL while printing its INPUTS is
    # a label, not a gate.
    # TEST APPLIED TO EVERY LINE BELOW: could a reader who cannot see the withheld
    # quantity still COMPUTE it from what is printed? If yes, it does not get printed.
    # So: rounds per arm YES (a progress figure, needed to know when to stop);
    #     per-arm death COUNTS NO (rounds + count = the rate, one division away).
    # Outcome tallies are therefore POOLED ACROSS ARMS below the floor.
    print("\n== BLINDED PROGRESS REPORT (below the %d-round floor) ==" % FLOOR)
    print("%-9s %-8s %-8s %-10s %s" % ("arm", "hours", "rounds", "reloads", "rounds excluded"))
    for arm in sorted(per_arm):
        n = sum(1 for e in RELOADS
                for (a, b), ser in blocks.items() if a == arm and ser[0][0] <= e <= ser[-1][0])
        print("%-9s %-8.2f %-8d %-10d %d"
              % (arm, per_arm[arm]["secs"] / 3600, _n_rounds[arm], n, excl_by_arm.get(arm, 0)))
    # ⚠⚠ THE POOLED TALLY IS WITHHELD TOO. Pooled at ONE instant it is uninformative,
    # but the arms ALTERNATE IN BLOCKS and only one arm is live at a time, so
    #     tally(end of a block) - tally(start of that block) = that ARM's deaths, exactly.
    # Blinding is defeated by REPETITION, not by a missing suppression, and a status
    # command is precisely what gets run repeatedly.
    #
    # ADMISSION CRITERION for anything printed below the floor (the general rule this
    # taught): a quantity is safe only if ITS TIME-DERIVATIVE IS ALSO UNINFORMATIVE about
    # the endpoint -- not merely if it looks aggregated. Rounds, hours, reloads and
    # exclusions per arm all pass: their deltas are denominators and nuisance counts, with
    # no death information. Any outcome count, pooled or not, FAILS: its delta is a
    # single-arm numerator.
    #
    # STRENGTHENED AUDIT TEST: not "can a reader compute the withheld quantity from this
    # output?" but "can a reader compute it from this output TOGETHER WITH ANY OTHER
    # OUTPUT THIS TOOL HAS EVER PRODUCED, INCLUDING EARLIER RUNS OF ITSELF?" Blinding is
    # a property of the whole output history, not of a single invocation.
    print("\noutcome tallies (pooled OR per-arm) are WITHHELD below the floor: the arms")
    print("alternate in blocks, so differencing two readings of a POOLED tally recovers a")
    print("single arm's deaths exactly. Safe-to-print here = its DELTA is also uninformative.")
    print("\nprogress to floor: " + ", ".join(
        "%s %d/%d" % (a, _n_rounds[a], FLOOR) for a in sorted(_n_rounds)))
    print("No endpoint rate, no comparison, no direction, no GO/NO-GO until every arm")
    print("clears the floor. Re-run with --unblind only at the stop; its use is stamped.")
else:
    # ---- UNBLINDED: at the stop, or explicitly requested --------------------------
    print("\n%-9s %-8s %-8s %-9s %s" % ("arm", "hours", "rounds", "rounds/h", "tally"))
    for arm, d in sorted(per_arm.items()):
        h = d["secs"] / 3600
        print("%-9s %-8.2f %-8d %-9.1f %s"
              % (arm, h, len(d["rounds"]), len(d["rounds"]) / h if h else 0,
                 rounds.tally(d["rounds"])))
    print("\n-- ENDPOINT: P2 (champion) topouts per completed round --")
    k = {}
    for arm, d in per_arm.items():
        n = len(d["rounds"]); x = sum(1 for r in d["rounds"] if r["outcome"] == "TOPOUT_P2")
        amb = sum(1 for r in d["rounds"] if r["outcome"] == "AMBIGUOUS")
        k[arm] = (x, n)
        print("  %-9s %3d / %3d = %.3f   (ambiguous %d)" % (arm, x, n, x / n if n else 0, amb))
    if len(k) == 2 and all(n for _, n in k.values()):
        (x1, n1), (x2, n2) = k["noproph"], k["proph"]
        p1, p2 = x1 / n1, x2 / n2
        p = (x1 + x2) / (n1 + n2)
        se = math.sqrt(p * (1 - p) * (1 / n1 + 1 / n2))
        if se:
            z = (p1 - p2) / se
            print("\n  noproph %.3f vs proph %.3f  d=%+.3f  z=%.2f  (R47 bar 2.8*SE=%.3f)"
                  % (p1, p2, p2 - p1, z, 2.8 * se))
