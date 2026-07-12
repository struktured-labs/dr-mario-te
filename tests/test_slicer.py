#!/usr/bin/env python3
"""Resumable SLICER — the cartridge form of search_firstply (INTEGRATION_SPEC §slicing).
State lives in RAM ($0190+, absolute) so it persists across per-frame calls; each
`slice` call does exactly ONE placement eval (or skips illegal cursors cheaply),
and on cursor-exhaustion publishes the best (col,orient) and latches ST_MODE=DONE.

Validated in py65 by driving arm -> slice* -> DONE and confirming the slicer picks
the SAME (col,orient) as the monolithic golden_search over the same 400 boards,
AND that it does exactly one eval per slice (resumability is real).
"""
import sys, os, random
sys.path.insert(0, os.path.dirname(__file__))
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from py65_harness import Cpu
from patch_vs_cpu import Asm6502
import primitives
from primitives import (emit_all, emit_kernel, emit_kernel_wc, emit_copy_place, emit_first_occ, EMPTY, ROWS, COLS,
                        RV_CELLS, RV_VIR, SH_MAXH, SH_HOLES, SH_TOPRISK,
                        Z_OFFA, Z_OFFB, Z_TILEA, Z_TILEB)
from test_search import golden_search, rand_board, BIAS, score_components, first_occ
from test_resolve import py_find_clears, py_gravity


def golden_capped(board, pca, pcb):
    """Cap=1 golden: one find_clears + gravity (no cascade loop) -- matches the
    cartridge resolve_capped. 0.5% divergence from the full cascade (measured)."""
    best = -1; key = None; cands = []
    for c in range(COLS):
        fo = first_occ(board, c)
        if fo >= 2: cands.append((0, c, (fo-2)*COLS+c, (fo-1)*COLS+c))
    for c in range(COLS-1):
        fo = min(first_occ(board, c), first_occ(board, c+1))
        if fo >= 1: cands.append((1, c, (fo-1)*COLS+c, (fo-1)*COLS+c+1))
    for orient, c, offa, offb in cands:
        b = list(board); b[offa] = 0x40|pca; b[offb] = 0x40|pcb
        cells, vir = py_find_clears(b)
        if cells: py_gravity(b)
        from test_shape_eval import golden_shape
        mh, ho, tr = golden_shape(b)
        s = score_components(vir, cells, mh, ho, tr)
        if s > best: best = s; key = (orient, c)
    return key, best

BASE = 0x4000
# --- driver state in RAM (absolute; persists across slices) ---
ST_MODE  = 0x01C0   # 0 IDLE / 1 SEARCHING / 2 DONE
SE_COL   = 0x01C1
SE_ORIENT= 0x01C2
SE_BCOL  = 0x01C3
SE_BORIENT=0x01C4
SE_BESTLO= 0x01C5
SE_BESTHI= 0x01C6
SE_PCA   = 0x01C7
SE_PCB   = 0x01C8
ST_BUSY  = 0x01C9
ST_PHASE = 0x01CA   # resumable eval phase: 0 LAND(copy+place) 1 CLEAR 2 GRAV 3 SHAPE
# --- CROSS-FRAME persistent shadows of the zp temps (validated-free $01xx RAM) ---
# The phase machine keeps pill tiles/offsets/clear-counts live ACROSS frames, but the
# game's NMI runs between our frames and may clobber zp. "Game-safe zp" only holds
# WITHIN one NMI call -- not across frames. So the authoritative values live here and
# each phase reloads its zp temps from these shadows at entry. (Confirmed live: with
# zp-only persistence the AI spread well but cleared 0 -- wrong-colored Z_TILE.)
ST_TILEA = 0x01CB   # shadow Z_TILEA ($D9): pill color A, set once per pill
ST_TILEB = 0x01CC   # shadow Z_TILEB ($DB): pill color B
ST_OFFA  = 0x01CD   # shadow Z_OFFA  ($DC): placed-cell A offset (LAND->CLEAR)
ST_OFFB  = 0x01CE   # shadow Z_OFFB  ($DE): placed-cell B offset
ST_RVC   = 0x01CF   # shadow RV_CELLS($E0): cleared cells (CLEAR->SHAPE)
ST_RVV   = 0x01D0   # shadow RV_VIR  ($E1): cleared viruses
PUB_DD   = 0x00DD   # publish target column (wrapper reads)
PUB_DA   = 0x00DA   # publish target orient  (wrapper reads)
# pool zp temps reused for score / landing (same as the verified diet)
SE_SLO, SE_SHI, SE_T, T_LO, T_HI, SE_FOL = 0xCA, 0xCB, 0xCC, 0xCD, 0xCE, 0xCB
WV = 18


def build_slicer(wc=False, base=BASE):
    a = Asm6502(base)

    # ============ dispatch: the SINGLE unit-1 entry per frame (cartridge) ============
    # One bank-switch wraps this. Does the new-pill edge check + arm IN unit-1, then a
    # slice. Avoids a second bank-switched call. $DF is updated by the fixed-bank wrapper.
    a.label("dispatch")
    a.ins16("LDA_abs", 0x0386); a.ins("CMP_zp", 0xDF)   # P2y vs last-y
    a.br("BCC", "d_slice"); a.br("BEQ", "d_slice")       # not a new pill -> just slice
    a.ins16("LDA_abs", 0x0381); a.ins16("STA_abs", SE_PCA)   # new pill: read colors
    a.ins16("LDA_abs", 0x0382); a.ins16("STA_abs", SE_PCB)
    a.jsr("arm")
    a.label("d_slice")
    a.jsr("slice")
    a.ins("RTS")

    # ================= arm: start a fresh search (called per new pill) =================
    a.label("arm")
    a.ins("LDA_imm", 1); a.ins16("STA_abs", ST_MODE)
    a.ins("LDA_imm", 0)
    a.ins16("STA_abs", SE_COL); a.ins16("STA_abs", SE_ORIENT)
    a.ins16("STA_abs", SE_BESTLO); a.ins16("STA_abs", SE_BESTHI)
    a.ins16("STA_abs", ST_BUSY); a.ins16("STA_abs", ST_PHASE)   # start at PHASE 0 LAND
    a.ins("LDA_imm", 0xFF); a.ins16("STA_abs", SE_BCOL); a.ins16("STA_abs", SE_BORIENT)
    # tiles set ONCE here from the pill colors; ALSO write the cross-frame shadow so
    # PHASE 0 can reload them every placement (zp may be clobbered between frames).
    a.ins16("LDA_abs", SE_PCA); a.ins("ORA_imm", 0x40)
    a.ins("STA_zp", Z_TILEA); a.ins16("STA_abs", ST_TILEA)
    a.ins16("LDA_abs", SE_PCB); a.ins("ORA_imm", 0x40)
    a.ins("STA_zp", Z_TILEB); a.ins16("STA_abs", ST_TILEB)
    a.ins("RTS")

    # ================= slice: ONE bounded eval PHASE per frame (resumable) =================
    # The cartridge NMI-hook budget is only ~8-10k cyc/frame, so a full atomic eval
    # (~13-24k) overruns and corrupts. We split each placement eval into phases, ONE
    # per frame, each <= ~8k: 0 LAND(copy+place) 1 CLEAR(find_clears) 2 GRAV 3 SHAPE+score.
    # WORK board lives in validated-free RAM; pill tiles/offsets/clear-counts persist via
    # the ST_* shadows (reloaded at each phase entry -- raw zp doesn't survive frames).
    a.label("slice")
    # guards use inverted branch + local RTS (sl_rts is now >127 B away)
    a.ins16("LDA_abs", ST_BUSY); a.br("BEQ", "sl_notbusy"); a.ins("RTS")
    a.label("sl_notbusy")
    a.ins16("LDA_abs", ST_MODE); a.ins("CMP_imm", 1); a.br("BEQ", "sl_go"); a.ins("RTS")
    a.label("sl_go")
    a.ins16("INC_abs", ST_BUSY)
    a.ins16("LDA_abs", ST_PHASE); a.br("BNE", "ph_notland")
    # --- PHASE 0 LAND: find next legal cursor (cheap illegal-skips), copy+place ---
    # reload pill tiles from the cross-frame shadow (zp may be clobbered since arm)
    a.ins16("LDA_abs", ST_TILEA); a.ins("STA_zp", Z_TILEA)
    a.ins16("LDA_abs", ST_TILEB); a.ins("STA_zp", Z_TILEB)
    a.label("ph_land")
    a.jsr("landing_current")                        # A=1 legal (Z_OFFA/B set) / 0 illegal
    a.ins("CMP_imm", 1); a.br("BEQ", "ph_land_ok")
    a.jsr("advance")                                # illegal -> advance cursor (may DONE)
    a.ins16("LDA_abs", ST_MODE); a.ins("CMP_imm", 1); a.br("BEQ", "ph_land")  # keep skipping
    a.jmp("sl_yield")                               # exhausted -> DONE
    a.label("ph_land_ok")
    # persist the placed-cell offsets for PHASE 1 (which runs a frame later)
    a.ins("LDA_zp", Z_OFFA); a.ins16("STA_abs", ST_OFFA)
    a.ins("LDA_zp", Z_OFFB); a.ins16("STA_abs", ST_OFFB)
    a.jsr("copy_place"); a.ins("LDA_imm", 1); a.ins16("STA_abs", ST_PHASE)
    a.jmp("sl_yield")
    a.label("ph_notland")
    a.ins("CMP_imm", 1); a.br("BNE", "ph_notclear")
    # --- PHASE 1 CLEAR: find_clears_targeted on WORK; branch to GRAV or SHAPE ---
    a.ins16("LDA_abs", ST_OFFA); a.ins("STA_zp", Z_OFFA)   # reload offsets from shadow
    a.ins16("LDA_abs", ST_OFFB); a.ins("STA_zp", Z_OFFB)
    a.jsr("find_clears_targeted")
    a.ins("LDA_zp", primitives.PASS_CELLS); a.ins("STA_zp", RV_CELLS); a.ins16("STA_abs", ST_RVC)
    a.ins("LDA_zp", primitives.PASS_VIR); a.ins("STA_zp", RV_VIR); a.ins16("STA_abs", ST_RVV)
    a.ins("LDA_zp", RV_CELLS); a.br("BEQ", "ph_clear_none")
    a.ins("LDA_imm", 2); a.ins16("STA_abs", ST_PHASE); a.jmp("sl_yield")  # cleared -> GRAV
    a.label("ph_clear_none")
    a.ins("LDA_imm", 3); a.ins16("STA_abs", ST_PHASE); a.jmp("sl_yield")  # -> SHAPE
    a.label("ph_notclear")
    a.ins("CMP_imm", 2); a.br("BNE", "ph_shape")
    # --- PHASE 2 GRAV: settle WORK once ---
    a.jsr("gravity")
    a.ins("LDA_imm", 3); a.ins16("STA_abs", ST_PHASE); a.jmp("sl_yield")
    # --- PHASE 3 SHAPE: shape + score + keep-best + advance cursor; phase -> LAND ---
    a.label("ph_shape")
    a.ins16("LDA_abs", ST_RVC); a.ins("STA_zp", RV_CELLS)  # reload clear-counts from shadow
    a.ins16("LDA_abs", ST_RVV); a.ins("STA_zp", RV_VIR)
    a.jsr("shape")
    a.jsr("score_update")
    a.jsr("advance")                                # next placement (may publish+DONE)
    a.ins("LDA_imm", 0); a.ins16("STA_abs", ST_PHASE)
    a.label("sl_yield")
    a.ins16("DEC_abs", ST_BUSY)
    a.label("sl_rts")
    a.ins("RTS")

    # ----- landing_current: compute Z_OFFA/Z_OFFB for (SE_ORIENT,SE_COL). A=1 legal / 0 illegal -----
    a.label("landing_current")
    a.ins16("LDA_abs", SE_ORIENT); a.br("BNE", "te_h")
    # vertical: fo=first_occ(col); legal if fo>=2; offb=(fo-1)*8+col, offa=offb-8
    a.ins16("LDX_abs", SE_COL); a.jsr("first_occ")     # A=fo
    a.ins("CMP_imm", 2); a.br("BCC", "te_skip")
    a.ins("ASL_A"); a.ins("ASL_A"); a.ins("ASL_A"); a.ins("STA_zp", SE_T)  # fo*8
    a.ins("LDA_zp", SE_T); a.ins("SEC"); a.ins("SBC_imm", 8)
    a.ins("CLC"); a.ins16("ADC_abs", SE_COL); a.ins("STA_zp", Z_OFFB)
    a.ins("LDA_zp", Z_OFFB); a.ins("SEC"); a.ins("SBC_imm", 8); a.ins("STA_zp", Z_OFFA)
    a.jmp("te_eval")
    a.label("te_h")
    # horizontal: fo=min(first_occ(col),first_occ(col+1)); legal if fo>=1
    a.ins16("LDX_abs", SE_COL); a.jsr("first_occ"); a.ins("STA_zp", SE_FOL)
    a.ins16("LDX_abs", SE_COL); a.ins("INX"); a.jsr("first_occ")
    a.ins("CMP_zp", SE_FOL); a.br("BCC", "te_hmin"); a.ins("LDA_zp", SE_FOL)
    a.label("te_hmin")
    a.ins("CMP_imm", 1); a.br("BCC", "te_skip")
    a.ins("ASL_A"); a.ins("ASL_A"); a.ins("ASL_A")
    a.ins("SEC"); a.ins("SBC_imm", 8); a.ins("CLC"); a.ins16("ADC_abs", SE_COL); a.ins("STA_zp", Z_OFFA)
    a.ins("LDA_zp", Z_OFFA); a.ins("CLC"); a.ins("ADC_imm", 1); a.ins("STA_zp", Z_OFFB)
    a.label("te_eval")
    a.ins("LDA_imm", 1); a.ins("RTS")        # legal: Z_OFFA/Z_OFFB set
    a.label("te_skip")
    a.ins("LDA_imm", 0); a.ins("RTS")        # illegal, skipped

    # ----- score_update: 16-bit score of the already-resolved WORK board + keep-best -----
    # (was eval_one; the kernel is now the phased LAND/CLEAR/GRAV/SHAPE machine. PHASE 3
    #  already ran shape() -> SH_MAXH/SH_HOLES/SH_TOPRISK and RV_VIR/RV_CELLS hold counts.)
    a.label("score_update")
    a.ins("LDA_imm", BIAS & 0xFF); a.ins("STA_zp", SE_SLO)
    a.ins("LDA_imm", (BIAS >> 8) & 0xFF); a.ins("STA_zp", SE_SHI)
    # + 18*vir
    a.ins("LDA_zp", RV_VIR); a.ins("ASL_A"); a.ins("ASL_A"); a.ins("ASL_A"); a.ins("ASL_A"); a.ins("STA_zp", SE_T)
    a.ins("LDA_zp", RV_VIR); a.ins("ASL_A"); a.ins("CLC"); a.ins("ADC_zp", SE_T); a.ins("STA_zp", SE_T)
    a.ins("LDA_zp", SE_SLO); a.ins("CLC"); a.ins("ADC_zp", SE_T); a.ins("STA_zp", SE_SLO)
    a.ins("LDA_zp", SE_SHI); a.ins("ADC_imm", 0); a.ins("STA_zp", SE_SHI)
    # + cells
    a.ins("LDA_zp", SE_SLO); a.ins("CLC"); a.ins("ADC_zp", RV_CELLS); a.ins("STA_zp", SE_SLO)
    a.ins("LDA_zp", SE_SHI); a.ins("ADC_imm", 0); a.ins("STA_zp", SE_SHI)
    # - maxh
    a.ins("LDA_zp", SE_SLO); a.ins("SEC"); a.ins("SBC_zp", SH_MAXH); a.ins("STA_zp", SE_SLO)
    a.ins("LDA_zp", SE_SHI); a.ins("SBC_imm", 0); a.ins("STA_zp", SE_SHI)
    # - 3*holes
    a.ins("LDA_zp", SH_HOLES); a.ins("ASL_A"); a.ins("STA_zp", T_LO)
    a.ins("LDA_imm", 0); a.ins("STA_zp", T_HI)
    a.ins("LDA_zp", T_LO); a.ins("CLC"); a.ins("ADC_zp", SH_HOLES); a.ins("STA_zp", T_LO)
    a.ins("LDA_zp", T_HI); a.ins("ADC_imm", 0); a.ins("STA_zp", T_HI)
    a.ins("LDA_zp", SE_SLO); a.ins("SEC"); a.ins("SBC_zp", T_LO); a.ins("STA_zp", SE_SLO)
    a.ins("LDA_zp", SE_SHI); a.ins("SBC_zp", T_HI); a.ins("STA_zp", SE_SHI)
    # - 5*toprisk
    a.ins("LDA_zp", SH_TOPRISK); a.ins("ASL_A"); a.ins("ASL_A"); a.ins("STA_zp", SE_T)
    a.ins("LDA_zp", SH_TOPRISK); a.ins("CLC"); a.ins("ADC_zp", SE_T); a.ins("STA_zp", SE_T)
    a.ins("LDA_zp", SE_SLO); a.ins("SEC"); a.ins("SBC_zp", SE_T); a.ins("STA_zp", SE_SLO)
    a.ins("LDA_zp", SE_SHI); a.ins("SBC_imm", 0); a.ins("STA_zp", SE_SHI)
    # compare score > best (unsigned 16-bit, strict keep-first)
    a.ins("LDA_zp", SE_SHI); a.ins16("CMP_abs", SE_BESTHI); a.br("BCC", "eo_no"); a.br("BNE", "eo_yes")
    a.ins("LDA_zp", SE_SLO); a.ins16("CMP_abs", SE_BESTLO); a.br("BCC", "eo_no"); a.br("BEQ", "eo_no")
    a.label("eo_yes")
    a.ins("LDA_zp", SE_SLO); a.ins16("STA_abs", SE_BESTLO)
    a.ins("LDA_zp", SE_SHI); a.ins16("STA_abs", SE_BESTHI)
    a.ins16("LDA_abs", SE_COL); a.ins16("STA_abs", SE_BCOL)
    a.ins16("LDA_abs", SE_ORIENT); a.ins16("STA_abs", SE_BORIENT)
    a.label("eo_no")
    a.ins("RTS")

    # ----- advance: next cursor; on exhaustion publish + ST_MODE=DONE -----
    a.label("advance")
    a.ins16("INC_abs", SE_COL)
    a.ins16("LDA_abs", SE_ORIENT); a.br("BNE", "ad_h")
    a.ins16("LDA_abs", SE_COL); a.ins("CMP_imm", COLS); a.br("BNE", "ad_done")  # vert col 0..7
    a.ins("LDA_imm", 1); a.ins16("STA_abs", SE_ORIENT)
    a.ins("LDA_imm", 0); a.ins16("STA_abs", SE_COL); a.jmp("ad_done")
    a.label("ad_h")
    a.ins16("LDA_abs", SE_COL); a.ins("CMP_imm", COLS - 1); a.br("BNE", "ad_done")  # horiz col 0..6
    a.jsr("publish"); a.ins("LDA_imm", 2); a.ins16("STA_abs", ST_MODE)
    a.label("ad_done")
    a.ins("RTS")

    # ----- publish: write target where the wrapper reads it. Store $DD,$DA FIRST,
    #       ST_MODE=DONE LAST (done by caller) so the wrapper never reads a torn pair.
    #       Topout fallback (SE_BCOL==$FF): safe col 3, orient 0. -----
    a.label("publish")
    a.ins16("LDA_abs", SE_BCOL); a.ins("CMP_imm", 0xFF); a.br("BNE", "pb_ok")
    a.ins("LDA_imm", 3); a.ins16("STA_abs", PUB_DD); a.ins("LDA_imm", 0); a.ins16("STA_abs", PUB_DA)
    a.ins("RTS")
    a.label("pb_ok")
    a.ins16("LDA_abs", SE_BCOL); a.ins16("STA_abs", PUB_DD)
    # orient encode: SE_BORIENT 1(horiz)->$03A5=0 (spawn default); 0(vert,PCA upper)->$03A5=3 (V a-top).
    # (Mesen-confirmed: P2 pill spawns horizontal $03A5=0; colors $0381 left/A, $0382 right/B.)
    a.ins16("LDA_abs", SE_BORIENT); a.br("BNE", "pb_horiz")
    a.ins("LDA_imm", 3); a.jmp("pb_setDA")               # vertical -> $DA=3
    a.label("pb_horiz")
    a.ins("LDA_imm", 0)                                   # horizontal -> $DA=0
    a.label("pb_setDA")
    a.ins16("STA_abs", PUB_DA)
    a.ins("RTS")

    emit_all(a)                     # resolve*/find_clears(+targeted)/gravity/shape
    emit_copy_place(a)              # PHASE 0 LAND uses this (both py65 + cartridge)
    emit_first_occ(a)
    return a.assemble(), a.labels


def main():
    import statistics
    # The phase machine keeps a WORK board separate from the LIVE settled board
    # ($0500), exactly like the cartridge (WORK=$0600, MARK=$068C). copy_place
    # copies LIVE->WORK fresh each placement; if WORK==LIVE it would accumulate.
    primitives.BOARD = 0x0600
    primitives.MARK = 0x068C
    code, labels = build_slicer()
    arm_addr = BASE + labels["arm"]; slice_addr = BASE + labels["slice"]
    rng = random.Random(31337)   # same seed as test_search for matching boards
    cpu = Cpu(); cpu.load(BASE, code)
    fails = 0; n = 400; slice_counts = []
    for t in range(n):
        board = rand_board(rng)
        pca, pcb = rng.randint(0, 2), rng.randint(0, 2)
        cpu.set_board(board)
        cpu.mem[SE_PCA] = pca; cpu.mem[SE_PCB] = pcb
        cpu.call(arm_addr)
        nsl = 0
        # phase machine: ~3-4 calls per legal placement (LAND/CLEAR/[GRAV]/SHAPE)
        while cpu.mem[ST_MODE] != 2 and nsl < 300:
            cpu.call(slice_addr); nsl += 1
        slice_counts.append(nsl)
        got = (cpu.mem[SE_BORIENT], cpu.mem[SE_BCOL])
        gkey, gbest = golden_capped(board, pca, pcb)
        gotbest = cpu.mem[SE_BESTLO] | (cpu.mem[SE_BESTHI] << 8)
        # also: published $DD == chosen col, $DA == encoded orient (0=horiz, 3=vert)
        exp_da = 0 if cpu.mem[SE_BORIENT] == 1 else 3
        pub_ok = (cpu.mem[PUB_DD] == cpu.mem[SE_BCOL] and cpu.mem[PUB_DA] == exp_da)
        if got != gkey or gotbest != gbest or not pub_ok:
            fails += 1
            if fails <= 8:
                print(f"  MISMATCH t={t}: got=(o{got[0]},c{got[1]},s{gotbest}) "
                      f"exp=(o{gkey[0]},c{gkey[1]},s{gbest}) slices={nsl} pub_ok={pub_ok}")
    print(f"routine size = {len(code)} bytes")
    print(f"validation: {n - fails}/{n} slicer picks == monolithic search + publish (fails={fails})")
    print(f"slices/search: min={min(slice_counts)} max={max(slice_counts)} avg={statistics.mean(slice_counts):.1f}")
    sys.exit(1 if fails else 0)


if __name__ == "__main__":
    main()
