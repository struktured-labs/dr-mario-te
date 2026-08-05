#!/usr/bin/env python3
"""Run the missing pressure arms (0:20, 2:20) reusing the verified saved control.

Control rows (wt=0 ws=0 under pressure, seeds 0..119) were verified byte-identical
across the two completed runs (wt1_ws20, wt4_ws20), so re-running control would be
pure waste: pressure_rig is deterministic per (seed, wt, ws).
"""
import json
import sys

sys.path.insert(0, "/home/struktured/projects/dr-mario-qa-wt/experiments/eval47")
import pressure_rig as pr  # noqa: E402

CTRL_SRC = "/tmp/claude-1000/pressure_1_20_wt1_ws20.json"
OUT = "/tmp/claude-1000/pressure_missing"

def main():
    ctrl_rows = json.load(open(CTRL_SRC))["ctrl"]
    ctrl = {r["seed"]: r for r in ctrl_rows}
    assert len(ctrl) == 120
    results = []
    for wt, ws in [(0, 20), (2, 20)]:
        arm = pr.run_arm(11, 120, 6, wt, ws)
        res = pr.compare(ctrl, arm, f"wt={wt} ws={ws}")
        results.append(res)
        with open(f"{OUT}_wt{wt}_ws{ws}.json", "w") as fh:
            json.dump({"summary": res,
                       "ctrl": [ctrl[s] for s in sorted(ctrl)],
                       "arm": [arm[s] for s in sorted(arm)]}, fh)
        print(f"ARM DONE wt={wt} ws={ws}: {json.dumps(res)}", flush=True)
    print("ALL DONE")

if __name__ == "__main__":
    main()
