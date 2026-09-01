"""Analyse the DRPROPH CvC A/B: round records per arm, tally, and a rate test."""
import csv, math, os, sys
import rounds

BASE = os.path.dirname(os.path.abspath(__file__))
rows = list(csv.DictReader(open(os.path.join(BASE, "ab_samples.csv"))))
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

per_arm = {}
for (arm, b), series in sorted(blocks.items(), key=lambda kv: (kv[0][1], kv[0][0])):
    recs = rounds.transitions(series)
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

if len(k) == 2 and all(n for _, n in k.values()):
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
