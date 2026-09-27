"""Couch-death forensics, 2026-09-25 G2 (CHAIN540 core, AI = P2): per placement, the sim's copy of the
brain (vs_race._decider("fw540") internals: StrandedChainD3Decider w_chain=540 ws=20 topk2=8
maxpass=0) vs where the capsule actually landed on silicon.

  python analyze_g2.py gate2                         # decider-plumbing gate (no video needed)
  python analyze_g2.py run PLACEMENTS.jsonl OUT.jsonl

GATE 2: replay a banked gate-(b) fw540 game, round-trip every board through the SAME string encoding
+ constructor used for video boards, and require the decider to return the identical action.

Per placement it also records:
  * mechanics cross-check: S_k + observed landing + faithful resolve() must be contained in S_{k+1}
    (extra cells = opponent garbage; missing/changed cells = reader or mechanics mismatch)
  * straight-drop test: is the landing a straight-drop resting position (the sim's action space)?
  * video timing: frames spawn -> first lateral move, per-column lateral gaps, rotations
  * DISTGATE budget (couch cart: DIST_TABLE[y] = 0 if y==0 else max(1, min(7, (30*y)//12)), y = fully
    empty rows below the capsule across [spawn col .. target col]), evaluated at spawn for the sim's
    target: is the target within the steering clamp?
  * DAS-carry counterfactual (ROM $8DCF): no-carry driver path vs carry path, see _reach().
"""
from __future__ import annotations

import json
import os
import sys

import numpy as np

CVX = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "cvx")
sys.path.insert(0, os.path.abspath(CVX))
import import_pin  # noqa: E402

import_pin.pin()
from drmario.faithful_game import FaithfulBoard, Pill, ORIENT_H, ORIENT_V  # noqa: E402

ROWS, COLS = 16, 8


def enc(a):
    return "".join(str(int(v)) for v in np.asarray(a).ravel())


def board_from_strings(color, virus, link):
    b = FaithfulBoard(ROWS, COLS)
    b.color = np.array([int(ch) for ch in color], np.int8).reshape(ROWS, COLS)
    b.is_virus = np.array([ch == "1" for ch in virus], bool).reshape(ROWS, COLS)
    b.link = np.array([int(ch) for ch in link], np.int8).reshape(ROWS, COLS)
    return b


_DEC = None


def decider():
    global _DEC
    if _DEC is None:
        import fast_rtl_x as FX
        import cascade_chain_x as C
        import cascade_stranded_x as S
        C.warmup_chain(topk2=8)
        w, fl = FX.variant("winner")
        _DEC = S.StrandedChainD3Decider(w, fl, topk2=8, maxpass=0, w_chain=540, ws=20)
    return _DEC


def decode(action, cur):
    """Sim action -> (orient 'H'|'V', col, colours in board order (left,right)|(top,bottom))."""
    var, col = action // COLS, action % COLS
    a, b = cur
    return {0: ("H", col, (a, b)), 1: ("H", col, (b, a)), 2: ("V", col, (a, b)), 3: ("V", col, (b, a))}[var]


def resting(board, orient, col):
    o = ORIENT_H if orient == "H" else ORIENT_V
    cells = board.resting_position(Pill(1, 1), o, col)
    return None if cells is None else cells[0]


# ------------------------------------------------------------------------------------------ gate 2
def gate2(seed=36734, n_pills=None):
    import gate_b as G
    import bursty_model as BM
    import vs_race as V
    model = BM.fit_struktured_20260804()
    choose_real = V._decider("fw540")
    log = []

    def choose(env, col, vir, ctx):
        a = choose_real(env, col, vir, ctx)
        log.append((enc(env.board.color), enc(env.board.is_virus.astype(int)), enc(env.board.link),
                    (int(env.cur.a), int(env.cur.b)), (int(env.nxt.a), int(env.nxt.b)), a))
        return a

    G.play(seed, None, model, choose=choose)
    dec = decider()
    same = 0
    for (c, v, l, cur, nxt, a) in log[:n_pills]:
        b = board_from_strings(c, v, l)
        a2 = dec.choose(b, Pill(*cur), Pill(*nxt))
        same += int(a2 == a)
    n = len(log[:n_pills])
    linked = sum(1 for (c, v, l, *_rest) in log if any(ch != "0" for ch in l))
    print(f"GATE2 seed {seed}: {same}/{n} identical actions via string round-trip + constructor "
          f"({linked} boards carried links)")
    return same == n


# ------------------------------------------------------------------------------------- per-placement
def _dist_budget(S, col_from, col_to, row):
    lo, hi = min(col_from, col_to), max(col_from, col_to)
    y = 0
    for r in range(row + 1, ROWS):
        if all(S[r, c] == 0 for c in range(lo, hi + 1)):
            y += 1
        else:
            break
    return 0 if y == 0 else max(1, min(7, (30 * y) // 12)), y


def _reach(S, target_col, think_f=6, engage_f=16, rep_f=6, grav_f=15, carry_v=None):
    """Can the capsule reach target_col (horizontal, left half) before it can fall no further?
    Fall budget = frames until the capsule sits on the stack along the straight path: rows of free fall
    below spawn row 0 over the span, times grav_f (natural gravity; measured ~15 f/row near topout).
    No-carry driver: think_f, then 1 col at press, 2nd col after engage_f, then every rep_f.
    Carry (ROM $8DCF, horVelocity carried): first col after (16 - v) frames, then every rep_f."""
    d = abs(target_col - 3)
    if d == 0:
        return True, 0, 0
    _, y = _dist_budget(S, 3, target_col, 0)
    fall = y * grav_f + grav_f            # frames until lock from the spawn row (incl. the lock frame)
    if carry_v is None:
        need = think_f + (0 if d == 1 else engage_f + (d - 2) * rep_f)
    else:
        need = (16 - carry_v) + (d - 1) * rep_f
    return need <= fall, need, fall


def analyze(placements_path, out_path):
    R = [json.loads(l) for l in open(placements_path)]
    dec = decider()
    rows = []
    for idx, r in enumerate(R):
        if r["landing"] is None or 0 in r["cur"] or 0 in r["nxt"]:
            continue                      # no capsule track, or a game-start/-end spawn (pill/preview blank)
        S = r["S"]
        b = board_from_strings(S["color"], S["virus"], S["link"])
        Sc = b.color.copy()
        cur = tuple(r["cur"]); nxt = tuple(r["nxt"])
        # ---- link sanity on the video board
        from reader import link_consistent
        lviol = link_consistent(b.color, b.link)
        # ---- sim choice
        a = dec.choose(b.clone(), Pill(*cur), Pill(*nxt))
        sim = decode(a, cur) if a is not None else None
        sim_row = resting(b, sim[0], sim[1]) if sim else None
        # ---- observed
        o, orow, ocol, ocolours = r["landing"]
        act_rest = resting(b, o, ocol)
        straight = act_rest is not None and act_rest[0] == orow
        match = sim is not None and sim[0] == o and sim[1] == ocol and tuple(sim[2]) == tuple(ocolours) and sim_row[0] == orow
        # ---- mechanics cross-check vs next settled board
        nxt_rec = next((q for q in R[idx + 1:] if q["S"]), None)
        mech = None
        if nxt_rec is not None:
            p = b.clone()
            if o == "H":
                p.color[orow, ocol], p.color[orow, ocol + 1] = ocolours
                p.link[orow, ocol], p.link[orow, ocol + 1] = 4, 3
                p.is_virus[orow, ocol] = p.is_virus[orow, ocol + 1] = False
            else:
                p.color[orow, ocol], p.color[orow + 1, ocol] = ocolours
                p.link[orow, ocol], p.link[orow + 1, ocol] = 2, 1
                p.is_virus[orow, ocol] = p.is_virus[orow + 1, ocol] = False
            tot, vir, chain = p.resolve()
            N = board_from_strings(nxt_rec["S"]["color"], nxt_rec["S"]["virus"], nxt_rec["S"]["link"])
            missing = int(((p.color > 0) & (N.color != p.color)).sum())
            extra = [(int(rr), int(cc), int(N.color[rr, cc])) for rr, cc in np.argwhere((N.color > 0) & (p.color == 0))]
            mech = {"cleared": int(tot), "viruses_cleared": int(vir), "chain": int(chain),
                    "missing_or_changed": missing, "extra": extra}
        # ---- video timing
        traj = r["traj"]
        t0 = r["t_spawn"]
        first_move = next((t for (t, oo, rr, cc, cl) in traj if cc != 3 or oo != "H"), None)
        lat = []
        last_c = 3
        for (t, oo, rr, cc, cl) in traj:
            if cc != last_c:
                lat.append((round((t - t0) * 60), cc)); last_c = cc
        rot = sum(1 for q in range(1, len(traj)) if traj[q][1] != traj[q - 1][1])
        # ---- short-landing / DISTGATE classification against the sim target
        cls = "MATCH" if match else None
        info = {}
        if not match and sim is not None:
            tgt = sim[1]
            toward = (tgt - 3) * (ocol - 3) >= 0 and abs(ocol - 3) < abs(tgt - 3)
            between = min(3, tgt) <= ocol <= max(3, tgt) and ocol != tgt
            budget, y = _dist_budget(Sc, 3, tgt, 0)
            info = {"sim_target_col": tgt, "dist_budget_at_spawn": budget, "free_rows_y": y,
                    "target_within_budget": abs(tgt - 3) <= budget,
                    "reach_nocarry": _reach(Sc, tgt), "reach_carry_v10": _reach(Sc, tgt, carry_v=10),
                    "reach_carry_v15": _reach(Sc, tgt, carry_v=15)}
            if between and toward and o == sim[0]:
                cls = "SHORT-LANDING"
            else:
                cls = "DIFFERENT-TARGET"
        heights = [int(16 - np.argmax(Sc[:, c] > 0)) if (Sc[:, c] > 0).any() else 0 for c in range(COLS)]
        rows.append({"k": r["k"], "t_spawn": t0, "virus_count": r["virus_count"], "cur": cur, "nxt": nxt,
                     "S": S, "heights": heights, "link_violations": lviol,
                     "sim_action": a, "sim": sim and [sim[0], sim[1], list(sim[2]), sim_row and list(sim_row)],
                     "actual": [o, ocol, list(ocolours), orow], "straight_drop": straight,
                     "verdict": cls, "short_info": info, "mech": mech,
                     "video": {"first_lateral_f": None if first_move is None else round((first_move - t0) * 60),
                               "lateral_steps_f_col": lat, "orient_changes": rot, "n_traj": len(traj)}})
    with open(out_path, "w") as fh:
        for q in rows:
            fh.write(json.dumps(q) + "\n")
    print(f"{len(rows)} placements -> {out_path}")


if __name__ == "__main__":
    if sys.argv[1] == "gate2":
        ok = all(gate2(s) for s in (36734, 36736, 40134))
        print("GATE2", "PASS" if ok else "FAIL")
        sys.exit(0 if ok else 1)
    analyze(sys.argv[2], sys.argv[3])
