"""OPP1 runner: gate (b) with steering ON and a pluggable OPPONENT (opp_models). The loop is gate_b.play's (steer
path) with the garbage decision delegated to `opponent.after_placement`. With OwnerBursty(fit_struktured_20260804) it
must reproduce gate_b rows byte-for-byte (identity gate).

  python opp_run.py BUILD OPPONENT LO CNT STEP OUT.jsonl
BUILD = a steer_run arm (s4_base = shipping REACH+TAP, s5b_hsv512); OPPONENT = owner0804 | owner202609 | striker5 | striker6 | striker8
"""
import sys, os, json
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import import_pin; import_pin.pin()
import numpy as np
import clock_play as CP
import steer_model as SM
import opp_models as OM


def make_opponent(name):
    import bursty_model as BM
    if name == "owner0804":
        return OM.OwnerBursty(BM.fit_struktured_20260804())
    if name.startswith("striker"):                       # striker5 / striker6 / striker8 (scaffold metric, timeout 9)
        return OM.Striker(BM.fit_struktured_20260804(), h_release=int(name[7:]))
    if name == "owner202609":
        import opp_owner202609 as O9
        return O9.make()
    raise ValueError(name)


def play(seed, choose, steer, opp, level=11, maxpills=600):
    from drmario.faithful_env import FaithfulDrMarioEnv
    from nes_pills import NesPillSource
    from fb import FB
    import root_search as RS
    env = FaithfulDrMarioEnv(level=level, seed=seed, max_pills=maxpills); env.reset()
    NesPillSource(seed=seed).attach(env); env.cur = env._rand_pill(); env.nxt = env._rand_pill()
    elapsed = 0.0; garbage = 0; res = "stall"; v_at_topout = None
    ctx = {"own_vleft": 48, "opp_vleft": 48, "own_t": 0.0, "opp_t": 0.0, "opp_spawn_h": 0, "own_spawn_h": 0}
    steer.reset(seed); opp.reset(seed)
    for _ in range(maxpills):
        if env.board.virus_count() == 0: res = "clear"; break
        fb = FB.from_board(env.board); col, vir = RS.board_flat_from_fb(fb)
        ctx["own_vleft"] = env.board.virus_count(); ctx["own_t"] = elapsed
        a = choose(env, col, vir, ctx)
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
        ex = steer.execute(env.board.color.tolist(), int(a), env.pills_placed)
        (_, _, term, trunc, info), _straight = SM.place_executed(env, ex)
        if term:
            res = "clear" if info["won"] else "topout"
            if res == "topout": v_at_topout = env.board.virus_count()
            break
        if trunc: break
        if env.pills_placed >= CP.GARBAGE_MIN_PILLS:
            clear_size = max(0, occ_before + 2 - int(np.count_nonzero(env.board.color)))
            garbage += opp.after_placement(env.board, seed, env.pills_placed, clear_size)
            if env.board.virus_count() == 0: res = "clear"; break
            if env.board.spawn_blocked(): res = "topout"; v_at_topout = env.board.virus_count(); break
    vleft = v_at_topout if v_at_topout is not None else env.board.virus_count()
    out = {"seed": seed, "won": int(res == "clear"), "topout": int(res == "topout"), "stall": int(res == "stall"),
           "pills": env.pills_placed, "elapsed_s": round(elapsed, 1), "garbage": garbage, "vleft": int(vleft),
           "dies_ahead": int(res == "topout" and v_at_topout is not None and v_at_topout <= 12), "how": res}
    out["steer"] = dict(steer.stats)
    if hasattr(opp, "summary"):
        out["opp"] = opp.summary()
    return out


if __name__ == "__main__":
    build, oppname, lo, cnt, step, outp = sys.argv[1], sys.argv[2], int(sys.argv[3]), int(sys.argv[4]), int(sys.argv[5]), sys.argv[6]
    import steer_run as SR
    steer, choose = SR.make(build)
    opp = make_opponent(oppname)
    with open(outp, "w") as fh:
        for i in range(cnt):
            r = play(lo + i * step, choose, steer, opp)
            r.update({"arm": f"{build}@{oppname}", "model": oppname, "trate": 0.0})
            fh.write(json.dumps(r) + "\n"); fh.flush()
