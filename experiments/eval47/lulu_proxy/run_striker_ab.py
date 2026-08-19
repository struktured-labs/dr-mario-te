#!/usr/bin/env python3
"""Lulu-proxy striker A/B: height-TIMED garbage vs a VOLUME-MATCHED blind
control, over the shipped champion decide path (and optionally the t3 tuck
vocabulary at theta 150/400).

DESIGN (pre-registered in PRE_REGISTRATION_20260808.md BEFORE any arm ran):
  striker arm   volleys EARNED with the exact bursty-v1 fire/size draws on
                the AI's own clears, BANKED, RELEASED (all banked volleys)
                only when the AI's max stack height >= H (H in {5,6,8}) or
                the oldest banked volley is BANK_TIMEOUT_PILLS=9 old.
  blind arm     the IDENTICAL per-seed multiset of released volley sizes,
                delivered at uniform-random placement indices over
                [GARBAGE_MIN_PILLS, striker-game horizon] -- deterministic
                per seed.  This is the MATCHED-INDEX / volume-matched
                control the house law mandates: any striker-vs-blind delta
                is a pure TIMING effect, the volley-count confound is dead
                by construction.
  primary       dies_ahead count and bad-end (topout+stall) count,
                McNemar exact binomial on discordant pairs (reach_root_ab
                convention).  secondary: clear rate, pills, exposure.
  exposure      fraction of decisions made with own max height >=
                EXPOSURE_H(6) while a volley is banked/pending; plus
                h_at_release for every volley impact.

This file COPIES pressure_rig's play()/run_arm() skeleton instead of
editing pressure_rig.py (live jobs import it; house rule
live-script-edit-mv) and copies run_2x2.py's t3 tuck decision/execution
glue (choose_with_base + _place_cells) against the qa worktree's own
reach_root/firmware_tier3_ab (verified identical to the tuckvalue
worktree's copies, diff 2026-08-08 -- no cross-worktree import, no code
skew).  NOTE (memory dr-mario-tuck-armD-enumerator-not-firmware.md): the
t3tuck arms are enumerator-consumed tuck execution -- a perfect-vocabulary
upper bound, NOT a ship signal.

Seeds: explicit list EXCLUDING degenerate seed 1 (constant pill stream).
Workers: hard-capped at 3 (live jobs own the box).

Usage:
  run_striker_ab.py --gate-demo                 # killed-mutant gate first
  run_striker_ab.py --decider champion --n 200 --H 5 6 8
  run_striker_ab.py --decider t3tuck --theta 150 --n 200 --H 6
  run_striker_ab.py --decider t3tuck --theta 400 --n 200 --H 6
"""
from __future__ import annotations

import sys
import os
import json
import random
import argparse
import statistics as st
from concurrent.futures import ProcessPoolExecutor, as_completed

HERE = os.path.dirname(os.path.abspath(__file__))
EVAL47 = os.path.dirname(HERE)
ROOT = "/home/struktured/projects/dr_mario_rl"
QA = "/home/struktured/projects/dr-mario-qa-wt/experiments"
for _p in (HERE, EVAL47, ROOT + "/tmp/combo_term", ROOT + "/tmp/endgame",
           ROOT + "/tmp/tuck", ROOT + "/tmp/pillrng",
           ROOT + "/.claude/worktrees/faithful-sim/src", QA, QA + "/tuck_v3"):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import pressure_rig as PR          # noqa: E402 -- read-only import, never edited
import reach_root_ab as AB         # noqa: E402 -- mcnemar/_bad_end reused
import striker_model as SM         # noqa: E402

GARBAGE_MIN_PILLS = PR.GARBAGE_MIN_PILLS                    # 25
DIES_AHEAD_VIRUS_THRESHOLD = PR.DIES_AHEAD_VIRUS_THRESHOLD  # 12
CHAMPION_WT, CHAMPION_WS = 0, 20   # s20b python image -- fixed, not a knob
MAX_WORKERS = 3                    # resource law: live jobs own the box
RELEASE_SALT = 0x5EED              # release/blind rng salt, distinct from the
                                   # earn stream's Random(seed*1000+pills)

_C = {}


def _seed_list(n):
    """n seeds from range(n+1) excluding degenerate seed 1 (dr-mario-
    degenerate-seed-1.md).  n=200 -> [0, 2..200]."""
    return [s for s in range(n + 1) if s != 1][:n]


# ------------------------------------------------------------------ t3 glue
# (copied from tuck_value/run_2x2.py -- choose_with_base / cached tier /
#  _place_cells -- resolving against THIS worktree's reach_root +
#  firmware_tier3_ab, which are diff-identical to the originals)
_TIER_CACHE = {"key": None, "ctx": None}


def _cached_firmware_tier_of(col, candidate):
    import firmware_tier3_ab as FT3
    target, rest, orient = FT3._unpack(candidate)
    key = bytes(bytearray(int(x) & 0xFF for x in col))
    if _TIER_CACHE["key"] != key:
        board = FT3._to_nes_board(col)
        _TIER_CACHE["key"] = key
        _TIER_CACHE["ctx"] = (board, FT3.TR.row_bfs_visited(board),
                              FT3.T3R.mono_reach(board, "L"),
                              FT3.T3R.mono_reach(board, "R"))
    board, visited, mono_L, mono_R = _TIER_CACHE["ctx"]
    if FT3.TR.derive_verified(board, target, rest, orient, visited) is not None:
        return 1
    if FT3.T3R.derive_tier3_verified(board, target, rest, orient, visited,
                                     mono_L, mono_R) is not None:
        return 1
    return 99


def _choose_t3(fb, col, vir, ca, cb, na, nb, theta):
    """run_2x2.choose_with_base, t3 vocabulary: same call chain as
    reach_root.choose_reach_tier (RR.WS=20, the champion dose)."""
    import reach_root as RR
    cands = RR._scored_base_candidates(fb, col, vir, ca, cb, na, nb, RR.WS,
                                       RR.TOPK2)
    reach_cands = [c for c in cands if c["reachable"]]
    pool = reach_cands if reach_cands else cands
    best = max(pool, key=lambda c: c["val"])
    best_out = {"kind": "base", "action": best["action"], "val": best["val"]}
    tier_filter = lambda p: _cached_firmware_tier_of(col, p) <= 1  # noqa: E731
    return RR._tuck_branch_pick(fb, col, vir, ca, cb, na, nb, RR.WS, theta,
                                RR.TOPK2, best["val"], best_out,
                                extra_filter=tier_filter)


def _place_cells(env, r0, c0, r1, c1, col0, col1):
    from drmario.faithful_game import LINK_LEFT, LINK_RIGHT, LINK_UP, LINK_DOWN
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


# ------------------------------------------------------------------ workers
def _init(level, decider, theta, model_kind, model_obj, h_release, timeout,
          mutant, schedules, budget, height_metric="scaffold", seed_offset=0):
    if decider == "champion":
        import numpy as np
        import fast_rtl_x as FX
        FX.warmup_ship_eh(topk2=8)
        w, fl = FX.variant("winner")
        from terms47 import g_tower, g_stranded
        z = np.zeros(128, dtype=np.int8)
        g_tower(z, z, PR.H0)
        g_stranded(z, z)
        _C.update(w=w, fl=fl)
    else:
        import reach_root as RR
        RR._lazy()
    _C.update(level=level, decider=decider, theta=theta, model_kind=model_kind,
              model_obj=model_obj, h_release=h_release, timeout=timeout,
              mutant=mutant, schedules=schedules or {}, budget=budget,
              height_metric=height_metric, seed_offset=seed_offset)


def play(seed):
    import numpy as np
    from drmario.faithful_env import FaithfulDrMarioEnv
    from fb import FB
    import root_search as RS
    from nes_pills import NesPillSource
    from terms47 import g_tower, g_stranded

    level, decider, theta = _C["level"], _C["decider"], _C["theta"]
    model_kind, model_obj = _C["model_kind"], _C["model_obj"]
    h_release, timeout, mutant = _C["h_release"], _C["timeout"], _C["mutant"]
    budget = _C["budget"]
    height_metric = _C["height_metric"]
    # PAIRING MUTANT ONLY: seed_offset != 0 desynchronizes the game seed from
    # the arm's nominal seed (offset 2, not 1 -- seeds 2k and 2k+1 are the
    # SAME game, dr-mario-seed-space-is-32767.md, so a +1 mutant would be
    # EQUIVALENT on even seeds and the pairing gate could not catch it).
    seed_offset = _C.get("seed_offset", 0)
    game_seed = seed + seed_offset
    schedule = _C["schedules"].get(seed, [])   # blind mode: [(idx, n_cells)]
    if model_kind == "bursty":
        from bursty_model import inject_bursty_garbage

    env = FaithfulDrMarioEnv(level=level, seed=game_seed, max_pills=300)
    env.reset()
    NesPillSource(seed=game_seed).attach(env)
    env.cur = env._rand_pill()
    env.nxt = env._rand_pill()
    # PAIRING EVIDENCE: fingerprint of the opening virus field (colors +
    # virus mask, before a single pill lands) and the realized capsule
    # stream, both logged per game so check_pairing() can prove two arms saw
    # the same game.
    import hashlib
    virus_sig = hashlib.md5(
        env.board.color.astype("int8").tobytes()
        + env.board.is_virus.astype("int8").tobytes()).hexdigest()
    capsule_seq = []

    res = "stall"
    col = vir = None
    v_at_topout = None
    garbage_injected = 0
    fired_tuck = 0
    earned_total = 0
    bank = []             # [{"earned_pill": int, "n_cells": int}], play-local:
                          # NEVER on the model object (workers share the pickle)
    sched_pos = 0
    release_log = []      # per release event, incl. h_at_release + reason
    impact_heights = []   # h_max just before every volley impact
    decisions = 0
    exposed = 0           # decisions with own h_max >= EXPOSURE_H and a
                          # volley banked (striker) / undelivered (blind)

    for _ in range(300):
        fb = FB.from_board(env.board)
        if env.board.virus_count() == 0:
            res = "clear"
            break
        col, vir = RS.board_flat_from_fb(fb)
        ca, cb = int(env.cur.a), int(env.cur.b)
        na, nb = int(env.nxt.a), int(env.nxt.b)
        capsule_seq.append((ca, cb))

        # --- EXPOSURE (pre-registered secondary): counted at decision time,
        # against the board the decision is made on
        h_dec = SM.max_height(env.board)
        pending = (bool(bank) if model_kind == "striker"
                   else (sched_pos < len(schedule) if model_kind == "blind"
                         else False))
        decisions += 1
        if pending and h_dec >= SM.EXPOSURE_H:
            exposed += 1

        # --- decide + execute
        occ_before = int(np.count_nonzero(env.board.color))
        stepped = False
        if decider == "champion":
            a, _c1b = PR._choose_base(col, vir, ca, cb, na, nb,
                                      _C["w"], _C["fl"],
                                      CHAMPION_WT, CHAMPION_WS)
            action = a
        else:  # t3tuck
            pick = _choose_t3(fb, col, vir, ca, cb, na, nb, theta)
            if pick["kind"] == "tuck":
                p = pick["placement"]
                r0, c0, r1, c1 = p["cells"]
                fired_tuck += 1
                _place_cells(env, r0, c0, r1, c1, pick["ca"], pick["cb"])
                stepped = True
                action = None
            else:
                action = pick["action"]

        if not stepped:
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
        else:
            if env.board.virus_count() == 0:
                res = "clear"
                break
            if env.board.spawn_blocked():
                res = "topout"
                v_at_topout = env.board.virus_count()
                break
            if env.pills_placed >= 300:
                break

        # --- GARBAGE PHASE (after the placement fully resolved) ---
        if model_kind != "none" and env.pills_placed >= GARBAGE_MIN_PILLS:
            pills = env.pills_placed
            landed = 0
            occ_after = int(np.count_nonzero(env.board.color))
            clear_size = max(0, occ_before + 2 - occ_after)

            if model_kind == "bursty":
                if clear_size > 0:
                    landed = inject_bursty_garbage(
                        env.board, model_obj, seed, pills, clear_size)

            elif model_kind == "striker":
                # RELEASE is evaluated BEFORE the earn step, so a volley
                # earned at placement p is only eligible from p+1: the bank
                # is a real bank (min age 1 tick) and check_release_log's
                # min_bank_ticks=1 assertion is meaningful.  Amendment
                # 2026-08-08 #2, made before any measured run.
                if bank and mutant != "ignores_bank":
                    h_rel = SM.measure_height(env.board, height_metric)
                    h_raw = SM.max_height(env.board)
                    age_oldest = pills - bank[0]["earned_pill"]
                    age_newest = pills - bank[-1]["earned_pill"]
                    rng_rel = random.Random((seed * 1000 + pills) ^ RELEASE_SALT)
                    reason = None
                    if SM.release_fires(mutant, h_rel, h_release, rng_rel):
                        reason = "height"
                    elif age_oldest >= timeout:
                        reason = "timeout"
                    if reason:
                        sizes = [b["n_cells"] for b in bank]
                        bank = []
                        placed = 0
                        for s in sizes:
                            placed += SM.drop_volley(env.board, s, rng_rel)
                        release_log.append(
                            {"pill": pills, "reason": reason,
                             "h_at_release": h_rel, "h_raw": h_raw,
                             "sizes": sizes, "placed": placed,
                             "age_oldest": age_oldest,
                             "age_newest": age_newest})
                        impact_heights.append(h_rel)
                        landed = placed
                # EARN: byte-identical draws to the bursty hook, banked
                if clear_size > 0 and (budget is None or earned_total < budget):
                    n = SM.earn_volley(model_obj, seed, pills, clear_size)
                    if budget is not None:
                        n = min(n, budget - earned_total)
                    if n > 0:
                        if mutant == "ignores_bank":
                            # MUTANT: never banks -- drops the volley the
                            # instant it is earned, whatever the height.
                            h_rel = SM.measure_height(env.board, height_metric)
                            rng_rel = random.Random(
                                (seed * 1000 + pills) ^ RELEASE_SALT)
                            placed = SM.drop_volley(env.board, n, rng_rel)
                            release_log.append(
                                {"pill": pills, "reason": "height",
                                 "h_at_release": h_rel,
                                 "h_raw": SM.max_height(env.board),
                                 "sizes": [n], "placed": placed,
                                 "age_oldest": 0, "age_newest": 0})
                            impact_heights.append(h_rel)
                            landed += placed
                        else:
                            bank.append({"earned_pill": pills, "n_cells": n})
                        earned_total += n

            elif model_kind == "blind":
                # volume-matched replay: same sizes, blind timing
                if sched_pos < len(schedule) and schedule[sched_pos][0] <= pills:
                    rng_rel = random.Random((seed * 1000 + pills) ^ RELEASE_SALT)
                    while (sched_pos < len(schedule)
                           and schedule[sched_pos][0] <= pills):
                        _idx, s = schedule[sched_pos]
                        sched_pos += 1
                        h_rel = SM.measure_height(env.board, height_metric)
                        placed = SM.drop_volley(env.board, s, rng_rel)
                        release_log.append(
                            {"pill": pills, "reason": "blind",
                             "h_at_release": h_rel,
                             "h_raw": SM.max_height(env.board),
                             "sizes": [s], "placed": placed})
                        impact_heights.append(h_rel)
                        landed += placed

            garbage_injected += landed
            if env.board.virus_count() == 0:
                res = "clear"
                break
            if env.board.spawn_blocked():
                res = "topout"
                v_at_topout = env.board.virus_count()
                break

    if col is None:
        fb = FB.from_board(env.board)
        col, vir = RS.board_flat_from_fb(fb)
    dies_ahead = int(res == "topout" and v_at_topout is not None
                     and v_at_topout <= DIES_AHEAD_VIRUS_THRESHOLD)
    return {"seed": seed, "won": int(res == "clear"),
            "topout": int(res == "topout"), "stall": int(res == "stall"),
            "pills": env.pills_placed, "garbage_injected": garbage_injected,
            "stranded_final": int(g_stranded(col, vir)),
            "tower_final": int(g_tower(col, vir, PR.H0)),
            "viruses_left_at_end": (v_at_topout if v_at_topout is not None
                                    else env.board.virus_count()),
            "dies_ahead": dies_ahead, "fired_tuck": fired_tuck,
            "earned_total": earned_total,
            "bank_leftover": (len(bank) if model_kind == "striker"
                              else len(schedule) - sched_pos),
            "decisions": decisions, "exposed_decisions": exposed,
            "exposure": (exposed / decisions) if decisions else 0.0,
            "impact_heights": impact_heights,
            "release_log": release_log,
            "virus_sig": virus_sig, "capsule_seq": capsule_seq,
            "game_seed": game_seed}


def run_arm(level, seeds, workers, decider, theta, model_kind, model_obj,
            h_release, timeout, mutant="none", schedules=None, budget=None,
            height_metric="scaffold", tag="", seed_offset=0):
    workers = min(workers, MAX_WORKERS)
    rows = []
    with ProcessPoolExecutor(max_workers=workers, initializer=_init,
                             initargs=(level, decider, theta, model_kind,
                                       model_obj, h_release, timeout, mutant,
                                       schedules, budget, height_metric,
                                       seed_offset)) as ex:
        futs = [ex.submit(play, s) for s in seeds]
        for i, f in enumerate(as_completed(futs)):
            rows.append(f.result())
            if (i + 1) % max(1, len(seeds) // 4) == 0 or (i + 1) == len(seeds):
                print(f"  [{tag}] {i + 1}/{len(seeds)}", flush=True)
    return {r["seed"]: r for r in rows}


# ------------------------------------------------------------------ analysis
def mcnemar_field(ctrl, on, seeds, field):
    """Exact binomial McNemar on a 0/1 row field (reach_root_ab.mcnemar
    generalized beyond _bad_end).  rescued = ctrl 1 / on 0."""
    from scipy.stats import binomtest
    rescued = harmed = 0
    for s in seeds:
        c, o = bool(ctrl[s][field]), bool(on[s][field])
        if c and not o:
            rescued += 1
        elif o and not c:
            harmed += 1
    disc = rescued + harmed
    p = binomtest(rescued, disc, 0.5).pvalue if disc else float("nan")
    return rescued, harmed, disc, p


def summarize_pair(blind, striker, tag):
    """blind = control, striker = arm.  COUNTS, never adjectives."""
    ss = sorted(set(blind) & set(striker))
    n = len(ss)
    out = {"tag": tag, "n": n}
    for field in ("dies_ahead",):
        r, h, d, p = mcnemar_field(blind, striker, ss, field)
        out[field] = {"ctrl": sum(blind[s][field] for s in ss),
                      "arm": sum(striker[s][field] for s in ss),
                      "rescued": r, "harmed": h, "discordant": d, "p": p}
    rb, hb, db, pb = mcnemar_field(
        {s: {"bad": AB._bad_end(blind[s])} for s in ss},
        {s: {"bad": AB._bad_end(striker[s])} for s in ss}, ss, "bad")
    out["bad_end"] = {"ctrl": sum(AB._bad_end(blind[s]) for s in ss),
                      "arm": sum(AB._bad_end(striker[s]) for s in ss),
                      "rescued": rb, "harmed": hb, "discordant": db, "p": pb}
    out["clear"] = {"ctrl": sum(blind[s]["won"] for s in ss),
                    "arm": sum(striker[s]["won"] for s in ss)}
    both = [s for s in ss if blind[s]["won"] and striker[s]["won"]]
    dp = [striker[s]["pills"] - blind[s]["pills"] for s in both]
    out["pills_delta_mean_bothwon"] = st.mean(dp) if dp else None
    out["garbage_per_game"] = {
        "ctrl": st.mean([blind[s]["garbage_injected"] for s in ss]),
        "arm": st.mean([striker[s]["garbage_injected"] for s in ss])}
    # rate-normalized pressure: striker games are PROLONGED by their own
    # releases (garbage covers viruses -> more pills -> more clears -> more
    # earned volleys), so per-game totals diverge even under a matched
    # schedule; halves per 100 placements compares pressure intensity on
    # unequal game lengths.
    out["garbage_per_100_pills"] = {
        "ctrl": st.mean([100.0 * blind[s]["garbage_injected"] / max(1, blind[s]["pills"])
                         for s in ss]),
        "arm": st.mean([100.0 * striker[s]["garbage_injected"] / max(1, striker[s]["pills"])
                        for s in ss])}
    out["exposure_mean"] = {
        "ctrl": st.mean([blind[s]["exposure"] for s in ss]),
        "arm": st.mean([striker[s]["exposure"] for s in ss])}
    ih = [h for s in ss for h in striker[s]["impact_heights"]]
    ihc = [h for s in ss for h in blind[s]["impact_heights"]]
    out["impact_height_mean"] = {"ctrl": st.mean(ihc) if ihc else None,
                                 "arm": st.mean(ih) if ih else None}
    # residual blind under-delivery, broken down by the blind game's outcome:
    # undelivered-because-WON is post-outcome (the tail could not have caused
    # the win); undelivered-because-DIED means the blind game got less
    # pressure before its death and the pair is volume-suspect.
    undeliv_won = sum(blind[s]["bank_leftover"] for s in ss if blind[s]["won"])
    undeliv_died = sum(blind[s]["bank_leftover"] for s in ss if not blind[s]["won"])
    out["blind_undelivered_volleys"] = {"total": undeliv_won + undeliv_died,
                                        "blind_won": undeliv_won,
                                        "blind_died": undeliv_died}
    # volume among the DISCORDANT dies-ahead pairs -- the games that drive
    # the primary McNemar count.  If the striker's kills sit on pairs where
    # the blind game under-received, the volume confound is back in play;
    # report the counts so that is inspectable, never asserted.
    disc_seeds = [s for s in ss
                  if bool(blind[s]["dies_ahead"]) != bool(striker[s]["dies_ahead"])]
    out["discordant_dies_ahead_garbage"] = [
        {"seed": s, "blind": blind[s]["garbage_injected"],
         "striker": striker[s]["garbage_injected"],
         "blind_undelivered": blind[s]["bank_leftover"],
         "which_died_ahead": "striker" if striker[s]["dies_ahead"] else "blind"}
        for s in disc_seeds]
    print(f"\n=== {tag} (n={n}) ===")
    print(f"  dies_ahead  blind {out['dies_ahead']['ctrl']} -> striker "
          f"{out['dies_ahead']['arm']}  rescued/harmed "
          f"{out['dies_ahead']['rescued']}/{out['dies_ahead']['harmed']} "
          f"p={out['dies_ahead']['p']:.4g}")
    print(f"  bad_end     blind {out['bad_end']['ctrl']} -> striker "
          f"{out['bad_end']['arm']}  rescued/harmed "
          f"{out['bad_end']['rescued']}/{out['bad_end']['harmed']} "
          f"p={out['bad_end']['p']:.4g}")
    print(f"  clear       blind {out['clear']['ctrl']}/{n} -> striker "
          f"{out['clear']['arm']}/{n}")
    print(f"  garbage/g   blind {out['garbage_per_game']['ctrl']:.2f} vs "
          f"striker {out['garbage_per_game']['arm']:.2f}  "
          f"(per 100 pills: {out['garbage_per_100_pills']['ctrl']:.2f} vs "
          f"{out['garbage_per_100_pills']['arm']:.2f})")
    print(f"  exposure    blind {out['exposure_mean']['ctrl']:.4f} vs "
          f"striker {out['exposure_mean']['arm']:.4f}")
    im_c, im_a = out["impact_height_mean"]["ctrl"], out["impact_height_mean"]["arm"]
    print(f"  impact h    blind {im_c if im_c is None else round(im_c, 2)} vs "
          f"striker {im_a if im_a is None else round(im_a, 2)}", flush=True)
    return out


def _schedules_for(striker, drop_one=False):
    """Per-seed blind schedules.  Horizon = the striker's LAST RELEASE pill
    (its actual delivery window), not the game's final pill -- see
    striker_model.build_blind_schedule docstring for the smoke measurement
    that forced this (blind under-delivery 48.4 vs 68.2 halves/game when
    drawing over [25, final_pills])."""
    scheds = {}
    for s, row in striker.items():
        rl = row["release_log"]
        horizon = max(ev["pill"] for ev in rl) if rl else row["pills"]
        scheds[s] = SM.build_blind_schedule(rl, horizon, s, GARBAGE_MIN_PILLS,
                                            drop_one=drop_one)
    return scheds


def volume_check(striker, schedules):
    """The blind schedule must carry EXACTLY the striker's released sizes,
    per seed.  By-construction assert (scheduled multiset == released
    multiset); landed counts can differ only via full-column skips."""
    for s, row in striker.items():
        released = sorted(x for ev in row["release_log"] for x in ev["sizes"])
        scheduled = sorted(x for _i, x in schedules.get(s, []))
        assert released == scheduled, \
            f"seed {s}: volume mismatch {released} != {scheduled}"


def gate_or_die(rows, h_release, timeout, expect_fail=False, tag=""):
    """Run the killed-mutant checker over every game's release log."""
    viol = []
    for s in sorted(rows):
        viol += [f"seed {s}: {v}" for v in
                 SM.check_release_log(rows[s]["release_log"], h_release, timeout)]
    n_rel = sum(len(rows[s]["release_log"]) for s in rows)
    if expect_fail:
        ok = len(viol) > 0
        print(f"  gate[{tag}]: {len(viol)} violations over {n_rel} releases "
              f"-- checker {'CAUGHT the mutant (PASS)' if ok else 'FAILED TO CATCH (GATE BROKEN)'}")
        return ok
    if viol:
        for v in viol[:10]:
            print("  GATE VIOLATION:", v)
        raise SystemExit(f"gate[{tag}]: {len(viol)} violations -- aborting")
    print(f"  gate[{tag}]: 0 violations over {n_rel} releases (PASS)")
    return True


# ------------------------------------------------------------------ drivers
def _load_model():
    import bursty_model
    m = bursty_model.fit_struktured_20260804()
    # strip the heavy per-frame ledger before pickling to workers
    # (pressure_rig.main idiom)
    m.meta = {k: v for k, v in m.meta.items() if k != "raw_events"}
    return m


def gate_demo(args):
    """KILLED-MUTANT GATE DEMO (must run + pass before any measured arm is
    trusted): the checker passes the real striker and FAILS the inverted
    mutant, the random mutant, and the blind control's own log.  Mutant
    non-equivalence is shown by the caught releases themselves (heights
    below H that the real predicate can never produce)."""
    model = _load_model()
    seeds = _seed_list(args.gate_n)
    H, TO = args.H[0], args.timeout
    print(f"=== KILLED-MUTANT GATE DEMO: H={H} timeout={TO} "
          f"n={len(seeds)} seeds ===")
    real = run_arm(args.level, seeds, args.workers, "champion", None,
                   "striker", model, H, TO, mutant="none",
                   height_metric=args.height_metric, tag="real")
    gate_or_die(real, H, TO, tag="real striker")
    results = []
    for mut in ("inverted", "inverted_lt", "random", "ignores_bank"):
        rows = run_arm(args.level, seeds, args.workers, "champion", None,
                       "striker", model, H, TO, mutant=mut,
                       height_metric=args.height_metric, tag=mut)
        results.append(gate_or_die(rows, H, TO, expect_fail=True, tag=mut))
    scheds = _schedules_for(real)
    blind = run_arm(args.level, seeds, args.workers, "champion", None,
                    "blind", model, H, TO, schedules=scheds,
                    height_metric=args.height_metric, tag="blind")
    results.append(gate_or_die(blind, H, TO, expect_fail=True, tag="blind"))
    if not all(results):
        raise SystemExit("GATE DEMO FAILED: a mutant survived the checker")
    print("GATE DEMO PASS: checker accepts the real striker and kills "
          "inverted + random + blind.")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=200,
                    help="games per arm (seeds = range(n+1) minus seed 1)")
    ap.add_argument("--level", type=int, default=11)
    ap.add_argument("--workers", type=int, default=3)
    ap.add_argument("--decider", choices=["champion", "t3tuck"],
                    default="champion")
    ap.add_argument("--theta", type=int, default=150,
                    help="t3tuck only: tuck margin gate "
                         "(150 = firmware DRCOPRO_TUCKV3_THETA default, "
                         "400 = the #85 brake dose)")
    ap.add_argument("--H", type=int, nargs="+", default=[5, 6, 8],
                    help="release height thresholds to sweep")
    ap.add_argument("--timeout", type=int, default=SM.BANK_TIMEOUT_PILLS)
    ap.add_argument("--height-metric", choices=SM.HEIGHT_METRICS,
                    default="scaffold",
                    help="release predicate height: 'scaffold' = contiguous "
                         "non-virus run atop the stack (default; raw stack "
                         "height at L11 never drops below 6, making H<=6 "
                         "vacuous -- see striker_model docstring); 'stack' = "
                         "raw max column height (the literal reading)")
    ap.add_argument("--budget", type=int, default=None,
                    help="optional total-halves earn cap per game "
                         "(53 = adversary_search BUDGET_HALVES)")
    ap.add_argument("--out", type=str, default=os.path.join(HERE, "results"))
    ap.add_argument("--gate-demo", action="store_true")
    ap.add_argument("--gate-n", type=int, default=12)
    a = ap.parse_args()
    a.workers = min(a.workers, MAX_WORKERS)

    if a.gate_demo:
        gate_demo(a)
        return

    os.makedirs(a.out, exist_ok=True)
    model = _load_model()
    seeds = _seed_list(a.n)
    theta = a.theta if a.decider == "t3tuck" else None
    dtag = a.decider + (f"_th{a.theta}" if a.decider == "t3tuck" else "")
    print(f"=== LULU-PROXY STRIKER A/B: decider={dtag} n={len(seeds)} "
          f"H={a.H} metric={a.height_metric} timeout={a.timeout} "
          f"budget={a.budget} workers={a.workers} ===", flush=True)

    all_summaries = []
    for H in a.H:
        tag = f"{dtag}_H{H}"
        striker = run_arm(a.level, seeds, a.workers, a.decider, theta,
                          "striker", model, H, a.timeout, budget=a.budget,
                          height_metric=a.height_metric,
                          tag=f"{tag} striker")
        gate_or_die(striker, H, a.timeout, tag=f"{tag} striker")
        scheds = _schedules_for(striker)
        volume_check(striker, scheds)
        blind = run_arm(a.level, seeds, a.workers, a.decider, theta,
                        "blind", model, H, a.timeout, schedules=scheds,
                        budget=a.budget, height_metric=a.height_metric,
                        tag=f"{tag} blind")
        summary = summarize_pair(blind, striker, tag)
        uv = summary["blind_undelivered_volleys"]
        print(f"  blind undelivered volleys (game ended first): {uv['total']} "
              f"(blind won: {uv['blind_won']}, blind died: {uv['blind_died']})")
        all_summaries.append(summary)
        out_path = os.path.join(a.out, f"striker_{tag}_n{len(seeds)}.json")
        with open(out_path, "w") as fh:
            json.dump({"meta": {"decider": a.decider, "theta": theta,
                                "H": H, "timeout": a.timeout,
                                "height_metric": a.height_metric,
                                "budget": a.budget, "n": len(seeds),
                                "level": a.level,
                                "champion": {"wt": CHAMPION_WT,
                                             "ws": CHAMPION_WS},
                                "exposure_h": SM.EXPOSURE_H,
                                "release_policy": "all-banked-at-trigger"},
                       "summary": summary,
                       "striker": [striker[s] for s in sorted(striker)],
                       "blind": [blind[s] for s in sorted(blind)]}, fh)
        print(f"  wrote {out_path}", flush=True)

    print("\n=== SWEEP SUMMARY (counts) ===")
    for smry in all_summaries:
        da, be = smry["dies_ahead"], smry["bad_end"]
        print(f"  {smry['tag']:>24s}  dies-ahead {da['ctrl']}->{da['arm']} "
              f"(p={da['p']:.3g})  bad-ends {be['ctrl']}->{be['arm']} "
              f"(p={be['p']:.3g})  exposure "
              f"{smry['exposure_mean']['ctrl']:.3f}->"
              f"{smry['exposure_mean']['arm']:.3f}")
    print("DONE")


if __name__ == "__main__":
    main()
