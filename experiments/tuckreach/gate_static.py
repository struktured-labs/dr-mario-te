#!/usr/bin/env python3
"""Static firmware gates for DRTUCKREACH / DRTUCKLIVE / DRROOTORD on the SHIPPED-style (delta) hexes.

  IDENTITY  every flag off == fw 1488e158 byte-for-byte (negative control), and every arm's hex is distinct
            (N labels -> N md5s, quartus-update-mif lesson)
  BOARD     where the tuck enumerator reads the board: absolute,X/Y loads of $0700-$077F (soft CUR) vs $0500-$057F
            (LIVE) inside the tuck image ($9000-$A3FF), by arm. DRTUCKLIVE must leave exactly one $0700 read (tsi_up,
            the deliberate upload of the tuck's own CUR) and move the 12 enumerator reads to $0500.
  SPACE     search / tuck / dist / reach images still fit their windows (asserted by build_copro_d3; sizes printed)
Usage: gate_static.py
"""
import hashlib
import os
import sys
from collections import Counter

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import fwlib as F  # noqa: E402

ARMS = {"off": (0, 0, 0), "tr": (1, 0, 0), "ro": (0, 1, 0), "tl": (0, 0, 1), "trro": (1, 1, 0), "trtl": (1, 0, 1),
        "rotl": (0, 1, 1), "ship": (1, 1, 1)}
LOADS = {0xBD: "LDA,X", 0xB9: "LDA,Y", 0xBE: "LDX,Y", 0xBC: "LDY,X", 0xDD: "CMP,X", 0xD9: "CMP,Y"}


def board_reads(img, lo, hi):
    c = Counter()
    for i in range(lo, hi - 2):
        if img[i] in LOADS:
            a = img[i + 1] | img[i + 2] << 8
            if 0x0700 <= a < 0x0780:
                c["CUR $07xx"] += 1
            elif 0x0500 <= a < 0x0580:
                c["LIVE $05xx"] += 1
    return dict(c)


def main():
    ok = True
    md5 = {}
    for a, (tr, ro, tl) in ARMS.items():
        img = F.image(tr, ro, delta=True, DRTUCKLIVE=tl)
        md5[a] = F.hex_md5(img)
        br = board_reads(img, 0x9000, 0xA400)
        end = max(i for i in range(0x8000, 0x9000) if img[i] != 0) + 1
        print(f"{a:5s} md5 {md5[a]}  search ends ${end:04X} (window $9000)  tuck-image board reads {br}")
        if tl:
            ok &= br.get("CUR $07xx", 0) == 1 and br.get("LIVE $05xx", 0) == 12
        else:
            ok &= br.get("CUR $07xx", 0) == 13 and br.get("LIVE $05xx", 0) == 0
    neg = md5["off"] == "1488e1583ab7ad8b2011d4c136926faf"
    distinct = len(set(md5.values())) == len(md5)
    print(f"IDENTITY every flag off == fw 1488e158: {'PASS' if neg else 'FAIL'}; {len(set(md5.values()))} distinct md5 for "
          f"{len(md5)} arms: {'PASS' if distinct else 'FAIL'}")
    ok &= neg and distinct
    print("GATE_STATIC", "PASS" if ok else "FAIL")
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
