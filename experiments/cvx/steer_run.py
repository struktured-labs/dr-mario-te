"""STEER1 runner: gate (b), OWNER burst model, L11, fw540 brain, with the steering-faithful execution layer.

  python steer_run.py ARM LO CNT STEP OUT.jsonl

ARM: off | couch | brainproph | prehold | pulse | reach   (see PREREG_STEER1.md)
"""
import sys, os, json
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import import_pin; import_pin.pin()
import gate_b as G
import bursty_model as BM
import vs_race as V
import steer_model as SM

ARMS = {
    "off":        dict(steer=None),
    "couch":      dict(steer=dict(proph="throat")),
    "brainproph": dict(steer=dict(proph="brain")),
    "prehold":    dict(steer=dict(proph="brain", prehold=True)),
    "pulse":      dict(steer=dict(proph="throat", pulse=True)),
    "reach":      dict(steer=dict(proph="throat"), reach=True),
}


def make(arm):
    spec = ARMS[arm]
    steer = SM.Steer(**spec["steer"]) if spec["steer"] is not None else None
    if spec.get("reach"):
        import fast_rtl_x as FX
        import cascade_chain_x as C
        import cascade_reach_x as R
        C.warmup_chain(topk2=8)
        w, fl = FX.variant("winner")
        dec = R.ReachAwareDecider(w, fl, topk2=8, maxpass=0, w_chain=540, ws=20)
        choose = lambda env, col, vir, ctx: dec.choose(env.board, env.cur, env.nxt, k=env.pills_placed)
    else:
        choose = V._decider("fw540")
    return steer, choose


if __name__ == "__main__":
    arm, lo, cnt, step, out = sys.argv[1], int(sys.argv[2]), int(sys.argv[3]), int(sys.argv[4]), sys.argv[5]
    model = BM.fit_struktured_20260804()
    steer, choose = make(arm)
    with open(out, "w") as fh:
        for i in range(cnt):
            r = G.play(lo + i * step, None, model, choose=choose, steer=steer)
            r.update({"arm": "fw540_steer_" + arm, "model": "owner", "trate": 0.0})
            fh.write(json.dumps(r) + "\n"); fh.flush()
