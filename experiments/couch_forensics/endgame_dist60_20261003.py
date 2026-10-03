"""2026-10-03 couch, owner vs ANTIBODY_DIST (P2), L11 MED: what did the AI do from 4 viruses to 0 in G3/G4, and why.

Input: track_hidden_dist60_20261003.py output (rawh_G3 / rawh_G4a / rawh_G4b) from scan_frames.py with
CF_GEOM=geom_dist60_20261003.json. G4 was paused (study mode) from ~947 s to ~1937 s: rawh_G4a record 54 (no landing,
preview blanked) is the same capsule as rawh_G4b record 0, so G4 pill p = A.k - 1 (k 1..53), then 53 + B.k.

Per placement (BANKED as cases_dist60_20261003.jsonl):
  board S (colour/virus/link strings), cur, nxt, pill index p (= pills_placed, drives the reach mask), silicon landing
  and its action index (None = not a straight drop = tuck), mechanics of the landing (cells / viruses cleared, cascade
  steps, MATCHED RUNS = ROM comboCounter, garbage sent = min(runs, 4) if runs >= 2), garbage received before the next
  board (mech_check.explain), the firmware DIST target (argmin D, ties lowest index, only at 1..4 viruses), D before,
  D after the landing, whether an allowed root move clears the target / reduces D, the sim brains' choices
  (ANTIBODY_DIST = Leaf6Decider dist_target60, ANTIBODY = mode off), and for DIST60 the per-root-action PV term
  decomposition (decomp_dist60_20261003._root_comps) of the chosen move vs the best D-reducing move.
Usage: python endgame_dist60_20261003.py DIR OUT.jsonl            (DIR = . for the banked rawh_dist60_20261003_*.jsonl)
       python endgame_dist60_20261003.py --prior prior_spec_dist60_20261003.json OUT.jsonl
"""
from __future__ import annotations

import json
import os
import sys

import numpy as np

import analyze_g2 as A
import mech_check as MC
import decomp_dist60_20261003 as DC
from drmario.faithful_game import Pill, ORIENT_H, ORIENT_V
from cascade_leaf6_x import _root_dists, Leaf6Decider
import fast_rtl_x as FX
import cascade_chain_x as C

ROWS, COLS = 16, 8


def _rawh(d, g):
    banked = os.path.join(d, f"rawh_dist60_20261003_{g}.jsonl")          # banked copy in couch_forensics
    return banked if os.path.exists(banked) else os.path.join(d, f"rawh_{g}.jsonl")


def load_games(d):
    G = {}
    R3 = [json.loads(l) for l in open(_rawh(d, "G3"))]
    G["G3"] = [(r["k"] - 1, r) for r in R3 if r["k"] >= 1]
    Ra = [json.loads(l) for l in open(_rawh(d, "G4a"))]
    Rb = [json.loads(l) for l in open(_rawh(d, "G4b"))]
    assert tuple(Ra[54]["cur"]) == tuple(Rb[0]["cur"]) and Ra[54]["landing"] is None
    G["G4"] = [(r["k"] - 1, r) for r in Ra if 1 <= r["k"] <= 53] + [(53 + r["k"], r) for r in Rb]
    return G


def count_runs(g):
    n = 0
    for r in range(ROWS):
        c = 0
        while c < COLS:
            v = g[r, c]
            c2 = c
            while c2 + 1 < COLS and g[r, c2 + 1] == v:
                c2 += 1
            if v != 0 and c2 - c + 1 >= 4:
                n += 1
            c = c2 + 1
    for c in range(COLS):
        r = 0
        while r < ROWS:
            v = g[r, c]
            r2 = r
            while r2 + 1 < ROWS and g[r2 + 1, c] == v:
                r2 += 1
            if v != 0 and r2 - r + 1 >= 4:
                n += 1
            r = r2 + 1
    return n


def resolve_runs(b):
    steps = []
    while True:
        runs = count_runs(b.color)
        mask = b._find_clears()
        n = int(mask.sum())
        if n == 0:
            break
        vir = b._apply_clear(mask)
        b._apply_gravity()
        steps.append({"cells": n, "viruses": int(vir), "runs": runs})
    return steps


def place(b, pose):
    o, c, cl = pose[0], pose[1], pose[2]
    bb = b.clone()
    if not bb.place_pill(Pill(*cl), ORIENT_H if o == "H" else ORIENT_V, c):
        return None
    return bb


def pose_of(a, cur, b):
    o, c, cl = A.decode(a, cur)
    row = A.resting(b, o, c)
    return [o, c, list(cl), row and row[0]]


def target_of(b):
    col, vir = DC.board_flat(b)
    nv = int(vir.sum())
    if not (1 <= nv <= 4):
        return None, None
    d = np.empty(ROWS * COLS, np.int64)
    _root_dists(col, vir, 16, d, 0)
    best = -1
    for i in range(ROWS * COLS):
        if d[i] >= 0 and (best < 0 or d[i] < d[best]):
            best = i
    return best, int(d[best])


def d_of(b, idx):
    if not b.is_virus[idx // COLS, idx % COLS]:
        return 0
    col, vir = DC.board_flat(b)
    d = np.empty(ROWS * COLS, np.int64)
    _root_dists(col, vir, 16, d, 0)
    return int(d[idx])


def after(b, pose):
    bb = place(b, pose)
    if bb is None:
        return None, None
    steps = resolve_runs(bb)
    return bb, steps


def summ(steps):
    runs = sum(s["runs"] for s in steps)
    return {"cells": sum(s["cells"] for s in steps), "viruses": sum(s["viruses"] for s in steps),
            "chain": len(steps), "runs": runs, "sent": (min(runs, 4) if runs >= 2 else 0), "steps": steps}


def load_prior(spec_path):
    """Prior couch endgames re-scanned with the hidden-spawn tracker. spec: {name: {"rawh": path, "p0": pill index of
    record 0 (from the old cases' k_game, which undercounts hidden spawns: the reach-mask band is approximate),
    "label": ..., "build": ...}}. Record k -> p = p0 + k."""
    spec = json.load(open(spec_path))
    G = {}
    for name, s in spec.items():
        R = [json.loads(l) for l in open(s["rawh"])]
        G[name] = [(s["p0"] + r["k"], r) for r in R]
    return G


def main(d, out, prior=None):
    C.warmup_chain(topk2=8)
    w, fl = FX.variant("winner")
    kw = dict(topk2=8, maxpass=0, w_chain=540, ws=20, tap=2)
    dist = DC.DecompDecider(w, fl, mode="dist_target", W=60, vk=4, **kw)
    off = Leaf6Decider(w, fl, mode="off", **kw)
    G = load_games(d) if prior is None else load_prior(prior)
    rows = []
    for g, L in G.items():
        L = [(p, r) for p, r in L]
        for n, (p, r) in enumerate(L):
            if r["landing"] is None or 0 in r["cur"] or 0 in r["nxt"]:
                continue
            S = r["S"]
            b = A.board_from_strings(S["color"], S["virus"], S["link"])
            cur, nxt = tuple(r["cur"]), tuple(r["nxt"])
            nv = b.virus_count()
            o, orow, ocol, ocl = r["landing"]
            actual = [o, ocol, list(ocl), orow]
            act_a = next((a for a in range(32) if pose_of(a, cur, b) == actual), None)
            ba, steps = after(b, actual)
            mech = summ(steps) if steps is not None else None
            # garbage received before the next settled board (ROM drops it after the receiver's placement)
            nxt_rec = next((q for _, q in L[n + 1:] if q["landing"] is not None and 0 not in q["cur"]), None)
            recv = MC.explain(r, nxt_rec) if nxt_rec is not None else None
            # brains
            res = dist.analyse(b.clone(), Pill(*cur), Pill(*nxt), p)
            a_dist = res["best"]
            a_off = off.choose(b.clone(), Pill(*cur), Pill(*nxt), p)
            tgt, d0 = target_of(b)
            rec = {"game": g, "p": p, "k": r["k"], "t_spawn": r["t_spawn"], "t_next_spawn": r["t_next_spawn"],
                   "spawn_kind": r.get("spawn_kind"), "cur": cur, "nxt": nxt, "S": S, "virus_count": nv,
                   "actual": actual, "actual_action": act_a, "straight_drop": act_a is not None,
                   "mech": mech, "garbage_recv": recv,
                   "dist_action": a_dist, "dist_pose": pose_of(a_dist, cur, b) if a_dist >= 0 else None,
                   "off_action": a_off, "off_pose": pose_of(a_off, cur, b) if a_off is not None else None,
                   "match_dist": act_a is not None and act_a == a_dist,
                   "match_dist_pose": (pose_of(a_dist, cur, b) == actual) if a_dist >= 0 else False,
                   "match_off_pose": (pose_of(a_off, cur, b) == actual) if a_off is not None else False,
                   "dist_differs_from_off": a_dist != a_off,
                   "w6": [int(x) for x in res["w6"]]}
            if tgt is not None:
                tr, tc = divmod(tgt, COLS)
                allowed = res["allowed"]
                per = {}
                for a in range(32):
                    if not res["ok"][a]:
                        continue
                    bb, st = after(b, pose_of(a, cur, b))
                    if bb is None:
                        continue
                    per[a] = {"d_after": d_of(bb, tgt), "clears_target": not bool(bb.is_virus[tr, tc]),
                              "mech": summ(st)}
                dred = [a for a in per if per[a]["d_after"] < d0 or per[a]["clears_target"]]
                fin = [a for a in per if per[a]["clears_target"]]
                alt = max(dred, key=lambda a: res["val"][a]) if dred else None
                ch = a_dist
                rec.update({
                    "target": [tr, tc, int(b.color[tr, tc])], "D_before": d0,
                    "D_after_actual": (d_of(ba, tgt) if ba is not None else None),
                    "actual_clears_target": (not bool(ba.is_virus[tr, tc])) if ba is not None else None,
                    "n_allowed": int(sum(int(x) for x in allowed)), "n_legal": len(per),
                    "n_d_reducing": len(dred), "n_finishing": len(fin),
                    "dist_choice_d_after": per[ch]["d_after"] if ch in per else None,
                    "dist_choice_clears_target": per[ch]["clears_target"] if ch in per else None,
                    "dist_choice_mech": per[ch]["mech"] if ch in per else None,
                    "off_choice_d_after": per[a_off]["d_after"] if a_off in per else None,
                    "best_dred_action": alt, "best_dred_pose": pose_of(alt, cur, b) if alt is not None else None,
                    "best_dred_d_after": per[alt]["d_after"] if alt is not None else None,
                    "best_dred_mech": per[alt]["mech"] if alt is not None else None,
                    "val_chosen": int(res["val"][ch]), "val_best_dred": int(res["val"][alt]) if alt is not None else None,
                    "comp_chosen": dict(zip(DC.NAMES, [round(float(x), 2) for x in res["comp"][ch]])),
                    "comp_best_dred": dict(zip(DC.NAMES, [round(float(x), 2) for x in res["comp"][alt]])) if alt is not None else None,
                    "pv2_chosen": (pose_of(int(res["pv2"][ch]), nxt, after(b, pose_of(ch, cur, b))[0])
                                   if res["pv2"][ch] >= 0 else None),
                    "pv2imm_chosen": [float(x) for x in res["pv2imm"][ch]],
                    "pv2imm_best_dred": [float(x) for x in res["pv2imm"][alt]] if alt is not None else None,
                    "actual_val_rank": (int(sorted([res["val"][a] for a in per], reverse=True).index(res["val"][act_a]))
                                        if act_a in per else None),
                })
            rows.append(rec)
            print(g, p, r["t_spawn"], "nv", nv, "act", actual, "dist", rec["dist_pose"], "match", rec["match_dist_pose"],
                  "D", rec.get("D_before"), "->", rec.get("D_after_actual"), flush=True)
    with open(out, "w") as fh:
        for q in rows:
            fh.write(json.dumps(q) + "\n")
    print(f"{len(rows)} placements -> {out}")


if __name__ == "__main__":
    if sys.argv[1] == "--prior":                 # --prior SPEC.json OUT.jsonl
        main(None, sys.argv[3], prior=sys.argv[2])
    else:
        main(sys.argv[1], sys.argv[2])
