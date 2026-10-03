#!/usr/bin/env python3
"""SWITCHABLE MIRROR of the depth-3 root search: one pure-python loop that is EITHER the sim brain
(cascade_leaf6_x._choose_d3_chain_s_leaf6, Leaf6Decider dist_target60 on ANTIBODY) OR the shipped firmware search
(test_search_d3._emit_search_d3_engine + _emit_expectimax_engine at the fw 1488e158 recipe), feature by feature.
Every node is the sim's own RTL-gated numba node (rtlengine_braingap_20261003.node, the engine py65 runs against).

Switches (python value -> firmware value):
  veto    0 -> 1   DRVETO (a+) spawn-plug veto: -20000 (16-bit saturating) at o_cand on a non-clearing, non-winning
                   root that plugs (0,3)/(0,4) while the root has viruses (test_search_d3.veto_plug)
  hang    0 -> 1   eh hang credit: base g_hang * 40 (fast_rtl_x._g_hang_ship) -> R4: credit 40 + 20*gap, only in
                   columns holding a virus (eh_hcredit)
  ehb1    0 -> 1   board the eh terms scan: the link-aware fixpoint child c1 -> the SOFT b1 (LIVE + land_place +
                   resolve_capped: targeted cap-1 clear + ONE compact gravity, test_resolve.py_gravity)
  ehnp    0 -> 1   eh on the no-legal-ply-2 path: added -> skipped (that path JMPs to o_cand)
  wrap    0 -> 1   arithmetic: int64 with the HSV/DIST extras added after the base leaf's wrap -> signed-16
                   everywhere the 6502 / LeafEval do it (sco incl. extras, imm, K keys, V3, E, B2-L1, V1)
  order   0 -> 1   root evaluation order (= tie-break): enumeration (o4, col) -> Pass-0 key K descending (first max)
  mask             the root mask: given by the caller (python Leaf6Decider mask or the firmware reach mask)
choose(..., sw) returns the action (var*8+col) and per-root components {imm1, leaf1, best2, ad, strand, veto, v1}.
"""
from __future__ import annotations

import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import rtlengine_braingap_20261003 as E  # noqa: E402  (pins the h16 sim modules + the te firmware tree)
from rtlengine_braingap_20261003 import dec, wrap16, w6_of, node, leaf_of, VAR_OF_O4  # noqa: E402
from fast_rtl_x import _g_excav_ship, _g_hang_ship  # noqa: E402
from cascade_stranded_x import _g_stranded47  # noqa: E402
import test_search_d3 as D3  # noqa: E402

WIN = 30000
THIRD = [(0, 1), (1, 2), (2, 0), (1, 1)]
FW = dict(veto=1, hang=1, ehb1=1, ehnp=1, wrap=1, order=1)
PY = dict(veto=0, hang=0, ehb1=0, ehnp=0, wrap=0, order=0)


def s16(x, on):
    return wrap16(x) if on else int(x)


# ------------------------------------------------------------------------------------------- soft b1 + eh terms
def _first_occ(b, c):
    for r in range(16):
        if b[r * 8 + c] != 0xFF:
            return r
    return 16


def _soft_land(b, o4, col):
    if o4 < 2:
        fo = _first_occ(b, col)
        if fo < 2:
            return None
        offb = (fo - 1) * 8 + col
        return offb - 8, offb
    if col + 1 >= 8:
        return None
    fo = min(_first_occ(b, col), _first_occ(b, col + 1))
    if fo < 1:
        return None
    offa = (fo - 1) * 8 + col
    return offa, offa + 1


def _soft_gravity(b):
    for c in range(8):
        dest = 15
        for read in range(15, -1, -1):
            off = read * 8 + c; t = b[off]
            if t == 0xFF:
                continue
            if (t & 0xF0) == 0xD0:
                dest = read - 1
            else:
                doff = dest * 8 + c
                if doff != off:
                    b[doff] = t; b[off] = 0xFF
                dest -= 1


def _cap1_targeted(b, offa, offb):
    mark = set()
    for off, step, cnt in ((offa & 0xF8, 1, 8), (offa & 0x07, 8, 16), (offb & 0xF8, 1, 8), (offb & 0x07, 8, 16)):
        run = 0; rstart = off; mcol = None; o = off
        for _ in range(cnt):
            x = b[o]
            if x == 0xFF:
                if run >= 4:
                    mark.update(rstart + k * step for k in range(run))
                run = 0; mcol = None
            elif (x & 0x0F) != mcol:
                if run >= 4:
                    mark.update(rstart + k * step for k in range(run))
                mcol = x & 0x0F; rstart = o; run = 1
            else:
                run += 1
            o += step
        if run >= 4:
            mark.update(rstart + k * step for k in range(run))
    for k in mark:
        b[k] = 0xFF
    if mark:
        _soft_gravity(b)


def soft_b1(root_nes, o4, col, ca, cb):
    land = _soft_land(root_nes, o4, col)
    if land is None:
        return None
    offa, offb = land
    ta, tb = (cb, ca) if (o4 & 1) else (ca, cb)
    b = list(root_nes)
    b[offa] = 0x40 | ta; b[offb] = 0x40 | tb
    _cap1_targeted(b, offa, offb)
    return b


def g_excav_nes(b):
    tot = 0
    for c in range(8):
        r = 0
        while r < 16 and b[r * 8 + c] == 0xFF:
            r += 1
        if r >= 16:
            continue
        vr = None
        for rr in range(r + 1, 16):
            x = b[rr * 8 + c]
            if x != 0xFF and (x & 0xF0) == 0xD0:
                vr = rr; break
        if vr is None or (b[r * 8 + c] & 0xF0) == 0xD0:
            continue
        top = b[r * 8 + c] & 0x0F; run = 1; rr = r + 1
        while rr < vr and b[rr * 8 + c] != 0xFF and (b[rr * 8 + c] & 0x0F) == top:
            run += 1; rr += 1
        tot += min(run, 3) ** 2
    return tot


def hang_credit_nes(b, r4):
    """r4=0: base g_hang * 40; r4=1: firmware eh_hcredit (virus column only, 40 + 20 * gap)."""
    tot = 0
    for idx in range(120):
        x = b[idx]
        if x == 0xFF or (x & 0xF0) == 0xD0 or b[idx + 8] != 0xFF:
            continue
        y = idx + 16
        while y < 128 and b[y] == 0xFF:
            y += 8
        if y >= 128 or (b[y] & 0x0F) != (x & 0x0F):
            continue
        if not r4:
            tot += 40; continue
        c = idx & 7
        if not any(b[q] != 0xFF and (b[q] & 0xF0) == 0xD0 for q in range(c, 128, 8)):
            continue
        gap = ((y - idx) >> 3) - 1
        tot += 40 + 20 * gap
    return tot


def eh_terms(root_nes, o4, col, ca, cb, c1_nes, sw):
    if sw["ehb1"]:
        b = soft_b1(root_nes, o4, col, ca, cb)
    else:
        b = c1_nes
    return 24 * g_excav_nes(b) + hang_credit_nes(b, sw["hang"])


# ------------------------------------------------------------------------------------------------ the search
from fast_sim_x import _virus_count  # noqa: E402
from fast_rtl_x import _leafv_ship  # noqa: E402
from cascade_chain_x import _expand_chain  # noqa: E402
from cascade_leaf5b_x import _x5  # noqa: E402
from cascade_leaf6_x import _x6  # noqa: E402
_MASK = np.empty(128, np.int8)


def _score(sco, win):
    return WIN if win else sco


def _leafv(col, vir, w6, wrap):
    """-> (sco, win). wrap=1: the engine's sco (base + HSV + DIST wrapped together, LeafEval);
    wrap=0: the python sim's value (base wrapped, extras added in int64)."""
    if _virus_count(vir) == 0:
        return 0, 1
    v = int(_leafv_ship(col, vir, E.W_LEAF, E.FL_LEAF)) + int(_x5(col, vir, E.FL_LEAF, E.W5)) + int(_x6(col, vir, w6))
    return (wrap16(v) if wrap else v), 0


def _node(p, o4, col, ca, cb, w6, wrap):
    pcol, pvir, plnk = p
    ccol = np.empty(128, np.int8); cvir = np.empty(128, np.int8); clnk = np.empty(128, np.int8)
    ok, nv, cells, ch = _expand_chain(pcol, pvir, plnk, VAR_OF_O4[o4], col, ca + 1, cb + 1, ccol, cvir, clnk,
                                      _MASK, 0)
    if ok == 0:
        return None
    nv = int(nv); cells = int(cells); ch = int(ch)
    if wrap:
        ch = min(ch, 15)
        imm = (180 * nv + 10 * cells + (540 * (ch - 1) if ch > 1 else 0)) & 0xFFFF
    else:
        imm = 180 * nv + 10 * cells + (540 * (ch - 1) if ch > 1 else 0)
    sco, win = _leafv(ccol, cvir, w6, wrap)
    return dict(cells=cells, nv=nv, imm=imm, sco=sco, win=win, child=(ccol, cvir, clnk), ch=ch)


def expectimax(b2, w6, wrap):
    tot = 0
    for (x, y) in THIRD:
        best = None
        for o4 in range(4):
            for c in range(8):
                n = _node(b2, o4, c, x, y, w6, wrap)
                if n is None:
                    continue
                v3 = s16(n["imm"] + _score(n["sco"], n["win"]), wrap)
                if best is None or v3 > best:
                    best = v3
        if best is None:
            sco, win = _leafv(b2[0], b2[1], w6, wrap)
            best = _score(sco, win)
        tot += best
    return tot >> 2 if wrap else tot // 4


def choose(root_nes, ca, cb, na, nb, mask_o4, sw, tgt=0, topk2=8):
    """root_nes: 128 NES bytes; ca..nb: 0-based colours; mask_o4[o4*8+col] (1 = allowed; None = all).
    Returns (action var*8+col or None, roots[list of dicts in evaluation order])."""
    w6 = w6_of(tgt)
    wrap = sw["wrap"]
    root = dec(root_nes)
    virf = any(x != 0xFF and (x & 0xF0) == 0xD0 for x in root_nes)
    cands = []
    for o4 in range(4):
        for col in range(8):
            if mask_o4 is not None and not mask_o4[o4 * 8 + col]:
                continue
            n = _node(root, o4, col, ca, cb, w6, wrap)
            if n is None:
                continue
            k = s16(n["imm"] + _score(n["sco"], n["win"]), wrap)
            cands.append((o4, col, k, n))
    if sw["order"]:
        cands = sorted(cands, key=lambda t: -t[2])          # stable: ties keep enumeration order (first max)
    best = None; best_v = None; roots = []
    for (o4, col, k, n) in cands:
        i1 = n["imm"]; l1 = n["sco"]; c1 = n["child"]
        strand = int(_g_stranded47(c1[0], c1[1]))
        veto = int(bool(sw["veto"] and not n["win"] and n["cells"] == 0 and virf
                        and D3.veto_plug(root_nes, o4, col)))
        ad = 0; b2v = None
        if n["win"]:
            v1 = s16(i1 + WIN, wrap)
        else:
            second = []
            for o42 in range(4):
                for c2 in range(8):
                    m = _node(c1, o42, c2, na, nb, w6, wrap)
                    if m is None:
                        continue
                    second.append((s16(m["imm"] + _score(m["sco"], m["win"]), wrap), m))
            if not second:
                v1 = s16(i1 + _score(l1, 0), wrap)
                if not sw["ehnp"]:
                    ad = eh_terms(root_nes, o4, col, ca, cb, E.enc(*c1), sw)
                    v1 += ad
            else:
                second.sort(key=lambda t: -t[0])
                for (_k2, m) in second[:topk2]:
                    if m["win"]:
                        v3 = s16(m["imm"] + WIN, wrap)
                    else:
                        v3 = s16(m["imm"] + expectimax(m["child"], w6, wrap), wrap)
                    if b2v is None or v3 > b2v:
                        b2v = v3
                ad = eh_terms(root_nes, o4, col, ca, cb, None if sw["ehb1"] else E.enc(*c1), sw)
                if wrap:
                    v1 = wrap16(i1 + l1 + (wrap16(b2v - l1) >> 1) + ad)
                else:
                    v1 = i1 + l1 + ((b2v - l1) >> 1) + ad
        v1 = s16(v1 - 20 * strand, wrap)
        if veto:
            t = v1 - 20000
            v1 = t if t >= -32768 else -32767
        roots.append(dict(o4=o4, col=col, k=k, imm1=i1, leaf1=l1, best2=b2v, ad=ad, strand=strand, veto=veto,
                          v1=v1, win=n["win"], cells=n["cells"], nv=n["nv"]))
        if best_v is None or v1 > best_v:
            best_v = v1; best = (o4, col)
    if best is None:
        return None, roots
    o4, col = best
    return VAR_OF_O4[o4] * 8 + col, roots
