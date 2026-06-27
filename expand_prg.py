#!/usr/bin/env python3
"""Expand a Dr. Mario (MMC1) ROM's PRG from 2 banks (32KB) to 4 banks (64KB),
WITHOUT changing any executed code, so depth-2 search code can live in a new
switchable bank.

MMC1 fixed-last config: $C000-$FFFF is fixed to the LAST 16KB bank (holds the
reset/NMI vectors), $8000-$BFFF is switchable. So the original fixed bank (orig
bank 1) MUST stay the last bank. Layout becomes:

  index 0: orig bank 0   (switchable; the game keeps selecting this, as before)
  index 1: NEW bank      (our search code goes here; select to run it)
  index 2: blank         (spare)
  index 3: orig bank 1   (fixed @ $C000; vectors intact)

Power-of-2 bank count keeps MMC1 bank-number wrapping clean. The game selects
bank 0 for $8000 exactly as before, so behavior is byte-identical until we add a
trampoline that switches to bank 1.
"""
import sys

BANK = 0x4000  # 16KB


def expand(in_path, out_path, new_bank_bytes=None):
    rom = bytearray(open(in_path, "rb").read())
    assert rom[:4] == b"NES\x1a", "not an iNES ROM"
    nprg = rom[4]
    nchr = rom[5]
    assert nprg == 2, f"expected 2 PRG banks, got {nprg}"
    prg = rom[16:16 + nprg * BANK]
    chr_ = rom[16 + nprg * BANK:]
    bank0 = prg[:BANK]
    bank1_fixed = prg[BANK:2 * BANK]

    new_bank = bytearray(b"\xff" * BANK)
    if new_bank_bytes:
        new_bank[:len(new_bank_bytes)] = new_bank_bytes
    blank = b"\xff" * BANK

    new_prg = bytes(bank0) + bytes(new_bank) + blank + bytes(bank1_fixed)
    assert len(new_prg) == 4 * BANK

    out = bytearray(rom[:16])
    out[4] = 4                      # 4 PRG banks now
    out += new_prg
    out += chr_                     # CHR unchanged
    open(out_path, "wb").write(out)
    print(f"wrote {out_path}: PRG {nprg}->4 banks ({len(new_prg)} B), "
          f"CHR {nchr} banks unchanged, total {len(out)} B")
    # sanity: vectors still in the (now last) fixed bank
    fixed = new_prg[-BANK:]
    rst = fixed[0x3FFC] | (fixed[0x3FFD] << 8)
    nmi = fixed[0x3FFA] | (fixed[0x3FFB] << 8)
    print(f"  fixed-bank vectors: RESET=${rst:04X} NMI=${nmi:04X} (expect FF00/8005)")
    return out_path


if __name__ == "__main__":
    inp = sys.argv[1] if len(sys.argv) > 1 else "drmario.nes"
    outp = sys.argv[2] if len(sys.argv) > 2 else "tmp/drmario_exp.nes"
    import os
    os.makedirs(os.path.dirname(outp) or ".", exist_ok=True)
    expand(inp, outp)
