"""Endgame STALL characterisation for one 2026-10-04 game (AI = P2), e.g. M5 G2 (FAIR; the owner won by full clear,
0 / AI 7: "it spun on last 2 stuck columns I think") and M4 G2 (FAIR2's tap-out).

Per AI placement (hidden-spawn tracker + fair_20261004.repair):
  * the SILICON-FAITHFUL brain (braingap Leaf6FwDecider, all firmware switches on; = fw 1488e158's main search, exact for
    FAIR; FAIR2's V11 adds tuck reach/order, so its tuck finals can differ), classify_g2 category;
  * the allowed root moves (reach mask at the true pill index) that clear >= 1 virus / clear the TARGET virus with the
    live capsule, and whether silicon / the brain took one;
  * CELL PROVENANCE: every cell carries a tag through the game: V (virus), P<p> (own pill half, straight drop),
    T<p> (own pill half placed by a non-straight-drop path = tuck/slide), G<p> (owner garbage that arrived after AI pill
    p). Tags move with the faithful resolve (clears remove them; gravity preserves each column's top-to-bottom order) and
    are reconciled to the next observed board column by column (extra cells on a column top = garbage).
Stalls = maximal runs of >= 10 consecutive placements at one virus count. For each: duration, the remaining viruses with
the column content above each (top -> virus, tagged), the sealing material by provenance, clearing moves available,
silicon == brain.

Usage: GAME=m5g2 python stall_fair_20261004.py    -> stall_<game>_fair_20261004.json + cases_stall_<game>_fair_20261004.jsonl
"""
from __future__ import annotations

import json
import os
import sys
from collections import Counter

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.abspath(os.path.join(HERE, "..", "braingap")))
import rtlengine_braingap_20261003 as E  # noqa: E402,F401
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

GAME = os.environ.get("GAME", "m5g2")
ROWS, COLS = 16, 8
GL = {1: "r", 2: "y", 3: "b"}


def brain():
    import fast_rtl_x as FX
    import cascade_chain_x as C
    C.warmup_chain(topk2=8)
    w, fl = FX.variant("winner")
    return F.Leaf6FwDecider(w, fl, sw=None, topk2=8, maxpass=0, w_chain=540, ws=20, tap=2, mode="dist_target", W=60, vk=4)


def load():
    t_round, t_end, final = FA.window(GAME)
    R = [json.loads(l) for l in open(os.path.join(FA.SCAN, f"rawh_{GAME}_p2.jsonl"))]
    R = [r for r in R if 0 not in r["cur"] and 0 not in r["nxt"] and t_round <= r["t_spawn"] <= t_end]
    for p, r in enumerate(R):
        r["p"] = p
    fixes = FA.repair(R)
    return [r for r in R if r["landing"] is not None], fixes, (t_round, t_end, final)


def _remap_gravity(before, after_, T):
    """Per column, the non-empty cells keep their top-to-bottom order under gravity."""
    T2 = np.full((ROWS, COLS), "", dtype=object)
    for c in range(COLS):
        src = [T[r, c] for r in range(ROWS) if before[r, c] > 0]
        dst = [r for r in range(ROWS) if after_[r, c] > 0]
        for r, t in zip(dst, src[len(src) - len(dst):] if len(src) >= len(dst) else src):
            T2[r, c] = t
    return T2


def resolve_tagged(b, T):
    while True:
        mask = b._find_clears()
        if int(mask.sum()) == 0:
            return b, T
        T = T.copy(); T[mask] = ""
        b._apply_clear(mask)
        before = b.color.copy()
        b._apply_gravity()
        T = _remap_gravity(before, b.color, T)


def reconcile(Pc, T, N, tag_new):
    """Map tags from the predicted board Pc onto the observed next board N, column by column. Extra cells on a
    column's top are new garbage (tag_new); fewer cells -> map from the bottom, unknown for the rest."""
    T2 = np.full((ROWS, COLS), "", dtype=object)
    for c in range(COLS):
        src = [T[r, c] for r in range(ROWS) if Pc[r, c] > 0]
        dst = [r for r in range(ROWS) if N[r, c] > 0]
        if len(dst) >= len(src):
            extra = len(dst) - len(src)
            for i, r in enumerate(dst):
                T2[r, c] = tag_new if i < extra else src[i - extra]
        else:
            k = len(src) - len(dst)
            for i, r in enumerate(dst):
                T2[r, c] = src[i + k] or "?"
    return T2


def main():
    dec = brain()
    L, fixes, (t_round, t_end, final) = load()
    t0 = L[0]["t_spawn"]
    S0 = FA.grid(L[0]["S"]["color"]); V0 = FA.grid(L[0]["S"]["virus"])
    T = np.full((ROWS, COLS), "", dtype=object)
    T[(S0 > 0) & (V0 > 0)] = "V"; T[(S0 > 0) & (V0 == 0)] = "?"
    rows = []
    for n, r in enumerate(L):
        S = r["S"]; b = A.board_from_strings(S["color"], S["virus"], S["link"])
        cur, nxt = tuple(r["cur"]), tuple(r["nxt"])
        o, orow, ocol, ocl = r["landing"]
        actual = [o, ocol, list(ocl), orow]
        act_a = next((a for a in range(32) if pose_of(a, cur, b) == actual), None)
        a_sim = dec.choose(b.clone(), Pill(*cur), Pill(*nxt), r["p"])
        sim = pose_of(a_sim, cur, b) if a_sim is not None else None
        if r.get("landing_repaired") or not r["traj"]:
            cat = "MATCH" if sim == actual else "NOTRAJ"
        else:
            cat = category(sim, actual, act_a is not None, r["traj"], r["t_spawn"], S["color"])[0] if sim else "NOMOVE"
        allowed = dec.mask(b, r["p"])
        nv = 0; vtargets = Counter()
        for a in range(32):
            if not allowed[a]:
                continue
            bb, st = after(b, pose_of(a, cur, b))
            if bb is not None and summ(st)["viruses"] > 0:
                nv += 1
        _, st_a = after(b, actual)
        sil_v = summ(st_a)["viruses"] if st_a is not None else 0
        sim_v = summ(after(b, sim)[1])["viruses"] if sim else 0
        h = FA.heights(FA.grid(S["color"]))
        # provenance snapshot BEFORE this placement (tags on S_k), then advance
        V = FA.grid(S["virus"]); C = FA.grid(S["color"])
        vir_cells = [(int(rr), int(cc)) for rr, cc in np.argwhere(V > 0)]
        cols_above = {}
        for (rr, cc) in vir_cells:
            seq = [(int(x), GL.get(int(C[x, cc]), "?") + ("*" if V[x, cc] else ""), str(T[x, cc]) or "?")
                   for x in range(rr) if C[x, cc] > 0]
            cols_above[f"{rr},{cc}"] = seq
        rows.append({"game": GAME, "p": r["p"], "t_rel": round(r["t_spawn"] - t0, 2), "virus_count": int(V.sum()),
                     "heights": h, "maxh": max(h), "cur": list(cur), "actual": actual, "actual_action": act_a,
                     "sim": sim, "sim_action": a_sim, "category": cat, "n_allowed": int(sum(bool(x) for x in allowed)),
                     "n_vclear": nv, "silicon_cleared_virus": sil_v, "brain_clears_virus": sim_v,
                     "viruses": [[rr, cc, GL[int(C[rr, cc])]] for rr, cc in vir_cells], "above_viruses": cols_above,
                     "tuck": act_a is None})
        # advance tags: place the pill, resolve with tags, reconcile with the next observed board
        tag = ("T" if act_a is None else "P") + str(r["p"])
        bp = A.board_from_strings(S["color"], S["virus"], S["link"])
        Tp = T.copy()
        if o == "H":
            bp.color[orow, ocol], bp.color[orow, ocol + 1] = ocl; bp.link[orow, ocol], bp.link[orow, ocol + 1] = 4, 3
            Tp[orow, ocol] = Tp[orow, ocol + 1] = tag
        else:
            bp.color[orow, ocol], bp.color[orow + 1, ocol] = ocl; bp.link[orow, ocol], bp.link[orow + 1, ocol] = 2, 1
            Tp[orow, ocol] = Tp[orow + 1, ocol] = tag
        bp.is_virus[orow, ocol] = False
        bp, Tp = resolve_tagged(bp, Tp)
        if n + 1 < len(L):
            N = FA.grid(L[n + 1]["S"]["color"])
            T = reconcile(bp.color, Tp, N, "G" + str(r["p"]))
            rows[-1]["garbage_new_cells"] = int(sum(1 for x in T.ravel() if x == "G" + str(r["p"])))
    # stalls = maximal runs of >= 10 placements at one virus count
    stalls = []; i = 0
    while i < len(rows):
        j = i
        while j + 1 < len(rows) and rows[j + 1]["virus_count"] == rows[i]["virus_count"]:
            j += 1
        if j - i + 1 >= 10:
            stalls.append((i, j))
        i = j + 1
    out = {"game": GAME, "repairs": fixes, "n_placements": len(rows), "t_end_rel": round(t_end - t0, 2), "stalls": []}
    for i, j in stalls:
        R_ = rows[i:j + 1]
        t_a = R_[0]["t_rel"]; t_b = rows[j + 1]["t_rel"] if j + 1 < len(rows) else round(t_end - t0, 2)
        # sealing material: tags above every remaining virus at the stall start and end
        def seal(rw):
            cnt = Counter()
            for k, seq in rw["above_viruses"].items():
                for (_, _, tg) in seq:
                    cnt[(tg or "?")[0]] += 1
            return dict(cnt)
        cols = Counter(v[1] for v in R_[0]["viruses"])
        s = {"p_first": R_[0]["p"], "p_last": R_[-1]["p"], "pills": len(R_), "t_from": t_a, "t_to": t_b,
             "seconds": round(t_b - t_a, 1), "virus_count": R_[0]["virus_count"],
             "viruses_at_start": R_[0]["viruses"], "virus_columns": dict(cols),
             "above_viruses_at_start": R_[0]["above_viruses"], "above_viruses_at_end": R_[-1]["above_viruses"],
             "sealing_cells_by_provenance_start": seal(R_[0]), "sealing_cells_by_provenance_end": seal(R_[-1]),
             "pills_with_a_virus_clearing_move": sum(1 for q in R_ if q["n_vclear"] > 0),
             "silicon_cleared_when_available": sum(1 for q in R_ if q["n_vclear"] > 0 and q["silicon_cleared_virus"] > 0),
             "brain_would_clear_when_available": sum(1 for q in R_ if q["n_vclear"] > 0 and q["brain_clears_virus"] > 0),
             "silicon_eq_brain": sum(1 for q in R_ if q["category"] == "MATCH"),
             "categories": dict(Counter(q["category"] for q in R_)), "tucks": sum(1 for q in R_ if q["tuck"]),
             "maxh_start_end": [R_[0]["maxh"], R_[-1]["maxh"]],
             "garbage_cells_received": sum(q.get("garbage_new_cells", 0) for q in R_)}
        out["stalls"].append(s)
    with open(os.path.join(HERE, f"cases_stall_{GAME}_fair_20261004.jsonl"), "w") as fh:
        for q in rows:
            fh.write(json.dumps(q) + "\n")
    json.dump(out, open(os.path.join(HERE, f"stall_{GAME}_fair_20261004.json"), "w"), indent=1)
    print(json.dumps({k: v for k, v in out.items() if k != "stalls"}))
    for s in out["stalls"]:
        print(json.dumps({k: v for k, v in s.items() if not k.startswith("above")}))
        for k, seq in s["above_viruses_at_start"].items():
            print("   start virus", k, "above (row, cell, tag):", seq)
        for k, seq in s["above_viruses_at_end"].items():
            print("   end   virus", k, "above (row, cell, tag):", seq)


if __name__ == "__main__":
    main()
