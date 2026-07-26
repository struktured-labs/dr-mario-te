#!/usr/bin/env python3
"""Generate a diverse hostdata.txt corpus for the delta cell-exact gate. The oracle columns
are dummy (0 0) -- the gate compares BASELINE-firmware moves vs DELTA-firmware moves on the
SAME boards, not vs any oracle. Keeps the known dense failing board (seed-41 case-1) as case 0.
Usage: gen_corpus.py [ncases]"""
import sys, os, random
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, os.path.join(ROOT, "tests")); sys.path.insert(0, ROOT)
from test_depth2 import _rand_board

N = int(sys.argv[1]) if len(sys.argv) > 1 else 40

# case 0: the exact dense board the bug was found on (cA=cB=1, nA=1 nB=2)
CASE1 = ("1 1 1 2 0 0 " + " ".join([
 "ff"]*42 + ["d2","d0","ff","d1","ff","ff","d2","d1","ff","d2","ff","d2","ff","d2","d2","ff",
 "d2","d0","d2","ff","ff","ff","d1","d2","d1","ff","ff","ff","d2","d1","d2","d0","d1","ff","ff",
 "ff","d1","d0","ff","ff","d1","ff","d1","d0","ff","ff","ff","ff","ff","d0","ff","d0","ff","d2",
 "ff","d2","d1","ff","ff","d0","ff","d0","d0","ff","d1","d1","ff","d2","ff","ff","d2","ff","ff",
 "ff","ff","ff","d0","ff","ff","ff","ff","d0","ff","d0","d1","d0"]))

rng = random.Random(41)
lines = [CASE1]
for _ in range(N - 1):
    b = _rand_board(rng)
    cA, cB, nA, nB = (rng.randint(0, 2) for _ in range(4))
    lines.append("%d %d %d %d 0 0 %s" % (cA, cB, nA, nB, " ".join("%02x" % (x & 0xFF) for x in b)))

with open(os.path.join(HERE, "hostdata.txt"), "w") as f:
    f.write(("%d\n" % N) + "\n".join(lines) + "\n")
print("wrote hostdata.txt: %d cases (case 0 = dense seed-41 board)" % N)
