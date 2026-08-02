#!/usr/bin/env python3
"""Drives the REAL EMIT_TUCK_V3=1/0 firmware (py65-executed, the actual assembled 6502
bytes from fpga/copro/tuck_v3.py + build_copro_d3.py in the canonical repo) as the
decision-maker for one placement, returning a `pick` dict shaped like
root_search.choose_root_with_tucks()'s return (kind/action or kind/placement+ca+cb).

TWO USES, kept in one module because the reconstruction logic is shared, but DIFFERENT
in what they prove -- see test_firmware_decider.py's own docstring for why exact-match
against root_search.py is NOT the decisive criterion:
  1. THE DECISIVE GATE (ab_root_firmware.py): DRCOPRO_TUCKV3=0 vs =1, BOTH driven by this
     class, real bytes both arms -- self-consistent by construction, never compared
     against root_search.py's absolute values at all.
  2. A DIAGNOSTIC (test_firmware_decider.py): compares this class's output against
     root_search.py's on the SAME board, to sanity-check the reconstruction plumbing.
     This diagnostic is what surfaced the eval-weight-configuration gap between
     fast_rtl_x.py's variant("winner") and build_image()'s actual shipped overrides
     (W_VRDY 8 vs 12, W_MATCHED_COVER 48 vs 60, plus a documented simplified hang-credit
     formula) -- a real, now-recorded instance of the "goldens-vs-shipped" trap class
     already known in this codebase (see dr-mario-golden-is-weekend-era memory). NOT a
     bug in this file or in tuck_v3.py: fast_rtl_x.py's own docstring already states it
     is a reconstruction, not a bit-exact copy of the real RTL-faithful firmware, and the
     decisive gate (use 1, above) never depends on this agreement.

Board representation bridge: root_search.py's world uses two int8[128] arrays (col, vir);
the real firmware's LIVE board ($0500) is a single NES-tile-byte array (EMPTY=0xFF, high
nibble 0xD0=virus/0x40=settled, low nibble=colour). `arrays_to_nes`/`nes_to_arrays`
(bitexact_gate/common.py) already exist and bridge this exactly -- reused here, not
reimplemented (avoids re-deriving the tile encoding a third time in this codebase).

Reconstructing the WINNING placement from the firmware's published subset:
  BASE action: firmware publishes D_BC (column) and D_BO (o4, the search's own o4
    convention). `action = FX._VAR_OF_O4[D_BO] * 8 + D_BC` reproduces root_search's own
    action encoding (`var*8+col`) exactly -- FX._VAR_OF_O4 = [2,3,0,1] is the SAME table
    fast_rtl_x.py already uses internally for this o4->variant mapping.
  TUCK action: the firmware publishes (target=D_BC, approach=TUCK_COL, trigger=TUCK_ROW)
    but NOT rest/orient (needed to reconstruct the exact resting cells). Re-running
    `ref_tuck_scan_v3` (the ALREADY bit-exact-verified python reference for tuck_scan_v3.py,
    fpga/copro/tuck_validation/tuck_scan_v3_ref.py) on the SAME board and matching the
    candidate whose (target, approach, trigger) equal the firmware's published fields
    recovers rest/orient safely -- this is NOT a new source of risk, it reuses an
    enumerator already proven bit-identical to the real 6502 across 67 boards.
"""
from __future__ import annotations

import os
import sys
import importlib.util

CANON = "/home/struktured/projects/dr-mario-canonical-wt"
QA = "/home/struktured/projects/dr-mario-qa-wt/experiments"
QA_TUCK = "/home/struktured/projects/dr-mario-qa-wt/fpga/copro/tuck_validation"
ROOT = "/home/struktured/projects/dr_mario_rl"

for _p in (os.path.join(CANON, "fpga", "copro"), os.path.join(QA, "bitexact_gate"),
           QA_TUCK, ROOT + "/tmp/combo_term"):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from common import arrays_to_nes                      # noqa: E402  bitexact_gate
from tuck_scan_v3_ref import ref_tuck_scan_v3, candidate_cells, H, V, RH, RV  # noqa: E402
import fast_rtl_x as FX                                 # noqa: E402

_FLIP = {H: 0, V: 1, RH: 1, RV: 0}


def _load_d3():
    """Same force-load trick dbg_build.py uses -- guarantees build_copro_d3's own
    `import test_search_d3` resolves to this exact module object (the one with
    eh_terms_scan), not whatever happens to be first on sys.path otherwise."""
    spec = importlib.util.spec_from_file_location(
        "test_search_d3", os.path.join(CANON, "tests", "test_search_d3.py"))
    d3 = importlib.util.module_from_spec(spec)
    sys.modules["test_search_d3"] = d3
    spec.loader.exec_module(d3)
    return d3


class FirmwareDecider:
    """One instance per WORKER (not per decision -- the D3/build_copro_d3 module load is
    the expensive one-time setup; each decision only re-runs build_image + a py65 call)."""

    def __init__(self, drchain=180, drfix=1, arm=1):
        os.environ["DRCOPRO_TUCKV3"] = "1"
        os.environ["DRCOPRO_ARM"] = "1" if arm else "0"
        os.environ["DRFIX"] = "1" if drfix else "0"
        os.environ["DRCHAIN"] = str(drchain)
        self.D3 = _load_d3()
        import build_copro_d3 as B
        assert B.D3 is self.D3, "build_copro_d3 imported a different test_search_d3"
        self.B = B
        from py65_harness import Cpu
        self.Cpu = Cpu

    def decide(self, col, vir, ca, cb, na, nb, max_steps=5_000_000_000):
        """col/vir: int8[128] arrays (root_search.py convention, 0=empty/1..3=colour for
        col, 0/1 for vir). ca/cb/na/nb: 0-indexed colours (root_search.py's own
        `int(cur.a)` convention -- NOT offset here, matches build_image's own S_CA/S_CB
        contract, which test_search_d3.py's _e_node masks with 0x0F and expects small
        ints). Returns a `pick` dict shaped like root_search.choose_root_with_tucks()."""
        board = arrays_to_nes(col, vir)
        img, _clen, _slen = self.B.build_image(board, ca, cb, na, nb)
        cpu = self.Cpu()
        for a, v in enumerate(img):
            cpu.mem[a] = v
        self.D3.attach_engine_emu(cpu)
        cpu.mem[self.B.DONE] = 0
        m = cpu.mpu
        m.pc = self.B.STUB
        m.sp = 0xFF
        steps = 0
        while steps < max_steps:
            m.step(); steps += 1
            if cpu.mem[self.B.DONE] == 1:
                break
        assert steps < max_steps, "firmware decision did not reach DONE (raise max_steps?)"

        d_bc = cpu.mem[self.D3.D_BC]
        d_bo = cpu.mem[self.D3.D_BO]
        tuck_col = cpu.mem[0x6139]
        tuck_row = cpu.mem[0x613A]

        if d_bo == 0xFF:
            return None    # no legal move at all (matches root_search's `best is None` case)

        if tuck_col == 0xFF:
            action = int(FX._VAR_OF_O4[d_bo]) * 8 + int(d_bc)
            return {"kind": "base", "action": action, "steps": steps}

        cands, _dropped = ref_tuck_scan_v3(board)
        match = [c for c in cands if c["target"] == d_bc and c["approach"] == tuck_col
                 and c["trigger"] == tuck_row]
        assert match, (
            f"firmware published a tuck descriptor (target={d_bc},approach={tuck_col},"
            f"trigger={tuck_row}) that the python reference enumerator does not "
            f"reproduce on the same board -- this is a REAL divergence between the "
            f"firmware and its reference, not a reconstruction bug; do not paper over it.")
        cand = match[0]
        offa, offb = candidate_cells(cand["target"], cand["rest"], cand["orient"])
        r0, c0 = offa // 8, offa % 8
        r1, c1 = offb // 8, offb % 8
        flip = _FLIP[cand["orient"]]
        col0, col1 = (ca, cb) if flip == 0 else (cb, ca)
        placement = {"cells": (r0, c0, r1, c1)}
        return {"kind": "tuck", "placement": placement, "ca": col0, "cb": col1,
                "steps": steps}
