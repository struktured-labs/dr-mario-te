#!/usr/bin/env python3
"""Generate LeafEval CMD-4 (NODE) co-sim cases for the LINK-AWARE engine.

Ground truth is `cascade_chain_x._expand_chain` + `fast_rtl_x._leafv_ship` -- the same
kernels the offline A/B ran on, difftested cell-exact against the faithful engine. Cases
come from REAL self-play boards (every legal placement of every board the shipped decider
actually reaches), not synthetic fills, because synthetic boards flatter link physics:
they rarely contain the tall stacks of intact pairs where body gravity and compact
gravity disagree.

Each record checks colour, VIRUS and LINK planes of the child board plus cells, viruses,
chain depth, imm, sco and win -- comparing only cells/viruses would pass while the link
plane rotted, and the link plane is what drives the NEXT placement's gravity.

Both arms are emitted: fix=0 (cap-1 = the lnk1 arm) and fix=1 (fixpoint = the chain arm).

Record layout (268 whitespace tokens):
  128 hex parent NES bytes | o4 col ca cb fix | legal cells vir chain imm sco win
  | 128 hex child NES bytes

Usage: gen_chain_cases.py <out.txt> [n_games] [level]
"""
from __future__ import annotations
import sys, os
import numpy as np

HERE = "/home/struktured/projects/dr_mario_rl/tmp/combo_term"
ROOT = "/home/struktured/projects/dr_mario_rl"
SIM = ROOT + "/.claude/worktrees/faithful-sim"
for p in (HERE, ROOT + "/tmp/endgame", SIM + "/src"):
    if p not in sys.path:
        sys.path.insert(0, p)

import fast_rtl_x as F
import cascade_link_x as L
import cascade_chain_x as C
from fast_sim_x import NCELL, COLS
from drmario.faithful_env import FaithfulDrMarioEnv

# RTL mailbox a_o4 -> reference variant. _VAR_OF_O4 = [2,3,0,1], i.e. XOR 2, self-inverse.
# Getting this backwards silently swaps horizontal for vertical and every case still
# "runs", so it is asserted rather than assumed.
assert list(F._VAR_OF_O4) == [2, 3, 0, 1]

# link code -> playfield high nibble (inverse of CoproDrMario's lev_lnk decode)
_HI = {0: 0x8,          # orphaned half
       L.LINK_UP: 0x5,  # bottom of a vertical pair
       L.LINK_DOWN: 0x4,  # top of a vertical pair
       L.LINK_LEFT: 0x7,  # right of a horizontal pair
       L.LINK_RIGHT: 0x6}  # left of a horizontal pair


def to_nes(col, vir, lnk):
    """(colour 0..3, virus, link) planes -> 128 NES playfield bytes."""
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
    out_path = sys.argv[1]
    n_games = int(sys.argv[2]) if len(sys.argv) > 2 else 4
    level = int(sys.argv[3]) if len(sys.argv) > 3 else 11

    w, fl = F.variant("winner")
    F.warmup_ship_eh(); F.warmup_delta(); L.warmup_linked(); C.warmup_chain()
    dec = F.FastShipD3DeciderEHDelta(w, fl, topk2=8)

    cc = np.empty(NCELL, dtype=np.int8); cv = np.empty(NCELL, dtype=np.int8)
    cl_ = np.empty(NCELL, dtype=np.int8); mk = np.empty(NCELL, dtype=np.int8)

    recs = []
    n_clear = n_chain = 0
    for s in range(n_games):
        env = FaithfulDrMarioEnv(level=level, seed=s, max_pills=300)
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
                            # illegal: the RTL reports legal=0 and nothing else is defined
                            recs.append((pnes, o4, c, pa - 1, pb - 1, fix,
                                         0, 0, 0, 0, 0, 0, 0, pnes))
                            continue
                        imm = 180 * nv + 10 * cells
                        if int(F._virus_count(cv)) == 0:
                            win, sco = 1, 0
                        else:
                            win, sco = 0, int(F._leafv_ship(cc, cv, w, fl)) & 0xFFFF
                        if cells:
                            n_clear += 1
                        if ch > 1:
                            n_chain += 1
                        recs.append((pnes, o4, c, pa - 1, pb - 1, fix,
                                     1, int(cells), int(nv), int(ch), imm, sco, win,
                                     to_nes(cc, cv, cl_)))
            _, _, term, trunc, _ = env.step(int(a))
            if term or trunc:
                break

    with open(out_path, "w") as f:
        f.write("%d\n" % len(recs))
        for (pn, o4, c, ca, cb, fix, legal, cells, nv, ch, imm, sco, win, chn) in recs:
            f.write(" ".join("%02x" % b for b in pn))
            f.write(" %d %d %d %d %d" % (o4, c, ca, cb, fix))
            f.write(" %d %d %d %d %d %d %d\n" % (legal, cells, nv, ch, imm, sco, win))
            f.write(" ".join("%02x" % b for b in chn) + "\n")

    print("wrote %s: %d cases (%d clearing, %d with chain>1) from %d L%d games"
          % (out_path, len(recs), n_clear, n_chain, n_games, level))


if __name__ == "__main__":
    main()
