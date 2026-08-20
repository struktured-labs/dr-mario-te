#!/usr/bin/env python3
"""seedjit_ss.py -- locate NES internal RAM inside a MiSTer NES save-state and
read/write the Dr. Mario RNG seed ($0017/$0018).

The save-state carries cart PRG-RAM ($6000-$7FFF) and internal RAM ($0000-$07FF)
contiguously, internal RAM first.  The absolute offset shifts with core/cart, so it is
found by SIGNATURE off the copro driver's state block at $6149 (NAV_MAGIC = $A5) rather
than hardcoded.

  seedjit_ss.py info  <state.ss>              -- base offset, mode $46, seed, virus counts
  seedjit_ss.py seed  <in.ss> <out.ss> <seed> -- write a 16-bit seed, print the result
  seedjit_ss.py board <state.ss>              -- dump P1/P2 virus cells as a sorted list
"""
import sys

IRAM = 0x800  # internal RAM precedes cart WRAM by this much
NAV_MAGIC_ADDR, NAV_MAGIC = 0x149, 0xA5  # $6149
SEED_LO, SEED_HI = 0x17, 0x18
MODE = 0x46
BOARDS = {"P1": 0x400, "P2": 0x500}


def find_base(blob):
    """Return the .ss offset of NES $0000. Requires a unique signature hit."""
    hits = []
    for w in range(0, len(blob) - 0x800):
        match blob[w + NAV_MAGIC_ADDR] == NAV_MAGIC and w >= IRAM:
            case False:
                continue
            case True:
                pass
        base = w - IRAM
        # corroborate: mode is a small enum, both boards hold only legal tiles, and the
        # game's own virus counters ($0324 P1 / $03A4 P2) agree with the boards themselves
        legal = all(
            b in (0x00, 0xFF) or (b >> 4) in (0x4, 0x5, 0x6, 0x7, 0x8, 0xD)
            for b in blob[base + 0x400 : base + 0x580]
        )
        # the counters are BCD (they are the on-screen digits)
        bcd = lambda x: (x >> 4) * 10 + (x & 0xF)
        counts_agree = legal and (
            bcd(blob[base + 0x324]) == len(viruses(blob, base, "P1"))
            and bcd(blob[base + 0x3A4]) == len(viruses(blob, base, "P2"))
        )
        match blob[base + MODE] in (0, 1, 4, 8) and counts_agree:
            case True:
                hits.append(base)
            case False:
                pass
    match len(set(hits)):
        case 1:
            return hits[0]
        case n:
            raise SystemExit(f"expected 1 RAM base, found {n}: {[hex(h) for h in hits]}")


def viruses(blob, base, which):
    """Sorted cell indices holding a virus on the named board."""
    b = base + BOARDS[which]
    return [i for i in range(128) if (blob[b + i] >> 4) == 0xD]


def main(argv):
    match argv:
        case ["info", src]:
            blob = open(src, "rb").read()
            base = find_base(blob)
            seed = blob[base + SEED_LO] | (blob[base + SEED_HI] << 8)
            print(
                f"base=0x{base:06x} mode=${blob[base + MODE]:02x} "
                f"seed=0x{seed:04x} ({seed}) "
                f"rng0=${blob[base + SEED_LO]:02x} rng1=${blob[base + SEED_HI]:02x} "
                f"viruses P1={len(viruses(blob, base, 'P1'))} "
                f"P2={len(viruses(blob, base, 'P2'))}"
            )
        case ["seed", src, dst, val]:
            seed = int(val, 0)
            match 0 <= seed <= 0xFFFF:
                case False:
                    raise SystemExit("seed must be 0..65535")
                case True:
                    pass
            blob = bytearray(open(src, "rb").read())
            base = find_base(blob)
            blob[base + SEED_LO] = seed & 0xFF
            blob[base + SEED_HI] = (seed >> 8) & 0xFF
            open(dst, "wb").write(blob)
            print(f"base=0x{base:06x} seed=0x{seed:04x} written to {dst}")
        case ["board", src]:
            blob = open(src, "rb").read()
            base = find_base(blob)
            for which in BOARDS:
                v = viruses(blob, base, which)
                print(f"{which} n={len(v)} {v}")
        case _:
            raise SystemExit(__doc__)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
