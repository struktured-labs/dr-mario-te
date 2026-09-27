"""Refine analyze_g2.py verdicts into mechanisms and bank the per-placement cases.

  python classify_g2.py ANALYSIS.jsonl PLACEMENTS_RAW.jsonl OUT.jsonl

Categories (first match wins):
  MATCH          silicon landing == the sim brain's choice (orientation, column, colours, row)
  TUCK           the landing is not a straight-drop resting position: the capsule slid under an
                 overhang (couch cart DRTUCK=1) -- outside the sim decider's action space
  PROPH-ESCAPE   DRPROPH fired (spawn on a throat ledge: min(first-occupied row of c3, c4) <= 2) and the
                 capsule ended on the pulse side while the sim target was on the other side
  LATE-FLIP      the capsule held the sim's exact target pose (orientation+column+colours) for >= 4
                 frames, then changed orientation/column before locking
  SHORT-LANDING  same orientation, landed strictly between spawn and the sim target column;
                 dist_clamp=True when the DISTGATE budget (recomputed along the actual path) fell below
                 the remaining distance while the capsule was still short of the target
  OTHER          anything else (a different target / orientation with no pose match)
"""
from __future__ import annotations

import json
import sys

ROWS, COLS = 16, 8


def fo(color, c):
    return next((r for r in range(ROWS) if color[r * COLS + c] != "0"), ROWS)


def proph(color):
    f3, f4 = fo(color, 3), fo(color, 4)
    if min(f3, f4) > 2:
        return None
    deep = "L" if f3 >= f4 else "R"
    gate_l, gate_r = fo(color, 2) >= 2, fo(color, 5) >= 2
    if deep == "L":
        return "L" if gate_l else ("R" if gate_r else "-")
    return "R" if gate_r else ("L" if gate_l else "-")


def budget(color, row, c_from, c_to):
    lo, hi = min(c_from, c_to), max(c_from, c_to)
    y = 0
    for r in range(row + 1, ROWS):
        if all(color[r * COLS + c] == "0" for c in range(lo, hi + 1)):
            y += 1
        else:
            break
    return 0 if y == 0 else max(1, min(7, (30 * y) // 12))


def reach_frames(d, mode, v=None):
    """Frames from spawn to complete a d-column traverse. nocarry (driver, measured): think gate then
    1 col, then 6 f/col (press edges every 12 hooks); carry (ROM $8DCF): (16 - v) then 6 f/col;
    pulse (DRPROPH): 1 col / 2 f starting t=1."""
    if d == 0:
        return 0
    if mode == "nocarry":
        return 6 + (d - 1) * 6
    if mode == "carry":
        return (16 - v) + (d - 1) * 6
    return 1 + (d - 1) * 2


def main(an_path, raw_path, out_path):
    A = [json.loads(l) for l in open(an_path)]
    RAW = {json.loads(l)["k"]: json.loads(l) for l in open(raw_path)}
    out = []
    for q in A:
        k = q["k"]; S = q["S"]["color"]
        sim_o, sim_c, sim_cl, sim_rc = q["sim"]
        act_o, act_c, act_cl, act_r = q["actual"]
        traj = RAW[k]["traj"]; t0 = RAW[k]["t_spawn"]
        pdir = proph(S)
        v = q["verdict"]
        cat, detail = None, {}
        if v == "MATCH":
            cat = "MATCH"
        elif not q["straight_drop"]:
            cat = "TUCK"
        if cat is None and pdir in ("L", "R"):
            side = lambda c: "L" if c < 3 else ("R" if c > 3 else "C")
            if side(act_c) == pdir and side(sim_c) not in (pdir,):
                cat = "PROPH-ESCAPE"
        if cat is None:
            held = [t for (t, o, r, c, cl) in traj if o == sim_o and c == sim_c and cl == list(sim_cl)]
            if len(held) >= 4:
                last_hold = max(held)
                final = (act_o, act_r, act_c)
                t_final = next(t for (t, o, r, c, cl) in traj if (o, r, c) == final)
                cat = "LATE-FLIP"
                detail["held_target_frames"] = len(held)
                detail["target_held_until_f"] = round((last_hold - t0) * 60)
                detail["final_pose_from_f"] = round((t_final - t0) * 60)
        if cat is None and v == "SHORT-LANDING":
            cat = "SHORT-LANDING"
            clamp = False
            for (t, o, r, c, cl) in traj:
                if c != sim_c and budget(S, r, c, sim_c) < abs(sim_c - c):
                    clamp = True
                    break
            detail["dist_clamp"] = clamp
        if cat is None:
            cat = "OTHER"
        # counterfactual reach (columns counted from spawn col 3 for the sim's left/single column)
        d = abs(sim_c - 3)
        cf = {"d_cols": d, "nocarry_f": reach_frames(d, "nocarry"),
              "carry_v10_f": reach_frames(d, "carry", 10), "carry_v15_f": reach_frames(d, "carry", 15),
              "pulse_f": reach_frames(d, "pulse")}
        lat = []
        last_c = 3
        for (t, o, r, c, cl) in traj:
            if c != last_c:
                lat.append(round((t - t0) * 60)); last_c = c
        out.append({**{kk: q[kk] for kk in ("k", "t_spawn", "virus_count", "cur", "nxt", "S", "heights",
                                             "sim_action", "sim", "actual", "straight_drop", "mech", "video")},
                    "category": cat, "detail": detail, "proph_dir": pdir,
                    "fo3": fo(S, 3), "fo4": fo(S, 4), "lateral_move_frames": lat, "counterfactual": cf,
                    "garbage_after": ([] if k >= 49 else [e for e in (q["mech"] or {}).get("extra", [])])})
    with open(out_path, "w") as fh:
        for o in out:
            fh.write(json.dumps(o) + "\n")
    print(f"{len(out)} -> {out_path}")


if __name__ == "__main__":
    main(*sys.argv[1:4])
