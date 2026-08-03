#!/usr/bin/env python3
"""The same harness as exec_tuck_sim, but with D2 REPAIRED so the executor can be observed.

D2: `patch_cartridge_copro.py` emits the `LDA #$FF / STA TUCK_C2` invalidation at the TOP of
h2_start, BEFORE the pend/delay early-outs.  h2_start runs on every frame with ARMED2 == 0 --
the whole descent -- and handle() precedes act_p2 in the same frame, so mv_p2 always reads
0xFF and the executor is dead code.  Moving the write AFTER the early-outs makes it fire only
when a search actually starts, which is the intended once-per-pill semantics.

★ The fix is applied to the emitter SOURCE IN MEMORY rather than by keeping a patched copy of
a 3000-line file in this tree -- a stale duplicate is exactly the provenance rot this
directory exists to avoid.  If driver-nav's source moves past the anchor the transform
asserts loudly instead of silently measuring the unfixed driver.  The equivalent unified diff
is committed alongside as d2_invalidation_fix.patch, for reading, not for running.
"""
import exec_tuck_sim as E

ANCHOR = '''        a.label(f"{L}_start")            # start a search: upload board+colors to THIS copro, GO
        if TUCK and idx == 2:
            # a new search invalidates any tuck from the PREVIOUS pill. Without this, stale
            # descriptor bytes would steer the next capsule to a pocket that no longer exists
            # -- the same class of bug as the uninitialised PEND/LASTY cold-state defect (P0.3).
            a.ins("LDA_imm", 0xFF); a.ins16("STA_abs", TUCK_C2)
        a.ins16("LDA_abs", pend); a.br("BNE", f"{L}_st1"); a.jmp(f"{L}_done"); a.label(f"{L}_st1")
        a.ins16("LDA_abs", delay); a.br("BEQ", f"{L}_st2"); a.jmp(f"{L}_done"); a.label(f"{L}_st2")
'''

REPLACEMENT = '''        a.label(f"{L}_start")            # start a search: upload board+colors to THIS copro, GO
        a.ins16("LDA_abs", pend); a.br("BNE", f"{L}_st1"); a.jmp(f"{L}_done"); a.label(f"{L}_st1")
        a.ins16("LDA_abs", delay); a.br("BEQ", f"{L}_st2"); a.jmp(f"{L}_done"); a.label(f"{L}_st2")
        if TUCK and idx == 2:
            # D2 FIX CANDIDATE: invalidate only when a search ACTUALLY starts.
            a.ins("LDA_imm", 0xFF); a.ins16("STA_abs", TUCK_C2)
'''


def _fix(src):
    assert ANCHOR in src, (
        "D2 anchor not found in driver-nav/patch_cartridge_copro.py -- the emitter has moved. "
        "Re-derive the fix rather than measuring the unfixed driver. "
        "MOST LIKELY CAUSE (2026-08-02): the real fix landed for real in driver-nav commit "
        "b850159 (task #17 phase 3 stage 1) -- the emitter no longer needs this in-memory "
        "transform at all. This harness going stale is a SIGN THE FIX SHIPPED, not that this "
        "directory rotted; retire this file (and real_ab.py, which imports it) in favour of "
        "measuring driver-nav's patch_cartridge_copro.py directly, the way "
        "qa-harness/experiments/tuck_regression.py's D2/D2b checks already do.")
    return src.replace(ANCHOR, REPLACEMENT)


_m, _code, _lab, _tog = E.build(source_transform=_fix)
TUCK_C2, TUCK_R2, EFF_C2 = _m.TUCK_C2, _m.TUCK_R2, _m.EFF_C2
occupied = E.occupied
ROWS, COLS, EMPTY = E.ROWS, E.COLS, E.EMPTY


def sim(board, best_col, best_orient_raw, tcol, trow, maxf=900):
    return E._sim(_code, _lab, _tog, TUCK_C2, board, best_col, best_orient_raw,
                  tcol, trow, maxf)
