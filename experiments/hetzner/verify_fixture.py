#!/usr/bin/env python3
"""verify_fixture.py -- prove the census's stored failure boards are usable.

The census claims its fatal boards are "adversarial fixture material". That
claim is worth nothing until a stored board round-trips back into a real
FaithfulBoard and reproduces the property it was captured for. This checks:

  1. the 128-cell col/vir/lnk planes reload into a board of the right shape;
  2. a board captured at a TOPOUT is genuinely spawn_blocked() -- i.e. the
     taxonomy label matches the artifact, not just the harness's bookkeeping;
  3. the stored trace replays from a fresh env and lands on the same outcome,
     which is the stronger property (it means the fixture is reconstructible
     even for STALL rows, whose board predates the harness's stall-capture fix).

Usage: verify_fixture.py results/upper/census.jsonl
"""
from __future__ import annotations

import sys
import json
import argparse

QA = "/home/struktured/projects/dr-mario-qa-wt/experiments"
sys.path.insert(0, QA + "/adversary")
import adversary_harness as AH  # noqa: E402


def check_board(row):
    L = AH._lazy()
    FaithfulDrMarioEnv = L["FaithfulDrMarioEnv"]
    b = row.get("board")
    if b is None:
        return "no board stored"
    env = FaithfulDrMarioEnv(level=AH.LEVEL, seed=row["seed"])
    env.reset()
    board = env.board
    n = board.rows * board.cols
    if not (len(b["col"]) == len(b["vir"]) == len(b["lnk"]) == n):
        return f"SHAPE MISMATCH: {len(b['col'])} vs board {n}"
    for i in range(n):
        r, c = divmod(i, board.cols)
        board.color[r, c] = b["col"][i]
        board.is_virus[r, c] = bool(b["vir"][i])
        board.link[r, c] = b["lnk"][i]
    blocked = bool(board.spawn_blocked())
    vc = int(board.virus_count())
    ok = blocked if row["result"] == "topout" else True
    return (f"reloaded OK  spawn_blocked={blocked}  virus_count={vc}  "
            f"(expected blocked={row['result'] == 'topout'}) "
            f"{'CONSISTENT' if ok else 'INCONSISTENT'}")


def check_replay(row):
    """Replay the stored trace from a fresh env; must reach the same outcome."""
    L = AH._lazy()
    FaithfulDrMarioEnv, NesPillSource = L["FaithfulDrMarioEnv"], L["NesPillSource"]
    tr = row.get("trace")
    if not tr:
        return "no trace stored"
    env = FaithfulDrMarioEnv(level=AH.LEVEL, seed=row["seed"], max_pills=300)
    env.reset()
    NesPillSource(seed=row["seed"]).attach(env)
    env.cur = env._rand_pill()
    env.nxt = env._rand_pill()
    for _, a in tr:
        _, _, term, trunc, info = env.step(int(a))
        if term or trunc:
            break
    vc = int(env.board.virus_count())
    match = (vc == row["viruses_left"] and env.pills_placed == row["pills"])
    return (f"replayed {len(tr)} moves -> pills={env.pills_placed} "
            f"virus_count={vc} (stored pills={row['pills']} vl={row['viruses_left']}) "
            f"{'MATCH' if match else 'MISMATCH'}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("path")
    a = ap.parse_args()

    rows = []
    for line in open(a.path):
        try:
            r = json.loads(line)
        except json.JSONDecodeError:
            continue
        if r["result"] != "clear":
            rows.append(r)

    print(f"{len(rows)} failure rows in {a.path}\n")
    for r in rows:
        print(f"seed {r['seed']}  {r['result']}  pills={r['pills']}  "
              f"vl={r['viruses_left']}")
        print(f"  board : {check_board(r)}")
        print(f"  replay: {check_replay(r)}")


if __name__ == "__main__":
    main()
