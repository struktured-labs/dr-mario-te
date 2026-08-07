#!/usr/bin/env python3
"""Validate this rig's v1 descriptor model against REAL RTL OUTPUT.

exec_model.v1_descriptor delegates to fpga/copro/tuck_scan.py::ref_tuck_scan,
the file whose docstring says "the 6502 must agree with this cell-for-cell".
That is an assertion about the 6502, not a measurement. The co-sim farm has
since run the actual verilated s20b firmware (fw md5 e970e9ab, the shipped
champion) over a corpus of real L11 boards and recorded the (TUCK_COL,
TUCK_ROW) pair the firmware ACTUALLY published for each one. Comparing the
two closes the loop: if they agree board-for-board, this rig's v1 arm is
driving the same descriptors the silicon would.

Costs no RTL -- it reads artifacts the co-sim farm already wrote. Read-only
with respect to their directory and their /mnt/data outputs.

Usage: validate_v1_vs_rtl.py [--decide <json>] [--hostdata <txt>]
"""
from __future__ import annotations

import argparse
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

import exec_model as EM  # noqa: E402  (sets up the canonical-worktree sys.path)

DEFAULT_DECIDE = "/mnt/data/drmario_cosim/results/decide_compare_l11_20.json"
COLS = 8


def read_hostdata(path):
    """N boards of 128 hex bytes, each preceded by 6 scalar tokens (pill
    colours + metadata the decider is handed alongside the board)."""
    toks = open(path).read().split()
    i = 0
    n = int(toks[i]); i += 1
    out = []
    for _ in range(n):
        i += 6
        out.append([int(toks[i + k], 16) for k in range(128)])
        i += 128
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--decide", default=DEFAULT_DECIDE)
    ap.add_argument("--hostdata", default=None)
    a = ap.parse_args()

    if not os.path.exists(a.decide):
        print(f"decide_compare artifact not present yet: {a.decide}")
        return 2
    d = json.load(open(a.decide))
    hostdata = a.hostdata or d["hostdata"]
    if not os.path.exists(hostdata):
        print(f"hostdata not present: {hostdata}")
        return 2

    boards = read_hostdata(hostdata)
    rows = d["rows"]["s20b"]          # the SHIPPED v1 firmware arm
    fw = d["arms"]["s20b"]["fw_md5"]
    print(f"=== v1 descriptor: this rig vs real RTL ===")
    print(f"firmware   {fw}  (s20b, the shipped champion)")
    print(f"boards     {len(boards)} from {os.path.basename(hostdata)}")
    print(f"RTL rows   {len(rows)}\n")

    import tuck_scan
    agree = 0
    disagree = []
    both_none = 0
    for i, (board, row) in enumerate(zip(boards, rows)):
        mine = tuck_scan.ref_tuck_scan(board)
        theirs = (int(row["tcol"]), int(row["trow"]))
        if mine == theirs:
            agree += 1
            if theirs[0] == 0xFF:
                both_none += 1
        else:
            disagree.append((i, mine, theirs))

    n = len(boards)
    print(f"agreement  {agree}/{n} ({agree / n:.1%})   "
          f"of which {both_none} are 'no descriptor' on both sides")
    print(f"published  RTL {sum(1 for r in rows if int(r['tcol']) != 0xFF)}/{n}   "
          f"mine {sum(1 for b in boards if tuck_scan.ref_tuck_scan(b)[0] != 0xFF)}/{n}")
    if disagree:
        print("\nDISAGREEMENTS (board, mine (col,row), RTL (col,row)):")
        for x in disagree[:10]:
            print(f"  board {x[0]:>3}  mine={x[1]}  rtl={x[2]}")
    else:
        print("\nEXACT MATCH on every board -- this rig's v1 descriptors are the "
              "ones the shipped firmware publishes.")

    # ---- and the coherence question, on the RTL's OWN chosen column --------
    print("\n=== v1 coherence, judged against the RTL's own chosen placement ===")
    import fast_rtl_x as FX
    var_of_o4 = FX._VAR_OF_O4
    pub = coh = deeper = 0
    for board, row in zip(boards, rows):
        tcol, trow = int(row["tcol"]), int(row["trow"])
        if tcol == 0xFF:
            continue
        pub += 1
        # fast-sim colour plane: 0 = empty. Only occupancy matters here.
        col = [0 if b == 0xFF else 1 for b in board]
        var = int(var_of_o4[int(row["o4"])])
        cc = int(row["col"])
        rest, landed, status = EM.v1_execute(col, var, cc, tcol, trow)
        plain = EM.straight_drop_row(col, cc, EM.is_horizontal(var))
        if status == "coherent":
            coh += 1
            if rest is not None and plain is not None and rest > plain:
                deeper += 1
    print(f"published {pub}   coherent {coh} ({coh / max(1, pub):.1%})   "
          f"lands deeper {deeper} ({deeper / max(1, pub):.1%})")
    print("\n(co-sim farm descriptor_audit.py, 50 real-L11 boards, same firmware: "
          "26 published, 11 coherent = 42%, 1 deeper = 4%)")
    return 0 if not disagree else 1


if __name__ == "__main__":
    sys.exit(main())
