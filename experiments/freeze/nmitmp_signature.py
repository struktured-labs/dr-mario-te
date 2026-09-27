"""Does a MiSTer NES save-state show the #133/#141 NMITMP freeze signature?

Root cause (2026-09-25, dr-mario-te #19): the stock getInputs runs from the NMI and writes its scratch
tmp49 ($49). That byte is also the END index of checkVerMatch's clear-marking loop ($94D2-$94F8:
mark ($57),Y · $5A += 8 · CPY $49 / BNE). An NMI mid-loop leaves an END index Y can never reach, so the
loop spins forever. The fix is DRNMITMP=1 in patch_cartridge_copro.py.

Signature: PC inside $94D2-$94F8, and $49's residue mod 8 differs from $5A's (the loop's step is 8).
Capture a frozen state with `misterclaw-send -H <mister> input combo leftalt f1` (the watcher's
`echo save_state > /dev/MiSTer_cmd` never works).

Save-state layout (MiSTer NES core, 1,327,112 B): PC little-endian at file offset 0x08, CPU RAM at
0x102B08, cart WRAM $6000 at 0x103308.

Usage: python nmitmp_signature.py STATE.ss [STATE.ss ...]
"""
import sys

SS_SIZE, PC_OFF, RAM = 1327112, 0x08, 0x102B08
LOOP_LO, LOOP_HI = 0x94D2, 0x94F8


def signature(path):
    b = open(path, "rb").read()
    if len(b) != SS_SIZE:
        return dict(path=path, error=f"size {len(b)} != {SS_SIZE} (not a MiSTer NES save-state?)")
    pc = b[PC_OFF] | (b[PC_OFF + 1] << 8)
    r = lambda a: b[RAM + a]
    in_loop = LOOP_LO <= pc <= LOOP_HI
    end, y = r(0x49), r(0x5A)
    stuck = in_loop and (end % 8) != (y % 8)
    return dict(path=path, pc=pc, in_loop=in_loop, end49=end, y5a=y, run47=r(0x47), ptr57=r(0x57) | (r(0x58) << 8),
                mode46=r(0x46), verdict="NMITMP-RACE" if stuck else ("in-loop, residues match" if in_loop else "no"))


if __name__ == "__main__":
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    for p in sys.argv[1:]:
        s = signature(p)
        if "error" in s:
            print(f"{p}: ERROR {s['error']}"); continue
        print(f"{p}: PC=${s['pc']:04X} $49={s['end49']:02X} $5A={s['y5a']:02X} (mod8 {s['end49'] % 8}/{s['y5a'] % 8}) "
              f"$47={s['run47']:02X} $57=${s['ptr57']:04X} mode={s['mode46']:X} -> {s['verdict']}")
