"""numpy-2 shim for nes_py (recreated; the garbwin original was lost to a scratchpad
clean -- memory dr-mario-garbage-window-mechanics names this file as the fix).
nes_py._rom.ROM header properties return numpy uint8 scalars; under numpy>=2 the
`size * 2**10` arithmetic raises OverflowError instead of promoting.  Wrap every
size/start/stop property to plain int."""
import nes_py._rom as _rom

for name in ("prg_rom_size", "chr_rom_size", "prg_ram_size", "chr_ram_size"):
    if hasattr(_rom.ROM, name):
        fget = getattr(_rom.ROM, name).fget
        setattr(_rom.ROM, name,
                property(lambda self, f=fget: int(f(self))))
