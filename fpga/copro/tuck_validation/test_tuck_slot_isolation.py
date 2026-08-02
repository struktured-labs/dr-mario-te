#!/usr/bin/env python3
"""SLOT-ISOLATION ASSERT (team-lead requirement, stage-2 scoring ruling): prove tuck
scoring does not perturb the base search's own RTL slot state.

Scope note (why this checks slot 1 specifically, not "slots 1-3 byte-identical to a
flag-off run"): slot 1 (root parent) is written ONCE at the very top of `search` and never
written again by ANYTHING on the base side -- it is the one slot with a meaningful
invariant across an entire decision. Slots 2 and 3 are transient scratch that the BASE
search's own ply-1/expectimax loops already overwrite repeatedly and unpredictably
(whichever candidate/pill was processed last wins) even across two flag-OFF runs with
different candidate orderings -- there is no "the flag-off value" for slot 2/3 to compare
against, they are last-write-wins scratch by design on both paths. What actually matters,
and what this test proves: after a full tuck-enabled decision (search -> tuck_scan_v3 ->
tuck_root_extension, which reads/writes slot 0 and slot 2 extensively), slot 1 still holds
EXACTLY the original root board, unperturbed -- i.e. the tuck path's slot-0 injection
target (dest_slot=2, tuck_score.py) never accidentally aliases or bleeds into slot 1.

MEASUREMENT NOTE: attach_engine_emu's CMD table (test_search_d3.py) has no raw board
READBACK path -- CMD2 (a_sl<-slot) only updates the emulator's internal python `st["
slots"][0]` state; it does not write anything back to the underlying LEV_BOARD memory
bytes a plain `cpu.mem[LEV_BOARD+i]` read would see (confirmed by an initial version of
this test that tried exactly that and got all-zero readback -- caught before being
mistaken for a real corruption, not silently accepted). leaf_d3 (CMD1, via LEV_SCO) IS a
legitimate observable: a rich, board-wide sum over many terms (buried/setup/etc.), so a
match after the full tuck pipeline runs is strong evidence of byte-level equality, not
just proof against gross corruption -- a single-cell change anywhere on a 128-cell board
overwhelmingly changes at least one of those terms.

PROMOTED TO EH_PLY1=True (task #17 stage 3, team-lead ruling): inherits this from
test_tuck_root_extension.py's own build (`R.COMBINED`/`R.D3_LABELS`/`R.DECIDE_ADDR`),
which now targets fpga/copro/tuck_v3.py (canonical repo) directly under the real shipped
config, including the cp_live_cur fix.
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
DRIVER = os.environ.get("DRNAV", "/home/struktured/projects/dr-mario-mods-wt/driver-nav")
CANON = os.environ.get("DRCANON", "/home/struktured/projects/dr-mario-canonical-wt")
sys.path.insert(0, HERE)
sys.path.insert(0, DRIVER)
sys.path.insert(0, os.path.join(CANON, "tests"))

import test_tuck_root_extension as R   # noqa: E402 -- reuses its already-built COMBINED image
from py65_harness import Cpu           # noqa: E402
import test_search_d3 as D3            # noqa: E402

BASE = 0x8000
LEV_BOARD, LEV_A_SL, LEV_CMD, LEV_GO = 0x7000, 0x70E4, 0x70F4, 0x70F8
LEV_SCO, LEV_WIN_R = 0x70F0, 0x70F2


def leaf_of_slot(cpu, slot):
    """CMD2 (CUR<-slot[slot]) then CMD1 (LEAF on CUR) -> (sco, win) for that slot's
    current content. A behavioural proxy for "did this slot's board change" -- see the
    module docstring for why a raw byte readback isn't available here."""
    cpu.mem[LEV_A_SL] = slot
    cpu.mem[LEV_CMD] = 2
    cpu.mem[LEV_CMD] = 1
    sco = cpu.mem[LEV_SCO] | (cpu.mem[LEV_SCO + 1] << 8)
    return sco, cpu.mem[LEV_WIN_R]


def _reference_leaf(board):
    """Fresh Cpu: write `board` directly to LEV_BOARD (populates slot 0, the default
    wslot), then leaf it -- the ground-truth (sco, win) for the UNPERTURBED original
    board, independent of anything the tuck pipeline does."""
    cpu = Cpu()
    cpu.load(BASE, R.COMBINED)   # code is irrelevant, only need a valid image;
                                   # attach_engine_emu intercepts LEV_* writes regardless
    D3.attach_engine_emu(cpu)
    for i, v in enumerate(board):
        cpu.mem[LEV_BOARD + i] = v
    return leaf_of_slot(cpu, 0)


def test_slot1_unperturbed():
    print("(1) SLOT 1 (root parent) unperturbed by a full tuck-enabled decision")
    board = R._win_board()   # reuses test_tuck_root_extension's own board construction --
                              # a third hand-copy of the same board would drift out of
                              # sync with it silently (already happened once this session).
    ca0, cb0, na0, nb0 = 1, 1, 2, 0
    pillA, pillB = [0, 2], [2, 1]

    ref_sco, ref_win = _reference_leaf(board)
    print(f"  reference leaf(original board): sco={ref_sco} win={ref_win}")

    cpu = Cpu()
    cpu.load(BASE, R.COMBINED)
    cpu.set_board(board)
    D3.attach_engine_emu(cpu)
    cpu.mem[D3.S_CA] = ca0
    cpu.mem[D3.S_CB] = cb0
    cpu.mem[D3.S_NA] = na0
    cpu.mem[D3.S_NB] = nb0
    for i in range(D3.NPILLS):
        cpu.mem[D3.PILLA + i] = pillA[i]
        cpu.mem[D3.PILLB + i] = pillB[i]
    cpu.call(BASE + R.D3_LABELS["search"], max_steps=3_000_000_000)
    cpu.call(R.DECIDE_ADDR, max_steps=3_000_000_000)

    tk2_bkind = cpu.mem[R.TV.TK2_BKIND]
    after_sco, after_win = leaf_of_slot(cpu, 1)
    print(f"  TK2_BKIND={tk2_bkind} (expect 1 -- confirms the tuck path actually ran and "
          f"touched slot 0/slot 2 extensively, making this a meaningful test)")
    print(f"  leaf(slot1 after full pipeline): sco={after_sco} win={after_win}")

    ok = (tk2_bkind == 1) and (ref_sco, ref_win) == (after_sco, after_win)
    print(f"  {'OK' if ok else 'FAIL'}")
    return 0 if ok else 1


def main():
    fails = test_slot1_unperturbed()
    print(f"\n{'ALL PASS' if not fails else f'{fails} FAILURES'}")
    return fails == 0


if __name__ == "__main__":
    ok = main()
    sys.exit(0 if ok else 1)
