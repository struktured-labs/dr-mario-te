#!/usr/bin/env python3
"""emit_tuck_bfs: 6502 port of the converged TE-free tuck enumerator (task #17,
stage 4 -- "THE CONVERGENCE ANSWER" in TUCK_V3_FIRMWARE_SAGA.md).

ALGORITHM. The reference (dr-mario-qa-wt/experiments/tuck_enum.py, mode="free")
is meatfighter's reachability BFS over states (x, y, orient): Left/Right/Down/
Rotate are unit-cost edges, no clock.  This file does NOT reproduce that BFS's
traversal directly (a FIFO work-queue would need an index up to 511, which
does not fit an 8-bit 6502 index register in a single absolute,X access).

Instead it exploits a structural fact about the move set: Down is the ONLY
move that changes row y, and it always INCREASES y (there is no Up).  Left,
Right and Rotate all preserve y.  So the reachable set can be computed
ROW-MAJOR: close row y under Left/Right/Rotate to a local fixed point (only
8 cols x 4 orients = 32 states -- an 8-bit index), THEN push Down into row
y+1, then repeat for y+1.  This is proved equivalent to the reference BFS's
full reachable set in tests/proto_rowbfs.py (500/500 random boards + the cave-
board regression, zero diffs) BEFORE any 6502 was written -- see that file's
docstring for the argument (row-monotonicity of the move graph: Down is the
only edge that changes y and it only ever increases it, so once row y's
Left/Right/Rotate closure is complete, nothing discovered later can ever
feed back into row y).

Both phases are then a single linear pass over the 512-bit VISITED plane in
the SAME (y, x, orient) order used by both this routine and the reference
comparison harness, which is what gives a canonical output order for the
bit-exact gate (see test_tuck_bfs_6502.py) without needing to replicate the
reference's own BFS discovery order (which this port does not attempt to
match -- only the discovered SET has to match, and set membership here is
provably order-independent; see the docstring argument above).

INPUT.  Board occupancy is read from LIVE_BOARD ($0500, primitives.py's own
convention: 128 bytes row-major, EMPTY=$FF, occupied tile's low nibble is the
colour) -- the same convention first_occ/emit_kernel_wc already read.  This
routine never writes to $0500.  PILL_A/PILL_B ($84/$85) are accepted as
documented mailbox-shaped inputs for interface parity with the eventual
firmware wiring, but are NOT read by the BFS -- legality depends only on
occupancy (colours never gate a placement), which is exactly what makes a
geometry-only enumerator correct in the first place.

OUTPUT.  BFS_OUTN ($83) = candidate count (capped at OUT_CAP=128, far above
the measured max of 54/board over 3000 synthetic boards -- see
TUCK_BFS_PORT_REPORT.md for the histogram).  OUT_X/OUT_Y/OUT_O (each 128
bytes) hold one (x, y, orient) triple per candidate, in ascending
(y, x, orient) order.  Cells are the deterministic function of (x, y, orient)
tuck_enum._cells_of uses: H/RH -> (y,x,y,x+1); V/RV -> (y-1,x,y,x).  Colours
are not emitted (they don't affect the reachable SET the bit-exact gate
checks; a downstream consumer applies tuck_enum._FLIP the same way tuck_enum
itself does).

MEMORY MAP -- PLACEHOLDER, flagged for confirmation before firmware
integration (task instructions: use a clearly-marked placeholder if free
addresses can't be independently confirmed).  Checked against every address
test_search_d3.py + primitives.py declare in this tree as of 2026-08-04:
LIVE=$0500-$057F, WORK1=$0600, CUR/MARK=$0700/$0780, TK=$0900-$09FF,
TK1=$0A00-$0A7F, WORK2=$0B00, DBG_RING=$0C00, DBG_RING2=$0D00, LEV_*=$70xx
(copro RTL I/O window).  $0E00-$0FFF is undocumented by any of those -- this
routine claims 448 of those 512 bytes.  Zero page: the d3 search's own map
(test_search_d3.py) ends at D_STR/D_P1L/D_P1H = $70-$72; this routine claims
$73-$86 (20 of a reserved $73-$8F, 29-byte block) starting immediately after.
NEITHER claim has been cross-checked against v18/v19 AI (patch_vs_cpu.py) ZP
usage ($00-$01, $6B-$6F, $CA-$E1) beyond eyeballing -- those routines are not
believed to run in the same build as the d3 search, but this needs an
explicit owner sign-off before the port is wired into a real firmware image.

    BFS_VIS  = $0E00  (64 B)   512-bit visited plane; state (x,y,o) -> bit
                                idx=y*32+x*4+o; byte=idx>>3, bit=idx&7. Row y
                                owns exactly bytes [y*4 .. y*4+3] (32 bits),
                                which is what makes the row-fixed-point phase
                                indexable by an 8-bit offset without ever
                                touching X>63.
    BFS_OUT_X = $0E40 (128 B)  candidate x, index 0..BFS_OUTN-1
    BFS_OUT_Y = $0EC0 (128 B)  candidate y
    BFS_OUT_O = $0F40 (128 B)  candidate orient (0=H,1=V,2=RH,3=RV)

    ZP $73 BFS_Y        current row (both phases)
       $74 BFS_S        current state-in-row, 0..31 (both phases)
       $75 BFS_X        decoded col  (=BFS_S>>2)
       $76 BFS_O        decoded orient (=BFS_S&3)
       $77 BFS_CHANGED  row fixed-point: did this pass mark anything new?
       $78 RT_TX        rotation kick scratch (post right-wall-clamp col)
       $79 IL_X / $7A IL_Y / $7B IL_O     is_legal() inputs
       $7C VB_ROWBASE / $7D VB_S          vis-bit inputs (rowbase=y*4)
       $7E VB_BYTEIDX / $7F VB_MASK       vis-bit scratch/outputs
       $80 CM_X / $81 CM_Y / $82 CM_O     check_and_mark() inputs
       $83 BFS_OUTN     output candidate count
       $84 PILL_A / $85 PILL_B            interface inputs, unread by the BFS
       $86 PASS_CNT     row fixed-point pass counter (must NOT alias RT_TX --
                         row_step's rotation blocks clobber RT_TX on every
                         call made from inside the pass loop's state scan)

ORIENTATION RING -- identical to tuck_enum.py: H=0, V=1, RH=2, RV=3;
is_h(o) = (o & 1) == 0.  Anchor = left cell (H/RH) or bottom cell (V/RV),
matching _cells_of.  Rotation right-wall clamp and the single left-kick
(no right/floor/up kick) are ported verbatim from _bfs_free's enq().

REGISTER DISCIPLINE. No subroutine here relies on X or Y surviving a JSR --
every loop variable that must outlive a call (BFS_Y, BFS_S, PASS_CNT, ...)
lives in zero page and is reloaded into X/Y fresh after each call.
"""
import sys
HERE = "/home/struktured/projects/dr-mario-mods"
sys.path.insert(0, HERE + "/tests")
sys.path.insert(0, HERE)
from patch_vs_cpu import Asm6502
import patch_vs_cpu
patch_vs_cpu.OPS.setdefault("PHA", 0x48)
patch_vs_cpu.OPS.setdefault("PLA", 0x68)
import primitives as PRIM

ROWS, COLS = 16, 8
EMPTY = 0xFF
LIVE_BOARD = PRIM.LIVE_BOARD   # $0500, read-only input

# ---- placeholder memory map (see module docstring) -------------------------
BFS_VIS = 0x0E00
BFS_OUT_X, BFS_OUT_Y, BFS_OUT_O = 0x0E40, 0x0EC0, 0x0F40
OUT_CAP = 128

(BFS_Y, BFS_S, BFS_X, BFS_O, BFS_CHANGED, RT_TX,
 IL_X, IL_Y, IL_O, VB_ROWBASE, VB_S, VB_BYTEIDX, VB_MASK,
 CM_X, CM_Y, CM_O, BFS_OUTN, PILL_A, PILL_B, PASS_CNT) = range(0x73, 0x73 + 20)

ROW_PASS_CAP = 40   # hard safety bound on the row fixed-point loop; the true
                    # ceiling is 32 (can't discover more than the row's 32
                    # states); measured max over 300 synthetic boards was 4.

_IS_H = (True, False, True, False)   # H, V, RH, RV


# ============================================================== is_legal ===
def _emit_is_legal(a):
    """is_legal: inputs IL_X/IL_Y/IL_O -> A=1 legal, A=0 illegal.
    Mirrors tuck_enum._legal_table exactly: anchor cell must be empty, and
    (H/RH) partner (y,x+1) empty with x<=6, or (V/RV) partner (y-1,x) empty
    or y==0 (top half clipped off-field, allowed as a transit state)."""
    a.label("tb_is_legal")
    a.ins("LDA_zp", IL_O)
    a.ins("AND_imm", 1)
    a.br("BNE", "tb_il_vert")
    # ---- horizontal (H/RH): x<=6, board[y,x] and board[y,x+1] both empty
    a.ins("LDA_zp", IL_X)
    a.ins("CMP_imm", 7)
    a.br("BCS", "tb_il_no")
    a.ins("LDA_zp", IL_Y)
    a.ins("ASL_A"); a.ins("ASL_A"); a.ins("ASL_A")   # y*8
    a.ins("CLC"); a.ins("ADC_zp", IL_X)
    a.ins("TAX")
    a.ins16("LDA_absX", LIVE_BOARD)
    a.ins("CMP_imm", EMPTY)
    a.br("BNE", "tb_il_no")
    a.ins("INX")
    a.ins16("LDA_absX", LIVE_BOARD)
    a.ins("CMP_imm", EMPTY)
    a.br("BNE", "tb_il_no")
    a.jmp("tb_il_yes")
    # ---- vertical (V/RV): board[y,x] empty AND (y==0 OR board[y-1,x] empty)
    a.label("tb_il_vert")
    a.ins("LDA_zp", IL_Y)
    a.ins("ASL_A"); a.ins("ASL_A"); a.ins("ASL_A")   # y*8
    a.ins("CLC"); a.ins("ADC_zp", IL_X)
    a.ins("TAX")
    a.ins16("LDA_absX", LIVE_BOARD)
    a.ins("CMP_imm", EMPTY)
    a.br("BNE", "tb_il_no")
    a.ins("LDA_zp", IL_Y)
    a.br("BEQ", "tb_il_yes")            # y==0 -> partner auto-satisfied
    a.ins("TXA")
    a.ins("SEC"); a.ins("SBC_imm", 8)   # offset - 8 = (y-1)*8+x
    a.ins("TAX")
    a.ins16("LDA_absX", LIVE_BOARD)
    a.ins("CMP_imm", EMPTY)
    a.br("BNE", "tb_il_no")
    a.label("tb_il_yes")
    a.ins("LDA_imm", 1)
    a.ins("RTS")
    a.label("tb_il_no")
    a.ins("LDA_imm", 0)
    a.ins("RTS")


# ================================================== visited-bitplane helpers
def _emit_vbit(a):
    """tb_vbit: inputs VB_ROWBASE (=y*4), VB_S (0..31) -> VB_BYTEIDX, VB_MASK.
    byte = VB_ROWBASE + (VB_S>>3); mask = 1 << (VB_S & 7). Shift-loop mirrors
    primitives.py's fc_flmark bit-mask idiom (no table needed)."""
    a.label("tb_vbit")
    a.ins("LDA_zp", VB_S)
    a.ins("LSR_A"); a.ins("LSR_A"); a.ins("LSR_A")   # s>>3, range 0..3
    a.ins("CLC"); a.ins("ADC_zp", VB_ROWBASE)
    a.ins("STA_zp", VB_BYTEIDX)
    a.ins("LDA_zp", VB_S)
    a.ins("AND_imm", 7)
    a.ins("TAX")
    a.ins("LDA_imm", 1)
    a.label("tb_vbit_sh")
    a.ins("DEX")
    a.br("BMI", "tb_vbit_shd")
    a.ins("ASL_A")
    a.jmp("tb_vbit_sh")
    a.label("tb_vbit_shd")
    a.ins("STA_zp", VB_MASK)
    a.ins("RTS")


def _emit_vis_test(a):
    """tb_vis_test: inputs VB_ROWBASE/VB_S -> A=1 if the bit is set, else 0."""
    a.label("tb_vis_test")
    a.jsr("tb_vbit")
    a.ins("LDX_zp", VB_BYTEIDX)
    a.ins16("LDA_absX", BFS_VIS)
    a.ins("AND_zp", VB_MASK)
    a.br("BEQ", "tb_vt_no")
    a.ins("LDA_imm", 1)
    a.ins("RTS")
    a.label("tb_vt_no")
    a.ins("LDA_imm", 0)
    a.ins("RTS")


def _emit_vis_set_new(a):
    """tb_vis_set_new: inputs VB_ROWBASE/VB_S. If the bit was clear, sets it
    and returns A=1 ("newly marked"); if already set, returns A=0 and leaves
    VIS untouched."""
    a.label("tb_vis_set_new")
    a.jsr("tb_vbit")
    a.ins("LDX_zp", VB_BYTEIDX)
    a.ins16("LDA_absX", BFS_VIS)
    a.ins("AND_zp", VB_MASK)
    a.br("BNE", "tb_vsn_already")
    a.ins("LDX_zp", VB_BYTEIDX)
    a.ins16("LDA_absX", BFS_VIS)
    a.ins("ORA_zp", VB_MASK)
    a.ins16("STA_absX", BFS_VIS)
    a.ins("LDA_imm", 1)
    a.ins("RTS")
    a.label("tb_vsn_already")
    a.ins("LDA_imm", 0)
    a.ins("RTS")


# ============================================== mark / check-and-mark =====
def _emit_mark_state(a):
    """tb_mark_state: inputs CM_X/CM_Y/CM_O.  NO legality check -- caller
    must have already confirmed legality.  Sets the VIS bit if new, and (as a
    side effect, harmless outside the row fixed-point loop) BFS_CHANGED=1."""
    a.label("tb_mark_state")
    a.ins("LDA_zp", CM_X)
    a.ins("ASL_A"); a.ins("ASL_A")
    a.ins("CLC"); a.ins("ADC_zp", CM_O)
    a.ins("STA_zp", VB_S)
    a.ins("LDA_zp", CM_Y)
    a.ins("ASL_A"); a.ins("ASL_A")
    a.ins("STA_zp", VB_ROWBASE)
    a.jsr("tb_vis_set_new")
    a.ins("CMP_imm", 1)
    a.br("BNE", "tb_mst_done")
    a.ins("LDA_imm", 1)
    a.ins("STA_zp", BFS_CHANGED)
    a.label("tb_mst_done")
    a.ins("RTS")


def _emit_check_and_mark(a):
    """tb_check_and_mark: inputs CM_X/CM_Y/CM_O. Copies to IL_*, tests
    legality; if legal, marks it (tb_mark_state). Returns A = legal flag
    (1/0) so callers needing the kick fallback can branch on it."""
    a.label("tb_check_and_mark")
    a.ins("LDA_zp", CM_X); a.ins("STA_zp", IL_X)
    a.ins("LDA_zp", CM_Y); a.ins("STA_zp", IL_Y)
    a.ins("LDA_zp", CM_O); a.ins("STA_zp", IL_O)
    a.jsr("tb_is_legal")
    a.ins("PHA")
    a.ins("CMP_imm", 1)
    a.br("BNE", "tb_cam_done")
    a.jsr("tb_mark_state")
    a.label("tb_cam_done")
    a.ins("PLA")
    a.ins("RTS")


# ===================================================== row-local transitions
def _emit_rot_block(a, no):
    """One unrolled rotation attempt: BFS_(X,Y,O) -> orientation `no`, with
    the right-wall pre-clamp (only when `no` is horizontal) and, on primary
    failure, the single left-kick (only when `no` is horizontal and the
    clamped column is >=1) -- both ported verbatim from _bfs_free's enq()."""
    is_h_no = _IS_H[no]
    skip = f"tb_rot{no}_skip"
    a.ins("LDA_zp", BFS_O)
    a.ins("CMP_imm", no)
    a.br("BEQ", skip)                    # already this orientation -- no-op
    if is_h_no:
        notx7 = f"tb_rot{no}_notx7"
        txset = f"tb_rot{no}_txset"
        a.ins("LDA_zp", BFS_X)
        a.ins("CMP_imm", 7)
        a.br("BNE", notx7)
        a.ins("LDA_imm", 6)
        a.jmp(txset)
        a.label(notx7)
        a.ins("LDA_zp", BFS_X)
        a.label(txset)
    else:
        a.ins("LDA_zp", BFS_X)            # V/RV: no right-wall clamp
    a.ins("STA_zp", RT_TX)
    a.ins("STA_zp", CM_X)
    a.ins("LDA_zp", BFS_Y); a.ins("STA_zp", CM_Y)
    a.ins("LDA_imm", no); a.ins("STA_zp", CM_O)
    a.jsr("tb_check_and_mark")
    a.ins("CMP_imm", 1)
    a.br("BEQ", skip)                     # primary target legal -- done
    if is_h_no:
        # left-kick: only rotating INTO horizontal, and only if tx>=1
        a.ins("LDA_zp", RT_TX)
        a.br("BEQ", skip)                 # tx==0 -> no room to kick
        a.ins("SEC"); a.ins("SBC_imm", 1)
        a.ins("STA_zp", CM_X)
        a.ins("LDA_zp", BFS_Y); a.ins("STA_zp", CM_Y)
        a.ins("LDA_imm", no); a.ins("STA_zp", CM_O)
        a.jsr("tb_check_and_mark")
    a.label(skip)


def _emit_row_step(a):
    """tb_row_step: for the CURRENT state (BFS_X, BFS_O) in row BFS_Y,
    attempt Left, Right, and the 3 other rotations. Any newly-legal
    neighbour is marked via tb_check_and_mark, which raises BFS_CHANGED so
    the row fixed-point loop knows to run another pass."""
    a.label("tb_row_step")
    # ---- LEFT: (x-1, y, o) ----
    a.ins("LDA_zp", BFS_X)
    a.br("BEQ", "tb_left_skip")
    a.ins("SEC"); a.ins("SBC_imm", 1)
    a.ins("STA_zp", CM_X)
    a.ins("LDA_zp", BFS_Y); a.ins("STA_zp", CM_Y)
    a.ins("LDA_zp", BFS_O); a.ins("STA_zp", CM_O)
    a.jsr("tb_check_and_mark")
    a.label("tb_left_skip")
    # ---- RIGHT: (x+1, y, o) ----
    a.ins("LDA_zp", BFS_X)
    a.ins("CMP_imm", 7)
    a.br("BEQ", "tb_right_skip")
    a.ins("CLC"); a.ins("ADC_imm", 1)
    a.ins("STA_zp", CM_X)
    a.ins("LDA_zp", BFS_Y); a.ins("STA_zp", CM_Y)
    a.ins("LDA_zp", BFS_O); a.ins("STA_zp", CM_O)
    a.jsr("tb_check_and_mark")
    a.label("tb_right_skip")
    # ---- ROTATIONS: all 3 other orientations, each unrolled ----
    for no in range(4):
        _emit_rot_block(a, no)
    a.ins("RTS")


def _emit_row_fixedpoint(a):
    """tb_row_fixedpoint: closes row BFS_Y under Left/Right/Rotate to a
    fixed point (repeat full 32-state passes while any pass changes
    something), bounded by ROW_PASS_CAP as a safety net."""
    a.label("tb_row_fixedpoint")
    a.ins("LDA_imm", ROW_PASS_CAP)
    a.ins("STA_zp", PASS_CNT)
    a.label("tb_rfp_pass")
    a.ins("LDA_imm", 0)
    a.ins("STA_zp", BFS_CHANGED)
    a.ins("LDA_imm", 0)
    a.ins("STA_zp", BFS_S)
    a.label("tb_rfp_state")
    a.ins("LDA_zp", BFS_Y)
    a.ins("ASL_A"); a.ins("ASL_A")
    a.ins("STA_zp", VB_ROWBASE)
    a.ins("LDA_zp", BFS_S)
    a.ins("STA_zp", VB_S)
    a.jsr("tb_vis_test")
    a.ins("CMP_imm", 1)
    a.br("BNE", "tb_rfp_next")
    a.ins("LDA_zp", BFS_S)
    a.ins("LSR_A"); a.ins("LSR_A")
    a.ins("STA_zp", BFS_X)
    a.ins("LDA_zp", BFS_S)
    a.ins("AND_imm", 3)
    a.ins("STA_zp", BFS_O)
    a.jsr("tb_row_step")
    a.label("tb_rfp_next")
    a.ins("INC_zp", BFS_S)
    a.ins("LDA_zp", BFS_S)
    a.ins("CMP_imm", 32)
    a.br("BNE", "tb_rfp_state")
    a.ins("DEC_zp", PASS_CNT)
    a.ins("LDA_zp", BFS_CHANGED)
    a.br("BEQ", "tb_rfp_done")            # no change this pass -> fixed point
    a.ins("LDA_zp", PASS_CNT)
    a.br("BNE", "tb_rfp_pass")            # passes remain -> go again
    a.label("tb_rfp_done")
    a.ins("RTS")


def _emit_down_propagate(a):
    """tb_down_propagate: after row BFS_Y's fixed point, push each visited
    state (x,o) down into (x, BFS_Y+1, o) if legal there. Single pass -- row
    BFS_Y+1's own fixed point (run next by the caller) absorbs these seeds
    along with its own Left/Right/Rotate closure."""
    a.label("tb_down_propagate")
    a.ins("LDA_zp", BFS_Y)
    a.ins("CMP_imm", ROWS - 1)
    a.br("BEQ", "tb_dp_done")             # floor row -> nothing below
    a.ins("LDA_imm", 0)
    a.ins("STA_zp", BFS_S)
    a.label("tb_dp_loop")
    a.ins("LDA_zp", BFS_Y)
    a.ins("ASL_A"); a.ins("ASL_A")
    a.ins("STA_zp", VB_ROWBASE)
    a.ins("LDA_zp", BFS_S)
    a.ins("STA_zp", VB_S)
    a.jsr("tb_vis_test")
    a.ins("CMP_imm", 1)
    a.br("BNE", "tb_dp_next")
    a.ins("LDA_zp", BFS_S)
    a.ins("LSR_A"); a.ins("LSR_A")
    a.ins("STA_zp", CM_X)
    a.ins("LDA_zp", BFS_Y)
    a.ins("CLC"); a.ins("ADC_imm", 1)
    a.ins("STA_zp", CM_Y)
    a.ins("LDA_zp", BFS_S)
    a.ins("AND_imm", 3)
    a.ins("STA_zp", CM_O)
    a.jsr("tb_check_and_mark")
    a.label("tb_dp_next")
    a.ins("INC_zp", BFS_S)
    a.ins("LDA_zp", BFS_S)
    a.ins("CMP_imm", 32)
    a.br("BNE", "tb_dp_loop")
    a.label("tb_dp_done")
    a.ins("RTS")


# ============================================================ emit phase ===
def _emit_emit_phase(a):
    """tb_emit_phase: linear scan over the full VISITED plane in ascending
    (y, x, orient) order (y outer, s=x*4+o inner) -- the canonical order the
    bit-exact comparison harness also sorts its python side into. Skips
    clipped states (V/RV at y=0, matching tuck_enum's default
    include_clipped=False) and non-resting states. Writes surviving
    candidates to OUT_X/OUT_Y/OUT_O, capped at OUT_CAP."""
    a.label("tb_emit_phase")
    a.ins("LDA_imm", 0)
    a.ins("STA_zp", BFS_OUTN)
    a.ins("LDA_imm", 0)
    a.ins("STA_zp", BFS_Y)
    a.label("tb_ep_row")
    a.ins("LDA_imm", 0)
    a.ins("STA_zp", BFS_S)
    a.label("tb_ep_state")
    a.ins("LDA_zp", BFS_Y)
    a.ins("ASL_A"); a.ins("ASL_A")
    a.ins("STA_zp", VB_ROWBASE)
    a.ins("LDA_zp", BFS_S)
    a.ins("STA_zp", VB_S)
    a.jsr("tb_vis_test")
    a.ins("CMP_imm", 1)
    a.br("BNE", "tb_ep_next")
    a.ins("LDA_zp", BFS_S)
    a.ins("LSR_A"); a.ins("LSR_A")
    a.ins("STA_zp", BFS_X)
    a.ins("LDA_zp", BFS_S)
    a.ins("AND_imm", 3)
    a.ins("STA_zp", BFS_O)
    # clipped: (V/RV) and y==0
    a.ins("LDA_zp", BFS_O)
    a.ins("AND_imm", 1)
    a.br("BEQ", "tb_ep_rest")             # H/RH -> never clipped
    a.ins("LDA_zp", BFS_Y)
    a.br("BNE", "tb_ep_rest")             # y!=0 -> not clipped
    a.jmp("tb_ep_next")                   # V/RV at y=0 -> clipped, skip
    a.label("tb_ep_rest")
    a.ins("LDA_zp", BFS_O)
    a.ins("AND_imm", 1)
    a.br("BNE", "tb_ep_rvert")
    # horizontal REST: y==15 or board[y+1,x]!=EMPTY or board[y+1,x+1]!=EMPTY
    a.ins("LDA_zp", BFS_Y)
    a.ins("CMP_imm", ROWS - 1)
    a.br("BEQ", "tb_ep_yes")
    a.ins("LDA_zp", BFS_Y)
    a.ins("CLC"); a.ins("ADC_imm", 1)
    a.ins("ASL_A"); a.ins("ASL_A"); a.ins("ASL_A")
    a.ins("CLC"); a.ins("ADC_zp", BFS_X)
    a.ins("TAX")
    a.ins16("LDA_absX", LIVE_BOARD)
    a.ins("CMP_imm", EMPTY)
    a.br("BNE", "tb_ep_yes")
    a.ins("INX")
    a.ins16("LDA_absX", LIVE_BOARD)
    a.ins("CMP_imm", EMPTY)
    a.br("BNE", "tb_ep_yes")
    a.jmp("tb_ep_next")                   # neither support cell occupied
    a.label("tb_ep_rvert")
    # vertical REST: y==15 or board[y+1,x]!=EMPTY
    a.ins("LDA_zp", BFS_Y)
    a.ins("CMP_imm", ROWS - 1)
    a.br("BEQ", "tb_ep_yes")
    a.ins("LDA_zp", BFS_Y)
    a.ins("CLC"); a.ins("ADC_imm", 1)
    a.ins("ASL_A"); a.ins("ASL_A"); a.ins("ASL_A")
    a.ins("CLC"); a.ins("ADC_zp", BFS_X)
    a.ins("TAX")
    a.ins16("LDA_absX", LIVE_BOARD)
    a.ins("CMP_imm", EMPTY)
    a.br("BNE", "tb_ep_yes")
    a.jmp("tb_ep_next")
    a.label("tb_ep_yes")
    a.ins("LDA_zp", BFS_OUTN)
    a.ins("CMP_imm", OUT_CAP)
    a.br("BCS", "tb_ep_next")             # capacity guard
    a.ins("LDX_zp", BFS_OUTN)
    a.ins("LDA_zp", BFS_X)
    a.ins16("STA_absX", BFS_OUT_X)
    a.ins("LDA_zp", BFS_Y)
    a.ins16("STA_absX", BFS_OUT_Y)
    a.ins("LDA_zp", BFS_O)
    a.ins16("STA_absX", BFS_OUT_O)
    a.ins("INC_zp", BFS_OUTN)
    a.label("tb_ep_next")
    a.ins("INC_zp", BFS_S)
    a.ins("LDA_zp", BFS_S)
    a.ins("CMP_imm", 32)
    a.br("BEQ", "tb_ep_rowdone")          # loop body is long -> invert+JMP
    a.jmp("tb_ep_state")                  # (BNE's +/-127 range doesn't reach)
    a.label("tb_ep_rowdone")
    a.ins("INC_zp", BFS_Y)
    a.ins("LDA_zp", BFS_Y)
    a.ins("CMP_imm", ROWS)
    a.br("BEQ", "tb_ep_alldone")
    a.jmp("tb_ep_row")
    a.label("tb_ep_alldone")
    a.ins("RTS")


# =============================================================== top level =
def _emit_tuck_bfs_main(a):
    """tuck_bfs: top-level entry. Clears VIS + BFS_OUTN, seeds the spawn
    state (3,0,H) if legal (else the board is topped out and the plane stays
    empty, matching tuck_enum's early `return [], {}`), then runs the
    row-by-row fixed-point + down-propagate loop for y=0..15, and finally
    the linear emit pass."""
    a.label("tuck_bfs")
    # clear VIS (64 bytes)
    a.ins("LDX_imm", 63)
    a.label("tb_clrvis")
    a.ins("LDA_imm", 0)
    a.ins16("STA_absX", BFS_VIS)
    a.ins("DEX")
    a.br("BPL", "tb_clrvis")
    a.ins("LDA_imm", 0)
    a.ins("STA_zp", BFS_OUTN)
    # seed spawn (3, 0, H)
    a.ins("LDA_imm", 3); a.ins("STA_zp", IL_X)
    a.ins("LDA_imm", 0); a.ins("STA_zp", IL_Y)
    a.ins("LDA_imm", 0); a.ins("STA_zp", IL_O)
    a.jsr("tb_is_legal")
    a.ins("CMP_imm", 1)
    a.br("BEQ", "tb_seed_ok")
    a.ins("RTS")                          # topped out: no seed, empty output
    a.label("tb_seed_ok")
    a.ins("LDA_imm", 0)
    a.ins("STA_zp", VB_ROWBASE)           # row 0
    a.ins("LDA_imm", 12)                  # s = x*4+o = 3*4+0 = 12
    a.ins("STA_zp", VB_S)
    a.jsr("tb_vis_set_new")
    # row loop
    a.ins("LDA_imm", 0)
    a.ins("STA_zp", BFS_Y)
    a.label("tb_row_loop")
    a.jsr("tb_row_fixedpoint")
    a.jsr("tb_down_propagate")
    a.ins("INC_zp", BFS_Y)
    a.ins("LDA_zp", BFS_Y)
    a.ins("CMP_imm", ROWS)
    a.br("BNE", "tb_row_loop")
    a.jsr("tb_emit_phase")
    a.ins("RTS")


def build(base=0x8000):
    a = Asm6502(base)
    _emit_tuck_bfs_main(a)
    _emit_row_fixedpoint(a)
    _emit_down_propagate(a)
    _emit_row_step(a)
    _emit_check_and_mark(a)
    _emit_mark_state(a)
    _emit_vis_set_new(a)
    _emit_vis_test(a)
    _emit_vbit(a)
    _emit_is_legal(a)
    _emit_emit_phase(a)
    return a


if __name__ == "__main__":
    a = build()
    code = a.assemble()
    print(f"tuck_bfs assembled: {len(code)} bytes @ ${a.base:04X}, "
          f"{len(a.labels)} labels")
