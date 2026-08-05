#!/usr/bin/env python3
"""#17 enumerator convergence step 2: characterize the SET DIFFERENCE between
RS.tuck_root_candidates (the proof's enumerator) and tuck_scan_v3 (the
validated firmware scanner) on boards from real played games.

The union A/B proved the union is worth −20.02 vs −12.94 for RS-only; to
extend tuck_scan_v3 with the RS-only class (and understand what RS lacks),
we need to know WHAT each side uniquely enumerates: orientation split,
resting-row depth, approach shape. This drives the scanner design instead of
guessing.

Boards: play ~N games with the fast base-only decider (winner variant), at
every decision enumerate both sets, normalize physically, and bucket.
"""
from __future__ import annotations

import sys
import os
from collections import Counter

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = "/home/struktured/projects/dr_mario_rl"
QA = "/home/struktured/projects/dr-mario-qa-wt/experiments"
QA_TUCK = "/home/struktured/projects/dr-mario-qa-wt/fpga/copro/tuck_validation"
for _p in (HERE, ROOT + "/tmp/combo_term", ROOT + "/tmp/endgame", ROOT + "/tmp/tuck",
           ROOT + "/tmp/pillrng", ROOT + "/.claude/worktrees/faithful-sim/src", QA,
           QA + "/bitexact_gate", QA_TUCK):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import numpy as np
import fast_rtl_x as FX
import root_search as RS
from fast_sim_x import NCELL, _expand_core
from tuck_scan_v3_ref import ref_tuck_scan_v3, candidate_cells, H, V, RH, RV
from common import arrays_to_nes

FLIP = {H: 0, V: 1, RH: 1, RV: 0}
ONAME = {H: "H", V: "V", RH: "RH", RV: "RV"}


def _norm(cells, colors):
    r0, c0, r1, c1 = cells
    a, b = colors
    return tuple(sorted([(r0, c0, int(a)), (r1, c1, int(b))]))


def _choose_base(col, vir, ca, cb, na, nb, w, fl):
    c1 = np.empty(NCELL, dtype=np.int8)
    v1 = np.empty(NCELL, dtype=np.int8)
    best_val, best_a = None, None
    for o4 in range(4):
        var = int(FX._VAR_OF_O4[o4])
        for cc in range(8):
            ok, nv, cells = _expand_core(col, vir, var, cc, ca, cb, c1, v1)
            if ok == 0:
                continue
            val = RS._root_value(c1, v1, nv, cells, na, nb, 8,
                                 FX._W_EXCAV_SHIP, FX._W_HANG_SHIP, w, fl)
            if best_val is None or val > best_val:
                best_val, best_a = val, var * 8 + cc
    return best_a


def main(games=20, level=11):
    from drmario.faithful_env import FaithfulDrMarioEnv
    from nes_pills import NesPillSource
    from fb import FB

    FX.warmup_ship_eh(topk2=8)
    w, fl = FX.variant("winner")

    shared = rs_only = fw_only = 0
    rs_only_orient = Counter()
    fw_only_orient = Counter()
    rs_only_height = Counter()   # resting row of the LOWER cell (15 = floor)
    fw_only_height = Counter()
    decisions = 0

    for seed in range(games):
        env = FaithfulDrMarioEnv(level=level, seed=seed, max_pills=300)
        env.reset()
        NesPillSource(seed=seed).attach(env)
        env.cur = env._rand_pill()
        env.nxt = env._rand_pill()
        for _ in range(300):
            fb = FB.from_board(env.board)
            if env.board.virus_count() == 0:
                break
            col, vir = RS.board_flat_from_fb(fb)
            ca, cb = int(env.cur.a), int(env.cur.b)
            na, nb = int(env.nxt.a), int(env.nxt.b)

            rs = RS.tuck_root_candidates(fb, ca, cb, 12, True)
            rs_map = {}
            for p in rs:
                rs_map[_norm(p["cells"], p["colors"])] = p
            board = arrays_to_nes(col, vir)
            fw_cands, _ = ref_tuck_scan_v3(board)
            fw_map = {}
            for c in fw_cands:
                r0, c0, r1, c1 = candidate_cells(c["target"], c["rest"], c["orient"])
                fp = FLIP[c["orient"]]
                col0, col1 = (ca, cb) if fp == 0 else (cb, ca)
                fw_map[_norm((r0, c0, r1, c1), (col0, col1))] = c

            ks_rs, ks_fw = set(rs_map), set(fw_map)
            shared += len(ks_rs & ks_fw)
            decisions += 1
            for k in ks_rs - ks_fw:
                rs_only += 1
                cells = [t[:2] for t in k]
                vert = cells[0][1] == cells[1][1]
                rs_only_orient["V" if vert else "H"] += 1
                rs_only_height[max(t[0] for t in cells)] += 1
            for k in ks_fw - ks_rs:
                fw_only += 1
                c = fw_map[k]
                fw_only_orient[ONAME[c["orient"]]] += 1
                cells = [t[:2] for t in k]
                fw_only_height[max(t[0] for t in cells)] += 1

            a = _choose_base(col, vir, ca, cb, na, nb, w, fl)
            if a is None:
                break
            _, _, term, trunc, _info = env.step(int(a))
            if term or trunc:
                break
        print(f"seed {seed} done ({decisions} cumulative decisions)", flush=True)

    tot = shared + rs_only + fw_only
    print(f"\n=== SET DIFFERENCE over {decisions} decisions ({games} games) ===")
    print(f"candidates: shared {shared} ({shared/max(tot,1):.0%})  "
          f"RS-only {rs_only} ({rs_only/max(tot,1):.0%})  "
          f"FW-only {fw_only} ({fw_only/max(tot,1):.0%})")
    print(f"RS-only by orientation: {dict(rs_only_orient)}")
    print(f"FW-only by orientation: {dict(fw_only_orient)}")
    print(f"RS-only by lower-cell row (15=floor): "
          f"{dict(sorted(rs_only_height.items()))}")
    print(f"FW-only by lower-cell row: {dict(sorted(fw_only_height.items()))}")


if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--games", type=int, default=20)
    a = ap.parse_args()
    main(a.games)
