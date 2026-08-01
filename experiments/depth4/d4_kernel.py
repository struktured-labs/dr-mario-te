#!/usr/bin/env python3
"""DEPTH-4 on the CURRENT ship kernel, delta-backed -- the re-test rig for the n=10
depth-4 NO-GO.

WHY A NEW KERNEL AND NOT THE OLD ONE
------------------------------------
The standing NO-GO (`dr-mario-mods/tmp/decide_d4_incr.py`, 2026-07-12, n=10) was
measured on `nes_d3_golden.decide_d3_incr`, i.e. the WEEKEND-era python golden:
topk1=32 with a ply-1 sort+prune, no DISC_SHIFT documented at that call site, and
whatever leaf weights the golden defaulted to.  The brain we actually ship today is
`fast_rtl_x._choose_d3_ship_eh` -- FULL ply-1 (no prune, enumeration order), topk2=8,
4-pill stratified THIRD with `tot//4`, DISC_SHIFT=1 blend, the ply-1 excav/hang root
add-on, and the coef-opt2 `winner` leaf.  Re-testing the old arm would re-test a brain
we no longer have.

So d4 here is `_choose_d3_ship_eh_delta` with EXACTLY ONE structural change: the ply-3
MAX layer, instead of terminating at a leaf, keeps its top-`topk3` placements and
expands each into a second chance layer (pill 4) + a ply-4 MAX -> leaf.  Everything
else -- enumeration order, tie-breaks, the topk2 stable sort, the DISC_SHIFT blend,
the eh add-on, imm -- is byte identical to the d3 arm.

  ply1 MAX   current pill (KNOWN)     full 32, no prune
   +- ply2 MAX  next pill (KNOWN)     full 32 -> stable-desc top-8
      +- ply3 CHANCE  pill 3          4-pill stratified THIRD, integer mean //4
         +- ply3 MAX  place           full 32 -> stable-desc top-K3   <-- NEW beam
            +- ply4 CHANCE  pill 4    configurable subset, integer mean   <-- NEW ply
               +- ply4 MAX  place     full 32 -> leaf

DEGENERACY GATE (the same trick the 07-12 rig used, and the only reason this port can
be trusted): with `ply4_mode=0` (ply4 returns the plain ship leaf of b3) and `topk3<=0`
(no ply-3 beam), the added layer collapses and `_choose_d4_ship_eh_delta` MUST return
the identical action to `_choose_d3_ship_eh_delta` on every board.  `validate()` checks
it.  Any disagreement means the port -- not depth -- moved the answer.

BOTH ARMS RUN THE DELTA LEAF.  The d3 arm is `_choose_d3_ship_eh_delta`, not the full
rescan; the d4 leaves are the same `_expand_leaf_delta` / `_leaf_delta_noboard` calls.
Comparing a delta arm to a non-delta arm would confound the kernel with the depth.
"""
from __future__ import annotations
import os
import sys

import numpy as np
from numba import njit, int64

HERE = os.path.dirname(os.path.abspath(__file__))
SNAP = os.path.join(HERE, "snap")
for _p in (SNAP,):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import fast_rtl_x as F                                                  # noqa: E402
from fast_rtl_x import (NCELL, NBASE, NT, _WIN_SHIP, _VAR_OF_O4,        # noqa: E402
                        _THIRD_X, _THIRD_Y, R_WVIR, R_WCELLS, R_VBONUS,
                        _base_scan, _leafv_ship, _expand_leaf_delta,
                        _leaf_delta_noboard, _g_excav_ship, _g_hang_ship,
                        _W_EXCAV_SHIP, _W_HANG_SHIP)
from fast_sim_x import _virus_count, _stable_desc                       # noqa: E402
from fast_sim_x import board_flat                                       # noqa: E402

# ---- ply-4 chance subsets (1-based faithful colours, == _THIRD_X/_THIRD_Y coding) ----
# "4" is the SAME stratified subset the ship uses at ply 3.  The 07-12 rig's default was
# the coarse "2", which its own docstring flags as biasing the estimate -- with the delta
# we can afford the unbiased one, so "4" is the primary arm here.
_P4 = {
    "2": (np.array([1, 3], dtype=np.int64), np.array([2, 1], dtype=np.int64)),
    "4": (_THIRD_X.copy(), _THIRD_Y.copy()),
    "9": (np.array([x for x in (1, 2, 3) for _ in (1, 2, 3)], dtype=np.int64),
          np.array([y for _ in (1, 2, 3) for y in (1, 2, 3)], dtype=np.int64)),
}


@njit(cache=True, fastmath=False)
def _expected_fourth(b3c, b3v, w, fl, p4x, p4y, base4, terms, tc, tv):
    """ply-4 CHANCE + ply-4 MAX -> leaf.  Integer mean over the pill subset, exactly the
    shape of `_expected_third_ship_delta` one ply down."""
    if _virus_count(b3v) == 0:
        return int64(_WIN_SHIP)
    _base_scan(b3c, b3v, fl, base4)
    n4 = p4x.shape[0]
    tot = int64(0)
    for t in range(n4):
        x = p4x[t]
        y = p4y[t]
        best4 = int64(0)
        have4 = False
        for o4 in range(4):
            var = _VAR_OF_O4[o4]
            for cl in range(8):
                ok, nv, cells, lv = _leaf_delta_noboard(b3c, b3v, base4, var, cl, x, y,
                                                        w, fl, tc, tv, terms)
                if ok == 0:
                    continue
                vv = int64(w[R_WVIR]) * nv + int64(w[R_WCELLS]) * cells \
                    + (int64(w[R_VBONUS]) if nv >= 2 else int64(0)) + lv
                if not have4 or vv > best4:
                    best4 = vv
                    have4 = True
        tot += best4 if have4 else _leafv_ship(b3c, b3v, w, fl)
    return tot // int64(n4)


@njit(cache=True, fastmath=False)
def _expected_third_d4(b2c, b2v, w, fl, topk3, ply4_mode, p4x, p4y,
                       base3, base4, terms, tc, tv, c3, v3,
                       b3col, b3vir, keys3, imms3, order3, e3c, e3v):
    """ply-3 CHANCE + ply-3 MAX(beam topk3) + ply-4 subtree.

    `ply4_mode=0` makes the ply-4 subtree return the plain ship leaf of b3, which with
    `topk3<=0` reproduces `_expected_third_ship_delta` value-for-value."""
    if _virus_count(b2v) == 0:
        return int64(_WIN_SHIP)
    _base_scan(b2c, b2v, fl, base3)
    tot = int64(0)
    for t in range(4):
        x = _THIRD_X[t]
        y = _THIRD_Y[t]
        m3 = 0
        for o4 in range(4):
            var = _VAR_OF_O4[o4]
            for cl in range(8):
                ok, nv, cells, lv = _expand_leaf_delta(b2c, b2v, base3, var, cl, x, y,
                                                       c3, v3, w, fl, terms)
                if ok == 0:
                    continue
                imm3 = int64(w[R_WVIR]) * nv + int64(w[R_WCELLS]) * cells \
                    + (int64(w[R_VBONUS]) if nv >= 2 else int64(0))
                keys3[m3] = np.float64(imm3 + lv)
                imms3[m3] = imm3
                for i in range(NCELL):
                    b3col[m3, i] = c3[i]
                    b3vir[m3, i] = v3[i]
                m3 += 1
        if m3 == 0:
            tot += _leafv_ship(b2c, b2v, w, fl)
            continue
        _stable_desc(keys3, m3, order3)
        kk3 = m3 if topk3 <= 0 or topk3 > m3 else topk3
        best3 = int64(0)
        have3 = False
        for s3 in range(kk3):
            k3 = order3[s3]
            for i in range(NCELL):
                e3c[i] = b3col[k3, i]
                e3v[i] = b3vir[k3, i]
            if _virus_count(e3v) == 0:
                v3v = imms3[k3] + int64(_WIN_SHIP)
            elif ply4_mode == 0:
                v3v = imms3[k3] + _leafv_ship(e3c, e3v, w, fl)
            else:
                v3v = imms3[k3] + _expected_fourth(e3c, e3v, w, fl, p4x, p4y,
                                                   base4, terms, tc, tv)
            if not have3 or v3v > best3:
                best3 = v3v
                have3 = True
        tot += best3
    return tot // int64(4)


@njit(cache=True, fastmath=False)
def _choose_d4_ship_eh_delta(pcol, pvir, ca, cb, na, nb, topk2, topk3, ply4_mode,
                             p4x, p4y, w_excav, w_hang, w, fl):
    """`_choose_d3_ship_eh_delta` with the ply-3 MAX layer replaced by beam+ply-4.
    Every other line is the d3 original."""
    c1 = np.empty(NCELL, dtype=np.int8); v1 = np.empty(NCELL, dtype=np.int8)
    b2col = np.empty((32, NCELL), dtype=np.int8); b2vir = np.empty((32, NCELL), dtype=np.int8)
    keys2 = np.empty(32, dtype=np.float64); imms2 = np.empty(32, dtype=np.int64)
    order2 = np.empty(32, dtype=np.int32)
    s2c = np.empty(NCELL, dtype=np.int8); s2v = np.empty(NCELL, dtype=np.int8)
    e2c = np.empty(NCELL, dtype=np.int8); e2v = np.empty(NCELL, dtype=np.int8)
    tc = np.empty(NCELL, dtype=np.int8); tv = np.empty(NCELL, dtype=np.int8)
    c3 = np.empty(NCELL, dtype=np.int8); v3 = np.empty(NCELL, dtype=np.int8)
    b3col = np.empty((32, NCELL), dtype=np.int8); b3vir = np.empty((32, NCELL), dtype=np.int8)
    keys3 = np.empty(32, dtype=np.float64); imms3 = np.empty(32, dtype=np.int64)
    order3 = np.empty(32, dtype=np.int32)
    e3c = np.empty(NCELL, dtype=np.int8); e3v = np.empty(NCELL, dtype=np.int8)
    base1 = np.empty(NBASE, dtype=np.int64); base2 = np.empty(NBASE, dtype=np.int64)
    base3 = np.empty(NBASE, dtype=np.int64); base4 = np.empty(NBASE, dtype=np.int64)
    terms = np.empty(NT, dtype=np.int64)
    _base_scan(pcol, pvir, fl, base1)
    best_val = int64(0); best_act = -1; have = False
    for o4 in range(4):
        var = _VAR_OF_O4[o4]
        for cl in range(8):
            ok, nv, cells, leaf1 = _expand_leaf_delta(pcol, pvir, base1, var, cl, ca, cb,
                                                      c1, v1, w, fl, terms)
            if ok == 0:
                continue
            imm1 = int64(w[R_WVIR]) * nv + int64(w[R_WCELLS]) * cells \
                + (int64(w[R_VBONUS]) if nv >= 2 else int64(0))
            if _virus_count(v1) == 0:
                val = imm1 + int64(_WIN_SHIP)
            else:
                _base_scan(c1, v1, fl, base2)
                m2 = 0
                for o42 in range(4):
                    var2 = _VAR_OF_O4[o42]
                    for cl2 in range(8):
                        ok2, nv2, cells2, lv2 = _expand_leaf_delta(c1, v1, base2, var2, cl2,
                                                                   na, nb, s2c, s2v, w, fl,
                                                                   terms)
                        if ok2 == 0:
                            continue
                        imm2 = int64(w[R_WVIR]) * nv2 + int64(w[R_WCELLS]) * cells2 \
                            + (int64(w[R_VBONUS]) if nv2 >= 2 else int64(0))
                        keys2[m2] = np.float64(imm2 + lv2)
                        imms2[m2] = imm2
                        for i in range(NCELL):
                            b2col[m2, i] = s2c[i]; b2vir[m2, i] = s2v[i]
                        m2 += 1
                if m2 == 0:
                    val = imm1 + leaf1
                else:
                    _stable_desc(keys2, m2, order2)
                    kk2 = m2 if topk2 <= 0 or topk2 > m2 else topk2
                    best2 = int64(0); have2 = False
                    for s2 in range(kk2):
                        k2 = order2[s2]
                        for i in range(NCELL):
                            e2c[i] = b2col[k2, i]; e2v[i] = b2vir[k2, i]
                        if _virus_count(e2v) == 0:
                            v2 = imms2[k2] + int64(_WIN_SHIP)
                        else:
                            v2 = imms2[k2] + _expected_third_d4(
                                e2c, e2v, w, fl, topk3, ply4_mode, p4x, p4y,
                                base3, base4, terms, tc, tv, c3, v3,
                                b3col, b3vir, keys3, imms3, order3, e3c, e3v)
                        if not have2 or v2 > best2:
                            best2 = v2; have2 = True
                    val = imm1 + leaf1 + ((best2 - leaf1) >> int64(1))
                val += w_excav * _g_excav_ship(c1, v1) + w_hang * _g_hang_ship(c1, v1)
            if not have or val > best_val:
                best_val = val; best_act = var * 8 + cl; have = True
    return best_act


class FastShipD4DeciderEHDelta:
    """Board-in decider with the SAME contract as `FastShipD3DeciderEHDelta`, so it drops
    into every existing harness (`destroy._G['dec']`, `latch_ab`, `plan_ab`, ...)."""

    def __init__(self, weights, flags, topk2=8, topk3=6, pills4="4",
                 w_excav=_W_EXCAV_SHIP, w_hang=_W_HANG_SHIP, ply4_mode=1):
        self.w = np.asarray(weights, dtype=np.float64)
        self.fl = np.asarray(flags, dtype=np.int32)
        self.topk2 = int(topk2)
        self.topk3 = int(topk3)
        self.ply4_mode = int(ply4_mode)
        self.p4x, self.p4y = _P4[str(pills4)]
        self.w_excav = int(w_excav)
        self.w_hang = int(w_hang)

    def choose(self, board, cur, nxt):
        col, vir = board_flat(board)
        a = _choose_d4_ship_eh_delta(col, vir, cur.a, cur.b, nxt.a, nxt.b,
                                     self.topk2, self.topk3, self.ply4_mode,
                                     self.p4x, self.p4y,
                                     self.w_excav, self.w_hang, self.w, self.fl)
        return None if a < 0 else int(a)


def warmup_d4(topk2=8, topk3=6, pills4="4"):
    bc = np.zeros(NCELL, dtype=np.int8); bv = np.zeros(NCELL, dtype=np.int8)
    w, fl = F.variant("winner")
    p4x, p4y = _P4[str(pills4)]
    F.warmup_delta(topk2=topk2)
    _choose_d4_ship_eh_delta(bc, bv, 1, 2, 1, 2, topk2, topk3, 1, p4x, p4y,
                             int(_W_EXCAV_SHIP), int(_W_HANG_SHIP), w, fl)
    _choose_d4_ship_eh_delta(bc, bv, 1, 2, 1, 2, topk2, 0, 0, p4x, p4y,
                             int(_W_EXCAV_SHIP), int(_W_HANG_SHIP), w, fl)


# ============================================================== degeneracy gate
def _random_boards(n, level, seed0=9000):
    """Real boards off real trajectories: play the ship d3 brain and snapshot mid-game
    states, so the gate runs on the distribution the A/B will actually see (a uniform
    random fill would over-represent boards the search never visits)."""
    sys.path.insert(0, "/home/struktured/projects/dr_mario_rl/.claude/worktrees/faithful-sim/src")
    from drmario.faithful_env import FaithfulDrMarioEnv
    w, fl = F.variant("winner")
    dec = F.FastShipD3DeciderEHDelta(w, fl, topk2=8)
    out = []
    s = seed0
    while len(out) < n:
        env = FaithfulDrMarioEnv(level=level, seed=s, max_pills=300)
        env.reset()
        s += 1
        for _ in range(300):
            col, vir = board_flat(env.board)
            out.append((col.copy(), vir.copy(), env.cur.a, env.cur.b, env.nxt.a, env.nxt.b))
            if len(out) >= n:
                break
            a = dec.choose(env.board, env.cur, env.nxt)
            if a is None:
                break
            _o, _r, term, trunc, _i = env.step(int(a))
            if term or trunc:
                break
    return out


def validate(n=300, level=11, arm="winner", verbose=True):
    """d4 with a degenerate ply-4 and NO ply-3 beam MUST equal d3, action for action."""
    w, fl = F.variant(arm)
    F.warmup_delta(); warmup_d4()
    p4x, p4y = _P4["4"]
    boards = _random_boards(n, level)
    agree = 0
    bad = []
    for (col, vir, ca, cb, na, nb) in boards:
        a3 = F._choose_d3_ship_eh_delta(col, vir, ca, cb, na, nb, 8,
                                        int(_W_EXCAV_SHIP), int(_W_HANG_SHIP), w, fl)
        a4 = _choose_d4_ship_eh_delta(col, vir, ca, cb, na, nb, 8, 0, 0, p4x, p4y,
                                      int(_W_EXCAV_SHIP), int(_W_HANG_SHIP), w, fl)
        if a3 == a4:
            agree += 1
        else:
            bad.append((int(a3), int(a4)))
    if verbose:
        print(f"degeneracy gate (ply4=leaf, topk3=inf): {agree}/{len(boards)} agree")
        for x in bad[:5]:
            print(f"   d3={x[0]}  d4-degenerate={x[1]}")
    return agree == len(boards)


def validate_delta_vs_full(n=200, level=11, arm="winner", verbose=True):
    """The substitution check the task demands BEFORE any A/B: on this snapshot, does the
    delta d3 kernel return the same action as the full-rescan d3 kernel?  If it does not,
    every 'delta arm' number below is measuring the delta, not the depth."""
    w, fl = F.variant(arm)
    F.warmup_ship_eh(); F.warmup_delta()
    boards = _random_boards(n, level, seed0=7000)
    agree = 0
    for (col, vir, ca, cb, na, nb) in boards:
        af = F._choose_d3_ship_eh(col, vir, ca, cb, na, nb, 8,
                                  int(_W_EXCAV_SHIP), int(_W_HANG_SHIP), w, fl)
        ad = F._choose_d3_ship_eh_delta(col, vir, ca, cb, na, nb, 8,
                                        int(_W_EXCAV_SHIP), int(_W_HANG_SHIP), w, fl)
        agree += (af == ad)
    if verbose:
        print(f"delta-vs-full d3 substitution: {agree}/{len(boards)} agree")
    return agree == len(boards)


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "validate"
    n = int(sys.argv[2]) if len(sys.argv) > 2 else 300
    if cmd == "validate":
        ok1 = validate_delta_vs_full(min(n, 200))
        ok2 = validate(n)
        print(f"GATE {'PASS' if (ok1 and ok2) else 'FAIL'}")
        raise SystemExit(0 if (ok1 and ok2) else 1)
    elif cmd == "bench":
        import time
        w, fl = F.variant("winner")
        F.warmup_delta(); warmup_d4()
        boards = _random_boards(n, 11, seed0=5000)
        p4x, p4y = _P4[os.environ.get("DR_PILLS4", "4")]
        k3 = int(os.environ.get("DR_TOPK3", "6"))
        for label, fn in (("d3", None), (f"d4(k3={k3},p4={p4x.shape[0]})", 1)):
            t0 = time.perf_counter()
            for (col, vir, ca, cb, na, nb) in boards:
                if fn is None:
                    F._choose_d3_ship_eh_delta(col, vir, ca, cb, na, nb, 8,
                                               int(_W_EXCAV_SHIP), int(_W_HANG_SHIP), w, fl)
                else:
                    _choose_d4_ship_eh_delta(col, vir, ca, cb, na, nb, 8, k3, 1, p4x, p4y,
                                             int(_W_EXCAV_SHIP), int(_W_HANG_SHIP), w, fl)
            dt = time.perf_counter() - t0
            print(f"  {label:>18}: {dt / len(boards) * 1e3:8.2f} ms/decision  "
                  f"({len(boards)} boards, {dt:.1f}s)")
