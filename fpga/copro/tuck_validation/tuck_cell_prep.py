#!/usr/bin/env python3
"""Given a CANDLIST entry (target, rest, orient) and the current pill's raw colours
(S_CA, S_CB), compute the two cell offsets and the colour that goes on each -- the
inputs land_place_at needs (LA_OFFA/LA_OFFB/LA_CA/LA_CB). Small, standalone, testable
before it's wired into the candidate loop.

CELL OFFSETS (matches tuck_scan_v3_ref.candidate_cells exactly):
  VERTICAL   (orient in {V=1, RV=3}):  offA = (rest-1)*8+target,  offB = rest*8+target
  HORIZONTAL (orient in {H=0, RH=2}):  offA = rest*8+target,      offB = offA+1

COLOUR-CELL MAPPING (matches tuck_enum.py's _FLIP = (0,1,1,0) for (H,V,RH,RV), restated
in tuck_scan_v3_ref.py as _FLIP = {H:0, V:1, RH:1, RV:0}): flip=0 -> cell0 gets colour A,
flip=1 -> cell0 gets colour B. So:
  H  (flip 0): offA<-ca, offB<-cb
  V  (flip 1): offA<-cb, offB<-ca
  RH (flip 1): offA<-cb, offB<-ca
  RV (flip 0): offA<-ca, offB<-cb
i.e. offA gets ca when orient in {H, RV} (0 or 3), cb when orient in {V, RH} (1 or 2).
"""
from __future__ import annotations

H, V, RH, RV = 0, 1, 2, 3

# CANDLIST field offsets (tuck_scan_v3.py): target=+0, approach=+1, trigger=+2, rest=+3,
# orient=+4. Reuse the same base/constants.
from tuck_scan_v3 import CANDLIST                       # noqa: E402
from land_place_at import LA_OFFA, LA_OFFB, LA_CA, LA_CB  # noqa: E402

# new zero page for this prep step's own temp (candidate index, byte offset into CANDLIST)
TP_IDX = 0x72   # next free after tuck_score.py's TI1L/TI1H (0x70/0x71), grepped-confirmed
TP_BASE = 0x73  # candidate*5 byte offset, kept for reuse across the 4 field reads


def emit_tuck_cell_prep(a, s_ca=None, s_cb=None):
    """Input: TP_IDX = candidate index (0..CAPACITY-1). Reads CANDLIST[TP_IDX] and
    S_CA/S_CB (passed as absolute addresses -- the search's current-pill colour bytes),
    writes LA_OFFA/LA_OFFB/LA_CA/LA_CB. Also leaves the candidate's raw fields in zero
    page for the caller (TP_TARGET/TP_TRIGGER/TP_REST/TP_APPROACH/TP_ORIENT) since the
    publish step needs approach+trigger+target+orient again later.
    Clobbers A, X."""
    a.label("tuck_cell_prep")
    # X = idx*5
    a.ins("LDA_zp", TP_IDX)
    a.ins("STA_zp", TP_BASE)              # stash idx (reuse TP_BASE as scratch first)
    a.ins("ASL_A"); a.ins("ASL_A")        # idx*4
    a.ins("CLC"); a.ins("ADC_zp", TP_BASE)  # idx*4 + idx = idx*5
    a.ins("TAX")
    a.ins16("LDA_absX", CANDLIST + 0); a.ins("STA_zp", TP_TARGET)
    a.ins16("LDA_absX", CANDLIST + 1); a.ins("STA_zp", TP_APPROACH)
    a.ins16("LDA_absX", CANDLIST + 2); a.ins("STA_zp", TP_TRIGGER)
    a.ins16("LDA_absX", CANDLIST + 3); a.ins("STA_zp", TP_REST)
    a.ins16("LDA_absX", CANDLIST + 4); a.ins("STA_zp", TP_ORIENT)

    # offB_base = rest*8 + target
    a.ins("LDA_zp", TP_REST)
    a.ins("ASL_A"); a.ins("ASL_A"); a.ins("ASL_A")
    a.ins("CLC"); a.ins("ADC_zp", TP_TARGET)
    a.ins("STA_zp", TP_BASE)              # TP_BASE = rest*8+target (== offB for H/RH; ==
                                           # offA+8 for V/RV, i.e. this IS offB there too:
                                           # V/RV offA=(rest-1)*8+target=TP_BASE-8, offB=TP_BASE)

    a.ins("LDA_zp", TP_ORIENT)
    a.ins("AND_imm", 1)                   # bit0: 0 for {H,RH}? NO -- H=0,RH=2 both even;
    # V=1,RV=3 both odd. So (orient & 1) == 1 <=> VERTICAL.
    a.br("BEQ", "tcp_horiz")
    # ---- VERTICAL: offA = TP_BASE-8, offB = TP_BASE ----
    a.ins("LDA_zp", TP_BASE); a.ins("SEC"); a.ins("SBC_imm", 8); a.ins("STA_zp", LA_OFFA)
    a.ins("LDA_zp", TP_BASE); a.ins("STA_zp", LA_OFFB)
    a.jmp("tcp_colour")
    a.label("tcp_horiz")
    # ---- HORIZONTAL: offA = TP_BASE, offB = TP_BASE+1 ----
    a.ins("LDA_zp", TP_BASE); a.ins("STA_zp", LA_OFFA)
    a.ins("CLC"); a.ins("ADC_imm", 1); a.ins("STA_zp", LA_OFFB)

    a.label("tcp_colour")
    # offA gets ca when orient in {H=0, RV=3}; cb when orient in {V=1, RH=2}.
    # H=0(00) RV=3(11) both have bit0==bit1. V=1(01) RH=2(10) both have bit0!=bit1. So
    # "offA gets ca" <=> bit0==bit1 <=> (orient>>1) == (orient&1). No EOR_zp in the OPS
    # table (only EOR_imm) -- use CMP_zp instead, equivalent for a 1-bit compare.
    a.ins("LDA_zp", TP_ORIENT)
    a.ins("LSR_A"); a.ins("STA_zp", TP_BASE)   # TP_BASE = orient>>1 (reuse, no longer needed)
    a.ins("LDA_zp", TP_ORIENT); a.ins("AND_imm", 1)
    a.ins("CMP_zp", TP_BASE)
    a.br("BNE", "tcp_swap")
    # offA <- ca, offB <- cb
    a.ins16("LDA_abs", s_ca); a.ins("STA_zp", LA_CA)
    a.ins16("LDA_abs", s_cb); a.ins("STA_zp", LA_CB)
    a.jmp("tcp_done")
    a.label("tcp_swap")
    a.ins16("LDA_abs", s_cb); a.ins("STA_zp", LA_CA)
    a.ins16("LDA_abs", s_ca); a.ins("STA_zp", LA_CB)
    a.label("tcp_done")
    a.ins("RTS")


# zero page for the candidate's raw fields, kept live across the caller's subsequent use
# (theta-gate compare + eventual publish). Chosen contiguous with TP_IDX/TP_BASE.
TP_TARGET, TP_APPROACH, TP_TRIGGER, TP_REST, TP_ORIENT = 0x74, 0x75, 0x76, 0x77, 0x78
