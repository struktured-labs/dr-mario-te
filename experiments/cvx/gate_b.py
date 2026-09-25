"""Gate (b) for VsPolicy candidates (#17) + the pinned calibration table (#16).

Solo play with pol.decide (so k_clock is live), garbage per the OWNER burst model
(bursty_model.fit_struktured_20260804 — the run-16 regime) or the Hartford NutmegModel,
optional clock stream TRATE.  Same loop as clock_play.play_hartford, model injectable.
"""
import sys, os, json, random
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import import_pin; import_pin.pin()
import clock_play as CP
from vs_choose import VsPolicy

def play(seed, pol, model, trate=0.0, level=11, maxpills=600, choose=None, steer=None):
    import pressure_rig_time as PRT
    from bursty_model import inject_bursty_garbage
    from drmario.faithful_env import FaithfulDrMarioEnv
    from nes_pills import NesPillSource
    from fb import FB
    import root_search as RS
    env = FaithfulDrMarioEnv(level=level, seed=seed, max_pills=maxpills); env.reset()
    NesPillSource(seed=seed).attach(env); env.cur = env._rand_pill(); env.nxt = env._rand_pill()
    elapsed = 0.0; garbage = 0; res = "stall"; v_at_topout = None
    if steer is not None:                     # steering-faithful execution (steer_model.py); None = unchanged
        import steer_model as SM
        steer.reset(seed)
    ctx = {"own_vleft": 48, "opp_vleft": 48, "own_t": 0.0, "opp_t": 0.0, "opp_spawn_h": 0, "own_spawn_h": 0}
    for _ in range(maxpills):
        if env.board.virus_count() == 0: res = "clear"; break
        fb = FB.from_board(env.board); col, vir = RS.board_flat_from_fb(fb)
        ctx["own_vleft"] = env.board.virus_count(); ctx["own_t"] = elapsed
        a = (choose(env, col, vir, ctx) if choose is not None else
             pol.decide(col, vir, int(env.cur.a), int(env.cur.b), int(env.nxt.a), int(env.nxt.b), ctx))
        if a is None: break
        var, cc = a // 8, a % 8
        cols_involved = [cc] if var in (2, 3) else [cc, min(cc + 1, 7)]
        hmax = 0
        for tc in cols_involved:
            filled = [r for r in range(16) if col[r * 8 + tc] != 0]
            h = 16 - min(filled) if filled else 0
            hmax = max(hmax, h)
        dt = CP.T_LAT + CP.FPR * max(0, 16 - hmax); elapsed += dt
        occ_before = int(np.count_nonzero(env.board.color))
        if steer is None:
            _, _, term, trunc, info = env.step(int(a))
        else:
            ex = steer.execute(env.board.color.tolist(), int(a), env.pills_placed)
            (_, _, term, trunc, info), _straight = SM.place_executed(env, ex)
        if term:
            res = "clear" if info["won"] else "topout"
            if res == "topout": v_at_topout = env.board.virus_count()
            break
        if trunc: break
        landed = 0
        if env.pills_placed >= CP.GARBAGE_MIN_PILLS:
            clear_size = max(0, occ_before + 2 - int(np.count_nonzero(env.board.color)))
            if clear_size > 0:
                landed += inject_bursty_garbage(env.board, model, seed, env.pills_placed, clear_size)
            if trate > 0.0:
                trng = random.Random(seed * 1000 + env.pills_placed + 777)
                if trng.random() < trate * dt:
                    x = trng.random()
                    k = 2 if x < 0.73 else (3 if x < 0.90 else (4 if x < 0.95 else (8 if x >= 0.96 else 2)))
                    landed += PRT._inject_garbage(env.board, seed, env.pills_placed + 500, k=k)
            garbage += landed
            if env.board.virus_count() == 0: res = "clear"; break
            if env.board.spawn_blocked(): res = "topout"; v_at_topout = env.board.virus_count(); break
    vleft = v_at_topout if v_at_topout is not None else env.board.virus_count()
    out = {"seed": seed, "won": int(res == "clear"), "topout": int(res == "topout"), "stall": int(res == "stall"),
            "pills": env.pills_placed, "elapsed_s": round(elapsed, 1), "garbage": garbage, "vleft": int(vleft),
            "dies_ahead": int(res == "topout" and v_at_topout is not None and v_at_topout <= 12), "how": res}
    if steer is not None:
        out["steer"] = dict(steer.stats)
    return out

ARMS = {"winner": dict(trunk="winner", k_clock=0.0), "kc40": dict(trunk="winner", k_clock=40.0),
        "holes80": dict(trunk="winholes80", k_clock=0.0),
        "h80kc10": dict(trunk="winholes80", k_clock=10.0), "h80kc20": dict(trunk="winholes80", k_clock=20.0),
        "h80kc40": dict(trunk="winholes80", k_clock=40.0)}

if __name__ == "__main__":
    arm, model_name, trate, lo, cnt, step, out = sys.argv[1], sys.argv[2], float(sys.argv[3]), int(sys.argv[4]), int(sys.argv[5]), int(sys.argv[6]), sys.argv[7]
    level = int(sys.argv[8]) if len(sys.argv) > 8 else 11
    if model_name == "owner":
        import bursty_model as BM; model = BM.fit_struktured_20260804()
    else:
        from nutmeg_model import NutmegModel; model = NutmegModel()
    if arm in ARMS:
        pol, choose = VsPolicy(**ARMS[arm]), None
    else:                                   # Combo Stomper lineage: board decider from vs_race
        import vs_race
        pol, choose = None, vs_race._decider(arm)
    with open(out, "w") as fh:
        for i in range(cnt):
            r = play(lo + i * step, pol, model, trate=trate, level=level, choose=choose)
            r.update({"arm": arm, "model": model_name, "trate": trate})
            if level != 11: r["level"] = level     # L11 rows stay byte-identical to the banked screen
            fh.write(json.dumps(r) + "\n"); fh.flush()
