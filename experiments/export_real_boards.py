#!/usr/bin/env python3
"""Export REAL L11 game positions in copro hostdata.txt format.

WHY. `sim_orient_trace` measured the pair-latch orient disagreement at 8.3% -- but on
`_rand_board` SYNTHETIC positions, where DONE landed at a median of ~34 frames. The
sim_mister.cpp comment cites dense depth-3 searches at ~0.5G clocks (~350 frames), far
beyond a capsule's fall time. If real positions search much slower than synthetic ones,
then late in a real game the cart commits its orientation on a FAR less converged search
than 8.3% implies -- which would explain the offline-vs-hardware gap that 8.3% alone does
not.

So: play real games with the shipped winner brain and snapshot positions across the whole
arc (opening / mid / dense endgame), tagged with occupancy, then feed those to the tracer.

hostdata cell encoding (tests/test_depth2.py::_rand_board):
    0xD0|col virus,  0x40|col pill,  0xFF empty,  col in 0..2
Our sim uses colour 1..3 with 0 = empty, so col_host = colour - 1.
"""
from __future__ import annotations
import sys, os, argparse, json

ROOT = "/home/struktured/projects/dr_mario_rl"
for p in (ROOT + "/tmp/combo_term", ROOT + "/.claude/worktrees/faithful-sim/src"):
    if p not in sys.path:
        sys.path.insert(0, p)

EMPTY = 0xFF


def to_host(board):
    """(8x16 row-major) -> 128 hostdata bytes, plus occupancy count."""
    import fast_rtl_x as NEW
    col, vir = NEW.board_flat(board)
    out, occ = [], 0
    for i in range(128):
        c = int(col[i])
        if c == 0:
            out.append(EMPTY)
        else:
            occ += 1
            out.append((0xD0 if int(vir[i]) else 0x40) | ((c - 1) & 0x03))
    return out, occ


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--games", type=int, default=8)
    ap.add_argument("--every", type=int, default=12, help="snapshot every N placements")
    ap.add_argument("--level", type=int, default=11)
    ap.add_argument("--out", default="hostdata_real.txt")
    a = ap.parse_args()

    import fast_rtl_x as NEW
    from drmario.faithful_env import FaithfulDrMarioEnv
    NEW.warmup_ship_eh(topk2=8)
    w, fl = NEW.variant("winner")
    dec = NEW.FastShipD3DeciderEH(w, fl, topk2=8)

    rows, meta = [], []
    for seed in range(a.games):
        env = FaithfulDrMarioEnv(level=a.level, seed=seed, max_pills=300)
        env.reset()
        k = 0
        while True:
            act = dec.choose(env.board, env.cur, env.nxt)
            if act is None:
                break
            if k % a.every == 0:
                cells, occ = to_host(env.board)
                vc = env.board.virus_count()
                rows.append("%d %d %d %d 0 0 %s" % (
                    env.cur.a - 1, env.cur.b - 1, env.nxt.a - 1, env.nxt.b - 1,
                    " ".join("%02x" % x for x in cells)))
                meta.append({"seed": seed, "placement": k, "occupancy": occ,
                             "virus": vc})
            _, _, term, trunc, _ = env.step(int(act))
            k += 1
            if term or trunc:
                break

    with open(a.out, "w") as f:
        f.write("%d\n" % len(rows) + "\n".join(rows) + "\n")
    json.dump(meta, open(a.out + ".meta.json", "w"), indent=1)
    occs = sorted(m["occupancy"] for m in meta)
    print(f"wrote {a.out}: {len(rows)} real L{a.level} positions")
    print(f"  occupancy  min={occs[0]} median={occs[len(occs)//2]} max={occs[-1]}")
    print(f"  virus      min={min(m['virus'] for m in meta)} max={max(m['virus'] for m in meta)}")


if __name__ == "__main__":
    main()
