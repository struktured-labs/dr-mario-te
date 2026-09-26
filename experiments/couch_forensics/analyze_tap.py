"""CHAIN540+REACH+TAP couch build (rbf 77b521b2 + cart 198a95e3): why is it stacking the spawn lane?

Per placement (from track.py output over a window that starts BEFORE each game so the game pill count is known):
  * unmasked brain  = fw540 (StrandedChainD3Decider, w_chain 540, ws 20)
  * masked brain    = the same search with the reach-root mask the firmware computes:
                      reach_fw_tap.reach_mask_fw(color, thr, tap=2), thr = steer_model.table_threshold(pill count)
                      (cascade_reach_x._choose_d3_chain_s_masked; all-ones mask == unmasked is checked first)
  * silicon landing, whether the mask allows it / allows the unmasked choice, #allowed candidates
  * video timing: first lateral move, lateral gaps, rotation (orientation-change) frames, PROPH trigger

Usage: python analyze_tap.py RAW.jsonl OUT.jsonl
"""
import json
import os
import sys

import numpy as np

import analyze_g2 as A                      # pins imports (import_pin) and provides board/decider helpers
from drmario.faithful_game import Pill
import classify_g2 as CL

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "cvx"))
import cascade_reach_x as CR  # noqa: E402
import reach_fw_tap as RFT  # noqa: E402
import steer_model as SM  # noqa: E402


def masked_choice(dec, b, cur, nxt, allowed):
    col, vir = A.board_from_strings(*b).color, None
    bb = A.board_from_strings(*b)
    from cascade_link_x import board_flat
    c, v = board_flat(bb)
    lnk = np.ascontiguousarray(bb.link, dtype=np.int8).reshape(-1)
    a = CR._choose_d3_chain_s_masked(c, v, lnk, cur[0], cur[1], nxt[0], nxt[1], dec.topk2, dec.w_excav, dec.w_hang,
                                     dec.w, dec.fl, dec.maxpass, dec.w_chain, dec.ws, np.asarray(allowed, np.int8))
    return None if a < 0 else int(a)


def pose_of(action, cur, board):
    o, c, cl = A.decode(action, cur)
    row = A.resting(board, o, c)
    return [o, c, list(cl), row and row[0]]


def run(raw_path, out_path):
    R = [json.loads(l) for l in open(raw_path)]
    dec = A.decider()
    # game pill count: spawns since the last blank-preview (game start) spawn
    # games by TIME window (GAMES env: "t0:t1,t0:t1"): a blank-preview frame mid-game (flicker) must not
    # reset the pill count, which drives thr. k_game = spawns since the game's first spawn.
    wins = [tuple(float(x) for x in w.split(":")) for w in os.environ["GAMES"].split(",")]
    kg = []
    for i, r in enumerate(R):
        g = next((j + 1 for j, (a, b) in enumerate(wins) if a <= r["t_spawn"] <= b), 0)
        first = next(q for q, rr in enumerate(R) if g and wins[g - 1][0] <= rr["t_spawn"] <= wins[g - 1][1]) if g else i
        kg.append((g, i - first))
    # identity gate: all-ones mask == unmasked on every analysable board
    same = tot = 0
    rows = []
    for i, r in enumerate(R):
        if r["landing"] is None or 0 in r["cur"] or 0 in r["nxt"] or kg[i][0] == 0:
            continue
        S = (r["S"]["color"], r["S"]["virus"], r["S"]["link"])
        b = A.board_from_strings(*S)
        cur, nxt = tuple(r["cur"]), tuple(r["nxt"])
        a_un = dec.choose(b.clone(), Pill(*cur), Pill(*nxt))
        a_one = masked_choice(dec, S, cur, nxt, [1] * 32)
        tot += 1; same += int(a_one == a_un)
        g, k = kg[i]
        thr = SM.table_threshold(k)
        mask = RFT.reach_mask_fw(b.color.tolist(), thr, 2)
        a_m = masked_choice(dec, S, cur, nxt, mask)
        o, orow, ocol, ocl = r["landing"]
        # which action index is the silicon landing (any variant with the same cells + colours)?
        act_a = None
        for a in range(32):
            po = pose_of(a, cur, b)
            if po[0] == o and po[1] == ocol and po[2] == list(ocl) and po[3] == orow:
                act_a = a; break
        traj = r["traj"]; t0 = r["t_spawn"]
        lat, rot = [], []
        last = None
        for (t, oo, rr, cc, cl) in traj:
            if last is not None:
                if cc != last[2]:
                    lat.append(round((t - t0) * 60))
                if oo != last[0] or cl != last[3]:
                    rot.append(round((t - t0) * 60))
            last = (oo, rr, cc, cl)
        un = pose_of(a_un, cur, b) if a_un is not None else None
        ms = pose_of(a_m, cur, b) if a_m is not None else None
        actual = [o, ocol, list(ocl), orow]
        rows.append({"game": g, "k_game": k, "k": r["k"], "t_spawn": t0, "thr": thr, "cur": cur, "nxt": nxt, "S": r["S"],
                     "heights": [int(16 - np.argmax(b.color[:, c] > 0)) if (b.color[:, c] > 0).any() else 0 for c in range(8)],
                     "fo3": CL.fo(r["S"]["color"], 3), "fo4": CL.fo(r["S"]["color"], 4), "proph": CL.proph(r["S"]["color"]),
                     "unmasked": un, "masked": ms, "actual": actual, "actual_action": act_a,
                     "match_unmasked": un == actual, "match_masked": ms == actual,
                     "mask_allows_actual": None if act_a is None else bool(mask[act_a]),
                     "mask_allows_unmasked": None if a_un is None else bool(mask[a_un]),
                     "n_allowed": int(sum(mask)), "lateral_f": lat, "rotation_f": rot,
                     "straight_drop": act_a is not None, "n_traj": len(traj)})
    with open(out_path, "w") as fh:
        for q in rows:
            fh.write(json.dumps(q) + "\n")
    print(f"identity gate (all-ones mask == unmasked): {same}/{tot}; {len(rows)} placements -> {out_path}")


if __name__ == "__main__":
    run(sys.argv[1], sys.argv[2])
