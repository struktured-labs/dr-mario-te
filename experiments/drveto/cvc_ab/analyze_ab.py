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
    print("  block %-2s %-8s samples=%-4d span=%5.1f min  transitions=%d %s"
          % (b, arm, len(series), (series[-1][0] - series[0][0]) / 60, len(recs),
             rounds.tally(recs) or ""))
    for rr in recs:
        print("      round end t=%.0f  dur=%5.1fs  last %s/%s  ->  %s"
              % (rr["end"], rr["dur_s"], rr["last_p1"], rr["last_p2"], rr["outcome"]))

print("\nreload events per arm (reported secondary -- unequal freeze rates make the")
print("denominators non-comparable, and that asymmetry is itself a finding):")
for arm in sorted(per_arm):
    n = sum(1 for e in RELOADS
            for (a, b), ser in blocks.items() if a == arm and ser[0][0] <= e <= ser[-1][0])
    print("   %-9s reloads=%d  rounds excluded=%d" % (arm, n, excl_by_arm.get(arm, 0)))
print("\n%-9s %-8s %-8s %-9s %s" % ("arm", "hours", "rounds", "rounds/h", "tally"))
for arm, d in sorted(per_arm.items()):
    h = d["secs"] / 3600
    print("%-9s %-8.2f %-8d %-9.1f %s"
          % (arm, h, len(d["rounds"]), len(d["rounds"]) / h if h else 0, rounds.tally(d["rounds"])))

# the endpoint: champion-seat (P2) topouts per round
print("\n-- ENDPOINT: P2 (champion) topouts per completed round --")
k = {}
for arm, d in per_arm.items():
    n = len(d["rounds"])
    x = sum(1 for r in d["rounds"] if r["outcome"] == "TOPOUT_P2")
    amb = sum(1 for r in d["rounds"] if r["outcome"] == "AMBIGUOUS")
    k[arm] = (x, n)
    print("  %-9s %3d / %3d = %.3f   (ambiguous %d, excluded)" % (arm, x, n, x / n if n else 0, amb))

# ---- R49 GATE: refuse the contrast below the pre-registered floor ----------------
# ⚠ This script previously PRINTED the two arms' rates side by side the moment both
# existed, which is exactly the partial comparison PREREG_READ.md forbids. The gate is
# the fix; the discipline cannot live only in the analyst's head.
FLOOR = 120
_short = {a: len(d["rounds"]) for a, d in per_arm.items() if len(d["rounds"]) < FLOOR}
if _short:
    print("\n-- CONTRAST WITHHELD (R49 / PREREG_READ.md) ------------------------------")
    for a, n in sorted(_short.items()):
        print("   %-9s %d rounds -- below the %d-round floor for a primary verdict" % (a, n, FLOOR))
    print("   Per-arm descriptive counts above are labelled by arm. No comparison, no")
    print("   direction, and no GO/NO-GO until every arm clears the floor.")
elif len(k) == 2 and all(n for _, n in k.values()):
    (x1, n1), (x2, n2) = k["noproph"], k["proph"]
    p1, p2 = x1 / n1, x2 / n2
    p = (x1 + x2) / (n1 + n2)
    se = math.sqrt(p * (1 - p) * (1 / n1 + 1 / n2))
    if se:
        z = (p1 - p2) / se
        print("\n  noproph %.3f  vs  proph %.3f   d=%+.3f  z=%.2f  (R47 bar: |d| >= 2.8*SE = %.3f)"
              % (p1, p2, p2 - p1, z, 2.8 * se))
        print("  VERDICT: %s" % ("SIGNAL" if abs(z) >= 2.8 else
                                 "UNDERPOWERED / no effect at this N -- do not read a direction"))
