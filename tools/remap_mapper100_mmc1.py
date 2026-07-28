#!/usr/bin/env python3
"""Copy a mapper-100 copro cart with its iNES mapper field rewritten to 1 (MMC1) so Mesen loads
the real MMC1 banking. The $5000-$53FF copro window is open bus under MMC1 and is served by
mesen_copro_qa.lua. Nothing else changes (PRG/CHR bytes, mirroring, size bits all preserved).

  usage: remap_mapper100_mmc1.py <in.nes> [out.nes]   (default out: tmp/<name>_mmc1.nes)
"""
import os, sys

def remap(src: str, dst: str):
    rom = bytearray(open(src, "rb").read())
    assert rom[:4] == b"NES\x1a", "not an iNES file"
    mapper = ((rom[7] >> 4) << 4) | (rom[6] >> 4)
    rom[6] = (rom[6] & 0x0F) | 0x10        # mapper low nibble -> 1
    rom[7] = (rom[7] & 0x0F) | 0x00        # mapper high nibble -> 0
    new = ((rom[7] >> 4) << 4) | (rom[6] >> 4)
    os.makedirs(os.path.dirname(dst) or ".", exist_ok=True)
    open(dst, "wb").write(rom)
    print(f"{src} (mapper {mapper}) -> {dst} (mapper {new}); prg={rom[4]*16}K chr={rom[5]*8}K")

if __name__ == "__main__":
    src = sys.argv[1]
    dst = sys.argv[2] if len(sys.argv) > 2 else os.path.join(
        "tmp", os.path.splitext(os.path.basename(src))[0] + "_mmc1.nes")
    remap(src, dst)
