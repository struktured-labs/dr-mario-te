"""2026-10-04 match 4 game 2: the FAIR2 bot (cart b1b57638 + rbf V11 43aa62d5, fw c51d2e21) TAPPED OUT at owner 12 /
AI 16, the first AI tap-out on a fair build. Tap-out forensics in the RESULT_COUCH_DIST60_G2.md style.

Input: scan2_fair_20261004.py 60 fps reads of both bottles (rec 2, 1126-1302 s), hidden-spawn tracker per bottle
(rawh_m4g2_p1/p2.jsonl in the tmp scan dir).

  cases   per AI placement: board, capsules, pill index p, silicon landing + its action (None = not a straight drop),
          the SILICON-FAITHFUL brain's choice (braingap Leaf6FwDecider, every firmware switch on; dist_target60,
          w_chain 540, ws 20, tap 2, reach mask at p), the classify_g2 category (g2_tapout_dist60_20261003.category),
          mechanics (cells/viruses/runs/sent), garbage received before the next board (mech_check.explain).
          -> cases_m4g2_fair_20261004.jsonl (pubtrace_g2.py CASES format)
  replay  brain-only replays from several pills (g2_counterfactual's replay with the silicon-faithful brain, observed
          capsules + observed garbage, perfect execution) -> printed + m4g2_replay_fair_20261004.txt

Usage: python m4g2_fair_20261004.py cases | replay [p0 ...]
"""
from __future__ import annotations

import json
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
BG = os.path.join(HERE, "..", "braingap")
sys.path.insert(0, os.path.abspath(BG))
import rtlengine_braingap_20261003 as E  # noqa: E402,F401  (pins paths + fresh numba cache, as the braingap tools do)
sys.path.insert(0, E.CVX)
sys.path.insert(0, HERE)
os.chdir(HERE)
import analyze_g2 as A  # noqa: E402
import mech_check as MC  # noqa: E402
import cascade_leaf6fw_braingap_20261003 as F  # noqa: E402
from drmario.faithful_game import Pill  # noqa: E402
from endgame_dist60_20261003 import after, pose_of, summ  # noqa: E402
from g2_tapout_dist60_20261003 import category  # noqa: E402
import fair_20261004 as FA  # noqa: E402

GAME = os.environ.get("GAME", "m4g2")
CASES = os.path.join(HERE, f"cases_{GAME}_fair_20261004.jsonl")


def heights_s(color):
    C = np.array([int(ch) for ch in color]).reshape(16, 8)
    return [int(16 - np.argmax(C[:, c] > 0)) if (C[:, c] > 0).any() else 0 for c in range(8)]


def brain():
    import fast_rtl_x as FX
    import cascade_chain_x as C
    C.warmup_chain(topk2=8)
    w, fl = FX.variant("winner")
    return F.Leaf6FwDecider(w, fl, sw=None, topk2=8, maxpass=0, w_chain=540, ws=20, tap=2, mode="dist_target", W=60, vk=4)


def load(seat):
    t_round, t_end, final = FA.window(GAME)
    R = [json.loads(l) for l in open(os.path.join(FA.SCAN, f"rawh_{GAME}_{seat}.jsonl"))]
    R = [r for r in R if 0 not in r["cur"] and 0 not in r["nxt"] and t_round <= r["t_spawn"] <= t_end]
    for p, r in enumerate(R):
        r["p"] = p                         # pills placed before this one (every spawn counts, landing or not)
    fixes = FA.repair(R)                   # clear-pop / lost-trajectory repair (shared with fair_20261004.py), in place
    for f in fixes:
        print("REPAIR", json.dumps(f))
    return R, (t_round, t_end, final)


def cases():
    dec = brain()
    R, (t_round, t_end, final) = load("p2")
    L = [r for r in R if r["landing"] is not None]
    rows = []
    for n, r in enumerate(L):
        S = r["S"]; b = A.board_from_strings(S["color"], S["virus"], S["link"])
        cur, nxt = tuple(r["cur"]), tuple(r["nxt"])
        o, orow, ocol, ocl = r["landing"]
        actual = [o, ocol, list(ocl), orow]
        act_a = next((a for a in range(32) if pose_of(a, cur, b) == actual), None)
        a_sim = dec.choose(b.clone(), Pill(*cur), Pill(*nxt), r["p"])
        sim = pose_of(a_sim, cur, b) if a_sim is not None else None
        cat, det = category(sim, actual, act_a is not None, r["traj"], r["t_spawn"], S["color"]) if sim else ("NOMOVE", {})
        ba, steps = after(b, actual)
        mech = summ(steps) if steps is not None else None
        nx = L[n + 1] if n + 1 < len(L) else None
        recv = MC.explain(r, nx) if nx is not None else None
        sim_mech = None
        if sim:
            bs, ss = after(b, sim)
            sim_mech = summ(ss) if ss is not None else None
        h = heights_s(S["color"])
        rows.append({"game": GAME, "p": r["p"], "k": r["k"], "t_spawn": r["t_spawn"], "t_rel": round(r["t_spawn"] - L[0]["t_spawn"], 3),
                     "spawn_kind": r.get("spawn_kind"), "S": S, "cur": list(cur), "nxt": list(nxt),
                     "virus_count": r["virus_count"], "heights": h, "maxh": max(h), "lane": max(h[3], h[4]),
                     "actual": actual, "actual_action": act_a, "sim": sim, "sim_action": a_sim,
                     "category": cat, "detail": det, "mech": mech, "sim_mech": sim_mech, "garbage_recv": recv,
                     "traj": r["traj"], "src": S["src"]})
        print(f"p{r['p']:3d} t{rows[-1]['t_rel']:6.1f} v{r['virus_count']:2d} maxh {max(h):2d} lane {max(h[3], h[4]):2d} "
              f"sil {actual} a{act_a} | brain {sim} a{a_sim} | {cat} {det} | recv {recv}", flush=True)
    with open(CASES, "w") as fh:
        for q in rows:
            fh.write(json.dumps(q) + "\n")
    from collections import Counter
    c = Counter(q["category"] for q in rows)
    tall = [q for q in rows if q["maxh"] >= 12]
    print(f"{GAME}: n={len(rows)} {dict(c)}  MATCH {100 * c['MATCH'] / len(rows):.0f}% | maxh>=12 n={len(tall)} "
          f"MATCH {sum(q['category'] == 'MATCH' for q in tall)} LF {sum(q['category'] == 'LATE-FLIP' for q in tall)} -> {CASES}")


def replay(p0s):
    import g2_counterfactual_dist60_20261003 as GC
    dec = brain()
    Q = [json.loads(l) for l in open(CASES)]
    idx = {q["p"]: i for i, q in enumerate(Q)}
    out = open(os.path.join(HERE, f"{GAME}_replay_fair_20261004.txt"), "w")
    sil = {q["p"]: (q["virus_count"], q["heights"]) for q in Q}
    for p0 in p0s:
        p0 = min(idx, key=lambda p: abs(p - p0))
        R = GC.replay(Q, dec, idx[p0])
        last = R[-1]
        s = (f"from p{p0}: {len(R)} pills -> end {last[1]} at p{last[0]} viruses {last[2]} heights {last[3]} "
             f"| silicon at that pill: {sil.get(last[0])} | silicon final p{Q[-1]['p']} vir {Q[-1]['virus_count']} h {Q[-1]['heights']}")
        print(s, flush=True); out.write(s + "\n")
        for (p, st, v, h) in R:
            if p % 10 == 0 or st != "ok":
                ss = sil.get(p + 1)
                line = f"    p{p:3d} {st:6s} vir {v:2d} max {max(h):2d} h {h} | silicon next: {ss}"
                print(line); out.write(line + "\n")
    out.close()



def stall():
    """Per pill: how many allowed root moves (reach mask at p, straight drops) clear >= 1 virus with the live capsule,
    and whether silicon / the brain took one. Appends 'n_vclear' etc. to the banked cases."""
    dec = brain()
    Q = [json.loads(l) for l in open(CASES)]
    for q in Q:
        b = A.board_from_strings(q["S"]["color"], q["S"]["virus"], q["S"]["link"])
        cur = tuple(q["cur"])
        allowed = dec.mask(b, q["p"])
        nv = nc = 0
        for a in range(32):
            if not allowed[a]:
                continue
            bb, st = after(b, pose_of(a, cur, b))
            if bb is None:
                continue
            sm = summ(st)
            nv += sm["viruses"] > 0; nc += sm["cells"] > 0
        q["n_allowed"] = int(sum(bool(x) for x in allowed)); q["n_vclear"] = nv; q["n_clear"] = nc
    with open(CASES, "w") as fh:
        for q in Q:
            fh.write(json.dumps(q) + "\n")
    for lo, hi in ((0, 63), (64, 89), (90, 108)):
        S = [q for q in Q if lo <= q["p"] <= hi]
        print(f"p{lo}-{hi}: pills {len(S)}, viruses {S[0]['virus_count']}->{S[-1]['virus_count']}, "
              f"no virus-clearing move available on {sum(q['n_vclear'] == 0 for q in S)}, "
              f"available and silicon cleared a virus {sum(q['n_vclear'] > 0 and q['mech'] and q['mech']['viruses'] > 0 for q in S)}, "
              f"available but silicon did not {sum(q['n_vclear'] > 0 and not (q['mech'] and q['mech']['viruses'] > 0) for q in S)}, "
              f"of those the brain would have {sum(q['n_vclear'] > 0 and not (q['mech'] and q['mech']['viruses'] > 0) and q['sim_mech'] and q['sim_mech']['viruses'] > 0 for q in S)}; "
              f"misses {sum(q['category'] != 'MATCH' for q in S)}, maxh>=14 on {sum(q['maxh'] >= 14 for q in S)}")
    for q in Q:
        if q["p"] >= 60 and (q["n_vclear"] > 0 or q["category"] != "MATCH"):
            print(f"  p{q['p']} v{q['virus_count']} maxh {q['maxh']} vclear-moves {q['n_vclear']}/{q['n_allowed']} {q['category']} "
                  f"sil {q['actual']} vir {q['mech'] and q['mech']['viruses']} | brain {q['sim']} vir {q['sim_mech'] and q['sim_mech']['viruses']}")



GO_F = 8          # spawn -> GO, frames (TRACE_G2_p99: GO at f8); commit gate = GO + 6 f (DRMINTHINK 12 hooks)


def cosim():
    """Join the V11 co-sim publish timelines (pubtrace_<game>_fair_20261004.jsonl, lateflip h16 pubtrace_g2.py with
    FW=fw540_reachtap_dist_tuckreach_leflush_c51d2e21.hex on the vsim_pub2 build of RTL 3b164c7) to the cases.
      FINAL     silicon == the copro's final answer
      AT-GATE   silicon == the running best published by GO+6 f (the commit) but != final: the later answer was not
                taken (LATEGUARD refusal, or no time)
      OTHER-PUB silicon == some other published candidate
      HYBRID    silicon is none of the published candidates nor the final (and a straight drop)
      TUCK      silicon is not a straight drop
    plus: copro final vs the silicon-faithful python brain, and DONE vs the pill's own lock frame."""
    Q = {q["p"]: q for q in map(json.loads, open(CASES))}
    T = {t["p"]: t for t in map(json.loads, open(os.path.join(HERE, f"pubtrace_{GAME}_fair_20261004.jsonl")))}
    rows = []
    from collections import Counter
    for p in sorted(T):
        t, q = T[p], Q.get(p)
        if q is None:
            continue
        sil = q["actual_action"]; fin = t["final"][2]
        pubs = [x[3] for x in t["pubs"]]
        gate = [x for x in t["pubs"] if x[0] <= 6.0]
        at_gate = gate[-1][3] if gate else None
        if sil is None:
            cat = "TUCK" if not (t.get("tuck") and t["tuck"][0] != 255) else "TUCK(copro tuck)"
        elif sil == fin:
            cat = "FINAL"
        elif sil == at_gate:
            cat = "AT-GATE"
        elif sil in pubs:
            cat = "OTHER-PUB"
        else:
            cat = "HYBRID"
        traj = q.get("traj") or []
        lock_f = round((traj[-1][0] - q["t_spawn"]) * 60, 1) if traj else None
        rows.append({"p": p, "cat_cosim": cat, "cat_brain": q["category"], "sil": sil, "final": fin, "at_gate": at_gate,
                     "pubs": t["pubs"], "done_f": t["done_f"], "lock_f": lock_f, "tuck": t.get("tuck"),
                     "brain": q["sim_action"], "brain_eq_final": q["sim_action"] == fin, "maxh": q["maxh"], "vc": q["virus_count"],
                     "search_outlived_pill": (lock_f is not None and t["done_f"] + GO_F > lock_f)})
    with open(os.path.join(HERE, f"cosim_{GAME}_fair_20261004.jsonl"), "w") as fh:
        for r in rows:
            fh.write(json.dumps(r) + "\n")
    c = Counter(r["cat_cosim"] for r in rows)
    print(f"{GAME}: n={len(rows)} co-sim categories {dict(c)}; copro final == silicon-faithful python brain on "
          f"{sum(r['brain_eq_final'] for r in rows)}/{len(rows)}; search outlived the pill on {sum(r['search_outlived_pill'] for r in rows)}")
    print("cross-tab (brain category -> co-sim category):", dict(Counter((r["cat_brain"], r["cat_cosim"]) for r in rows)))
    for r in rows:
        if r["cat_cosim"] != "FINAL" or r["cat_brain"] != "MATCH" or not r["brain_eq_final"]:
            print(f"  p{r['p']:3d} v{r['vc']:2d} maxh {r['maxh']:2d} {r['cat_brain']:13s} {r['cat_cosim']:9s} sil a{r['sil']} final a{r['final']} "
                  f"gate a{r['at_gate']} brain a{r['brain']} DONE {r['done_f']}f lock {r['lock_f']}f pubs " +
                  " ".join(f"a{x[3]}@{x[0]}" for x in r["pubs"]) + (f" tuck {r['tuck']}" if r['tuck'] and r['tuck'][0] != 255 else ""))


if __name__ == "__main__":
    if sys.argv[1] == "cosim":
        cosim()
    elif sys.argv[1] == "stall":
        stall()
    elif sys.argv[1] == "cases":
        cases()
    else:
        replay([int(x) for x in sys.argv[2:]] or [0, 20, 40, 60, 80])
