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
    # POST-HOC SENSITIVITY (not pre-registered): rotation-conditional answer latency (steer_model.latency_by_rot)
    "couch_byrot":   dict(steer=dict(proph="throat", lat_mode="byrot")),
    "prehold_byrot": dict(steer=dict(proph="brain", prehold=True, lat_mode="byrot")),
    # POST-HOC REALISTIC (not pre-registered): arm (3) with the direction taken from the PREVIOUS search's ply-2
    # plan for this pill (cascade_plan_x) instead of the oracle final target -- what a firmware change can deliver
    "prehold_plan":       dict(steer=dict(proph="plan", prehold=True), plan=True),
    "prehold_plan_byrot": dict(steer=dict(proph="plan", prehold=True, lat_mode="byrot"), plan=True),
    # STEER2: dose x reach under couch steering (decider built by vs_race._decider)
    "w180":       dict(steer=dict(proph="throat"), dec="fw_winner"),
    "w180_reach": dict(steer=dict(proph="throat"), dec="fw_winner_reach"),
    "reachfw":    dict(steer=dict(proph="throat"), dec="fw540_reachfw"),        # STEER2 post-hoc firmware rule
    # STEER3: tap-steering at P frames/column for ALL normal moves, reach root simulating the same P
    **{f"tap{P}_reach": dict(steer=dict(proph="throat", pulse=True, tap_period=P), tapreach=P) for P in (2, 3, 4, 5)},
    # STEER4: the SHIPPING couch build (fw540 + reach_fw_tap mask P=2 + unified DRTAPP=2 steering) + shape terms
    **{name: dict(steer=dict(proph="throat", pulse=True, tap_period=2, tap_unified=True), shape=kw) for name, kw in {
        "s4_base":  {},
        "s4_sv180": {"w_sv": 180, "r_hi": 9},
        "s4_sv540": {"w_sv": 540, "r_hi": 9},
        "s4_sp100": {"w_sp": 100, "hs": 10},
        "s4_sp300": {"w_sp": 300, "hs": 10},
        "s4_rot2":  {"rot_margin": 2},
        "s4_combo": {"w_sv": 180, "r_hi": 9, "rot_margin": 2},    # arm (4) by the pre-registered rule
    }.items()},
}


def make(arm):
    spec = ARMS[arm]
    steer = SM.Steer(**spec["steer"]) if spec["steer"] is not None else None
    if spec.get("plan"):
        import fast_rtl_x as FX
        import cascade_chain_x as C
        import cascade_plan_x as PX
        C.warmup_chain(topk2=8)
        w, fl = FX.variant("winner")
        dec = PX.PlanDecider(w, fl, topk2=8, maxpass=0, w_chain=540, ws=20)
        steer.use_hint = True
        state = {"next_hint": None}

        def choose(env, col, vir, ctx):
            if env.pills_placed == 0:
                state["next_hint"] = None
            steer.hint_side = state["next_hint"]          # plan made by the PREVIOUS search (None on pill 0)
            a = dec.choose(env.board, env.cur, env.nxt)
            p2 = dec.plan
            state["next_hint"] = None if p2 < 0 else SM.target_side(p2 // 8, p2 % 8)
            return a
        return steer, choose
    if "shape" in spec:
        import fast_rtl_x as FX
        import cascade_chain_x as C
        import cascade_shape_x as SH
        C.warmup_chain(topk2=8)
        w, fl = FX.variant("winner")
        dec = SH.ShapeReachDecider(w, fl, topk2=8, maxpass=0, w_chain=540, ws=20, tap=2, **spec["shape"])
        return steer, (lambda env, col, vir, ctx: dec.choose(env.board, env.cur, env.nxt, k=env.pills_placed))
    if spec.get("tapreach"):
        import fast_rtl_x as FX
        import cascade_chain_x as C
        import cascade_reach_x as R
        C.warmup_chain(topk2=8)
        w, fl = FX.variant("winner")
        dec = R.ReachAwareDecider(w, fl, topk2=8, maxpass=0, w_chain=540, ws=20,
                                  steer_kw={"pulse": True, "tap_period": spec["tapreach"]})
        return steer, (lambda env, col, vir, ctx: dec.choose(env.board, env.cur, env.nxt, k=env.pills_placed))
    if spec.get("reach"):
        import fast_rtl_x as FX
        import cascade_chain_x as C
        import cascade_reach_x as R
        C.warmup_chain(topk2=8)
        w, fl = FX.variant("winner")
        dec = R.ReachAwareDecider(w, fl, topk2=8, maxpass=0, w_chain=540, ws=20)
        choose = lambda env, col, vir, ctx: dec.choose(env.board, env.cur, env.nxt, k=env.pills_placed)
    else:
        choose = V._decider(spec.get("dec", "fw540"))
    return steer, choose


if __name__ == "__main__":
    arm, lo, cnt, step, out = sys.argv[1], int(sys.argv[2]), int(sys.argv[3]), int(sys.argv[4]), sys.argv[5]
    level = int(sys.argv[6]) if len(sys.argv) > 6 else 11
    model = BM.fit_struktured_20260804()
    steer, choose = make(arm)
    with open(out, "w") as fh:
        for i in range(cnt):
            r = G.play(lo + i * step, None, model, level=level, choose=choose, steer=steer)
            r.update({"arm": "fw540_steer_" + arm, "model": "owner", "trate": 0.0})
            if level != 11: r["level"] = level
            fh.write(json.dumps(r) + "\n"); fh.flush()
