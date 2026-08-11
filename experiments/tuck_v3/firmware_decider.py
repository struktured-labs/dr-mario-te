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

    def __init__(self, drchain=180, drfix=1, arm=1, tuck=1, theta=150, strand=0):
        # ROOT-CAUSE BUG FIXED HERE (team-lead's sanity-8-v3 diagnostic: paired-pills
        # delta exactly 0.00 on every pair yet fires/game=3.12 -- the signature of both
        # A/B arms executing the SAME decider). This used to hardcode "1" unconditionally,
        # clobbering whatever DRCOPRO_TUCKV3 the caller (ab_root_firmware.py's `_init`)
        # had just set from its own `tuck` arg, BEFORE `_load_d3()` below ever imports
        # build_copro_d3 (which reads the env var once, at import time). Every worker --
        # off-arm or on-arm -- therefore always built the SAME EMIT_TUCK_V3=True image.
        # Confirmed directly: constructing this class with DRCOPRO_TUCKV3 pre-set to "0"
        # still left build_copro_d3.EMIT_TUCK_V3 == True and produced the identical
        # image hash regardless of the caller's intent. Fix: accept `tuck` and set the
        # env var FROM it, matching the pattern DRCOPRO_ARM/DRFIX already use here.
        os.environ["DRCOPRO_TUCKV3"] = "1" if tuck else "0"
        os.environ["DRCOPRO_ARM"] = "1" if arm else "0"
        os.environ["DRFIX"] = "1" if drfix else "0"
        os.environ["DRCHAIN"] = str(drchain)
        # Root-only stranded-half cost.  The shipped champion uses 20; historical tuck
        # gates used the byte-identical default 0.  Make the choice explicit so a py65
        # cross-check cannot accidentally compare strand20 Python to strand0 firmware.
        os.environ["DRSTRAND"] = str(strand)
        # theta mini-sweep build knob (task #17 stage 3, team-lead directive): tuck_v3.THETA
        # reads this once at import time, same hazard/pattern as DRCOPRO_TUCKV3 above -- set
        # BEFORE any firmware module import in this process. Default "150" preserves every
        # prior build byte-for-byte (tuck_v3.py's own default).
        os.environ["DRCOPRO_TUCKV3_THETA"] = str(theta)
        self.D3 = _load_d3()
        import build_copro_d3 as B
        assert B.D3 is self.D3, "build_copro_d3 imported a different test_search_d3"
        self.B = B
        from py65_harness import Cpu
        self.Cpu = Cpu

    def decide(self, col, vir, ca, cb, na, nb, max_steps=5_000_000_000, lnk=None):
        """col/vir: int8[128] arrays (root_search.py/FaithfulBoard convention: col 0=empty,
        1..3=colour; vir 0/1). ca/cb/na/nb: colours in the SAME 1..3 convention (matching
        root_search.py's own `int(cur.a)`, which is what FaithfulBoard/NesPillSource
        naturally produce -- confirmed via env.cur.a/b taking values in {1,2,3} directly).

        ROOT-CAUSE BUG FIXED HERE (found via ab_root_firmware.py's sanity-8 rider tripping
        at 0% clear both arms): this function used to pass ca/cb/na/nb straight through,
        UNCHANGED, into build_image()'s S_CA/S_CB/S_NA/S_NB. But build_image()'s own
        validated caller (build_copro_d3.py main()'s `problem()`, line ~215:
        `return list(faithful_to_nes(fb)), ca - 1, cb - 1, na - 1, nb_ - 1`) SUBTRACTS 1
        before calling build_image() -- the firmware's S_CA/S_CB mailbox speaks the 0..2
        convention (matching arrays_to_nes's `col[i]-1` board-cell low nibble), NOT the
        1..3 convention col[]/FaithfulBoard use. Every pill colour was off by one for the
        entire life of this diagnostic and the A/B harness -- confirmed directly via
        D_BVL/D_BVH firmware readback landing far from root_search._root_value's prediction
        for the SAME reconstructed action, and via a topout-by-pill-23 game trace on a
        seed that clears in 94 pills through the (correctly-1-indexed) python decider."""
        if lnk is None:
            # Historical diagnostics supplied the compact colour/virus planes only.
            # Keep that behavior for replay compatibility, but it is not sufficient for
            # a fixpoint-policy fidelity proof because real parent pills carry links.
            board = arrays_to_nes(col, vir)
        else:
            # faithful_game/cascade_link_x link code -> NES playfield high nibble.
            # 0x8 is the canonical unlinked spelling; 0x4/5 vertical and 0x6/7
            # horizontal.  Viruses always use 0xD regardless of the link plane.
            hi = (0x8, 0x5, 0x4, 0x7, 0x6)
            assert len(lnk) == len(col) == len(vir) == 128
            board = []
            for i in range(128):
                color = int(col[i])
                if color == 0:
                    board.append(0xFF)
                elif int(vir[i]):
                    board.append(0xD0 | (color - 1))
                else:
                    link = int(lnk[i])
                    assert 0 <= link < len(hi), link
                    board.append((hi[link] << 4) | (color - 1))
        img, _clen, _slen = self.B.build_image(board, ca - 1, cb - 1, na - 1, nb - 1)
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
        raw_value = cpu.mem[self.D3.D_BVL] | (cpu.mem[self.D3.D_BVH] << 8)
        best_value = raw_value if raw_value < 0x8000 else raw_value - 0x10000

        # SECOND ROOT-CAUSE BUG FOUND (exposed only once the tuck-arg-clobber fix above
        # let the off arm genuinely build with EMIT_TUCK_V3=False): build_copro_d3.py
        # gates the TUCK_COL/TUCK_ROW=0xFF sentinel init behind
        # `if EMIT_TUCK or EMIT_TUCK_V3` (its own comment: "Gated so the SHIPPED
        # firmware stays byte-identical -- an unconditional write here moved
        # c87e60a1 to 44a7b37e"), which is a real, load-bearing invariant of the
        # production builder that must not be touched here. That means when
        # EMIT_TUCK_V3 is False, $6139/$613A are NEVER WRITTEN by this image at all --
        # reading them returns whatever py65 initialises unwritten RAM to (observed:
        # 0x00, not 0xFF), which decide() used to misread as a real published tuck
        # descriptor (target=D_BC, approach=0, trigger=0), then either crashed on the
        # ref-enumerator match assert or, worse, could have spuriously matched a real
        # candidate on some board and silently reconstructed a tuck action THE OFF-ARM
        # FIRMWARE NEVER ACTUALLY COMPUTED. Fix: trust the build's own EMIT_TUCK_V3
        # flag (ground truth for "did this image even assemble tuck code") rather than
        # inspecting mailbox bytes that are only meaningfully written when tuck is on.
        if self.B.EMIT_TUCK_V3:
            tuck_col = cpu.mem[0x6139]
            tuck_row = cpu.mem[0x613A]
        else:
            tuck_col = tuck_row = 0xFF

        if d_bo == 0xFF:
            return None    # no legal move at all (matches root_search's `best is None` case)

        if tuck_col == 0xFF:
            action = int(FX._VAR_OF_O4[d_bo]) * 8 + int(d_bc)
            return {"kind": "base", "action": action, "value": best_value,
                    "steps": steps}

        cands, _dropped = ref_tuck_scan_v3(board)
        match = [c for c in cands if c["target"] == d_bc and c["approach"] == tuck_col
                 and c["trigger"] == tuck_row]
        assert match, (
            f"firmware published a tuck descriptor (target={d_bc},approach={tuck_col},"
            f"trigger={tuck_row}) that the python reference enumerator does not "
            f"reproduce on the same board -- this is a REAL divergence between the "
            f"firmware and its reference, not a reconstruction bug; do not paper over it.")
        cand = match[0]
        # candidate_cells (tuck_scan_v3_ref.py) returns (r0,c0,r1,c1) DIRECTLY -- a
        # DIFFERENT function from land_place_at.py's cell_offsets(), which returns flat
        # 0-127 offsets for the REAL 6502 path's LA_OFFA/LA_OFFB zero-page inputs. This
        # function needs row/col pairs for env.board, not flat offsets for the 6502 --
        # candidate_cells is already the right call; the bug was unpacking its 4-tuple
        # as if it were a 2-tuple of flat offsets (confusing the two functions).
        r0, c0, r1, c1 = candidate_cells(cand["target"], cand["rest"], cand["orient"])
        flip = _FLIP[cand["orient"]]
        col0, col1 = (ca, cb) if flip == 0 else (cb, ca)
        placement = {"cells": (r0, c0, r1, c1)}
        return {"kind": "tuck", "placement": placement, "ca": col0, "cb": col1,
                "value": best_value, "steps": steps}
