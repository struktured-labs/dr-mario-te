#!/usr/bin/env python3
"""STEER10 (2026-10-06): candidate rules aimed at the AI's ENDGAME STALLS on sealed EDGE columns (couch 10/05 vs
dr. lulu: all 3 of her wins were AI stalls at 7 / 16 / 13 viruses on edge-column viruses; 10/04 M5 G2 alike).

Base = the silicon-faithful brain (braingap Leaf6FwDecider, every fw switch on, dist_target W60 vk4 = DIST60 = the FAIR
build's brain). Every rule below is a ROOT-SIDE (firmware) change, except the DIST target choice (firmware picks the
target; the RTL DIST FSM is unchanged as long as kdig == 0):

TARGET (w6_for, firmware-side target pick; leaf term unchanged = cascade_leaf6_x._x6 on ONE target):
  tgt="min"   DIST60 exactly: the root virus with the smallest D (kdig), active while root vcount <= vk
  tgt="edge"  as "min", but restricted to EDGE-column viruses (cols 0 and 7) whenever one of them is LIVE (D < cap);
              otherwise the "min" target. Active while root vcount <= vk. (vk_min: the plain DIST60 gate still applies
              below vk_min, so tgt="edge" with vk=16, vk_min=4 = DIST60 at <= 4 plus edge targeting at 5..16.)

ROOT PENALTIES (pen[a] >= 0, subtracted after DRVETO with its 16-bit saturation; seal_steer9._choose_fw_seal, a
mechanical copy of braingap _choose_fw that is value-identical at pen == 0), all on the firmware's SOFT b1:
  rule "eseal" (family b, EDGE HYGIENE): pen = P x (number of EDGE-column viruses LIVE on the root and SEALED on b1(a),
              still viruses) -- cascade_leaf6_x._vdist(kdig 0) route predicate, as STEER9 SEALV but only columns 0/7.
              Gate: root vcount > vlo (vlo = 12: the OPENING / mid-game only; the endgame belongs to "edig").
  rule "edig" (family c, EDGE DIG): for every EDGE column whose top virus is SEALED on the ROOT board, pen = P x
              DC(b1(a), c), the vertical DIG COST of that column on b1(a):
                 cap = the non-virus cells above the column's top virus, parsed into same-colour runs from the top;
                 DC  = sum over runs NOT adjacent-and-matching the virus of (4 - min(L, 3)) + (3 - Lm), Lm = the length
                       of the run sitting directly on the virus when it has the virus's colour (else 0);
                 a column whose top virus is gone on b1(a) -> the same cost for its new top virus (0 if none).
              (A same-colour cell on the top run lowers DC by 1; a different colour adds a new run (+3); completing a
              run clears it.) Gate: root vcount <= vk_dig. cols = "edge" (0, 7) or "all".
  rule "ereach" (family d, from the mechanism check: EDGE REACH): the couch stalls are REACH losses -- an edge
              column holding viruses, or its neighbour, grows to height >= 13-15 (reach_fw_tap: vertical col 0 / 7 is
              unreachable from height 15 at pill 0, 14 at pill 50-100, 13 at 150+), and its viruses are out of the
              mask for the rest of the game. For each side (col 0 + col 1; col 7 + col 6) whose EDGE column holds a
              virus on the root, pen = P x max(0, max height of the side's 2 columns on b1(a) - h0). Penalises raising
              the side above h0 and, relatively, rewards clearing cells there (digging). Always on (no vcount gate).
Activity counters (rule 26): dec, fired (some allowed root carries pen > 0), changed (chosen != the no-penalty
argmax = what the target-only brain picks on the same board), tgt_edge (decisions where the edge target was used),
tgt_diff (decisions whose target differs from DIST60's min target at the same gate).
"""
from __future__ import annotations

import os
import sys

import numpy as np
from numba import njit, int8, int64

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, "..", "braingap"))
import import_pin  # noqa: E402
import_pin.pin()
from fast_sim_x import ROWS, COLS, NCELL  # noqa: E402
from cascade_link_x import board_flat  # noqa: E402
from cascade_leaf6_x import _vdist, _root_dists  # noqa: E402
from cascade_leaf6fw_braingap_20261003 import _soft_b1, Leaf6FwDecider  # noqa: E402
import seal_steer9 as S9  # noqa: E402

RCAP = 99
EDGE = (0, 7)


@njit(cache=True, fastmath=False)
def _edge_live(col, vir, out):
    """out[idx] = 1 LIVE edge virus, 0 SEALED edge virus, -1 otherwise (not a virus / not an edge column)."""
    top = np.empty(COLS, dtype=np.int64)
    for c in range(COLS):
        t = ROWS
        for r in range(ROWS):
            if col[r * COLS + c] != 0:
                t = r; break
        top[c] = t
    for idx in range(NCELL):
        c = idx % COLS
        if vir[idx] != 0 and (c == 0 or c == COLS - 1):
            out[idx] = 1 if _vdist(col, vir, top, idx // COLS, c, RCAP, 0) < RCAP else 0
        else:
            out[idx] = -1


@njit(cache=True, fastmath=False)
def _col_sealed_top(col, vir, c):
    """1 if column c's top virus is SEALED, 0 if LIVE, -1 if the column holds no virus."""
    top = np.empty(COLS, dtype=np.int64)
    for cc in range(COLS):
        t = ROWS
        for r in range(ROWS):
            if col[r * COLS + cc] != 0:
                t = r; break
        top[cc] = t
    for r in range(ROWS):
        if vir[r * COLS + c] != 0:
            return 0 if _vdist(col, vir, top, r, c, RCAP, 0) < RCAP else 1
    return -1


@njit(cache=True, fastmath=False)
def _dig_cost(col, vir, c):
    """vertical DIG COST of column c (module doc); 0 if the column holds no virus."""
    rv = -1
    for r in range(ROWS):
        if vir[r * COLS + c] != 0:
            rv = r; break
    if rv < 0:
        return 0
    vc = col[rv * COLS + c]
    r = 0
    while r < rv and col[r * COLS + c] == 0:
        r += 1
    cost = 0
    while r < rv:
        x = col[r * COLS + c]
        L = 0
        while r < rv and col[r * COLS + c] == x:
            L += 1; r += 1
        if r == rv and x == vc:                    # the run sits on the virus and matches it: part of its line
            m = L if L < 3 else 3
            return cost + 3 - m
        m = L if L < 3 else 3
        cost += 4 - m
    return cost + 3


@njit(cache=True, fastmath=False)
def _rule_pen(pcol, pvir, ca, cb, allowed, kind, P, cols_all, pen, nfire):
    """kind 1 = eseal, 2 = edig (module doc). pen[a] / nfire[a] per allowed legal root (nfire -1 = not evaluated)."""
    sbc = np.empty(NCELL, dtype=int8); sbv = np.empty(NCELL, dtype=int8)
    r0 = np.empty(NCELL, dtype=np.int64); r1 = np.empty(NCELL, dtype=np.int64)
    sealed = np.zeros(COLS, dtype=np.int64)
    if kind == 1:
        _edge_live(pcol, pvir, r0)
    else:
        for c in range(COLS):
            if cols_all == 0 and c != 0 and c != COLS - 1:
                continue
            sealed[c] = 1 if _col_sealed_top(pcol, pvir, c) == 1 else 0
    for a in range(32):
        pen[a] = 0; nfire[a] = -1
        if allowed[a] == 0:
            continue
        if _soft_b1(pcol, pvir, a // 8, a % 8, ca, cb, sbc, sbv) == 0:
            continue
        n = 0
        if kind == 1:
            _edge_live(sbc, sbv, r1)
            for idx in range(NCELL):
                if r0[idx] == 1 and r1[idx] == 0:
                    n += 1
        else:
            for c in range(COLS):
                if sealed[c]:
                    n += _dig_cost(sbc, sbv, c)
        nfire[a] = n
        pen[a] = int64(P) * n


@njit(cache=True, fastmath=False)
def _side_h(col, c0, c1):
    """max height of columns c0, c1"""
    h = 0
    for c in (c0, c1):
        for r in range(ROWS):
            if col[r * COLS + c] != 0:
                if ROWS - r > h:
                    h = ROWS - r
                break
    return h


@njit(cache=True, fastmath=False)
def _reach_pen(pcol, pvir, ca, cb, allowed, P, h0, pen, nfire):
    """kind 3 = ereach (family d, EDGE REACH): for each side (edge col 0 with its neighbour 1; edge col 7 with 6) whose
    EDGE column holds a virus on the ROOT board, n += max(0, max height of the side's two columns on b1(a) - h0)."""
    sbc = np.empty(NCELL, dtype=int8); sbv = np.empty(NCELL, dtype=int8)
    vl = 0; vr = 0
    for r in range(ROWS):
        if pvir[r * COLS] != 0:
            vl = 1
        if pvir[r * COLS + COLS - 1] != 0:
            vr = 1
    for a in range(32):
        pen[a] = 0; nfire[a] = -1
        if allowed[a] == 0:
            continue
        if _soft_b1(pcol, pvir, a // 8, a % 8, ca, cb, sbc, sbv) == 0:
            continue
        n = 0
        if vl:
            hl = _side_h(sbc, 0, 1)
            if hl > h0:
                n += hl - h0
        if vr:
            hr = _side_h(sbc, COLS - 2, COLS - 1)
            if hr > h0:
                n += hr - h0
        nfire[a] = n
        pen[a] = int64(P) * n


class S10Decider(Leaf6FwDecider):
    """Leaf6FwDecider (all fw switches) + STEER10 target / root rules. rule = dict(tgt, vk, vk_min, kdig, W,
    kind ('none'|'eseal'|'edig'), P, vlo, vk_dig, cols_all). Defaults == DIST60 exactly."""

    def __init__(self, weights, flags, rule=None, **kw):
        r = dict(tgt="min", vk=4, vk_min=4, kdig=0, W=60, kind="none", P=0, vlo=12, vk_dig=12, cols_all=0, h0=11)
        if rule:
            r.update(rule)
        self.rule = r
        kw = dict(kw)
        kw.update(mode="dist_target", W=int(r["W"]), vk=int(r["vk"]), kdig=int(r["kdig"]))
        super().__init__(weights, flags, **kw)
        self.pen = np.zeros(32, dtype=np.int64)
        self.nfire = np.full(32, -1, dtype=np.int64)
        self.act0 = np.full(1, -1, dtype=np.int64)
        self.stats = dict(dec=0, fired=0, changed=0, tgt_on=0, tgt_edge=0, tgt_diff=0)

    def w6_for(self, col, vir, cur, allowed, k):
        """dist_target with the STEER10 target choice (DIST60's own gate/argmin when tgt == 'min')."""
        r = self.rule
        w6 = np.zeros(6, dtype=np.int64); w6[1] = self.cap; w6[2] = -1; w6[5] = self.kdig
        nv = int(vir.sum())
        self.decisions += 1
        if nv > self.vk:
            self.stats["tgt_diff"] += 0 if nv > 4 else 1                       # (only if vk < 4: never used)
            return w6
        _root_dists(col, vir, self.cap, self._d, self.kdig)
        best = -1; beste = -1
        for i in range(NCELL):
            d = self._d[i]
            if d < 0:
                continue
            if best < 0 or d < self._d[best]:
                best = i
            c = i % COLS
            if (c == 0 or c == COLS - 1) and d < self.cap and (beste < 0 or d < self._d[beste]):
                beste = i
        tg = best
        if r["tgt"] == "edge" and beste >= 0:
            tg = beste
        elif r["tgt"] == "edge" and nv > int(r["vk_min"]):
            tg = -1                                   # no live edge virus above the DIST60 gate: term off
        if tg >= 0:
            w6[0] = self.W; w6[2] = tg
            self.active += 1
            self.stats["tgt_on"] += 1
            self.stats["tgt_edge"] += int(tg == beste and beste >= 0 and r["tgt"] == "edge")
        self.stats["tgt_diff"] += int(tg != (best if nv <= 4 else -1))        # vs DIST60's target on this board
        return w6

    def choose(self, board, cur, nxt, k=0):
        col, vir = board_flat(board)
        lnk = np.ascontiguousarray(board.link, dtype=np.int8).reshape(-1)
        allowed = self.mask(board, k) if self.mask_fn is None else self.mask_fn(board, k)
        w6 = self.w6_for(col, vir, cur, allowed, k)
        r = self.rule; s = self.sw
        nv = int(vir.sum())
        kind = {"none": 0, "eseal": 1, "edig": 2, "ereach": 3}[r["kind"]]
        on = (kind == 1 and nv > int(r["vlo"])) or (kind == 2 and nv <= int(r["vk_dig"])) or kind == 3
        if kind == 3 and int(r["P"]) != 0:
            _reach_pen(col, vir, cur.a, cur.b, allowed, int(r["P"]), int(r["h0"]), self.pen, self.nfire)
        elif kind and on and int(r["P"]) != 0:
            _rule_pen(col, vir, cur.a, cur.b, allowed, kind, int(r["P"]), int(r["cols_all"]), self.pen, self.nfire)
        else:
            self.pen[:] = 0; self.nfire[:] = -1
        a = S9._choose_fw_seal(col, vir, lnk, cur.a, cur.b, nxt.a, nxt.b, self.topk2, self.w_excav, self.w_hang,
                               self.w, self.fl, self.maxpass, self.w_chain, self.ws, allowed, self.w5, w6,
                               int(s["veto"]), int(s["hang"]), int(s["ehb1"]), int(s["ehnp"]), int(s["wrap"]),
                               int(s["order"]), self.vals, self.pen, 0, self.act0)
        self.stats["dec"] += 1
        fired = bool((self.pen > 0).any()) and int(self.pen.max()) != int(self.pen[self.nfire >= 0].min())
        self.stats["fired"] += int(fired)
        self.stats["changed"] += int(a >= 0 and int(self.act0[0]) != a)
        return None if a < 0 else int(a)


def make(rule=None):
    import fast_rtl_x as FX
    import cascade_chain_x as C
    C.warmup_chain(topk2=8)
    w, fl = FX.variant("winner")
    return S10Decider(w, fl, rule=rule, sw=None, topk2=8, maxpass=0, w_chain=540, ws=20, tap=2)


def base_decider():
    """the reference: braingap Leaf6FwDecider exactly as couch_forensics m4g2_fair_20261004.brain()"""
    import fast_rtl_x as FX
    import cascade_chain_x as C
    C.warmup_chain(topk2=8)
    w, fl = FX.variant("winner")
    return Leaf6FwDecider(w, fl, sw=None, topk2=8, maxpass=0, w_chain=540, ws=20, tap=2, mode="dist_target", W=60,
                          vk=4)
