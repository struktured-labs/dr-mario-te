"""STEER6c-s (POST-HOC sensitivity, PREREG_STEER6c.md addendum): the latency cost applied the way the RTL route
actually pays it -- ONLY on ACTIVE decisions (root viruses <= 4: when the D term is switched on) and at its measured
FRACTIONAL size D frames, realised as floor(D) + Bernoulli(frac(D)) whole frames per active decision (deterministic
per board). Inactive decisions run at nominal latency. Same four hooks as steer6_dlat.py (steer answer frame, reach
mask T_LAT, vs_race BASE_F, gate-b clock).

  python steer6_dlat_frac.py gb   ARM OPPONENT LO CNT STEP OUT DFRAMES
  python steer6_dlat_frac.py race ARM LAM      LO CNT STEP OUT DFRAMES
"""
import sys, os, json, hashlib, random
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import import_pin; import_pin.pin()


def wrap(choose0, steer, D, vk=4):
    import reach_fw_tap as RFT, vs_race as V, clock_play as CP
    lat0 = list(steer.lat); lats = [[x + j for x in lat0] for j in range(int(D) + 2)]
    stats = {"active": 0, "extra_frames": 0}

    def choose(env, col, vir, ctx):
        d = 0
        if int(env.board.virus_count()) <= vk:
            h = hashlib.md5(env.board.color.tobytes() + env.board.is_virus.tobytes() + int(env.pills_placed).to_bytes(2, "little")).hexdigest()
            u = random.Random(int(h[:12], 16)).random()
            d = int(D) + (1 if u < D - int(D) else 0)
            stats["active"] += 1; stats["extra_frames"] += d
        RFT.T_LAT = 19 + d; V.BASE_F = 45.0 + d; CP.T_LAT = 0.6 + d / 60.0988
        steer.lat = lats[d]
        return choose0(env, col, vir, ctx)
    return choose, stats


if __name__ == "__main__":
    import stuck_probe as SP, steer_model as SM, steer_run as SR, reach_fw_tap as RFT, vs_race as V
    assert RFT.T_LAT == 19 and V.BASE_F == 45.0
    mode, D = sys.argv[1], float(sys.argv[-1])
    if mode == "gb":
        import opp_run as OR
        arm, oppname, lo, cnt, step, outp = sys.argv[2], sys.argv[3], int(sys.argv[4]), int(sys.argv[5]), int(sys.argv[6]), sys.argv[7]
        steer, choose0 = SR.make(arm); opp = OR.make_opponent(oppname)
        choose, st = wrap(choose0, steer, D)
        with open(outp, "w") as fh:
            for i in range(cnt):
                st["active"] = st["extra_frames"] = 0
                r = SP.play_gb(lo + i * step, choose, steer, opp, probe=SP.StuckProbe())
                r.update({"arm": f"{arm}@{oppname}", "model": oppname, "trate": 0.0, "dfrac": D, "lat_active": st["active"],
                          "lat_extra_f": st["extra_frames"]})
                fh.write(json.dumps(r) + "\n"); fh.flush()
    elif mode == "race":
        arm, lam, lo, cnt, step, outp = sys.argv[2], float(sys.argv[3]), int(sys.argv[4]), int(sys.argv[5]), int(sys.argv[6]), sys.argv[7]
        steer = SM.Steer(proph="throat", pulse=True, tap_period=2, tap_unified=True)
        choose, st = wrap(SR.make(arm)[1], steer, D)
        with open(outp, "w") as fh:
            for i in range(cnt):
                st["active"] = st["extra_frames"] = 0
                r = SP.play_race(lo + i * step, arm, lam, level=11, steer=steer, probe=SP.StuckProbe(), choose=choose)
                r["arm"] = arm + "~steer"; r["level"] = 11; r["tap"] = 2; r["tap_unified"] = True
                r.update({"dfrac": D, "lat_active": st["active"], "lat_extra_f": st["extra_frames"]})
                fh.write(json.dumps(r) + "\n"); fh.flush()
