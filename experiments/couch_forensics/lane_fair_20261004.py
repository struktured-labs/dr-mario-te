"""Owner-seat spawn-lane provenance at death, 2026-10-04 (M1-M4): which cells filled columns 3-4 (the spawn lane)
-- the owner's own pill halves (P<k>), the AI's garbage (G<k>), viruses (V) -- using stall_fair_20261004's tag tracker
(tags follow the faithful resolve; reconciled to each next observed board column by column; extra cells on a column
top = garbage). Reported at the owner's last placement before game over.
Usage: python lane_fair_20261004.py   -> lane_fair_20261004.json"""
import json, os
from collections import Counter
import numpy as np
import fair_20261004 as FA
import stall_fair_20261004 as SF
A = SF.A

out = {}
for g, build, m, gi, rec, log in FA.GAMES:
    t_round, t_end, final = FA.window(g)
    R = FA.load_raw(g, "p1", t_round, t_end)
    S0 = FA.grid(R[0]["S"]["color"]); V0 = FA.grid(R[0]["S"]["virus"])
    T = np.full((16, 8), "", dtype=object); T[(S0 > 0) & (V0 > 0)] = "V"; T[(S0 > 0) & (V0 == 0)] = "?"
    for n, r in enumerate(R):
        S = r["S"]; o, orow, ocol, ocl = r["landing"]
        bp = A.board_from_strings(S["color"], S["virus"], S["link"]); Tp = T.copy(); tag = "P%d" % n
        if o == "H":
            bp.color[orow, ocol], bp.color[orow, ocol + 1] = ocl; bp.link[orow, ocol], bp.link[orow, ocol + 1] = 4, 3
            Tp[orow, ocol] = Tp[orow, ocol + 1] = tag
        else:
            bp.color[orow, ocol], bp.color[orow + 1, ocol] = ocl; bp.link[orow, ocol], bp.link[orow + 1, ocol] = 2, 1
            Tp[orow, ocol] = Tp[orow + 1, ocol] = tag
        bp, Tp = SF.resolve_tagged(bp, Tp)
        if n + 1 < len(R):
            T = SF.reconcile(bp.color, Tp, FA.grid(R[n + 1]["S"]["color"]), "G%d" % n)
        else:
            Tlast, Plast = Tp, bp.color
    # final board 3 frames before game over: cells beyond the last placement's resolved board = garbage after it
    F = FA.grid(final["p1"]["color"])
    Tf = SF.reconcile(Plast, Tlast, F, "Gend")
    lane = {}
    for c in (3, 4):
        V = FA.grid(final["p1"]["virus"])
        cells = [(r, int(F[r, c]), str(Tf[r, c])) for r in range(16) if F[r, c] > 0]
        top_v = next((r for r in range(16) if V[r, c]), 16)
        above = [x for x in cells if x[0] < top_v]
        lane[c] = {"height": 16 - (cells[0][0] if cells else 16), "cells_above_top_virus": len(above),
                   "by_provenance": dict(Counter(x[2][0] if x[2] else "?" for x in above)),
                   "top_cells": [(x[0], x[2]) for x in cells[:4]]}
    out[g] = {"build": build, "log": log, "lane": lane}
    print(g, build, json.dumps({c: {k: v for k, v in d.items()} for c, d in lane.items()}))
json.dump(out, open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "lane_fair_20261004.json"), "w"), indent=1)
