"""STEER6c: a STEER6 arm with its ANSWER LATENCY slowed by DLAT frames (the RTL route's extra cycles).

Applied consistently to every place the sim uses the answer latency:
  steer_model      each sampled first-answer frame + DLAT        (the couch driver acts later)
  reach_fw_tap     T_LAT 19 -> 19 + DLAT                          (the firmware mask's constant, matched)
  vs_race          BASE_F + DLAT frames per ply                   (race tempo; conservative: no overlap credit)
  gate (b) clock   CP.T_LAT + DLAT/60 s per placement             (elapsed only; gate-b garbage is per placement)
Applied to EVERY decision (conservative: the RTL cost is only paid while the term is active).
Wraps stuck_probe without editing it (it is imported by running jobs).

  python steer6_dlat.py gb   ARM OPPONENT LO CNT STEP OUT DLAT
  python steer6_dlat.py race ARM LAM      LO CNT STEP OUT DLAT
"""
import sys, os, json
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import import_pin; import_pin.pin()


def apply_dlat(d, steer=None):
    import reach_fw_tap as RFT, vs_race as V, clock_play as CP
    RFT.T_LAT = 19 + d
    V.BASE_F = 45.0 + d
    CP.T_LAT = 0.6 + d / 60.0988
    if steer is not None:
        steer.lat = [x + d for x in steer.lat]


if __name__ == "__main__":
    import stuck_probe as SP, steer_model as SM, steer_run as SR, reach_fw_tap as RFT, vs_race as V
    assert RFT.T_LAT == 19 and V.BASE_F == 45.0, "unexpected baseline constants"
    mode, d = sys.argv[1], int(sys.argv[-1])
    if mode == "gb":
        import opp_run as OR
        arm, oppname, lo, cnt, step, outp = sys.argv[2], sys.argv[3], int(sys.argv[4]), int(sys.argv[5]), int(sys.argv[6]), sys.argv[7]
        steer, choose = SR.make(arm); opp = OR.make_opponent(oppname)
        steer.lat = list(steer.lat)
        apply_dlat(d, steer)
        with open(outp, "w") as fh:
            for i in range(cnt):
                r = SP.play_gb(lo + i * step, choose, steer, opp, probe=SP.StuckProbe())
                r.update({"arm": f"{arm}@{oppname}", "model": oppname, "trate": 0.0, "dlat": d})
                fh.write(json.dumps(r) + "\n"); fh.flush()
    elif mode == "race":
        arm, lam, lo, cnt, step, outp = sys.argv[2], float(sys.argv[3]), int(sys.argv[4]), int(sys.argv[5]), int(sys.argv[6]), sys.argv[7]
        steer = SM.Steer(proph="throat", pulse=True, tap_period=2, tap_unified=True)
        steer.lat = list(steer.lat)
        choose = SR.make(arm)[1]
        apply_dlat(d, steer)
        with open(outp, "w") as fh:
            for i in range(cnt):
                r = SP.play_race(lo + i * step, arm, lam, level=11, steer=steer, probe=SP.StuckProbe(), choose=choose)
                r["arm"] = arm + "~steer"; r["level"] = 11; r["tap"] = 2; r["tap_unified"] = True; r["dlat"] = d
                fh.write(json.dumps(r) + "\n"); fh.flush()
