#!/usr/bin/env python3
"""Positive-path trajectory proof (task #17, closing item 1, 2026-08-05): drive a FULL
real L11 game through the WIRED firmware (DRCOPRO_TUCKBFS=1 or DRCOPRO_TUCKV3=1 as a
control), decision by decision, using py65's RTL-engine emulation for each one, until a
tuck-class candidate actually wins the theta-gated decision and gets published to
TUCK_COL/TUCK_ROW -- then verifies the published descriptor matches the winning
candidate's own approach/trigger and that applying the placement to the real game board
lands on the tuck's own claimed rest cells.

Pattern adapted from dr-mario-qa-wt/experiments/tuck_v3/union_mirror.py's own play()
loop (base actions via env.step(), tuck actions via direct board mutation) -- same
shape, but the DECIDER here is the real firmware (via a fresh build_image() + py65
stub-flow reset->DONE per decision), not a Python mirror model.

Run as ONE game per process (see this file's own __main__): the corpus-loop anomaly
documented in validate_tuckbfs_wiring_corpus.py's docstring was never chased down, so
per-game subprocess isolation is used here too rather than looping games in one process.
"""
import sys
import os
import json
import argparse

COPRO = "/home/struktured/projects/dr-mario-canonical-wt/fpga/copro"
ROOT = "/home/struktured/projects/dr-mario-canonical-wt"
sys.path.insert(0, COPRO)
sys.path.insert(0, os.path.join(ROOT, "tests"))
sys.path.insert(0, ROOT)

# nes_pills / fast_rtl_x / the faithful env live in dr_mario_rl's tmp/ + worktree tree,
# NOT in this canonical worktree -- same path set union_mirror.py (dr-mario-qa-wt/
# experiments/tuck_v3/union_mirror.py) already proved works for this exact module combo.
ROOT_RL = "/home/struktured/projects/dr_mario_rl"
QA = "/home/struktured/projects/dr-mario-qa-wt/experiments"
for _p in (ROOT_RL + "/tmp/combo_term", ROOT_RL + "/tmp/endgame", ROOT_RL + "/tmp/tuck",
           ROOT_RL + "/tmp/pillrng", ROOT_RL + "/.claude/worktrees/faithful-sim/src", QA):
    if _p not in sys.path:
        sys.path.insert(0, _p)

EMPTY = 0xFF


def to_host(board):
    """FaithfulBoard -> 128 NES tile bytes (export_real_boards.py's own convention:
    0xD0|colour for virus, 0x40|colour for capsule, 0xFF empty). Needed here (not the
    simpler EMPTY/occupied-only convention tuck_bfs_6502.py's own test harnesses use)
    because the REST of the firmware -- virus counting, clearing, scoring -- cares
    about the full tile encoding, not just occupancy."""
    import fast_rtl_x as NEW
    col, vir = NEW.board_flat(board)
    out = []
    for i in range(128):
        c = int(col[i])
        if c == 0:
            out.append(EMPTY)
        else:
            out.append((0xD0 if int(vir[i]) else 0x40) | ((c - 1) & 0x03))
    return out


def query_firmware(board_host, ca0, cb0, na0, nb0):
    """One decision: fresh build_image() + py65 stub-flow reset->DONE. Returns a dict
    with the chosen action (S_BEST_C/S_BEST_O), whether a tuck won, the published
    TUCK_COL/TUCK_ROW, and (if a tuck won) the full CANDLIST for verification."""
    import build_copro_d3 as B
    from py65_harness import Cpu
    from test_search_d3 import attach_engine_emu, S_BEST_C, S_BEST_O
    from test_depth2 import S_CA, S_CB, S_NA, S_NB
    import tuck_bfs_translate_6502 as TRB

    img, clen, slen = B.build_image(board_host, ca0, cb0, na0, nb0)
    cpu = Cpu()
    for addr, v in enumerate(img):
        cpu.mem[addr] = v
    attach_engine_emu(cpu)
    cpu.mem[S_CA] = ca0; cpu.mem[S_CB] = cb0
    cpu.mem[S_NA] = na0; cpu.mem[S_NB] = nb0
    cpu.mem[B.DONE] = 0
    m = cpu.mpu
    m.pc = B.STUB
    m.sp = 0xFF
    steps = 0
    while steps < 300_000_000:
        m.step(); steps += 1
        if cpu.mem[B.DONE] == 1:
            break
    else:
        return {"error": "DONE never reached", "steps": steps}

    # int(...) throughout: cpu.mem is numpy-backed (py65_harness), so raw reads are
    # numpy.uint8/numpy.bool_, not JSON-serializable Python types -- cast once here
    # at the source rather than at every downstream call site.
    best_c = int(cpu.mem[S_BEST_C])
    best_o = int(cpu.mem[S_BEST_O])
    tuck_col = int(cpu.mem[B.TUCK_COL])
    tuck_row = int(cpu.mem[B.TUCK_ROW])
    tucked = bool(tuck_col != 0xFF)
    out = {"steps": steps, "best_c": best_c, "best_o": best_o,
           "tucked": tucked, "tuck_col": tuck_col, "tuck_row": tuck_row}
    if tucked:
        ts_cnt = int(cpu.mem[TRB.TS_CNT])
        candlist = [tuple(int(cpu.mem[TRB.CANDLIST + i * 5 + k]) for k in range(5))
                    for i in range(ts_cnt)]
        out["candlist"] = candlist
    return out


# orient (tuck_enum ring H=0,V=1,RH=2,RV=3) -> o4 (test_depth2 0-1=VERT,2-3=HORIZ),
# matching tuck_v3.py's own tuck_o4_table = O4_TABLE = [2, 1, 3, 0] (index by H/V/RH/RV).
O4_TABLE = [2, 1, 3, 0]
# o4 -> the 32-action `variant` space env.step() expects (fast_rtl_x._VAR_OF_O4).
VAR_OF_O4 = None  # filled in lazily (needs fast_rtl_x import)


def play_game(seed, arm, level=11, max_pills=300, progress_every=10):
    """arm: 'bfs' (DRCOPRO_TUCKBFS) or 'v3' (DRCOPRO_TUCKV3) -- caller must have set the
    matching env var BEFORE this process started (module-level flags in build_copro_d3
    are read once at import time)."""
    global VAR_OF_O4
    from drmario.faithful_env import FaithfulDrMarioEnv
    from drmario.faithful_game import LINK_LEFT, LINK_RIGHT, LINK_UP, LINK_DOWN
    from nes_pills import NesPillSource
    import fast_rtl_x as FX
    VAR_OF_O4 = FX._VAR_OF_O4

    import build_copro_d3 as B
    print(f"[trajectory] arm={arm} EMIT_TUCK_BFS={B.EMIT_TUCK_BFS} "
          f"EMIT_TUCK_V3={B.EMIT_TUCK_V3}", flush=True)

    env = FaithfulDrMarioEnv(level=level, seed=seed, max_pills=max_pills)
    env.reset()
    NesPillSource(seed=seed).attach(env)
    env.cur = env._rand_pill()
    env.nxt = env._rand_pill()

    fires = []
    verification_failures = []
    res = "stall"
    k = 0
    for k in range(max_pills):
        if env.board.virus_count() == 0:
            res = "clear"
            break
        board_host = to_host(env.board)
        ca, cb = int(env.cur.a), int(env.cur.b)
        na, nb = int(env.nxt.a), int(env.nxt.b)
        d = query_firmware(board_host, ca - 1, cb - 1, na - 1, nb - 1)
        if "error" in d:
            print(f"  pill {k}: FIRMWARE ERROR: {d}", flush=True)
            res = "firmware_error"
            break

        if d["tucked"]:
            # find the CANDLIST entry matching the winning decision (target=best_c,
            # orient matching best_o via O4_TABLE) -- this is the self-consistency
            # check: does the published (TUCK_COL,TUCK_ROW) match THAT entry's own
            # (approach,trigger)? Matched on ALL FOUR of (target,o4,approach,trigger)
            # together, not target+o4 alone: tuck_scan_v3's own CANDLIST can (and
            # does, e.g. seed0/pill71 on the v3 control arm) carry MULTIPLE entries
            # for the SAME (target,orient) that differ only by trigger row -- the
            # search picks one and publishes ITS descriptor, so the published
            # (TUCK_COL,TUCK_ROW) is what disambiguates which entry actually fired,
            # not (target,orient) alone. (tuck_bfs's own translate_candidates()
            # dedupes by target+orient before this ever matters, which is why this
            # ambiguity is a v3-arm-only structural difference, not a wiring bug.)
            match = [c for c in d["candlist"]
                     if c[0] == d["best_c"] and O4_TABLE[c[4]] == d["best_o"]
                     and c[1] == d["tuck_col"] and c[2] == d["tuck_row"]]
            if len(match) != 1:
                verification_failures.append({
                    "pill": k, "reason": f"no unique CANDLIST match ({len(match)} hits)",
                    "best_c": int(d["best_c"]), "best_o": int(d["best_o"]),
                    "tuck_col": int(d["tuck_col"]), "tuck_row": int(d["tuck_row"]),
                    "candlist": [[int(v) for v in c] for c in d["candlist"]]})
                print(f"  pill {k}: TUCK FIRED but no unique CANDLIST match "
                      f"({len(match)} hits): {d}", flush=True)
                res = "verification_failed"
                break

            target, approach, trigger, rest, orient = match[0]
            ok_descriptor = bool(approach == d["tuck_col"] and trigger == d["tuck_row"])
            if not ok_descriptor:
                verification_failures.append({
                    "pill": k, "reason": "descriptor mismatch",
                    "entry": [int(v) for v in match[0]],
                    "tuck_col": int(d["tuck_col"]), "tuck_row": int(d["tuck_row"])})
                print(f"  pill {k}: descriptor MISMATCH: entry={match[0]} "
                      f"published=({d['tuck_col']},{d['tuck_row']})", flush=True)

            # apply the tuck placement directly to the real board (union_mirror.py's
            # own pattern) -- cells from tuck_enum's own _cells_of(x,y,o) convention.
            x, y = target, rest
            is_vert = orient in (1, 3)
            if is_vert:
                r0, c0, r1, c1 = y - 1, x, y, x
            else:
                r0, c0, r1, c1 = y, x, y, x + 1
            # legality/rest check -- both cells must be empty on the CURRENT board
            # (proves the published descriptor's target really is where tuck_bfs
            # claimed, on the ACTUAL board this decision was made against)
            b = env.board
            # bool(...) here: b.color is a numpy array, so the raw comparison is a
            # numpy.bool_, not a JSON-serializable Python bool (bit this script once
            # already -- both games that reached this far crashed writing --out,
            # having already printed every fire correctly beforehand).
            cells_empty = bool(b.color[r0, c0] == 0 and b.color[r1, c1] == 0)
            if not cells_empty:
                verification_failures.append({
                    "pill": k, "reason": "tuck rest cells not empty on the real board",
                    "cells": [int(r0), int(c0), int(r1), int(c1)]})
                print(f"  pill {k}: TUCK cells NOT EMPTY on real board -- {(r0, c0, r1, c1)}",
                      flush=True)

            col0, col1 = (cb, ca) if orient in (1, 2) else (ca, cb)
            b.color[r0, c0] = col0
            b.color[r1, c1] = col1
            if r0 == r1:
                b.link[r0, c0] = LINK_RIGHT; b.link[r1, c1] = LINK_LEFT
            else:
                b.link[r0, c0] = LINK_DOWN; b.link[r1, c1] = LINK_UP
            b.is_virus[r0, c0] = False
            b.is_virus[r1, c1] = False
            b.resolve()
            verified = bool(ok_descriptor and cells_empty)
            fires.append({"pill": k, "target": int(x), "rest": int(y), "orient": int(orient),
                          "approach": int(d["tuck_col"]), "trigger": int(d["tuck_row"]),
                          "verified": verified})
            print(f"  pill {k}: TUCK FIRED target={x} rest={y} orient={orient} "
                  f"approach={d['tuck_col']} trigger={d['tuck_row']} "
                  f"verified={verified}", flush=True)
            env.pills_placed += 1
            env.cur = env.nxt
            env.nxt = env._rand_pill()
            if b.virus_count() == 0:
                res = "clear"; break
            if b.spawn_blocked():
                res = "topout"; break
            continue

        # base action: S_BEST_O is o4, needs the variant mapping for env.step()
        action = int(VAR_OF_O4[d["best_o"]]) * 8 + d["best_c"]
        _, _, term, trunc, info = env.step(action)
        if term:
            res = "clear" if info["won"] else "topout"
            break
        if trunc:
            res = "trunc"
            break
        if (k + 1) % progress_every == 0:
            print(f"  ...pill {k+1}/{max_pills}, fires so far={len(fires)}", flush=True)

    return {"seed": seed, "arm": arm, "level": level, "result": res,
            "pills": env.pills_placed, "n_fires": len(fires), "fires": fires,
            "verification_failures": verification_failures}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--seed", type=int, required=True)
    ap.add_argument("--arm", choices=["bfs", "v3"], required=True)
    ap.add_argument("--level", type=int, default=11)
    ap.add_argument("--max-pills", type=int, default=300)
    ap.add_argument("--out", default=None)
    a = ap.parse_args()

    result = play_game(a.seed, a.arm, level=a.level, max_pills=a.max_pills)
    print(json.dumps({k: v for k, v in result.items() if k not in ("fires",)}, indent=1))
    if a.out:
        with open(a.out, "w") as f:
            json.dump(result, f, indent=1)
        print(f"wrote {a.out}")


if __name__ == "__main__":
    main()
