#!/usr/bin/env python3
"""Restore the VIRUS counts (and LEVEL digits) on the STUDY pause screen.

User 2026-07-28: "when I press pause for study the virus counts disappear - ideally stays too."

MEASURED, not guessed (tools/study_viruscount_probe.lua on v9):
  the counter is OAM slots 12-15 : Y=$BF  attr=$01  X=$6E/$76/$83/$8B
  the LEVEL digits are slots 8-11: Y=$2B  attr=$01  X=$6D/$75/$84/$8C
  ★ the TILE IS THE DIGIT (tile $00,$04 rendered "04" for 4 viruses -- matched both counts)
  ★ on pause the shadow OAM ($0200-$02FF) for slots 8-15 is blanked to $FF, so the tiles are
    DESTROYED, not merely parked offscreen -> they must be REBUILT, not un-hidden
  ★ the counts themselves survive ($0324 P1 / $03A4 P2), so this is purely a display fix

So: append a routine to the STUDY tail that reads the two counts, splits each into tens/ones
by repeated subtraction, and writes the four sprites back into shadow OAM. Runs on the STUDY
path only, so 1P/normal play is untouched.
"""
import sys, os, hashlib

VC_P1, VC_P2 = 0x0324, 0x03A4
OAM = 0x0200
Y_VIR, ATTR = 0xBF, 0x01
XS = (0x6E, 0x76, 0x83, 0x8B)          # P1 tens, P1 ones, P2 tens, P2 ones


def build_blob(cpu_base, with_level=True):
    """Emit the routine at `cpu_base`; returns bytes. Self-contained, ends RTS."""
    b = bytearray()

    def emit_pair(count_addr, sa, sb, xa, xb, ytop):
        nonlocal b
        b += bytes([0xAD, count_addr & 0xFF, count_addr >> 8])     # LDA count
        b += bytes([0xA2, 0x00])                                   # LDX #0
        loop = len(b)
        b += bytes([0xC9, 0x0A])                                   # CMP #10
        # ★ BCC must clear SBC(2)+INX(1)+JMP(3) = 6 bytes. An earlier +3 landed ON the JMP,
        # which is an INFINITE LOOP for any count < 10 -- i.e. every endgame board.
        b += bytes([0x90, 0x06])                                   # BCC +6 -> past the JMP
        b += bytes([0xE9, 0x0A])                                   # SBC #10
        b += bytes([0xE8])                                         # INX
        # BPL-style unconditional back-branch to loop
        off = (loop - (len(b) + 2)) & 0xFF
        b += bytes([0x4C, (cpu_base + loop) & 0xFF, (cpu_base + loop) >> 8])  # JMP loop
        # ones digit in A, tens in X
        b += bytes([0x48])                                         # PHA (save ones)
        # --- tens sprite ---
        b += bytes([0xA9, ytop]);        b += bytes([0x8D, (OAM+sa*4) & 0xFF, (OAM+sa*4) >> 8])
        b += bytes([0x8A])                                         # TXA (tens -> A)
        b += bytes([0x8D, (OAM+sa*4+1) & 0xFF, (OAM+sa*4+1) >> 8])
        b += bytes([0xA9, ATTR]);        b += bytes([0x8D, (OAM+sa*4+2) & 0xFF, (OAM+sa*4+2) >> 8])
        b += bytes([0xA9, xa]);          b += bytes([0x8D, (OAM+sa*4+3) & 0xFF, (OAM+sa*4+3) >> 8])
        # --- ones sprite ---
        b += bytes([0xA9, ytop]);        b += bytes([0x8D, (OAM+sb*4) & 0xFF, (OAM+sb*4) >> 8])
        b += bytes([0x68])                                         # PLA (ones -> A)
        b += bytes([0x8D, (OAM+sb*4+1) & 0xFF, (OAM+sb*4+1) >> 8])
        b += bytes([0xA9, ATTR]);        b += bytes([0x8D, (OAM+sb*4+2) & 0xFF, (OAM+sb*4+2) >> 8])
        b += bytes([0xA9, xb]);          b += bytes([0x8D, (OAM+sb*4+3) & 0xFF, (OAM+sb*4+3) >> 8])

    emit_pair(VC_P1, 12, 13, XS[0], XS[1], Y_VIR)
    emit_pair(VC_P2, 14, 15, XS[2], XS[3], Y_VIR)
    b += bytes([0x60])                                             # RTS
    return bytes(b)


if __name__ == "__main__":
    blob = build_blob(0xFC00)
    print(f"virus-count restore routine: {len(blob)} bytes at $FC00")
    print(f"  fits the free run $FB80-$FCFF alongside the 83 B study tail: "
          f"{'YES' if 0xFC00 + len(blob) <= 0xFD00 else 'NO'}")
    print("  hex:", blob.hex())
