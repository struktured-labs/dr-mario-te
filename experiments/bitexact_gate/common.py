"""bitexact_gate common: board interchange, weight layout, corpus IO.

Canonical board interchange (everywhere in this gate): 128 NES-encoded bytes,
row-major, row 0 = top.  0xFF empty, 0xD0|c virus, 0x40|c pill, c in 0..2.
This is the exact encoding of leafeval_cases.txt / hostdata.txt, so every gate
artifact is directly replayable against the Verilator testbenches.

Weight-vector layout mirrors combo_term/fast_rtl_x.py (indices MUST stay in
sync -- the reference kernel is imported from there, not copied).
"""
from __future__ import annotations
import hashlib
import os
import sys

import numpy as np

COMBO_TERM = "/home/struktured/projects/dr_mario_rl/tmp/combo_term"
RTL_DEFAULT = "/home/struktured/projects/NES_MiSTer-winner/rtl/mappers/LeafEval.sv"
QA_COPRO = "/home/struktured/projects/dr-mario-qa-wt/fpga/copro"
HERE = os.path.dirname(os.path.abspath(__file__))

if COMBO_TERM not in sys.path:
    sys.path.insert(0, COMBO_TERM)

ROWS, COLS, NCELL = 16, 8, 128

# ---- weight layout (mirror of fast_rtl_x; only leaf-relevant slots used) ----
R_BIAS, R_MAXH, R_HOLES, R_TOPRISK, R_SPAWN = 0, 1, 2, 3, 4
R_SETUP, R_MATCHED, R_BURIED, R_RDYEXT, R_VRDY, R_POLL = 5, 6, 7, 8, 9, 10
R_WVIR, R_WCELLS, R_WINBONUS, R_CROSS, R_VBONUS = 11, 12, 13, 14, 15
NRW = 16
LEAF_W_IDX = [R_BIAS, R_MAXH, R_HOLES, R_TOPRISK, R_SPAWN, R_SETUP, R_MATCHED,
              R_BURIED, R_RDYEXT, R_VRDY, R_POLL, R_CROSS]  # the 12 leaf weights
LEAF_W_NAMES = ["bias", "maxh", "holes", "toprisk", "spawn", "setup", "matched",
                "buried", "rdyext", "vrdy", "poll", "cross"]
FL_COLOR_AWARE, FL_NEAREST2, FL_MATCHED = 0, 1, 2


def make_w(**kv):
    """Weight vector from term names (unlisted = 0)."""
    w = np.zeros(NRW, dtype=np.float64)
    for k, v in kv.items():
        w[LEAF_W_IDX[LEAF_W_NAMES.index(k)]] = float(v)
    return w


def make_fl(color_aware=1, nearest2=1, matched=1):
    return np.array([color_aware, nearest2, matched], dtype=np.int32)


# ---- NES board <-> kernel arrays -------------------------------------------
def nes_to_arrays(board):
    """128 NES bytes -> (col int8[128] 0=empty/1..3, vir int8[128] 0/1)."""
    col = np.zeros(NCELL, dtype=np.int8)
    vir = np.zeros(NCELL, dtype=np.int8)
    for i, b in enumerate(board):
        if b != 0xFF:
            col[i] = (b & 0x0F) + 1
            vir[i] = 1 if (b & 0xF0) == 0xD0 else 0
    return col, vir


def arrays_to_nes(col, vir):
    out = []
    for i in range(NCELL):
        if col[i] == 0:
            out.append(0xFF)
        else:
            out.append((0xD0 if vir[i] else 0x40) | (int(col[i]) - 1))
    return out


def board_hex(board):
    return " ".join("%02x" % b for b in board)


def parse_board_hex(line):
    b = [int(t, 16) for t in line.split()]
    assert len(b) == NCELL, "board line must have 128 hex cells, got %d" % len(b)
    for x in b:
        assert x == 0xFF or (x & 0xF0) in (0xD0, 0x40) and (x & 0x0F) <= 2, \
            "bad NES cell 0x%02x" % x
    return b


def virus_count(board):
    return sum(1 for b in board if b != 0xFF and (b & 0xF0) == 0xD0)


# ---- corpus IO --------------------------------------------------------------
def write_corpus(path, boards, classes):
    """corpus.txt: n then one 128-hex line per board.  Sidecar .classes.txt has
    the class tag per line (kept separate so the file stays fscanf-compatible)."""
    assert len(boards) == len(classes)
    with open(path, "w") as f:
        f.write("%d\n" % len(boards))
        for b in boards:
            f.write(board_hex(b) + "\n")
    with open(path + ".classes", "w") as f:
        for c in classes:
            f.write(c + "\n")


def read_corpus(path):
    with open(path) as f:
        toks = f.read().split()
    n = int(toks[0]); toks = toks[1:]
    boards = [[int(x, 16) for x in toks[k * NCELL:(k + 1) * NCELL]] for k in range(n)]
    cpath = path + ".classes"
    if os.path.exists(cpath):
        classes = [l.strip() for l in open(cpath)]
    else:
        classes = ["?"] * n
    return boards, classes


def file_md5(path):
    return hashlib.md5(open(path, "rb").read()).hexdigest()
