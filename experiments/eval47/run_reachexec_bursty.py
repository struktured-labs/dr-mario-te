#!/usr/bin/env python3
"""ITERATION 3 reconciliation-arm bursty gate (task #60, team-lead follow-on):
reachexec vs BOTH base32 and reachfull2, same 120 paired seeds, all three
arms run once so the McNemar/moved-seed comparisons are truly paired across
all three, not re-derived from separate runs with different RNG draws.

reach_root_ab.py's own CLI always uses base32 as the control and doesn't
support an arm-vs-arm comparison (only ctrl-vs-arm) -- this script reuses its
run_arm()/compare() functions directly (no CLI changes, no risk to the
already-validated `main()` path) to get both required comparisons from ONE
set of runs.
"""
from __future__ import annotations
import sys, os, json

HERE = os.path.dirname(os.path.abspath(__file__))
for _p in (HERE,):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import reach_root_ab as AB
import bursty_model

SEEDS = 120
WORKERS = 6
LEVEL = 11

bursty_model_obj = bursty_model.fit_struktured_20260804()
bursty_model_obj.meta = {k: v for k, v in bursty_model_obj.meta.items() if k != "raw_events"}
print(f"=== bursty-v1 fit: n_matches={bursty_model_obj.n_matches} "
      f"n_volleys={bursty_model_obj.n_volleys} n_clears={bursty_model_obj.n_clears} ===", flush=True)

print(f"=== reachexec reconciliation gate, L{LEVEL}, n={SEEDS}, pressure=bursty ===", flush=True)
base32 = AB.run_arm(LEVEL, SEEDS, WORKERS, "base32", "bursty", bursty_model_obj)
reachfull2 = AB.run_arm(LEVEL, SEEDS, WORKERS, "reachfull2", "bursty", bursty_model_obj)
reachexec = AB.run_arm(LEVEL, SEEDS, WORKERS, "reachexec", "bursty", bursty_model_obj)

print()
s1 = AB.compare(base32, reachfull2, "reachfull2 vs base32   ")
s2 = AB.compare(base32, reachexec, " reachexec vs base32   ")
s3 = AB.compare(reachfull2, reachexec, " reachexec vs reachfull2")

out = {"reachfull2_vs_base32": s1, "reachexec_vs_base32": s2,
       "reachexec_vs_reachfull2": s3,
       "raw": {"base32": [base32[s] for s in sorted(base32)],
               "reachfull2": [reachfull2[s] for s in sorted(reachfull2)],
               "reachexec": [reachexec[s] for s in sorted(reachexec)]}}
out_path = f"{HERE}/results/reachexec_bursty_n120.json"
with open(out_path, "w") as fh:
    json.dump(out, fh)
print(f"\nwrote {out_path}")
print("\nDONE")
