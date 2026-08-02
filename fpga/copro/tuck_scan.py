#!/usr/bin/env python3
"""6502 TUCK ENUMERATOR for the copro firmware -- the search half of the tuck executor.

Publishes the descriptor the driver's executor reads:
    TUCK_COL ($6139 -> cart $5087) = approach column, 0xFF = no tuck this pill
    TUCK_ROW ($613A -> cart $5088) = trigger row; the executor steers to TUCK_COL while
                                     the capsule is above this row and to best_col at/below

MOTION MODEL -- must match the executor EXACTLY, no more and no less. The executor makes
ONE horizontal switch, at a configurable trigger row:

    fall in approach column `a`, switch to target column `c` at ANY row `r` the capsule
    passes through, then fall straight down in `c`.

★ Getting this wrong in the PERMISSIVE direction is the dangerous one: publishing a tuck
the executor cannot perform makes the capsule steer to an approach column, miss the
target, and land somewhere the search never scored -- strictly worse than no tuck. (An
over-RESTRICTIVE model merely leaves value on the table; my first offline model did that
and turned a real -5.20 pills into a false WASH.)

ALGORITHM, using primitives that already exist (first_occ reads the LIVE settled board):

    for target column c:
        fc = first_occ(c)            # topmost occupied row, 16 if empty
        sd = fc - 1                  # deepest row a STRAIGHT drop into c reaches
        for approach a in {c-1, c+1}:
            ra = first_occ(a) - 1    # deepest row the capsule can occupy in a
            for r = fc .. ra:        # rows strictly deeper than the straight drop
                if board[r*8+c] != EMPTY: continue      # cannot enter c at this row
                rf = r; while rf+1 < 16 and board[(rf+1)*8+c] == EMPTY: rf += 1
                if rf > sd: candidate(approach=a, trigger=r, rest=rf)

Selection: DEEPEST rest row wins (ties -> first found). Depth is the right proxy here --
a tuck is worth taking precisely because it reaches under an overhang, and the driver
still takes its DESTINATION column from best_col, so this only chooses among cells the
straight-drop search could not reach at all.

Scratch lives at $61A1+ (free block: $61A0 is used, next used is $61C1) so it cannot
collide with search state in zero page.
"""

ROWS, COLS = 16, 8
EMPTY = 0xFF
TUCK_COL, TUCK_ROW = 0x6139, 0x613A

# scratch ($61A1-$61C0 is free)
TS_C     = 0x61A1   # target column
TS_FC    = 0x61A2   # first_occ(c)
TS_A     = 0x61A3   # approach column
TS_RA    = 0x61A4   # deepest row reachable in the approach column
TS_R     = 0x61A5   # candidate trigger row
TS_RF    = 0x61A6   # rest row after falling in c from r
TS_BEST  = 0x61A7   # best (deepest) rest row seen; 0xFF = none yet
TS_OFF   = 0x61A8   # board offset scratch
TS_SIDE  = 0x61A9   # 0 = a is c-1, 1 = a is c+1
TS_FO    = 0x61AA   # ts_focc working offset


def _far(a, cond, inv, target, tag):
    """Branch to a FAR label: invert the condition over a JMP.

    The 6502's relative branches only reach +-127 B and this routine is ~200 B, so several
    of these exceed range. The assembler asserts on out-of-range rather than emitting a
    wrong offset -- which is the same bug class that once shipped a `BCC +3` landing on a
    JMP -- so every long branch is written explicitly as invert-and-jump.
    """
    a.br(inv, f"{tag}_ok")
    a.jmp(target)
    a.label(f"{tag}_ok")


def emit_tuck_scan(a, first_occ_label=None, live=0x0500):
    """Emit `tuck_scan` plus its OWN first-occupied scan. Clobbers A/X/Y and $61A1+.

    ★ It emits its own scanner ON PURPOSE and ignores `first_occ_label`. The depth-3 search
    REBINDS primitives.LIVE_BOARD to $0700 (CUR, its per-node working board) before emitting,
    so the shared `first_occ` in that image disassembles to `LDA $0700,X`. Calling it here
    returned "row 0 occupied" for every column -- reading the search's scratch, not the
    settled playfield -- and the enumerator silently published "no tuck" on every board.
    A standalone test did NOT catch this because it emitted first_occ itself with primitives
    unmodified. Depending on another module's ADDRESS BINDING is the hazard; owning the 20
    bytes removes it.
    """
    a.label("tuck_scan")
    a.ins("LDA_imm", 0xFF)
    a.ins16("STA_abs", TUCK_COL)
    a.ins16("STA_abs", TUCK_ROW)
    a.ins16("STA_abs", TS_BEST)                    # 0xFF = no candidate yet
    a.ins("LDA_imm", 0)
    a.ins16("STA_abs", TS_C)

    # ---------------- for each target column c ----------------
    a.label("ts_col")
    a.ins16("LDX_abs", TS_C)
    a.jsr("ts_focc")                                # A = first occupied row in c
    a.ins16("STA_abs", TS_FC)
    # a column that is occupied at row 0 has no straight drop AND no way in; skip it
    a.ins("CMP_imm", 0)
    _far(a, "BEQ", "BNE", "ts_cnext", "ts_c0")

    a.ins("LDA_imm", 0)
    a.ins16("STA_abs", TS_SIDE)

    # ---------------- for each approach side ----------------
    a.label("ts_side")
    a.ins16("LDA_abs", TS_C)
    a.ins16("LDX_abs", TS_SIDE)
    a.br("BNE", "ts_plus")
    a.ins("SEC"); a.ins("SBC_imm", 1)               # a = c - 1
    _far(a, "BCC", "BCS", "ts_snext", "ts_lo")      # underflow -> no left neighbour
    a.jmp("ts_have_a")
    a.label("ts_plus")
    a.ins("CLC"); a.ins("ADC_imm", 1)               # a = c + 1
    a.ins("CMP_imm", COLS)
    _far(a, "BCS", "BCC", "ts_snext", "ts_hi")      # >= COLS -> no right neighbour
    a.label("ts_have_a")
    a.ins16("STA_abs", TS_A)

    a.ins16("LDX_abs", TS_A)
    a.jsr("ts_focc")                                # A = first occupied row in a
    a.ins("CMP_imm", 0)
    _far(a, "BEQ", "BNE", "ts_snext", "ts_a0")      # approach col blocked at the top
    a.ins("SEC"); a.ins("SBC_imm", 1)               # ra = first_occ(a) - 1
    a.ins16("STA_abs", TS_RA)

    # r starts at fc (= sd+1, the first row deeper than the straight drop)
    a.ins16("LDA_abs", TS_FC)
    a.ins16("STA_abs", TS_R)

    # ---------------- for r = fc .. ra ----------------
    a.label("ts_row")
    a.ins16("LDA_abs", TS_R)
    a.ins16("CMP_abs", TS_RA)
    a.br("BEQ", "ts_row_ok")                        # r == ra is in range
    _far(a, "BCS", "BCC", "ts_snext", "ts_rend")    # r > ra -> done this side
    a.label("ts_row_ok")

    # offset = r*8 + c
    a.ins16("LDA_abs", TS_R)
    a.ins("ASL_A"); a.ins("ASL_A"); a.ins("ASL_A")  # r*8 (rows 0-15 -> max 120, no carry)
    a.ins("CLC"); a.ins16("ADC_abs", TS_C)
    a.ins16("STA_abs", TS_OFF)

    a.ins16("LDX_abs", TS_OFF)
    a.ins16("LDA_absX", live)
    a.ins("CMP_imm", EMPTY)
    a.br("BNE", "ts_rnext")                         # cannot enter c at this row

    # rf = r; fall while the cell BELOW is empty
    a.ins16("LDA_abs", TS_R)
    a.ins16("STA_abs", TS_RF)
    a.label("ts_fall")
    a.ins16("LDA_abs", TS_RF)
    a.ins("CMP_imm", ROWS - 1)
    a.br("BEQ", "ts_fall_done")                     # already on the floor
    a.ins16("LDA_abs", TS_OFF)
    a.ins("CLC"); a.ins("ADC_imm", COLS)            # offset of the cell below
    a.ins("TAX")
    a.ins16("LDA_absX", live)
    a.ins("CMP_imm", EMPTY)
    a.br("BNE", "ts_fall_done")
    a.ins("TXA"); a.ins16("STA_abs", TS_OFF)        # descend
    a.ins16("LDA_abs", TS_RF); a.ins("CLC"); a.ins("ADC_imm", 1)
    a.ins16("STA_abs", TS_RF)
    a.jmp("ts_fall")
    a.label("ts_fall_done")

    # keep it only if strictly deeper than the straight drop: rf > sd, i.e. rf >= fc
    a.ins16("LDA_abs", TS_RF)
    a.ins16("CMP_abs", TS_FC)
    a.br("BCC", "ts_rnext")                         # rf < fc -> not deeper

    # deepest-wins. TS_BEST starts 0xFF, so treat 0xFF as "none".
    a.ins16("LDA_abs", TS_BEST)
    a.ins("CMP_imm", 0xFF)
    a.br("BEQ", "ts_take")                          # nothing yet -> take it
    a.ins16("LDA_abs", TS_RF)
    a.ins16("CMP_abs", TS_BEST)
    a.br("BCC", "ts_rnext")                         # rf < best -> keep old
    a.br("BEQ", "ts_rnext")                         # equal -> keep first found
    a.label("ts_take")
    a.ins16("LDA_abs", TS_RF); a.ins16("STA_abs", TS_BEST)
    a.ins16("LDA_abs", TS_A);  a.ins16("STA_abs", TUCK_COL)
    a.ins16("LDA_abs", TS_R);  a.ins16("STA_abs", TUCK_ROW)

    a.label("ts_rnext")
    a.ins16("LDA_abs", TS_R); a.ins("CLC"); a.ins("ADC_imm", 1)
    a.ins16("STA_abs", TS_R)
    a.jmp("ts_row")

    a.label("ts_snext")
    a.ins16("LDA_abs", TS_SIDE)
    a.ins("CMP_imm", 1)
    a.br("BEQ", "ts_cnext")
    a.ins("LDA_imm", 1); a.ins16("STA_abs", TS_SIDE)
    a.jmp("ts_side")

    a.label("ts_cnext")
    a.ins16("LDA_abs", TS_C); a.ins("CLC"); a.ins("ADC_imm", 1)
    a.ins16("STA_abs", TS_C)
    a.ins("CMP_imm", COLS)
    a.br("BCS", "ts_done")
    a.jmp("ts_col")

    a.label("ts_done")
    a.ins("RTS")

    # ---- ts_focc: X = column -> A = row of the topmost occupied cell, 16 if empty.
    # Reads `live` explicitly so it cannot be re-bound by whatever else shares the image.
    a.label("ts_focc")
    a.ins("STX_abs" if False else "TXA")
    a.ins16("STA_abs", TS_FO)
    a.ins("LDY_imm", 0)
    a.label("ts_fo_lp")
    a.ins16("LDX_abs", TS_FO)
    a.ins16("LDA_absX", live)
    a.ins("CMP_imm", EMPTY)
    a.br("BNE", "ts_fo_hit")
    a.ins16("LDA_abs", TS_FO); a.ins("CLC"); a.ins("ADC_imm", COLS)
    a.ins16("STA_abs", TS_FO)
    a.ins("INY"); a.ins("CPY_imm", ROWS)
    a.br("BNE", "ts_fo_lp")
    a.label("ts_fo_hit")
    a.ins("TYA"); a.ins("RTS")


# ---------------------------------------------------------------- python reference
def ref_tuck_scan(board):
    """Same algorithm in Python. The 6502 must agree with this cell-for-cell."""
    def occ(r, c):
        return board[r * COLS + c] != EMPTY

    def first_occ(c):
        for r in range(ROWS):
            if occ(r, c):
                return r
        return ROWS

    best = None          # (rest_row, approach, trigger)
    for c in range(COLS):
        fc = first_occ(c)
        if fc == 0:
            continue
        sd = fc - 1
        for side in (0, 1):
            a = c - 1 if side == 0 else c + 1
            if not (0 <= a < COLS):
                continue
            fa = first_occ(a)
            if fa == 0:
                continue
            ra = fa - 1
            r = fc
            while r <= ra:
                if not occ(r, c):
                    rf = r
                    while rf < ROWS - 1 and not occ(rf + 1, c):
                        rf += 1
                    if rf > sd:
                        if best is None or rf > best[0]:
                            best = (rf, a, r)
                r += 1
    if best is None:
        return (0xFF, 0xFF)
    return (best[1], best[2])
