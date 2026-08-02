#!/usr/bin/env python3
"""COPRO-RAM AUDIT -- the authority for "is this scratch byte free", built programmatically
from what the firmware emission ACTUALLY writes, not eyeballed from comments.

Task #17 phase 3 stage 2, decision #3 (team-lead, 2026-08-02): "Same lesson as
FREE_SPACE_MAP -- filler is not proof of free... Write a copro-RAM audit (extract every
absolute $0xxx/$61xx address the firmware emission actually touches across
build_copro_d3.py + test_search_d3.py + tuck_scan.py, compute the free set
programmatically), commit it as the copro-RAM map, then allocate the 64B [candidate list]
from it WITH an assert in the builder that fails if any future emission overlaps."

METHOD: monkey-patch Asm6502.ins16 (the single choke point for every absolute-mode 6502
instruction with an EXPLICIT numeric operand -- STA_abs/LDA_abs/CMP_abs/INC_abs/etc; JSR/JMP
targets go through a SEPARATE method with label fixups, so this never records code addresses,
only data/register addresses) to record every address touched during a REAL build, across
BOTH valid copro RAM windows (CoproDrMario.sv: copro RAM is ONLY $0000-$0FFF + $6100-$61FF,
per test_search_d3.py's own HW-CONSTRAINT comment). Run with EMIT_TUCK=1 and DRCOPRO_ARM=1 so
the audit reflects the fullest realistic build (today's shipped search + the existing v1 tuck
enumerator + the #33 passenger's arm-select registers), not just the bare search.

This is DYNAMIC (actually assembling real code), not a grep over declared constants -- a
declared-but-unused constant would falsely read as "touched"; a dynamically-computed address
(none exist in this codebase's Asm6502 usage, but would be invisible to a static grep) would
falsely read as "free". Neither hazard applies here because every RAM access in this codebase
is emitted via ins16() with a literal integer at build time.

Usage: python3 ram_audit.py [--out ram_map.json]
"""
from __future__ import annotations

import os
import sys
import json
import argparse

CANON = os.environ.get("DRCANON", "/home/struktured/projects/dr-mario-canonical-wt")
COPRO = os.path.join(CANON, "fpga", "copro")
sys.path.insert(0, COPRO)
sys.path.insert(0, CANON)
sys.path.insert(0, os.path.join(CANON, "tests"))

RANGES = [(0x0000, 0x1000), (0x6100, 0x6200)]   # copro RAM: $0000-$0FFF, $6100-$61FF

# PROPOSED allocation for the tuck v3 candidate list (16 slots x 4B = 64B: approach col,
# trigger row, rest row, orient), immediately after tuck_scan's existing 10-byte scratch
# ($61A1-$61AA) in the $613B-$61FE free run this audit found. NOT YET CONSUMED by any
# emission -- reserving it here and gating on it lets the allocation be pinned BEFORE the
# enumerator that uses it is written, per the house rule (assert the outcome, not the code
# position) -- any future emission that touches this range without updating this constant
# fails the check below immediately, rather than silently colliding at runtime.
TUCK_V3_CANDLIST = (0x61AB, 0x61EB)   # [lo, hi), 64 bytes, $61AB-$61EA


def check_reserved(touched, lo, hi):
    """Fail if anything in `touched` falls inside [lo, hi) -- the allocation must stay
    virgin until the candidate-list emission itself claims it."""
    hits = sorted(a for a in touched if lo <= a < hi)
    return hits


def in_ram(addr):
    return any(lo <= addr < hi for lo, hi in RANGES)


def run_audit():
    import patch_vs_cpu
    Asm6502 = patch_vs_cpu.Asm6502

    touched = {}   # addr -> set of mnemonics that touched it

    orig_ins16 = Asm6502.ins16
    orig_ins = Asm6502.ins

    def traced_ins16(self, mnem, value):
        # absolute-family: STA_abs/LDA_abs/STA_absX/etc, 2-byte operand IS the address.
        if in_ram(value):
            touched.setdefault(value, set()).add(mnem)
        return orig_ins16(self, mnem, value)

    ZP_SUFFIXES = ("_zp",)   # ins() is ALSO used for LDA_imm etc where the operand is a
                             # VALUE, not an address -- only _zp-suffixed mnemonics (zero
                             # page addressing) have an address operand here; zero page IS
                             # inside the $0000-$0FFF window so no separate range needed.

    def traced_ins(self, mnem, *operands):
        if mnem.endswith(ZP_SUFFIXES) and operands:
            addr = operands[0]
            if in_ram(addr):
                touched.setdefault(addr, set()).add(mnem)
        return orig_ins(self, mnem, *operands)

    Asm6502.ins16 = traced_ins16
    Asm6502.ins = traced_ins
    try:
        os.environ["DRCOPRO_TUCK"] = "1"
        os.environ["DRCOPRO_ARM"] = "1"
        # fresh import (module-level EMIT_TUCK/EMIT_ARM are read at import time)
        for mod in ("build_copro_d3", "test_search_d3", "tuck_scan", "primitives",
                    "test_depth2", "test_leaf_d3", "test_pollution", "test_readiness_ext",
                    "test_vrdy", "nes_d3_golden"):
            sys.modules.pop(mod, None)
        import build_copro_d3 as B
        img, clen, slen = B.build_image([0xFF] * 128, 0, 0, 0, 0)
    finally:
        Asm6502.ins16 = orig_ins16
        Asm6502.ins = orig_ins

    return touched


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=os.path.join(
        os.path.dirname(os.path.abspath(__file__)), "copro_ram_map.json"))
    a = ap.parse_args()

    touched = run_audit()
    touched_addrs = sorted(touched)

    free_runs = []
    for lo, hi in RANGES:
        run_start = None
        for addr in range(lo, hi):
            if addr in touched:
                if run_start is not None:
                    free_runs.append((run_start, addr))   # [run_start, addr)
                    run_start = None
            else:
                if run_start is None:
                    run_start = addr
        if run_start is not None:
            free_runs.append((run_start, hi))

    total_free = sum(hi - lo for lo, hi in free_runs)
    total_touched = len(touched_addrs)

    print(f"COPRO RAM AUDIT (dynamic, EMIT_TUCK=1 + DRCOPRO_ARM=1)")
    print(f"  windows: {[(hex(lo), hex(hi)) for lo, hi in RANGES]}")
    print(f"  touched: {total_touched} bytes")
    print(f"  free   : {total_free} bytes, in {len(free_runs)} run(s)")
    print(f"\n  FREE RUNS (>= 4 bytes shown):")
    for lo, hi in free_runs:
        if hi - lo >= 4:
            print(f"    ${lo:04X}-${hi-1:04X}  ({hi - lo} bytes)")

    lo, hi = TUCK_V3_CANDLIST
    hits = check_reserved(touched, lo, hi)
    print(f"\n  RESERVED for tuck v3 candidate list: ${lo:04X}-${hi-1:04X} ({hi-lo} bytes)")
    if hits:
        print(f"  [FAIL] {len(hits)} address(es) inside the reservation are ALREADY touched: "
              f"{[hex(x) for x in hits]}")
    else:
        print(f"  [PASS] reservation is virgin -- safe to allocate")

    out = {
        "windows": RANGES,
        "touched_addrs": touched_addrs,
        "touched_detail": {hex(a): sorted(mnems) for a, mnems in touched.items()},
        "free_runs": free_runs,
        "total_touched": total_touched,
        "total_free": total_free,
        "tuck_v3_candlist_reservation": [lo, hi],
        "tuck_v3_candlist_reservation_hits": [hex(x) for x in hits],
    }
    with open(a.out, "w") as fh:
        json.dump(out, fh, indent=1)
    print(f"\nwrote {a.out}")
    sys.exit(1 if hits else 0)


if __name__ == "__main__":
    main()
