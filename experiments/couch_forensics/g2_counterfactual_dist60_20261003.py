"""10/03 G2 counterfactuals on cases_g2_dist60_20261003.jsonl.

(1) BRAIN-ONLY REPLAY: from pill P0, the sim brain (Leaf6Decider dist_target60 == ANTIBODY above 4 viruses, reach
    mask at the true pill index) places every pill by straight drop, with the OBSERVED capsule sequence and the
    OBSERVED garbage (surviving garbage cells of each received volley, dropped onto that column's top after the same
    pill). Reports top-out / viruses / heights at every observed pill. Execution is perfect, so the difference vs
    silicon = execution + its downstream effects.
(2) TOWER DECOMPOSITION: every decision where the SIM brain's own choice raises max(h4, h5) to >= 11: chosen vs the
    best allowed move that does not raise max(h3, h4, h5), PV term split (decomp_dist60_20261003).
(3) LATE-FLIP probe: for each silicon LATE-FLIP, does the flipped final pose equal the sim brain's choice under a
    plausible wrong input? (a) the PREVIEW pill searched instead of the live one (spawn-edge mix-up); (b) the live
    capsule's pre-flip cells baked into the board; (c) cur/nxt swapped.
Usage: python g2_counterfactual_dist60_20261003.py [P0 ...]
"""
from __future__ import annotations

import json
import sys

import numpy as np

import analyze_g2 as A
import decomp_dist60_20261003 as DC
import fast_rtl_x as FX
import cascade_chain_x as C
from cascade_leaf6_x import Leaf6Decider
from drmario.faithful_game import Pill
from endgame_dist60_20261003 import after, pose_of, summ

CASES = "cases_g2_dist60_20261003.jsonl"
RAW = "rawh_dist60_20261003_G2.jsonl"
NAMES = DC.NAMES


def heights(b):
    return [int(16 - np.argmax(b.color[:, c] > 0)) if (b.color[:, c] > 0).any() else 0 for c in range(8)]


def garbage_cells(Q, i):
    """surviving garbage cells (col, colour) received after placement i: S_{i+1} cells not in (S_i + landing)."""
    import mech_check as MC
    if i + 1 >= len(Q) or not Q[i]["garbage_recv"]:
        return []
    r = {"S": Q[i]["S"], "landing": [Q[i]["actual"][0], Q[i]["actual"][3], Q[i]["actual"][1], Q[i]["actual"][2]]}
    P = MC.after_pill(r)
    N = np.array([int(ch) for ch in Q[i + 1]["S"]["color"]]).reshape(16, 8)
    return [(int(c), int(N[rr, c])) for rr, c in sorted(np.argwhere((N > 0) & (P.color == 0)).tolist(), key=lambda x: -x[0])]


def drop(b, cells):
    for c, col in cells:
        top = next((r for r in range(16) if b.color[r, c] > 0), 16)
        if top == 0:
            return False
        b.color[top - 1, c] = col; b.link[top - 1, c] = 0; b.is_virus[top - 1, c] = False
    b.resolve()
    return True


def replay(Q, dec, i0):
    b = A.board_from_strings(Q[i0]["S"]["color"], Q[i0]["S"]["virus"], Q[i0]["S"]["link"])
    out = []
    for i in range(i0, len(Q)):
        q = Q[i]
        if b.spawn_blocked():
            out.append((q["p"], "TOPOUT", b.virus_count(), heights(b))); break
        a = dec.choose(b.clone(), Pill(*q["cur"]), Pill(*q["nxt"]), q["p"])
        if a is None:
            out.append((q["p"], "NOMOVE", b.virus_count(), heights(b))); break
        bb, st = after(b, pose_of(a, tuple(q["cur"]), b))
        b = bb
        if b.virus_count() == 0:
            out.append((q["p"], "CLEAR", 0, heights(b))); break
        if not drop(b, garbage_cells(Q, i)) or b.spawn_blocked():
            out.append((q["p"], "TOPOUT", b.virus_count(), heights(b))); break
        out.append((q["p"], "ok", b.virus_count(), heights(b)))
    return out


def main(p0s):
    C.warmup_chain(topk2=8)
    w, fl = FX.variant("winner")
    kw = dict(topk2=8, maxpass=0, w_chain=540, ws=20, tap=2)
    dec = Leaf6Decider(w, fl, mode="dist_target", W=60, vk=4, **kw)
    dd = DC.DecompDecider(w, fl, mode="dist_target", W=60, vk=4, **kw)
    Q = [json.loads(l) for l in open(CASES)]
    idx = {q["p"]: i for i, q in enumerate(Q)}
    print("=== (1) brain-only replay (observed capsules + observed garbage, perfect execution) ===")
    sil = {q["p"]: (q["virus_count"], q["heights"]) for q in Q}
    for p0 in p0s:
        R = replay(Q, dec, idx[p0])
        last = R[-1]
        print(f"from p{p0}: {len(R)} pills -> end {last[1]} at p{last[0]} viruses {last[2]} heights {last[3]}")
        for (p, st, v, h) in R:
            if p % 10 == 0 or st != "ok" or p in (96, 100, 104, 110, 114):
                s = sil.get(p + 1)
                print(f"    p{p:3d} {st:6s} vir {v:2d} h {h} max {max(h)} | silicon next board: vir {s[0] if s else '-'} h {s[1] if s else '-'}")
    print("\n=== (2) tower-building decisions of the SIM brain (choice raises max(h4,h5) to >= 11) ===")
    acc = []
    for q in Q:
        b = A.board_from_strings(q["S"]["color"], q["S"]["virus"], q["S"]["link"])
        h0 = q["heights"]
        res = dd.analyse(b.clone(), Pill(*q["cur"]), Pill(*q["nxt"]), q["p"])
        ch = res["best"]
        info = {}
        for a in range(32):
            if not res["ok"][a]:
                continue
            bb, st = after(b, pose_of(a, tuple(q["cur"]), b))
            if bb is not None:
                info[a] = heights(bb)
        hc = info[ch]
        if max(hc[4], hc[5]) <= max(h0[4], h0[5]) or max(hc[4], hc[5]) < 11:
            continue
        alts = [a for a in info if max(info[a][3:6]) <= max(h0[3:6])]
        if not alts:
            print(f"  p{q['p']} {q['sim']}: no non-raising alternative"); continue
        alt = max(alts, key=lambda a: res["val"][a])
        d = res["comp"][ch] - res["comp"][alt]
        acc.append(d)
        print(f"  p{q['p']:3d} t{q['t_spawn']:.0f} vir{q['virus_count']} h{h0} sim {q['sim']} -> tower {max(hc[4], hc[5])} | silicon {q['category']} "
              f"| vs {pose_of(alt, tuple(q['cur']), b)} margin {int(res['val'][ch] - res['val'][alt])}: "
              + " ".join(f"{k}{d[i]:+.0f}" for i, k in enumerate(NAMES) if abs(d[i]) >= 1))
    if acc:
        m = np.mean(acc, 0)
        print(f"  n={len(acc)} mean:", " ".join(f"{k}{m[i]:+.0f}" for i, k in enumerate(NAMES) if abs(m[i]) >= 0.5))
    print("\n=== (3) LATE-FLIP probe ===")
    raw = {json.loads(l)["k"]: json.loads(l) for l in open(RAW)}
    for q in Q:
        if q["category"] != "LATE-FLIP":
            continue
        b = A.board_from_strings(q["S"]["color"], q["S"]["virus"], q["S"]["link"])
        cur, nxt = tuple(q["cur"]), tuple(q["nxt"]); fin = q["actual"]
        hyp = {}
        a = dec.choose(b.clone(), Pill(*nxt), Pill(*nxt), q["p"])          # (a) preview pill searched
        if a is not None:
            o, c, _ = A.decode(a, nxt)
            hyp["preview_pill"] = (o, c)
        a = dec.choose(b.clone(), Pill(*nxt), Pill(*cur), q["p"])          # (c) swapped
        if a is not None:
            o, c, _ = A.decode(a, nxt)
            hyp["swapped"] = (o, c)
        r = raw[q["k"]]
        held = [x for x in r["traj"] if x[1] == q["sim"][0] and x[3] == q["sim"][1]]
        if held:                                                           # (b) pre-flip cells baked in
            t, o, rr, cc, cl = held[-1]
            bb = b.clone()
            cells = [(rr, cc), (rr, cc + 1)] if o == "H" else [(rr, cc), (rr + 1, cc)]
            for (y, x), col in zip(cells, cl):
                bb.color[y, x] = col; bb.is_virus[y, x] = False; bb.link[y, x] = 0
            a = dec.choose(bb, Pill(*cur), Pill(*nxt), q["p"])
            if a is not None:
                o2, c2, _ = A.decode(a, cur)
                hyp["capsule_baked"] = (o2, c2)
        hits = [k for k, v in hyp.items() if v == (fin[0], fin[1])]
        print(f"  p{q['p']:3d} cur{cur} nxt{nxt} sim {q['sim'][:2]} final {fin[:2]} held {q['cat_detail'].get('held_target_frames')} f "
              f"| hypotheses {hyp} -> match {hits or '-'}")


if __name__ == "__main__":
    main([int(x) for x in sys.argv[1:]] or [0, 31, 59, 90])


def steer_replay(Q, dec, i0, seed):
    """Brain + the steering-faithful execution model (steer_model.Steer, the shipping unified tap-2 driver: DISTGATE
    clamps, PROPH pulses, sampled answer latency; NO answer churn / late flips), observed capsules + garbage."""
    import steer_model as SM
    from cascade_link_x import LINK_RIGHT, LINK_LEFT, LINK_DOWN, LINK_UP
    st = SM.Steer(proph="throat", pulse=True, tap_period=2, tap_unified=True); st.reset(seed)
    b = A.board_from_strings(Q[i0]["S"]["color"], Q[i0]["S"]["virus"], Q[i0]["S"]["link"])
    for i in range(i0, len(Q)):
        q = Q[i]
        if b.spawn_blocked():
            return q["p"], "TOPOUT", b.virus_count()
        a = dec.choose(b.clone(), Pill(*q["cur"]), Pill(*q["nxt"]), q["p"])
        ex = st.execute(b.color.tolist(), int(a), q["p"])
        (r0, c0), (r1, c1) = ex["cells"]
        if r0 < 0 or r1 < 0 or b.color[r0, c0] or b.color[r1, c1]:
            return q["p"], "TOPOUT", b.virus_count()
        ca, cb = q["cur"]
        var = ex["var"]
        x0, x1 = (ca, cb) if var in (0, 2) else (cb, ca)
        b.color[r0, c0], b.color[r1, c1] = x0, x1
        b.is_virus[r0, c0] = b.is_virus[r1, c1] = False
        if var < 2:
            b.link[r0, c0], b.link[r1, c1] = LINK_RIGHT, LINK_LEFT
        else:
            b.link[r0, c0], b.link[r1, c1] = LINK_DOWN, LINK_UP
        b.resolve()
        if b.virus_count() == 0:
            return q["p"], "CLEAR", 0
        if not drop(b, garbage_cells(Q, i)) or b.spawn_blocked():
            return q["p"], "TOPOUT", b.virus_count()
    return Q[-1]["p"], "alive", b.virus_count()


def steer_main(p0s, nseed=20):
    C.warmup_chain(topk2=8)
    w, fl = FX.variant("winner")
    dec = Leaf6Decider(w, fl, mode="dist_target", W=60, vk=4, topk2=8, maxpass=0, w_chain=540, ws=20, tap=2)
    Q = [json.loads(l) for l in open(CASES)]
    idx = {q["p"]: i for i, q in enumerate(Q)}
    for p0 in p0s:
        res = [steer_replay(Q, dec, idx[p0], s) for s in range(nseed)]
        from collections import Counter
        print(f"steering-model replay from p{p0}, {nseed} latency seeds: outcomes {dict(Counter(r[1] for r in res))}; "
              f"viruses at end {sorted(r[2] for r in res)}; top-out pills {sorted(r[0] for r in res if r[1] == 'TOPOUT')}")
