#!/usr/bin/env python3
"""6502 ports of the 3 depth-2 'progress' eval terms, validated cell-exact in
py65 against NES-board goldens (which xcheck 400/400 vs the faithful sim):
  - buried:   per virus, occupied cells stacked above it in its column. -> 16-bit
  - readiness:per virus, max same-color run through it (row|col), sum run^2. -> 16-bit
  - setup:    length-3 same-color runs (row|col) touching a same-color virus. -> 8-bit
These three lift cart depth-2 from 22% to 70% on L11.
"""
import sys, os, random
sys.path.insert(0, os.path.dirname(__file__))
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from py65_harness import Cpu
from patch_vs_cpu import Asm6502

EMPTY = 0xFF
ROWS, COLS = 16, 8
BOARD = 0x0500
BASE = 0x4000


# ----------------------- NES-board goldens (== faithful, xcheck'd) -----------------------
def _col(b, o):
    return -1 if b[o] == EMPTY else (b[o] & 0x0F)

def _isvir(b, o):
    return b[o] != EMPTY and (b[o] & 0xF0) == 0xD0

def g_buried(b):
    total = 0
    for c in range(COLS):
        for r in range(ROWS):
            o = r * COLS + c
            if _isvir(b, o):
                for rr in range(r):
                    if b[rr * COLS + c] != EMPTY:
                        total += 1
    return total

def g_readiness(b):
    total = 0
    for r in range(ROWS):
        for c in range(COLS):
            o = r * COLS + c
            if not _isvir(b, o):
                continue
            color = b[o] & 0x0F
            hr = 1; cc = c - 1
            while cc >= 0 and _col(b, r * COLS + cc) == color:
                hr += 1; cc -= 1
            cc = c + 1
            while cc < COLS and _col(b, r * COLS + cc) == color:
                hr += 1; cc += 1
            vr = 1; rr = r - 1
            while rr >= 0 and _col(b, rr * COLS + c) == color:
                vr += 1; rr -= 1
            rr = r + 1
            while rr < ROWS and _col(b, rr * COLS + c) == color:
                vr += 1; rr += 1
            total += max(hr, vr) ** 2
    return total

def g_setup(b):
    def axis(get, n_line, n_along):
        cnt = 0
        for line in range(n_line):
            for i in range(n_along - 2):
                o0, o1, o2 = get(line, i), get(line, i + 1), get(line, i + 2)
                c0 = _col(b, o0)
                if c0 == -1 or _col(b, o1) != c0 or _col(b, o2) != c0:
                    continue
                touch = any(_isvir(b, o) and (b[o] & 0x0F) == c0 for o in (o0, o1, o2))
                if not touch and i - 1 >= 0:
                    op = get(line, i - 1); touch = _isvir(b, op) and (b[op] & 0x0F) == c0
                if not touch and i + 3 < n_along:
                    on = get(line, i + 3); touch = _isvir(b, on) and (b[on] & 0x0F) == c0
                if touch:
                    cnt += 1
        return cnt
    return (axis(lambda L, i: L * COLS + i, ROWS, COLS) +
            axis(lambda L, i: i * COLS + L, COLS, ROWS))


# ----------------------- 6502 routines -----------------------
# I/O zero page (standalone test; addresses don't matter for validation)
O_LO, O_HI = 0xE0, 0xE1
T0, T1, T2, T3, T4, T5, T6 = 0xE2, 0xE3, 0xE4, 0xE5, 0xE6, 0xE7, 0xE8


def emit_buried(a):
    a.label("buried")
    a.ins("LDA_imm", 0); a.ins("STA_zp", O_LO); a.ins("STA_zp", O_HI); a.ins("STA_zp", T1)  # T1=col
    a.label("bu_col")
    a.ins("LDA_zp", T1); a.ins("STA_zp", T0)          # T0 = offset (row 0)
    a.ins("LDY_imm", 0)                                # Y = occupied-above
    a.ins("LDA_imm", ROWS); a.ins("STA_zp", T2)        # T2 = row counter
    a.label("bu_cell")
    a.ins("LDX_zp", T0); a.ins16("LDA_absX", BOARD); a.ins("CMP_imm", EMPTY); a.br("BEQ", "bu_next")
    a.ins("AND_imm", 0xF0); a.ins("CMP_imm", 0xD0); a.br("BNE", "bu_occ")
    # virus: total += Y
    a.ins("TYA"); a.ins("CLC"); a.ins("ADC_zp", O_LO); a.ins("STA_zp", O_LO)
    a.ins("LDA_zp", O_HI); a.ins("ADC_imm", 0); a.ins("STA_zp", O_HI)
    a.label("bu_occ")
    a.ins("INY")
    a.label("bu_next")
    a.ins("LDA_zp", T0); a.ins("CLC"); a.ins("ADC_imm", 8); a.ins("STA_zp", T0)
    a.ins("DEC_zp", T2); a.br("BNE", "bu_cell")
    a.ins("INC_zp", T1); a.ins("LDA_zp", T1); a.ins("CMP_imm", COLS); a.br("BNE", "bu_col")
    a.ins("RTS")


def emit_readiness(a):
    # T0=off, T1=color, T2=row, T3=run accumulator (H then max), T4=scan offset, T5=V run
    a.label("readiness")
    a.ins("LDA_imm", 0); a.ins("STA_zp", O_LO); a.ins("STA_zp", O_HI); a.ins("STA_zp", T0)
    a.label("rd_cell")
    a.ins("LDX_zp", T0); a.ins16("LDA_absX", BOARD); a.ins("CMP_imm", EMPTY); a.br("BNE", "rd_c1"); a.jmp("rd_next")
    a.label("rd_c1")
    a.ins("AND_imm", 0xF0); a.ins("CMP_imm", 0xD0); a.br("BEQ", "rd_c2"); a.jmp("rd_next")
    a.label("rd_c2")
    a.ins("LDX_zp", T0); a.ins16("LDA_absX", BOARD); a.ins("AND_imm", 0x0F); a.ins("STA_zp", T1)  # color
    a.ins("LDA_zp", T0); a.ins("LSR_A"); a.ins("LSR_A"); a.ins("LSR_A"); a.ins("STA_zp", T2)       # row
    # --- horizontal run -> T3 ---
    a.ins("LDA_imm", 1); a.ins("STA_zp", T3)
    a.ins("LDA_zp", T0); a.ins("STA_zp", T4)            # scan = off
    a.ins("LDX_zp", T0); a.ins("TXA"); a.ins("AND_imm", 7); a.ins("TAX")  # X = col
    a.label("rd_hl")
    a.ins("CPX_imm", 0); a.br("BEQ", "rd_hr0")
    a.ins("DEX"); a.ins("DEC_zp", T4)
    a.ins("LDY_zp", T4); a.ins16("LDA_absY", BOARD); a.ins("CMP_imm", EMPTY); a.br("BEQ", "rd_hr0")
    a.ins("AND_imm", 0x0F); a.ins("CMP_zp", T1); a.br("BNE", "rd_hr0")
    a.ins("INC_zp", T3); a.jmp("rd_hl")
    a.label("rd_hr0")
    a.ins("LDA_zp", T0); a.ins("STA_zp", T4)
    a.ins("LDA_zp", T0); a.ins("AND_imm", 7); a.ins("TAX")  # X = col
    a.label("rd_hr")
    a.ins("CPX_imm", COLS - 1); a.br("BEQ", "rd_v")
    a.ins("INX"); a.ins("INC_zp", T4)
    a.ins("LDY_zp", T4); a.ins16("LDA_absY", BOARD); a.ins("CMP_imm", EMPTY); a.br("BEQ", "rd_v")
    a.ins("AND_imm", 0x0F); a.ins("CMP_zp", T1); a.br("BNE", "rd_v")
    a.ins("INC_zp", T3); a.jmp("rd_hr")
    # --- vertical run -> T5 ---
    a.label("rd_v")
    a.ins("LDA_imm", 1); a.ins("STA_zp", T5)
    a.ins("LDA_zp", T0); a.ins("STA_zp", T4)
    a.ins("LDX_zp", T2)                                  # X = row
    a.label("rd_vu")
    a.ins("CPX_imm", 0); a.br("BEQ", "rd_vd0")
    a.ins("DEX")
    a.ins("LDA_zp", T4); a.ins("SEC"); a.ins("SBC_imm", 8); a.ins("STA_zp", T4)
    a.ins("LDY_zp", T4); a.ins16("LDA_absY", BOARD); a.ins("CMP_imm", EMPTY); a.br("BEQ", "rd_vd0")
    a.ins("AND_imm", 0x0F); a.ins("CMP_zp", T1); a.br("BNE", "rd_vd0")
    a.ins("INC_zp", T5); a.jmp("rd_vu")
    a.label("rd_vd0")
    a.ins("LDA_zp", T0); a.ins("STA_zp", T4)
    a.ins("LDX_zp", T2)
    a.label("rd_vd")
    a.ins("CPX_imm", ROWS - 1); a.br("BEQ", "rd_max")
    a.ins("INX")
    a.ins("LDA_zp", T4); a.ins("CLC"); a.ins("ADC_imm", 8); a.ins("STA_zp", T4)
    a.ins("LDY_zp", T4); a.ins16("LDA_absY", BOARD); a.ins("CMP_imm", EMPTY); a.br("BEQ", "rd_max")
    a.ins("AND_imm", 0x0F); a.ins("CMP_zp", T1); a.br("BNE", "rd_max")
    a.ins("INC_zp", T5); a.jmp("rd_vd")
    # --- run = max(T3,T5); total += run^2 (two square tables) ---
    a.label("rd_max")
    a.ins("LDA_zp", T3); a.ins("CMP_zp", T5); a.br("BCS", "rd_useh"); a.ins("LDA_zp", T5)
    a.label("rd_useh")
    a.ins("TAX")
    a.ins16("LDA_absX", 0)  # placeholder; patched to SQLO below
    sqlo_fix = len(a.code) - 2
    a.ins("CLC"); a.ins("ADC_zp", O_LO); a.ins("STA_zp", O_LO)
    a.ins16("LDA_absX", 0)  # placeholder SQHI
    sqhi_fix = len(a.code) - 2
    a.ins("ADC_zp", O_HI); a.ins("STA_zp", O_HI)
    a.label("rd_next")
    a.ins("INC_zp", T0); a.ins("LDA_zp", T0); a.ins("CMP_imm", 128); a.br("BEQ", "rd_done"); a.jmp("rd_cell")
    a.label("rd_done")
    a.ins("RTS")
    return ("sqfix", sqlo_fix, sqhi_fix)


def emit_setup(a):
    # T0=line, T1=i, T2=base off, T3=step, T4=color, T5=nline, T6=nalong; output O_LO (8-bit)
    # We run two passes (rows: step=1,nline=16,nalong=8 ; cols: step=8,nline=8,nalong=16)
    a.label("setup")
    a.ins("LDA_imm", 0); a.ins("STA_zp", O_LO)
    # pass 1: rows
    a.ins("LDA_imm", 1); a.ins("STA_zp", T3)
    a.ins("LDA_imm", ROWS); a.ins("STA_zp", T5)
    a.ins("LDA_imm", COLS); a.ins("STA_zp", T6)
    a.jsr("su_pass")
    # pass 2: cols
    a.ins("LDA_imm", 8); a.ins("STA_zp", T3)
    a.ins("LDA_imm", COLS); a.ins("STA_zp", T5)
    a.ins("LDA_imm", ROWS); a.ins("STA_zp", T6)
    a.jsr("su_pass")
    a.ins("RTS")

    # su_pass: iterate line=0..T5-1, i=0..T6-3 ; base = line*(stride) + i*step
    # For rows: base offset of (line,i) = line*8 + i*1.  For cols: line*1 + i*8.
    # The per-line stride = step==1 ? 8 : 1.  Compute base incrementally.
    a.label("su_pass")
    a.ins("LDA_imm", 0); a.ins("STA_zp", T0)            # line
    a.label("su_line")
    # base0 = line * linestride. linestride = (step==1)?8:1
    a.ins("LDA_zp", T3); a.ins("CMP_imm", 1); a.br("BNE", "su_lcol")
    # rows: linestride 8 -> base0 = line*8
    a.ins("LDA_zp", T0); a.ins("ASL_A"); a.ins("ASL_A"); a.ins("ASL_A"); a.jmp("su_lset")
    a.label("su_lcol")
    a.ins("LDA_zp", T0)                                  # cols: linestride 1 -> base0 = line
    a.label("su_lset")
    a.ins("STA_zp", T2)                                  # T2 = base offset for i=0
    a.ins("LDA_imm", 0); a.ins("STA_zp", T1)            # i
    a.label("su_i")
    # window cells base=T2, base+step, base+2step
    a.ins("LDX_zp", T2); a.ins16("LDA_absX", BOARD); a.ins("CMP_imm", EMPTY); a.br("BEQ", "su_iadv")
    a.ins("AND_imm", 0x0F); a.ins("STA_zp", T4)          # c0 color
    # cell1
    a.ins("LDA_zp", T2); a.ins("CLC"); a.ins("ADC_zp", T3); a.ins("TAX")  # X = base+step
    a.ins16("LDA_absX", BOARD); a.ins("CMP_imm", EMPTY); a.br("BEQ", "su_iadv")
    a.ins("AND_imm", 0x0F); a.ins("CMP_zp", T4); a.br("BNE", "su_iadv")
    # cell2
    a.ins("TXA"); a.ins("CLC"); a.ins("ADC_zp", T3); a.ins("TAX")  # X = base+2step
    a.ins16("LDA_absX", BOARD); a.ins("CMP_imm", EMPTY); a.br("BEQ", "su_iadv")
    a.ins("AND_imm", 0x0F); a.ins("CMP_zp", T4); a.br("BNE", "su_iadv")
    # run-of-3 same color confirmed. now TOUCH test -> JSR su_touch (sets carry if touch)
    a.jsr("su_touch")
    a.br("BCC", "su_iadv")
    a.ins("INC_zp", O_LO)
    a.label("su_iadv")
    a.ins("LDA_zp", T2); a.ins("CLC"); a.ins("ADC_zp", T3); a.ins("STA_zp", T2)  # base += step
    a.ins("INC_zp", T1)
    a.ins("LDA_zp", T6); a.ins("SEC"); a.ins("SBC_imm", 2); a.ins("CMP_zp", T1)  # i < nalong-2 ?
    a.br("BNE", "su_i")
    a.ins("INC_zp", T0); a.ins("LDA_zp", T0); a.ins("CMP_zp", T5); a.br("BNE", "su_line")
    a.ins("RTS")

    # su_touch: window base=T2, step=T3, color=T4. Sets C=1 if a same-color virus is
    # in the 3 window cells OR at base-step (i>0) OR base+3step (i+3<nalong). Else C=0.
    a.label("su_touch")
    # check the 3 cells
    a.ins("LDX_zp", T2); a.jsr("su_chkv"); a.br("BCS", "su_t1")
    a.ins("LDA_zp", T2); a.ins("CLC"); a.ins("ADC_zp", T3); a.ins("TAX"); a.jsr("su_chkv"); a.br("BCS", "su_t1")
    a.ins("LDA_zp", T2); a.ins("CLC"); a.ins("ADC_zp", T3); a.ins("CLC"); a.ins("ADC_zp", T3); a.ins("TAX")
    a.jsr("su_chkv"); a.br("BCS", "su_t1")
    # end-adjacent: base-step if i>0
    a.ins("LDA_zp", T1); a.br("BEQ", "su_tend")
    a.ins("LDA_zp", T2); a.ins("SEC"); a.ins("SBC_zp", T3); a.ins("TAX"); a.jsr("su_chkv"); a.br("BCS", "su_t1")
    a.label("su_tend")
    # base+3step if i+3 < nalong  (i < nalong-3 -> i <= nalong-4)
    a.ins("LDA_zp", T6); a.ins("SEC"); a.ins("SBC_imm", 3); a.ins("CMP_zp", T1); a.br("BEQ", "su_t0"); a.br("BCC", "su_t0")
    a.ins("LDA_zp", T2); a.ins("CLC"); a.ins("ADC_zp", T3); a.ins("CLC"); a.ins("ADC_zp", T3)
    a.ins("CLC"); a.ins("ADC_zp", T3); a.ins("TAX"); a.jsr("su_chkv"); a.br("BCS", "su_t1")
    a.label("su_t0")
    a.ins("CLC"); a.ins("RTS")
    a.label("su_t1")
    a.ins("SEC"); a.ins("RTS")

    # su_chkv: X=offset. C=1 if board[X] is a virus with low-nibble==T4, else C=0.
    a.label("su_chkv")
    a.ins16("LDA_absX", BOARD); a.ins("CMP_imm", EMPTY); a.br("BEQ", "su_cv0")
    a.ins("STA_zp", 0xEF)                                   # stash full byte
    a.ins("AND_imm", 0xF0); a.ins("CMP_imm", 0xD0); a.br("BNE", "su_cv0")
    a.ins("LDA_zp", 0xEF); a.ins("AND_imm", 0x0F); a.ins("CMP_zp", T4); a.br("BNE", "su_cv0")
    a.ins("SEC"); a.ins("RTS")
    a.label("su_cv0")
    a.ins("CLC"); a.ins("RTS")


SQUARES = [(i * i) & 0xFF for i in range(17)]
SQUARES_HI = [(i * i) >> 8 for i in range(17)]


def build(routine):
    a = Asm6502(BASE)
    fix = None
    if routine == "buried":
        emit_buried(a)
    elif routine == "readiness":
        fix = emit_readiness(a)
    elif routine == "setup":
        emit_setup(a)
    code = a.assemble()
    extra = {}
    if routine == "readiness":
        # append square tables after the code, patch the two absX operands
        sqlo_addr = BASE + len(code)
        sqhi_addr = sqlo_addr + 17
        code = code + bytes(SQUARES) + bytes(SQUARES_HI)
        _, lo_fix, hi_fix = fix
        code = bytearray(code)
        code[lo_fix] = sqlo_addr & 0xFF; code[lo_fix + 1] = (sqlo_addr >> 8) & 0xFF
        code[hi_fix] = sqhi_addr & 0xFF; code[hi_fix + 1] = (sqhi_addr >> 8) & 0xFF
        code = bytes(code)
    return code, a.labels


def rand_board(rng):
    b = [EMPTY] * 128
    # settled columns with clustered colors to create runs + viruses
    for c in range(COLS):
        h = rng.randint(0, ROWS)
        for r in range(ROWS - h, ROWS):
            roll = rng.random()
            col = rng.randint(0, 2)
            if roll < 0.4:
                b[r * COLS + c] = 0xD0 | col          # virus
            else:
                b[r * COLS + c] = 0x40 | col          # pill cell
    for _ in range(rng.randint(0, 8)):
        b[rng.randint(0, 127)] = EMPTY
    return b


def main():
    rng = random.Random(99)
    total_fail = 0
    for routine, golden, out16 in [("buried", g_buried, True),
                                   ("readiness", g_readiness, True),
                                   ("setup", g_setup, False)]:
        code, labels = build(routine)
        cpu = Cpu(); cpu.load(BASE, code)
        addr = BASE + labels[routine]
        fails = 0; n = 500; cyc_max = 0
        for t in range(n):
            board = rand_board(rng)
            cpu.set_board(board)
            cyc = cpu.call(addr); cyc_max = max(cyc_max, cyc)
            got = cpu.zp(O_LO) | (cpu.zp(O_HI) << 8) if out16 else cpu.zp(O_LO)
            exp = golden(board)
            if got != exp:
                fails += 1
                if fails <= 4:
                    print(f"  [{routine}] MISMATCH t={t}: got={got} exp={exp}")
        total_fail += fails
        print(f"{routine:10}: {n - fails}/{n} match  size={len(code)}B  cyc_max={cyc_max}")
    sys.exit(1 if total_fail else 0)


if __name__ == "__main__":
    main()
