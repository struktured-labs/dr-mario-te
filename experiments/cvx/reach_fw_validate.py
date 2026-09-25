"""Validate reach_fw.reach_mask_fw (closed-form firmware rule) against the frame simulator on real boards.
Boards come from gate-(b) games (fw540, owner model, couch steering). Two references:
  lenient = cascade_reach_x.ReachAwareDecider.mask (column+orientation match; counts tuck landings)
  strict  = the capsule lands EXACTLY on the brain's straight-drop cells (what the brain scored)
Usage: python reach_fw_validate.py LEVEL SEED [SEED ...]
"""
import sys, os, json
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import import_pin; import_pin.pin()
import numpy as np
import gate_b as G, bursty_model as BM, vs_race as V, steer_model as SM, reach_fw as RF
import cascade_chain_x as C, cascade_reach_x as R, fast_rtl_x as FX

if __name__ == "__main__":
    level = int(sys.argv[1]); seeds = [int(x) for x in sys.argv[2:]]
    C.warmup_chain(topk2=8); w, fl = FX.variant("winner")
    dec = R.ReachAwareDecider(w, fl, topk2=8, maxpass=0, w_chain=540, ws=20)
    m = BM.fit_struktured_20260804(); base = V._decider("fw540")
    recs = []
    def choose(env, col, vir, ctx):
        recs.append((env.board.color.tolist(), env.pills_placed, env.board.clone(),
                     int(env.cur.a), int(env.cur.b), int(env.nxt.a), int(env.nxt.b)))
        return base(env, col, vir, ctx)
    for s in seeds:
        G.play(s, None, m, level=level, choose=choose, steer=SM.Steer(proph="throat"))
    n = a_len = a_str = arg_len = arg_str = 0
    for color, k, b, ca, cb, na, nb in recs:
        thr = SM.table_threshold(k)
        fw = RF.reach_mask_fw(color, thr)
        len_m = [int(x) for x in dec.mask(b, k)]
        strict = [0] * 32
        for a in range(32):
            if SM.straight_cells(color, a // 8, a % 8) is None:
                continue
            r = SM.Steer(proph="throat", seed=0).execute(color, a, k, t_act=19, phase=1)
            strict[a] = int(r["exact"] and SM.is_straight(color, r))
        if not any(strict):
            strict = [1] * 32
        a_len += sum(int(x == y) for x, y in zip(fw, len_m)); a_str += sum(int(x == y) for x, y in zip(fw, strict)); n += 32
        col_, vir_ = R.board_flat(b); lnk = np.ascontiguousarray(b.link, dtype=np.int8).reshape(-1)
        pick = lambda mk: R._choose_d3_chain_s_masked(col_, vir_, lnk, ca, cb, na, nb, 8, dec.w_excav, dec.w_hang,
                                                      dec.w, dec.fl, 0, 540, 20, np.asarray(mk, dtype=np.int8))
        af = pick(fw); arg_len += int(af == pick(len_m)); arg_str += int(af == pick(strict))
    B = len(recs)
    print(json.dumps({"level": level, "seeds": seeds, "boards": B,
                      "action_agree_strict": round(100 * a_str / n, 3), "action_agree_lenient": round(100 * a_len / n, 3),
                      "argmax_agree_strict": round(100 * arg_str / B, 3), "argmax_agree_lenient": round(100 * arg_len / B, 3)}))
