#!/usr/bin/env python3
"""Per-board decision diff across arms -- the cheap upper bound on any A/B effect.

A full-game A/B costs ~100 RTL decisions per game. This costs ONE per board, and answers
the question that bounds everything else: on identical boards, how often do the arms
choose differently at all? If the arms agree on 95% of boards, no amount of games will
find a large effect, and the games are then only measuring how the remaining 5% compound.

It also separates the two things the tier-3 arm changes, which a game-level A/B cannot:
  * how often each arm PUBLISHES a tuck descriptor ($5087 != 0xFF)
  * how often each arm's published PLACEMENT (best_col, best_orient) differs
On the deployed cart only the second can affect play at all, because the cart has no tuck
executor (see README).

Usage: decide_compare.py <hostdata.txt> --arms name=dir [name=dir ...] [--out x.json]
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from cosim import Cosim, read_hostdata  # noqa: E402

BUILD = os.environ.get("COSIM_FARM_BUILD", os.path.join(HERE, "build"))
FARM_BIN = os.path.join(BUILD, "obj_farm", "farm_vsim")


def run_arm(fw_dir, cases, label):
    out = []
    t0 = time.time()
    with Cosim(FARM_BIN, fw_dir) as cs:
        md5 = cs.fw_md5
        for i, c in enumerate(cases):
            out.append(cs.decide(c["board"], c["cA"], c["cB"], c["nA"], c["nB"]))
            print(f"  {label} {i+1}/{len(cases)}", flush=True)
    return out, md5, time.time() - t0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("hostdata")
    ap.add_argument("--arms", nargs="+", required=True, help="name=fw_dir")
    ap.add_argument("--out")
    a = ap.parse_args()

    cases = read_hostdata(a.hostdata)
    arms = {}
    order = []
    for spec in a.arms:
        name, d = spec.split("=", 1)
        order.append(name)
        rows, md5, el = run_arm(d, cases, name)
        arms[name] = {"rows": rows, "fw_md5": md5, "secs": el,
                      "secs_per_decision": el / len(cases)}
        n_t = sum(1 for r in rows if r["tcol"] != 0xFF)
        print(f"{name}: fw={md5} {el:.0f}s ({el/len(cases):.1f}s/dec)  "
              f"tuck descriptor published {n_t}/{len(cases)} ({n_t/len(cases):.0%})",
              flush=True)

    base = order[0]
    cmp_out = {}
    print(f"\n=== placement diffs vs {base} (n={len(cases)} boards) ===")
    for name in order[1:]:
        A, B = arms[base]["rows"], arms[name]["rows"]
        d_place = [i for i in range(len(cases))
                   if (A[i]["col"], A[i]["o4"]) != (B[i]["col"], B[i]["o4"])]
        d_col = [i for i in range(len(cases)) if A[i]["col"] != B[i]["col"]]
        d_o4 = [i for i in range(len(cases)) if A[i]["o4"] != B[i]["o4"]]
        med_a = sorted(r["clocks"] for r in A)[len(A) // 2]
        med_b = sorted(r["clocks"] for r in B)[len(B) // 2]
        cmp_out[name] = {
            "n": len(cases),
            "n_placement_differs": len(d_place),
            "frac_placement_differs": len(d_place) / len(cases),
            "n_col_differs": len(d_col), "n_orient_differs": len(d_o4),
            "boards_differing": d_place,
            "median_clocks_control": med_a, "median_clocks_arm": med_b,
            "search_cost_ratio": med_b / med_a if med_a else None,
        }
        print(f"{name:<14} placement differs on {len(d_place)}/{len(cases)} "
              f"({len(d_place)/len(cases):5.1%})   col {len(d_col)}  orient {len(d_o4)}   "
              f"median search cost {med_b/med_a:.2f}x control")

    res = {"hostdata": a.hostdata, "n_boards": len(cases), "base": base,
           "arms": {k: {kk: vv for kk, vv in v.items() if kk != "rows"}
                    for k, v in arms.items()},
           "tuck_published": {k: sum(1 for r in v["rows"] if r["tcol"] != 0xFF)
                              for k, v in arms.items()},
           "comparisons": cmp_out,
           "rows": {k: v["rows"] for k, v in arms.items()}}
    if a.out:
        os.makedirs(os.path.dirname(a.out), exist_ok=True)
        json.dump(res, open(a.out, "w"), indent=1)
        print(f"\nwrote {a.out}")


if __name__ == "__main__":
    main()
