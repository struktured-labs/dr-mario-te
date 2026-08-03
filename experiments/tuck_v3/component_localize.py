#!/usr/bin/env python3
"""20-board component-level localization (task #17 stage 3, team-lead directive after
the theta sweep washed at {150,250,400}): for the SAME tuck candidate on the SAME board,
compare offline root_search.py values component-by-component (imm1, leaf1, ply-2 best
[raw], DISC blend, eh add-on, total) against the REAL FIRMWARE's readbacks for the exact
same components -- ALSO for the base argmax on the same board (already proven to match
through the RTL NODE path by the stage-2 value-equivalence gate; if base matches here too
and tuck diverges, the divergence lives in the SOFT scoring path, not the RTL).

OFFLINE SIDE: `_components()` below is a byte-for-byte COPY of root_search.py's
`_ply2plus_value_ship_eh` (never modified -- that function is the already-validated
offline scorer; this file must not become a second, quietly-diverging copy of the real
one used by the theta sweep's own offline reference), except it returns the five
intermediate terms (leaf1, best2_raw, blend, eh, total_rest) instead of only the final
scalar. Verified against the real function on real boards before trusting it (see
verify_matches_offline() below) -- a silently-wrong "instrumented copy" would invalidate
every comparison this file produces.

FIRMWARE SIDE: reuses the canonical fpga/copro/tuck_v3.py + tests/test_search_d3.py
directly (same combined-image pattern as tuck_validation/test_tuck_root_extension.py):
  - BASE argmax components: `search()` run once with test_search_d3.DEBUG_VAL1=True
    (extended this session -- canonical commit pending -- to also carry imm1/leaf1/eh per
    ply-1 candidate, not just C1/O1/V1/B2), then look up the ring entry whose (C1,O1)
    equals the winning (D_BC,D_BO).
  - TUCK candidate components: a TARGETED single-candidate score (tuck_cell_prep ->
    land_place_at -> resolve_capped -> tuck_imm1 -> tuck_slot0_inject -> tuck_ply2_score,
    the exact sequence tuck_validation/test_tuck_ply2_score.py already validates
    bit-exact) for the SPECIFIC (target,rest,orient) the offline model proposed --
    D_I1L/D_I1H, D_L1L/D_L1H, D_B2L/D_B2H, D_ADL/D_ADH, D_V1L/D_V1H are the SAME
    zero-page cells the base search uses (tuck_ply2_score's k_done block is a verified
    byte-for-byte mirror of the base's), so no new readback wiring is needed there.

BOARD SOURCE: real capsule-stream play (FaithfulDrMarioEnv + NesPillSource, never
uniform-random, per house rules) using root_search.choose_root_with_tucks at theta=0 as
the decider, collecting every decision where a tuck won, ranked by margin (val - best_
base_val) descending -- the top 20 are "boards where the offline model scored a tuck
child well above base", as directed.
"""
from __future__ import annotations

import os
import sys
import importlib.util

ROOT = "/home/struktured/projects/dr_mario_rl"
QA = "/home/struktured/projects/dr-mario-qa-wt/experiments"
CANON = "/home/struktured/projects/dr-mario-canonical-wt"
HERE = os.path.dirname(os.path.abspath(__file__))
for _p in (ROOT + "/tmp/combo_term", ROOT + "/tmp/endgame", ROOT + "/tmp/tuck",
           ROOT + "/.claude/worktrees/faithful-sim/src", QA, HERE,
           os.path.join(CANON, "fpga", "copro"), os.path.join(CANON, "tests")):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import numpy as np
from numba import njit, int8, int32, int64, float64

import fast_rtl_x as FX
from fast_sim_x import NCELL, _expand_core, _virus_count, _stable_desc
import root_search as RS
from fb import FB


# ============================================================= offline components ===
@njit(cache=True, fastmath=False)
def _components(c1, v1, na, nb, topk2, w_excav, w_hang, w, fl):
    """Byte-for-byte copy of root_search._ply2plus_value_ship_eh's BODY (never edit one
    without the other -- see module docstring), returning (leaf1, best2_raw, blend, eh,
    total_rest) instead of just total_rest. Caller must not call when virus_count(v1)==0
    (unchanged precondition from the original)."""
    b2col = np.empty((32, NCELL), dtype=int8)
    b2vir = np.empty((32, NCELL), dtype=int8)
    keys2 = np.empty(32, dtype=float64)
    imms2 = np.empty(32, dtype=int64)
    order2 = np.empty(32, dtype=int32)
    s2c = np.empty(NCELL, dtype=int8)
    s2v = np.empty(NCELL, dtype=int8)
    e2c = np.empty(NCELL, dtype=int8)
    e2v = np.empty(NCELL, dtype=int8)
    m2 = 0
    for o42 in range(4):
        var2 = FX._VAR_OF_O4[o42]
        for col2 in range(8):
            ok2, nv2, cells2 = _expand_core(c1, v1, var2, col2, na, nb, s2c, s2v)
            if ok2 == 0:
                continue
            imm2 = (int64(w[FX.R_WVIR]) * nv2 + int64(w[FX.R_WCELLS]) * cells2
                    + (int64(w[FX.R_VBONUS]) if nv2 >= 2 else int64(0)))
            keys2[m2] = float64(imm2 + FX._leafv_ship(s2c, s2v, w, fl))
            imms2[m2] = imm2
            for i in range(NCELL):
                b2col[m2, i] = s2c[i]
                b2vir[m2, i] = s2v[i]
            m2 += 1
    leaf1 = FX._leafv_ship(c1, v1, w, fl)
    if m2 == 0:
        best2 = int64(0)          # no ply-2 legal moves: matches the offline "val_rest =
        blend = leaf1              # leaf1" branch: best2 undefined/unused, blend = leaf1.
    else:
        _stable_desc(keys2, m2, order2)
        kk2 = m2 if topk2 <= 0 or topk2 > m2 else topk2
        best2 = int64(0)
        have2 = False
        for s2 in range(kk2):
            k2 = order2[s2]
            for i in range(NCELL):
                e2c[i] = b2col[k2, i]
                e2v[i] = b2vir[k2, i]
            if _virus_count(e2v) == 0:
                v2 = imms2[k2] + int64(FX._WIN_SHIP)
            else:
                v2 = imms2[k2] + FX._expected_third_ship(e2c, e2v, w, fl)
            if not have2 or v2 > best2:
                best2 = v2
                have2 = True
        blend = leaf1 + ((best2 - leaf1) >> int64(1))
    eh = w_excav * FX._g_excav_ship(c1, v1) + w_hang * FX._g_hang_ship(c1, v1)
    total_rest = blend + eh
    return leaf1, best2, blend, eh, total_rest


def root_components(col, vir, nv, cells, na, nb, topk2, w_excav, w_hang, w, fl):
    """imm1 + _components(...), mirroring root_search._root_value's shape but returning
    every intermediate. Only valid for the non-WIN branch (virus_count(vir) > 0) -- the
    20-board sample is filtered to real mid-game boards, never a last-virus WIN, so this
    is not exercised there; asserted defensively anyway."""
    assert _virus_count(vir) > 0, "root_components: WIN branch not supported (imm1+WIN only)"
    imm1 = (float(w[FX.R_WVIR]) * nv + float(w[FX.R_WCELLS]) * cells
            + (float(w[FX.R_VBONUS]) if nv >= 2 else 0.0))
    leaf1, best2, blend, eh, total_rest = _components(
        col, vir, int64(na), int64(nb), int64(topk2), int64(w_excav), int64(w_hang), w, fl)
    return {
        "imm1": imm1, "leaf1": float(leaf1), "best2_raw": float(best2),
        "blend": float(blend), "eh": float(eh), "total": imm1 + float(total_rest),
    }


def verify_matches_offline(n=200, seed=20260803):
    """`_components` must reproduce root_search._ply2plus_value_ship_eh's SCALAR exactly
    on random legal ply-1 boards -- proof this instrumented copy did not quietly drift
    from the real function it stands in for. Required before trusting ANY comparison
    this file produces."""
    rng = np.random.RandomState(seed)
    FX.warmup_ship_eh(topk2=8)
    w, fl = FX.variant("winner")
    mism = 0
    for i in range(n):
        col = rng.randint(0, 4, size=NCELL).astype(np.int8)
        vir = np.zeros(NCELL, dtype=np.int8)
        # a handful of viruses so the non-WIN branch is exercised
        for _ in range(6):
            j = rng.randint(0, NCELL)
            if col[j] != 0:
                vir[j] = 1
        if _virus_count(vir) == 0:
            vir[rng.randint(0, NCELL)] = 1
            if col[np.argmax(vir)] == 0:
                col[np.argmax(vir)] = 1
        na, nb = int(rng.randint(1, 4)), int(rng.randint(1, 4))
        ref = RS._ply2plus_value_ship_eh(col, vir, na, nb, 8, FX._W_EXCAV_SHIP,
                                          FX._W_HANG_SHIP, w, fl)
        _, _, _, _, total_rest = _components(col, vir, na, nb, 8, FX._W_EXCAV_SHIP,
                                              FX._W_HANG_SHIP, w, fl)
        if int(ref) != int(total_rest):
            mism += 1
            print(f"  MISMATCH board {i}: ref={ref} components_total={total_rest}")
    print(f"verify_matches_offline: {n - mism}/{n} match")
    return mism == 0


# ==================================================================== decision + harvest ===
def choose_with_base_argmax(fb, cur, nxt, w, fl, topk2=8,
                             w_excav=FX._W_EXCAV_SHIP, w_hang=FX._W_HANG_SHIP,
                             frames_per_row=12, exec_only=True, tuck_cands=None, theta=0.0):
    """Mirrors root_search.choose_root_with_tucks EXACTLY (same loops, same helper calls,
    same theta gate), but ALSO returns the base argmax's own (var, col, c1, v1, nv, cells)
    -- root_search.py's own function only keeps best_base_val (the scalar), not which
    action produced it, so there is no way to recover the base argmax's board/component
    breakdown from its return value alone. Written as a parallel function (not a change to
    root_search.py, which is the already-validated function the theta sweep's own offline
    reference used and must not be perturbed) that reuses the identical already-validated
    helpers (_expand_core, _expand_core_at, _root_value, tuck_root_candidates)."""
    col = np.frombuffer(bytes(fb.col), dtype=np.uint8).astype(np.int8)
    vir = np.frombuffer(bytes(fb.vir), dtype=np.uint8).astype(np.int8)
    ca, cb, na, nb = int(cur.a), int(cur.b), int(nxt.a), int(nxt.b)

    c1 = np.empty(NCELL, dtype=np.int8)
    v1 = np.empty(NCELL, dtype=np.int8)
    best_val = None
    best = None
    base_argmax = None   # (var, cc, c1.copy(), v1.copy(), nv, cells)

    for o4 in range(4):
        var = int(FX._VAR_OF_O4[o4])
        for cc in range(8):
            ok, nv, cells = _expand_core(col, vir, var, cc, ca, cb, c1, v1)
            if ok == 0:
                continue
            val = RS._root_value(c1, v1, nv, cells, na, nb, topk2, w_excav, w_hang, w, fl)
            if best_val is None or val > best_val:
                best_val = val
                best = {"kind": "base", "action": var * 8 + cc, "val": val}
                base_argmax = (var, cc, c1.copy(), v1.copy(), int(nv), int(cells))

    best_base_val = best_val

    if tuck_cands is None:
        tuck_cands = RS.tuck_root_candidates(fb, ca, cb, frames_per_row, exec_only)
    n_legal = 0
    for p in tuck_cands:
        r0, c0, r1, c1_ = p["cells"]
        col0, col1 = p["colors"]
        nv, cells = RS._expand_core_at(col, vir, r0, c0, r1, c1_, col0, col1, c1, v1)
        val = RS._root_value(c1, v1, nv, cells, na, nb, topk2, w_excav, w_hang, w, fl)
        n_legal += 1
        if best_base_val is not None and val < best_base_val + theta:
            continue
        if best_val is None or val > best_val:
            best_val = val
            best = {"kind": "tuck", "placement": p, "ca": col0, "cb": col1, "val": val,
                    "margin": val - best_base_val if best_base_val is not None else None}

    best["n_tuck_cands"] = len(tuck_cands)
    best["n_tuck_legal"] = n_legal
    best["best_base_val"] = best_base_val
    return best, base_argmax


def harvest_boards(n_target=20, seeds=range(0, 400), level=11, max_pills=300):
    """Plays real capsule-stream games (FaithfulDrMarioEnv + NesPillSource, never
    uniform-random) at theta=0.0 with the offline decider, collecting every decision
    where a tuck won, ranked by margin (val - best_base_val) descending. Returns the top
    n_target -- "boards where the offline model scored a tuck child well above base", as
    directed. Executes EVERY decision (base or tuck) to advance the game, exactly
    mirroring ab_root_firmware.py's play() loop's tuck-execution code, so later decision
    points in the same game are reached on a real, continuously-evolving board."""
    from drmario.faithful_env import FaithfulDrMarioEnv
    from drmario.faithful_game import LINK_LEFT, LINK_RIGHT, LINK_UP, LINK_DOWN
    from nes_pills import NesPillSource

    FX.warmup_ship_eh(topk2=8)
    w, fl = FX.variant("winner")
    samples = []

    for seed in seeds:
        env = FaithfulDrMarioEnv(level=level, seed=seed, max_pills=max_pills)
        env.reset()
        NesPillSource(seed=seed).attach(env)
        env.cur = env._rand_pill()
        env.nxt = env._rand_pill()

        for _ in range(max_pills):
            fb = FB.from_board(env.board)
            vc = env.board.virus_count()
            if vc == 0:
                break
            best, base_argmax = choose_with_base_argmax(fb, env.cur, env.nxt, w, fl, topk2=8)

            if best["kind"] == "tuck" and best.get("margin") is not None and base_argmax is not None:
                col, vir = RS.board_flat_from_fb(fb)
                var, cc, bc1, bv1, bnv, bcells = base_argmax
                base_comp = root_components(bc1, bv1, bnv, bcells, int(env.nxt.a), int(env.nxt.b),
                                             8, FX._W_EXCAV_SHIP, FX._W_HANG_SHIP, w, fl)
                p = best["placement"]
                r0, c0, r1, c1_ = p["cells"]
                col0, col1 = p["colors"]
                tc1 = np.empty(NCELL, dtype=np.int8)
                tv1 = np.empty(NCELL, dtype=np.int8)
                tnv, tcells = RS._expand_core_at(col, vir, r0, c0, r1, c1_, col0, col1, tc1, tv1)
                tuck_comp = root_components(tc1, tv1, tnv, tcells, int(env.nxt.a), int(env.nxt.b),
                                             8, FX._W_EXCAV_SHIP, FX._W_HANG_SHIP, w, fl)
                # offa/offb/ta/tb: land_place_at's own calling convention (flat 0-127
                # cell offsets + colours). tuck_enum.enumerate's own docstring: "colors
                # (colour at cell0, colour at cell1)", cells=(r0,c0,r1,c1) -- cell0/cell1
                # order already matches colors' order directly, no _FLIP table needed
                # (that table is tuck_scan_v3_ref.py's OWN convention for its DIFFERENT
                # target/rest/orient encoding, not applicable to tuck_enum's dict).
                offa, offb = r0 * 8 + c0, r1 * 8 + c1_
                samples.append({
                    "seed": seed, "board": bytes(col), "vir": bytes(vir),
                    "ca": int(env.cur.a), "cb": int(env.cur.b),
                    "na": int(env.nxt.a), "nb": int(env.nxt.b),
                    "base_var": var, "base_col": cc,
                    "tuck_offa": int(offa), "tuck_offb": int(offb),
                    "tuck_ta": int(col0), "tuck_tb": int(col1),
                    "tuck_cells": p["cells"], "tuck_orient": p["orient"],
                    "margin": float(best["margin"]),
                    "offline_base": base_comp, "offline_tuck": tuck_comp,
                })

            # execute the winning action (base or tuck) to advance the real game
            if best["kind"] == "tuck":
                p = best["placement"]
                r0, c0, r1, c1_ = p["cells"]
                col0, col1 = p["colors"]
                b = env.board
                b.color[r0, c0] = col0
                b.color[r1, c1_] = col1
                if r0 == r1:
                    b.link[r0, c0] = LINK_RIGHT; b.link[r1, c1_] = LINK_LEFT
                else:
                    b.link[r0, c0] = LINK_DOWN; b.link[r1, c1_] = LINK_UP
                b.is_virus[r0, c0] = False
                b.is_virus[r1, c1_] = False
                b.resolve()
                env.pills_placed += 1
                env.cur = env.nxt
                env.nxt = env._rand_pill()
                if b.virus_count() == 0 or b.spawn_blocked() or env.pills_placed >= max_pills:
                    break
            else:
                a = best["action"]
                _, _, term, trunc, info = env.step(int(a))
                if term or trunc:
                    break

        if len(samples) >= n_target * 6:   # enough of a pool to rank confidently; stop early
            break

    samples.sort(key=lambda s: s["margin"], reverse=True)
    print(f"harvested {len(samples)} tuck-won decisions across seeds up to {seed}; "
          f"margin range [{samples[-1]['margin']:.1f}, {samples[0]['margin']:.1f}]"
          if samples else "harvested 0 tuck-won decisions")
    return samples[:n_target]


if __name__ == "__main__":
    ok = verify_matches_offline()
    print("OK" if ok else "FAILED -- _components has drifted from the real offline scorer")
    sys.exit(0 if ok else 1)
