#!/usr/bin/env python3
"""Deterministic in-place byte patch: repaint the in-game "Dr.MARIO ™" logo to "TE".

Works on ANY already-built Dr. Mario TE binary (standalone 32 KiB-PRG OR copro cart 64 KiB-PRG):
the CHR base is read from the iNES header (16 + 16384*PRG_banks), so the tile $9A offset on CHR
pages 0 & 1 is located correctly in either layout.  This is the same repaint as
title_screen.apply_ingame_te_mark, expressed as a self-contained patcher for staged binaries.

  standalone (PRG=2): page0 tile $9A @ file 0x089B0, page1 @ 0x099B0
  copro cart (PRG=4): page0 tile $9A @ file 0x109B0, page1 @ 0x119B0

Guards: only patches a tile currently holding the original ™ "M" glyph (or already the "E", so the
patch is idempotent); anything else aborts.  Refuses to run on a ROM whose CHR pages 0/1 do not
carry the expected ™ glyph.  Usage:  python patch_ingame_te.py <in.nes> <out.nes>
"""
import sys, os, hashlib

CHR_PAGE_SIZE = 0x1000
INGAME_TM_PAGES = (0, 1)
INGAME_TM_TILE_ID = 0x9A
INGAME_M_GLYPH = bytes.fromhex("000000000000000000006c5454444400")  # original in-game ™ "M"
INGAME_E_GLYPH = bytes.fromhex("00000000000000000000784070407800")  # repainted "E"


def chr_base(rom):
    if rom[:4] != b"NES\x1a":
        raise ValueError("not an iNES ROM")
    return 16 + rom[4] * 16384                       # CHR follows PRG


def tile_off(base, page, tile_id):
    return base + page * CHR_PAGE_SIZE + tile_id * 16


def apply(rom):
    """Repaint tile $9A (™ 'M' -> 'E') on CHR pages 0 & 1 of ``rom`` (bytearray). Returns [(off,page)]."""
    base = chr_base(rom)
    sites = []
    for page in INGAME_TM_PAGES:
        off = tile_off(base, page, INGAME_TM_TILE_ID)
        existing = bytes(rom[off:off + 16])
        if existing not in (INGAME_M_GLYPH, INGAME_E_GLYPH):
            raise ValueError(
                f"CHR page {page} tile 0x{INGAME_TM_TILE_ID:02X} @ 0x{off:05X} is not the ™ 'M' "
                f"glyph ({existing.hex()}) — refusing to patch")
        rom[off:off + 16] = INGAME_E_GLYPH
        sites.append((off, page))
    return sites


def main():
    if len(sys.argv) != 3:
        sys.exit("usage: patch_ingame_te.py <in.nes> <out.nes>")
    src = open(sys.argv[1], "rb").read()
    rom = bytearray(src)
    sites = apply(rom)
    open(sys.argv[2], "wb").write(rom)
    print(f"in-game ™ -> TE : {sys.argv[1]}  (md5 {hashlib.md5(src).hexdigest()})")
    print(f"              -> {sys.argv[2]}  (md5 {hashlib.md5(rom).hexdigest()})")
    print(f"  CHR base 0x{chr_base(rom):05X}; repainted tile $9A on pages "
          + ", ".join(f"{p} @ 0x{o:05X}" for o, p in sites))
    changed = [i for i in range(len(src)) if src[i] != rom[i]]
    print(f"  byte-diff: {len(changed)} bytes changed"
          + (f" (0x{changed[0]:05X}..0x{changed[-1]:05X})" if changed else ""))


if __name__ == "__main__":
    main()
