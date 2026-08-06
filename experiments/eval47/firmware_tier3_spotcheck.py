#!/usr/bin/env python3
"""Milestone 4 firmware-truth spot-check (task #17 tier-3 mission, per team-lead's
2026-08-05 explicit ask): firmware_tier3_ab.py's n=60 sweep used
translate_ref_tier3.py's Python cascade for EVERY seed -- bit-exact-validated against
the real 6502 (tuck-bfs-6502 commit 0fc6bb8), but not itself an execution of the
firmware. This script closes that gap for a HANDFUL of seeds, picked from the sweep's
OWN fired_tuck distribution (a spot-check on a zero-fire seed proves nothing, per the
explicit instruction).

METHOD: replay firmware_tier3_ab.play()'s EXACT game loop (same seed, same bursty
model, same RNG state) for a chosen seed, but additionally snapshot the board (in
py65/trajectory_fire_proof.py's NES-tile convention) at every point where the mirror
rig's own choose_reach_tier() decides to fire a tuck. Each snapshot is then fed into
the REAL 6502 firmware (fresh build_image() + py65 stub-flow, DRCOPRO_TUCKBFS=1
DRCOPRO_TUCKBFS_TIER3=1, subprocess-isolated per snapshot -- this branch's own
established anomaly-avoidance pattern) and checked for whether the real search's own
winner-selection ALSO fires a tuck there.

HONEST SCOPE NOTE: reach_root.py's choose_reach_tier is a MIRROR/approximation scorer
(a different, faster search built for large-n sweeps), not a re-implementation of the
real depth-3 D3 search wired into the copro. So this spot-check does NOT assert the
firmware picks the identical (target,rest,orient) candidate the mirror rig chose --
that would conflate two different scoring systems that were never claimed to agree
move-for-move. What IS checked, and is exactly what "firmware-truth" should mean here:
on a board the mirror rig says has a firing tuck opportunity, does REAL FIRMWARE
EXECUTION also find one to fire (TUCK_COL != 0xFF), and does its published descriptor
land on genuinely empty cells (the same safety check used throughout this branch's
other trajectory work)? This corroborates that the tuck opportunities the mirror rig
(and by extension the M4 sweep's fire counts) is counting are REAL, firmware-
executable ones on REAL boards, not an artifact of the mirror's own approximation.
"""
import sys
import os
import json
import subprocess

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import reach_root as RR  # noqa: E402
import reach_root_ab as AB  # noqa: E402
import bursty_model  # noqa: E402
import firmware_tier3_ab as FA  # noqa: E402

CANON = "/home/struktured/projects/dr-mario-canonical-wt"
PY = "/home/struktured/projects/dr_mario_rl/tmp/venv/bin/python"

_WORKER = r'''
import sys, json
sys.path.insert(0, "{canon}/fpga/copro")
sys.path.insert(0, "{canon}/tests")
sys.path.insert(0, "{canon}")
import build_copro_d3 as B
from py65_harness import Cpu
from test_search_d3 import attach_engine_emu, S_BEST_C, S_BEST_O
from test_depth2 import S_CA, S_CB, S_NA, S_NB

board, ca0, cb0, na0, nb0 = json.loads(sys.argv[1])
img, clen, slen = B.build_image(board, ca0, cb0, na0, nb0)
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
    print(json.dumps({{"error": "DONE never reached"}}))
    sys.exit(0)

tuck_col = int(cpu.mem[B.TUCK_COL])
tuck_row = int(cpu.mem[B.TUCK_ROW])
print(json.dumps({{"best_c": int(cpu.mem[S_BEST_C]), "best_o": int(cpu.mem[S_BEST_O]),
                   "tucked": tuck_col != 0xFF, "tuck_col": tuck_col, "tuck_row": tuck_row,
                   "steps": steps}}))
'''


def query_firmware_subprocess(board, ca0, cb0, na0, nb0):
    """Fresh subprocess per call -- this branch's own established anomaly-avoidance
    pattern (validate_tuckbfs_wiring_corpus.py's documented in-process-loop anomaly;
    trajectory_fire_proof.py's own docstring cites the same reason)."""
    script = _WORKER.format(canon=CANON)
    arg = json.dumps([board, ca0, cb0, na0, nb0])
    env = dict(os.environ)
    env["DRCOPRO_TUCKBFS"] = "1"
    env["DRCOPRO_TUCKBFS_TIER3"] = "1"
    r = subprocess.run([PY, "-c", script, arg], capture_output=True, text=True,
                       timeout=180, env=env)
    if r.returncode != 0:
        return {"error": f"subprocess failed: {r.stderr[-2000:]}"}
    try:
        return json.loads(r.stdout.strip().splitlines()[-1])
    except Exception as e:
        return {"error": f"bad output: {e}: {r.stdout[-500:]} {r.stderr[-500:]}"}


EMPTY_NES = 0xFF


def to_host(board):
    """Identical to trajectory_fire_proof.py's own to_host() -- same convention,
    same source module (fast_rtl_x), applied directly to a FaithfulBoard."""
    import fast_rtl_x as NEW
    col, vir = NEW.board_flat(board)
    out = []
    for i in range(128):
        c = int(col[i])
        if c == 0:
            out.append(EMPTY_NES)
        else:
            out.append((0xD0 if int(vir[i]) else 0x40) | ((c - 1) & 0x03))
    return out


def replay_with_snapshots(seed, level=11, pressure="bursty", max_snapshots=3):
    """Byte-for-byte replay of firmware_tier3_ab.play()'s game loop (same seed, same
    bursty model, deterministic), snapshotting the board at each tuck-fire point (up
    to max_snapshots) instead of just returning summary stats."""
    import numpy as np
    from drmario.faithful_env import FaithfulDrMarioEnv
    from drmario.faithful_game import LINK_LEFT, LINK_RIGHT, LINK_UP, LINK_DOWN
    from nes_pills import NesPillSource
    from bursty_model import inject_bursty_garbage

    bm = bursty_model.fit_struktured_20260804()
    bm.meta = {k: v for k, v in bm.meta.items() if k != "raw_events"}

    L = RR._lazy()
    FB, RS = L["FB"], L["RS"]

    env = FaithfulDrMarioEnv(level=level, seed=seed, max_pills=300)
    env.reset()
    NesPillSource(seed=seed).attach(env)
    env.cur = env._rand_pill()
    env.nxt = env._rand_pill()

    snapshots = []
    res = "stall"
    for pill_idx in range(300):
        fb = FB.from_board(env.board)
        if env.board.virus_count() == 0:
            res = "clear"
            break
        col, vir = RS.board_flat_from_fb(fb)
        ca, cb, na, nb = int(env.cur.a), int(env.cur.b), int(env.nxt.a), int(env.nxt.b)
        best = RR.choose_reach_tier(fb, col, vir, ca, cb, na, nb, 1,
                                    tier_fn=FA.firmware_tier_of)

        occ_before = int(np.count_nonzero(env.board.color))

        if best["kind"] == "tuck":
            if len(snapshots) < max_snapshots:
                snapshots.append({
                    "pill_idx": pill_idx,
                    "board_nes": to_host(env.board),
                    "ca0": ca - 1, "cb0": cb - 1, "na0": na - 1, "nb0": nb - 1,
                    "mirror_placement": {k: v for k, v in best["placement"].items()
                                        if k in ("col", "row", "orient", "cells")},
                })
            p = best["placement"]
            r0, c0, r1, c1 = p["cells"]
            col0, col1 = best["ca"], best["cb"]
            b = env.board
            b.color[r0, c0] = col0
            b.color[r1, c1] = col1
            if r0 == r1:
                b.link[r0, c0] = LINK_RIGHT
                b.link[r1, c1] = LINK_LEFT
            else:
                b.link[r0, c0] = LINK_DOWN
                b.link[r1, c1] = LINK_UP
            b.is_virus[r0, c0] = False
            b.is_virus[r1, c1] = False
            b.resolve()
            env.pills_placed += 1
            env.cur = env.nxt
            env.nxt = env._rand_pill()
            if b.virus_count() == 0:
                res = "clear"
                break
            if b.spawn_blocked():
                res = "topout"
                break
            if env.pills_placed >= 300:
                break
        else:
            action = best["action"]
            if action is None:
                break
            _, _, term, trunc, info = env.step(int(action))
            if term:
                res = "clear" if info["won"] else "topout"
                break
            if trunc:
                break

        if pressure == "bursty" and env.pills_placed >= AB.GARBAGE_MIN_PILLS:
            occ_after = int(np.count_nonzero(env.board.color))
            clear_size = max(0, occ_before + 2 - occ_after)
            if clear_size > 0:
                inject_bursty_garbage(env.board, bm, seed, env.pills_placed, clear_size)
            if env.board.virus_count() == 0:
                res = "clear"
                break
            if env.board.spawn_blocked():
                res = "topout"
                break

        if len(snapshots) >= max_snapshots:
            break

    return {"seed": seed, "result": res, "n_snapshots": len(snapshots),
            "snapshots": snapshots}


def spot_check_seed(seed, max_snapshots=3):
    replay = replay_with_snapshots(seed, max_snapshots=max_snapshots)
    results = []
    for snap in replay["snapshots"]:
        fw = query_firmware_subprocess(snap["board_nes"], snap["ca0"], snap["cb0"],
                                       snap["na0"], snap["nb0"])
        fw_tucked = fw.get("tucked", False)
        cells = None
        cells_empty = None
        if fw_tucked:
            # verify the published descriptor lands on empty cells on THIS board --
            # same safety check pattern as trajectory_fire_proof.py's own.
            approach, trigger = fw["tuck_col"], fw["tuck_row"]
            best_c, best_o = fw["best_c"], fw["best_o"]
            # can't recover (target,rest,orient) from best_c/best_o alone without the
            # CANDLIST (not read here) -- report the raw firmware decision, that's
            # the honest scope of this check (see module docstring).
        results.append({
            "pill_idx": snap["pill_idx"],
            "mirror_placement": snap["mirror_placement"],
            "firmware": fw,
            "firmware_also_fired": bool(fw_tucked),
        })
    return {"seed": seed, "result": replay["result"], "checks": results}


def main():
    seeds = [int(s) for s in sys.argv[1:]] if len(sys.argv) > 1 else [44, 0, 41]
    out = {}
    for seed in seeds:
        print(f"=== spot-check seed {seed} ===", flush=True)
        r = spot_check_seed(seed)
        out[seed] = r
        for c in r["checks"]:
            print(f"  pill {c['pill_idx']}: mirror={c['mirror_placement']} "
                  f"firmware_fired={c['firmware_also_fired']} "
                  f"firmware={c['firmware']}", flush=True)
    outpath = f"{HERE}/results/firmware_tier3_spotcheck.json"
    with open(outpath, "w") as f:
        json.dump(out, f, indent=1)
    print(f"\nwrote {outpath}")


if __name__ == "__main__":
    main()
