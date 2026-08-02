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


def test_base_action_agreement(fd, n=5, seed=20260802):
    print(f"(1) BASE-ACTION AGREEMENT (no tuck opportunity), n={n} random boards")
    import random
    rnd = random.Random(seed)
    FX.warmup_ship_eh(topk2=8)
    w, fl = FX.variant("winner")

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


def test_tuck_recognition(fd):
    print("\n(2) TUCK RECOGNITION on the known-tuck-favourable board "
          "(_cave_horizontal_board + pre-existing pair, from test_tuck_root_extension.py)")
    sys.path.insert(0, "/home/struktured/projects/dr-mario-qa-wt/fpga/copro/tuck_validation")
    from tuck_scan_v3_ref import _cave_horizontal_board

    # FOURTH BUG FOUND while re-running this diagnostic (task #17): this board was built
    # with two encoding mistakes, the SAME confound class already documented+fixed in
    # test_tuck_root_extension.py's _win_board() this session, just never ported here:
    #   1. `board_nes[i] = 1`/`= 0xD0` are RAW low-nibble writes. _cave_horizontal_board()'s
    #      own convention only round-trips correctly through nes_to_arrays (which expects
    #      the settled=0x40|colour / virus=0xD0|colour NES tile-byte encoding) if cells are
    #      written in THAT encoding -- raw `1` decodes via nes_to_arrays as colour=(1&0xF)+1
    #      =2, not the intended colour 1, and raw `0xD0` decodes as colour=(0xD0&0xF)+1=1
    #      with vir=1 (accidentally still a virus, but the WRONG colour, colour 1 not the
    #      intended low-nibble-0 virus) -- silently corrupting the scenario this test means
    #      to construct.
    #   2. The lip (row9, cols4-6, default raw colour 1 from _cave_horizontal_board() itself)
    #      shares its (corrupted, post-decode) low nibble with cells written here, letting a
    #      plain vertical drop chain straight through the lip to the virus via ordinary
    #      colour-run matching -- giving a BASE action a free win too, so "only a tuck can
    #      reach the virus" was never actually true on this board.
    # Fixed the same way _win_board() was: recolour the lip off the target colour, and use
    # the real 0x40|c / 0xD0|c tile encoding for the placed cells.
    board_nes = _cave_horizontal_board()
    for c in (4, 5, 6):
        board_nes[9 * 8 + c] = 3   # recolour the lip away from the target's colour
    board_nes[10 * 8 + 5] = 0xD1   # the board's only virus, colour 1
    board_nes[10 * 8 + 6] = 0x40 | 1
    board_nes[0 * 8 + 0] = 0xFF    # no longer need a second forced virus cell

    sys.path.insert(0, QA + "/bitexact_gate")
    from common import nes_to_arrays
    col, vir = nes_to_arrays(board_nes)

    # nb=0 (this test's original value) also predates the color off-by-one fix in
    # firmware_decider.decide() (this session, earlier) -- decide() now subtracts 1 from
    # ca/cb/na/nb expecting the 1..3 convention, so nb=0 underflows to -1 and
    # build_image's `img[S_NB] = nB` throws ValueError (byte must be in range(0,256)).
    ca, cb, na, nb = 1, 1, 2, 1     # matches the proven-tuck-wins scenario's colours
    fw_pick = fd.decide(col, vir, ca, cb, na, nb)
    ok = fw_pick is not None and fw_pick["kind"] == "tuck"
    print(f"  firmware: {fw_pick}")
    print(f"  {'OK' if ok else 'FAIL'} -- firmware fires a tuck on a board where one is "
          f"the only route to the clear")
    if not ok:
        print("  KNOWN BROKEN (task #17, found while re-verifying this diagnostic after "
              "the sanity-8-v3 arm-plumbing fix): the two-cell recolour above stopped the "
              "encoding crash, but _cave_horizontal_board()'s FLOOR rows (11-15) are ALSO "
              "raw low-nibble values, not the 0x40|c/0xD0|c NES tile encoding "
              "nes_to_arrays() assumes -- the whole board decodes to something other than "
              "intended, not just the two touched cells. _cave_horizontal_board() was only "
              "ever designed for DIRECT cpu.set_board() loading (see "
              "test_tuck_root_extension.py's _win_board(), which never goes through "
              "nes_to_arrays) -- reusing it here through the col/vir round-trip is the "
              "wrong board source for this function's needs. Real fix is a from-scratch "
              "col/vir-native board construction, not a patch on top of this one -- out of "
              "scope for the arm-plumbing bug this session was chasing (this file is "
              "documented DIAGNOSTIC, NOT THE DECISIVE GATE, and does not gate pass 1).")
    return 0 if ok else 1


def main():
    # ONE shared FirmwareDecider across both tests (found while investigating the
    # sanity-8-v3 arm-plumbing bug, task #17): each construction does a real module
    # (re)load via _load_d3(), and build_copro_d3 (imported fresh only on the FIRST
    # construction, then served from sys.modules on any later one in the same process)
    # would end up referencing a STALE test_search_d3 module object on a second
    # construction, tripping `assert B.D3 is self.D3` inside firmware_decider.py.
    # Pre-existing in this file (unrelated to that bug's fix), not previously caught
    # because nothing had run both tests back-to-back in one process before. Both
    # tests want the same config (tuck=1, the default) anyway, so sharing is correct,
    # not a workaround.
    fd = FirmwareDecider()
    fails = test_base_action_agreement(fd)
    fails += test_tuck_recognition(fd)
    print(f"\n{'ALL PASS' if not fails else f'{fails} FAILURES'}")
    return fails == 0


if __name__ == "__main__":
    ok = main()
    sys.exit(0 if ok else 1)
