"""Turn per-frame reads (scan_frames.py) into per-placement records for P2.

Spawn k = a frame where the preview changes (the previous preview becomes the live capsule).
  S_k      = the board on the frame before spawn k (previous capsule locked, clears/garbage settled)
  cur_k    = the preview shown before spawn k (left, right) = sim Pill(a, b) at spawn (H, a at col 3)
  nxt_k    = the preview shown after spawn k
  traj_k   = per-frame pose of the falling capsule: frames whose board differs from S_k by exactly the
             two capsule cells (adjacent, colours = cur_k in some orientation)
  landing  = the last traj pose before the capsule's cells become part of the next settled board

Mechanics cross-check (the reader gate that needs no human): place cur_k at the observed landing on
S_k with drmario.faithful_game and resolve(); the result must be a SUBSET of S_{k+1} with every extra
cell a single (unlinked) half sitting on a column top = opponent garbage. Mismatches are flagged.
"""
from __future__ import annotations

import json
import sys

import numpy as np

ROWS, COLS = 16, 8


def arr(s, dt=np.int8):
    return np.array([int(ch) for ch in s], dtype=dt).reshape(ROWS, COLS)


def load(path):
    F = [json.loads(l) for l in open(path)]
    for f in F:
        f["C"] = arr(f["color"]); f["V"] = arr(f["virus"]).astype(bool); f["L"] = arr(f["link"])
    return F


def spawns(F):
    out = []
    for i in range(1, len(F)):
        if tuple(F[i]["prev"]) != tuple(F[i - 1]["prev"]):
            out.append(i)
    return out


def capsule_pose(C, S, cur):
    """If C differs from S by exactly two adjacent occupied cells whose colours match cur (either
    order), return (orient, r, c, colours-in-board-order) with orient 'H' (cells (r,c),(r,c+1)) or
    'V' (cells (r,c),(r+1,c)); else None."""
    d = np.argwhere((C != S) & (C > 0))
    gone = np.argwhere((C != S) & (C == 0))
    if len(d) != 2 or len(gone):
        return None
    (r0, c0), (r1, c1) = sorted((int(a), int(b)) for a, b in d)
    cols = (int(C[r0, c0]), int(C[r1, c1]))
    if sorted(cols) != sorted(cur):
        return None
    if r0 == r1 and c1 == c0 + 1:
        return ("H", r0, c0, cols)
    if c0 == c1 and r1 == r0 + 1:
        return ("V", r0, c0, cols)
    return None


def settled_at_spawn(F, i, cur):
    """Settled board for spawn i. Two capture facts (measured on this recording):
    (1) the preview updates ~1 frame before the playfield re-renders, and (2) the new capsule appears
    while the previous clear's "pop" tiles are still drawn (~10 frames); pops read as virus-like tiles.
    So: m = first frame >= i+2 whose virus-like count equals the minimum over [i+2, i+40] (pops gone),
    then erase the capsule = the adjacent pair in rows 0-1 carrying cur's colours that was NOT drawn on
    the pre-spawn frame. The capsule has at most moved a row/column by m (think gate >= 6 frames)."""
    hi = min(i + 40, len(F))
    vmin = min(int(F[j]["V"].sum()) for j in range(min(i + 2, hi - 1), hi))
    m = next(j for j in range(min(i + 2, hi - 1), hi) if int(F[j]["V"].sum()) == vmin)
    C = F[m]["C"].copy(); V = F[m]["V"].copy(); L = F[m]["L"].copy()
    pre = F[i - 1]["C"]
    cands = []
    for r in range(0, 2):
        for c in range(COLS):
            for (dr, dc) in ((0, 1), (1, 0)):
                r2, c2 = r + dr, c + dc
                if r2 >= ROWS or c2 >= COLS:
                    continue
                pair = sorted((int(C[r, c]), int(C[r2, c2])))
                if pair == sorted(cur) and (pre[r, c] == 0 or pre[r2, c2] == 0):
                    cands.append((r, c, r2, c2))
    src = f"m=i+{m - i}"
    if (0, 3, 0, 4) in cands:                       # prefer the spawn cells when ambiguous
        cands.remove((0, 3, 0, 4)); cands.insert(0, (0, 3, 0, 4))
    if len(cands) >= 1:
        r, c, r2, c2 = cands[0]
        if len(cands) > 1:
            src += f" AMBIG{len(cands)}"
        for (rr, cc) in ((r, c), (r2, c2)):
            C[rr, cc] = 0; V[rr, cc] = False; L[rr, cc] = 0
    else:
        src += " NOCAPSULE"
    enc = lambda a: "".join(str(int(v)) for v in np.asarray(a).ravel())
    return {"C": C, "color": enc(C), "virus": enc(V.astype(int)), "link": enc(L), "src": src, "m": m}


def run(frames_path, out_path):
    F = load(frames_path)
    sp = spawns(F)
    recs = []
    for k, i in enumerate(sp):
        cur = tuple(F[i - 1]["prev"]); nxt = tuple(F[i]["prev"])
        S = settled_at_spawn(F, i, cur)
        j_end = sp[k + 1] if k + 1 < len(sp) else len(F)
        traj = []
        for j in range(S["m"], j_end):
            p = capsule_pose(F[j]["C"], S["C"], cur)
            if p is not None:
                traj.append((F[j]["t"], p))
        recs.append({"k": k, "i_spawn": i, "t_spawn": F[i]["t"], "cur": cur, "nxt": nxt,
                     "S": {"color": S["color"], "virus": S["virus"], "link": S["link"], "src": S["src"]},
                     "virus_count": S["virus"].count("1"),
                     "traj": [(t, p[0], p[1], p[2], list(p[3])) for t, p in traj],
                     "landing": (lambda p: [p[1][0], p[1][1], p[1][2], list(p[1][3])] if p else None)(traj[-1] if traj else None),
                     "t_next_spawn": F[j_end]["t"] if j_end < len(F) else None})
    with open(out_path, "w") as fh:
        for r in recs:
            fh.write(json.dumps(r) + "\n")
    print(f"spawns {len(sp)} -> {out_path}")


if __name__ == "__main__":
    run(sys.argv[1], sys.argv[2])
