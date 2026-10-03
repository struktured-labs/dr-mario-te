"""STEER7 desk analysis: the copro search's ANYTIME trajectory on real boards (no builds, no silicon).

The firmware (tests/test_search_d3.py, engine build) runs:
  Pass 0   every allowed legal root candidate, key = imm1 + score1, into TK1
  select   roots in DESCENDING Pass-0 key (repeated max; the first max in TK1 order wins ties); for each root:
           replay ply-1 (NODE); ply-2 rank over every legal next-pill placement (CMD 6 base + CMD 7 deltas);
           for the top-8 ply-2 children: replay (NODE) + expectimax over 4 third-pill classes x every legal placement
  o_cand   val1 vs running best (strictly greater replaces) -> LIVE-PUBLISH the running best to the mailbox
This tool replays that order with the golden leaf/val functions of cascade_leaf6_x (the s6_dist_target60 brain) and
counts the leaf evaluations each root costs, so every publish gets a TIME (leaves -> clocks -> frames after GO).
It reports: total leaves by ply, first publish, the time the FINAL answer is first published (stabilisation), the
number of publishes, and P(running best == final answer) at fixed times after GO (the driver's MIN_THINK gate is
25 hooks = 12.5 f after GO at 2 hooks/frame).

Identity: the trajectory's final argmax must equal Leaf6Decider.choose on every board (ties aside; counted).

  python steer7_anytime.py N_SEEDS OUT.jsonl
"""
import sys, os, json
from types import SimpleNamespace
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import import_pin; import_pin.pin()
import numpy as np
from numba import njit, int8, int32, int64, float64
from fast_sim_x import NCELL, _virus_count, _stable_desc, _resting
from fast_rtl_x import _WIN_SHIP, _VAR_OF_O4, NBASE, NT, _base_scan, _g_excav_ship, _g_hang_ship
from cascade_link_x import board_flat
from cascade_chain_x import _imm_chain
from cascade_stranded_x import _g_stranded47
from cascade_shape_x import _shape_terms
from cascade_leaf6_x import _leaf_chain6, _expected_third_chain6

CLK_PER_LEAF = 1849.0                     # STEER6c calibration: 69-board co-sim median 48.3M clocks / 26,129 leaves
FRAME_CLK = 85.909e6 / 60.0988            # MiSTer copro clocks per NES frame


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


@njit(cache=True)
def trajectory(pcol, pvir, plnk, ca, cb, na, nb, topk2, w_excav, w_hang, w, fl, maxpass, w_chain, ws, allowed,
               w_sv, r_hi, w_sp, hs, w5, w6, out_act, out_val, out_leaves, out_ply, out_d2, out_m2):
    """Fills, in FIRMWARE processing order: out_act[i], out_val[i], out_leaves[i] (leaves this root cost).
    out_ply = [pass0 leaves, ply2 leaves, ply3 leaves]. out_d2[i] = a DEPTH-2 estimate of the root's value (best ply-2
    key in place of the expectimax: a candidate cheap ordering key), out_m2[i] = its ply-2 leaf count. Returns n roots."""
    c1 = np.empty(NCELL, dtype=int8); v1 = np.empty(NCELL, dtype=int8); l1 = np.empty(NCELL, dtype=int8)
    b2col = np.empty((32, NCELL), dtype=int8); b2vir = np.empty((32, NCELL), dtype=int8)
    b2lnk = np.empty((32, NCELL), dtype=int8)
    keys2 = np.empty(32, dtype=float64); imms2 = np.empty(32, dtype=int64); order2 = np.empty(32, dtype=int32)
    s2c = np.empty(NCELL, dtype=int8); s2v = np.empty(NCELL, dtype=int8); s2l = np.empty(NCELL, dtype=int8)
    e2c = np.empty(NCELL, dtype=int8); e2v = np.empty(NCELL, dtype=int8); e2l = np.empty(NCELL, dtype=int8)
    tc = np.empty(NCELL, dtype=int8); tv = np.empty(NCELL, dtype=int8); tl = np.empty(NCELL, dtype=int8)
    mask = np.empty(NCELL, dtype=int8)
    base1 = np.empty(NBASE, dtype=int64); base2 = np.empty(NBASE, dtype=int64)
    base3 = np.empty(NBASE, dtype=int64); terms = np.empty(NT, dtype=int64)
    _base_scan(pcol, pvir, fl, base1)
    # ---- Pass 0: keys for every allowed legal root
    acts = np.empty(32, dtype=int64); keys1 = np.empty(32, dtype=float64); order1 = np.empty(32, dtype=int32)
    n1 = 0
    for o4 in range(4):
        var = _VAR_OF_O4[o4]
        for cl in range(8):
            if allowed[var * 8 + cl] == 0:
                continue
            ok, nv, cells, leaf1, ch1 = _leaf_chain6(pcol, pvir, plnk, base1, var, cl, ca, cb, w, fl, c1, v1, l1, mask,
                                                    terms, maxpass, True, w5, w6)
            if ok == 0:
                continue
            imm1 = _imm_chain(nv, cells, ch1, w, w_chain)
            sc = int64(_WIN_SHIP) if _virus_count(v1) == 0 else leaf1
            acts[n1] = var * 8 + cl; keys1[n1] = float64(imm1 + sc); n1 += 1
    out_ply[0] = n1; out_ply[1] = 0; out_ply[2] = 0
    if n1 == 0:
        return 0
    _stable_desc(keys1, n1, order1)                       # descending, ties keep TK1 (enumeration) order
    for j in range(n1):
        a = acts[order1[j]]; var = a // 8; cl = a % 8
        ok, nv, cells, leaf1, ch1 = _leaf_chain6(pcol, pvir, plnk, base1, var, cl, ca, cb, w, fl, c1, v1, l1, mask,
                                                terms, maxpass, True, w5, w6)
        imm1 = _imm_chain(nv, cells, ch1, w, w_chain)
        lv = 1                                            # replay ply-1 (NODE)
        d2 = int64(0); m2 = 0
        if _virus_count(v1) == 0:
            val = imm1 + int64(_WIN_SHIP); d2 = val
        else:
            _base_scan(c1, v1, fl, base2)
            m2 = 0
            for o42 in range(4):
                var2 = _VAR_OF_O4[o42]
                for cl2 in range(8):
                    ok2, nv2, cells2, lv2, ch2 = _leaf_chain6(c1, v1, l1, base2, var2, cl2, na, nb, w, fl,
                                                             s2c, s2v, s2l, mask, terms, maxpass, True, w5, w6)
                    if ok2 == 0:
                        continue
                    imm2 = _imm_chain(nv2, cells2, ch2, w, w_chain)
                    keys2[m2] = float64(imm2 + lv2); imms2[m2] = imm2
                    for i in range(NCELL):
                        b2col[m2, i] = s2c[i]; b2vir[m2, i] = s2v[i]; b2lnk[m2, i] = s2l[i]
                    m2 += 1
            lv += m2; out_ply[1] += m2
            if m2 == 0:
                val = imm1 + leaf1; d2 = val
                lv += 1
            else:
                _stable_desc(keys2, m2, order2)
                d2 = imm1 + leaf1 + ((int64(keys2[order2[0]]) - leaf1) >> int64(1))
                kk2 = m2 if topk2 <= 0 or topk2 > m2 else topk2
                best2 = int64(0); have2 = False
                for s2 in range(kk2):
                    k2 = order2[s2]
                    for i in range(NCELL):
                        e2c[i] = b2col[k2, i]; e2v[i] = b2vir[k2, i]; e2l[i] = b2lnk[k2, i]
                    lv += 1                               # replay ply-2 (NODE)
                    if _virus_count(e2v) == 0:
                        v2 = imms2[k2] + int64(_WIN_SHIP)
                    else:
                        n3 = 4 * _legal_count(e2c)
                        lv += n3; out_ply[2] += n3
                        v2 = imms2[k2] + _expected_third_chain6(e2c, e2v, e2l, w, fl, base3, terms, tc, tv, tl, mask,
                                                                maxpass, w_chain, w5, w6)
                    if not have2 or v2 > best2:
                        best2 = v2; have2 = True
                val = imm1 + leaf1 + ((best2 - leaf1) >> int64(1))
            val += w_excav * _g_excav_ship(c1, v1) + w_hang * _g_hang_ship(c1, v1)
            d2 += w_excav * _g_excav_ship(c1, v1) + w_hang * _g_hang_ship(c1, v1)
        extra = -ws * _g_stranded47(c1, v1) + _shape_terms(pcol, var, cl, nv, cells, w_sv, r_hi, w_sp, hs)
        val += extra; d2 += extra
        out_act[j] = a; out_val[j] = val; out_leaves[j] = lv; out_d2[j] = d2; out_m2[j] = m2
    return n1


def summarise(n1, act, val, leaves, ply, d2=None, m2=None):
    """Publishes in time order: the running best changes when val is STRICTLY greater (o_cand's BPL skip)."""
    pubs = []; best = None; cum = ply[0]
    for j in range(n1):
        cum += leaves[j]
        if best is None or val[j] > best:
            best = val[j]; pubs.append((int(cum), int(act[j])))
    final = pubs[-1][1]
    stab = next(t for t, a in pubs if a == final)
    extra = {}
    if d2 is not None:
        extra = {"roots_act": [int(x) for x in act[:n1]], "roots_val": [int(x) for x in val[:n1]],
                 "roots_leaves": [int(x) for x in leaves[:n1]], "roots_d2": [int(x) for x in d2[:n1]],
                 "roots_m2": [int(x) for x in m2[:n1]]}
    return {**extra, "total": int(cum), "pass0": int(ply[0]), "ply2": int(ply[1]), "ply3": int(ply[2]), "roots": int(n1),
            "first_pub": pubs[0][0], "stab": stab, "npub": len(pubs), "final": final, "pubs": pubs,
            "final_rank": int(next(j for j in range(n1) if act[j] == final))}


def collect(n_seeds, lo=36734):
    import stuck_probe as SP, steer_run as SR, opp_run as OR
    out = []
    for i in range(n_seeds):
        steer, choose = SR.make("s6_dist_target60"); opp = OR.make_opponent("owner0804")
        dec = choose.__closure__[0].cell_contents if choose.__closure__ else None

        def ch(env, col, vir, ctx, choose=choose, dec=dec):
            out.append((dec, env.board.clone(), SimpleNamespace(a=int(env.cur.a), b=int(env.cur.b)),
                        SimpleNamespace(a=int(env.nxt.a), b=int(env.nxt.b)), int(env.pills_placed)))
            return choose(env, col, vir, ctx)
        SP.play_gb(lo + 2 * i, ch, steer, opp)
    return out


if __name__ == "__main__":
    n_seeds, outp = int(sys.argv[1]), sys.argv[2]
    boards = collect(n_seeds)
    act = np.empty(32, np.int64); val = np.empty(32, np.int64); lvs = np.empty(32, np.int64); ply = np.empty(3, np.int64)
    d2 = np.empty(32, np.int64); m2 = np.empty(32, np.int64)
    same = diff = 0
    with open(outp, "w") as fh:
        for dec, b, cur, nxt, k in boards:
            col, vir = board_flat(b)
            lnk = np.ascontiguousarray(b.link, dtype=np.int8).reshape(-1)
            allowed = dec.mask(b, k)
            w6 = dec.w6_for(col, vir, cur, allowed, k)
            n1 = trajectory(col, vir, lnk, cur.a, cur.b, nxt.a, nxt.b, dec.topk2, dec.w_excav, dec.w_hang, dec.w, dec.fl,
                            dec.maxpass, dec.w_chain, dec.ws, allowed, dec.w_sv, dec.r_hi, dec.w_sp, dec.hs, dec.w5, w6,
                            act, val, lvs, ply, d2, m2)
            if n1 == 0:
                continue
            s = summarise(n1, act, val, lvs, ply, d2, m2)
            ref = dec.choose(b, cur, nxt, k)
            same += int(ref == s["final"]); diff += int(ref != s["final"])
            s.update(k=k, nv=int(vir.sum()), ref=ref, dist_active=int(w6[0] != 0))
            fh.write(json.dumps(s) + "\n")
    print(f"boards {same + diff}: final == Leaf6Decider.choose on {same}, differ {diff}")
