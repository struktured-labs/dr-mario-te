#!/usr/bin/env python3
"""EXACT solo poker on the most dangerous real positions.

The taxonomy's solo negative ("no killing pill sequence found") rests on a BEAM,
and the VS run just demonstrated that a badly-built adversary understates the
champion's vulnerability by 5x. A beam negative is therefore only as good as the
beam. This replaces it with IDA*, which is exhaustive: when it reports no kill
at depth <= K, no pill sequence of length <= K exists, full stop -- no beam
width, no move ordering, no heuristic can change that.

It is affordable only on positions where the admissible bound h is already
small (the stack is up), which is exactly where the danger is. We run it on the
lowest spawn_top bins.
"""
from __future__ import annotations
import sys, os, json, argparse
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import margin as MG   # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--positions", type=str, default="results/positions.json")
    ap.add_argument("--max-spawn-top", type=int, default=3)
    ap.add_argument("--max-depth", type=int, default=5)
    ap.add_argument("--max-oracle", type=int, default=40_000)
    ap.add_argument("--workers", type=int, default=4)
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--out", type=str, default="results/exact_solo.json")
    a = ap.parse_args()

    pos = json.load(open(os.path.join(HERE, a.positions)))
    sel = [p for p in pos if p["spawn_top"] <= a.max_spawn_top]
    if a.limit:
        sel = sel[:a.limit]
    specs = [{"tag": f"L{p['level']}s{p['seed']}p{p['ply']}st{p['spawn_top']}",
              "col": p["col"], "vir": p["vir"], "link": p["link"],
              "cur": p["cur"], "max_depth": a.max_depth,
              "max_oracle": a.max_oracle} for p in sel]
    print(f"=== EXACT SOLO (IDA*): {len(specs)} positions with spawn_top<="
          f"{a.max_spawn_top}, exhaustive to depth {a.max_depth} ===", flush=True)
    rows = MG.run_specs(specs, workers=a.workers, out=a.out, label="(exact)")

    n = len(rows)
    killed = [r for r in rows if r["K"] is not None]
    budget = [r for r in rows if r["budget_hit"]]
    proved = [r for r in rows if r["K"] is None and not r["budget_hit"]]
    print(f"\n=== EXACT RESULT ===")
    print(f"  positions            : {n}")
    print(f"  KILLABLE within {a.max_depth}   : {len(killed)}")
    for r in killed:
        print(f"     {r['tag']}  K={r['K']}  E={r.get('E')}")
    print(f"  PROVED safe to {a.max_depth}    : {len(proved)}  "
          f"(exhaustive -- no pill sequence of length <= {a.max_depth} exists)")
    print(f"  budget-truncated     : {len(budget)}  (searched to "
          f"{[r['searched_to'] for r in budget]})")


if __name__ == "__main__":
    main()
