#!/usr/bin/env python3
"""Micro-test for pressure_rig.py: determinism + pairing of garbage injection.

Usage: micro_pressure_check.py WT:WS [seed]
Prints ONE json line: {"wt":..,"ws":..,"seed":..,"log":[[pills,cols,colors,placed],...],
                       "res": {...play() row...}}
Run in a FRESH process per invocation so process-level state can't fake determinism.
"""
import sys
import json
import random

import pressure_rig as PR

wt, ws = (int(x) for x in sys.argv[1].split(":"))
seed = int(sys.argv[2]) if len(sys.argv) > 2 else 0

LOG = []
_orig = PR._inject_garbage


def _recorder(board, s, pills_placed):
    # replicate the rig's rng draws exactly (sample, then one randint per column,
    # in cols order) BEFORE calling the original, which re-creates the same rng
    rng = random.Random(s * 1000 + pills_placed)
    cols = rng.sample(range(board.cols), PR.GARBAGE_K)
    colors = [rng.randint(1, 3) for _ in cols]
    placed = _orig(board, s, pills_placed)
    LOG.append([pills_placed, cols, colors, placed])
    return placed


PR._inject_garbage = _recorder
PR._init(11, wt, ws)
res = PR.play(seed)
print(json.dumps({"wt": wt, "ws": ws, "seed": seed, "log": LOG, "res": res}))
