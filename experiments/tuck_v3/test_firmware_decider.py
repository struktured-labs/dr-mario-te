#!/usr/bin/env python3
"""DIAGNOSTIC, NOT THE DECISIVE GATE. This file compares the REAL firmware's decision
(via FirmwareDecider) against the offline python reference (root_search.choose_root_
with_tucks) on the same board/pill -- it exists to sanity-check firmware_decider.py's
reconstruction plumbing (board conversion, action/tuck-cell recovery), not to certify
that root-action tucks work. The actual decisive gate is ab_root_firmware.py's within-
firmware A/B (DRCOPRO_TUCKV3=0 vs 1, both real bytes), which never depends on this file's
comparison agreeing.

FINDING (recorded here, not just in chat -- this is the artifact that produced the
evidence): running this file's base-action-agreement check on 5 boards surfaced 3/5
action mismatches. Confirmed NOT tie-breaking (the firmware's D_SEED tie-break jitter is
skipped when the seed byte is 0, which it is for plain 0-3 colour values) and NOT a
tuck_v3.py bug (TS_CNT=0, TUCK_COL=0xFF on every mismatching board -- zero tuck code
involved). Root cause: fast_rtl_x.py's `variant("winner")` (what root_search.py, and
therefore the ENTIRE phase-1/phase-2 offline tuck-v3 proof, scores under) uses
W_VRDY=8, W_MATCHED=48, and a FLAT W_HANG_SHIP=40 hang-credit term (fast_rtl_x.py's own
comment: "NOT R4-refined in the python bridge"). build_copro_d3.build_image() -- the
actual shipped firmware config -- sets W_VRDY=12, W_MATCHED_COVER=60, and the R4-refined
depth-proportional/virus-column-only hang credit (HANG_DEPTH_PROP, HANG_VIRUS_COL_ONLY,
W_HANG_GAP=20). Verified via direct D_BVL/D_BVH firmware readback vs root_search._root_
value on identical (board, action) pairs: a 50-point gap on one board, confirmed not a
readback artifact.

This is NOT a bug in firmware_decider.py, tuck_v3.py, or root_search.py -- fast_rtl_x.py's
own top-of-file docstring already states it is a "RECONSTRUCTION of build_copro_d3...
imm-invariant across A/B arms", never claimed to be bit-exact against the real RTL-
faithful firmware. It IS a real, now-recorded instance of the "goldens-vs-shipped" trap
class already known in this codebase (dr-mario-golden-is-weekend-era memory: nes_d3_
golden ignores R47 flags too) -- worth finding for the next person who tries an absolute
python-vs-firmware value comparison, which is exactly what this file does and why it is
kept as a diagnostic rather than deleted once the decisive-gate reframe was accepted.

Two levels of agreement were checked, deliberately NOT collapsed into one pass/fail: the
base-action check above, and a separate tuck-recognition check (does the firmware
correctly IDENTIFY and FIRE a tuck on a board where one is clearly available) -- kept
separate because tuck_scan_v3.py's enumerator (fpga/copro/tuck_validation/
tuck_scan_v3_ref.py) and root_search.py's tuck_root_candidates (tuck_enum.py-based) are
NOT the same enumerator and may legitimately propose different candidate sets, so an
exact placement match was never asserted there, only that BOTH recognise the opportunity.
"""
import os
import sys

ROOT = "/home/struktured/projects/dr_mario_rl"
QA = "/home/struktured/projects/dr-mario-qa-wt/experiments"
for _p in (ROOT + "/tmp/combo_term", ROOT + "/tmp/endgame", ROOT + "/tmp/tuck",
           ROOT + "/.claude/worktrees/faithful-sim/src", QA, QA + "/tuck_v3"):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import numpy as np
import fast_rtl_x as FX
from fb import FB
import root_search as RS
from firmware_decider import FirmwareDecider


class P:
    def __init__(self, a, b):
        self.a = a
        self.b = b


def test_base_action_agreement(n=5, seed=20260802):
    print(f"(1) BASE-ACTION AGREEMENT (no tuck opportunity), n={n} random boards")
    import random
    rnd = random.Random(seed)
    FX.warmup_ship_eh(topk2=8)
    w, fl = FX.variant("winner")
    fd = FirmwareDecider()

    fails = 0
    for i in range(n):
        grid = [0] * 128
        for c in range(8):
            h = rnd.randrange(0, 16 + 1)
            for r in range(16 - h, 16):
                grid[r * 8 + c] = rnd.randint(1, 3)
        grid[3] = grid[4] = 0     # keep columns 3/4 open, matches equivalence_selftest
        fb = FB(grid)
        cur = P(rnd.randint(1, 3), rnd.randint(1, 3))
        nxt = P(rnd.randint(1, 3), rnd.randint(1, 3))

        py_pick = RS.choose_root_with_tucks(fb, cur, nxt, w, fl, topk2=8, tuck_cands=[])
        col, vir = RS.board_flat_from_fb(fb)
        fw_pick = fd.decide(col, vir, cur.a, cur.b, nxt.a, nxt.b)

        py_action = py_pick["action"] if py_pick["kind"] == "base" else None
        fw_action = fw_pick["action"] if fw_pick and fw_pick["kind"] == "base" else None
        ok = (py_action == fw_action)
        print(f"  [{i}] py={py_pick.get('action')}({py_pick['kind']}) "
              f"fw={fw_pick.get('action') if fw_pick else None}"
              f"({fw_pick['kind'] if fw_pick else None}) steps={fw_pick.get('steps') if fw_pick else '-'}"
              f"  {'OK' if ok else 'FAIL'}")
        if not ok:
            fails += 1
    return fails


def test_tuck_recognition():
    print("\n(2) TUCK RECOGNITION on the known-tuck-favourable board "
          "(_cave_horizontal_board + pre-existing pair, from test_tuck_root_extension.py)")
    sys.path.insert(0, "/home/struktured/projects/dr-mario-qa-wt/fpga/copro/tuck_validation")
    from tuck_scan_v3_ref import _cave_horizontal_board

    board_nes = _cave_horizontal_board()
    board_nes[10 * 8 + 5] = 1
    board_nes[10 * 8 + 6] = 1
    board_nes[0 * 8 + 0] = 0xD0

    sys.path.insert(0, QA + "/bitexact_gate")
    from common import nes_to_arrays
    col, vir = nes_to_arrays(board_nes)

    fd = FirmwareDecider()
    ca, cb, na, nb = 1, 1, 2, 0     # matches the proven-tuck-wins scenario's colours
    fw_pick = fd.decide(col, vir, ca, cb, na, nb)
    ok = fw_pick is not None and fw_pick["kind"] == "tuck"
    print(f"  firmware: {fw_pick}")
    print(f"  {'OK' if ok else 'FAIL'} -- firmware fires a tuck on a board where one is "
          f"the only route to the clear")
    return 0 if ok else 1


def main():
    fails = test_base_action_agreement()
    fails += test_tuck_recognition()
    print(f"\n{'ALL PASS' if not fails else f'{fails} FAILURES'}")
    return fails == 0


if __name__ == "__main__":
    ok = main()
    sys.exit(0 if ok else 1)
