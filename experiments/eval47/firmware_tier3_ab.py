#!/usr/bin/env python3
"""Milestone 4 (tuck-bfs tier-3 mission, 2026-08-05): OFFLINE FIRMWARE A/B.

run_tier_sweep.py's n=120 sweep (results/tier_sweep_bursty_n120_real.json,
commit 414a1e8) already showed tier<=3 under translatable.tier_of()'s ABSTRACT
classification is bit-for-bit indistinguishable from the reachfull2 oracle
(0/120 seeds moved). That's the ceiling -- "if the search could pick ANY
tier<=3-classified candidate, does it match the oracle." It does NOT prove the
tuck-bfs-6502 FIRMWARE delivers that value: translate_ref_tier3.py's cascade
(bit-exact-validated against the real 6502, tuck-bfs-6502 branch commit
0fc6bb8) only finds a PUBLISHABLE (approach,trigger) descriptor for 97.7% of
that tier<=3 population (1456/1490 on the 200-board corpus) -- the other 2.3%
are candidates tier_of() calls "tier<=3 reachable" but the firmware's own
safety-checked derivation correctly declines to publish (see that module's
docstring for the documented root cause: late/interleaved rotation timing a
fixed-final-orientation 2-phase descriptor can't safely express).

THIS SCRIPT measures whether that 2.3% gap costs anything in practice: a new
tier_fn, `firmware_tier_of`, wraps the ACTUAL firmware-validated cascade
(translate_ref.derive_verified for tier 1, translate_ref_tier3.
derive_tier3_verified as the fallback) instead of the abstract tier_of()
ladder, returning 1 (publishable) or TIER_UNREACHABLE-equivalent (99,
unpublishable). `play()` below is a duplicate of run_tier_sweep.py's own
play() (same "new file over refactor-in-place" convention that file's own
docstring documents), calling reach_root.choose_reach_tier(..., max_tier=1,
tier_fn=firmware_tier_of) -- reach_root.py itself is untouched (owned by
another agent mid-run; read-only import here, exactly run_tier_sweep.py's own
pattern).

Compares three arms at n=60 (the task's stated minimum): base32 (no tucks),
firmware-tier3 (this script's new arm), reachfull2 (the oracle). The already-
committed tier<=1 (today's SHIPPED vocabulary) and abstract tier<=3 numbers
from the n=120 run are cited alongside for context, not recomputed here.
"""
from __future__ import annotations
import sys
import os
import json
from concurrent.futures import ProcessPoolExecutor, as_completed

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

import reach_root as RR  # noqa: E402 -- read-only import, not edited
import reach_root_ab as AB  # noqa: E402
import bursty_model  # noqa: E402

CANON = "/home/struktured/projects/dr-mario-canonical-wt"
_TESTS = os.path.join(CANON, "tests")
if _TESTS not in sys.path:
    sys.path.insert(0, _TESTS)
import translate_ref as TR  # noqa: E402 (cross-repo: dr-mario-canonical-wt, same
                             # sys.path pattern translatable.py already uses)
import translate_ref_tier3 as T3R  # noqa: E402

SEEDS = 60
WORKERS = 6
LEVEL = 11
EMPTY_NES = 0xFF


def _to_nes_board(col):
    return [EMPTY_NES if int(c) == 0 else int(c) for c in col]


def _unpack(candidate):
    if isinstance(candidate, dict):
        return int(candidate["col"]), int(candidate["row"]), int(candidate["orient"])
    target, rest, orient = candidate
    return int(target), int(rest), int(orient)


def firmware_tier_of(col, candidate):
    """tier_fn(col, candidate) -> int, matching reach_root.py's contract
    exactly (2 positional args). 1 if the ACTUAL firmware-validated cascade
    (tier 1 then tier 3, bit-exact vs tuck_bfs_tier3_6502.py) finds a
    publishable descriptor, else 99 (never <= any real max_tier, same
    TIER_UNREACHABLE convention translatable.py's own tier_of() uses and for
    the same reason -- see that module's CONTRACT note)."""
    target, rest, orient = _unpack(candidate)
    board = _to_nes_board(col)
    visited = TR.row_bfs_visited(board)
    if TR.derive_verified(board, target, rest, orient, visited) is not None:
        return 1
    mono_L = T3R.mono_reach(board, "L")
    mono_R = T3R.mono_reach(board, "R")
    if T3R.derive_tier3_verified(board, target, rest, orient, visited, mono_L, mono_R) is not None:
        return 1
    return 99


_C = {}


def _init(level, pressure, bursty_model_obj=None):
    RR._lazy()
    _C.update(level=level, pressure=pressure, bursty_model_obj=bursty_model_obj)


def play(seed):
    """Duplicate of run_tier_sweep.py's play() (same bursty injection rule,
    dies_ahead threshold, tuck-cell execution convention), with tier_fn fixed
    to firmware_tier_of and max_tier=1 (firmware_tier_of only ever returns 1
    or 99, so max_tier=1 is the correct -- and only meaningful -- threshold)."""
    import numpy as np
    from drmario.faithful_env import FaithfulDrMarioEnv
    from drmario.faithful_game import LINK_LEFT, LINK_RIGHT, LINK_UP, LINK_DOWN
    from nes_pills import NesPillSource

    level, pressure = _C["level"], _C["pressure"]
    bursty_model_obj = _C.get("bursty_model_obj")
    if pressure == "bursty":
        from bursty_model import inject_bursty_garbage

    L = RR._lazy()
    FB, RS = L["FB"], L["RS"]

    env = FaithfulDrMarioEnv(level=level, seed=seed, max_pills=300)
    env.reset()
    NesPillSource(seed=seed).attach(env)
    env.cur = env._rand_pill()
    env.nxt = env._rand_pill()

    res = "stall"
    fired_tuck = 0
    garbage_injected = 0
    v_at_topout = None

    for _ in range(300):
        fb = FB.from_board(env.board)
        if env.board.virus_count() == 0:
            res = "clear"
            break
        col, vir = RS.board_flat_from_fb(fb)
        ca, cb, na, nb = int(env.cur.a), int(env.cur.b), int(env.nxt.a), int(env.nxt.b)
        best = RR.choose_reach_tier(fb, col, vir, ca, cb, na, nb, 1,
                                    tier_fn=firmware_tier_of)

        occ_before = int(np.count_nonzero(env.board.color)) if pressure == "bursty" else 0

        if best["kind"] == "tuck":
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
            fired_tuck += 1
            if b.virus_count() == 0:
                res = "clear"
                break
            if b.spawn_blocked():
                res = "topout"
                v_at_topout = b.virus_count()
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
                if res == "topout":
                    v_at_topout = env.board.virus_count()
                break
            if trunc:
                break

        if pressure == "bursty" and env.pills_placed >= AB.GARBAGE_MIN_PILLS:
            occ_after = int(np.count_nonzero(env.board.color))
            clear_size = max(0, occ_before + 2 - occ_after)
            if clear_size > 0:
                landed = inject_bursty_garbage(
                    env.board, bursty_model_obj, seed, env.pills_placed, clear_size)
                garbage_injected += landed
            if env.board.virus_count() == 0:
                res = "clear"
                break
            if env.board.spawn_blocked():
                res = "topout"
                v_at_topout = env.board.virus_count()
                break

    dies_ahead = int(res == "topout" and v_at_topout is not None
                      and v_at_topout <= AB.DIES_AHEAD_VIRUS_THRESHOLD)
    return {"seed": seed, "won": int(res == "clear"), "topout": int(res == "topout"),
            "stall": int(res == "stall"), "pills": env.pills_placed,
            "fired_tuck": fired_tuck, "garbage_injected": garbage_injected,
            "viruses_left_at_end": v_at_topout if v_at_topout is not None else env.board.virus_count(),
            "dies_ahead": dies_ahead}


def run_firmware_arm(level, seeds, workers, pressure, bursty_model_obj):
    rows = []
    with ProcessPoolExecutor(max_workers=workers, initializer=_init,
                             initargs=(level, pressure, bursty_model_obj)) as ex:
        futs = [ex.submit(play, s) for s in range(seeds)]
        for i, f in enumerate(as_completed(futs)):
            rows.append(f.result())
            if (i + 1) % max(1, seeds // 5) == 0 or (i + 1) == seeds:
                print(f"  firmware-tier3 {i + 1}/{seeds}", flush=True)
    return {r["seed"]: r for r in rows}


def main():
    bursty_model_obj = bursty_model.fit_struktured_20260804()
    bursty_model_obj.meta = {k: v for k, v in bursty_model_obj.meta.items() if k != "raw_events"}
    print(f"=== firmware tier-3 A/B, L{LEVEL}, n={SEEDS}, pressure=bursty ===", flush=True)

    base32 = AB.run_arm(LEVEL, SEEDS, WORKERS, "base32", "bursty", bursty_model_obj)
    reachfull2 = AB.run_arm(LEVEL, SEEDS, WORKERS, "reachfull2", "bursty", bursty_model_obj)
    firmware = run_firmware_arm(LEVEL, SEEDS, WORKERS, "bursty", bursty_model_obj)

    print()
    s_base = AB.compare(base32, firmware, "firmware-tier3 vs base32     ")
    s_oracle = AB.compare(reachfull2, firmware, "firmware-tier3 vs reachfull2")

    base_bad = sum(base32[s]["topout"] + base32[s]["stall"] for s in base32)
    oracle_bad = sum(reachfull2[s]["topout"] + reachfull2[s]["stall"] for s in reachfull2)
    fw_bad = sum(firmware[s]["topout"] + firmware[s]["stall"] for s in firmware)
    oracle_rescue = base_bad - oracle_bad
    fw_rescue = base_bad - fw_bad
    survival = fw_rescue / oracle_rescue if oracle_rescue else float("nan")

    n_fw_fires = sum(firmware[s]["fired_tuck"] for s in firmware)
    print(f"\n=== bad-ends summary ===")
    print(f"base32 bad-ends={base_bad}  reachfull2(oracle) bad-ends={oracle_bad}  "
          f"firmware-tier3 bad-ends={fw_bad}")
    print(f"oracle rescue={oracle_rescue}  firmware-tier3 rescue={fw_rescue}  "
          f"survival_of_oracle_rescue={survival:.1%}")
    print(f"firmware-tier3 total fires across {SEEDS} seeds: {n_fw_fires}")

    out = {"n_seeds": SEEDS, "vs_base32": s_base, "vs_reachfull2": s_oracle,
           "base32_bad_ends": base_bad, "reachfull2_bad_ends": oracle_bad,
           "firmware_tier3_bad_ends": fw_bad, "oracle_rescue": oracle_rescue,
           "firmware_tier3_rescue": fw_rescue, "survival_of_oracle_rescue": survival,
           "firmware_tier3_total_fires": n_fw_fires}
    out_path = f"{HERE}/results/firmware_tier3_ab_n{SEEDS}.json"
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    with open(out_path, "w") as fh:
        json.dump(out, fh, indent=1)
    print(f"\nwrote {out_path}")
    print("\nDONE")


if __name__ == "__main__":
    main()
