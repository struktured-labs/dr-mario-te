"""STEER10 (PREREG_STEER10.md): endgame-stall / edge-column rules on the silicon-faithful brain, FAIR driver model.

  python steer10_run.py gb   ARM OPPONENT LO CNT STEP OUT
  python steer10_run.py race ARM LAM SIZES LO CNT STEP OUT        SIZES = hartford | lulu202610b

REUSE (declared): the STEER8/9 harness verbatim -- steer8_run.ARMS["fD_bdepD"] (fair DRSETTLE: G0 -5 / round-start -4,
answer -6, tempo -6, PROPH-first D at f11, DEPLOYED fw mask T19/G0 8), stuck_probe.play_gb / play_race, refit_opp
opponents, the steer_model hooks. The ONLY difference from steer8_run.make("fD_bdepD") is the decider:
rules_steer10.S10Decider (= braingap Leaf6FwDecider + one STEER10 rule; the empty rule is value-identical).
`s10_base` must reproduce the banked fD_bdepD rows (identity gate).
SIZES: vs_race.SIZES for the race's volley sizes. hartford = vs_race's own (2:73% 3:17% 4:10%, the rc10 instrument of
STEER6r-9); lulu202610b = lulu_fit_202610b.json size_hist renormalised over 2-4 (112/9/14 of 135). Only the size mapping
of each volley's uniform draw changes; the volley TIMES and colours (CRN stream keyed by seed, lam) are unchanged.
Rows carry this file's sha, rules_steer10's sha, the git HEAD, the arm's full spec, SIZES, and the decider's activity
counters.
"""
import sys, os, json, hashlib
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import import_pin; import_pin.pin()
import steer8_run as S8

HERE = os.path.dirname(os.path.abspath(__file__))
_SHA = hashlib.sha256(open(os.path.abspath(__file__), "rb").read()).hexdigest()[:16]
_SHA_RULES = hashlib.sha256(open(os.path.join(HERE, "rules_steer10.py"), "rb").read()).hexdigest()[:16]
BASE_ARM = "fD_bdepD"
SIZES = {
    "hartford": ((2, 0.73), (3, 0.17), (4, 0.10)),
    "lulu202610b": ((2, 112 / 135), (3, 9 / 135), (4, 14 / 135)),
}
RULE_ARMS = {
    "s10_base": dict(),                                   # identity: == steer8 fD_bdepD rows
    # PRE-REGISTERED arms (PREREG_STEER10.md sec. 4), chosen from the mechanism grid (steer10/mech_check.txt)
    "s10_A16": dict(vk=16),                               # (a) dist_target gate vk 4 -> 16 (W 60, min-D target)
    "s10_R60": dict(kind="ereach", P=60, h0=11),          # (d) edge reach, dig-preserving dose
    "s10_R120": dict(kind="ereach", P=120, h0=11),        # (d) edge reach, stronger dose
    "s10_A16R120": dict(vk=16, kind="ereach", P=120, h0=11),   # (a) + (d) combined (combined flags need a combined cert)
}


def make(arm):
    import steer_model as SM, reach_fw_tap as RFT, vs_race as V, clock_play as CP
    import cascade_chain_x as C
    import rules_steer10 as R10
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
    dec = R10.make(dict(RULE_ARMS[arm]))
    def choose(env, col, vir, ctx):
        SM.G0_CHOICES = g_k0 if int(env.pills_placed) == 0 else g_mid
        return dec.choose(env.board, env.cur, env.nxt, k=env.pills_placed)
    return steer, choose, dec


if __name__ == "__main__":
    import stuck_probe as SP, refit_opp as RO, vs_race as V
    mode, arm = sys.argv[1], sys.argv[2]
    stamp = {"wrapper": "steer10_run.py", "sha": _SHA, "rules_sha": _SHA_RULES, "git": S8._git(), "arm": arm,
             "base": BASE_ARM, "spec": json.loads(json.dumps(S8.ARMS[BASE_ARM])), "rule": RULE_ARMS[arm]}
    steer, choose, dec = make(arm)
    zero = lambda: {k: 0 for k in dec.stats}
    if mode == "gb":
        oppname, lo, cnt, step, outp = sys.argv[3], int(sys.argv[4]), int(sys.argv[5]), int(sys.argv[6]), sys.argv[7]
        opp = RO.make_opponent(oppname)
        with open(outp, "w") as fh:
            for i in range(cnt):
                dec.stats = zero()
                r = SP.play_gb(lo + i * step, choose, steer, opp, probe=SP.StuckProbe())
                r.update({"arm": f"{arm}@{oppname}", "model": oppname, "trate": 0.0, "rig": stamp, "rule": dict(dec.stats)})
                fh.write(json.dumps(r) + "\n"); fh.flush()
    elif mode == "race":
        lam, sizes = float(sys.argv[3]), sys.argv[4]
        lo, cnt, step, outp = int(sys.argv[5]), int(sys.argv[6]), int(sys.argv[7]), sys.argv[8]
        V.SIZES = SIZES[sizes]
        stamp["sizes"] = sizes
        with open(outp, "w") as fh:
            for i in range(cnt):
                dec.stats = zero()
                r = SP.play_race(lo + i * step, arm, lam, level=11, steer=steer, probe=SP.StuckProbe(), choose=choose)
                r["arm"] = arm + "~steer"; r["level"] = 11; r["tap"] = 2; r["tap_unified"] = True; r["rig"] = stamp
                r["sizes"] = sizes; r["rule"] = dict(dec.stats)
                fh.write(json.dumps(r) + "\n"); fh.flush()
