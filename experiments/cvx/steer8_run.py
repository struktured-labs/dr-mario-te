"""STEER8 (PREREG_STEER8.md): the SILICON-FAITHFUL brain (experiments/braingap Leaf6FwDecider: firmware eh_terms
semantics -- R4 hang, soft b1, eh skip on no-legal-ply-2 -- plus VETO / int16 wrap / Pass-0 order) under the corrected
2026-10 send fits, and the fair-settle (gravity-pin) pricing.

  python steer8_run.py gb   ARM OPPONENT LO CNT STEP OUT
  python steer8_run.py race ARM LAM      LO CNT STEP OUT
Same game loops as stuck_probe gb/race (unified DRTAPP=2 steering, reach_fw_tap mask, nominal latency unless the arm
shifts it). ARMS below; `*_off` arms switch every firmware switch off and must reproduce the banked python rows
(identity gate). Rows carry this file's sha, the git HEAD and the arm's full parameter dict.
"""
import sys, os, json, hashlib, subprocess
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import import_pin; import_pin.pin()

HERE = os.path.dirname(os.path.abspath(__file__))
_SHA = hashlib.sha256(open(os.path.abspath(__file__), "rb").read()).hexdigest()[:16]
SW_ON = dict(veto=1, hang=1, ehb1=1, ehnp=1, wrap=1, order=1)
SW_OFF = dict(veto=0, hang=0, ehb1=0, ehnp=0, wrap=0, order=0)
DIST = dict(mode="dist_target", W=60, vk=4)
OFF = dict(mode="off", W=0)
# timing (frames): g0 = gravity-start shift of the steer model (G0_CHOICES 7|8 = TODAY's pinned cart), g0_k0 = the same
# for the round-start pill; ans = steer answer-frame shift; mask = reach_fw_tap T_LAT shift; mask_g0 = reach_fw_tap G0
# shift; tempo = vs_race BASE_F / gate-b clock shift per placement
T0 = dict(g0=0, g0_k0=0, ans=0, mask=0, mask_g0=0, tempo=0,
          p_end=None, dg_b=False, ledge_c=False, mask_pend=None, mask_b=False, mask_ledge=None,
          p_first=None, mask_pfirst=False)   # fix D (DRPROPHFIRST): steer window end / mask spawn-row exit
# AMENDED 8b fields (PREREG_STEER8b amendment): p_end = steer PROPH window end (None = until the commit, the pre-STEER8b
# model); dg_b / ledge_c = fix B / fix C in the steer; mask_pend / mask_b / mask_ledge = the same in reach_fw_tap
# (None/False = the DEPLOYED fw mask: PROPH credited until T_LAT, no B, no C)
# STEER8b fair-settle arms AS FIRST PRE-REGISTERED (94a7f82e) -- SUPERSEDED by the amendment before any 8b game; NOT RUN
SETTLE = {
    "fD_sB_ref": dict(g0=-5, g0_k0=-4, ans=-6, mask=-6, mask_g0=-5, tempo=-6),  # fair DRSETTLE=3, mask refit T13/G0 3
    "fD_sB_dep": dict(g0=-5, g0_k0=-4, ans=-6, mask=0, mask_g0=0, tempo=-6),    # fair DRSETTLE=3, DEPLOYED fw mask T19/G0 8
    "fD_sC": dict(g0=-5, g0_k0=-4, ans=0, mask=0, mask_g0=-5, tempo=0),         # fair, no settle cut (settle 15, no pin)
}
ARMS = {
    "fA_off": dict(leaf6=OFF, sw=SW_OFF, t=T0),          # identity: == s5b_hsv512 (python ANTIBODY)
    "fD_off": dict(leaf6=DIST, sw=SW_OFF, t=T0),         # identity: == s6_dist_target60 (python DIST60)
    "fA": dict(leaf6=OFF, sw=SW_ON, t=T0),               # faithful ANTIBODY
    "fD": dict(leaf6=DIST, sw=SW_ON, t=T0),              # faithful DIST60 (= block 3 arm (a), today's timing)
    "fD_ehb0": dict(leaf6=DIST, sw={**SW_ON, "ehb1": 0}, t=T0),   # eh on the TRUE b1 (firmware-fix candidate)
    "fD_hang0": dict(leaf6=DIST, sw={**SW_ON, "hang": 0}, t=T0),  # flat hang instead of R4
}
for name, t in SETTLE.items():
    ARMS[name] = dict(leaf6=DIST, sw=SW_ON, t={**T0, **t})
# AMENDED STEER8b block 3 (settle lane, Mesen frame traces, CONFIRMED; PREREG_STEER8b.md amendment)
FAIR = dict(g0=-5, g0_k0=-4)
SETTLE2 = {
    "fD_a2":      dict(p_end=10),                                                         # (a) today, PROPH to 1st pub
    "fD_bdep2":   dict(**FAIR, ans=-6, tempo=-6, p_end=4),                                # (b) fair, DEPLOYED mask
    "fD_bref2":   dict(**FAIR, ans=-6, tempo=-6, p_end=4, mask=-6, mask_g0=-5, mask_pend=4),   # (b) fair, REFIT mask
    "fD_c2":      dict(**FAIR, p_end=10, mask_g0=-5),                                     # (c) fair, no settle cut
    "fD_brefA":   dict(**FAIR, ans=-6, tempo=-6, p_end=None, mask=-6, mask_g0=-5),        # + fix A (PROPH to commit)
    "fD_brefAB":  dict(**FAIR, ans=-6, tempo=-6, p_end=None, mask=-6, mask_g0=-5, dg_b=True, mask_b=True),
    "fD_brefABC": dict(**FAIR, ans=-6, tempo=-6, p_end=4, mask=-6, mask_g0=-5, dg_b=True, mask_b=True,
                       ledge_c=True, mask_ledge=4),                                       # + fix C (armed: commit at p_end)
}
for name, t in SETTLE2.items():
    ARMS[name] = dict(leaf6=DIST, sw=SW_ON, t={**T0, **t})
# SECOND AMENDMENT (fix D, settle lane Mesen pick; A/AB/ABC above ruled out by Mesen -- NOT RUN)
SETTLE3 = {
    # armed pills: D's window [F0, min(11, spawn-row exit)) governs PROPH (p_end must stay None so it is not cut at 4)
    "fD_brefD": dict(**FAIR, ans=-6, tempo=-6, mask=-6, mask_g0=-5,
                     p_first=11, mask_ledge=11, mask_pfirst=True),          # fair, REFIT mask (PROPH [F0, GO+6)), D driver
    "fD_bdepD": dict(**FAIR, ans=-6, tempo=-6, p_first=11),                 # fair, DEPLOYED fw mask, D driver
}
for name, t in SETTLE3.items():
    ARMS[name] = dict(leaf6=DIST, sw=SW_ON, t={**T0, **t})
B_EXTRA = lambda thr, spd: min(7, max(0, thr - spd) // 2)    # fix B (DRDISTROW): replaces the 0-free-row budget

def _git():
    try:
        return subprocess.run(["git", "-C", HERE, "rev-parse", "--short=8", "HEAD"], capture_output=True, text=True,
                              timeout=10).stdout.strip()
    except Exception:
        return "?"


def make(arm):
    import steer_model as SM, reach_fw_tap as RFT, vs_race as V, clock_play as CP
    import fast_rtl_x as FX, cascade_chain_x as C
    sys.path.insert(0, os.path.join(HERE, "..", "braingap"))
    import cascade_leaf6fw_braingap_20261003 as FW
    spec = ARMS[arm]; t = spec["t"]
    assert RFT.T_LAT == 19 and RFT.G0 == 8 and V.BASE_F == 45.0 and SM.G0_CHOICES == (7, 8)
    assert RFT.PROPH_END is None and RFT.LEDGE_T is None and RFT.DISTROW is False and RFT.PROPHFIRST is False
    RFT.PROPHFIRST = bool(t["mask_pfirst"])
    RFT.PROPH_END = t["mask_pend"]; RFT.DISTROW = bool(t["mask_b"]); RFT.LEDGE_T = t["mask_ledge"]
    g_mid, g_k0 = (7 + t["g0"], 8 + t["g0"]), (7 + t["g0_k0"], 8 + t["g0_k0"])
    SM.G0_CHOICES = g_mid; RFT.G0 = 8 + t["mask_g0"]
    RFT.T_LAT = 19 + t["mask"]; V.BASE_F = 45.0 + t["tempo"]; CP.T_LAT = 0.6 + t["tempo"] / 60.0988
    steer = SM.Steer(proph="throat", pulse=True, tap_period=2, tap_unified=True)
    steer.lat = [max(SM.F0, x + t["ans"]) for x in steer.lat]
    steer.proph_end_f = t["p_end"]; steer.dg_extra = B_EXTRA if t["dg_b"] else None; steer.ledge_commit = bool(t["ledge_c"])
    steer.proph_first_end = t["p_first"]
    C.warmup_chain(topk2=8)
    w, fl = FX.variant("winner")
    dec = FW.Leaf6FwDecider(w, fl, sw=dict(spec["sw"]), topk2=8, maxpass=0, w_chain=540, ws=20, tap=2, **spec["leaf6"])
    def choose(env, col, vir, ctx):
        # round-start pill: its own gravity start (the steer model executes this pill right after choose returns)
        SM.G0_CHOICES = g_k0 if int(env.pills_placed) == 0 else g_mid
        return dec.choose(env.board, env.cur, env.nxt, k=env.pills_placed)
    return steer, choose


if __name__ == "__main__":
    import stuck_probe as SP, refit_opp as RO
    mode, arm = sys.argv[1], sys.argv[2]
    stamp = {"wrapper": "steer8_run.py", "sha": _SHA, "git": _git(), "arm": arm,
             "spec": json.loads(json.dumps(ARMS[arm]))}
    steer, choose = make(arm)
    if mode == "gb":
        oppname, lo, cnt, step, outp = sys.argv[3], int(sys.argv[4]), int(sys.argv[5]), int(sys.argv[6]), sys.argv[7]
        opp = RO.make_opponent(oppname)
        with open(outp, "w") as fh:
            for i in range(cnt):
                r = SP.play_gb(lo + i * step, choose, steer, opp, probe=SP.StuckProbe())
                r.update({"arm": f"{arm}@{oppname}", "model": oppname, "trate": 0.0, "rig": stamp})
                fh.write(json.dumps(r) + "\n"); fh.flush()
    elif mode == "race":
        lam, lo, cnt, step, outp = float(sys.argv[3]), int(sys.argv[4]), int(sys.argv[5]), int(sys.argv[6]), sys.argv[7]
        with open(outp, "w") as fh:
            for i in range(cnt):
                r = SP.play_race(lo + i * step, arm, lam, level=11, steer=steer, probe=SP.StuckProbe(), choose=choose)
                r["arm"] = arm + "~steer"; r["level"] = 11; r["tap"] = 2; r["tap_unified"] = True; r["rig"] = stamp
                fh.write(json.dumps(r) + "\n"); fh.flush()
