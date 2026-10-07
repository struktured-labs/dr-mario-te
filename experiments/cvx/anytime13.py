"""STEER13 part B: the copro search's ANYTIME publish timeline on the SILICON-FAITHFUL brain (braingap Leaf6FwDecider).

The faithful brain's per-root values equal the py65 firmware's root V1 on every root of the 10/03 couch boards
(braingap VALIDATION: 0 of 2,580 / 3,990 roots mismatch) and it already evaluates roots in the firmware's Pass-0 order
(sw_order). So the firmware's live-publish SEQUENCE is reproducible exactly from the root values; only its TIMING needs
a model. `_choose_fw_meta` is `cascade_leaf6fw_braingap_20261003._choose_fw` VERBATIM plus outputs, per root in TODAY's
(Pass-0) order: action, value, d2 (the DRROOTORD depth-2 key: the val1 formula with best2 := the best ply-2 KEY, no
expectimax; test_search_d3 DRROOTORD pass B), and the work counters m2 (ply-2 leaves), kk2 (ply-2 children replayed),
n3 (ply-3 leaves = 4 x legal placements per non-winning replayed child).

Publish rules (test_search_d3 o_cand):
  fw 1488  roots in today's order; the running best is replaced on a STRICTLY greater value; each replacement is
           live-published when that root completes.
  V11      (V1 a1ef31c8 = 1488 + DRTUCKREACH + DRTUCKLIVE + DRROOTORD; + DRLEFLUSH, publish-identical without a
           preemption): pass B (the depth-2 pre-pass over every root, no publishes) then pass C, the deep pass in
           DESCENDING d2 (ties: the earlier today-rank first); replaced on a strictly greater value OR an equal value from
           an earlier today-rank (so the final argmax is today's).
Timing: frames after GO = T0 + a*n1 + sum over completed root work of (b + c*m2 + d*n3 + e*kk2) [pass B: b + c*m2 per
root]; coefficients fitted on the measured 1488 co-sim publish times (steer13_anytime_cal.py) and checked
out-of-sample on V1's.
Tucks are not modelled (the sim has none): co-sim boards whose timeline carries tuck publishes are excluded from fits.
"""
import os
import sys

import numpy as np
from numba import njit, int8, int32, int64, float64

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, "..", "braingap"))
import import_pin  # noqa: E402
import_pin.pin()
from fast_sim_x import NCELL, _virus_count, _stable_desc, _resting  # noqa: E402
from fast_rtl_x import _WIN_SHIP, _VAR_OF_O4, NBASE, NT, _base_scan, _g_excav_ship, _g_hang_ship  # noqa: E402
from cascade_link_x import board_flat  # noqa: E402
from cascade_stranded_x import _g_stranded47  # noqa: E402
from cascade_leaf6fw_braingap_20261003 import (_w16, _imm_w, _leaf_chain6w, _expected_third_w, _soft_b1, _hang_r4,  # noqa: E402
                                               _veto_plug, VETO_PENALTY)


@njit(cache=True)
def _legal_count(b):
    n = 0
    for o4 in range(4):
        var = _VAR_OF_O4[o4]
        for cl in range(8):
            ok, r0, c0, r1, c1 = _resting(b, var, cl)
            if ok != 0:
                n += 1
    return n


@njit(cache=True, fastmath=False)
def _choose_fw_meta(pcol, pvir, plnk, ca, cb, na, nb, topk2, w_excav, w_hang, w, fl, maxpass, w_chain, ws, allowed,
                    w5, w6, sw_veto, sw_hang, sw_ehb1, sw_ehnp, sw_wrap, sw_order, out_val,
                    o_act, o_val, o_d2, o_m2, o_kk2, o_n3, o_n):
    """_choose_fw verbatim + per-root (today's order index jj) outputs. o_n[0] = n1 (roots, = Pass-0 leaves)."""
    c1s = np.empty((32, NCELL), dtype=int8); v1s = np.empty((32, NCELL), dtype=int8); l1s = np.empty((32, NCELL), dtype=int8)
    acts = np.empty(32, dtype=np.int64); nvs = np.empty(32, dtype=np.int64); cellss = np.empty(32, dtype=np.int64)
    leaf1s = np.empty(32, dtype=np.int64); ch1s = np.empty(32, dtype=np.int64)
    keys1 = np.empty(32, dtype=float64); order1 = np.empty(32, dtype=int32)
    b2col = np.empty((32, NCELL), dtype=int8); b2vir = np.empty((32, NCELL), dtype=int8)
    b2lnk = np.empty((32, NCELL), dtype=int8)
    keys2 = np.empty(32, dtype=float64); imms2 = np.empty(32, dtype=int64); wins2 = np.empty(32, dtype=int64)
    order2 = np.empty(32, dtype=int32)
    s2c = np.empty(NCELL, dtype=int8); s2v = np.empty(NCELL, dtype=int8); s2l = np.empty(NCELL, dtype=int8)
    e2c = np.empty(NCELL, dtype=int8); e2v = np.empty(NCELL, dtype=int8); e2l = np.empty(NCELL, dtype=int8)
    tc = np.empty(NCELL, dtype=int8); tv = np.empty(NCELL, dtype=int8); tl = np.empty(NCELL, dtype=int8)
    mask = np.empty(NCELL, dtype=int8)
    sbc = np.empty(NCELL, dtype=int8); sbv = np.empty(NCELL, dtype=int8)
    c1 = np.empty(NCELL, dtype=int8); v1 = np.empty(NCELL, dtype=int8); l1 = np.empty(NCELL, dtype=int8)
    base1 = np.empty(NBASE, dtype=int64); base2 = np.empty(NBASE, dtype=int64)
    base3 = np.empty(NBASE, dtype=int64); terms = np.empty(NT, dtype=int64)
    for a in range(32):
        out_val[a] = -(int64(1) << 40)
    o_n[0] = 0
    _base_scan(pcol, pvir, fl, base1)
    virf = _virus_count(pvir) > 0
    n1 = 0
    for o4 in range(4):                                       # Pass 0 (enumeration order)
        var = _VAR_OF_O4[o4]
        for cl in range(8):
            if allowed[var * 8 + cl] == 0:
                continue
            ok, nv, cells, leaf1, ch1 = _leaf_chain6w(pcol, pvir, plnk, base1, var, cl, ca, cb, w, fl, c1, v1, l1,
                                                     mask, terms, maxpass, True, w5, w6, sw_wrap)
            if ok == 0:
                continue
            for i in range(NCELL):
                c1s[n1, i] = c1[i]; v1s[n1, i] = v1[i]; l1s[n1, i] = l1[i]
            acts[n1] = var * 8 + cl; nvs[n1] = nv; cellss[n1] = cells; leaf1s[n1] = leaf1; ch1s[n1] = ch1
            k1 = _imm_w(nv, cells, ch1, w_chain, sw_wrap) + leaf1
            keys1[n1] = float64(_w16(k1) if sw_wrap else k1)
            n1 += 1
    o_n[0] = n1
    if n1 == 0:
        return -1
    if sw_order:
        _stable_desc(keys1, n1, order1)
    else:
        for j in range(n1):
            order1[j] = j
    best_val = int64(0); best_act = -1; have = False
    for jj in range(n1):
        j = order1[jj]
        a = acts[j]; var = a // 8; cl = a % 8
        for i in range(NCELL):
            c1[i] = c1s[j, i]; v1[i] = v1s[j, i]; l1[i] = l1s[j, i]
        nv = nvs[j]; cells = cellss[j]; leaf1 = leaf1s[j]; ch1 = ch1s[j]
        imm1 = _imm_w(nv, cells, ch1, w_chain, sw_wrap)
        win1 = _virus_count(v1) == 0
        veto = sw_veto != 0 and (not win1) and cells == 0 and virf and _veto_plug(pcol, var, cl)
        m2 = 0; kk2 = 0; n3 = 0
        if win1:
            val = imm1 + int64(_WIN_SHIP)
            if sw_wrap:
                val = _w16(val)
            d2 = val
        else:
            # eh terms
            if sw_ehb1:
                _soft_b1(pcol, pvir, var, cl, ca, cb, sbc, sbv)
                ex = _g_excav_ship(sbc, sbv)
                hg = _hang_r4(sbc, sbv) if sw_hang else int64(w_hang) * _g_hang_ship(sbc, sbv)
            else:
                ex = _g_excav_ship(c1, v1)
                hg = _hang_r4(c1, v1) if sw_hang else int64(w_hang) * _g_hang_ship(c1, v1)
            eh = int64(w_excav) * ex + hg
            _base_scan(c1, v1, fl, base2)
            for o42 in range(4):
                var2 = _VAR_OF_O4[o42]
                for cl2 in range(8):
                    ok2, nv2, cells2, lv2, ch2 = _leaf_chain6w(c1, v1, l1, base2, var2, cl2, na, nb, w, fl,
                                                               s2c, s2v, s2l, mask, terms, maxpass, True, w5, w6,
                                                               sw_wrap)
                    if ok2 == 0:
                        continue
                    imm2 = _imm_w(nv2, cells2, ch2, w_chain, sw_wrap)
                    k2 = imm2 + lv2
                    keys2[m2] = float64(_w16(k2) if sw_wrap else k2)
                    imms2[m2] = imm2
                    for i in range(NCELL):
                        b2col[m2, i] = s2c[i]; b2vir[m2, i] = s2v[i]; b2lnk[m2, i] = s2l[i]
                    m2 += 1
            if m2 == 0:
                val = imm1 + leaf1
                if sw_wrap:
                    val = _w16(val)
                if sw_ehnp == 0:
                    val += eh
                d2 = val
            else:
                _stable_desc(keys2, m2, order2)
                b2k = int64(keys2[order2[0]])                   # DRROOTORD pass B: best ply-2 KEY, no expectimax
                if sw_wrap:
                    d2 = _w16(imm1 + leaf1 + (_w16(b2k - leaf1) >> int64(1)) + eh)
                else:
                    d2 = imm1 + leaf1 + ((b2k - leaf1) >> int64(1)) + eh
                kk2 = m2 if topk2 <= 0 or topk2 > m2 else topk2
                best2 = int64(0); have2 = False
                for s2 in range(kk2):
                    k2i = order2[s2]
                    for i in range(NCELL):
                        e2c[i] = b2col[k2i, i]; e2v[i] = b2vir[k2i, i]; e2l[i] = b2lnk[k2i, i]
                    if _virus_count(e2v) == 0:
                        v2 = imms2[k2i] + int64(_WIN_SHIP)
                    else:
                        n3 += 4 * _legal_count(e2c)
                        v2 = imms2[k2i] + _expected_third_w(e2c, e2v, e2l, w, fl, base3, terms, tc, tv, tl, mask,
                                                            maxpass, w_chain, w5, w6, sw_wrap)
                    if sw_wrap:
                        v2 = _w16(v2)
                    if not have2 or v2 > best2:
                        best2 = v2; have2 = True
                if sw_wrap:
                    val = _w16(imm1 + leaf1 + (_w16(best2 - leaf1) >> int64(1)) + eh)
                else:
                    val = imm1 + leaf1 + ((best2 - leaf1) >> int64(1)) + eh
        val -= int64(ws) * _g_stranded47(c1, v1)
        d2 -= int64(ws) * _g_stranded47(c1, v1)
        if sw_wrap:
            val = _w16(val)
            d2 = _w16(d2)
        if veto:
            t = val - VETO_PENALTY
            val = t if t >= -32768 else int64(-32767)
            t = d2 - VETO_PENALTY
            d2 = t if t >= -32768 else int64(-32767)
        out_val[a] = val
        o_act[jj] = a; o_val[jj] = val; o_d2[jj] = d2; o_m2[jj] = m2; o_kk2[jj] = kk2; o_n3[jj] = n3
        if not have or val > best_val:
            best_val = val; best_act = a; have = True
    return best_act


class Meta:
    """per-decision buffers + the search call on a Leaf6FwDecider's own state (mask, w6, weights, switches)"""

    def __init__(self):
        self.vals = np.empty(32, np.int64)
        self.act = np.empty(32, np.int64); self.val = np.empty(32, np.int64); self.d2 = np.empty(32, np.int64)
        self.m2 = np.empty(32, np.int64); self.kk2 = np.empty(32, np.int64); self.n3 = np.empty(32, np.int64)
        self.n = np.zeros(1, np.int64)

    def run(self, dec, board, cur, nxt, k, allowed=None):
        col, vir = board_flat(board)
        lnk = np.ascontiguousarray(board.link, dtype=np.int8).reshape(-1)
        if allowed is None:
            allowed = dec.mask(board, k) if dec.mask_fn is None else dec.mask_fn(board, k)
        w6 = dec.w6_for(col, vir, cur, allowed, k)
        s = dec.sw
        a = _choose_fw_meta(col, vir, lnk, cur.a, cur.b, nxt.a, nxt.b, dec.topk2, dec.w_excav, dec.w_hang, dec.w,
                            dec.fl, dec.maxpass, dec.w_chain, dec.ws, allowed, dec.w5, w6, int(s["veto"]),
                            int(s["hang"]), int(s["ehb1"]), int(s["ehnp"]), int(s["wrap"]), int(s["order"]),
                            self.vals, self.act, self.val, self.d2, self.m2, self.kk2, self.n3, self.n)
        n1 = int(self.n[0])
        roots = [(int(self.act[j]), int(self.val[j]), int(self.d2[j]), int(self.m2[j]), int(self.kk2[j]),
                  int(self.n3[j])) for j in range(n1)]
        return (None if a < 0 else int(a)), roots


# --------------------------------------------------------------------------------------------- publish timelines
def publishes(roots, fw, coef):
    """[(t_frames_after_GO, action)] in time order; the last action is the final answer. coef = dict(T0, a, b, c, d, e).
    roots = Meta.run's list in TODAY's order: (act, val, d2, m2, kk2, n3)."""
    n1 = len(roots)
    if n1 == 0:
        return []
    t = coef["T0"] + coef["a"] * n1
    deep = lambda r: coef["b"] + coef["c"] * r[3] + coef["d"] * r[5] + coef["e"] * r[4]
    pubs = []
    if fw == "1488":
        best = None
        for r in roots:
            t += deep(r)
            if best is None or r[1] > best:
                best = r[1]; pubs.append((t, r[0]))
        return pubs
    assert fw == "v11"
    for r in roots:                                           # pass B: the depth-2 pre-pass, no publishes
        t += coef["b"] + coef["c"] * r[3]
    order = sorted(range(n1), key=lambda j: (-roots[j][2], j))  # descending d2, ties: earlier today-rank first
    best = None; bj = None
    for j in order:
        r = roots[j]
        t += deep(r)
        if best is None or r[1] > best or (r[1] == best and j < bj):
            best = r[1]; bj = j; pubs.append((t, r[0]))
    return pubs


def mailbox(pubs, t):
    """the published action at time t (frames after GO), None before the first publish"""
    m = None
    for tp, a in pubs:
        if tp <= t:
            m = a
        else:
            break
    return m
