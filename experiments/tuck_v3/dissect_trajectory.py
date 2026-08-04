#!/usr/bin/env python3
"""Task #17 DISSECTION (the saga doc's 'Dissection plan' made real): matched-board
per-decision comparison of the FIRMWARE decider vs the MIRROR decider ALONG REAL
FIRMWARE TRAJECTORIES.

Drives whole games with firmware_decider.FirmwareDecider (tuck=1, theta=150 -- the
mirror's PEAK config, and the config the pooled n=240 firmware A/B washed at). At
EVERY decision point, before committing the firmware's move, also asks
mirrored_leaf.choose_root_with_tucks_mirrored (same theta) what it would do on the
IDENTICAL board+pills, and scores the firmware's own chosen action under the mirror
ruler. The game then follows the FIRMWARE pick, so the state distribution is the
firmware's real played distribution -- exactly what the 20-board frozen harvest could
not sample.

Per decision, logs (JSONL, one row per decision):
  seed, pill (index), vc (viruses), regime (open/mid/end per ab_root_firmware's own
  vc>32 / vc>8 convention), maxh (tallest column height, rows-from-floor),
  fw_kind, mir_kind, cls (match class), and under the MIRROR ruler:
    mir_val        -- value of the mirror's own pick (the per-board optimum)
    mirval_fw      -- value of the FIRMWARE's pick
    regret         -- mir_val - mirval_fw  (>=0 means fw left value on the table)
    mir_base       -- mirror's best base value (margin denominator)
    fw_in_mir_cands -- for fw tucks: is the fired (cells,colors) even IN the mirror's
                       candidate list? (fw enumerates via tuck_scan_v3, mirror via
                       RS.tuck_root_candidates -- a membership miss here is an
                       ENUMERATOR-SET divergence, a class the saga's plan never had
                       visibility into)

Match classes: base_same / base_diff / tuck_same / tuck_diff / fw_tuck_mir_base /
fw_base_mir_tuck.

The analysis (dissect_analyze.py) then answers the saga's question 2 directly:
are firmware fires systematically lower-margin under the true ruler, do the
disagreement classes cluster by regime/height, and how much total mirror-value does
the firmware bleed per game vs the 2/20-static-flip prediction.

Usage: dissect_trajectory.py --seeds 40 --level 11 --workers 8 --out dissect_L11
"""
from __future__ import annotations

import sys
import os
import json
import argparse
from concurrent.futures import ProcessPoolExecutor, as_completed

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = "/home/struktured/projects/dr_mario_rl"
QA = "/home/struktured/projects/dr-mario-qa-wt/experiments"
for _p in (HERE, ROOT + "/tmp/combo_term", ROOT + "/tmp/endgame", ROOT + "/tmp/tuck",
           ROOT + "/tmp/pillrng", ROOT + "/.claude/worktrees/faithful-sim/src", QA,
           QA + "/bitexact_gate"):
    if _p not in sys.path:
        sys.path.insert(0, _p)

_C = {}

THETA = 150   # the mirror's peak AND the firmware A/B's tested config -- one config,
              # both deciders, no cross-theta confounds.


def _init(level, theta=THETA):
    """Once per worker: env vars BEFORE any firmware import (the documented
    module-import-time caching hazard), then the expensive loads."""
    os.environ["DRCOPRO_TUCKV3"] = "1"
    os.environ["DRCOPRO_ARM"] = "1"
    os.environ["DRFIX"] = "1"
    os.environ["DRCHAIN"] = "180"
    from firmware_decider import FirmwareDecider
    fd = FirmwareDecider(drchain=180, drfix=1, arm=1, tuck=1, theta=theta)
    import fast_rtl_x as FX
    FX.warmup_ship_eh(topk2=8)
    w, fl = FX.variant("winner")
    _C.update(level=level, theta=theta, fd=fd, w=w)


def _maxh(col):
    """Tallest column height in rows-from-floor. col is the int8[128] flat board,
    row-major r*8+c with row 0 at the TOP (root_search convention); height of a
    column = 16 - topmost occupied row index."""
    best = 0
    for c in range(8):
        for r in range(16):
            if col[r * 8 + c] != 0:
                best = max(best, 16 - r)
                break
    return best


def _norm_tuck(cells, colors):
    """Canonical form of a tuck placement for identity comparison: sort the two
    (r,c,colour) cell tuples so H/RH and V/RV descriptions of the same physical
    result compare equal."""
    r0, c0, r1, c1 = cells
    a, b = colors
    return tuple(sorted([(r0, c0, int(a)), (r1, c1, int(b))]))


def _classify(fw, mir):
    if fw["kind"] == "base" and mir["kind"] == "base":
        return "base_same" if fw["action"] == mir["action"] else "base_diff"
    if fw["kind"] == "tuck" and mir["kind"] == "base":
        return "fw_tuck_mir_base"
    if fw["kind"] == "base" and mir["kind"] == "tuck":
        return "fw_base_mir_tuck"
    fw_t = _norm_tuck(fw["placement"]["cells"], (fw["ca"], fw["cb"]))
    mir_t = _norm_tuck(mir["placement"]["cells"], mir["placement"]["colors"])
    return "tuck_same" if fw_t == mir_t else "tuck_diff"


def _mirval_of_pick(pick, col, vir, ca, cb, na, nb, w):
    """Score an arbitrary pick (either decider's) under the MIRROR ruler, by
    re-expanding its resulting board and calling root_value_mirrored -- the same
    arithmetic choose_root_with_tucks_mirrored applies to its own candidates."""
    import numpy as np
    import fast_rtl_x as FX
    import root_search as RS
    import mirrored_leaf as ML
    from fast_sim_x import NCELL, _expand_core

    c1 = np.empty(NCELL, dtype=np.int8)
    v1 = np.empty(NCELL, dtype=np.int8)
    if pick["kind"] == "base":
        a = pick["action"]
        var, cc = a // 8, a % 8
        ok, nv, cells = _expand_core(col, vir, var, cc, ca, cb, c1, v1)
        if ok == 0:
            return None   # fw chose an action the mirror physics call illegal --
                          # log as its own anomaly, do not crash the trajectory
    else:
        r0, c0, r1, c1_ = pick["placement"]["cells"]
        if "colors" in pick.get("placement", {}):
            col0, col1 = pick["placement"]["colors"]
        else:
            col0, col1 = pick["ca"], pick["cb"]
        nv, cells = RS._expand_core_at(col, vir, r0, c0, r1, c1_, col0, col1, c1, v1)
    return float(ML.root_value_mirrored(c1, v1, nv, cells, na, nb, 8,
                                        FX._W_EXCAV_SHIP, FX._W_HANG_SHIP, w))


def play(seed):
    from drmario.faithful_env import FaithfulDrMarioEnv
    from drmario.faithful_game import LINK_LEFT, LINK_RIGHT, LINK_UP, LINK_DOWN
    from nes_pills import NesPillSource
    from fb import FB
    import root_search as RS
    import mirrored_leaf as ML

    fd, w, theta = _C["fd"], _C["w"], _C["theta"]
    env = FaithfulDrMarioEnv(level=_C["level"], seed=seed, max_pills=300)
    env.reset()
    NesPillSource(seed=seed).attach(env)
    env.cur = env._rand_pill()
    env.nxt = env._rand_pill()

    rows = []
    res = "stall"
    while True:
        fb = FB.from_board(env.board)
        vc = env.board.virus_count()
        if vc == 0:
            res = "clear"
            break
        col, vir = RS.board_flat_from_fb(fb)
        ca, cb, na, nb = int(env.cur.a), int(env.cur.b), int(env.nxt.a), int(env.nxt.b)

        fw = fd.decide(col, vir, ca, cb, na, nb)
        if fw is None:
            res = "stall"
            break

        # SHADOW: the mirror on the identical board. Enumerate the mirror's tuck
        # candidates ONCE here (not inside choose) so the same list also serves the
        # enumerator-membership check below.
        mir_cands = RS.tuck_root_candidates(fb, ca, cb, 12, True)
        mir = ML.choose_root_with_tucks_mirrored(fb, env.cur, env.nxt, w, topk2=8,
                                                 tuck_cands=mir_cands, theta=theta)

        cls = _classify(fw, mir)
        mirval_fw = (mir["val"] if cls in ("base_same", "tuck_same")
                     else _mirval_of_pick(fw, col, vir, ca, cb, na, nb, w))
        fw_in_mir_cands = None
        if fw["kind"] == "tuck":
            fw_t = _norm_tuck(fw["placement"]["cells"], (fw["ca"], fw["cb"]))
            fw_in_mir_cands = any(
                _norm_tuck(p["cells"], p["colors"]) == fw_t for p in mir_cands)

        rows.append({
            "seed": seed, "pill": env.pills_placed, "vc": vc,
            "regime": "open" if vc > 32 else ("mid" if vc > 8 else "end"),
            "maxh": _maxh(col),
            "fw_kind": fw["kind"], "mir_kind": mir["kind"], "cls": cls,
            "mir_val": float(mir["val"]),
            "mirval_fw": mirval_fw,
            "regret": (float(mir["val"]) - mirval_fw) if mirval_fw is not None else None,
            "mir_base": (float(mir["best_base_val"])
                         if mir.get("best_base_val") is not None else None),
            "fw_in_mir_cands": fw_in_mir_cands,
            "fw_desc": (fw["action"] if fw["kind"] == "base"
                        else list(fw["placement"]["cells"])),
            "mir_desc": (mir["action"] if mir["kind"] == "base"
                         else list(mir["placement"]["cells"])),
        })

        # COMMIT the FIRMWARE pick -- the trajectory is the firmware's own.
        if fw["kind"] == "tuck":
            r0, c0, r1, c1 = fw["placement"]["cells"]
            b = env.board
            b.color[r0, c0] = fw["ca"]
            b.color[r1, c1] = fw["cb"]
            if r0 == r1:
                b.link[r0, c0] = LINK_RIGHT; b.link[r1, c1] = LINK_LEFT
            else:
                b.link[r0, c0] = LINK_DOWN; b.link[r1, c1] = LINK_UP
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
            continue

        _, _, term, trunc, info = env.step(int(fw["action"]))
        if term:
            res = "clear" if info["won"] else "topout"
            break
        if trunc:
            break

    return {"seed": seed, "res": res, "pills": env.pills_placed, "rows": rows}


def _log_rss(tag):
    import subprocess
    try:
        out = subprocess.run(
            ["bash", "-c", "ps -o rss= -C python 2>/dev/null | awk '{s+=$1} END {print s+0}'"],
            capture_output=True, text=True, timeout=10)
        rss_kb = int(out.stdout.strip() or "0")
        print(f"  [RSS] {tag}: {rss_kb/1024:.0f} MB across all python processes", flush=True)
    except Exception as e:
        print(f"  [RSS] {tag}: measurement failed ({e})", flush=True)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--seeds", type=int, default=40)
    ap.add_argument("--seed-offset", type=int, default=0)
    ap.add_argument("--level", type=int, default=11)
    ap.add_argument("--workers", type=int, default=8)
    ap.add_argument("--out", type=str, required=True)
    a = ap.parse_args()

    print(f"=== DISSECTION: firmware-trajectory matched comparison, L{a.level}, "
          f"seeds {a.seed_offset}..{a.seed_offset + a.seeds - 1}, theta={THETA} ===",
          flush=True)
    games = []
    with ProcessPoolExecutor(max_workers=a.workers, initializer=_init,
                             initargs=(a.level,)) as ex:
        futs = [ex.submit(play, s)
                for s in range(a.seed_offset, a.seed_offset + a.seeds)]
        for i, f in enumerate(as_completed(futs)):
            g = f.result()
            games.append(g)
            print(f"  seed {g['seed']}: {g['res']} in {g['pills']} pills, "
                  f"{len(g['rows'])} decisions logged", flush=True)
            if (i + 1) % max(1, a.seeds // 10) == 0 or (i + 1) == a.seeds:
                _log_rss(f"after {i + 1}/{a.seeds} games")

    fn = f"{a.out}.jsonl"
    with open(fn, "w") as fh:
        for g in sorted(games, key=lambda g: g["seed"]):
            for r in g["rows"]:
                fh.write(json.dumps(r) + "\n")
            fh.write(json.dumps({"seed": g["seed"], "GAME_END": g["res"],
                                 "pills": g["pills"]}) + "\n")
    print(f"wrote {fn} ({sum(len(g['rows']) for g in games)} decision rows, "
          f"{len(games)} games)", flush=True)


if __name__ == "__main__":
    main()
