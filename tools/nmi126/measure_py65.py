#!/usr/bin/env python3
"""#126 stage 3: ADVERSARIAL measured worst-case of the two spike paths, on the
real emitted bytes, cycle-exact (py65). Sits beside the static bound in the
budget table: bound >= adversarial-measured >= field-measured, and the gap
between the columns is the analyzer's conservatism, stated not hidden.

Scenarios:
  p1_search  DRP1NATIVE (TCVC): JSR search_entry on adversarial boards.
  pre_tick   DRPRESTART (v6e): the release-edge projection spike, full commit
             path (copy + orphan guard + settle + match scan + upload + GO).

Run with the dr-mario-mods venv python (py65).
"""
import json
import os
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


def run_routine(mem, entry, state, max_steps=2_000_000):
    from py65.devices.mpu6502 import MPU
    m = MPU(memory=list(mem))
    for a, v in state.items():
        m.memory[a] = v
    SENT = 0x3000
    m.memory[SENT] = 0xEA
    m.pc = entry
    m.memory[0x1FE] = (SENT - 1) & 0xFF
    m.memory[0x1FF] = ((SENT - 1) >> 8) & 0xFF
    m.sp = 0xFD
    steps = 0
    while m.pc != SENT and steps < max_steps:
        m.step()
        steps += 1
    assert m.pc == SENT, f"did not return (pc=${m.pc:04X} after {steps} steps)"
    return m.processorCycles, m


def load_units(ir_path):
    meta = json.load(open(ir_path))
    mem = [0] * 0x10000
    for u in meta["units"].values():
        b = bytes.fromhex(u["bytes"])
        mem[u["base"]:u["base"] + len(b)] = list(b)
    return meta, mem


def boards_p1():
    """Adversarial P1 boards ($0400, $FF = empty). Cost drivers: land_col row
    scans (deep on EMPTY columns), eval_pair's 3 scan_cell_* per placement
    (long same-colour runs), all 8V+7H placements evaluated (no unusable
    columns)."""
    out = {}
    empty = [0xFF] * 128
    out["empty"] = empty
    # floor of same-colour cells: every column lands at row 14/15 (deep scan)
    # and every scan_run walks a full 8-cell row run + 2-cell columns.
    floor = [0xFF] * 128
    for c in range(8):
        floor[15 * 8 + c] = 0xD0  # virus colour 0, full bottom row
        floor[14 * 8 + c] = 0xD0
    out["floor_runs"] = floor
    # tall same-colour columns with tops staggered so nothing is unusable:
    # long column runs for scan_cell_col, deep-ish falls.
    tall = [0xFF] * 128
    for c in range(8):
        for r in range(4 + (c % 2), 16):
            tall[r * 8 + c] = 0xD0
    out["tall_cols"] = tall
    return out


def measure_tcvc(ir):
    meta, mem = load_units(ir)
    u = meta["units"]["p1ai"]
    entry = u["base"] + u["labels"]["search_entry"]
    print("== TCVC p1_search (search_entry), adversarial boards ==")
    worst = 0
    for name, board in boards_p1().items():
        state = {0x0301: 0x00, 0x0302: 0x00}   # same colour both halves
        for i, v in enumerate(board):
            state[0x0400 + i] = v
        cyc, _ = run_routine(mem, entry, state)
        worst = max(worst, cyc)
        print(f"  {name:12s} {cyc:7d} cyc")
    print(f"  ADVERSARIAL MEASURED WORST: {worst} cyc")
    return worst


def measure_v6e(ir):
    meta, mem = load_units(ir)
    env = json.load(open("roms/manifests/v6e.json"))["flag_snapshot"]
    os.environ.update({k: str(v) for k, v in env.items()})
    sys.path.insert(0, os.getcwd())
    import patch_cartridge_copro as pcc
    u = meta["units"]["main"]
    entry = u["base"] + u["labels"]["pre_tick"]
    print("== v6e pre_tick (release-edge projection), adversarial states ==")

    def state_for(row0_singles, col_depth_empty=True, runs=False):
        st = {}
        # board $0500: empty ($FF), volley singles at row 0
        for i in range(128):
            st[0x0500 + i] = 0xFF
        if not col_depth_empty:
            # half-full columns: singles land mid-board
            for c in range(8):
                for r in range(8, 16):
                    st[0x0500 + r * 8 + c] = 0xD0 + (c % 3)
        if runs:
            # bottom rows: 3-in-a-row of each colour so every match scan walks
            # far without ever finding 4 (no bail; commit path)
            for c in range(8):
                st[0x0500 + 15 * 8 + c] = 0xD0 + ((c // 3) % 3)
        for c in row0_singles:
            st[0x0500 + c] = 0x80  # singleHalfPill colour 0 at row 0
        # release edge: attackSize now 0, was nonzero last hook
        st[0x0398] = 0x00
        st[pcc.PRE_LAST2] = 0x03
        st[pcc.PRE_ACT2] = 0x00
        st[getattr(pcc, "ARMED2")] = 0x00
        st[getattr(pcc, "PEND2")] = 0x00
        # preview colours + seed + reserve index for the commit tail
        st[0x039A] = 0x01
        st[0x039B] = 0x02
        st[0x03A7] = 0x00
        st[0x0780] = 0x08   # reserve value 8 -> pt_dv max iterations
        return st

    cases = {
        "vs4_empty":  state_for([0, 2, 4, 6]),                       # ROM-max volley, 16-row falls
        "vs4_runs":   state_for([0, 2, 4, 6], runs=True),
        "hyp8_empty": state_for(list(range(8))),                     # beyond ROM (size<=4): hypothetical
        "hyp8_runs":  state_for(list(range(8)), runs=True),
    }
    worst_rom = worst_hyp = 0
    for name, st in cases.items():
        cyc, m = run_routine(mem, entry, st)
        committed = m.memory[pcc.PRE_ACT2]
        print(f"  {name:12s} {cyc:7d} cyc  (committed={committed})")
        if name.startswith("vs4"):
            worst_rom = max(worst_rom, cyc)
        else:
            worst_hyp = max(worst_hyp, cyc)
    print(f"  ADVERSARIAL MEASURED WORST: ROM-reachable(<=4 cols) {worst_rom} cyc,"
          f" hypothetical 8-col {worst_hyp} cyc")
    return worst_rom, worst_hyp


def main():
    for ir, need in (("tmp/nmi126/v6e_ir.json", "roms/manifests/v6e.json"),
                     ("tmp/nmi126/tcvc_ir.json", "roms/manifests/tuck-cvc-mister.json")):
        if not os.path.exists(ir):
            subprocess.run([sys.executable, "tools/nmi126/capture_ir.py", need, ir],
                           check=True)
    measure_tcvc("tmp/nmi126/tcvc_ir.json")
    measure_v6e("tmp/nmi126/v6e_ir.json")


if __name__ == "__main__":
    main()
