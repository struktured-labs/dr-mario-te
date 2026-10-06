#!/usr/bin/env python3
"""Does this tree's co-sim (sim_pubchain.cpp, fresh mode) reproduce the BANKED publish timelines the Mesen replays
use? Compares the pubtrace_g2.py conversion: valid publishes (frames to 0.01, col, orient, action), done_f, final, tuck.
  check_banked.py BANKED.jsonl FRESH.jsonl"""
import json
import sys

B = {json.loads(l)["p"]: json.loads(l) for l in open(sys.argv[1])}
F = {json.loads(l)["p"]: json.loads(l) for l in open(sys.argv[2])}
bad = []
for p, f in F.items():
    b = B[p]
    ok = ([list(x) for x in b["pubs"]] == f["pubs"] and abs(b["done_f"] - f["done_f"]) < 1e-9
          and list(b["final"]) == f["final"] and list(b.get("tuck") or [255, 255]) == f["tuck"])
    if not ok:
        bad.append(p)
print(f"{sys.argv[2].split('/')[-1]}: {len(F) - len(bad)}/{len(F)} reproduce the banked timeline" +
      (f"  MISMATCH {bad}" if bad else ""))
sys.exit(1 if bad or not F else 0)
