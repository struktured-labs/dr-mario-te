#!/usr/bin/env python3
"""Tier-3 adversary policy: cascade_stranded_x._choose_d3_chain_s (the SAME depth-3
search machinery the champion uses -- fast_rtl_x "winner" leaf, ChainRewardD3Decider's
w_chain, #47's g_stranded) plus THREE opponent-aware attack-shaping terms, mechanical
copy + one addition per this project's established discipline (cascade_dbl_x,
cascade_stranded_x). selfcheck() below proves the copy is bit-exact before any knob
is turned on.

THE CHAMPION, pinned by value (do not import this from a mutable source):
    fast_rtl_x.variant("winner") weights, ChainRewardD3Decider family,
    w_chain=180, ws=20 -- i.e. cascade_stranded_x.StrandedChainD3Decider(w, fl,
    topk2=8, maxpass=0, w_chain=180, ws=20). This is h2h_vs.py's "strand180_20"
    pattern and matches the silicon build NES_stomper180s20_20260804.rbf (memory
    dr-mario-eval47-stranded-win). eval47/ab47.py::_choose_base tests the SAME
    ws=20 g_stranded term in isolation (base-only, no chain) as a cheaper mirror
    proof; the deployed VS decider is the chain180+stranded180s20 combination
    reproduced here. AT w_chain=180, ws=20, w_press=w_hold=w_bigsq=0 this kernel
    must be bit-identical to StrandedChainD3Decider -- selfcheck() asserts it.

THE THREE NEW KNOBS (root-level, additive, applied to the SAME `val` cascade_stranded_x
already computes for each of the 32 root candidates -- nothing upstream of it changes):

  w_press  -- val += w_press * opp_maxh * cells   (cells > 0 only)
              Scales the reward of EVERY clearing placement by the opponent's current
              max column height. A shallow clear against a short opponent is worth
              little; the same clear against a tall opponent is worth a lot. This is
              the "hold small clears, unload when it hurts" lever -- NOT a veto, a
              price, so the search can still take an urgent clear if its own board
              needs it (per house rule: price the cost, don't gate the action).
  w_hold   -- val += w_hold * max(0, HOLD_H0 - opp_maxh)   (cells == 0 only)
              A bonus applied ONLY to non-clearing root candidates, active only while
              the opponent is still short (< HOLD_H0, fixed at 8 to match g_tower's
              H0 convention). Makes patient board-building relatively more attractive
              than an available small clear while there is no one to hurt yet.
  w_bigsq  -- val += w_bigsq * cells * cells   (cells > 0 only)
              Pure preference for BIGGER single clears (more cells resolved this
              placement, chain or simultaneous) over small ones, independent of the
              opponent's state. Quadratic so doubling the clear is worth 4x, not 2x --
              favours holding for one big cascade over two small ones even at parity.

  Column TARGETING is deliberately absent as a knob: the ROM's garbage columns are
  `frameCounter & 3`-keyed (vs_harness.py `garbage_columns`), not player-chosen --
  giving the adversary a "target column" parameter would build in a capability the
  real VS rules do not grant (the exact ROM-TRUE-ATTACK-RULE mistake this project has
  been burned by before: don't invent mechanics the disassembly doesn't support).

HOLD_H0 is fixed, not searched, to keep the search space small (5 free ints:
w_chain_adv, ws_adv, w_press, w_hold, w_bigsq).
"""
from __future__ import annotations

import sys
import os
import numpy as np
from numba import njit, int8, int32, int64, float64

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = "/home/struktured/projects/dr_mario_rl"
QA = "/home/struktured/projects/dr-mario-qa-wt/experiments"
for _p in (HERE, ROOT + "/tmp/combo_term", ROOT + "/tmp/endgame", ROOT + "/tmp/tuck",
           ROOT + "/tmp/pillrng", ROOT + "/.claude/worktrees/faithful-sim/src", QA,
           QA + "/tuck_v3"):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from fast_sim_x import NCELL, _virus_count, _stable_desc
from cascade_chain_x import (_leaf_chain, _imm_chain, _base_scan,
                              _expected_third_chain, _choose_d3_chain,
                              NBASE, NT, ChainRewardD3Decider)
from fast_rtl_x import (_VAR_OF_O4, _WIN_SHIP, _W_EXCAV_SHIP, _W_HANG_SHIP, variant,
                         _g_excav_ship, _g_hang_ship)
from cascade_link_x import board_flat
from cascade_stranded_x import _g_stranded47, StrandedChainD3Decider

HOLD_H0 = 8   # opponent max-height below which "hold" is active; fixed, not searched


@njit(int64(int8[:], int8[:], int8[:], int64, int64, int64, int64, int64, int64, int64,
            float64[:], int32[:], int64, int64, int64,
            int64, int64, int64, int64), cache=True, fastmath=False)
def _choose_d3_adv(pcol, pvir, plnk, ca, cb, na, nb, topk2, w_excav, w_hang,
                    w, fl, maxpass, w_chain, ws,
                    opp_maxh, w_press, w_hold, w_bigsq):
    """Mechanical copy of cascade_stranded_x._choose_d3_chain_s + the three
    opponent-aware root terms above. At w_press=w_hold=w_bigsq=0 this must equal
    _choose_d3_chain_s exactly (selfcheck)."""
    c1 = np.empty(NCELL, dtype=int8); v1 = np.empty(NCELL, dtype=int8)
    l1 = np.empty(NCELL, dtype=int8)
    b2col = np.empty((32, NCELL), dtype=int8); b2vir = np.empty((32, NCELL), dtype=int8)
    b2lnk = np.empty((32, NCELL), dtype=int8)
    keys2 = np.empty(32, dtype=float64); imms2 = np.empty(32, dtype=int64)
    order2 = np.empty(32, dtype=int32)
    s2c = np.empty(NCELL, dtype=int8); s2v = np.empty(NCELL, dtype=int8)
    s2l = np.empty(NCELL, dtype=int8)
    e2c = np.empty(NCELL, dtype=int8); e2v = np.empty(NCELL, dtype=int8)
    e2l = np.empty(NCELL, dtype=int8)
    tc = np.empty(NCELL, dtype=int8); tv = np.empty(NCELL, dtype=int8)
    tl = np.empty(NCELL, dtype=int8); mask = np.empty(NCELL, dtype=int8)
    base1 = np.empty(NBASE, dtype=int64); base2 = np.empty(NBASE, dtype=int64)
    base3 = np.empty(NBASE, dtype=int64); terms = np.empty(NT, dtype=int64)
    _base_scan(pcol, pvir, fl, base1)
    best_val = int64(0); best_act = -1; have = False
    for o4 in range(4):
        var = _VAR_OF_O4[o4]
        for cl in range(8):
            ok, nv, cells, leaf1, ch1 = _leaf_chain(pcol, pvir, plnk, base1, var, cl,
                                                     ca, cb, w, fl, c1, v1, l1, mask,
                                                     terms, maxpass, True)
            if ok == 0:
                continue
            imm1 = _imm_chain(nv, cells, ch1, w, w_chain)
            if _virus_count(v1) == 0:
                val = imm1 + int64(_WIN_SHIP)
            else:
                _base_scan(c1, v1, fl, base2)
                m2 = 0
                for o42 in range(4):
                    var2 = _VAR_OF_O4[o42]
                    for cl2 in range(8):
                        ok2, nv2, cells2, lv2, ch2 = _leaf_chain(
                            c1, v1, l1, base2, var2, cl2, na, nb, w, fl,
                            s2c, s2v, s2l, mask, terms, maxpass, True)
                        if ok2 == 0:
                            continue
                        imm2 = _imm_chain(nv2, cells2, ch2, w, w_chain)
                        keys2[m2] = float64(imm2 + lv2)
                        imms2[m2] = imm2
                        for i in range(NCELL):
                            b2col[m2, i] = s2c[i]; b2vir[m2, i] = s2v[i]; b2lnk[m2, i] = s2l[i]
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
                            e2c[i] = b2col[k2, i]; e2v[i] = b2vir[k2, i]; e2l[i] = b2lnk[k2, i]
                        if _virus_count(e2v) == 0:
                            v2 = imms2[k2] + int64(_WIN_SHIP)
                        else:
                            v2 = imms2[k2] + _expected_third_chain(
                                e2c, e2v, e2l, w, fl, base3, terms, tc, tv, tl, mask,
                                maxpass, w_chain)
                        if not have2 or v2 > best2:
                            best2 = v2; have2 = True
                    val = imm1 + leaf1 + ((best2 - leaf1) >> int64(1))
                val += w_excav * _g_excav_ship(c1, v1) + w_hang * _g_hang_ship(c1, v1)
            val -= ws * _g_stranded47(c1, v1)
            # ---- the three new opponent-aware terms (root-level, additive only) ----
            if cells > 0:
                val += w_press * opp_maxh * cells
                val += w_bigsq * cells * cells
            else:
                hold_gap = HOLD_H0 - opp_maxh
                if hold_gap > 0:
                    val += w_hold * hold_gap
            if not have or val > best_val:
                best_val = val; best_act = var * 8 + cl; have = True
    return best_act


class AdversaryD3Decider:
    """Opponent-AWARE decider: choose(board, cur, nxt, opp_board), 4-arg signature
    (matches vs_harness.play_match's native calling convention -- no blind() wrap).

    Parameter vector (5 ints), the whole adversary policy search space:
      w_chain, ws        -- the champion's own two knobs, but free to differ from 180/20
      w_press, w_hold, w_bigsq -- the three opponent-aware terms in _choose_d3_adv
    """

    def __init__(self, weights, flags, topk2=8, maxpass=0,
                 w_chain=180, ws=20, w_press=0, w_hold=0, w_bigsq=0,
                 w_excav=_W_EXCAV_SHIP, w_hang=_W_HANG_SHIP):
        self.w = np.asarray(weights, dtype=np.float64)
        self.fl = np.asarray(flags, dtype=np.int32)
        self.topk2 = int(topk2)
        self.maxpass = int(maxpass)
        self.w_chain = int(w_chain)
        self.ws = int(ws)
        self.w_press = int(w_press)
        self.w_hold = int(w_hold)
        self.w_bigsq = int(w_bigsq)
        self.w_excav = int(w_excav)
        self.w_hang = int(w_hang)

    @staticmethod
    def from_vector(vec, weights, flags, topk2=8):
        """vec = (w_chain, ws, w_press, w_hold, w_bigsq), the search's genome."""
        w_chain, ws, w_press, w_hold, w_bigsq = (int(round(x)) for x in vec)
        return AdversaryD3Decider(weights, flags, topk2=topk2, w_chain=w_chain, ws=ws,
                                  w_press=w_press, w_hold=w_hold, w_bigsq=w_bigsq)

    def to_vector(self):
        return (self.w_chain, self.ws, self.w_press, self.w_hold, self.w_bigsq)

    def choose(self, board, cur, nxt, opp_board):
        col, vir = board_flat(board)
        lnk = np.ascontiguousarray(board.link, dtype=np.int8).reshape(-1)
        opp_maxh = int(opp_board.column_heights().max())
        a = _choose_d3_adv(col, vir, lnk, cur.a, cur.b, nxt.a, nxt.b, self.topk2,
                           self.w_excav, self.w_hang, self.w, self.fl, self.maxpass,
                           self.w_chain, self.ws, opp_maxh,
                           self.w_press, self.w_hold, self.w_bigsq)
        return None if a < 0 else int(a)


def warmup_adv(topk2=8):
    """Numba JIT warmup on a dummy board + dummy opponent height -- run once per
    worker process before timing anything."""
    bc = np.zeros(NCELL, dtype=np.int8); bv = np.zeros(NCELL, dtype=np.int8)
    bl = np.zeros(NCELL, dtype=np.int8)
    w, fl = variant("winner")
    w = np.asarray(w, dtype=np.float64); fl = np.asarray(fl, dtype=np.int32)
    _choose_d3_adv(bc, bv, bl, 1, 2, 1, 2, topk2, int(_W_EXCAV_SHIP), int(_W_HANG_SHIP),
                  w, fl, 0, 180, 20, 8, 0, 0, 0)


def selfcheck(n=200, seed=7):
    """(a) w_press=w_hold=w_bigsq=0 (any opp_maxh) must reproduce
    cascade_stranded_x's _choose_d3_chain_s == cascade_chain_x._choose_d3_chain at
    ws=0, action-identical on n random boards -- proves the mechanical copy didn't
    drift. (b) at the champion's own values (w_chain=180, ws=20, knobs=0) the
    adversary kernel must equal StrandedChainD3Decider.choose() exactly, on the
    SAME boards, so the adversary is provably a strict superset of the champion's
    decision function. (c) each knob, turned on alone, must move >=1 decision on
    the corpus (a knob with zero effect anywhere is not a knob, it's dead code)."""
    import fast_rtl_x as X
    from cascade_stranded_x import _choose_d3_chain_s
    rng = np.random.default_rng(seed)
    w, fl = X.variant("winner")
    w = np.asarray(w, dtype=np.float64); fl = np.asarray(fl, dtype=np.int32)
    moved_press = moved_hold = moved_bigsq = 0
    for t in range(n):
        col = np.zeros(NCELL, dtype=np.int8); vir = np.zeros(NCELL, dtype=np.int8)
        lnk = np.zeros(NCELL, dtype=np.int8)
        for i in range(NCELL):
            r = i // 8
            if r >= 8 and rng.random() < 0.35:
                col[i] = rng.integers(1, 4)
                if rng.random() < 0.5:
                    vir[i] = 1
        ca, cb, na, nb = (int(rng.integers(1, 4)) for _ in range(4))
        opp_h = int(rng.integers(0, 16))

        a_chain = _choose_d3_chain(col, vir, lnk, ca, cb, na, nb, 8,
                                   int(_W_EXCAV_SHIP), int(_W_HANG_SHIP), w, fl, 0, 180)
        a_strand = _choose_d3_chain_s(col, vir, lnk, ca, cb, na, nb, 8,
                                      int(_W_EXCAV_SHIP), int(_W_HANG_SHIP), w, fl, 0,
                                      180, 20)
        a_adv0 = _choose_d3_adv(col, vir, lnk, ca, cb, na, nb, 8,
                                int(_W_EXCAV_SHIP), int(_W_HANG_SHIP), w, fl, 0,
                                180, 0, opp_h, 0, 0, 0)
        assert a_adv0 == a_chain, f"board {t}: ws=0,knobs=0 diverged from _choose_d3_chain"
        a_adv_champ = _choose_d3_adv(col, vir, lnk, ca, cb, na, nb, 8,
                                     int(_W_EXCAV_SHIP), int(_W_HANG_SHIP), w, fl, 0,
                                     180, 20, opp_h, 0, 0, 0)
        assert a_adv_champ == a_strand, \
            f"board {t}: champion params diverged from StrandedChainD3Decider"

        a_press = _choose_d3_adv(col, vir, lnk, ca, cb, na, nb, 8,
                                 int(_W_EXCAV_SHIP), int(_W_HANG_SHIP), w, fl, 0,
                                 180, 20, opp_h, 40, 0, 0)
        if a_press != a_strand:
            moved_press += 1
        a_hold = _choose_d3_adv(col, vir, lnk, ca, cb, na, nb, 8,
                                int(_W_EXCAV_SHIP), int(_W_HANG_SHIP), w, fl, 0,
                                180, 20, opp_h, 0, 200, 0)
        if a_hold != a_strand:
            moved_hold += 1
        a_bigsq = _choose_d3_adv(col, vir, lnk, ca, cb, na, nb, 8,
                                 int(_W_EXCAV_SHIP), int(_W_HANG_SHIP), w, fl, 0,
                                 180, 20, opp_h, 0, 0, 10)
        if a_bigsq != a_strand:
            moved_bigsq += 1
    assert moved_press > 0, "w_press never moved a single decision in the corpus"
    assert moved_hold > 0, "w_hold never moved a single decision in the corpus"
    assert moved_bigsq > 0, "w_bigsq never moved a single decision in the corpus"
    return {"moved_press": moved_press, "moved_hold": moved_hold, "moved_bigsq": moved_bigsq,
            "n": n}


if __name__ == "__main__":
    r = selfcheck()
    print(f"selfcheck OK: ws=0 bit-identical to _choose_d3_chain; champion params "
          f"bit-identical to StrandedChainD3Decider; knobs moved "
          f"press={r['moved_press']} hold={r['moved_hold']} bigsq={r['moved_bigsq']} "
          f"of {r['n']} boards")
