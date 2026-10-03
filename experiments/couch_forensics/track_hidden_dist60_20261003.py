"""track.py + HIDDEN SPAWNS (2026-10-03 couch, ANTIBODY_DIST).

track.spawns() finds a spawn where the PREVIEW changes. When capsule k+2 has the same colours as capsule k+1, the
preview does not change at spawn k+1 and that spawn is MISSED (two placements merge into one step; ~1 in 9 spawns).
Measured on this capture: a 664-frame run of one preview held 3 capsules.

Hidden spawn rule: inside a run of preview P, a frame j where row 0 cols 3,4 read exactly (P.left, P.right) and on
frame j-1 both cells were empty, at least MIN_GAP frames after the previous capsule appeared. Garbage cannot match
(volleys are never adjacent singles in one row). The hidden spawn is placed at i = j - 2 (a regular spawn's capsule
appears ~2 frames after its preview change), so cur = nxt = P.

Usage: python track_hidden_dist60_20261003.py FRAMES.jsonl OUT.jsonl
"""
from __future__ import annotations

import json
import sys

import track as T

MIN_GAP = 30


def spawns_hidden(F):
    sp = T.spawns(F)
    out = []
    for n, i in enumerate(sp):
        out.append((i, "preview"))
        j_end = sp[n + 1] if n + 1 < len(sp) else len(F)
        P = tuple(F[i]["prev"])
        if 0 in P:
            continue
        last_appear = i + 2
        for j in range(i + 3, j_end):
            r0, r0p = F[j]["color"][0:8], F[j - 1]["color"][0:8]
            if r0p[3] == "0" and r0p[4] == "0" and r0[3] != "0" and r0[4] != "0":
                if (int(r0[3]), int(r0[4])) == P and j - last_appear >= MIN_GAP and j - 2 > i:
                    out.append((j - 2, "hidden"))
                last_appear = j
    out.sort()
    return out


def run(frames_path, out_path):
    F = T.load(frames_path)
    SP = spawns_hidden(F)
    sp = [i for i, _ in SP]
    kind = dict(SP)
    recs = []
    for k, i in enumerate(sp):
        cur = tuple(F[i - 1]["prev"]); nxt = tuple(F[i]["prev"])
        S = T.settled_at_spawn(F, i, cur)
        j_end = sp[k + 1] if k + 1 < len(sp) else len(F)
        traj = []
        for j in range(S["m"], j_end):
            p = T.capsule_pose(F[j]["C"], S["C"], cur)
            if p is not None:
                traj.append((F[j]["t"], p))
        recs.append({"k": k, "i_spawn": i, "t_spawn": F[i]["t"], "spawn_kind": kind[i], "cur": cur, "nxt": nxt,
                     "S": {"color": S["color"], "virus": S["virus"], "link": S["link"], "src": S["src"]},
                     "virus_count": S["virus"].count("1"),
                     "traj": [(t, p[0], p[1], p[2], list(p[3])) for t, p in traj],
                     "landing": (lambda p: [p[1][0], p[1][1], p[1][2], list(p[1][3])] if p else None)(traj[-1] if traj else None),
                     "t_next_spawn": F[j_end]["t"] if j_end < len(F) else None})
    with open(out_path, "w") as fh:
        for r in recs:
            fh.write(json.dumps(r) + "\n")
    print(f"spawns {len(sp)} ({sum(1 for _, q in SP if q == 'hidden')} hidden) -> {out_path}")


if __name__ == "__main__":
    run(sys.argv[1], sys.argv[2])
