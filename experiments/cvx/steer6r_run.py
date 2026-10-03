"""STEER6r (PREREG_STEER6r.md): the stuck_probe runner (gate (b) and race, nominal answer latency, unified tap
steering) with the corrected 2026-10 send fits available as opponents (refit_opp.py).

  python steer6r_run.py gb   BUILD OPPONENT LO CNT STEP OUT      OPPONENT: owner202610 | lulu202610 | opp_run names
  python steer6r_run.py race BUILD LAM      LO CNT STEP OUT
Same code path as `stuck_probe.py gb|race` (identity: with owner0804 / lam 6 / lam 4.7 it reproduces the banked
STEER6 rows). Rows carry this file's sha and the git HEAD.
"""
import sys, os, json, hashlib, subprocess
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import import_pin; import_pin.pin()

HERE = os.path.dirname(os.path.abspath(__file__))
_SHA = hashlib.sha256(open(os.path.abspath(__file__), "rb").read()).hexdigest()[:16]


def _git():
    try:
        return subprocess.run(["git", "-C", HERE, "rev-parse", "--short=8", "HEAD"], capture_output=True, text=True,
                              timeout=10).stdout.strip()
    except Exception:
        return "?"


if __name__ == "__main__":
    import stuck_probe as SP, steer_model as SM, refit_opp as RO
    stamp = {"wrapper": "steer6r_run.py", "sha": _SHA, "git": _git()}
    mode = sys.argv[1]
    if mode == "gb":
        import steer_run as SR
        build, oppname, lo, cnt, step, outp = sys.argv[2], sys.argv[3], int(sys.argv[4]), int(sys.argv[5]), int(sys.argv[6]), sys.argv[7]
        steer, choose = SR.make(build); opp = RO.make_opponent(oppname)
        with open(outp, "w") as fh:
            for i in range(cnt):
                r = SP.play_gb(lo + i * step, choose, steer, opp, probe=SP.StuckProbe())
                r.update({"arm": f"{build}@{oppname}", "model": oppname, "trate": 0.0, "rig": stamp})
                fh.write(json.dumps(r) + "\n"); fh.flush()
    elif mode == "race":
        build, lam, lo, cnt, step, outp = sys.argv[2], float(sys.argv[3]), int(sys.argv[4]), int(sys.argv[5]), int(sys.argv[6]), sys.argv[7]
        steer = SM.Steer(proph="throat", pulse=True, tap_period=2, tap_unified=True)
        choose = None
        if build.startswith("s6_"):                        # == stuck_probe's race main
            import steer_run as SR
            choose = SR.make(build)[1]
        with open(outp, "w") as fh:
            for i in range(cnt):
                r = SP.play_race(lo + i * step, build, lam, level=11, steer=steer, probe=SP.StuckProbe(), choose=choose)
                r["arm"] = build + "~steer"; r["level"] = 11; r["tap"] = 2; r["tap_unified"] = True; r["rig"] = stamp
                fh.write(json.dumps(r) + "\n"); fh.flush()
