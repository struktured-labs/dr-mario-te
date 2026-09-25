"""DRREACH -- the reach-root pre-filter for the copro search (STEER2, 2026-09-25).

At the ROOT only, drop every candidate the couch P2 driver cannot land EXACTLY on its straight-drop cells before
gravity locks it. Python reference: h16-wt experiments/cvx/reach_fw.py (copied verbatim, with md5, to
experiments/reach/reach_fw.py). It was validated against the steering-faithful frame simulator on 46,272 candidates
(STEER2): the reach-root brain cuts couch-like early tap-outs 28.8% -> 9.8% under steering with no race cost.

This module emits a SELF-CONTAINED routine at REACH_ROM ($A800, the v1-tuck window, never co-resident: asserted
in build_copro_d3). The search JSRs it once per search, after the board upload and before Pass 0:
  * decode the gravity threshold `thr` from the high nibbles of S_NA/S_NB (the DRREACHTX cart transport);
  * fill ROK[32] ($0A80, index o4*8+col in COPRO orient space) with 1 = reachable / 0 = not;
  * set R_FLT (zp $C9) = 1 iff the filter is active.
Pass 0 then skips (jmp p0_next) every legal candidate with R_FLT && !ROK[o4*8+col]; if that leaves no candidate,
the search clears R_FLT and reruns Pass 0 unfiltered (= today's behaviour).

TRANSPORT (cart DRREACHTX, patch_cartridge_copro.py; both GO paths):
  S_NA high nibble = speedUps & $0F
  S_NB high nibble = ((speedUps >> 4) & 3) | ((speed + 1) << 2)          speed = P2 $038B in 0..2, speedUps = P2 $038A
  thr = speedCounterTable[baseSpeedSettingValue[speed] + speedUps]       (index clamped to 80)
  DEVIATION FROM THE STEER2 SPEC (deliberate): speed is sent as speed+1, so a DRREACHTX cart NEVER sends a zero NB
  high nibble. Zero therefore means "old cart" -> R_FLT = 0, no filtering -> exactly today's search.
  Every firmware read of S_NA/S_NB masks AND #$0F (test_search_d3 _e_node/_e_dnode), so the nibbles are inert to
  the search itself (gate G1 proves it).
  PAIRING RULE: a DRREACHTX cart must ONLY run with a DRREACH firmware... no: a DRREACHTX cart with an OLD firmware is
  ALSO safe (old firmware masks the nibbles too); the rule that matters is the other way -- a DRREACH firmware with an
  old cart silently runs unfiltered. See CHAIN540_REACH_BUILD.md.

FRAMES are 16-bit (a narrow deep well at LOW speed can keep the rotation retrying past frame 255; saturating
would diverge from reach_fw). Rows are computed on the fly (<= 16 subtract iterations in every call site, because
every row_at(t) is evaluated at t < the current lock frame <= T(15)). TICK[r] = G0 + thr + r*(thr+1), r = 0..15.
Constants are silicon-fitted (steer_model.py): T_LAT 19, G0 8, F0 3, DAS 16/6, NROT by o4 [1, 1, 0, 2].
"""
import sys as _sys
for _p in ("/home/struktured/projects/dr-mario-mods/tests", "/home/struktured/projects/dr-mario-mods"):
    if _p not in _sys.path:
        _sys.path.append(_p)       # APPEND: never shadow the worktree's tests/test_search_d3 (build_copro_d3's guard)
import patch_vs_cpu

for _k, _v in (("ORA_abs", 0x0D), ("AND_abs", 0x2D), ("ORA_zp", 0x05), ("STX_abs", 0x8E), ("CMP_absX", 0xDD),
               ("SBC_absX", 0xFD), ("ADC_absX", 0x7D), ("INC_abs", 0xEE), ("DEC_abs", 0xCE)):
    patch_vs_cpu.OPS.setdefault(_k, _v)

REACH_ROM = 0xA800
LIVE = 0x0500
ROK = 0x0A80                     # 32 B: 1 = reachable, index o4*8+col (copro orient space)
TOP = 0x0AA0                     # 8 B: first occupied row per column (16 = empty column)
TICKL, TICKH = 0x0AA8, 0x0AB8    # 16 B each: lock frame of a capsule resting at row r
V_T1L, V_T1H = 0x0AC8, 0x0AC9    # t1 (first lateral frame)
V_NROT, V_DONE = 0x0ACA, 0x0ACB
V_X0, V_L0L, V_L0H = 0x0ACC, 0x0ACD, 0x0ACE
V_PLOCK, V_PIDX = 0x0ACF, 0x0AD0  # PROPH locked before the answer / the one reachable index ($FF none)
V_PD = 0x0AD1                    # PROPH direction: 0 none, 1 right, $FF left
V_TMP, V_TMP2 = 0x0AD2, 0x0AD3
V_IDX, V_ANY = 0x0AD4, 0x0AD5
V_LO, V_HI = 0x0AD6, 0x0AD7      # lateral span columns
V_G0T = 0x0AD8                   # G0 + thr
V_SR = 0x0AD9                    # scratch rest row
REACH_RAM_END = 0x0ADA
# zp $B6-$C9: unclaimed by every module of the Childproof/CHAIN540 build (measured by instrumenting the
# assembler over a full build_image: only $B4/$B5 (DRVETO) are used in $B4-$C9).
(R_THR, R_TP1, R_X, R_LKL, R_LKH, R_FL, R_FH, R_O4, R_COL, R_VRT, R_FX, R_FR, R_FV, RW_L, RW_H, R_I, R_D, R_SD,
 R_R, R_FLT) = range(0xB6, 0xCA)
assert R_FLT == 0xC9

T_LAT, G0, F0 = 19, 8, 3
NROT_O4 = [1, 1, 0, 2]           # sim var = o4 ^ 2; NROT by var {0: 0, 1: 2, 2: 1, 3: 1}
SPEED_TABLE = [0x45, 0x43, 0x41, 0x3F, 0x3D, 0x3B, 0x39, 0x37, 0x35, 0x33, 0x31, 0x2F, 0x2D, 0x2B, 0x29, 0x27,
               0x25, 0x23, 0x21, 0x1F, 0x1D, 0x1B, 0x19, 0x17, 0x15, 0x13, 0x12, 0x11, 0x10, 0x0F, 0x0E, 0x0D,
               0x0C, 0x0B, 0x0A, 0x09, 0x09, 0x08, 0x08, 0x07, 0x07, 0x06, 0x06, 0x05, 0x05, 0x05, 0x05, 0x05,
               0x05, 0x05, 0x05, 0x05, 0x05, 0x05, 0x05, 0x04, 0x04, 0x04, 0x04, 0x04, 0x03, 0x03, 0x03, 0x03,
               0x03, 0x02, 0x02, 0x02, 0x02, 0x02, 0x01, 0x01, 0x01, 0x01, 0x01, 0x01, 0x01, 0x01, 0x01, 0x01,
               0x00]             # NTSC speedCounterTable (disassembly data/drmario_data_game.asm)
SPEED_BASE = [0x0F, 0x19, 0x1F]  # baseSpeedSettingValue LOW/MED/HI
assert len(SPEED_TABLE) == 81

# TEST-ONLY mutants (gate G2 must kill each). Never set by any build.
_MUT = "none"   # "tlat_m1" | "tlat_p1" | "no_distgate" | "penalty" (handled in test_search_d3) | "no_fallback"


def thr_from_nibbles(na, nb):
    """Firmware decode of the DRREACHTX transport. None = no transport (old cart) or invalid -> no filter."""
    nbh = (nb >> 4) & 0x0F
    if nbh == 0:
        return None
    sp = (nbh >> 2) - 1
    if not 0 <= sp <= 2:
        return None
    su = ((nbh & 3) << 4) | ((na >> 4) & 0x0F)
    return SPEED_TABLE[min(80, SPEED_BASE[sp] + su)]


def pack_nibbles(speed, speedups):
    """Cart side (DRREACHTX): the high nibbles OR-ed into nA / nB."""
    return (speedups & 0x0F) << 4, ((((speedups >> 4) & 3) | ((speed + 1) << 2)) & 0x0F) << 4


# ------------------------------------------------------------------ Python mirror of the 6502 (dev + gate aid)
def mirror_mask(live, thr, tlat=T_LAT, distgate=True):
    """The exact integer algorithm the 6502 implements, on NES bytes (empty = $FF or $00), in COPRO o4 space.
    Returns (rok[32], flt). Must equal reach_fw.reach_mask_fw (re-indexed var = o4 ^ 2) on every board."""
    emp = lambda r, c: live[r * 8 + c] in (0xFF, 0x00)
    top = [next((r for r in range(16) if not emp(r, c)), 16) for c in range(8)]
    tick = [min(0xFFFF, G0 + thr + r * (thr + 1)) for r in range(16)]

    def row(t):
        v = t - (G0 + thr)
        if v < 0:
            return 0
        return min(255, v // (thr + 1) + 1)

    def fits(x, r, v):
        if r >= 16:
            return False
        if not v:
            if not 0 <= x <= 6:
                return False
            return emp(r, x) and emp(r, x + 1)
        if not 0 <= x <= 7:
            return False
        return emp(r, x) and (r == 0 or emp(r - 1, x))

    def rest(x, r, v):
        while fits(x, r + 1, v):
            r += 1
        return r

    def tk(r):
        return tick[r] if r < 16 else 0xFFFF

    # PROPH
    pd = 0
    if top[3] <= 2 or top[4] <= 2:
        gl = emp(0, 2) and emp(1, 2)
        gr = emp(0, 5) and emp(1, 5)
        if top[4] > top[3]:
            pd = 1 if gr else (-1 if gl else 0)
        else:
            pd = -1 if gl else (1 if gr else 0)
    x = 3
    plock, pidx = False, None
    if pd:
        lock = tk(rest(3, 0, False))
        for f in range(F0, tlat):
            if f >= lock:
                break
            if f & 1:
                r = row(f)
                if fits(x + pd, r, False):
                    x += pd
                    lock = tk(rest(x, r, False))
        if lock <= tlat:
            plock = True
            r = row(lock) if lock > G0 + thr else 0
            land = rest(x, min(r, rest(x, 0, False)), False)
            sr = min(top[x], top[x + 1]) - 1 if 0 <= x <= 6 else None
            pidx = 16 + x if land == sr else None
    x0 = x
    if not plock:
        l0 = tk(rest(x0, row(tlat - 1), False))
    rok = [0] * 32
    for idx in range(32):
        o4, col = idx >> 3, idx & 7
        vert = (o4 & 2) == 0
        if not vert and col >= 7:
            continue
        if vert and top[col] < 2:
            continue
        if not vert and min(top[col], top[col + 1]) < 1:
            continue
        if plock:
            rok[idx] = int(idx == pidx)
            continue
        x, lock, f, done, nrot = x0, l0, tlat, 0, NROT_O4[o4]
        ok = True
        while done < nrot:
            if f >= lock:
                ok = False
                break
            r = row(f)
            if done == 0:
                if fits(x, r, True):
                    done = 1
                    lock = tk(rest(x, r, True))
            else:
                if fits(x, r, False):
                    done = 2
                elif fits(x - 1, r, False):
                    x -= 1
                    done = 2
                if done == 2:
                    lock = tk(rest(x, r, False))
            f += 1
        if not ok:
            continue
        t1 = f
        d = abs(col - x)
        sd = 1 if col > x else -1
        r = row(t1 - 1)
        ti = t1
        for i in range(1, d + 1):
            if ti >= lock:
                ok = False
                break
            if distgate:
                rb = row(ti - 1) + 1
                lo, hi = min(x, col), max(x, col)
                if rb >= 16 or not all(emp(rb, c) for c in range(lo, hi + 1)):
                    ok = False
                    break
            r = row(ti)
            if not fits(x + sd, r, vert):
                ok = False
                break
            x += sd
            lock = tk(rest(x, r, vert))
            ti = t1 + 16 if i == 1 else ti + 6
        if not ok:
            continue
        sr = (top[x] - 1) if vert else (min(top[x], top[x + 1]) - 1)
        rok[idx] = int(rest(x, r, vert) == sr)
    flt = int(any(rok))
    return rok, flt


# ------------------------------------------------------------------ 6502 emitter
def emit_reach(a, s_na, s_nb):
    """Emit the routine; the FIRST instruction is the entry point (label reach_mask at offset 0, asserted by the
    builder), so the search can JSR REACH_ROM without a cross-image label. Clobbers A/X/Y, zp $B6-$C9, RAM
    $0A80-$0AD9. Leaves R_FLT and ROK for the Pass-0 filter."""
    tlat = T_LAT + (-1 if _MUT == "tlat_m1" else 1 if _MUT == "tlat_p1" else 0)
    a.label("reach_mask")
    # ---------- transport decode -> thr, or no filter ----------
    a.ins("LDA_imm", 0); a.ins("STA_zp", R_FLT)
    a.ins16("LDA_abs", s_nb); a.ins("LSR_A"); a.ins("LSR_A"); a.ins("LSR_A"); a.ins("LSR_A")
    a.br("BNE", "rm_tx"); a.ins("RTS")                        # old cart: no transport -> no filter
    a.label("rm_tx")
    a.ins16("STA_abs", V_TMP)                                   # nb high nibble
    a.ins("LSR_A"); a.ins("LSR_A"); a.ins("SEC"); a.ins("SBC_imm", 1)   # speed = (nbh >> 2) - 1
    a.ins("CMP_imm", 3); a.br("BCC", "rm_spok"); a.ins("RTS")   # invalid speed -> no filter
    a.label("rm_spok")
    a.ins("TAX")
    _lda_absx_label(a, "rm_base"); a.ins16("STA_abs", V_TMP2)   # base index
    a.ins16("LDA_abs", V_TMP); a.ins("AND_imm", 0x03)
    a.ins("ASL_A"); a.ins("ASL_A"); a.ins("ASL_A"); a.ins("ASL_A"); a.ins16("STA_abs", V_TMP)
    a.ins16("LDA_abs", s_na); a.ins("LSR_A"); a.ins("LSR_A"); a.ins("LSR_A"); a.ins("LSR_A")
    a.ins16("ORA_abs", V_TMP)                                   # speedUps 0..63
    a.ins("CLC"); a.ins16("ADC_abs", V_TMP2)
    a.ins("CMP_imm", 81); a.br("BCC", "rm_ixok"); a.ins("LDA_imm", 80)
    a.label("rm_ixok")
    a.ins("TAX"); _lda_absx_label(a, "rm_speedtab"); a.ins("STA_zp", R_THR)
    a.ins("CLC"); a.ins("ADC_imm", 1); a.ins("STA_zp", R_TP1)
    a.ins("LDA_zp", R_THR); a.ins("CLC"); a.ins("ADC_imm", G0); a.ins16("STA_abs", V_G0T)
    # ---------- TICK[r] = G0 + thr + r*(thr+1), r = 0..15 (16-bit) ----------
    a.ins16("LDA_abs", V_G0T); a.ins16("STA_abs", TICKL); a.ins("LDA_imm", 0); a.ins16("STA_abs", TICKH)
    a.ins("LDX_imm", 0)
    a.label("rm_tk")
    a.ins("CLC"); a.ins16("LDA_absX", TICKL); a.ins("ADC_zp", R_TP1); a.ins16("STA_absX", TICKL + 1)
    a.ins16("LDA_absX", TICKH); a.ins("ADC_imm", 0); a.ins16("STA_absX", TICKH + 1)
    a.ins("INX"); a.ins("CPX_imm", 15); a.br("BNE", "rm_tk")
    # ---------- TOP[c] ----------
    a.ins("LDX_imm", 0)
    a.label("rm_topc")
    a.ins("TXA"); a.ins("TAY"); a.ins("LDA_imm", 0); a.ins16("STA_abs", V_TMP)   # Y = cell index, V_TMP = row
    a.label("rm_topr")
    a.jsr("re_cell"); a.br("BCC", "rm_topd")
    a.ins("TYA"); a.ins("CLC"); a.ins("ADC_imm", 8); a.ins("TAY")
    a.ins16("INC_abs", V_TMP); a.ins16("LDA_abs", V_TMP); a.ins("CMP_imm", 16); a.br("BNE", "rm_topr")
    a.label("rm_topd")
    a.ins16("LDA_abs", V_TMP); a.ins16("STA_absX", TOP)
    a.ins("INX"); a.ins("CPX_imm", 8); a.br("BNE", "rm_topc")
    # ---------- PROPH direction ----------
    a.ins("LDA_imm", 0); a.ins16("STA_abs", V_PD); a.ins16("STA_abs", V_PLOCK)
    a.ins("LDA_imm", 0xFF); a.ins16("STA_abs", V_PIDX)
    a.ins16("LDA_abs", TOP + 3); a.ins("CMP_imm", 3); a.br("BCC", "rm_parm")
    a.ins16("LDA_abs", TOP + 4); a.ins("CMP_imm", 3); a.br("BCC", "rm_parm")
    a.jmp("rm_nopd")
    a.label("rm_parm")
    # gl -> V_TMP (1 = left gate free), gr -> V_TMP2
    a.ins("LDA_imm", 0); a.ins16("STA_abs", V_TMP); a.ins16("STA_abs", V_TMP2)
    a.ins("LDY_imm", 2); a.jsr("re_cell"); a.br("BCC", "rm_gl0")
    a.ins("LDY_imm", 10); a.jsr("re_cell"); a.br("BCC", "rm_gl0")
    a.ins("LDA_imm", 1); a.ins16("STA_abs", V_TMP)
    a.label("rm_gl0")
    a.ins("LDY_imm", 5); a.jsr("re_cell"); a.br("BCC", "rm_gr0")
    a.ins("LDY_imm", 13); a.jsr("re_cell"); a.br("BCC", "rm_gr0")
    a.ins("LDA_imm", 1); a.ins16("STA_abs", V_TMP2)
    a.label("rm_gr0")
    # if top4 > top3: R if gr else (L if gl else 0) ; else: L if gl else (R if gr else 0)
    a.ins16("LDA_abs", TOP + 3); a.ins16("CMP_abs", TOP + 4); a.br("BCS", "rm_pdl")   # top3 >= top4 -> left pref
    a.ins16("LDA_abs", V_TMP2); a.br("BNE", "rm_pdR")
    a.ins16("LDA_abs", V_TMP); a.br("BNE", "rm_pdL"); a.jmp("rm_nopd")
    a.label("rm_pdl")
    a.ins16("LDA_abs", V_TMP); a.br("BNE", "rm_pdL")
    a.ins16("LDA_abs", V_TMP2); a.br("BNE", "rm_pdR"); a.jmp("rm_nopd")
    a.label("rm_pdR"); a.ins("LDA_imm", 1); a.ins16("STA_abs", V_PD); a.jmp("rm_pph")
    a.label("rm_pdL"); a.ins("LDA_imm", 0xFF); a.ins16("STA_abs", V_PD)
    # ---------- PROPH pulse phase ----------
    a.label("rm_pph")
    a.ins("LDA_imm", 3); a.ins("STA_zp", R_X)
    a.ins("STA_zp", R_FX); a.ins("LDA_imm", 0); a.ins("STA_zp", R_FR); a.ins("STA_zp", R_FV)
    a.jsr("rx_rest"); a.ins("LDA_zp", R_FR); a.jsr("rx_tick")                 # lock = T(rest(3, 0, H))
    a.ins("LDA_imm", F0); a.ins("STA_zp", R_FL); a.ins("LDA_imm", 0); a.ins("STA_zp", R_FH)
    a.label("rm_pf")
    a.ins("LDA_zp", R_FL); a.ins("CMP_imm", tlat); a.br("BCC", "rm_pf1"); a.jmp("rm_pfe")   # f < T_LAT (FH == 0 here)
    a.label("rm_pf1")
    a.ins("LDA_zp", R_FL); a.ins("CMP_zp", R_LKL); a.ins("LDA_zp", R_FH); a.ins("SBC_zp", R_LKH)
    a.br("BCC", "rm_pf2"); a.jmp("rm_pfe")                                    # f >= lock -> break
    a.label("rm_pf2")
    a.ins("LDA_zp", R_FL); a.ins("AND_imm", 1); a.br("BEQ", "rm_pfn")         # even frame: no pulse
    a.ins("LDA_zp", R_FL); a.ins("STA_zp", RW_L); a.ins("LDA_zp", R_FH); a.ins("STA_zp", RW_H)
    a.jsr("rx_row"); a.ins("STA_zp", R_R)
    a.ins("LDA_zp", R_X); a.ins("CLC"); a.ins16("ADC_abs", V_PD); a.ins("STA_zp", R_FX)
    a.ins("LDA_zp", R_R); a.ins("STA_zp", R_FR); a.ins("LDA_imm", 0); a.ins("STA_zp", R_FV)
    a.jsr("rx_fits"); a.br("BCC", "rm_pfn")
    a.ins("LDA_zp", R_FX); a.ins("STA_zp", R_X)                              # x += step
    a.ins("LDA_zp", R_R); a.ins("STA_zp", R_FR); a.jsr("rx_rest"); a.ins("LDA_zp", R_FR); a.jsr("rx_tick")
    a.label("rm_pfn")
    a.ins("INC_zp", R_FL); a.jmp("rm_pf")
    a.label("rm_pfe")
    # locked at or before T_LAT?  lock <= T_LAT  <=>  !(lock > T_LAT)  <=>  LKH == 0 && LKL <= T_LAT
    a.ins("LDA_zp", R_LKH); a.br("BNE", "rm_x0")
    a.ins("LDA_imm", tlat); a.ins("CMP_zp", R_LKL); a.br("BCC", "rm_x0")        # T_LAT < LKL -> not locked
    a.ins("LDA_imm", 1); a.ins16("STA_abs", V_PLOCK)
    # r = row(lock) if lock > G0+thr else 0   (lock <= 19 < 256 here)
    a.ins("LDA_imm", 0); a.ins("STA_zp", R_R)
    a.ins16("LDA_abs", V_G0T); a.ins("CMP_zp", R_LKL); a.br("BCS", "rm_pl0")  # G0T >= lock -> r = 0
    a.ins("LDA_zp", R_LKL); a.ins("STA_zp", RW_L); a.ins("LDA_imm", 0); a.ins("STA_zp", RW_H)
    a.jsr("rx_row"); a.ins("STA_zp", R_R)
    a.label("rm_pl0")
    # land = rest(x, min(r, rest(x, 0, H)), H)
    a.ins("LDA_zp", R_X); a.ins("STA_zp", R_FX); a.ins("LDA_imm", 0); a.ins("STA_zp", R_FR); a.ins("STA_zp", R_FV)
    a.jsr("rx_rest")
    a.ins("LDA_zp", R_FR); a.ins("CMP_zp", R_R); a.br("BCC", "rm_plm")      # rest0 < r -> use rest0
    a.ins("LDA_zp", R_R)
    a.label("rm_plm")
    a.ins("STA_zp", R_FR); a.jsr("rx_rest")                                    # R_FR = land
    # straight rest at x (H): x <= 6 required, min(top[x], top[x+1]) - 1
    a.ins("LDA_zp", R_X); a.ins("CMP_imm", 7); a.br("BCS", "rm_x0p")        # x > 6 -> no index
    a.ins("TAX"); a.jsr("rx_srh")                                              # A = straight rest (H) at X
    a.ins("CMP_zp", R_FR); a.br("BNE", "rm_x0p")
    a.ins("LDA_zp", R_X); a.ins("CLC"); a.ins("ADC_imm", 16); a.ins16("STA_abs", V_PIDX)
    a.label("rm_x0p")
    a.jmp("rm_cands")
    a.label("rm_nopd")
    a.ins("LDA_imm", 3); a.ins("STA_zp", R_X)
    a.label("rm_x0")
    # ---------- x0, lock0 = T(rest(x0, row(T_LAT - 1), H)) ----------
    a.ins("LDA_zp", R_X); a.ins16("STA_abs", V_X0)
    a.ins("LDA_imm", tlat - 1); a.ins("STA_zp", RW_L); a.ins("LDA_imm", 0); a.ins("STA_zp", RW_H)
    a.jsr("rx_row"); a.ins("STA_zp", R_FR)
    a.ins("LDA_zp", R_X); a.ins("STA_zp", R_FX); a.ins("LDA_imm", 0); a.ins("STA_zp", R_FV)
    a.jsr("rx_rest"); a.ins("LDA_zp", R_FR); a.jsr("rx_tick")
    a.ins("LDA_zp", R_LKL); a.ins16("STA_abs", V_L0L); a.ins("LDA_zp", R_LKH); a.ins16("STA_abs", V_L0H)
    # ---------- per-candidate loop ----------
    a.label("rm_cands")
    a.ins("LDA_imm", 0); a.ins16("STA_abs", V_IDX); a.ins16("STA_abs", V_ANY)
    a.label("rm_cl")
    a.ins16("LDX_abs", V_IDX); a.ins("LDA_imm", 0); a.ins16("STA_absX", ROK)
    a.ins("TXA"); a.ins("AND_imm", 7); a.ins("STA_zp", R_COL)
    a.ins("TXA"); a.ins("LSR_A"); a.ins("LSR_A"); a.ins("LSR_A"); a.ins("STA_zp", R_O4)
    a.ins("AND_imm", 2); a.br("BEQ", "rm_cv")
    a.ins("LDA_imm", 0); a.ins("STA_zp", R_VRT); a.jmp("rm_cvd")
    a.label("rm_cv"); a.ins("LDA_imm", 1); a.ins("STA_zp", R_VRT)
    a.label("rm_cvd")
    # legality (reach_fw): H needs col <= 6 and min(top) >= 1; V needs top >= 2
    a.ins("LDX_zp", R_COL)
    a.ins("LDA_zp", R_VRT); a.br("BEQ", "rm_lh")
    a.ins16("LDA_absX", TOP); a.ins("CMP_imm", 2); a.br("BCS", "rm_lok"); a.jmp("rm_cn")
    a.label("rm_lh")
    a.ins("CPX_imm", 7); a.br("BCC", "rm_lh1"); a.jmp("rm_cn")
    a.label("rm_lh1")
    a.ins16("LDA_absX", TOP); a.br("BNE", "rm_lh2"); a.jmp("rm_cn")
    a.label("rm_lh2")
    a.ins16("LDA_absX", TOP + 1); a.br("BNE", "rm_lok"); a.jmp("rm_cn")
    a.label("rm_lok")
    a.ins16("LDA_abs", V_PLOCK); a.br("BEQ", "rm_run")
    a.ins16("LDA_abs", V_IDX); a.ins16("CMP_abs", V_PIDX); a.br("BEQ", "rm_ok"); a.jmp("rm_cn")
    a.label("rm_run")
    a.jsr("rx_cand"); a.br("BCS", "rm_ok"); a.jmp("rm_cn")
    a.label("rm_ok")
    a.ins16("LDX_abs", V_IDX); a.ins("LDA_imm", 1); a.ins16("STA_absX", ROK); a.ins16("STA_abs", V_ANY)
    a.label("rm_cn")
    a.ins16("INC_abs", V_IDX); a.ins16("LDA_abs", V_IDX); a.ins("CMP_imm", 32); a.br("BEQ", "rm_ce"); a.jmp("rm_cl")
    a.label("rm_ce")
    a.ins16("LDA_abs", V_ANY); a.ins("STA_zp", R_FLT)          # none allowed -> no filter (reach_fw all-ones)
    if _MUT == "no_fallback":
        a.ins("LDA_imm", 1); a.ins("STA_zp", R_FLT)
    a.ins("RTS")

    # ================= rx_cand: rotation + lateral phases for (R_O4, R_COL, R_VRT). C=1 reachable =========
    a.label("rx_cand")
    a.ins16("LDA_abs", V_X0); a.ins("STA_zp", R_X)
    a.ins16("LDA_abs", V_L0L); a.ins("STA_zp", R_LKL); a.ins16("LDA_abs", V_L0H); a.ins("STA_zp", R_LKH)
    a.ins("LDA_imm", tlat); a.ins("STA_zp", R_FL); a.ins("LDA_imm", 0); a.ins("STA_zp", R_FH)
    a.ins16("STA_abs", V_DONE)
    a.ins("LDX_zp", R_O4); _lda_absx_label(a, "rm_nrot"); a.ins16("STA_abs", V_NROT)
    a.label("rc_rl")
    a.ins16("LDA_abs", V_DONE); a.ins16("CMP_abs", V_NROT); a.br("BNE", "rc_r1"); a.jmp("rc_re")
    a.label("rc_r1")
    a.ins("LDA_zp", R_FL); a.ins("CMP_zp", R_LKL); a.ins("LDA_zp", R_FH); a.ins("SBC_zp", R_LKH)
    a.br("BCC", "rc_r2"); a.jmp("rc_no")                                   # f >= lock -> DENY
    a.label("rc_r2")
    a.ins("LDA_zp", R_FL); a.ins("STA_zp", RW_L); a.ins("LDA_zp", R_FH); a.ins("STA_zp", RW_H)
    a.jsr("rx_row"); a.ins("STA_zp", R_R)
    a.ins16("LDA_abs", V_DONE); a.br("BNE", "rc_r2nd")
    # first press -> vertical at x
    a.ins("LDA_zp", R_X); a.ins("STA_zp", R_FX); a.ins("LDA_zp", R_R); a.ins("STA_zp", R_FR)
    a.ins("LDA_imm", 1); a.ins("STA_zp", R_FV)
    a.jsr("rx_fits"); a.br("BCC", "rc_rn")
    a.ins("LDA_imm", 1); a.ins16("STA_abs", V_DONE)
    a.jsr("rx_rest"); a.ins("LDA_zp", R_FR); a.jsr("rx_tick"); a.jmp("rc_rn")
    a.label("rc_r2nd")
    # second press -> horizontal at x, else wall-kick to x-1
    a.ins("LDA_zp", R_X); a.ins("STA_zp", R_FX); a.ins("LDA_zp", R_R); a.ins("STA_zp", R_FR)
    a.ins("LDA_imm", 0); a.ins("STA_zp", R_FV)
    a.jsr("rx_fits"); a.br("BCS", "rc_r2ok")
    a.ins("LDA_zp", R_X); a.ins("SEC"); a.ins("SBC_imm", 1); a.ins("STA_zp", R_FX)
    a.ins("LDA_zp", R_R); a.ins("STA_zp", R_FR)
    a.jsr("rx_fits"); a.br("BCC", "rc_rn")
    a.ins("LDA_zp", R_FX); a.ins("STA_zp", R_X)
    a.label("rc_r2ok")
    a.ins("LDA_imm", 2); a.ins16("STA_abs", V_DONE)
    a.ins("LDA_zp", R_X); a.ins("STA_zp", R_FX); a.ins("LDA_zp", R_R); a.ins("STA_zp", R_FR)
    a.ins("LDA_imm", 0); a.ins("STA_zp", R_FV)
    a.jsr("rx_rest"); a.ins("LDA_zp", R_FR); a.jsr("rx_tick")
    a.label("rc_rn")
    a.ins("INC_zp", R_FL); a.br("BNE", "rc_rl2"); a.ins("INC_zp", R_FH)
    a.label("rc_rl2")
    a.jmp("rc_rl")
    a.label("rc_re")
    # t1 = f ; d = |col - x| ; sd ; r = row(t1 - 1)
    a.ins("LDA_zp", R_FL); a.ins16("STA_abs", V_T1L); a.ins("LDA_zp", R_FH); a.ins16("STA_abs", V_T1H)
    a.ins("LDA_zp", R_COL); a.ins("SEC"); a.ins("SBC_zp", R_X)
    a.br("BEQ", "rc_d0"); a.br("BCC", "rc_dneg")
    a.ins("STA_zp", R_D); a.ins("LDA_imm", 1); a.ins("STA_zp", R_SD)
    a.jmp("rc_dd")
    a.label("rc_dneg")
    a.ins("EOR_imm", 0xFF); a.ins("CLC"); a.ins("ADC_imm", 1); a.ins("STA_zp", R_D)
    a.ins("LDA_imm", 0xFF); a.ins("STA_zp", R_SD)
    a.jmp("rc_dd")
    a.label("rc_d0")
    a.ins("STA_zp", R_D)                                                   # A = 0
    a.label("rc_dd")
    # r = row(t1 - 1)
    a.ins("LDA_zp", R_FL); a.ins("SEC"); a.ins("SBC_imm", 1); a.ins("STA_zp", RW_L)
    a.ins("LDA_zp", R_FH); a.ins("SBC_imm", 0); a.ins("STA_zp", RW_H)
    a.jsr("rx_row"); a.ins("STA_zp", R_R)
    # ti = t1 (already in R_FL/R_FH) ; i = 1
    a.ins("LDA_imm", 1); a.ins("STA_zp", R_I)
    a.label("rc_ll")
    a.ins("LDA_zp", R_D); a.ins("CMP_zp", R_I); a.br("BCS", "rc_l1"); a.jmp("rc_fin")   # i > d -> final
    a.label("rc_l1")
    a.ins("LDA_zp", R_FL); a.ins("CMP_zp", R_LKL); a.ins("LDA_zp", R_FH); a.ins("SBC_zp", R_LKH)
    a.br("BCC", "rc_l2"); a.jmp("rc_no")                                   # ti >= lock -> DENY
    a.label("rc_l2")
    if _MUT != "no_distgate":
        # DISTGATE budget: the row below row(ti - 1) must be entirely empty across [lo..hi]
        a.ins("LDA_zp", R_FL); a.ins("SEC"); a.ins("SBC_imm", 1); a.ins("STA_zp", RW_L)
        a.ins("LDA_zp", R_FH); a.ins("SBC_imm", 0); a.ins("STA_zp", RW_H)
        # span = [min(x, col) .. max(x, col)] with the CURRENT x (reach_fw recomputes it every step)
        a.ins("LDA_zp", R_X); a.ins("CMP_zp", R_COL); a.br("BCC", "rc_spx")
        a.ins("LDA_zp", R_COL); a.ins16("STA_abs", V_LO); a.ins("LDA_zp", R_X); a.ins16("STA_abs", V_HI); a.jmp("rc_spd")
        a.label("rc_spx")
        a.ins("LDA_zp", R_X); a.ins16("STA_abs", V_LO); a.ins("LDA_zp", R_COL); a.ins16("STA_abs", V_HI)
        a.label("rc_spd")
        a.jsr("rx_row"); a.ins("CLC"); a.ins("ADC_imm", 1)
        a.br("BCS", "rc_dgno")                                             # 255 + 1 -> off the floor
        a.ins("CMP_imm", 16); a.br("BCS", "rc_dgno")
        a.ins("ASL_A"); a.ins("ASL_A"); a.ins("ASL_A"); a.ins16("ORA_abs", V_LO); a.ins("TAY")
        a.ins16("LDA_abs", V_LO); a.ins16("STA_abs", V_TMP)
        a.label("rc_dgl")
        a.jsr("re_cell"); a.br("BCC", "rc_dgno")
        a.ins16("LDA_abs", V_TMP); a.ins16("CMP_abs", V_HI); a.br("BEQ", "rc_dgok")
        a.ins16("INC_abs", V_TMP); a.ins("INY"); a.jmp("rc_dgl")
        a.label("rc_dgno"); a.jmp("rc_no")
        a.label("rc_dgok")
    # r = row(ti) ; fits(x + sd, r, vert)
    a.ins("LDA_zp", R_FL); a.ins("STA_zp", RW_L); a.ins("LDA_zp", R_FH); a.ins("STA_zp", RW_H)
    a.jsr("rx_row"); a.ins("STA_zp", R_R)
    a.ins("LDA_zp", R_X); a.ins("CLC"); a.ins("ADC_zp", R_SD); a.ins("STA_zp", R_FX)
    a.ins("LDA_zp", R_R); a.ins("STA_zp", R_FR); a.ins("LDA_zp", R_VRT); a.ins("STA_zp", R_FV)
    a.jsr("rx_fits"); a.br("BCS", "rc_l3"); a.jmp("rc_no")
    a.label("rc_l3")
    a.ins("LDA_zp", R_FX); a.ins("STA_zp", R_X)
    a.ins("LDA_zp", R_R); a.ins("STA_zp", R_FR); a.jsr("rx_rest"); a.ins("LDA_zp", R_FR); a.jsr("rx_tick")
    # next ti: i == 1 -> t1 + 16 ; else ti + 6
    a.ins("LDA_zp", R_I); a.ins("CMP_imm", 1); a.br("BNE", "rc_t6")
    a.ins16("LDA_abs", V_T1L); a.ins("CLC"); a.ins("ADC_imm", 16); a.ins("STA_zp", R_FL)
    a.ins16("LDA_abs", V_T1H); a.ins("ADC_imm", 0); a.ins("STA_zp", R_FH); a.jmp("rc_tn")
    a.label("rc_t6")
    a.ins("LDA_zp", R_FL); a.ins("CLC"); a.ins("ADC_imm", 6); a.ins("STA_zp", R_FL)
    a.ins("LDA_zp", R_FH); a.ins("ADC_imm", 0); a.ins("STA_zp", R_FH)
    a.label("rc_tn")
    a.ins("INC_zp", R_I); a.jmp("rc_ll")
    # final: rest(x, r, vert) == straight rest (vert: top[x]-1 ; H: min(top[x],top[x+1])-1)
    a.label("rc_fin")
    a.ins("LDA_zp", R_X); a.ins("STA_zp", R_FX); a.ins("LDA_zp", R_R); a.ins("STA_zp", R_FR)
    a.ins("LDA_zp", R_VRT); a.ins("STA_zp", R_FV)
    a.jsr("rx_rest")
    a.ins("LDX_zp", R_X)
    a.ins("LDA_zp", R_VRT); a.br("BEQ", "rc_fh")
    a.ins16("LDA_absX", TOP); a.ins("SEC"); a.ins("SBC_imm", 1); a.jmp("rc_fc")
    a.label("rc_fh")
    a.jsr("rx_srh")
    a.label("rc_fc")
    a.ins("CMP_zp", R_FR); a.br("BNE", "rc_no")
    a.ins("SEC"); a.ins("RTS")
    a.label("rc_no")
    a.ins("CLC"); a.ins("RTS")

    # ================= helpers =================
    # rx_srh: X = x (<= 6) -> A = min(top[x], top[x+1]) - 1
    a.label("rx_srh")
    a.ins16("LDA_absX", TOP); a.ins16("CMP_absX", TOP + 1); a.br("BCC", "rs_m")
    a.ins16("LDA_absX", TOP + 1)
    a.label("rs_m")
    a.ins("SEC"); a.ins("SBC_imm", 1); a.ins("RTS")
    # re_cell: Y = cell index -> C=1 iff LIVE[Y] is empty ($FF or $00)
    a.label("re_cell")
    a.ins16("LDA_absY", LIVE); a.ins("CMP_imm", 0xFF); a.br("BEQ", "re_e")
    a.ins("CMP_imm", 0x00); a.br("BEQ", "re_e")
    a.ins("CLC"); a.ins("RTS")
    a.label("re_e"); a.ins("SEC"); a.ins("RTS")
    # rx_fits: (R_FX, R_FR, R_FV) -> C=1 iff the capsule's cells are empty. Preserves X.
    a.label("rx_fits")
    a.ins("LDA_zp", R_FR); a.ins("CMP_imm", 16); a.br("BCS", "rf_no")
    a.ins("LDA_zp", R_FV); a.br("BNE", "rf_v")
    a.ins("LDA_zp", R_FX); a.ins("CMP_imm", 7); a.br("BCS", "rf_no")
    a.ins("LDA_zp", R_FR); a.ins("ASL_A"); a.ins("ASL_A"); a.ins("ASL_A"); a.ins("ORA_zp", R_FX); a.ins("TAY")
    a.jsr("re_cell"); a.br("BCC", "rf_no")
    a.ins("INY"); a.jsr("re_cell"); a.br("BCC", "rf_no")
    a.ins("SEC"); a.ins("RTS")
    a.label("rf_v")
    a.ins("LDA_zp", R_FX); a.ins("CMP_imm", 8); a.br("BCS", "rf_no")
    a.ins("LDA_zp", R_FR); a.ins("ASL_A"); a.ins("ASL_A"); a.ins("ASL_A"); a.ins("ORA_zp", R_FX); a.ins("TAY")
    a.jsr("re_cell"); a.br("BCC", "rf_no")
    a.ins("LDA_zp", R_FR); a.br("BEQ", "rf_yes")
    a.ins("TYA"); a.ins("SEC"); a.ins("SBC_imm", 8); a.ins("TAY")
    a.jsr("re_cell"); a.br("BCC", "rf_no")
    a.label("rf_yes"); a.ins("SEC"); a.ins("RTS")
    a.label("rf_no"); a.ins("CLC"); a.ins("RTS")
    # rx_rest: fall from (R_FX, R_FR, R_FV) while the next row fits -> R_FR = rest row
    a.label("rx_rest")
    a.ins("INC_zp", R_FR); a.jsr("rx_fits"); a.br("BCS", "rx_rest")
    a.ins("DEC_zp", R_FR); a.ins("RTS")
    # rx_tick: A = rest row -> (R_LKL, R_LKH) = TICK[row] ($FFFF if row >= 16)
    a.label("rx_tick")
    a.ins("CMP_imm", 16); a.br("BCS", "rt_big")
    a.ins("TAX"); a.ins16("LDA_absX", TICKL); a.ins("STA_zp", R_LKL); a.ins16("LDA_absX", TICKH); a.ins("STA_zp", R_LKH)
    a.ins("RTS")
    a.label("rt_big"); a.ins("LDA_imm", 0xFF); a.ins("STA_zp", R_LKL); a.ins("STA_zp", R_LKH); a.ins("RTS")
    # rx_row: t in (RW_L, RW_H) -> A = row_at(t) = 0 if t < G0+thr else (t-G0-thr) div (thr+1) + 1 (sat 255).
    # Destroys RW_L/RW_H. Preserves Y.
    a.label("rx_row")
    a.ins("LDA_zp", RW_L); a.ins("SEC"); a.ins16("SBC_abs", V_G0T); a.ins("STA_zp", RW_L)
    a.ins("LDA_zp", RW_H); a.ins("SBC_imm", 0); a.ins("STA_zp", RW_H)
    a.br("BCS", "rr_ge"); a.ins("LDA_imm", 0); a.ins("RTS")
    a.label("rr_ge")
    a.ins("LDX_imm", 1)
    a.label("rr_l")
    a.ins("LDA_zp", RW_H); a.br("BNE", "rr_sub")
    a.ins("LDA_zp", RW_L); a.ins("CMP_zp", R_TP1); a.br("BCC", "rr_d")
    a.label("rr_sub")
    a.ins("LDA_zp", RW_L); a.ins("SEC"); a.ins("SBC_zp", R_TP1); a.ins("STA_zp", RW_L)
    a.ins("LDA_zp", RW_H); a.ins("SBC_imm", 0); a.ins("STA_zp", RW_H)
    a.ins("CPX_imm", 0xFF); a.br("BEQ", "rr_d")
    a.ins("INX"); a.jmp("rr_l")
    a.label("rr_d")
    a.ins("TXA"); a.ins("RTS")
    # ================= tables =================
    a.label("rm_speedtab"); a.raw(*SPEED_TABLE)
    a.label("rm_base"); a.raw(*SPEED_BASE)
    a.label("rm_nrot"); a.raw(*NROT_O4)


def _lda_absx_label(a, label):
    """LDA <label>,X with the label resolved at assemble time (same idiom as test_search_d3._lda_absx_label)."""
    a.code.append(patch_vs_cpu.OPS["LDA_absX"])
    a.fixups.append((len(a.code), "abs", label))
    a.code.append(0x00); a.code.append(0x00)
