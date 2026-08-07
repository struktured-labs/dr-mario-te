#!/usr/bin/env python3
"""PRICE THE m3 BLUNDERS IN PILLS OF SURVIVAL MARGIN.

For each of the six m3 commits we have the board, the capsule, the placement the
EVAL wanted, and the placement the TAPE actually made. m3_counterfactual.py
showed the eval's line survives the known stream and the tape's died. This asks
HOW MUCH the tape's placement cost, in the only unit that matters at the top of
the board: how many pills an omniscient enemy would then need to finish it.

  margin(position) = shortest adversarial pill sequence that tops the champion
                     out from here (IDA*, exact when it terminates)

A blunder that drops the margin from 6 to 2 has handed the game away four pills
early. A blunder that leaves the margin unchanged was cosmetic.

CAVEAT, stated up front: these are VS boards and the real m3 also had garbage
arriving. A pure pill-stream adversary is a LOWER bound on the pressure the
champion was actually under, so the margins here are optimistic -- the real
position was at least this dangerous, probably more.
"""
from __future__ import annotations
import sys, os, json
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import numpy as np                      # noqa: E402
import champion as CH                   # noqa: E402
import poker as PK                      # noqa: E402
import margin as MG                     # noqa: E402
from m3_counterfactual import (RECON, parse_board, pill_of, identify_action,  # noqa: E402
                               act_str)

MAX_DEPTH = 6
MAX_ORACLE = 14_000


def main():
    CH.init_champion()
    d = json.load(open(RECON))
    commits = [e for e in d["boards"] if e.get("pill")]
    boards, pills = [], []
    for e in commits:
        col, vir = parse_board(e)
        boards.append(CH.board_from_flat(col, vir))
        pills.append(pill_of(e["pill"]))
    stream = list(pills) + [pill_of(commits[-1]["next"])]

    specs = []
    for i in range(len(commits)):
        b, (ca, cb) = boards[i], pills[i]
        na, nb = stream[i + 1]
        col, vir = CH.board_to_flat(b)
        want = CH.champion_move(col, vir, ca, cb, na, nb)
        tape = None
        if i < len(commits) - 1:
            col_after, _ = parse_board(commits[i + 1])
            hits = identify_action(b, pills[i], col_after)
            tape = hits[0] if hits else None
        for label, act in (("eval", want), ("tape", tape)):
            if act is None:
                continue
            nb_ = b.clone()
            ok, _c, _v, _ch = CH.apply_action(nb_, act, ca, cb)
            if not ok:
                continue
            if nb_.spawn_blocked():
                specs.append({"tag": f"c{i+1}-{label}-DEAD", "col": [0] * 128,
                              "vir": [0] * 128, "link": None, "cur": list(stream[i + 1]),
                              "_precomputed": 0, "_act": act})
                continue
            specs.append({"tag": f"c{i+1}-{label}",
                          "col": nb_.color.reshape(-1).astype(int).tolist(),
                          "vir": nb_.is_virus.reshape(-1).astype(int).tolist(),
                          "link": nb_.link.reshape(-1).astype(int).tolist(),
                          "cur": list(stream[i + 1]),
                          "max_depth": MAX_DEPTH, "max_oracle": MAX_ORACLE,
                          "_act": act})

    live = [s for s in specs if "_precomputed" not in s]
    print(f"=== m3 MARGIN: {len(live)} post-placement positions "
          f"(eval vs tape at each commit) ===", flush=True)
    for s in live:
        print(f"    {s['tag']:14s} action={act_str(s['_act'])}")
    rows = MG.run_specs([{k: v for k, v in s.items() if not k.startswith("_")}
                         for s in live],
                        workers=6, out="results/m3_margin.json", label="(m3)")

    by = {r["tag"]: r for r in rows}
    print("\n=== BLUNDER PRICE (pills of survival margin) ===")
    print(f"{'commit':8s} {'eval K':>8s} {'tape K':>8s} {'cost':>8s}")
    for i in range(len(commits)):
        e = by.get(f"c{i+1}-eval")
        t = by.get(f"c{i+1}-tape")
        if not e or not t:
            print(f"c{i+1:<7d} {'-' if not e else e['K']!s:>8s} "
                  f"{'-' if not t else t['K']!s:>8s} {'(no tape)':>8s}")
            continue
        ek = e["K"] if e["K"] is not None else f">{e['searched_to']}"
        tk = t["K"] if t["K"] is not None else f">{t['searched_to']}"
        cost = (e["K"] - t["K"]) if (e["K"] is not None and t["K"] is not None) else "?"
        print(f"c{i+1:<7d} {ek!s:>8s} {tk!s:>8s} {cost!s:>8s}")
    print("\n(K = shortest adversarial kill from the resulting position; "
          "'>n' = proved no kill within n. cost = pills of margin the tape threw away.)")


if __name__ == "__main__":
    main()
