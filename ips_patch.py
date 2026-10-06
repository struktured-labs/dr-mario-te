#!/usr/bin/env python3
"""Minimal IPS encoder for TE releases (the decoder used to verify it lives elsewhere on purpose:
tools/ipsdiff.py:apply_ips, plus Floating IPS in the release round-trip).

IPS = b"PATCH" + records + b"EOF".
  record = 3-byte big-endian offset + 2-byte big-endian size + `size` literal bytes
  RLE    = 3-byte offset + 0x0000 + 2-byte run length + 1 fill byte

Edge cases this encoder handles explicitly:
  * the "EOF" trap: a record whose offset is 0x454F46 reads as the footer to every patcher.
    A record that would start there is started one byte earlier, carrying the preceding
    (unchanged) target byte so the record no longer begins at the magic offset.
  * size limits: literal records and RLE runs are split at 0xFFFF bytes; offsets must fit
    in 24 bits (16 MiB) or encoding fails.
  * RLE is used only for runs of >= RLE_MIN identical CHANGED bytes, where it is strictly
    smaller than a literal record. No record ever carries bytes that equal the source,
    except the single byte the EOF guard may borrow -- so the patch distributes only the
    hack's own bytes.
  * truncation is not expressible in plain IPS, and the TE target is the same size as the
    base, so a size change is rejected rather than silently mishandled.

  usage: ips_patch.py <source.nes> <target.nes> <out.ips>
"""
from __future__ import annotations
import sys

EOF_OFFSET = 0x454F46            # b"EOF" as a 24-bit offset
MAX_OFFSET = 0xFFFFFF
MAX_SIZE = 0xFFFF
RLE_MIN = 9                      # a run this long costs 8 B as RLE vs 5+n as its own literal
                                 # record; shorter runs stay inline in the literal record


def _changed_runs(src: bytes, tgt: bytes) -> list[tuple[int, int]]:
    runs, i, n = [], 0, len(tgt)
    while i < n:
        if tgt[i] != src[i]:
            j = i
            while j < n and tgt[j] != src[j]:
                j += 1
            runs.append((i, j))
            i = j
        else:
            i += 1
    return runs


def _split_rle(seg: bytes) -> list[tuple[int, int, bool]]:
    """(start, end, is_rle) pieces of one changed run."""
    out, i, n = [], 0, len(seg)
    lit_start = 0
    while i < n:
        j = i
        while j < n and seg[j] == seg[i]:
            j += 1
        if j - i >= RLE_MIN:
            if lit_start < i:
                out.append((lit_start, i, False))
            out.append((i, j, True))
            lit_start = j
        i = j
    if lit_start < n:
        out.append((lit_start, n, False))
    return out


def make_ips(src: bytes, tgt: bytes) -> bytes:
    if len(src) != len(tgt):
        raise ValueError(f"source {len(src)} B != target {len(tgt)} B; this encoder does not resize")
    body = bytearray(b"PATCH")

    def emit(off: int, data: bytes, rle: bool) -> None:
        if off == EOF_OFFSET:
            raise AssertionError("internal: record at the EOF offset escaped the guard")
        if off > MAX_OFFSET:
            raise ValueError(f"offset 0x{off:X} does not fit in 24 bits")
        body.extend(off.to_bytes(3, "big"))
        if rle:
            body.extend(b"\x00\x00")
            body.extend(len(data).to_bytes(2, "big"))
            body.append(data[0])
        else:
            body.extend(len(data).to_bytes(2, "big"))
            body.extend(data)

    for start, end in _changed_runs(src, tgt):
        if start == EOF_OFFSET:                      # borrow the previous byte (start > 0 here)
            start -= 1
        seg = bytes(tgt[start:end])
        for a, b, rle in _split_rle(seg):
            while a < b:                             # respect the 16-bit size field
                n = min(MAX_SIZE, b - a)
                if start + a == EOF_OFFSET:          # an RLE/size split can land on the magic offset
                    raise ValueError("record split landed on the EOF offset; adjust MAX_SIZE")
                emit(start + a, seg[a:a + n], rle)
                a += n
    body.extend(b"EOF")
    return bytes(body)


if __name__ == "__main__":
    s = open(sys.argv[1], "rb").read()
    t = open(sys.argv[2], "rb").read()
    p = make_ips(s, t)
    open(sys.argv[3], "wb").write(p)
    print(f"wrote {sys.argv[3]} ({len(p)} bytes)")
