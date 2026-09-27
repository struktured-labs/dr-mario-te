"""STEER4 G1': the unified-tap frame simulator (steer_model tap_unified, P=2, the shipping DRTAPP=2 cart) vs the
shipping mask rule reach_fw_tap.reach_mask_fw(tap=2) -- strict (exact straight-drop landing), on boards from
baseline games (fw540 + reach_fw_tap mask, unified tap steering).
Usage: python reach_fw_tap_validate.py LEVEL SEED [SEED ...]
"""
import sys, os, json
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import import_pin; import_pin.pin()
import numpy as np
import gate_b as G, bursty_model as BM, steer_model as SM, reach_fw_tap as RT
import cascade_chain_x as C, cascade_shape_x as S, fast_rtl_x as FX

TAP = 2


def strict_mask(color, k):
    out = [0] * 32
    for a in range(32):
        if SM.straight_cells(color, a // 8, a % 8) is None:
            continue
        r = SM.Steer(proph="throat", seed=0, pulse=True, tap_period=TAP, tap_unified=True).execute(
            color, a, k, t_act=19, phase=1)
        out[a] = int(r["exact"] and SM.is_straight(color, r))
    return out if any(out) else [1] * 32


if __name__ == "__main__":
    level = int(sys.argv[1]); seeds = [int(x) for x in sys.argv[2:]]
    C.warmup_chain(topk2=8); w, fl = FX.variant("winner")
    dec = S.ShapeReachDecider(w, fl, tap=TAP)
    m = BM.fit_struktured_20260804(); recs = []
    def choose(env, col, vir, ctx):
        recs.append((env.board.color.tolist(), env.pills_placed))
        return dec.choose(env.board, env.cur, env.nxt, k=env.pills_placed)
    for s in seeds:
        G.play(s, None, m, level=level, choose=choose,
               steer=SM.Steer(proph="throat", pulse=True, tap_period=TAP, tap_unified=True))
    n = agree = 0; bad = []
    for color, k in recs:
        fw = RT.reach_mask_fw(color, SM.table_threshold(k), tap=TAP)
        st = strict_mask(color, k)
        for a in range(32):
            n += 1; agree += int(fw[a] == st[a])
            if fw[a] != st[a]:
                bad.append((k, a, fw[a], st[a]))
    print(json.dumps({"level": level, "seeds": seeds, "boards": len(recs), "candidates": n,
                      "agree_pct": round(100 * agree / n, 3),
                      "mismatch_k_hist": dict(__import__("collections").Counter(b[0] // 50 * 50 for b in bad)),
                      "agree_pct_k_lt_300": round(100 * (1 - sum(1 for b in bad if b[0] < 300) /
                                                        max(1, 32 * sum(1 for _, k in recs if k < 300))), 3)}))
