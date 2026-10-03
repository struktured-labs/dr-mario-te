"""2026-10-03 match-1 G2: the AI (P2, ANTIBODY_DIST; > 4 viruses so the leaf is ANTIBODY's) tapped out at 10 viruses.

Input: rawh_dist60_20261003_G2.jsonl (track_hidden_dist60_20261003.py; scan 182-456 s). The STUDY pause runs
314.65-394.2 s: record 77 (preview blanked, no landing) is the capsule landed as record 79 (it re-appears at row 0),
record 78 is the pause's preview flicker. Pill index p = k-1 for k <= 76, p = 76 for k = 79, p = k-3 for k >= 80.

Per placement (BANKED as cases_g2_dist60_20261003.jsonl):
  board, heights, spawn lane (max h3, h4), tower = max(h4, h5), HSV-region viruses (cols 3-5, rows < 9);
  silicon landing + action (None = not a straight drop = tuck); category (classify_g2.py rules: MATCH / TUCK /
  PROPH-ESCAPE / LATE-FLIP / SHORT-LANDING (+ DISTGATE clamp) / OTHER) vs the sim brain;
  sim brain = Leaf6Decider dist_target60 (== ANTIBODY above 4 viruses) with the reach mask at the true pill index,
  plus its per-action values / PV term split (decomp_dist60_20261003);
  mechanics of the landing (cells, viruses, cascade, runs, garbage sent), garbage received (mech_check.explain);
  act-stall flag: no allowed root move clears any virus with the actual capsule.
Usage: python g2_tapout_dist60_20261003.py OUT.jsonl
"""
from __future__ import annotations

import json
import sys

import numpy as np

import analyze_g2 as A
import classify_g2 as CL
import mech_check as MC
import decomp_dist60_20261003 as DC
import fast_rtl_x as FX
import cascade_chain_x as C
from drmario.faithful_game import Pill
from endgame_dist60_20261003 import after, pose_of, summ

RAW = "rawh_dist60_20261003_G2.jsonl"


def pill_index(k):
    if k <= 76:
        return k - 1
    if k == 79:
        return 76
    return k - 3


def heights(color):
    return [next((16 - r for r in range(16) if color[r * 8 + c] != "0"), 0) for c in range(8)]


def category(sim, actual, straight, traj, t0, S):
    """classify_g2.main's rules on one placement."""
    so, sc, scl, srow = sim
    ao, ac, acl, arow = actual
    if sim == actual:
        return "MATCH", {}
    if not straight:
        return "TUCK", {}
    pdir = CL.proph(S)
    side = lambda c: "L" if c < 3 else ("R" if c > 3 else "C")
    if pdir in ("L", "R") and side(ac) == pdir and side(sc) != pdir:
        return "PROPH-ESCAPE", {"proph_dir": pdir}
    held = [t for (t, o, r, c, cl) in traj if o == so and c == sc and cl == list(scl)]
    if len(held) >= 4:
        return "LATE-FLIP", {"held_target_frames": len(held)}
    toward = (sc - 3) * (ac - 3) >= 0 and abs(ac - 3) < abs(sc - 3)
    between = min(3, sc) <= ac <= max(3, sc) and ac != sc
    if between and toward and ao == so:
        clamp = any(c != sc and CL.budget(S, r, c, sc) < abs(sc - c) for (t, o, r, c, cl) in traj)
        return "SHORT-LANDING", {"dist_clamp": clamp}
    return "OTHER", {}


def main(out):
    C.warmup_chain(topk2=8)
    w, fl = FX.variant("winner")
    dd = DC.DecompDecider(w, fl, mode="dist_target", W=60, vk=4, topk2=8, maxpass=0, w_chain=540, ws=20, tap=2)
    R = [json.loads(l) for l in open(RAW)]
    L = [(pill_index(r["k"]), r) for r in R if r["k"] != 77 and r["k"] != 78]
    rows = []
    for n, (p, r) in enumerate(L):
        if r["landing"] is None or 0 in r["cur"] or 0 in r["nxt"]:
            continue
        S = r["S"]; b = A.board_from_strings(S["color"], S["virus"], S["link"])
        cur, nxt = tuple(r["cur"]), tuple(r["nxt"])
        o, orow, ocol, ocl = r["landing"]
        actual = [o, ocol, list(ocl), orow]
        act_a = next((a for a in range(32) if pose_of(a, cur, b) == actual), None)
        res = dd.analyse(b.clone(), Pill(*cur), Pill(*nxt), p)
        a_sim = res["best"]
        sim = pose_of(a_sim, cur, b)
        cat, det = category(sim, actual, act_a is not None, r["traj"], r["t_spawn"], S["color"])
        ba, steps = after(b, actual)
        mech = summ(steps) if steps is not None else None
        nxt_rec = next((q for _, q in L[n + 1:] if q["landing"] is not None and 0 not in q["cur"]), None)
        recv = MC.explain(r, nxt_rec) if nxt_rec is not None else None
        clear_exists = False
        per = {}
        for a in range(32):
            if not res["ok"][a]:
                continue
            bb, st = after(b, pose_of(a, cur, b))
            if bb is None:
                continue
            sm = summ(st)
            hh = heights("".join(str(int(x)) for x in bb.color.ravel()))
            per[a] = {"vir": sm["viruses"], "cells": sm["cells"], "tower_after": max(hh[4], hh[5]),
                      "lane_after": max(hh[3], hh[4]), "maxh_after": max(hh)}
            clear_exists |= sm["viruses"] > 0
        h = heights(S["color"])
        V = np.array([int(c) for c in S["virus"]]).reshape(16, 8)
        hab = heights("".join(str(int(x)) for x in ba.color.ravel())) if ba is not None else None
        rows.append({"p": p, "k": r["k"], "t_spawn": r["t_spawn"], "spawn_kind": r.get("spawn_kind"), "cur": cur,
                     "nxt": nxt, "S": S, "virus_count": int(V.sum()), "heights": h, "lane": max(h[3], h[4]),
                     "tower": max(h[4], h[5]), "hsv_viruses": int(V[:9, 3:6].sum()),
                     "actual": actual, "actual_action": act_a, "straight_drop": act_a is not None,
                     "sim": sim, "sim_action": a_sim, "category": cat, "cat_detail": det, "proph_dir": CL.proph(S["color"]),
                     "mech": mech, "garbage_recv": recv, "heights_after_actual": hab,
                     "act_clear_exists": clear_exists, "n_allowed": int(sum(int(x) for x in res["allowed"])),
                     "per_action": {str(a): v for a, v in per.items()},
                     "val": {str(a): int(res["val"][a]) for a in per},
                     "comp": {str(a): [round(float(x), 1) for x in res["comp"][a]] for a in per},
                     "lateral_f": [round((t - r["t_spawn"]) * 60) for (t, oo, rr, cc, cl), prev in
                                   zip(r["traj"][1:], r["traj"][:-1]) if cc != prev[3]]})
        print(p, r["t_spawn"], "v", rows[-1]["virus_count"], "h", h, "act", actual, "sim", sim, cat, "recv", recv,
              "mech", (mech or {}).get("cells"), flush=True)
    with open(out, "w") as fh:
        for q in rows:
            fh.write(json.dumps(q) + "\n")
    print(f"{len(rows)} placements -> {out}")


if __name__ == "__main__":
    main(sys.argv[1])
