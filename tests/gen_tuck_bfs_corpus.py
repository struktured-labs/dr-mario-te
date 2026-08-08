#!/usr/bin/env python3
"""tuck_bfs 200-board corpus generator (task #17 stage 4, deliverable #2).

Real L11 game positions, same style as dr-mario-qa-wt/experiments/
export_real_boards.py: play whole games with the shipped winner decider
(fast_rtl_x.FastShipD3DeciderEH) across deterministic seeds, snapshot the
board every `--every` placements so the corpus spans opening/mid/dense
endgame rather than only fresh-game shapes. Saved in FB convention
(0=empty, 1..3=colour) plus the pill-in-hand colours at the snapshot, which
is exactly what tuck_bfs_6502.py's bit-exact gate needs to call both the
6502 routine (after conversion to NES-tile occupancy) and tuck_enum.py's
python reference on the identical position.

Deterministic: fixed seed list, fixed `--every` stride -- rerunning this
script reproduces the same 200 boards byte-for-byte.
"""
import sys
import os
import json
import argparse

ROOT = "/home/struktured/projects/dr_mario_rl"
for p in (ROOT + "/tmp/combo_term", ROOT + "/.claude/worktrees/faithful-sim/src"):
    if p not in sys.path:
        sys.path.insert(0, p)


def board_to_fb(board):
    return board.color.reshape(-1).astype(int).tolist()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--target", type=int, default=200)
    ap.add_argument("--every", type=int, default=7,
                     help="snapshot every N placements (spans the whole game arc)")
    ap.add_argument("--level", type=int, default=11)
    ap.add_argument("--out", default=os.path.join(
        os.path.dirname(__file__), "tuck_bfs_corpus_200.json"))
    a = ap.parse_args()

    import fast_rtl_x as NEW
    from drmario.faithful_env import FaithfulDrMarioEnv
    NEW.warmup_ship_eh(topk2=8)
    w, fl = NEW.variant("winner")
    dec = NEW.FastShipD3DeciderEH(w, fl, topk2=8)

    boards = []
    seed = 0
    while len(boards) < a.target:
        env = FaithfulDrMarioEnv(level=a.level, seed=seed, max_pills=300)
        env.reset()
        k = 0
        while len(boards) < a.target:
            act = dec.choose(env.board, env.cur, env.nxt)
            if act is None:
                break
            if k % a.every == 0:
                boards.append({
                    "id": len(boards),
                    "seed": seed,
                    "placement": k,
                    "col": board_to_fb(env.board),
                    "ca": int(env.cur.a),
                    "cb": int(env.cur.b),
                    "virus": int(env.board.virus_count()),
                })
            _, _, term, trunc, _ = env.step(int(act))
            k += 1
            if term or trunc:
                break
        seed += 1

    with open(a.out, "w") as f:
        json.dump({"n": len(boards), "level": a.level, "every": a.every,
                    "seeds_used": seed, "boards": boards}, f)
    occ = sorted(sum(1 for c in b["col"] if c != 0) for b in boards)
    vir = sorted(b["virus"] for b in boards)
    print(f"wrote {a.out}: {len(boards)} boards from {seed} seeds")
    print(f"  occupancy  min={occ[0]} median={occ[len(occ)//2]} max={occ[-1]}")
    print(f"  virus      min={vir[0]} median={vir[len(vir)//2]} max={vir[-1]}")


if __name__ == "__main__":
    main()
