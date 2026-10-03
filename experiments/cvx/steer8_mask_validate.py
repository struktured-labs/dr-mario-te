"""STEER8b gate (fair G0): STEER7 gate G2 re-run with the gravity start shifted by STEER8_G0SHIFT (default -5:
steer_model G0_CHOICES 2|3, reach_fw_tap G0 3). Original doc: STEER7 gate G2: the reach mask rule (reach_fw_tap.reach_mask_fw, tap=2) at the SHIFTED T_LAT constants STEER7 uses
vs the unified-tap frame simulator (steer_model, strict: exact straight-drop landing) with the answer at the same frame.
reach_fw_tap was validated at T_LAT = 19 only (STEER2/STEER4); STEER7 runs it at 20, 18, 17, 15 (and lower on active
decisions) and at F0 = 3 (the zero-latency ceiling). Same method as reach_fw_tap_validate.py.

  python steer7_mask_validate.py LEVEL SEED [SEED ...]
"""
import sys, os, json
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import import_pin; import_pin.pin()
import gate_b as G, bursty_model as BM, steer_model as SM, reach_fw_tap as RT
import cascade_chain_x as C, cascade_shape_x as S, fast_rtl_x as FX

TAP = 2
TS = (7, 13, 19)
G0S = int(os.environ.get("STEER8_G0SHIFT", "-5"))


def strict_mask(color, k, t):
    out = [0] * 32
    for a in range(32):
        if SM.straight_cells(color, a // 8, a % 8) is None:
            continue
        r = SM.Steer(proph="throat", seed=0, pulse=True, tap_period=TAP, tap_unified=True).execute(
            color, a, k, t_act=t, phase=1)
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
    SM.G0_CHOICES = (7 + G0S, 8 + G0S); RT.G0 = 8 + G0S                 # boards above were played at TODAY's G0
    out = {"level": level, "seeds": seeds, "boards": len(recs), "G0_CHOICES": SM.G0_CHOICES, "RT_G0": RT.G0}
    for t in TS:
        RT.T_LAT = t
        n = agree = allowed_fw = allowed_st = 0; bad_k = []
        for color, k in recs:
            fw = RT.reach_mask_fw(color, SM.table_threshold(k), tap=TAP)
            st = strict_mask(color, k, t)
            for a in range(32):
                n += 1; agree += int(fw[a] == st[a]); allowed_fw += fw[a]; allowed_st += st[a]
                if fw[a] != st[a]:
                    bad_k.append(k)
        out[f"T{t}"] = {"candidates": n, "agree_pct": round(100 * agree / n, 3), "mismatch": n - agree,
                        "mismatch_k_lt_300": sum(1 for k in bad_k if k < 300),
                        "allowed_per_board_fw": round(allowed_fw / len(recs), 2),
                        "allowed_per_board_sim": round(allowed_st / len(recs), 2)}
    RT.T_LAT = 19
    print(json.dumps(out))
