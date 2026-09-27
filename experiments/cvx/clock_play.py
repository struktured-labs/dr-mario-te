"""Solo Hartford-v2 stream for a VsPolicy: nutmeg bursty + TRATE=0.025 clock volleys.

Same physics as pressure_rig_time.play (T_LAT=0.6, FPR=0.35, nutmeg fire, TRATE
volley-size dist). Decider is pol.decide, not _choose_base, so k_clock is live.
ws=0 (cart DRSTRAND). cap 600 (cap-300 censors slow-safe policies).
"""
from __future__ import annotations
import random
import numpy as np

TRATE = 0.025
MAXPILLS = 600
GARBAGE_MIN_PILLS = 25
DIES_AHEAD_VIRUS_THRESHOLD = 12
T_LAT, FPR = 0.6, 0.35


def play_hartford(seed, pol, trate=TRATE, level=11, maxpills=MAXPILLS):
    import pressure_rig_time as PRT
    from nutmeg_model import NutmegModel
    from bursty_model import inject_bursty_garbage
    from drmario.faithful_env import FaithfulDrMarioEnv
    from nes_pills import NesPillSource
    from fb import FB
    import root_search as RS

    env = FaithfulDrMarioEnv(level=level, seed=seed, max_pills=maxpills)
    env.reset()
    NesPillSource(seed=seed).attach(env)
    env.cur = env._rand_pill()
    env.nxt = env._rand_pill()
    bursty = NutmegModel()
    elapsed = 0.0
    garbage = 0
    res = "stall"
    v_at_topout = None
    ctx = {"own_vleft": 48, "opp_vleft": 48, "own_t": 0.0, "opp_t": 0.0,
           "opp_spawn_h": 0, "own_spawn_h": 0}
    for _ in range(maxpills):
        if env.board.virus_count() == 0:
            res = "clear"
            break
        fb = FB.from_board(env.board)
        col, vir = RS.board_flat_from_fb(fb)
        ctx["own_vleft"] = env.board.virus_count()
        ctx["own_t"] = elapsed
        a = pol.decide(col, vir, int(env.cur.a), int(env.cur.b),
                       int(env.nxt.a), int(env.nxt.b), ctx)
        if a is None:
            break
        var, cc = a // 8, a % 8
        cols_involved = [cc] if var in (2, 3) else [cc, min(cc + 1, 7)]
        hmax = 0
        for tc in cols_involved:
            filled = [r for r in range(16) if col[r * 8 + tc] != 0]
            h = 16 - min(filled) if filled else 0
            if h > hmax:
                hmax = h
        dt = T_LAT + FPR * max(0, 16 - hmax)
        elapsed += dt
        occ_before = int(np.count_nonzero(env.board.color))
        _, _, term, trunc, info = env.step(int(a))
        if term:
            res = "clear" if info["won"] else "topout"
            if res == "topout":
                v_at_topout = env.board.virus_count()
            break
        if trunc:
            break
        landed = 0
        if env.pills_placed >= GARBAGE_MIN_PILLS:
            occ_after = int(np.count_nonzero(env.board.color))
            clear_size = max(0, occ_before + 2 - occ_after)
            if clear_size > 0:
                landed += inject_bursty_garbage(
                    env.board, bursty, seed, env.pills_placed, clear_size)
            if trate > 0.0:
                trng = random.Random(seed * 1000 + env.pills_placed + 777)
                if trng.random() < trate * dt:
                    x = trng.random()
                    k = 2 if x < 0.73 else (3 if x < 0.90 else (4 if x < 0.95 else (8 if x >= 0.96 else 2)))
                    landed += PRT._inject_garbage(env.board, seed, env.pills_placed + 500, k=k)
            garbage += landed
            if env.board.virus_count() == 0:
                res = "clear"
                break
            if env.board.spawn_blocked():
                res = "topout"
                v_at_topout = env.board.virus_count()
                break
    vleft = v_at_topout if v_at_topout is not None else env.board.virus_count()
    dies_ahead = int(res == "topout" and v_at_topout is not None
                     and v_at_topout <= DIES_AHEAD_VIRUS_THRESHOLD)
    return {
        "seed": seed, "won": int(res == "clear"), "topout": int(res == "topout"),
        "stall": int(res == "stall"), "pills": env.pills_placed,
        "elapsed_s": round(elapsed, 1), "garbage": garbage,
        "vleft": int(vleft), "dies_ahead": dies_ahead, "how": res,
    }
