"""DRDIST -- the endgame TARGET for the LeafEval clearing-distance term (STEER6b dist_target60, 2026-09-28).

Once per search, from the untouched ROOT board at LIVE ($0500), before any engine evaluation:
  * count the viruses; if there are none or more than VK (4; env DRDIST_VK): write $70F5 = 0 (no target -> the RTL
    term is exactly 0, so the search is ANTIBODY's before the endgame);
  * else compute every virus's clearing distance D (cascade_leaf6_x._vdist, cap 16, kdig 0) and write
    $70F5 = $80 | index of the SMALLEST D (ties: lowest index r*8+c) -- Leaf6Decider mode "dist_target".
The RTL (LeafEval `DRDIST`) then scores every leaf of the search with -60 * D(target) on the LEAF board.
D (module doc of cascade_leaf6_x): min over the horizontal and vertical windows of 4 through the virus of the cells
still to build -- same colour 0; horizontal empty cell reachable from above: 1 + its support gap = top[c] - vr;
vertical empty cell ABOVE the virus and above the column top: 1; anything else makes the window infeasible.
Self-contained routine at DIST_ROM, JSR'd by the search (test_search_d3, env DRDIST). Absolute RAM only:
$0AE0-$0AF3, clear of reach_6502 ($0A80-$0ADC), TK1 ($0A00-$0A7F) and WORK2 ($0B00). Cost: one 128-cell count
every search (~1.3k cycles); the D scan only with <= VK viruses (~2-6k cycles per virus). Once per decision, not per leaf.
"""
import os as _os
import sys as _sys
for _p in ("/home/struktured/projects/dr-mario-mods/tests", "/home/struktured/projects/dr-mario-mods"):
    if _p not in _sys.path:
        _sys.path.append(_p)
import patch_vs_cpu

for _k, _v in (("ORA_abs", 0x0D), ("INC_abs", 0xEE), ("SBC_abs", 0xED), ("ADC_abs", 0x6D), ("CMP_absX", 0xDD)):
    patch_vs_cpu.OPS.setdefault(_k, _v)

DIST_ROM = 0xA400                 # free window: tuck_bfs ends ~$9DED, reach_6502 starts $A800
LIVE = 0x0500
LEV_TGT = 0x70F5                  # CoproDrMario `DRDIST`: target register, cleared by every GO's copro reset
# DRDIST_VK (2026-10-07, STEER10/13 arm A16): the endgame gate -- a target is chosen with 1..VK viruses on the root.
# Default 4 = byte-identical firmware (1488e158 / c51d2e21). A16 = 16: only the CMP immediate in emit_dist moves, and
# the D scan then also runs on 5..VK-virus boards (its cost grows with the count; gate_dist_fw.py reports it).
VK = int(_os.environ.get("DRDIST_VK", "4"))
assert 1 <= VK <= 127, f"DRDIST_VK={VK}: the gate is CMP #VK+1 on a one-byte virus count"
CAP = 16
DTOP = 0x0AE0                     # 8 B: first occupied row per column (16 = empty)
(D_NV, D_I, D_BEST, D_BIDX, D_VR, D_VC, D_VCOL, D_CUR, D_S, D_COST, D_K, D_T) = range(0x0AE8, 0x0AF4)
DIST_RAM_END = 0x0AF4

# TEST-ONLY mutants (gate_dist_fw.py must kill each; never set by a build)
_MUT = "none"   # "vk5" | "tie_le" | "hwin" | "gap" | "cavity" | "vbelow" | "cap15"


def emit_dist(a):
    mut = _MUT
    a.label("dist_tgt")
    # ---- virus count on the root ----
    a.ins("LDA_imm", 0); a.ins16("STA_abs", D_NV)
    a.ins("LDX_imm", 0)
    a.label("dc_l")
    a.ins16("LDA_absX", LIVE); a.ins("CMP_imm", 0xFF); a.br("BEQ", "dc_n")
    a.ins("AND_imm", 0xF0); a.ins("CMP_imm", 0xD0); a.br("BNE", "dc_n")
    a.ins16("INC_abs", D_NV)
    a.label("dc_n")
    a.ins("INX"); a.ins("CPX_imm", 128); a.br("BNE", "dc_l")
    a.ins16("LDA_abs", D_NV); a.br("BEQ", "dt_off")
    a.ins("CMP_imm", (VK + 2) if mut == "vk5" else (VK + 1)); a.br("BCC", "dt_on")
    a.label("dt_off")
    a.ins("LDA_imm", 0); a.ins16("STA_abs", LEV_TGT)
    a.ins("RTS")
    a.label("dt_on")
    # ---- column tops ----
    a.ins("LDA_imm", 0); a.ins16("STA_abs", D_T)
    a.label("tp_c")
    a.ins16("LDX_abs", D_T); a.ins("LDY_imm", 0)
    a.label("tp_r")
    a.ins16("LDA_absX", LIVE); a.ins("CMP_imm", 0xFF); a.br("BNE", "tp_hit")
    a.ins("TXA"); a.ins("CLC"); a.ins("ADC_imm", 8); a.ins("TAX")
    a.ins("INY"); a.ins("CPY_imm", 16); a.br("BNE", "tp_r")
    a.label("tp_hit")
    a.ins("TYA"); a.ins16("LDX_abs", D_T); a.ins16("STA_absX", DTOP)
    a.ins16("INC_abs", D_T); a.ins16("LDA_abs", D_T); a.ins("CMP_imm", 8); a.br("BNE", "tp_c")
    # ---- every virus: D, keep the smallest (strictly smaller wins -> ties keep the lowest index) ----
    a.ins("LDA_imm", 0xFF); a.ins16("STA_abs", D_BEST); a.ins16("STA_abs", D_BIDX)
    a.ins("LDA_imm", 0); a.ins16("STA_abs", D_I)
    a.label("vl")
    a.ins16("LDX_abs", D_I); a.ins16("LDA_absX", LIVE); a.ins("CMP_imm", 0xFF); a.br("BEQ", "vnext")
    a.ins("AND_imm", 0xF0); a.ins("CMP_imm", 0xD0); a.br("BNE", "vnext")
    a.ins16("LDA_absX", LIVE); a.ins("AND_imm", 0x0F); a.ins16("STA_abs", D_VCOL)
    a.ins("TXA"); a.ins("AND_imm", 7); a.ins16("STA_abs", D_VC)
    a.ins("TXA"); a.ins("LSR_A"); a.ins("LSR_A"); a.ins("LSR_A"); a.ins16("STA_abs", D_VR)
    a.jsr("dist_one")
    a.ins16("LDA_abs", D_CUR); a.ins16("CMP_abs", D_BEST)
    if mut == "tie_le":
        a.br("BEQ", "vtake")
    a.br("BCS", "vnext")
    a.label("vtake")
    a.ins16("STA_abs", D_BEST); a.ins16("LDA_abs", D_I); a.ins16("STA_abs", D_BIDX)
    a.label("vnext")
    a.ins16("INC_abs", D_I); a.ins16("LDA_abs", D_I); a.ins("CMP_imm", 128); a.br("BNE", "vl")
    a.ins16("LDA_abs", D_BIDX); a.ins("ORA_imm", 0x80); a.ins16("STA_abs", LEV_TGT)
    a.ins("RTS")

    # ---- D of the virus at (D_VR, D_VC), colour D_VCOL -> D_CUR (0..16) ----
    a.label("dist_one")
    a.ins("LDA_imm", CAP - 1 if mut == "cap15" else CAP); a.ins16("STA_abs", D_CUR)
    # horizontal windows s = max(0, vc-3) .. min(vc, 4)
    a.ins16("LDA_abs", D_VC); a.ins("SEC"); a.ins("SBC_imm", 3); a.br("BCS", "h_s0"); a.ins("LDA_imm", 0)
    a.label("h_s0"); a.ins16("STA_abs", D_S)
    a.label("h_win")
    a.ins16("LDA_abs", D_S); a.ins("CMP_imm", 5); a.br("BCS", "h_done")
    a.ins16("CMP_abs", D_VC)
    if mut == "hwin":
        a.br("BCS", "h_done")                  # MUTANT: drops the window that STARTS at the virus column
    else:
        a.br("BEQ", "h_go"); a.br("BCS", "h_done")
    a.label("h_go")
    a.ins("LDA_imm", 0); a.ins16("STA_abs", D_COST)
    a.ins16("LDA_abs", D_S); a.ins16("STA_abs", D_K)
    a.label("h_cell")
    a.ins16("LDA_abs", D_K); a.ins16("CMP_abs", D_VC); a.br("BEQ", "h_cn")
    a.ins16("LDA_abs", D_VR); a.ins("ASL_A"); a.ins("ASL_A"); a.ins("ASL_A"); a.ins16("ORA_abs", D_K); a.ins("TAX")
    a.ins16("LDA_absX", LIVE); a.ins("CMP_imm", 0xFF); a.br("BEQ", "h_emp")
    a.ins("AND_imm", 0x0F); a.ins16("CMP_abs", D_VCOL); a.br("BEQ", "h_cn")
    a.jmp("h_inf")                              # wrong colour
    a.label("h_emp")
    a.ins16("LDX_abs", D_K); a.ins16("LDA_absX", DTOP)
    a.ins16("CMP_abs", D_VR)
    if mut == "cavity":
        a.br("BEQ", "h_fill1"); a.br("BCC", "h_fill1")    # MUTANT: the pocket under an overhang counted as fillable
    else:
        a.br("BEQ", "h_inf"); a.br("BCC", "h_inf")        # top <= vr: pocket under an overhang -> infeasible
    a.ins("SEC"); a.ins16("SBC_abs", D_VR)     # top - vr = 1 + support gap
    if mut == "gap":
        a.ins("SEC"); a.ins("SBC_imm", 1)
    a.ins("CLC"); a.ins16("ADC_abs", D_COST); a.ins16("STA_abs", D_COST)
    if mut == "cavity":
        a.jmp("h_cn")
        a.label("h_fill1"); a.ins16("INC_abs", D_COST)
    a.label("h_cn")
    a.ins16("INC_abs", D_K); a.ins16("LDA_abs", D_K); a.ins("SEC"); a.ins16("SBC_abs", D_S); a.ins("CMP_imm", 4)
    a.br("BNE", "h_cell")
    a.ins16("LDA_abs", D_COST); a.ins16("CMP_abs", D_CUR); a.br("BCS", "h_inf")
    a.ins16("STA_abs", D_CUR)
    a.label("h_inf")
    a.ins16("INC_abs", D_S); a.jmp("h_win")
    a.label("h_done")
    # vertical windows s = max(0, vr-3) .. min(vr, 12)
    a.ins16("LDA_abs", D_VR); a.ins("SEC"); a.ins("SBC_imm", 3); a.br("BCS", "v_s0"); a.ins("LDA_imm", 0)
    a.label("v_s0"); a.ins16("STA_abs", D_S)
    a.label("v_win")
    a.ins16("LDA_abs", D_S); a.ins("CMP_imm", 13); a.br("BCS", "v_done")
    a.ins16("CMP_abs", D_VR); a.br("BEQ", "v_go"); a.br("BCS", "v_done")
    a.label("v_go")
    a.ins("LDA_imm", 0); a.ins16("STA_abs", D_COST)
    a.ins16("LDA_abs", D_S); a.ins16("STA_abs", D_K)
    a.label("v_cell")
    a.ins16("LDA_abs", D_K); a.ins16("CMP_abs", D_VR); a.br("BEQ", "v_cn")
    a.ins("ASL_A"); a.ins("ASL_A"); a.ins("ASL_A"); a.ins16("ORA_abs", D_VC); a.ins("TAX")
    a.ins16("LDA_absX", LIVE); a.ins("CMP_imm", 0xFF); a.br("BEQ", "v_emp")
    a.ins("AND_imm", 0x0F); a.ins16("CMP_abs", D_VCOL); a.br("BEQ", "v_cn")
    a.jmp("v_inf")                              # occupied, wrong colour
    a.label("v_emp")
    a.ins16("LDA_abs", D_K); a.ins16("CMP_abs", D_VR)
    a.br("BCS", "v_fill" if mut == "vbelow" else "v_inf")   # empty BELOW the virus: never (MUTANT: fillable)
    a.ins16("LDX_abs", D_VC); a.ins16("LDA_abs", D_K); a.ins16("CMP_absX", DTOP); a.br("BCS", "v_inf")  # overhang
    a.label("v_fill")
    a.ins16("INC_abs", D_COST)
    a.label("v_cn")
    a.ins16("INC_abs", D_K); a.ins16("LDA_abs", D_K); a.ins("SEC"); a.ins16("SBC_abs", D_S); a.ins("CMP_imm", 4)
    a.br("BNE", "v_cell")
    a.ins16("LDA_abs", D_COST); a.ins16("CMP_abs", D_CUR); a.br("BCS", "v_inf")
    a.ins16("STA_abs", D_CUR)
    a.label("v_inf")
    a.ins16("INC_abs", D_S); a.jmp("v_win")
    a.label("v_done")
    a.ins("RTS")
