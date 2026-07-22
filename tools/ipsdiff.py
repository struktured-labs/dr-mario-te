#!/usr/bin/env python3
"""Apply an IPS patch to the clean Dr. Mario base ROM and report every changed
byte-run as (file-offset, length, region, cpu-addr-guess, before->after preview).

IPS format: 'PATCH' + records + 'EOF'. Record = 3B offset + 2B size; size==0 means
RLE run: 2B run-length + 1B value. Offsets are into the whole .nes (header included).

Base layout (65552 B): 0x00-0x0F iNES header; 0x10-0x800F PRG 32K; 0x8010-0x1000F CHR 32K.
"""
import os
import sys

# Rev 0 USA base ROM (md5 d3ec44424b5ac1a4dc77709829f721c9). The ROM is not committed
# (*.nes is gitignored); point DRMARIO_BASE at your clean copy, or pass it as argv[2].
BASE = (
    (sys.argv[2] if len(sys.argv) > 2 else None)
    or os.environ.get("DRMARIO_BASE")
    or ("drmario.nes" if os.path.exists("drmario.nes") else None)
    or os.path.expanduser("~/projects/dr-mario-mods/drmario.nes")
)

def apply_ips(base: bytearray, ips: bytes) -> bytearray:
    assert ips[:5] == b"PATCH", "not an IPS file"
    out = bytearray(base)
    p = 5
    while True:
        if ips[p:p+3] == b"EOF":
            break
        off = (ips[p] << 16) | (ips[p+1] << 8) | ips[p+2]; p += 3
        size = (ips[p] << 8) | ips[p+1]; p += 2
        if size == 0:  # RLE
            rle = (ips[p] << 8) | ips[p+1]; p += 2
            val = ips[p]; p += 1
            if off + rle > len(out):
                out.extend(b"\x00" * (off + rle - len(out)))
            for i in range(rle):
                out[off+i] = val
        else:
            data = ips[p:p+size]; p += size
            if off + size > len(out):
                out.extend(b"\x00" * (off + size - len(out)))
            out[off:off+size] = data
    return out

def region(off: int, base_len: int):
    if off < 0x10:
        return "iNES-header", None
    if off < 0x8010:
        prg = off - 0x10
        if prg < 0x4000:
            cpu = 0x8000 + prg
            return "PRG (bank0/$8000-$BFFF)", cpu
        else:
            cpu = 0xC000 + (prg - 0x4000)
            return "PRG (fixed/$C000-$FFFF)", cpu
    if off < 0x10010:
        return "CHR (graphics)", None
    return "APPENDED (beyond base)", None

def diff(base: bytearray, patched: bytearray):
    n = max(len(base), len(patched))
    runs = []
    i = 0
    while i < n:
        b = base[i] if i < len(base) else None
        q = patched[i] if i < len(patched) else None
        if b != q:
            j = i
            while j < n:
                bb = base[j] if j < len(base) else None
                qq = patched[j] if j < len(patched) else None
                if bb == qq:
                    break
                j += 1
            runs.append((i, j - i))
            i = j
        else:
            i += 1
    return runs

def main():
    ips_path = sys.argv[1]
    base = bytearray(open(BASE, "rb").read())
    ips = open(ips_path, "rb").read()
    patched = apply_ips(base, ips)
    runs = diff(base, patched)
    total = sum(l for _, l in runs)
    print(f"### {ips_path}")
    print(f"base={len(base)}B patched={len(patched)}B  changed_runs={len(runs)} changed_bytes={total}")
    # coalesce reporting per region
    for off, length in runs:
        reg, cpu = region(off, len(base))
        b_prev = bytes(base[off:off+min(length,8)]) if off < len(base) else b""
        p_prev = bytes(patched[off:off+min(length,8)])
        cpu_s = f" cpu~${cpu:04X}" if cpu is not None else ""
        print(f"  file 0x{off:05X} len {length:5d}  [{reg}]{cpu_s}")
        if length <= 24 and reg != "CHR (graphics)":
            print(f"      before: {b_prev.hex()}  after: {p_prev.hex()}")
    # region summary
    from collections import defaultdict
    agg = defaultdict(int)
    for off, length in runs:
        agg[region(off, len(base))[0]] += length
    print("  region totals:", dict(agg))
    print()

if __name__ == "__main__":
    main()
