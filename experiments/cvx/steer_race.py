"""STEER2 race runner: vs_race.play with the couch steering model (steer_model.Steer(proph="throat")).

  python steer_race.py ARM LAM LO CNT STEP OUT.jsonl [LEVEL]

ARM is any vs_race arm (fw540, fw_winner, fw540_reach, fw_winner_reach, ...). Rows are labelled ARM + "~steer"
so analyze_vsrace groups them apart from the perfect-execution rows.
"""
import sys, os, json
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import vs_race as V
import steer_model as SM

if __name__ == "__main__":
    arm, lam, lo, cnt, step, out = sys.argv[1], float(sys.argv[2]), int(sys.argv[3]), int(sys.argv[4]), int(sys.argv[5]), sys.argv[6]
    level = int(sys.argv[7]) if len(sys.argv) > 7 else 11
    tap = int(sys.argv[8]) if len(sys.argv) > 8 else 0          # STEER3: tap period (0 = DAS)
    unified = len(sys.argv) > 9 and sys.argv[9] == "unified"      # STEER4: shipping DRTAPP scheduler
    steer = (SM.Steer(proph="throat", pulse=True, tap_period=tap, tap_unified=unified) if tap
             else SM.Steer(proph="throat"))
    with open(out, "w") as fh:
        for i in range(cnt):
            r = V.play(lo + i * step, arm, lam, level=level, steer=steer)
            r["arm"] = arm + "~steer"; r["level"] = level
            if tap: r["tap"] = tap
            if unified: r["tap_unified"] = True
            fh.write(json.dumps(r) + "\n"); fh.flush()
