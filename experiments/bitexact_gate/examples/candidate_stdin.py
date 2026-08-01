#!/usr/bin/env python3
"""Reference implementation of the SUBPROCESS protocol (what a Rust candidate
speaks).  Per line: 12 weights (bias maxh holes toprisk spawn setup matched
buried rdyext vrdy poll cross), 3 flags (color_aware nearest2 matched), then
128 hex NES cells.  Respond with one signed decimal score per line."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from common import make_w, make_fl, LEAF_W_NAMES
import pyleaf

out = []
for line in sys.stdin:
    toks = line.split()
    if not toks:
        continue
    w = make_w(**dict(zip(LEAF_W_NAMES, [int(x) for x in toks[:12]])))
    fl = make_fl(*[int(x) for x in toks[12:15]])
    board = [int(x, 16) for x in toks[15:143]]
    out.append(str(pyleaf.py_eval(board, w, fl)))
sys.stdout.write("\n".join(out) + "\n")
