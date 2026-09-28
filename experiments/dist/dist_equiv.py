#!/usr/bin/env python3
"""The gate's spec-fixed DRDIST reference (gate.dist_D, pure Python) == the sim's cascade_leaf6_x._vdist (cap 16,
kdig 0) and the firmware-rule target (smallest D, ties lowest index) == Leaf6Decider's dist_target choice, on the
pinned corpus + node children + random boards. Usage: dist_equiv.py [N_RANDOM]"""
import os, sys, random
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "gate"))
H16 = "/home/struktured/projects/dr-mario-h16-wt/experiments/cvx"
sys.path.insert(0, H16)
import import_pin; import_pin.pin()                        # h16's pinned module resolution
import cascade_leaf6_x as L6
import gate as G
from common import read_corpus, nes_to_arrays


def top_of(col):
    top = np.empty(8, dtype=np.int64)
    for c in range(8):
        t = 16
        for r in range(16):
            if col[r * 8 + c] != 0:
                t = r; break
        top[c] = t
    return top


def rand_board(rng):
    b = [0xFF] * 128
    for c in range(8):
        h = rng.choice([0, 2, 4, 6, 8, 10, 12, 14, 15, 16])
        for r in range(16 - h, 16):
            b[r * 8 + c] = (0xD0 if rng.random() < 0.3 else rng.choice([0x40, 0x50, 0x60, 0x70, 0x80])) | rng.randrange(3)
        if rng.random() < 0.3:                          # carve cavities / floating viruses
            for r in range(16):
                if rng.random() < 0.2:
                    b[r * 8 + c] = 0xFF
    return b


def main(nrand=20000):
    boards, _ = read_corpus(os.path.join(HERE, "gate", "corpus.txt"))
    rng = random.Random(7)
    boards += [rand_board(rng) for _ in range(nrand)]
    nd = nbad = nt = ntbad = 0
    for b in boards:
        col, vir = nes_to_arrays(b)
        top = top_of(col)
        vs = [i for i in range(128) if vir[i]]
        for i in vs:
            a = int(L6._vdist(col, vir, top, i // 8, i % 8, 16, 0)); g = G.dist_D(b, i)
            nd += 1; nbad += a != g
        if vs:
            out = np.empty(128, dtype=np.int64); L6._root_dists(col, vir, 16, out, 0)
            best = -1
            for i in range(128):
                if out[i] >= 0 and (best < 0 or out[i] < out[best]):
                    best = i
            mine = min(vs, key=lambda i: (G.dist_D(b, i), i))
            nt += 1; ntbad += best != mine
    print(f"D per virus: {nd - nbad}/{nd} identical to cascade_leaf6_x._vdist (cap 16, kdig 0)")
    print(f"target choice: {nt - ntbad}/{nt} identical to Leaf6Decider dist_target (smallest D, ties lowest index)")
    ok = nbad == 0 and ntbad == 0
    print("DIST_EQUIV", "PASS" if ok else "FAIL")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main(int(sys.argv[1]) if len(sys.argv) > 1 else 20000))
