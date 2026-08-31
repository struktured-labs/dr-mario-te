#!/usr/bin/env python3
"""remap_mapper.py — make a mapper-100 Dr. Mario COPRO cart loadable in Mesen.

The shipped copro cart stamps iNES mapper 100 only to route it to the custom MiSTer/Pocket
core. Its actual PRG banking is plain MMC1 (32KB-switch mode) — the `_sel` routine writes the
MMC1 serial shift register at $FFF0. Mesen's mapper 100 is NESticle (MMC3-ish) and does NOT
match, so we rewrite the header to mapper 1 (MMC1). The copro window at $5000 is unmapped
open-bus under MMC1 and is emulated by copro_emu.lua's memory callbacks.

Only the 2 mapper-nibble header bytes change; PRG+CHR are untouched (so the QA'd image is
byte-for-byte the shipped cart apart from the header the FPGA core ignores anyway).

Usage:  python3 remap_mapper.py <in .nes> <out .nes>
"""
import sys, hashlib


def remap(in_path, out_path):
    rom = bytearray(open(in_path, "rb").read())
    assert rom[:4] == b"NES\x1a", "not an iNES ROM"
    old_mapper = ((rom[7] >> 4) << 4) | (rom[6] >> 4)
    # mapper low nibble -> byte6 hi nibble; mapper high nibble -> byte7 hi nibble.
    # target mapper 1: byte6 hi = 1, byte7 hi = 0. Preserve byte6 low-nibble flags
    # (mirroring/battery/trainer/4-screen) and clear byte7 hi (no NES2.0 / console bits touched).
    rom[6] = (rom[6] & 0x0F) | 0x10
    rom[7] = (rom[7] & 0x0F) | 0x00
    new_mapper = ((rom[7] >> 4) << 4) | (rom[6] >> 4)
    open(out_path, "wb").write(rom)
    print(f"{in_path}\n  md5 {hashlib.md5(open(in_path,'rb').read()).hexdigest()}  mapper {old_mapper}")
    print(f"{out_path}\n  md5 {hashlib.md5(rom).hexdigest()}  mapper {new_mapper}  (PRG+CHR identical; header only)")
    assert new_mapper == 1, "expected mapper 1 after remap"


if __name__ == "__main__":
    if len(sys.argv) != 3:
        print(__doc__); sys.exit(1)
    remap(sys.argv[1], sys.argv[2])
