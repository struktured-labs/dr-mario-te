#!/usr/bin/env python3
"""Added DONE latency of tuck_scan, from paired co-sim runs (same boards, same RTL,
only the firmware differs: c87e60a1 baseline vs 751b6ce9 tuck)."""
import csv, os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
SP = os.path.join(HERE, "results")
tag = sys.argv[1] if len(sys.argv) > 1 else "real"
T = list(csv.DictReader(open("%s/out_tuck_%s.csv" % (SP, tag))))
B = list(csv.DictReader(open("%s/out_base_%s.csv" % (SP, tag))))
n = min(len(T), len(B))
T, B = T[:n], B[:n]

CLK = 85.9e6
FRAME = CLK / 60.0            # master clocks per NES frame at 85.9 MHz

d = []
same = 0
for t, b in zip(T, B):
    if t["best_col"] == b["best_col"] and t["best_orient"] == b["best_orient"]:
        same += 1
    d.append(int(t["clocks"]) - int(b["clocks"]))
d.sort()
mean = sum(d) / len(d)
print("paired boards            : %d" % n)
print("search answer unchanged  : %d / %d (the tuck must not perturb the search)" % (same, n))
print("baseline DONE            : min %d  median %d  max %d clocks  (max %.1f frames)"
      % (min(int(x["clocks"]) for x in B), sorted(int(x["clocks"]) for x in B)[n // 2],
         max(int(x["clocks"]) for x in B), max(int(x["clocks"]) for x in B) / FRAME))
print()
print("ADDED clocks by tuck_scan: min %d  median %d  mean %.0f  max %d" % (d[0], d[n // 2], mean, d[-1]))
print("  max as time            : %.3f ms @85.9MHz  =  %.4f frames" % (d[-1] / CLK * 1e3, d[-1] / FRAME))
print("  max at the /2 clock    : %.3f ms @42.95MHz =  %.4f frames" % (d[-1] / (CLK / 2) * 1e3, d[-1] / (FRAME / 2)))
print("  max as %% of baseline DONE: %.3f%%" % (100.0 * d[-1] / max(1, sorted(int(x["clocks"]) for x in B)[n // 2])))
