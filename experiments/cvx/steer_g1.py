"""G1 (hardware replay) for steer_model: for every banked couch placement, simulate the couch driver
executing the sim brain's target on the recorded settled board and compare the predicted landing with
the silicon landing (experiments/couch_forensics/cases_all_games.jsonl, 467 placements, 7 games).

Inputs per placement: board S, pill colours, the sim brain's action, the observed first-action frame
(video first_lateral_f; if absent the model samples the empirical distribution), pill index k (speed).
The hardware brain's final answer is NOT always the sim's (LATE-FLIP / OTHER classes); the gate is
reported per forensic class. Usage: python steer_g1.py [--phase 0|1|sweep]
"""
import os, sys, json, collections
CVX = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, CVX)
import steer_model as SM

CASES = os.path.join(CVX, "..", "couch_forensics", "cases_all_games.jsonl")


def grid(s):
    return [[int(s[r * 8 + c]) for c in range(8)] for r in range(16)]


def actual_cells(act):
    o, c, cl, r = act
    return ((r, c), (r, c + 1)) if o == "H" else ((r, c), (r + 1, c))


def var_of(orient, cols, cur):
    a, b = cur
    if orient == "H":
        return 0 if tuple(cols) == (a, b) else 1
    return 2 if tuple(cols) == (a, b) else 3


def run(phase=None, use_obs_latency=True, verbose=False):
    C = [json.loads(l) for l in open(CASES)]
    tab = collections.defaultdict(lambda: [0, 0])
    detail = []
    for q in C:
        if not q.get("verified", True):
            continue
        color = grid(q["S"]["color"])
        a = q["sim_action"]
        st = SM.Steer(proph="throat", seed=1)
        t = q["video"]["first_lateral_f"] if use_obs_latency else None
        if SM.proph_throat(color) in ("L", "R") and t is not None:
            # armed spawn: the first observed move is the DRPROPH pulse, not the answer. The answer is the
            # first lateral step that breaks the 2-frame pulse cadence (gap > 3 f or a direction reversal);
            # if none, the pill locked before the answer mattered -> sample.
            steps = q["video"]["lateral_steps_f_col"]
            t = None
            for i in range(1, len(steps)):
                gap = steps[i][0] - steps[i - 1][0]
                rev = i >= 2 and (steps[i][1] - steps[i - 1][1]) * (steps[i - 1][1] - steps[i - 2][1]) < 0
                if gap > 3 or rev:
                    t = steps[i][0]; break
        res = st.execute(color, a, q["k"], t_act=t, phase=phase)
        pred = (res["var"], tuple(map(tuple, res["cells"])))
        act = q["actual"]
        avar = var_of(act[0], act[2], q["cur"])
        acells = actual_cells(act)
        ok = (pred[0] == avar and pred[1] == acells)
        cat = q["category"]
        if cat == "SHORT-LANDING":
            steps = q["video"]["lateral_steps_f_col"]
            rev = any((steps[i][1] - steps[i - 1][1]) * (q["sim"][1] - 3) < 0 for i in range(1, len(steps)))
            if avar != a // 8 or rev:
                cat = "SHORT-LANDING/brain-target-differs"      # the hardware aimed elsewhere (not steering)
            elif not ok and res["exact"]:
                cat = "SHORT-LANDING/hw-stopped-short-open"     # model reaches the target; silicon committed
            else:                                               # to an intermediate (anytime/slam-on-stability)
                cat = "SHORT-LANDING/mechanism"
        tab[cat][0] += int(ok); tab[cat][1] += 1
        tab["ALL"][0] += int(ok); tab["ALL"][1] += 1
        detail.append({"game": q["game"], "k": q["k"], "cat": cat, "ok": ok, "pred": [pred[0], pred[1]],
                       "act": [avar, acells], "sim": q["sim"], "proph": res["proph"], "armed": res["armed"],
                       "clamped": res["clamped"], "t_act": res["t_act"], "lock_f": res["lock_f"]})
    return tab, detail


if __name__ == "__main__":
    ph = sys.argv[sys.argv.index("--phase") + 1] if "--phase" in sys.argv else "0"
    phases = [0, 1] if ph == "sweep" else [int(ph)]
    for p in phases:
        tab, det = run(phase=p)
        print(f"phase {p}:  " + "  ".join(f"{k} {v[0]}/{v[1]}" for k, v in sorted(tab.items())))
    json.dump(det, open(os.path.join(CVX, "..", "..", "tmp", "steer_g1_detail.json"), "w"))
