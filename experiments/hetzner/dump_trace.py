#!/usr/bin/env python3
"""dump_trace.py -- dump one seed's full move trace, twice, for divergence work.

Runs the same seed TWICE in one process so within-machine determinism is
checked at the same time as the cross-machine comparison. If a seed is
self-consistent on each node but differs between them, the divergence is in
the machine (instruction selection / FP), not in the harness.
"""
import sys
import json
import argparse

QA = "/home/struktured/projects/dr-mario-qa-wt/experiments"
sys.path.insert(0, QA + "/adversary")
import adversary_harness as AH  # noqa: E402

ap = argparse.ArgumentParser()
ap.add_argument("seed", type=int)
ap.add_argument("--out", required=True)
a = ap.parse_args()

r1 = AH.play_seed(a.seed)
r2 = AH.play_seed(a.seed)
t1 = [[int(i), int(x)] for i, x in r1["trace"]]
t2 = [[int(i), int(x)] for i, x in r2["trace"]]

print(f"seed {a.seed}: {r1['result']} pills={r1['pills']} vl={r1['viruses_left']}")
print(f"within-machine determinism: {'OK' if t1 == t2 else 'NONDETERMINISTIC'}")

with open(a.out, "w") as f:
    json.dump({"seed": a.seed, "result": r1["result"], "pills": r1["pills"],
               "viruses_left": r1["viruses_left"], "trace": t1,
               "self_consistent": t1 == t2}, f)
print(f"wrote {a.out} ({len(t1)} moves)")
