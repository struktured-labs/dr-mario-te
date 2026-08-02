#!/usr/bin/env python3
"""Is link-body gravity CONFLUENT?  The answer decides how much silicon the RTL needs.

`cascade_link_x._link_gravity` mirrors the engine exactly: it enumerates bodies
row-major, then STABLE-SORTS them lowest-first before dropping each one row.  A 128-entry
stable sort is expensive in RTL (compare/swap network or a multi-pass bubble), so before
building it I want to know whether the sort is OBSERVABLE in the fixpoint.

Claim under test: body gravity is a confluent rewriting system -- bodies only ever move
DOWN, so whatever order you drop them in, iterating to "nothing moved" lands on the same
board.  If true, the RTL can use a plain bottom-up sweep with no sort and no priority
queue, and still be cell-exact with the engine.

The RTL-shaped variant here is deliberately the CHEAPEST thing that could work, and it
differs from the reference in all three ways that could matter:
  - representative cell: BOTTOM of a vertical pair / LEFT of a horizontal pair
    (reference uses TOP / LEFT, because it enumerates row-major top-down)
  - scan order: bottom-up rows, left-to-right columns (reference: top-down)
  - no stable sort at all (reference: stable_desc on max body row)

Compared on REAL self-play boards over every legal placement, both round caps, on the
FULL result: colour plane, virus plane, LINK plane, cells, viruses, and chain depth.
Comparing only cells/viruses would pass while the link plane rotted.

Usage: gravity_order_test.py [n_games] [level]
"""
from __future__ import annotations
import sys, os
import numpy as np
from numba import njit, int8, int64

HERE = "/home/struktured/projects/dr_mario_rl/tmp/combo_term"
ROOT = "/home/struktured/projects/dr_mario_rl"
SIM = ROOT + "/.claude/worktrees/faithful-sim"
for p in (HERE, ROOT + "/tmp/endgame", SIM + "/src"):
    if p not in sys.path:
        sys.path.insert(0, p)

import fast_rtl_x as F
import cascade_link_x as L
from cascade_link_x import (LINK_NONE, LINK_UP, LINK_DOWN, LINK_LEFT, LINK_RIGHT,
                            _apply_clear_linked, _find_clears_mask)
from fast_sim_x import ROWS, COLS, NCELL
from fb import FB
from drmario.faithful_env import FaithfulDrMarioEnv


# ------------------------------------------------------- the RTL-shaped candidate
@njit(cache=True, fastmath=False)
def _link_gravity_rtl(col, vir, lnk):
    """Bottom-up sweep, canonical representative, NO sort.  Exactly what a state machine
    walking the board backwards can do with a single pointer and no scratch RAM.

    Representative rule (removes the need for a `seen` array entirely):
      LINK_NONE  -> single body here
      LINK_UP    -> bottom half of a vertical pair; partner is idx-COLS (above, not yet
                    scanned this pass because we sweep bottom-up)
      LINK_RIGHT -> left half of a horizontal pair; partner is idx+1
      LINK_DOWN / LINK_LEFT -> the partner is the representative; skip
    A link pointing off-board or at an empty cell is a dangling link: treat as a single,
    matching the reference's `else` arm.
    """
    while True:
        moved = False
        for r in range(ROWS - 2, -1, -1):        # bottom row can never fall
            for c in range(COLS):
                idx = r * COLS + c
                if col[idx] == 0 or vir[idx]:
                    continue
                lk = lnk[idx]
                k0 = idx
                k1 = -1
                if lk == LINK_UP:
                    pr = r - 1
                    if pr >= 0 and col[pr * COLS + c] != 0:
                        k1 = pr * COLS + c
                elif lk == LINK_RIGHT:
                    pc = c + 1
                    if pc < COLS and col[r * COLS + pc] != 0:
                        k1 = r * COLS + pc
                elif lk == LINK_DOWN or lk == LINK_LEFT:
                    # partner is the representative -- but only if it really exists
                    if lk == LINK_DOWN:
                        pr = r + 1
                        if pr < ROWS and col[pr * COLS + c] != 0:
                            continue
                    else:
                        pc = c - 1
                        if pc >= 0 and col[r * COLS + pc] != 0:
                            continue
                    # dangling -> fall through as a single
                # can the whole body fall?
                fall = True
                for t in range(2):
                    kk = k0 if t == 0 else k1
                    if kk < 0:
                        continue
                    if kk // COLS + 1 >= ROWS:
                        fall = False
                        break
                    nk = kk + COLS
                    if nk != k0 and nk != k1 and col[nk] != 0:
                        fall = False
                        break
                if not fall:
                    continue
                c0v = col[k0]; v0v = vir[k0]; l0v = lnk[k0]
                col[k0] = 0; vir[k0] = 0; lnk[k0] = LINK_NONE
                if k1 >= 0:
                    c1v = col[k1]; v1v = vir[k1]; l1v = lnk[k1]
                    col[k1] = 0; vir[k1] = 0; lnk[k1] = LINK_NONE
                col[k0 + COLS] = c0v; vir[k0 + COLS] = v0v; lnk[k0 + COLS] = l0v
                if k1 >= 0:
                    col[k1 + COLS] = c1v; vir[k1 + COLS] = v1v; lnk[k1 + COLS] = l1v
                moved = True
        if not moved:
            break


@njit(cache=True, fastmath=False)
def _resolve_rtl(col, vir, lnk, mask, maxpass):
    cells = 0; nv = 0; chain = 0
    while maxpass <= 0 or chain < maxpass:
        n = _find_clears_mask(col, mask)
        if n == 0:
            break
        chain += 1
        cells += n
        nv += _apply_clear_linked(col, vir, lnk, mask)
        _link_gravity_rtl(col, vir, lnk)
    return (cells, nv, chain)


@njit(cache=True, fastmath=False)
def _resolve_ref(col, vir, lnk, mask, maxpass):
    """Reference resolve, but returning chain too (cascade_link_x._resolve_linked does)."""
    cells = 0; nv = 0; chain = 0
    while maxpass <= 0 or chain < maxpass:
        n = _find_clears_mask(col, mask)
        if n == 0:
            break
        chain += 1
        cells += n
        nv += _apply_clear_linked(col, vir, lnk, mask)
        L._link_gravity(col, vir, lnk)
    return (cells, nv, chain)


def _place(col, vir, lnk, var, c, pa, pb, ccol, cvir, clnk):
    """Mirror of _expand_linked's placement half (uses the reference _resting)."""
    from fast_sim_x import _resting
    ok, r0, c0, r1, c1 = _resting(col, var, c)
    if ok == 0:
        return None
    ccol[:] = col; cvir[:] = vir; clnk[:] = lnk
    col0, col1 = (pa, pb) if var in (0, 2) else (pb, pa)
    i0 = r0 * COLS + c0; i1 = r1 * COLS + c1
    ccol[i0] = col0; ccol[i1] = col1
    cvir[i0] = 0; cvir[i1] = 0
    if var < 2:
        clnk[i0] = LINK_RIGHT; clnk[i1] = LINK_LEFT
    else:
        clnk[i0] = LINK_DOWN; clnk[i1] = LINK_UP
    return True


def main():
    n_games = int(sys.argv[1]) if len(sys.argv) > 1 else 6
    level = int(sys.argv[2]) if len(sys.argv) > 2 else 11
    w, fl = F.variant("winner")
    F.warmup_ship_eh(); F.warmup_delta(); L.warmup_linked()
    dec = F.FastShipD3DeciderEHDelta(w, fl, topk2=8)

    a1 = [np.empty(NCELL, dtype=np.int8) for _ in range(3)]
    a2 = [np.empty(NCELL, dtype=np.int8) for _ in range(3)]
    mk = np.empty(NCELL, dtype=np.int8)

    n = 0
    bad = dict(cells=0, vir=0, chain=0, col=0, virplane=0, link=0)
    chained = 0          # placements whose fixpoint actually took >1 round
    maxchain = 0
    first = None
    for maxpass in (1, 0):
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
                pa, pb = env.cur.a, env.cur.b
                for var in range(4):
                    for c in range(COLS):
                        if _place(col, vir, lnk, var, c, pa, pb, *a1) is None:
                            continue
                        _place(col, vir, lnk, var, c, pa, pb, *a2)
                        rc, rv, rch = _resolve_ref(a1[0], a1[1], a1[2], mk, maxpass)
                        tc, tv, tch = _resolve_rtl(a2[0], a2[1], a2[2], mk, maxpass)
                        n += 1
                        if maxpass == 0 and rch > 1:
                            chained += 1
                            maxchain = max(maxchain, rch)
                        okall = True
                        if rc != tc: bad["cells"] += 1; okall = False
                        if rv != tv: bad["vir"] += 1; okall = False
                        if rch != tch: bad["chain"] += 1; okall = False
                        if not np.array_equal(a1[0], a2[0]): bad["col"] += 1; okall = False
                        if not np.array_equal(a1[1], a2[1]): bad["virplane"] += 1; okall = False
                        if not np.array_equal(a1[2], a2[2]): bad["link"] += 1; okall = False
                        if not okall and first is None:
                            first = (s, var, c, maxpass, rc, tc, rch, tch)
                _, _, term, trunc, _ = env.step(int(a))
                if term or trunc:
                    break

    print(f"\n===== GRAVITY ORDER CONFLUENCE (L{level}, {n_games} games) =====")
    print(f"placements compared (ref sort vs RTL sweep) : {n:,}   [maxpass 1 and fixpoint]")
    print(f"  fixpoint placements with chain > 1        : {chained:,}  (max chain {maxchain})")
    for k, v in bad.items():
        print(f"  {k:10s} mismatch : {v}")
    if first:
        print(f"  first divergence: seed={first[0]} var={first[1]} col={first[2]} "
              f"maxpass={first[3]} cells {first[4]}/{first[5]} chain {first[6]}/{first[7]}")
    ok = not any(bad.values())
    print("\nVERDICT:", "CONFLUENT -- RTL needs no sort" if ok else "ORDER MATTERS -- sort required")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
