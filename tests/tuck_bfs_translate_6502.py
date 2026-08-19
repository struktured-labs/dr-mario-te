#!/usr/bin/env python3
"""emit_translate: 6502 translation step, tuck_bfs's output arrays -> tuck_v3.py's
CANDLIST format (task #17, next increment after the bit-exact port).

CONTRACT (established by investigation before writing any assembly -- see
tests/translate_ref.py's docstring for the full derivation and
TUCK_BFS_PORT_REPORT.md's translation section).

CANDLIST ($61AC, tuck_v3.CAPACITY=14 slots x 5B: target/approach/trigger/rest/orient) is
consumed by tuck_v3.py's UNCHANGED scoring functions (tuck_cell_prep only reads target/
rest/orient to place cells; tuck_root_extension reads approach/trigger ONLY for the WINNING
candidate, publishing them to TUCK_COL/TUCK_ROW as the driver's physical steering target).
approach/trigger are therefore a REAL execution contract, not passthrough metadata -- this
translation cannot invent them.

tuck_bfs's (target, rest, orient) already IS tuck_scan_v3's geometric candidate identity
(_cells_of(x,y,o) and candidate_cells(target,rest,orient) are the same function). What's
missing is a valid (approach, trigger): a single-adjacent-column, single-row entry point a
real capsule could slide through to reach that exact rest position, in tuck_scan_v3's own
restricted motion vocabulary (adjacent columns only, no multi-step paths) -- NOT every
tuck_bfs candidate has one, precisely because tuck_bfs's fuller reachability model is a
proper superset of tuck_scan_v3's (that's the entire reason it was built). Measured on the
200-board real-L11 corpus: median 36 BFS candidates/board, but only median 2 survive
translation (mean 3.34, max 12, the 14-slot capacity never binds) -- the other ~89% require
genuinely complex multi-step paths this translation is explicitly NOT scoped to express
("translation, not scoring-loop rework" -- surfacing the rest is the wider execution-model
work already flagged as in progress elsewhere, not pre-empted here).

DERIVATION: for each tuck_bfs candidate (already in tuck_bfs's own depth-descending
priority order), try side=target-1 then side=target+1 (matching tuck_scan_v3's own
docstring-declared tie-break order exactly), scanning trigger rows ascending and simulating
the fall, looking for a match on tuck_bfs's own `rest`. Validated bit-exact against
tuck_scan_v3_ref.py's own (uncapped) output on 400 random boards: 0/732 mismatches.

DEFENSIVE REFINEMENT (found necessary, not speculative): tuck_scan_v3's own rule uses only
first_occ(approach) as its row bound -- it does not check that the approach column is
reachable at the shallow trigger row, only that it is *empty* that deep. Found a concrete
board where this over-approximates: scan_v3 claims target=7,rest=5,approach=6,trigger=5 is
valid, but column 6 is only enterable by first passing through column 5's wall, which does
not open until row 8 -- with no Up move, a pill reaching column 6 at all is already past
row 5. Because translation only ever queries this derivation for (target,rest,orient)
tuck_bfs independently proved reachable, that specific failure mode can't leak in through
the target side (this exact key was confirmed absent from tuck_bfs's own reachable set on
that board). As a second line of defense, every found (approach,trigger) is additionally
checked against tuck_bfs's own VISITED bitplane (BFS_VIS is still populated after tuck_bfs
returns; this reuses tb_vis_test verbatim, no new computation) before being accepted. A
candidate whose approach/trigger doesn't verify is dropped, not silently accepted.

MEMORY: no new RAM claims. Writes only into tuck_v3.py's own pre-existing CANDLIST/TS_CNT/
TS_DROP addresses ($61AC/$61F6/$61F7) -- the SAME bytes tuck_scan_v3's own enumerator would
have written, just sourced from tuck_bfs's superset-reachable candidate list instead. New
ZP: $97-$A8 (18 B), starting immediately after tuck_bfs_6502.py's own $81-$96 claim.
"""
import sys
HERE = "/home/struktured/projects/dr-mario-mods"
sys.path.insert(0, HERE + "/tests")
sys.path.insert(0, HERE)
import tuck_bfs_6502 as TB

COPRO = "/home/struktured/projects/dr-mario-canonical-wt/fpga/copro"
if COPRO not in sys.path:
    sys.path.insert(0, COPRO)
import tuck_v3 as TV

EMPTY = TB.EMPTY
LIVE_BOARD = TB.LIVE_BOARD
CANDLIST, TS_CNT, TS_DROP, CAPACITY = TV.CANDLIST, TV.TS_CNT, TV.TS_DROP, TV.CAPACITY
_far = TV._far

(TR_I, TR_TARGET, TR_REST, TR_ORIENT, TR_ISVERT, TR_A, TR_FC, TR_SD, TR_FA, TR_RA,
 TR_R, TR_RF, TR_FOC_X, TR_FOUND, TR_R2, TR_C2, TR_TMP, TR_TMP2) = range(0x97, 0x97 + 18)


# ============================================================== board helpers ===
def _emit_tr_first_occ(a):
    """tr_first_occ: input TR_FOC_X (col) -> A = first occupied row, or 16 if empty.
    Mirrors primitives.py's emit_first_occ (same idiom, self-contained)."""
    a.label("tr_first_occ")
    a.ins("LDA_zp", TR_FOC_X)
    a.ins("STA_zp", TR_TMP)
    a.ins("LDY_imm", 0)
    a.label("tr_fo_loop")
    a.ins("LDX_zp", TR_TMP)
    a.ins16("LDA_absX", LIVE_BOARD)
    a.ins("CMP_imm", EMPTY)
    a.br("BNE", "tr_fo_hit")
    a.ins("LDA_zp", TR_TMP)
    a.ins("CLC"); a.ins("ADC_imm", 8)
    a.ins("STA_zp", TR_TMP)
    a.ins("INY")
    a.ins("CPY_imm", 16)
    a.br("BNE", "tr_fo_loop")
    a.label("tr_fo_hit")
    a.ins("TYA")
    a.ins("RTS")


def _emit_tr_is_empty(a):
    """tr_is_empty: input TR_R2, TR_C2 -> A=1 if that board cell is empty, else 0."""
    a.label("tr_is_empty")
    a.ins("LDA_zp", TR_R2)
    a.ins("ASL_A"); a.ins("ASL_A"); a.ins("ASL_A")
    a.ins("CLC"); a.ins("ADC_zp", TR_C2)
    a.ins("TAX")
    a.ins16("LDA_absX", LIVE_BOARD)
    a.ins("CMP_imm", EMPTY)
    a.br("BEQ", "tr_ie_yes")
    a.ins("LDA_imm", 0)
    a.ins("RTS")
    a.label("tr_ie_yes")
    a.ins("LDA_imm", 1)
    a.ins("RTS")


def _emit_tr_fall_vert(a):
    """tr_fall_vert: input TR_TARGET (col), TR_R (start row) -> TR_RF (final row)."""
    a.label("tr_fall_vert")
    a.ins("LDA_zp", TR_R)
    a.ins("STA_zp", TR_RF)
    a.label("tfv_loop")
    a.ins("LDA_zp", TR_RF)
    a.ins("CMP_imm", 15)
    a.br("BEQ", "tfv_done")
    a.ins("LDA_zp", TR_RF)
    a.ins("CLC"); a.ins("ADC_imm", 1)
    a.ins("ASL_A"); a.ins("ASL_A"); a.ins("ASL_A")
    a.ins("CLC"); a.ins("ADC_zp", TR_TARGET)
    a.ins("TAX")
    a.ins16("LDA_absX", LIVE_BOARD)
    a.ins("CMP_imm", EMPTY)
    a.br("BNE", "tfv_done")
    a.ins("INC_zp", TR_RF)
    a.jmp("tfv_loop")
    a.label("tfv_done")
    a.ins("RTS")


def _emit_tr_fall_horiz(a):
    """tr_fall_horiz: input TR_TARGET (anchor col), TR_R (start row) -> TR_RF."""
    a.label("tr_fall_horiz")
    a.ins("LDA_zp", TR_R)
    a.ins("STA_zp", TR_RF)
    a.label("tfh_loop")
    a.ins("LDA_zp", TR_RF)
    a.ins("CMP_imm", 15)
    a.br("BEQ", "tfh_done")
    a.ins("LDA_zp", TR_RF)
    a.ins("CLC"); a.ins("ADC_imm", 1)
    a.ins("ASL_A"); a.ins("ASL_A"); a.ins("ASL_A")
    a.ins("CLC"); a.ins("ADC_zp", TR_TARGET)
    a.ins("TAX")
    a.ins16("LDA_absX", LIVE_BOARD)
    a.ins("CMP_imm", EMPTY)
    a.br("BNE", "tfh_done")
    a.ins("INX")
    a.ins16("LDA_absX", LIVE_BOARD)
    a.ins("CMP_imm", EMPTY)
    a.br("BNE", "tfh_done")
    a.ins("INC_zp", TR_RF)
    a.jmp("tfh_loop")
    a.label("tfh_done")
    a.ins("RTS")


# ==================================================================== per-side try
def _emit_tr_try_vert(a):
    """tr_try_vert: inputs TR_TARGET, TR_REST, TR_A -> TR_FOUND (0/1), TR_R valid iff
    found. Mirrors translate_ref.derive_vert exactly (fc/sd/fa/ra bounds, entry +
    top-cell-at-entry + top-cell-at-rest checks, row-ascending scan)."""
    a.label("tr_try_vert")
    a.ins("LDA_imm", 0); a.ins("STA_zp", TR_FOUND)
    a.ins("LDA_zp", TR_TARGET); a.ins("STA_zp", TR_FOC_X)
    a.jsr("tr_first_occ"); a.ins("STA_zp", TR_FC)
    a.ins("CMP_imm", 0); a.br("BEQ", "ttv_ret")
    a.ins("SEC"); a.ins("SBC_imm", 1); a.ins("STA_zp", TR_SD)
    a.ins("LDA_zp", TR_A); a.ins("STA_zp", TR_FOC_X)
    a.jsr("tr_first_occ"); a.ins("STA_zp", TR_FA)
    a.ins("CMP_imm", 0); a.br("BEQ", "ttv_ret")
    a.ins("SEC"); a.ins("SBC_imm", 1); a.ins("STA_zp", TR_RA)
    a.ins("LDA_zp", TR_FC); a.ins("STA_zp", TR_R)
    a.label("ttv_rloop")
    a.ins("LDA_zp", TR_R); a.ins("CMP_zp", TR_RA)
    a.br("BEQ", "ttv_rok")
    _far(a, "BCS", "BCC", "ttv_ret", "ttvrend")
    a.label("ttv_rok")
    a.ins("LDA_zp", TR_R); a.ins("STA_zp", TR_R2)
    a.ins("LDA_zp", TR_TARGET); a.ins("STA_zp", TR_C2)
    a.jsr("tr_is_empty")
    a.ins("CMP_imm", 1)
    a.br("BNE", "ttv_rnext")
    a.ins("LDA_zp", TR_R)
    a.br("BEQ", "ttv_topok1")
    a.ins("SEC"); a.ins("SBC_imm", 1); a.ins("STA_zp", TR_R2)
    a.ins("LDA_zp", TR_TARGET); a.ins("STA_zp", TR_C2)
    a.jsr("tr_is_empty")
    a.ins("CMP_imm", 1)
    a.br("BNE", "ttv_rnext")
    a.label("ttv_topok1")
    a.jsr("tr_fall_vert")
    a.ins("LDA_zp", TR_RF); a.ins("CMP_zp", TR_REST)
    a.br("BNE", "ttv_rnext")
    a.ins("LDA_zp", TR_RF); a.ins("CMP_zp", TR_SD)
    a.br("BEQ", "ttv_rnext")
    a.br("BCC", "ttv_rnext")
    a.ins("LDA_zp", TR_RF)
    a.br("BEQ", "ttv_restok")
    a.ins("SEC"); a.ins("SBC_imm", 1); a.ins("STA_zp", TR_R2)
    a.ins("LDA_zp", TR_TARGET); a.ins("STA_zp", TR_C2)
    a.jsr("tr_is_empty")
    a.ins("CMP_imm", 1)
    a.br("BNE", "ttv_rnext")
    a.label("ttv_restok")
    a.ins("LDA_imm", 1); a.ins("STA_zp", TR_FOUND)
    a.ins("RTS")
    a.label("ttv_rnext")
    a.ins("INC_zp", TR_R)
    a.jmp("ttv_rloop")
    a.label("ttv_ret")
    a.ins("RTS")


def _emit_tr_try_horiz(a):
    """tr_try_horiz: inputs TR_TARGET, TR_REST, TR_A -> TR_FOUND (0/1), TR_R valid iff
    found. Mirrors translate_ref.derive_horiz. Guards TR_A==7 up front (the two-cell
    approach check needs column TR_A+1, which would read past LIVE_BOARD's 128-byte
    array into unmapped territory for TR_A==7 -- tuck_bfs's own candidates never have
    TR_TARGET==7 for horizontal geometry (is_legal caps target at 6), but TR_A=target+1
    can still be 7, so this bound is real and load-bearing, not defensive-only)."""
    a.label("tr_try_horiz")
    a.ins("LDA_imm", 0); a.ins("STA_zp", TR_FOUND)
    a.ins("LDA_zp", TR_A); a.ins("CMP_imm", 7)
    a.br("BNE", "tth_aok")
    a.ins("RTS")
    a.label("tth_aok")
    # fc = min(first_occ(target), first_occ(target+1)). NOTE: the first result must be
    # stashed in TR_TMP2, NOT TR_TMP -- tr_first_occ uses TR_TMP as its OWN internal
    # offset-walking scratch, so a second nested call clobbers TR_TMP before the min
    # comparison runs (found via py65: this exact bug produced FC=11 instead of 6 on a
    # real corpus board -- see TUCK_BFS_PORT_REPORT.md's translation section).
    a.ins("LDA_zp", TR_TARGET); a.ins("STA_zp", TR_FOC_X)
    a.jsr("tr_first_occ"); a.ins("STA_zp", TR_TMP2)
    a.ins("LDA_zp", TR_TARGET); a.ins("CLC"); a.ins("ADC_imm", 1); a.ins("STA_zp", TR_FOC_X)
    a.jsr("tr_first_occ")
    a.ins("CMP_zp", TR_TMP2)
    a.br("BCC", "th_fcs")
    a.ins("LDA_zp", TR_TMP2)
    a.label("th_fcs")
    a.ins("STA_zp", TR_FC)
    a.ins("CMP_imm", 0); a.br("BEQ", "tth_ret")
    a.ins("SEC"); a.ins("SBC_imm", 1); a.ins("STA_zp", TR_SD)
    # fa = min(first_occ(approach), first_occ(approach+1)) -- same TR_TMP2 fix.
    a.ins("LDA_zp", TR_A); a.ins("STA_zp", TR_FOC_X)
    a.jsr("tr_first_occ"); a.ins("STA_zp", TR_TMP2)
    a.ins("LDA_zp", TR_A); a.ins("CLC"); a.ins("ADC_imm", 1); a.ins("STA_zp", TR_FOC_X)
    a.jsr("tr_first_occ")
    a.ins("CMP_zp", TR_TMP2)
    a.br("BCC", "th_fas")
    a.ins("LDA_zp", TR_TMP2)
    a.label("th_fas")
    a.ins("CMP_imm", 0); a.br("BEQ", "tth_ret")
    a.ins("SEC"); a.ins("SBC_imm", 1); a.ins("STA_zp", TR_RA)
    a.ins("LDA_zp", TR_FC); a.ins("STA_zp", TR_R)
    a.label("tth_rloop")
    a.ins("LDA_zp", TR_R); a.ins("CMP_zp", TR_RA)
    a.br("BEQ", "tth_rok")
    _far(a, "BCS", "BCC", "tth_ret", "tthrend")
    a.label("tth_rok")
    a.ins("LDA_zp", TR_R); a.ins("STA_zp", TR_R2)
    a.ins("LDA_zp", TR_TARGET); a.ins("STA_zp", TR_C2)
    a.jsr("tr_is_empty")
    a.ins("CMP_imm", 1)
    a.br("BNE", "tth_rnext")
    a.ins("LDA_zp", TR_R); a.ins("STA_zp", TR_R2)
    a.ins("LDA_zp", TR_TARGET); a.ins("CLC"); a.ins("ADC_imm", 1); a.ins("STA_zp", TR_C2)
    a.jsr("tr_is_empty")
    a.ins("CMP_imm", 1)
    a.br("BNE", "tth_rnext")
    a.jsr("tr_fall_horiz")
    a.ins("LDA_zp", TR_RF); a.ins("CMP_zp", TR_REST)
    a.br("BNE", "tth_rnext")
    a.ins("LDA_zp", TR_RF); a.ins("CMP_zp", TR_SD)
    a.br("BEQ", "tth_rnext")
    a.br("BCC", "tth_rnext")
    a.ins("LDA_imm", 1); a.ins("STA_zp", TR_FOUND)
    a.ins("RTS")
    a.label("tth_rnext")
    a.ins("INC_zp", TR_R)
    a.jmp("tth_rloop")
    a.label("tth_ret")
    a.ins("RTS")


# ============================================================ derive + verify ===
def _emit_tr_derive(a):
    """tr_derive: inputs TR_TARGET, TR_REST, TR_ORIENT, TR_ISVERT -> TR_FOUND (0/1),
    TR_A/TR_R valid iff found. Tries side=target-1 then side=target+1 (matching
    tuck_scan_v3's own tie-break order), and on a geometric match, cross-checks
    (TR_A, TR_R, TR_ORIENT) against tuck_bfs's own VISITED plane via tb_vis_test
    before accepting."""
    a.label("tr_derive")
    a.ins("LDA_imm", 0); a.ins("STA_zp", TR_FOUND)
    a.ins("LDA_zp", TR_TARGET)
    a.br("BEQ", "td_try2")
    a.ins("SEC"); a.ins("SBC_imm", 1); a.ins("STA_zp", TR_A)
    a.jsr("td_try_and_verify")
    a.ins("LDA_zp", TR_FOUND)
    a.br("BNE", "td_ret")
    a.label("td_try2")
    a.ins("LDA_zp", TR_TARGET); a.ins("CMP_imm", 7)
    a.br("BEQ", "td_ret")
    a.ins("CLC"); a.ins("ADC_imm", 1); a.ins("STA_zp", TR_A)
    a.jsr("td_try_and_verify")
    a.label("td_ret")
    a.ins("RTS")

    a.label("td_try_and_verify")
    a.ins("LDA_zp", TR_ISVERT)
    a.br("BEQ", "tdav_horiz")
    a.jsr("tr_try_vert")
    a.jmp("tdav_check")
    a.label("tdav_horiz")
    a.jsr("tr_try_horiz")
    a.label("tdav_check")
    a.ins("LDA_zp", TR_FOUND)
    a.br("BEQ", "tdav_ret")
    a.ins("LDA_zp", TR_R)
    a.ins("ASL_A"); a.ins("ASL_A")
    a.ins("STA_zp", TB.VB_ROWBASE)
    a.ins("LDA_zp", TR_A)
    a.ins("ASL_A"); a.ins("ASL_A")
    a.ins("CLC"); a.ins("ADC_zp", TR_ORIENT)
    a.ins("STA_zp", TB.VB_S)
    a.jsr("tb_vis_test")
    a.ins("CMP_imm", 1)
    a.br("BEQ", "tdav_ret")
    a.ins("LDA_imm", 0); a.ins("STA_zp", TR_FOUND)
    a.label("tdav_ret")
    a.ins("RTS")


# ============================================================= top-level entry ===
def _emit_tr_translate(a):
    """tr_translate: call AFTER tuck_bfs. Walks BFS_OUT_X/Y/O[0..BFS_OUTN-1] in
    tuck_bfs's own depth-descending priority order, translating each into a CANDLIST
    entry when tr_derive finds a verified descriptor, stopping early once CAPACITY
    entries are written (no point scanning further candidates once CANDLIST is full).
    Sets TS_CNT (entries written) and TS_DROP (candidates that didn't make it, either
    for lacking a verified descriptor or for arriving after the cap)."""
    a.label("tr_translate")
    a.ins("LDA_imm", 0)
    a.ins16("STA_abs", TS_CNT)
    a.ins16("STA_abs", TS_DROP)
    a.ins("STA_zp", TR_I)
    a.label("trt_loop")
    a.ins("LDA_zp", TR_I); a.ins("CMP_zp", TB.BFS_OUTN)
    a.br("BEQ", "trt_done")
    a.ins("LDX_zp", TR_I)
    a.ins16("LDA_absX", TB.BFS_OUT_X); a.ins("STA_zp", TR_TARGET)
    a.ins16("LDA_absX", TB.BFS_OUT_Y); a.ins("STA_zp", TR_REST)
    a.ins16("LDA_absX", TB.BFS_OUT_O); a.ins("STA_zp", TR_ORIENT)
    a.ins("LDA_zp", TR_ORIENT); a.ins("AND_imm", 1); a.ins("STA_zp", TR_ISVERT)
    a.jsr("tr_derive")
    a.ins("LDA_zp", TR_FOUND)
    a.br("BEQ", "trt_dropped")
    a.ins16("LDA_abs", TS_CNT); a.ins("CMP_imm", CAPACITY)
    a.br("BCC", "trt_room")
    a.ins16("INC_abs", TS_DROP)
    a.jmp("trt_done")
    a.label("trt_room")
    a.ins16("LDA_abs", TS_CNT)
    a.ins("ASL_A"); a.ins("ASL_A")
    a.ins("CLC"); a.ins16("ADC_abs", TS_CNT)
    a.ins("TAX")
    a.ins("LDA_zp", TR_TARGET); a.ins16("STA_absX", CANDLIST + 0)
    a.ins("LDA_zp", TR_A); a.ins16("STA_absX", CANDLIST + 1)
    a.ins("LDA_zp", TR_R); a.ins16("STA_absX", CANDLIST + 2)
    a.ins("LDA_zp", TR_REST); a.ins16("STA_absX", CANDLIST + 3)
    a.ins("LDA_zp", TR_ORIENT); a.ins16("STA_absX", CANDLIST + 4)
    a.ins16("INC_abs", TS_CNT)
    a.jmp("trt_next")
    a.label("trt_dropped")
    a.ins16("INC_abs", TS_DROP)
    a.label("trt_next")
    a.ins("INC_zp", TR_I)
    a.jmp("trt_loop")
    a.label("trt_done")
    a.ins("RTS")


def emit_translate(a):
    _emit_tr_first_occ(a)
    _emit_tr_is_empty(a)
    _emit_tr_fall_vert(a)
    _emit_tr_fall_horiz(a)
    _emit_tr_try_vert(a)
    _emit_tr_try_horiz(a)
    _emit_tr_derive(a)
    _emit_tr_translate(a)


def build_combined(base=0x8000):
    a = TB.build(base)
    emit_translate(a)
    return a


if __name__ == "__main__":
    a = build_combined()
    code = a.assemble()
    print(f"tuck_bfs+translate assembled: {len(code)} bytes @ ${a.base:04X}, "
          f"{len(a.labels)} labels")
