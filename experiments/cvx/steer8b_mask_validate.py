"""STEER8b (amended) gate: the reach mask rule vs the unified-tap frame simulator under each block-3 arm's driver model
(fair G0, PROPH window end p_end, fix A/B/C). "consistent" configs model the same driver on both sides and must agree
100%; "deployed" configs pair the DEPLOYED fw mask (PROPH to T_LAT, no B/C) with the arm's driver -- their disagreement is
a MEASURED mask/driver mismatch, reported, not a failure. Boards: today's-G0 games (as steer7/8 mask gates).

  python steer8b_mask_validate.py LEVEL SEED [SEED ...]
"""
import sys, os, json
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import import_pin; import_pin.pin()
import gate_b as G, bursty_model as BM, steer_model as SM, reach_fw_tap as RT
import cascade_chain_x as C, cascade_shape_x as S, fast_rtl_x as FX

TAP = 2
B_EXTRA = lambda thr, spd: min(7, max(0, thr - spd) // 2)
# name: (G0 shift, T, steer p_end, steer B, steer C, mask PROPH_END, mask DISTROW, mask LEDGE_T, kind)
CONFIGS = {
    "a2 today-consistent":   (0, 19, 10, False, False, 10, False, None, "consistent"),
    "a2 DEPLOYED mask":      (0, 19, 10, False, False, None, False, None, "deployed"),
    "b-ref":                 (-5, 13, 4, False, False, 4, False, None, "consistent"),
    "b-dep DEPLOYED mask":   (-5, 13, 4, False, False, None, False, None, "deployed"),
    "c-consistent":          (-5, 19, 10, False, False, 10, False, None, "consistent"),
    "b-ref+A":               (-5, 13, None, False, False, None, False, None, "consistent"),
    "b-ref+A+B":             (-5, 13, None, True, False, None, True, None, "consistent"),
    "b-ref+A+B+C":           (-5, 13, 4, True, True, None, True, 4, "consistent"),
}


def strict_mask(color, k, t, pend, b, c):
    out = [0] * 32
    for a in range(32):
        if SM.straight_cells(color, a // 8, a % 8) is None:
            continue
        st = SM.Steer(proph="throat", seed=0, pulse=True, tap_period=TAP, tap_unified=True)
        st.proph_end_f = pend; st.dg_extra = B_EXTRA if b else None; st.ledge_commit = c
        r = st.execute(color, a, k, t_act=t, phase=1)
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
    armed = sum(1 for color, k in recs if SM.proph_throat(color) in ("L", "R"))
    out = {"level": level, "seeds": seeds, "boards": len(recs), "proph_armed_boards": armed}
    for name, (g0s, t, pend, b, c, mpe, mrow, mledge, kind) in CONFIGS.items():
        SM.G0_CHOICES = (7 + g0s, 8 + g0s); RT.G0 = 8 + g0s; RT.T_LAT = t
        RT.PROPH_END = mpe; RT.DISTROW = mrow; RT.LEDGE_T = mledge
        n = agree = n_arm = agree_arm = 0
        for color, k in recs:
            fw = RT.reach_mask_fw(color, SM.table_threshold(k), tap=TAP)
            st = strict_mask(color, k, t, pend, b, c)
            arm = SM.proph_throat(color) in ("L", "R")
            for a in range(32):
                n += 1; agree += int(fw[a] == st[a])
                if arm:
                    n_arm += 1; agree_arm += int(fw[a] == st[a])
        out[name] = {"kind": kind, "agree_pct": round(100 * agree / n, 3), "mismatch": n - agree,
                     "armed_candidates": n_arm, "armed_agree_pct": round(100 * agree_arm / max(1, n_arm), 3)}
    SM.G0_CHOICES = (7, 8); RT.G0 = 8; RT.T_LAT = 19; RT.PROPH_END = None; RT.DISTROW = False; RT.LEDGE_T = None
    ok = all(v["agree_pct"] == 100.0 for v in out.values() if isinstance(v, dict) and v.get("kind") == "consistent")
    out["consistent_all_100"] = ok
    print(json.dumps(out, indent=1))
