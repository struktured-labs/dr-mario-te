"""STEER7 DECLARED SECONDARY (PREREG_STEER7.md addendum, added AFTER the prereg because of the couch tracker bug):
the same wrapper as steer7_dlat.py (imported, not copied: steer7_dlat.wrap is the executed code path) with the
corrected 2026-10 send fits -- gate (b) on owner_fit_202610, the LULU race at lam 2.56.

  python steer7_refit.py gb   ARM OPPONENT LO CNT STEP OUT SHIFT     OPPONENT: owner202610 | any opp_run name
  python steer7_refit.py race ARM LAM      LO CNT STEP OUT SHIFT
Identity: with OPPONENT owner0804 / LAM 6 this must reproduce steer7_dlat.py rows (= banked STEER6d rows at S = 0).
"""
import sys, os, json, hashlib
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import import_pin; import_pin.pin()
import steer7_dlat as S7

_SHA = hashlib.sha256(open(os.path.abspath(__file__), "rb").read()).hexdigest()[:16]

if __name__ == "__main__":
    import stuck_probe as SP, steer_model as SM, steer_run as SR, reach_fw_tap as RFT, vs_race as V, refit_opp as RO
    assert RFT.T_LAT == 19 and V.BASE_F == 45.0
    S7._GIT = S7._git_head()
    mode, sh = sys.argv[1], sys.argv[-1]
    shift = "ceil" if sh == "ceil" else int(sh)
    xs = S7.deltas()
    stamp = {"wrapper": "steer7_refit.py", "sha": _SHA, "steer7_dlat_sha": S7._SRC_SHA, "git": S7._GIT}
    if mode == "gb":
        arm, oppname, lo, cnt, step, outp = sys.argv[2], sys.argv[3], int(sys.argv[4]), int(sys.argv[5]), int(sys.argv[6]), sys.argv[7]
        steer, choose0 = SR.make(arm); opp = RO.make_opponent(oppname)
        choose, st, reset = S7.wrap(choose0, steer, xs, shift)
        with open(outp, "w") as fh:
            for i in range(cnt):
                reset()
                r = SP.play_gb(lo + i * step, choose, steer, opp, probe=SP.StuckProbe())
                r.update({"arm": f"{arm}@{oppname}", "model": oppname, "trate": 0.0})
                r.update(S7._row_extra(shift, st)); r["rig"] = stamp
                fh.write(json.dumps(r) + "\n"); fh.flush()
    elif mode == "race":
        arm, lam, lo, cnt, step, outp = sys.argv[2], float(sys.argv[3]), int(sys.argv[4]), int(sys.argv[5]), int(sys.argv[6]), sys.argv[7]
        steer = SM.Steer(proph="throat", pulse=True, tap_period=2, tap_unified=True)
        choose, st, reset = S7.wrap(SR.make(arm)[1], steer, xs, shift)
        with open(outp, "w") as fh:
            for i in range(cnt):
                reset()
                r = SP.play_race(lo + i * step, arm, lam, level=11, steer=steer, probe=SP.StuckProbe(), choose=choose)
                r["arm"] = arm + "~steer"; r["level"] = 11; r["tap"] = 2; r["tap_unified"] = True
                r.update(S7._row_extra(shift, st)); r["rig"] = stamp
                fh.write(json.dumps(r) + "\n"); fh.flush()
