#!/usr/bin/env python3
"""Decode a DRTRACE ring dump. Feed it 199+ bytes starting at $5000 (copro window) OR $6200 (PRG-RAM):
  python decode_trace.py <dump.bin>            # raw binary of the region
  python decode_trace.py --hex "08 5a 5a ..."  # space/comma-separated hex bytes
Layout (offset from the region base): [0..0xBF]=64 x (mode,$0727,$04); 0xC0=write_idx; 0xC1/0xC2=count
lo/hi; 0xC3..0xC5=LIVE (mode,$0727,$04); 0xC6=magic 0x54."""
import sys
def load(argv):
    if argv and argv[0] == "--hex":
        return bytes(int(x, 16) for x in argv[1].replace(",", " ").split())
    return open(argv[0], "rb").read()
b = load(sys.argv[1:])
assert len(b) >= 0xC7, f"need >=199 bytes, got {len(b)}"
idx, cnt = b[0xC0], b[0xC1] | (b[0xC2] << 8)
mag = b[0xC6]; live = (b[0xC3], b[0xC4], b[0xC5])
NAMES = {0: "title", 1: "levelsel", 4: "PLAY", 7: "postmatch", 8: "intro/DRAW"}
def mode(m): return f"{m:#04x}({NAMES.get(m,'?')})"
print(f"magic={mag:#x} {'OK' if mag==0x54 else 'BAD -- not a valid tracer dump'}")
print(f"change_count={cnt}  write_idx={idx}  LIVE now: mode={mode(live[0])} $0727={live[1]:#04x} $04={live[2]:#04x}")
n = min(cnt, 64)
order = range(n) if cnt <= 64 else [((idx // 3) + k) % 64 for k in range(64)]  # oldest-first if wrapped
print(f"--- {n} logged transitions (oldest first){' [WRAPPED]' if cnt>64 else ''} ---")
for k, e in enumerate(order):
    o = e * 3
    vs = " <= VS-CPU" if (b[o+1] == 2 and b[o+2] == 1) else (" <= 1P" if (b[o]==4 and b[o+1]==1) else "")
    print(f"  {k:2}: mode={mode(b[o])} $0727={b[o+1]:#04x} $04={b[o+2]:#04x}{vs}")
