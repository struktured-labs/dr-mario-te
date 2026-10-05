"""2026-10-04 couch, owner (P1) vs the FAIR bots (AI = P2), L11 MED. Owner question after match 3:
"it seemed more aggressive in the opening than fair2? any chance of that?"

Builds: FAIR  = cart dbbb5007 + rbf 318607aa (fw 1488e158): match 1 (rec 1) and match 3 (rec 2, 615-770 s)
        FAIR2 = cart b1b57638 + rbf V11 43aa62d5:           match 2 (rec 2, 42-546 s)

Input: scan2_fair_20261004.py 60 fps reads of BOTH bottles (geom_fair_20261004.json), re-tracked with the hidden-spawn
tracker (track_hidden_dist60_20261003.py) per bottle.

Per game:
  * AI SENDS, two independent instruments:
      sender side   = every AI placement's ROM comboCounter (matched runs summed over the cascade, endgame_dist60's
                      count_runs/resolve_runs) -> attack min(runs, 4) if runs >= 2, timed at the AI's next spawn;
      receiver side = garbage that appears on the OWNER's board (refit_sends_202610.volleys, verbatim extraction),
                      validated with the ROM attack-column rule (refit_sends_202610.rom_rule) and matched 1:1 to the
                      sender-side attacks (arrival = after the owner's next placement, ROM receiver timing).
  * Opening windows: first 60 s and 120 s of play, t0 = the first AI spawn (both bottles throw together).
  * Pace: placements/min and viruses cleared/min for both seats (virus counts from the settled boards).
  * Death: the frozen final owner board vs the last tracked owner board + its landing (P): the cells that arrived after
    the last placement are the killing volley; the loss condition is (0,3)/(0,4) occupied at the throw.

Usage: python fair_20261004.py track     (rawh_* into the tmp scan dir; mech_check gates)
       python fair_20261004.py analyze   (cases_fair_20261004*.jsonl, summary_fair_20261004.json, printed tables)
"""
from __future__ import annotations

import json
import os
import statistics as st
import subprocess
import sys
from collections import Counter

import numpy as np

import mech_check as MC
import refit_sends_202610 as RS

HERE = os.path.dirname(os.path.abspath(__file__))
SCAN = os.path.expanduser("~/projects/dr_mario_rl/tmp/fair_20261004/scan")
PY = sys.executable
ROWS, COLS = 16, 8

# name, build, match, game, rec, log (owner-left / AI-left, result as logged)
GAMES = [
    ("m1g1", "FAIR", 1, 1, 1, "AI full clear, owner 17 / AI 0"),
    ("m1g2", "FAIR", 1, 2, 1, "owner tapped out 25 / 5"),
    ("m2g1", "FAIR2", 2, 1, 2, "owner tapped out 42 / 27"),
    ("m2g2", "FAIR2", 2, 2, 2, "owner topped out 32 / AI 1 (logged as a full clear; the recording shows 1 virus left)"),
    ("m2g3", "FAIR2", 2, 3, 2, "owner tapped out 19 / 4"),
    ("m3g1", "FAIR", 3, 1, 2, "owner topped out 42 / 26 ('garbage killed the spawn cells')"),
    ("m3g2", "FAIR", 3, 2, 2, "owner out 43 / 33 ('I messed up')"),
    ("m3g3", "FAIR", 3, 3, 2, "owner out 44 / 31 ('messed up again')"),
    ("m4g1", "FAIR2", 4, 1, 2, "AI full clear, owner at 5 (race loss)"),
    ("m4g2", "FAIR2", 4, 2, 2, "AI TAPPED OUT, owner 12 / AI 16"),
]


# ---- ROM comboCounter (copied from endgame_dist60_20261003.count_runs / resolve_runs; that module imports the decider)
def count_runs(g):
    n = 0
    for r in range(ROWS):
        c = 0
        while c < COLS:
            v = g[r, c]; c2 = c
            while c2 + 1 < COLS and g[r, c2 + 1] == v:
                c2 += 1
            if v != 0 and c2 - c + 1 >= 4:
                n += 1
            c = c2 + 1
    for c in range(COLS):
        r = 0
        while r < ROWS:
            v = g[r, c]; r2 = r
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


def placed(r):
    """S_k + landing, unresolved (mech_check.after_pill without the resolve)."""
    b = MC.A.board_from_strings(r["S"]["color"], r["S"]["virus"], r["S"]["link"])
    o, orow, ocol, ocl = r["landing"]
    if o == "H":
        b.color[orow, ocol], b.color[orow, ocol + 1] = ocl
        b.link[orow, ocol], b.link[orow, ocol + 1] = 4, 3
        b.is_virus[orow, ocol] = b.is_virus[orow, ocol + 1] = False
    else:
        b.color[orow, ocol], b.color[orow + 1, ocol] = ocl
        b.link[orow, ocol], b.link[orow + 1, ocol] = 2, 1
        b.is_virus[orow, ocol] = b.is_virus[orow + 1, ocol] = False
    return b


def grid(s):
    return np.array([int(ch) for ch in s]).reshape(ROWS, COLS)


def heights(C):
    h = []
    for c in range(COLS):
        top = next((r for r in range(ROWS) if C[r, c] > 0), ROWS)
        h.append(ROWS - top)
    return h


# ---------------------------------------------------------------------------------------------------- track
def track():
    for g, *_ in GAMES:
        for seat in ("p1", "p2"):
            fr = os.path.join(SCAN, f"f60_{g}_{seat}.jsonl")
            out = os.path.join(SCAN, f"rawh_{g}_{seat}.jsonl")
            subprocess.run([PY, os.path.join(HERE, "track_hidden_dist60_20261003.py"), fr, out], check=True)


# ---------------------------------------------------------------------------------------------------- game window
def frames(g, seat):
    return [json.loads(l) for l in open(os.path.join(SCAN, f"f60_{g}_{seat}.jsonl"))]


def window(g):
    """t_round = first frame with a full virus field and a non-zero preview on both seats; t_end = first frame after
    play started where both previews read (0,0) for >= 60 consecutive frames (game over).
    final[seat] = the board 3 frames before game over (the failed capsule is drawn over the spawn cells 1-2 frames
    before the previews blank, so the plug is read before it), and the final virus count (min over the last 3 s: clear
    pops read as virus-like, never the reverse; a full clear's end animation reads as viruses, so analyze() sets the
    AI's count to 0 where the AI full-cleared, which the log and the recording agree on)."""
    A, B = frames(g, "p1"), frames(g, "p2")
    n = min(len(A), len(B))
    t_round = next(A[i]["t"] for i in range(n) if 0 not in A[i]["prev"] and 0 not in B[i]["prev"]
                   and A[i]["virus"].count("1") >= 40)
    i0 = next(i for i in range(n) if A[i]["t"] >= t_round)
    t_end = None
    for i in range(i0, n - 60):
        if all(tuple(A[j]["prev"]) == (0, 0) and tuple(B[j]["prev"]) == (0, 0) for j in range(i, i + 60)):
            t_end = A[i]["t"]; i_end = i
            break
    if t_end is None:
        return t_round, None, None
    final = {}
    for seat, F in (("p1", A), ("p2", B)):
        # 3 frames before game over: the killing lock / garbage has landed, the failed capsule is not drawn yet (it is
        # drawn 1-2 frames before the previews blank, with or without a preview change: 10/04 M3 G1 vs M3 G2)
        final[seat] = dict(F[i_end - 3], t_last_throw=F[i_end - 3]["t"],
                           virus_final=min(F[i]["virus"].count("1") for i in range(max(i0, i_end - 180), i_end - 2)))
    return t_round, t_end, final


def _enc(a):
    return "".join(str(int(v)) for v in np.asarray(a).ravel())


def _explains(r, nxt):
    try:
        return MC.explain(r, nxt) is not None
    except Exception:
        return False


def repair(R):
    """Fix the tracker's clear-pop artefact (seen 10/04 M4 G2 p21): when the next capsule appears while the previous
    clear's pop tiles are still drawn, settled_at_spawn can return a board that still holds a capsule half at the top
    ('NOCAPSULE') and the trajectory reads the hovering capsule as a row-0 'landing'.
    (1) 'NOCAPSULE' boards: drop FLOATING cells in rows 0-2 (occupied over an empty cell: impossible on a settled board).
    (2) a landing that mech_check cannot explain against the next board, a spawn-cell 'landing' whose trajectory never
        left the spawn cells, or a MISSING landing (trajectory lost, e.g. 10/04 M3 G1 AI k10, a 5-s cascade + garbage
        step) is re-derived: every resting (H/V, row, col, colour order) pose of cur on the cleaned board, first one
        that explains S_{k+1} (exact preferred; a spawn-cell landing is only replaced by an exact one).
    Returns the list of repairs (banked in the summary)."""
    fixes = []
    for k, r in enumerate(R):
        if "NOCAPSULE" in r["S"]["src"]:
            C, V, L = grid(r["S"]["color"]), grid(r["S"]["virus"]), grid(r["S"]["link"])
            changed = True; removed = []
            while changed:
                changed = False
                for rr in range(0, 3):
                    for c in range(COLS):
                        held = ((L[rr, c] == 4 and c + 1 < COLS and C[rr, c + 1] > 0 and C[rr + 1, c + 1] > 0) or
                                (L[rr, c] == 3 and c - 1 >= 0 and C[rr, c - 1] > 0 and C[rr + 1, c - 1] > 0))
                        if C[rr, c] > 0 and C[rr + 1, c] == 0 and not held:
                            removed.append((rr, c, int(C[rr, c]))); C[rr, c] = 0; V[rr, c] = 0; L[rr, c] = 0; changed = True
            if removed:
                r["S"] = dict(r["S"], color=_enc(C), virus=_enc(V), link=_enc(L), src=r["S"]["src"] + " REPAIRED_FLOAT")
                r["virus_count"] = int(V.sum())
                fixes.append({"k": r["k"], "t": r["t_spawn"], "fix": "float_removed", "cells": removed})
    for k, r in enumerate(R):
        if k + 1 >= len(R):
            continue
        exact_only = False
        if r["landing"] is not None:          # (a record with NO landing -- trajectory lost -- goes straight to the search)
            o0, row0, c0, _ = r["landing"]
            at_spawn = (o0 == "H" and row0 == 0 and c0 == 3 and all(p[1] == "H" and p[2] == 0 and p[3] == 3 for p in r["traj"]))
            if at_spawn:
                exact_only = True             # a 'landing' that never left the spawn cells while the next board shows play
            elif _explains(r, R[k + 1]):
                continue
        C = grid(r["S"]["color"]); N = grid(R[k + 1]["S"]["color"])
        cur = tuple(r["cur"]); cands = []
        for o in ("H", "V"):
            for row in range(ROWS):
                for c in range(COLS):
                    cells = [(row, c), (row, c + 1)] if o == "H" else [(row, c), (row + 1, c)]
                    if any(rr >= ROWS or cc >= COLS or C[rr, cc] > 0 for rr, cc in cells):
                        continue
                    below = [(rr + 1, cc) for rr, cc in cells if (rr + 1, cc) not in cells]
                    if not any(rr >= ROWS or C[rr, cc] > 0 for rr, cc in below):
                        continue
                    for cl in {cur, cur[::-1]}:
                        cands.append([o, row, c, list(cl)])
        best = None
        for land in cands:
            q = dict(r, landing=land)
            P = MC.after_pill(q)
            if np.array_equal(P.color, N):
                best = (land, "exact"); break
        if best is None and exact_only:
            continue                          # keep the spawn-cell landing (a real lock at spawn, e.g. the death pill)
        if best is None:
            Nocc = N > 0
            for land in cands:
                P = MC.after_pill(dict(r, landing=land))
                if int(((P.color > 0) != Nocc).sum()) > 8:      # cheap pre-filter: a volley adds <= 4 cells (+ its clears)
                    continue
                if _explains(dict(r, landing=land), R[k + 1]):
                    best = (land, "garbage"); break
        if best is not None:
            fixes.append({"k": r["k"], "t": r["t_spawn"], "fix": "landing_rederived", "old": r["landing"], "new": best[0],
                          "how": best[1]})
            r["landing"] = best[0]; r["landing_repaired"] = True
        else:
            fixes.append({"k": r["k"], "t": r["t_spawn"], "fix": "unexplained_kept", "landing": r["landing"]})
    return fixes


def load_raw(g, seat, t_round, t_end, with_fixes=False):
    R = [json.loads(l) for l in open(os.path.join(SCAN, f"rawh_{g}_{seat}.jsonl"))]
    R = [r for r in R if 0 not in r["cur"] and 0 not in r["nxt"] and t_round <= r["t_spawn"] <= t_end]
    fixes = repair(R)
    R = [r for r in R if r["landing"] is not None]
    return (R, fixes) if with_fixes else R


# ---------------------------------------------------------------------------------------------------- analysis
def ai_attacks(R2, t0):
    """Sender side, per AI placement (BANKED as per-pill cases)."""
    cases, att = [], []
    for k, r in enumerate(R2):
        b = placed(r)
        steps = resolve_runs(b)
        runs = sum(s["runs"] for s in steps)
        sent = min(runs, 4) if runs >= 2 else 0
        Cs = grid(r["S"]["color"])
        t_lock = r["t_next_spawn"] if r["t_next_spawn"] is not None else r["t_spawn"]
        c = {"k": k, "t_spawn": r["t_spawn"], "t_rel": round(r["t_spawn"] - t0, 3), "spawn_kind": r.get("spawn_kind"),
             "cur": r["cur"], "landing": r["landing"], "virus_count": r["virus_count"],
             "max_h_before": max(heights(Cs)), "cells": sum(s["cells"] for s in steps),
             "viruses": sum(s["viruses"] for s in steps), "chain": len(steps), "runs": runs, "sent": sent,
             "steps": steps, "traj_frames": len(r["traj"]), "src": r["S"]["src"]}
        cases.append(c)
        if sent:
            att.append({"k": k, "t_send": t_lock, "t_rel": round(t_lock - t0, 3), "size": sent, "runs": runs,
                        "chain": len(steps), "viruses": c["viruses"]})
    return cases, att


def owner_side(R1, t0):
    vol, _ = RS.volleys(R1)
    for v in vol:
        v["t_rel"] = round(v["t"] - t0, 3)
    pills = []
    for k, r in enumerate(R1):
        b = placed(r)
        steps = resolve_runs(b)
        Cs = grid(r["S"]["color"])
        h = heights(Cs)
        pills.append({"k": k, "t_spawn": r["t_spawn"], "t_rel": round(r["t_spawn"] - t0, 3), "cur": r["cur"],
                      "landing": r["landing"], "virus_count": r["virus_count"], "heights_before": h,
                      "max_h_before": max(h), "h34_before": [h[3], h[4]],
                      "cells": sum(s["cells"] for s in steps), "viruses": sum(s["viruses"] for s in steps),
                      "runs": sum(s["runs"] for s in steps), "src": r["S"]["src"]})
    return vol, pills


def match_attacks(att, vol):
    """Reconcile sender-side attacks with owner-board volleys under the ROM's ACCUMULATION rule (rom_attack_rule:
    attackSize += comboCounter until the receiver's next checkAttack releases it, size >= 4 -> 4 tiles): every attack
    is assigned to the first owner-board volley arriving at or after it (<= 8 s); a volley's expected size is
    min(sum of its attacks, 4). Attacks with no later volley are 'in flight' (the owner topped out first).
    Returns (pairs [(attack, volley|None)], groups [(volley, [attacks])], unmatched received volleys)."""
    V = [v for v in vol if v["size"]]
    groups = {id(v): [] for v in V}
    pairs = []
    for a in att:
        v = next((v for v in V if v["t"] >= a["t_send"] - 0.2 and v["t"] - a["t_send"] <= 8.0), None)
        if v is not None:
            groups[id(v)].append(a)
        pairs.append((a, v))
    G = [(v, groups[id(v)]) for v in V]
    unmatched = [v for v, g in G if not g]
    return pairs, G, unmatched


def vcount_at(cases, t, final_v):
    """Virus count on the settled board at time t (the last placement starting at or before t)."""
    prior = [c for c in cases if c["t_spawn"] <= t]
    nxt = [c for c in cases if c["t_spawn"] > t]
    if nxt:
        return nxt[0]["virus_count"]
    return final_v


def death(seat_final, R, vol):
    """The seat's state at its last throw. plug = (0,3)/(0,4) occupied on the board just before the throw (ROM: the only
    loss condition). Provenance: P = the last placement before that throw, resolved (mech_check.after_pill); a plug cell
    absent from P arrived afterwards = GARBAGE; present in P = already there (own pill, or older garbage: see link)."""
    if seat_final is None or not R:
        return None
    t_thr = seat_final["t_last_throw"]
    prior = [r for r in R if r["t_spawn"] < t_thr - 0.05]
    last = prior[-1]
    P = MC.after_pill(last)
    F = grid(seat_final["color"]); L = grid(seat_final["link"])
    extras = [(int(a), int(c), int(F[a, c])) for a, c in np.argwhere((F > 0) & (P.color == 0))]
    plug = [(0, c) for c in (3, 4) if F[0, c] > 0]
    newc = {(a, c) for a, c, _ in extras}
    # a new cell with a horizontally/vertically adjacent new cell of the same colour is a capsule (a lock after the last
    # tracked placement), not garbage: ROM volleys are unlinked singles at least 2 columns apart (rom_attack_rule)
    pill_like = {(a, c) for (a, c) in newc for (da, dc) in ((0, 1), (0, -1), (1, 0), (-1, 0))
                 if (a + da, c + dc) in newc and F[a + da, c + dc] == F[a, c]}
    plug_garbage = [(0, c) for (_, c) in plug if P.color[0, c] == 0 and (0, c) not in pill_like]
    plug_new_pill = [(0, c) for (_, c) in plug if (0, c) in pill_like]
    plug_present_before = [(0, c, "linked" if L[0, c] else "single") for (_, c) in plug if P.color[0, c] > 0]
    h = heights(F)
    g34 = sum(1 for v in vol if v["size"] for c in v["cols"] if c in (3, 4))
    return {"t_last_throw": t_thr, "t_last_placement": last["t_spawn"], "last_landing": last["landing"],
            "heights_at_death": h, "max_h": max(h), "h34": [h[3], h[4]],
            "virus_final": seat_final["virus_final"], "cells": int((F > 0).sum()),
            "plug": plug, "plug_by_garbage_after_last_placement": plug_garbage, "plug_by_untracked_last_pill": plug_new_pill,
            "plug_present_before": plug_present_before,
            "cells_arrived_after_last_placement": extras,
            "garbage_volleys_with_a_cell_in_cols34": sum(1 for v in vol if v["size"] and any(c in (3, 4) for c in v["cols"])),
            "garbage_cells_into_cols34_all_game": g34}


def per_window(att, vol, cases2, pills1, t0, t_end, w, final_v2, final_v1, vol_recv_by_ai):
    hi = min(t0 + w, t_end); mins = (hi - t0) / 60.0
    A = [a for a in att if a["t_send"] <= hi]
    V = [v for v in vol if v["size"] and v["t"] <= hi]
    P2 = [c for c in cases2 if c["t_spawn"] <= hi]
    P1 = [c for c in pills1 if c["t_spawn"] <= hi]
    v2_0 = cases2[0]["virus_count"] if cases2 else None
    v1_0 = pills1[0]["virus_count"] if pills1 else None
    v2_hi = vcount_at(cases2, hi, final_v2); v1_hi = vcount_at(pills1, hi, final_v1)
    Vo = [v for v in vol_recv_by_ai if v["size"] and v["t"] <= hi]
    return {"window_s": w, "covered_s": round(hi - t0, 1), "game_shorter": t_end < t0 + w,
            "ai_sent_volleys": len(A), "ai_sent_cells": sum(a["size"] for a in A),
            "ai_sent_volleys_per_min": round(len(A) / mins, 2), "ai_sent_cells_per_min": round(sum(a["size"] for a in A) / mins, 2),
            "owner_recv_volleys": len(V), "owner_recv_cells": sum(v["size"] for v in V),
            "owner_recv_volleys_per_min": round(len(V) / mins, 2),
            "ai_pills": len(P2), "ai_pills_per_min": round(len(P2) / mins, 2),
            "ai_viruses_cleared": (v2_0 - v2_hi) if v2_0 is not None else None,
            "ai_viruses_per_min": round((v2_0 - v2_hi) / mins, 2) if v2_0 is not None else None,
            "ai_combo_placements": sum(1 for c in P2 if c["runs"] >= 2),
            "owner_pills": len(P1), "owner_pills_per_min": round(len(P1) / mins, 2),
            "owner_viruses_cleared": (v1_0 - v1_hi) if v1_0 is not None else None,
            "owner_viruses_per_min": round((v1_0 - v1_hi) / mins, 2) if v1_0 is not None else None,
            "owner_sent_volleys": len(Vo), "owner_sent_cells": sum(v["size"] for v in Vo)}


def layout(R2):
    """Initial virus layout (identical for both seats in 2P): virus rows/columns."""
    if not R2:
        return None
    C = grid(R2[0]["S"]["color"]); V = grid(R2[0]["S"]["virus"]).astype(bool)
    rows = [int(r) for r, c in np.argwhere(V)]
    return {"viruses": int(V.sum()), "top_virus_row": min(rows) if rows else None,
            "viruses_rows_le_8": sum(1 for r in rows if r <= 8),
            "viruses_cols34": int(V[:, 3:5].sum()), "viruses_cols34_rows_le_8": int(V[:9, 3:5].sum())}


def analyze():
    out_games, cases_ai, cases_owner, cases_vol = [], [], [], []
    for g, build, m, gi, rec, log in GAMES:
        t_round, t_end, final = window(g)
        R2 = load_raw(g, "p2", t_round, t_end); R1 = load_raw(g, "p1", t_round, t_end)
        t0 = R2[0]["t_spawn"]
        mech2 = [MC.explain(R2[i], R2[i + 1]) for i in range(len(R2) - 1)]
        mech1 = [MC.explain(R1[i], R1[i + 1]) for i in range(len(R1) - 1)]
        c2, att = ai_attacks(R2, t0)
        vol, pills1 = owner_side(R1, t0)
        vol_ai, _ = RS.volleys(R2)                         # owner -> AI sends, received by the AI
        pairs, groups, unrecv = match_attacks(att, vol)
        fv2 = 0 if "AI full clear" in log else final["p2"]["virus_final"]; fv1 = final["p1"]["virus_final"]
        dth = {"owner": death(final["p1"], R1, vol), "ai": death(final["p2"], R2, RS.volleys(R2)[0])}
        dur = t_end - t0
        W = {str(w): per_window(att, vol, c2, pills1, t0, t_end, w, fv2, fv1, vol_ai) for w in (30, 60, 120)}
        W["all"] = per_window(att, vol, c2, pills1, t0, t_end, 1e9, fv2, fv1, vol_ai)
        sizes_sent = Counter(a["size"] for a in att)
        sizes_recv = Counter(v["size"] for v in vol if v["size"])
        row = {"game": g, "build": build, "match": m, "g": gi, "rec": rec, "log": log,
               "t_round": t_round, "t0_first_spawn": t0, "t_end": t_end, "dur_s": round(dur, 1),
               "ai_placements": len(R2), "owner_placements": len(R1),
               "hidden_spawns_ai": sum(1 for r in R2 if r.get("spawn_kind") == "hidden"),
               "hidden_spawns_owner": sum(1 for r in R1 if r.get("spawn_kind") == "hidden"),
               "mech_gate_ai": {"steps": len(mech2), "exact": sum(1 for v in mech2 if v == 0),
                                "garbage": sum(1 for v in mech2 if v not in (None, 0)), "unexplained": sum(1 for v in mech2 if v is None)},
               "mech_gate_owner": {"steps": len(mech1), "exact": sum(1 for v in mech1 if v == 0),
                                   "garbage": sum(1 for v in mech1 if v not in (None, 0)), "unexplained": sum(1 for v in mech1 if v is None)},
               "final_virus_owner": fv1, "final_virus_ai": fv2,
               "layout": layout(R2),
               "ai_first_send_s": att[0]["t_rel"] if att else None,
               "owner_first_recv_s": next((v["t_rel"] for v in vol if v["size"]), None),
               "ai_sent_sizes": {str(k): v for k, v in sorted(sizes_sent.items())},
               "owner_recv_sizes": {str(k): v for k, v in sorted(sizes_recv.items())},
               "rom_column_rule_owner_recv": RS.rom_rule(vol),
               "sender_receiver_match": {"sent": len(att), "assigned_to_a_volley": sum(1 for a, v in pairs if v),
                                         "in_flight_at_end": sum(1 for a, v in pairs if v is None),
                                         "recv_volleys": len(groups),
                                         "recv_size_eq_min(sum,4)": sum(1 for v, g in groups if g and v["size"] == min(sum(a["size"] for a in g), 4)),
                                         "recv_with_merged_sends": sum(1 for v, g in groups if len(g) >= 2),
                                         "recv_unmatched": len(unrecv),
                                         "recv_unexplained": sum(1 for v in vol if not v["size"]),
                                         "lag_s_median": (round(st.median([v["t"] - a["t_send"] for a, v in pairs if v]), 2)
                                                          if any(v for a, v in pairs) else None)},
               "windows": W, "death": dth}
        out_games.append(row)
        for c in c2:
            cases_ai.append({"game": g, "build": build, **c})
        for p in pills1:
            cases_owner.append({"game": g, "build": build, **p})
        for a, v in pairs:
            cases_vol.append({"game": g, "build": build, "kind": "ai_send", **a,
                              "recv": ({k: v[k] for k in ("t", "t_rel", "size", "how", "cols", "n_cols")} if v else None)})
        for v, gr in groups:
            cases_vol.append({"game": g, "build": build, "kind": "owner_recv", **{k: v[k] for k in ("t", "t_rel", "size", "how", "cols", "n_cols")},
                              "sends": [a["k"] for a in gr], "expected_size": min(sum(a["size"] for a in gr), 4) if gr else None,
                              "rom_cols_ok": RS.rom_rule([v])["conform"] == 1, "rom_cols_checkable": sum(RS.rom_rule([v]).values()) == 1})
        for v in vol_ai:
            cases_vol.append({"game": g, "build": build, "kind": "owner_send_recv_by_ai", **v, "t_rel": round(v["t"] - t0, 3)})
    w = lambda name, rows: open(os.path.join(HERE, name), "w").write("".join(json.dumps(r) + "\n" for r in rows))
    w("cases_fair_20261004_ai_pills.jsonl", cases_ai)
    w("cases_fair_20261004_owner_pills.jsonl", cases_owner)
    w("cases_fair_20261004_volleys.jsonl", cases_vol)
    cmp_ = compare(out_games)
    json.dump({"games": out_games, "compare": cmp_}, open(os.path.join(HERE, "summary_fair_20261004.json"), "w"), indent=1)
    report(out_games)
    print_compare(cmp_)


METRICS = ("ai_sent_volleys", "ai_sent_cells", "ai_sent_volleys_per_min", "ai_sent_cells_per_min", "owner_recv_volleys",
           "owner_recv_cells", "ai_pills_per_min", "ai_viruses_per_min", "owner_pills_per_min", "owner_viruses_per_min",
           "owner_sent_volleys")


def perm_p(a, b):
    """Exact two-sided permutation p for the difference in means (all splits of the pooled games)."""
    import itertools
    x = a + b; n = len(a); obs = abs(st.mean(a) - st.mean(b)); hit = tot = 0
    for idx in itertools.combinations(range(len(x)), n):
        A_ = [x[i] for i in idx]; B_ = [x[i] for i in range(len(x)) if i not in idx]
        hit += abs(st.mean(A_) - st.mean(B_)) >= obs - 1e-12; tot += 1
    return round(hit / tot, 3)


def compare(G):
    """FAIR vs FAIR2 per window: per-game values, means, exact permutation p (game = unit), pooled rates.
    Sets: 'all' = FAIR (M1 + M3) vs FAIR2 (M2 + M4); 'asked' = M3 (FAIR) vs M2 (FAIR2), the owner's comparison."""
    sets = {"all": (lambda r: r["build"] == "FAIR", lambda r: r["build"] == "FAIR2"),
            "asked_M3_vs_M2": (lambda r: r["match"] == 3, lambda r: r["match"] == 2)}
    out = {}
    for sname, (fa, fb) in sets.items():
        A_ = [r for r in G if fa(r)]; B_ = [r for r in G if fb(r)]
        out[sname] = {"FAIR_games": [r["game"] for r in A_], "FAIR2_games": [r["game"] for r in B_]}
        for wk in ("30", "60", "120", "all"):
            d = {}
            for m in METRICS:
                a = [r["windows"][wk][m] for r in A_]; b = [r["windows"][wk][m] for r in B_]
                d[m] = {"FAIR": a, "FAIR2": b, "mean_FAIR": round(st.mean(a), 2), "mean_FAIR2": round(st.mean(b), 2),
                        "perm_p": perm_p(a, b)}
            mins_a = sum(r["windows"][wk]["covered_s"] for r in A_) / 60; mins_b = sum(r["windows"][wk]["covered_s"] for r in B_) / 60
            d["pooled_ai_sent_volleys_per_min"] = {"FAIR": round(sum(r["windows"][wk]["ai_sent_volleys"] for r in A_) / mins_a, 2),
                                                   "FAIR2": round(sum(r["windows"][wk]["ai_sent_volleys"] for r in B_) / mins_b, 2),
                                                   "minutes": [round(mins_a, 2), round(mins_b, 2)]}
            out[sname][wk] = d
        fs = lambda R_: [r["ai_first_send_s"] for r in R_]
        out[sname]["first_send_s"] = {"FAIR": fs(A_), "FAIR2": fs(B_), "perm_p": perm_p(fs(A_), fs(B_))}
    return out


def print_compare(C):
    for sname, d in C.items():
        print(f"\n== {sname}: FAIR {d['FAIR_games']} vs FAIR2 {d['FAIR2_games']}")
        print(f"   first AI send (s): FAIR {d['first_send_s']['FAIR']} vs FAIR2 {d['first_send_s']['FAIR2']}  perm p {d['first_send_s']['perm_p']}")
        for wk in ("30", "60", "120", "all"):
            x = d[wk]
            print(f"   window {wk}: pooled AI volleys/min FAIR {x['pooled_ai_sent_volleys_per_min']['FAIR']} vs FAIR2 "
                  f"{x['pooled_ai_sent_volleys_per_min']['FAIR2']} (min {x['pooled_ai_sent_volleys_per_min']['minutes']})")
            for m in ("ai_sent_volleys", "ai_sent_volleys_per_min", "owner_recv_cells", "ai_pills_per_min", "ai_viruses_per_min",
                      "owner_pills_per_min", "owner_viruses_per_min", "owner_sent_volleys"):
                y = x[m]
                print(f"      {m:26s} FAIR {y['FAIR']} (mean {y['mean_FAIR']}) | FAIR2 {y['FAIR2']} (mean {y['mean_FAIR2']}) | perm p {y['perm_p']}")


def report(G):
    print("game  build  dur  AIpl ownpl | gate AI ex/garb/unexpl | gate own | final own/AI | first send | sent sizes | recv sizes | ROM | match")
    for r in G:
        a, o = r["mech_gate_ai"], r["mech_gate_owner"]
        print(f"{r['game']} {r['build']:5s} {r['dur_s']:6.1f} {r['ai_placements']:4d} {r['owner_placements']:4d} | "
              f"{a['exact']}/{a['garbage']}/{a['unexplained']} of {a['steps']} | {o['exact']}/{o['garbage']}/{o['unexplained']} of {o['steps']} | "
              f"{r['final_virus_owner']}/{r['final_virus_ai']} | {r['ai_first_send_s']} / {r['owner_first_recv_s']} | "
              f"{r['ai_sent_sizes']} | {r['owner_recv_sizes']} | {r['rom_column_rule_owner_recv']} | {r['sender_receiver_match']}")
    for wk in ("30", "60", "120", "all"):
        print(f"\n-- window {wk} s: game build covered | AI sent vol (cells) /min | owner recv vol | AI pills/min vir/min combos | owner pills/min vir/min | owner sent vol")
        for r in G:
            x = r["windows"][wk]
            print(f"{r['game']} {r['build']:5s} {x['covered_s']:6.1f}{'*' if x['game_shorter'] else ' '} | "
                  f"{x['ai_sent_volleys']:2d} ({x['ai_sent_cells']:2d}) {x['ai_sent_volleys_per_min']:5.2f}/{x['ai_sent_cells_per_min']:5.2f} | "
                  f"{x['owner_recv_volleys']:2d} ({x['owner_recv_cells']:2d}) | {x['ai_pills_per_min']:5.1f} {x['ai_viruses_per_min']:5.1f} {x['ai_combo_placements']:2d} | "
                  f"{x['owner_pills_per_min']:5.1f} {x['owner_viruses_per_min']:5.1f} | {x['owner_sent_volleys']} ({x['owner_sent_cells']})")
    print("\n-- death: seat whose spawn cells were plugged at its last throw")
    for r in G:
        for who in ("owner", "ai"):
            d = r["death"][who]
            if d and d["plug"]:
                print(r["game"], r["build"], who, json.dumps({k: d[k] for k in ("t_last_throw", "h34", "max_h", "virus_final", "plug",
                                                                              "plug_by_garbage_after_last_placement", "plug_by_untracked_last_pill", "plug_present_before",
                                                                              "cells_arrived_after_last_placement",
                                                                              "garbage_volleys_with_a_cell_in_cols34")}))
    print("\n-- layouts")
    for r in G:
        print(r["game"], r["build"], r["layout"])


if __name__ == "__main__":
    {"track": track, "analyze": analyze}[sys.argv[1]]()
