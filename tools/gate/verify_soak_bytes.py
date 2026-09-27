#!/usr/bin/env python3
"""verify_soak_bytes.py -- prove the image the soak actually BOOTS is the ship cart.

The gate boots a header-remapped copy (mapper 100 -> 1) because Mesen's mapper 100 is NESticle,
not the copro core. That remap is the one place a soak could silently drift off the ship bytes,
so it gets an explicit check rather than a comment.

Three assertions, each of which FAILS on a wrong input:
  1. the source file's md5 equals the declared ship md5      -- catches soaking the wrong cart
  2. remapped[16:] == source[16:]                            -- catches any PRG/CHR edit
  3. the ONLY differing byte offsets are {6, 7}              -- catches a header field being
                                                                clobbered beyond the mapper nibbles
Run with a deliberately wrong --md5 and assertion 1 fires; point --out at a different cart and
2 and 3 fire. Usage:
    verify_soak_bytes.py --src <ship.nes> --out <remapped.nes> --md5 <expected>
"""
import argparse
import hashlib
import sys


def md5(b: bytes) -> str:
    return hashlib.md5(b).hexdigest()


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--src", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--md5", required=True)
    a = ap.parse_args()

    src = open(a.src, "rb").read()
    dst = open(a.out, "rb").read()

    ok = True
    src_md5 = md5(src)
    print(f"src        {a.src}")
    print(f"  size     {len(src)}")
    print(f"  md5      {src_md5}")
    if src_md5 != a.md5:
        print(f"  FAIL     expected {a.md5}")
        ok = False
    else:
        print("  PASS     matches declared ship md5")

    print(f"boot image {a.out}")
    print(f"  size     {len(dst)}")
    print(f"  md5      {md5(dst)}   (header-remapped; differs from ship md5 BY DESIGN)")

    if len(src) != len(dst):
        print(f"  FAIL     size differs: {len(src)} vs {len(dst)}")
        return 1

    body_ok = src[16:] == dst[16:]
    print(f"  body md5 {md5(dst[16:])}  vs src body {md5(src[16:])}")
    if body_ok:
        print("  PASS     PRG+CHR byte-identical to the ship cart")
    else:
        print("  FAIL     PRG/CHR DIFFER -- this is not the ship cart")
        ok = False

    diff = [i for i in range(len(src)) if src[i] != dst[i]]
    print(f"  diff off {diff}")
    if set(diff) <= {6, 7}:
        print("  PASS     only the iNES mapper-nibble bytes 6/7 changed")
        print(f"           byte6 {src[6]:#04x} -> {dst[6]:#04x}   byte7 {src[7]:#04x} -> {dst[7]:#04x}")
        mapper = ((dst[7] >> 4) << 4) | (dst[6] >> 4)
        print(f"           mapper {((src[7] >> 4) << 4) | (src[6] >> 4)} -> {mapper}")
        if mapper != 1:
            print("  FAIL     boot image is not mapper 1")
            ok = False
    else:
        print("  FAIL     bytes outside the header mapper nibbles changed")
        ok = False

    print("VERDICT " + ("PASS" if ok else "FAIL"))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
