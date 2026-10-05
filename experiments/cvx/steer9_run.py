"""STEER9 (PREREG_STEER9.md): "don't seal a live column" rules on the silicon-faithful brain, FAIR driver model.

  python steer9_run.py gb   ARM OPPONENT LO CNT STEP OUT
  python steer9_run.py race ARM LAM      LO CNT STEP OUT

REUSE (declared): the STEER8 harness verbatim -- steer8_run.ARMS["fD_bdepD"] (fair DRSETTLE: G0 -5 / round-start -4,
answer -6, tempo -6, PROPH-first D at f11, DEPLOYED fw mask T19/G0 8), stuck_probe.play_gb / play_race, refit_opp
opponents, the steer_model hooks, seeds 39134-40332. The ONLY difference from steer8_run.make("fD_bdepD") is the decider:
seal_steer9.SealFwDecider (= braingap Leaf6FwDecider + one STEER9 seal rule; P = 0 and wleaf = 0 is value-identical).
`s9_base` must reproduce the banked fD_bdepD rows (identity gate). Rows carry this file's sha, seal_steer9's sha, the
git HEAD, the arm's full spec, and the decider's activity counters (seal: dec / fired / changed).
"""
import sys, os, json, hashlib
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import import_pin; import_pin.pin()
import steer8_run as S8

HERE = os.path.dirname(os.path.abspath(__file__))
_SHA = hashlib.sha256(open(os.path.abspath(__file__), "rb").read()).hexdigest()[:16]
_SHA_SEAL = hashlib.sha256(open(os.path.join(HERE, "seal_steer9.py"), "rb").read()).hexdigest()[:16]
BASE_ARM = "fD_bdepD"
SEAL_ARMS = {
    "s9_base": dict(P=0, wleaf=0),                       # identity: == steer8 fD_bdepD rows
    "s9_V150": dict(kind=0, mode=0, P=150, wleaf=0),     # SEALV penalty: -150 per newly sealed virus (soft b1)
    "s9_VVETO": dict(kind=0, mode=1, P=20000, wleaf=0),  # SEALV veto: -20000 iff it seals and a 0-seal root exists
    "s9_CVETO": dict(kind=1, mode=1, P=20000, wleaf=0),  # SEALC veto: column-top virus only
}


def make(arm):
    import steer_model as SM, reach_fw_tap as RFT, vs_race as V, clock_play as CP
    import fast_rtl_x as FX, cascade_chain_x as C
    import seal_steer9 as S9
    spec = S8.ARMS[BASE_ARM]; t = spec["t"]
    assert spec["leaf6"] == dict(mode="dist_target", W=60, vk=4) and spec["sw"] == S8.SW_ON
    assert RFT.T_LAT == 19 and RFT.G0 == 8 and V.BASE_F == 45.0 and SM.G0_CHOICES == (7, 8)
    assert RFT.PROPH_END is None and RFT.LEDGE_T is None and RFT.DISTROW is False and RFT.PROPHFIRST is False
    # ---- verbatim steer8_run.make timing block ----
    RFT.PROPHFIRST = bool(t["mask_pfirst"])
    RFT.PROPH_END = t["mask_pend"]; RFT.DISTROW = bool(t["mask_b"]); RFT.LEDGE_T = t["mask_ledge"]
    g_mid, g_k0 = (7 + t["g0"], 8 + t["g0"]), (7 + t["g0_k0"], 8 + t["g0_k0"])
    SM.G0_CHOICES = g_mid; RFT.G0 = 8 + t["mask_g0"]
    RFT.T_LAT = 19 + t["mask"]; V.BASE_F = 45.0 + t["tempo"]; CP.T_LAT = 0.6 + t["tempo"] / 60.0988
    steer = SM.Steer(proph="throat", pulse=True, tap_period=2, tap_unified=True)
    steer.lat = [max(SM.F0, x + t["ans"]) for x in steer.lat]
    steer.proph_end_f = t["p_end"]; steer.dg_extra = S8.B_EXTRA if t["dg_b"] else None; steer.ledge_commit = bool(t["ledge_c"])
    steer.proph_first_end = t["p_first"]
    C.warmup_chain(topk2=8)
    w, fl = FX.variant("winner")
    dec = S9.SealFwDecider(w, fl, sw=dict(spec["sw"]), seal=dict(SEAL_ARMS[arm]), topk2=8, maxpass=0, w_chain=540,
                           ws=20, tap=2, **spec["leaf6"])
    def choose(env, col, vir, ctx):
        SM.G0_CHOICES = g_k0 if int(env.pills_placed) == 0 else g_mid
        return dec.choose(env.board, env.cur, env.nxt, k=env.pills_placed)
    return steer, choose, dec


if __name__ == "__main__":
    import stuck_probe as SP, refit_opp as RO
    mode, arm = sys.argv[1], sys.argv[2]
    stamp = {"wrapper": "steer9_run.py", "sha": _SHA, "seal_sha": _SHA_SEAL, "git": S8._git(), "arm": arm,
             "base": BASE_ARM, "spec": json.loads(json.dumps(S8.ARMS[BASE_ARM])), "seal": SEAL_ARMS[arm]}
    steer, choose, dec = make(arm)
    if mode == "gb":
        oppname, lo, cnt, step, outp = sys.argv[3], int(sys.argv[4]), int(sys.argv[5]), int(sys.argv[6]), sys.argv[7]
        opp = RO.make_opponent(oppname)
        with open(outp, "w") as fh:
            for i in range(cnt):
                dec.stats = dict(dec=0, fired=0, changed=0)
                r = SP.play_gb(lo + i * step, choose, steer, opp, probe=SP.StuckProbe())
                r.update({"arm": f"{arm}@{oppname}", "model": oppname, "trate": 0.0, "rig": stamp, "seal": dict(dec.stats)})
                fh.write(json.dumps(r) + "\n"); fh.flush()
    elif mode == "race":
        lam, lo, cnt, step, outp = float(sys.argv[3]), int(sys.argv[4]), int(sys.argv[5]), int(sys.argv[6]), sys.argv[7]
        with open(outp, "w") as fh:
            for i in range(cnt):
                dec.stats = dict(dec=0, fired=0, changed=0)
                r = SP.play_race(lo + i * step, arm, lam, level=11, steer=steer, probe=SP.StuckProbe(), choose=choose)
                r["arm"] = arm + "~steer"; r["level"] = 11; r["tap"] = 2; r["tap_unified"] = True; r["rig"] = stamp
                r["seal"] = dict(dec.stats)
                fh.write(json.dumps(r) + "\n"); fh.flush()
