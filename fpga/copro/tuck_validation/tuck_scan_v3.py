#!/usr/bin/env python3
"""6502 emitter for the tuck v3 multi-candidate, both-orientation enumerator.

Task #17 phase 3 stage 2. Direct, careful port of tuck_scan_v3_ref.py's validated
`ref_tuck_scan_v3` -- the 6502 must agree with it cell-for-cell (same standing as v1's
tuck_scan.py / ref_tuck_scan relationship). Does NOT modify CANON's tuck_scan.py; this is
new, additive code, callable the same way (`emit_tuck_scan_v3(a, live=0x0500)`).

RAM, REVISED (superseded the first draft's allocation -- see commit history for why):
the candidate list needs a 5th field (REST, not just target/approach/trigger/orient --
the first draft omitted it, a real bug: the scoring stage cannot reconstruct a
candidate's landing cells from (target, orient) alone without re-deriving rest via a
second first-occ-style scan, which the design never asked for). At 5B/candidate the
original 16-slot/64B layout doesn't fit the audited free run alongside the extra scratch
horizontal geometry needs -- so:

  - VERTICAL and HORIZONTAL phases run SEQUENTIALLY, never interleaved, so horizontal
    REUSES every one of v1's original scratch bytes (TS_C/TS_FC/TS_A/TS_RA/TS_R/TS_RF/
    TS_OFF/TS_SIDE/TS_FO) instead of needing its own copies -- v1's TS_BEST is unused
    by v3 (no more single-best tracking) and is repurposed as TS_TMP. Only ONE genuinely
    NEW scratch byte is needed: TS_OFF2, the second cell's offset during the horizontal
    fall-loop (which must track TWO columns' occupancy per step, unlike vertical's one).
  - CAPACITY dropped from 16 to 14, matching the ACTUAL measured real-stream maximum
    (decisions_L{11,20}.json, phase 2: max 14/decision at L11, never higher at either
    level) rather than an arbitrary round number. The cap-drop counter (TS_DROP) means
    this is not a silent behaviour change if reality ever exceeds it -- it would show up
    in captures. Matches team-lead rider #1 exactly ("the real stream never hits the cap
    ... this only shapes adversarial behaviour" -- so size the safe/comfortable case for
    reality, not for the enumerator's own worst-case raw output, which the drop counter
    already protects against regardless of the exact number chosen).

RAM MAP (verified against ram_audit.py's dynamic audit, EMIT_TUCK=1+DRCOPRO_ARM=1 --
see commit history for the reconciliation of tuck_scan.py's own "$61A0 used, next used
$61C1" comment: that address (NV_SH in tests/test_delta6502.py) belongs to a SEPARATE,
unwired prototype -- tests/test_resumable_incr.py -- not reachable from build_copro_d3.py's
actual build path, so it does not conflict with this allocation):

  $61A1-$61A6, $61A8-$61AA   reused from v1 (TS_C/TS_FC/TS_A/TS_RA/TS_R/TS_RF/TS_OFF/
                             TS_SIDE/TS_FO -- 9 bytes, same roles both phases)
  $61A7                      TS_TMP (repurposed from v1's now-unused TS_BEST)
  $61AB                      TS_OFF2 (new)
  $61AC-$61F5                CANDLIST: 14 slots x 5B (target, approach, trigger, rest,
                             orient) = 70 bytes
  $61F6                      TS_CNT
  $61F7                      TS_DROP
  $61F8-$61FE                7 bytes spare (comfortable margin, not razor-thin)
"""
from __future__ import annotations

CAPACITY = 14
CANDLIST = 0x61AC              # 14 x 5B: target, approach, trigger, rest, orient
TS_CNT = 0x61F6
TS_DROP = 0x61F7

# reused from tuck_scan.py (v1), same roles, same addresses -- v3 replaces v1's use of them;
# TS_BEST ($61A7) is repurposed as TS_TMP (v3 has no single-best to track)
TS_C, TS_FC, TS_A, TS_RA, TS_R, TS_RF, TS_TMP, TS_OFF, TS_SIDE, TS_FO = (
    0x61A1, 0x61A2, 0x61A3, 0x61A4, 0x61A5, 0x61A6, 0x61A7, 0x61A8, 0x61A9, 0x61AA)
TS_OFF2 = 0x61AB                # new: second cell's offset (horizontal fall-loop only)

ROWS, COLS, EMPTY = 16, 8, 0xFF
# orient encoding, matches tuck_enum.py's ring
H, V, RH, RV = 0, 1, 2, 3


def _far(a, cond, inv, target, tag):
    """Same idiom as tuck_scan.py's _far: invert the condition over a JMP for branches
    that may exceed the 6502's +-127B relative range."""
    a.br(inv, f"{tag}_ok")
    a.jmp(target)
    a.label(f"{tag}_ok")


def emit_tuck_scan_v3(a, live=0x0500):
    """Emit `tuck_scan_v3` plus its own first-occupied scan (owns it, same reason v1
    does -- do not depend on another module's address binding for `live`)."""
    a.label("tuck_scan_v3")
    a.ins("LDA_imm", 0); a.ins16("STA_abs", TS_CNT); a.ins16("STA_abs", TS_DROP)

    # ================================================================ VERTICAL geometry
    a.ins("LDA_imm", 0); a.ins16("STA_abs", TS_C)
    a.label("v3_vcol")
    a.ins16("LDX_abs", TS_C)
    a.jsr("ts3_focc")
    a.ins16("STA_abs", TS_FC)
    a.ins("CMP_imm", 0)
    _far(a, "BEQ", "BNE", "v3_vcnext", "v3vc0")

    a.ins("LDA_imm", 0); a.ins16("STA_abs", TS_SIDE)
    a.label("v3_vside")
    a.ins16("LDA_abs", TS_C); a.ins16("LDX_abs", TS_SIDE)
    a.br("BNE", "v3_vplus")
    a.ins("SEC"); a.ins("SBC_imm", 1)
    _far(a, "BCC", "BCS", "v3_vsnext", "v3vlo")
    a.jmp("v3_vhavea")
    a.label("v3_vplus")
    a.ins("CLC"); a.ins("ADC_imm", 1)
    a.ins("CMP_imm", COLS)
    _far(a, "BCS", "BCC", "v3_vsnext", "v3vhi")
    a.label("v3_vhavea")
    a.ins16("STA_abs", TS_A)

    a.ins16("LDX_abs", TS_A)
    a.jsr("ts3_focc")
    a.ins("CMP_imm", 0)
    _far(a, "BEQ", "BNE", "v3_vsnext", "v3va0")
    a.ins("SEC"); a.ins("SBC_imm", 1)
    a.ins16("STA_abs", TS_RA)

    a.ins16("LDA_abs", TS_FC); a.ins16("STA_abs", TS_R)
    a.label("v3_vrow")
    a.ins16("LDA_abs", TS_R); a.ins16("CMP_abs", TS_RA)
    a.br("BEQ", "v3_vrow_ok")
    _far(a, "BCS", "BCC", "v3_vsnext", "v3vrend")
    a.label("v3_vrow_ok")

    a.ins16("LDA_abs", TS_R)
    a.ins("ASL_A"); a.ins("ASL_A"); a.ins("ASL_A")
    a.ins("CLC"); a.ins16("ADC_abs", TS_C)
    a.ins16("STA_abs", TS_OFF)
    a.ins16("LDX_abs", TS_OFF); a.ins16("LDA_absX", live)
    a.ins("CMP_imm", EMPTY)
    a.br("BNE", "v3_vrnext")

    # TWO-CELL entry check: r==0, or occ(r-1,c) -> reject (top cell has no room to enter)
    a.ins16("LDA_abs", TS_R); a.ins("CMP_imm", 0)
    a.br("BEQ", "v3_vrnext")
    a.ins16("LDA_abs", TS_OFF); a.ins("SEC"); a.ins("SBC_imm", COLS)
    a.ins("TAX"); a.ins16("LDA_absX", live)
    a.ins("CMP_imm", EMPTY)
    a.br("BNE", "v3_vrnext")

    a.ins16("LDA_abs", TS_R); a.ins16("STA_abs", TS_RF)
    a.label("v3_vfall")
    a.ins16("LDA_abs", TS_RF); a.ins("CMP_imm", ROWS - 1)
    a.br("BEQ", "v3_vfall_done")
    a.ins16("LDA_abs", TS_OFF); a.ins("CLC"); a.ins("ADC_imm", COLS)
    a.ins("TAX"); a.ins16("LDA_absX", live)
    a.ins("CMP_imm", EMPTY)
    a.br("BNE", "v3_vfall_done")
    a.ins16("LDA_abs", TS_OFF); a.ins("CLC"); a.ins("ADC_imm", COLS)
    a.ins16("STA_abs", TS_OFF)
    a.ins16("LDA_abs", TS_RF); a.ins("CLC"); a.ins("ADC_imm", 1)
    a.ins16("STA_abs", TS_RF)
    a.jmp("v3_vfall")
    a.label("v3_vfall_done")

    a.ins16("LDA_abs", TS_RF); a.ins16("CMP_abs", TS_FC)
    _far(a, "BCC", "BCS", "v3_vrnext", "v3vsd")

    # TWO-CELL rest check: rf==0, or occ(rf-1,c) -> reject
    a.ins16("LDA_abs", TS_RF); a.ins("CMP_imm", 0)
    a.br("BEQ", "v3_vrnext")
    a.ins16("LDA_abs", TS_RF); a.ins("SEC"); a.ins("SBC_imm", 1)
    a.ins("ASL_A"); a.ins("ASL_A"); a.ins("ASL_A")
    a.ins("CLC"); a.ins16("ADC_abs", TS_C)
    a.ins("TAX"); a.ins16("LDA_absX", live)
    a.ins("CMP_imm", EMPTY)
    a.br("BNE", "v3_vrnext")

    a.jsr("ts3_emit_v")

    a.label("v3_vrnext")
    a.ins16("LDA_abs", TS_R); a.ins("CLC"); a.ins("ADC_imm", 1)
    a.ins16("STA_abs", TS_R)
    a.jmp("v3_vrow")

    a.label("v3_vsnext")
    a.ins16("LDA_abs", TS_SIDE); a.ins("CMP_imm", 1)
    a.br("BEQ", "v3_vcnext")
    a.ins("LDA_imm", 1); a.ins16("STA_abs", TS_SIDE)
    a.jmp("v3_vside")

    a.label("v3_vcnext")
    a.ins16("LDA_abs", TS_C); a.ins("CLC"); a.ins("ADC_imm", 1)
    a.ins16("STA_abs", TS_C)
    a.ins("CMP_imm", COLS)
    # LOGIC-INVERSION BUG (found via py65 differential vs the python reference): the jump
    # condition for "still in range, loop back" is BCC (TS_C < COLS), not BCS. The
    # original BCS version looped back only when TS_C was ALREADY out of range and fell
    # through (exited) while still in range -- terminating both column loops after
    # column 0, silently, for any board whose relevant candidates weren't AT column 0
    # (every board in the first test pass that happened to pass did so by coincidence:
    # its candidates were at column 0). Caught by running the FULL random-board sweep
    # in test_tuck_scan_v3.py, not the hand-picked goldens alone.
    _far(a, "BCC", "BCS", "v3_vcol", "v3vcd")

    # ============================================================== HORIZONTAL geometry
    # Reuses TS_C (now the anchor column), TS_FC (now min(fo(c),fo(c+1))), TS_A, TS_RA,
    # TS_R, TS_RF, TS_OFF (cell0 offset), TS_SIDE -- all the SAME bytes vertical used, safe
    # because the phases never interleave. TS_TMP holds the second first_occ() call's
    # result before the min. TS_OFF2 holds cell1's offset during the fall-loop.
    a.ins("LDA_imm", 0); a.ins16("STA_abs", TS_C)
    a.label("v3_hcol")
    a.ins16("LDX_abs", TS_C)
    a.jsr("ts3_focc"); a.ins16("STA_abs", TS_TMP)       # fo(c)
    a.ins16("LDX_abs", TS_C); a.ins("INX")
    a.jsr("ts3_focc")                                    # fo(c+1)
    a.ins16("CMP_abs", TS_TMP); a.br("BCC", "v3_hmin")
    a.ins16("LDA_abs", TS_TMP)
    a.label("v3_hmin")
    a.ins16("STA_abs", TS_FC)                            # fc = min(fo(c), fo(c+1))
    a.ins("CMP_imm", 0)
    _far(a, "BEQ", "BNE", "v3_hcnext", "v3hc0")

    a.ins("LDA_imm", 0); a.ins16("STA_abs", TS_SIDE)
    a.label("v3_hside")
    a.ins16("LDA_abs", TS_C); a.ins16("LDX_abs", TS_SIDE)
    a.br("BNE", "v3_hplus")
    a.ins("SEC"); a.ins("SBC_imm", 1)
    _far(a, "BCC", "BCS", "v3_hsnext", "v3hlo")
    a.jmp("v3_hhavea")
    a.label("v3_hplus")
    a.ins("CLC"); a.ins("ADC_imm", 1)
    a.ins("CMP_imm", COLS - 1)                           # a+1 must stay < COLS
    _far(a, "BCS", "BCC", "v3_hsnext", "v3hhi")
    a.label("v3_hhavea")
    a.ins16("STA_abs", TS_A)

    a.ins16("LDX_abs", TS_A)
    a.jsr("ts3_focc"); a.ins16("STA_abs", TS_TMP)        # fo(a)
    a.ins16("LDX_abs", TS_A); a.ins("INX")
    a.jsr("ts3_focc")                                     # fo(a+1)
    a.ins16("CMP_abs", TS_TMP); a.br("BCC", "v3_hamin")
    a.ins16("LDA_abs", TS_TMP)
    a.label("v3_hamin")                                   # fa = min(fo(a), fo(a+1))
    a.ins("CMP_imm", 0)
    _far(a, "BEQ", "BNE", "v3_hsnext", "v3ha0")
    a.ins("SEC"); a.ins("SBC_imm", 1)
    a.ins16("STA_abs", TS_RA)

    a.ins16("LDA_abs", TS_FC); a.ins16("STA_abs", TS_R)
    a.label("v3_hrow")
    a.ins16("LDA_abs", TS_R); a.ins16("CMP_abs", TS_RA)
    a.br("BEQ", "v3_hrow_ok")
    _far(a, "BCS", "BCC", "v3_hsnext", "v3hrend")
    a.label("v3_hrow_ok")

    a.ins16("LDA_abs", TS_R)
    a.ins("ASL_A"); a.ins("ASL_A"); a.ins("ASL_A")
    a.ins("CLC"); a.ins16("ADC_abs", TS_C)
    a.ins16("STA_abs", TS_OFF)
    a.ins16("LDX_abs", TS_OFF); a.ins16("LDA_absX", live)
    a.ins("CMP_imm", EMPTY); a.br("BNE", "v3_hrnext")
    a.ins16("LDA_abs", TS_OFF); a.ins("CLC"); a.ins("ADC_imm", 1)
    a.ins("TAX"); a.ins16("LDA_absX", live)
    a.ins("CMP_imm", EMPTY); a.br("BNE", "v3_hrnext")

    a.ins16("LDA_abs", TS_R); a.ins16("STA_abs", TS_RF)
    a.label("v3_hfall")
    a.ins16("LDA_abs", TS_RF); a.ins("CMP_imm", ROWS - 1)
    a.br("BEQ", "v3_hfall_done")
    a.ins16("LDA_abs", TS_OFF); a.ins("CLC"); a.ins("ADC_imm", COLS)
    a.ins16("STA_abs", TS_OFF2)                          # candidate cell0 offset next row
    a.ins("TAX"); a.ins16("LDA_absX", live)
    a.ins("CMP_imm", EMPTY); a.br("BNE", "v3_hfall_done")
    a.ins16("LDA_abs", TS_OFF2); a.ins("CLC"); a.ins("ADC_imm", 1)
    a.ins("TAX"); a.ins16("LDA_absX", live)
    a.ins("CMP_imm", EMPTY); a.br("BNE", "v3_hfall_done")
    a.ins16("LDA_abs", TS_OFF2); a.ins16("STA_abs", TS_OFF)
    a.ins16("LDA_abs", TS_RF); a.ins("CLC"); a.ins("ADC_imm", 1)
    a.ins16("STA_abs", TS_RF)
    a.jmp("v3_hfall")
    a.label("v3_hfall_done")

    a.ins16("LDA_abs", TS_RF); a.ins16("CMP_abs", TS_FC)
    _far(a, "BCC", "BCS", "v3_hrnext", "v3hsd")

    a.jsr("ts3_emit_h")

    a.label("v3_hrnext")
    a.ins16("LDA_abs", TS_R); a.ins("CLC"); a.ins("ADC_imm", 1)
    a.ins16("STA_abs", TS_R)
    a.jmp("v3_hrow")

    a.label("v3_hsnext")
    a.ins16("LDA_abs", TS_SIDE); a.ins("CMP_imm", 1)
    a.br("BEQ", "v3_hcnext")
    a.ins("LDA_imm", 1); a.ins16("STA_abs", TS_SIDE)
    a.jmp("v3_hside")

    a.label("v3_hcnext")
    a.ins16("LDA_abs", TS_C); a.ins("CLC"); a.ins("ADC_imm", 1)
    a.ins16("STA_abs", TS_C)
    a.ins("CMP_imm", COLS - 1)
    _far(a, "BCC", "BCS", "v3_hcol", "v3hcd")   # same inversion fix as v3_vcnext above

    a.ins("RTS")

    # ---- ts3_emit_v: append (target=TS_C, approach=TS_A, trigger=TS_R, rest=TS_RF,
    # orient=V), then RV. TS_TMP carries the orient value across the JSR (free -- unused
    # during the vertical phase's own body).
    a.label("ts3_emit_v")
    a.ins("LDA_imm", V); a.jsr("ts3_append")
    a.ins("LDA_imm", RV); a.jsr("ts3_append")
    a.ins("RTS")

    # ---- ts3_emit_h: append (target=TS_C, approach=TS_A, trigger=TS_R, rest=TS_RF,
    # orient=H), then RH. Same field SOURCES as vertical (TS_C/TS_A/TS_R/TS_RF) since
    # horizontal reuses those bytes -- ts3_append is shared, unmodified, between both.
    a.label("ts3_emit_h")
    a.ins("LDA_imm", H); a.jsr("ts3_append")
    a.ins("LDA_imm", RH); a.jsr("ts3_append")
    a.ins("RTS")

    # ---- ts3_append: A=orient (in). Writes CANDLIST[cnt] = {TS_C,TS_A,TS_R,TS_RF,A}.
    # if cnt >= CAPACITY: INC TS_DROP, return. else write + INC TS_CNT. Shared by both
    # phases -- correct because both leave target/approach/trigger/rest in the SAME four
    # scratch bytes (TS_C/TS_A/TS_R/TS_RF) by construction.
    a.label("ts3_append")
    a.ins16("STA_abs", TS_OFF2)                          # stash orient (TS_OFF2 free here:
                                                          # only live during the fall-loop)
    a.ins16("LDA_abs", TS_CNT); a.ins("CMP_imm", CAPACITY)
    _far(a, "BCC", "BCS", "ts3a_ok", "ts3adr")
    a.ins16("INC_abs", TS_DROP)
    a.ins("RTS")
    a.label("ts3a_ok")
    # X = cnt*5 (5 bytes/candidate): cnt*4 + cnt, via a zp scratch byte for the +cnt term.
    # 0xE6 is primitives.py's own scratch numbering scheme (RV_CELLS/RV_VIR etc. live at
    # 0xE0-0xE1, Z_OFFA/Z_OFFB at 0xDC/0xDE) -- unused by tuck_scan_v3 itself and dead
    # here since this routine runs standalone (no concurrent land_place/resolve_capped
    # call), but NOT safe to assume once this is wired into the search's scoring loop
    # (stage 2 next step) where primitives ARE live concurrently. Flagged for that wiring
    # to re-home this to a tuck-v3-owned byte instead of borrowing primitives' scratch.
    a.ins16("LDA_abs", TS_CNT)
    a.ins("STA_zp", 0xE6)
    a.ins("ASL_A"); a.ins("ASL_A")                       # cnt*4
    a.ins("CLC"); a.ins("ADC_zp", 0xE6)                  # cnt*4 + cnt = cnt*5
    a.ins("TAX")
    a.ins16("LDA_abs", TS_C); a.ins16("STA_absX", CANDLIST + 0)
    a.ins16("LDA_abs", TS_A); a.ins16("STA_absX", CANDLIST + 1)
    a.ins16("LDA_abs", TS_R); a.ins16("STA_absX", CANDLIST + 2)
    a.ins16("LDA_abs", TS_RF); a.ins16("STA_absX", CANDLIST + 3)
    a.ins16("LDA_abs", TS_OFF2); a.ins16("STA_absX", CANDLIST + 4)
    a.ins16("INC_abs", TS_CNT)
    a.ins("RTS")

    # ---- ts3_focc: X=column -> A=row of topmost occupied cell, 16 if empty. Owns its own
    # scan of `live` (see module + v1's tuck_scan docstring for why: address-binding hazard).
    a.label("ts3_focc")
    a.ins("TXA"); a.ins16("STA_abs", TS_FO)
    a.ins("LDY_imm", 0)
    a.label("ts3_fo_lp")
    a.ins16("LDX_abs", TS_FO); a.ins16("LDA_absX", live)
    a.ins("CMP_imm", EMPTY)
    a.br("BNE", "ts3_fo_hit")
    a.ins16("LDA_abs", TS_FO); a.ins("CLC"); a.ins("ADC_imm", COLS)
    a.ins16("STA_abs", TS_FO)
    a.ins("INY"); a.ins("CPY_imm", ROWS)
    a.br("BNE", "ts3_fo_lp")
    a.label("ts3_fo_hit")
    a.ins("TYA"); a.ins("RTS")
