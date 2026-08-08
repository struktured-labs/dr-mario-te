#!/usr/bin/env python3
"""#47 CMD-8 unit vectors: random + adversarial boards -> strand_cases.txt
(per line: 128 engine-encoded cells ((vir<<2)|col, col 0=empty 1..3) + expected
stranded count). Expected counts are computed INLINE with the same neighbour
rule and CROSS-ASSERTED against terms47.g_stranded (the offline-gated
reference) so this generator cannot drift into a third variant of the metric.

Case 0 is the USER-FLAGGED silicon board (P2 of the 2026-08-03 slot-4 capture,
evidence in dr-mario-qa-wt/experiments/eval47/fixtures/) — Exhibit A's two
halves MUST be counted (plan step 4).
"""
import sys, os, random

QA = "/home/struktured/projects/dr-mario-qa-wt/experiments/eval47"
sys.path.insert(0, QA)
import numpy as np
from terms47 import g_stranded

FIXTURE = os.path.join(QA, "fixtures", "user_flag_20260803_slot4.ss")
RAM = 0x102B08


def stranded_inline(col, vir):
    n = 0
    for r in range(16):
        for c in range(8):
            i = r * 8 + c
            if col[i] == 0 or vir[i]:
                continue
            k = col[i]
            if (r > 0 and col[i - 8] == k) or (r < 15 and col[i + 8] == k) \
               or (c > 0 and col[i - 1] == k) or (c < 7 and col[i + 1] == k):
                continue
            n += 1
    return n


def board_from_fixture():
    d = open(FIXTURE, "rb").read()
    cells = d[RAM + 0x500: RAM + 0x580]
    col = [0] * 128
    vir = [0] * 128
    for i, b in enumerate(cells):
        if b == 0xFF:
            continue
        col[i] = (b & 0x0F) + 1
        vir[i] = 1 if (b & 0xF0) == 0xD0 else 0
    return col, vir


def rand_board(rng, fill, vir_frac):
    col = [0] * 128
    vir = [0] * 128
    for i in range(128):
        r = i // 8
        if r >= 4 and rng.random() < fill:
            col[i] = rng.randint(1, 3)
            if rng.random() < vir_frac:
                vir[i] = 1
    return col, vir


def main(n=200, seed=47):
    rng = random.Random(seed)
    boards = [board_from_fixture()]
    # adversarial: monochrome column tower (0 stranded), barber pole (all stranded),
    # single isolated cells at all 4 corners + centre
    mono = [0] * 128; mv = [0] * 128
    for r in range(8, 16): mono[r * 8 + 3] = 2
    boards.append((mono, mv))
    pole = [0] * 128; pv = [0] * 128
    for r in range(8, 16): pole[r * 8 + 4] = 1 + (r % 2)
    boards.append((pole, pv))
    iso = [0] * 128; iv = [0] * 128
    for i in (0, 7, 120, 127, 8 * 8 + 4): iso[i] = 1
    boards.append((iso, iv))
    while len(boards) < n:
        boards.append(rand_board(rng, rng.uniform(0.1, 0.7), rng.uniform(0.0, 0.8)))

    lines = [str(len(boards))]
    for col, vir in boards:
        exp = stranded_inline(col, vir)
        ref = int(g_stranded(np.array(col, dtype=np.int8), np.array(vir, dtype=np.int8)))
        assert exp == ref, f"inline vs terms47 drift: {exp} vs {ref}"
        enc = [((v << 2) | c) for c, v in zip(col, vir)]
        lines.append(" ".join(str(e) for e in enc) + f" {exp}")
    open("strand_cases.txt", "w").write("\n".join(lines) + "\n")
    fx = stranded_inline(*boards[0])
    print(f"wrote strand_cases.txt ({len(boards)} cases; fixture board count={fx})")
    assert fx >= 2, "fixture board must contain Exhibit A's >=2 stranded halves"


if __name__ == "__main__":
    main()
