#!/usr/bin/env python3
"""ram_fingerprint.py -- print the GAME-STATE fingerprint of a save-state.

Prints "<lfsr_hi><lfsr_lo> <virus_p1> <virus_p2> <mode>". Used by the driver to
tell a CAPTURE fault from a WEDGE when the screen stops moving:

    frozen screen + ADVANCING fingerprint -> the screenshot channel failed
    frozen screen + FROZEN   fingerprint -> the GAME is wedged, and that is DATA

Deliberately NOT a hash of the whole RAM window: free-running frame counters
would make a genuinely wedged game look alive. These four fields are exactly the
ones that stood still for 360 s in the two confirmed #133 pause soft-locks.
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent / "vendor"))
import seedjit_ss

FAST_BASE = 0x102B08

def base_of(blob):
    b = FAST_BASE
    if b + 0x2800 <= len(blob) and blob[b + 0x800 + seedjit_ss.NAV_MAGIC_ADDR] == seedjit_ss.NAV_MAGIC:
        return b
    try:
        return seedjit_ss.find_base(blob)
    except BaseException:
        return None

def bcd(x): return (x >> 4) * 10 + (x & 0x0F)

def main(path):
    blob = Path(path).read_bytes()
    b = base_of(blob)
    if b is None:
        print("UNDECODABLE"); return 1
    print(f"{blob[b+0x18]:02x}{blob[b+0x17]:02x} {bcd(blob[b+0x324])} {bcd(blob[b+0x3A4])} {blob[b+seedjit_ss.MODE]:02x}")
    return 0

if __name__ == "__main__":
    sys.exit(main(sys.argv[1]))
