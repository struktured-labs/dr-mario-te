#!/usr/bin/env python3
"""Build the PINNED link-aware node corpus for `gate.py linknode`.

WHY A SECOND CORPUS.  The existing pinned corpus carries NO link information -- every
non-virus pill cell in node_cases.txt is encoded `$4x` (measured: high-nibble histogram is
exactly {4, 13, 15}).  It therefore cannot distinguish body gravity from compact gravity,
which is the whole point of the link engine.  Rather than rewrite node_cases.txt -- other
lanes' blessings are tied to its md5 -- this adds a parallel corpus and a parallel level.

Cases come from REAL self-play boards, which is where the link plane is real: the shipped
decider plays the game and every board it reaches contributes all 64 (orient x column)
placements, under both round caps.  Ground truth is `cascade_chain_x._expand_chain` plus
`fast_rtl_x._leafv_ship`, the kernels the offline A/B ran on.

STRATIFIED, because size matters and information does not distribute evenly: every
CLEARING and every CHAINING placement is kept (those exercise the new gravity and the
fixpoint loop), plus a fixed sample of non-clearing ones as a control.  The non-clearing
path is already covered exhaustively by the gate's LEAF and DELTA phases.

Usage: linkcorpus.py [--force]
"""
from __future__ import annotations
import os, sys, random
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
COMBO = "/home/struktured/projects/dr_mario_rl/tmp/combo_term"
ROOT = "/home/struktured/projects/dr_mario_rl"
SIM = ROOT + "/.claude/worktrees/faithful-sim"
for p in (COMBO, ROOT + "/tmp/endgame", SIM + "/src"):
    if p not in sys.path:
        sys.path.insert(0, p)

import fast_rtl_x as F
import cascade_link_x as L
import cascade_chain_x as C
from fast_sim_x import NCELL, COLS
from drmario.faithful_env import FaithfulDrMarioEnv

OUT = os.path.join(HERE, "linknode_cases.txt")
GAMES = ((11, 0), (11, 1), (11, 2), (17, 0), (17, 1), (17, 2))
N_CONTROL = 3000          # non-clearing controls kept
SEED = 20260801

# RTL a_o4 -> reference variant. Getting this backwards swaps horizontal for vertical and
# every case still "runs", so it is asserted, not assumed.
assert list(F._VAR_OF_O4) == [2, 3, 0, 1]

_HI = {0: 0x8, L.LINK_UP: 0x5, L.LINK_DOWN: 0x4, L.LINK_LEFT: 0x7, L.LINK_RIGHT: 0x6}


def to_nes(col, vir, lnk):
    out = []
    for i in range(NCELL):
        c = int(col[i])
        if c == 0:
            out.append(0xFF)
        elif vir[i]:
            out.append(0xD0 | (c - 1))
        else:
            out.append((_HI[int(lnk[i])] << 4) | (c - 1))
    return out


def main():
    if os.path.exists(OUT) and "--force" not in sys.argv:
        print("refusing to overwrite pinned %s (use --force)" % OUT)
        return 2

    w, fl = F.variant("winner")
    F.warmup_ship_eh(); F.warmup_delta(); L.warmup_linked(); C.warmup_chain()
    dec = F.FastShipD3DeciderEHDelta(w, fl, topk2=8)

    cc = np.empty(NCELL, dtype=np.int8); cv = np.empty(NCELL, dtype=np.int8)
    cl_ = np.empty(NCELL, dtype=np.int8); mk = np.empty(NCELL, dtype=np.int8)

    clearing, chaining, control = [], [], []
    for level, seed in GAMES:
        env = FaithfulDrMarioEnv(level=level, seed=seed, max_pills=300)
        env.reset()
        while True:
            a = dec.choose(env.board, env.cur, env.nxt)
            if a is None:
                break
            col = np.ascontiguousarray(env.board.color, dtype=np.int8).reshape(-1).copy()
            vir = env.board.is_virus.reshape(-1).astype(np.int8).copy()
            lnk = np.ascontiguousarray(env.board.link, dtype=np.int8).reshape(-1).copy()
            pnes = to_nes(col, vir, lnk)
            pa, pb = env.cur.a, env.cur.b
            for fix in (0, 1):
                maxpass = 1 if fix == 0 else 0
                for o4 in range(4):
                    var = int(F._VAR_OF_O4[o4])
                    for c in range(COLS):
                        ok, nv, cells, ch = C._expand_chain(
                            col, vir, lnk, var, c, pa, pb, cc, cv, cl_, mk, maxpass)
                        if ok == 0:
                            control.append((pnes, o4, c, pa - 1, pb - 1, fix,
                                            0, 0, 0, 0, 0, 0, 0, pnes))
                            continue
                        imm = 180 * nv + 10 * cells
                        if int(F._virus_count(cv)) == 0:
                            win, sco = 1, 0
                        else:
                            win, sco = 0, int(F._leafv_ship(cc, cv, w, fl)) & 0xFFFF
                        rec = (pnes, o4, c, pa - 1, pb - 1, fix, 1, int(cells), int(nv),
                               int(ch), imm, sco, win, to_nes(cc, cv, cl_))
                        if ch > 1:
                            chaining.append(rec)
                        elif cells:
                            clearing.append(rec)
                        else:
                            control.append(rec)
            _, _, term, trunc, _ = env.step(int(a))
            if term or trunc:
                break

    rng = random.Random(SEED)
    rng.shuffle(control)
    recs = chaining + clearing + control[:N_CONTROL]

    with open(OUT, "w") as f:
        f.write("%d\n" % len(recs))
        for (pn, o4, c, ca, cb, fix, legal, cells, nv, ch, imm, sco, win, chn) in recs:
            f.write(" ".join("%02x" % b for b in pn))
            f.write(" %d %d %d %d %d" % (o4, c, ca, cb, fix))
            f.write(" %d %d %d %d %d %d %d\n" % (legal, cells, nv, ch, imm, sco, win))
            f.write(" ".join("%02x" % b for b in chn) + "\n")

    print("wrote %s" % OUT)
    print("  chaining (chain>1) : %d" % len(chaining))
    print("  clearing (chain=1) : %d" % len(clearing))
    print("  controls kept      : %d  (of %d)" % (len(recs) - len(chaining) - len(clearing),
                                                  len(control)))
    print("  total              : %d" % len(recs))
    return 0


if __name__ == "__main__":
    sys.exit(main())
