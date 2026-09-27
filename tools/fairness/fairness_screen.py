#!/usr/bin/env python3
"""Capsule-fairness screen: is a move's advantage structural, or seed-peeking?

THE PROBLEM (proven 2026-08-13): a CLAIR fork judges moves on the TRUE future
capsule stream, so with K=1 its preferred move is optimal for the actual draw,
not in expectation. 7/10 quiz exhibits and 4/6 published exhibits dissolved
under this screen; only 5/114 (4%) of gap>=3 flips survived it.

THE SCREEN: re-fork BOTH candidate moves under N alternate capsule streams
(swap `env._rand_pill` for a fresh `PillDraw(NesPillSource(seed=ALT))` and
redraw `nxt`), play the champion policy forward H pills, compare mean progress.
Garbage stays keyed by (game_seed, pills_placed) — the CLAIR garbage caveat
still applies; this screen removes CAPSULE clairvoyance only.

VERDICT BAR (as used for the survivor fixtures): mean diff >= +1.0 AND wins on
>= 9/17 streams at n=17 (two-stage: n=5 pre-screen at >= +1.0 and 4/5).

USAGE (from a checkout with the oracle rig importable; see the session
scripts in the 2026-08-13 scratchpad for the full worked pipeline):

    from fairness_screen import screen_moves
    verdict = screen_moves(env, game_seed, move_a, move_b, C, bmodel, weights)

FIXTURES: survivor_fixtures.json in this directory holds the 5 screened
structural evaluator gaps (seed/ply/rank/n17 stats). Any candidate eval or
re-ranker change should flip all 5 to the screened-better move; missing >= 2
rejects the candidate before endpoint spend (see the H12 draft prereg).

Standard alt-stream set (frozen so screens are comparable):
    ALT17 = (11111, 22222, 3333, 4444, 5555, 101, 202, 303, 404, 505,
             606, 707, 808, 909, 1001, 1102, 1203)
"""
from __future__ import annotations

import copy

ALT17 = (11111, 22222, 3333, 4444, 5555, 101, 202, 303, 404, 505,
         606, 707, 808, 909, 1001, 1102, 1203)


def fork_fair(env, game_seed, action, cap_seed, C, bmodel, weights,
              horizon=15, oracle_arm=None):
    """Fork `action` from a deepcopy of `env` under an ALTERNATE capsule stream.

    weights = (w, fl, wt, ws) as unpacked from the rig config.
    Returns viruses cleared during the fork.
    """
    OA = oracle_arm
    if OA is None:
        import oracle_arm as OA  # noqa: N813
    from nes_pills import NesPillSource
    from fb import FB
    import root_search as RS

    w, fl, wt, ws = weights
    e = copy.deepcopy(env)
    if cap_seed is not None:
        e._rand_pill = OA.PillDraw(NesPillSource(seed=cap_seed))
        e.nxt = e._rand_pill()
    v0 = e.board.virus_count()
    r, _ = OA._advance(e, action, C, game_seed, bmodel)
    n = 1
    while r is None and n < horizon and e.board.virus_count() > 0:
        fb = FB.from_board(e.board)
        colf, virf = RS.board_flat_from_fb(fb)
        vals = OA._champ_values(colf, virf, int(e.cur.a), int(e.cur.b),
                                int(e.nxt.a), int(e.nxt.b), w, fl, wt, ws)
        a2 = OA._champ_action(vals, OA.CHAMP_ORDER)
        r, _ = OA._advance(e, a2, C, game_seed, bmodel)
        n += 1
    return v0 - e.board.virus_count()


def screen_moves(env, game_seed, move_a, move_b, C, bmodel, weights,
                 streams=ALT17, horizon=15):
    """Return dict: is move_b's advantage over move_a structural?"""
    da, db = [], []
    for cs in streams:
        da.append(fork_fair(env, game_seed, move_a, cs, C, bmodel, weights, horizon))
        db.append(fork_fair(env, game_seed, move_b, cs, C, bmodel, weights, horizon))
    diffs = [y - x for x, y in zip(da, db)]
    n = len(diffs)
    mean = sum(diffs) / n
    wins = sum(1 for d in diffs if d > 0)
    return {
        "n": n, "mean": mean, "wins": wins,
        "ties": sum(1 for d in diffs if d == 0),
        "losses": sum(1 for d in diffs if d < 0),
        "structural": mean >= 1.0 and wins >= (9 if n >= 17 else max(4, n - 1)),
        "diffs": diffs,
    }
