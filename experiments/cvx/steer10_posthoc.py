"""STEER10 POST-HOC (declared in RESULT_STEER10.md as post-hoc, not the bar): LULU race losses by TYPE per arm
(slow = AI alive but slower; kill = AI topped out first), fixed / new per type, at each M of the prior."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import analyze_steer10 as A
from vs_race import evaluate
base = A.fair_rows()[0]
for arm in A.PREREG_ARMS:
    X = A.arm_rows(arm)[0]
    S = [s for s in A.LULU10B if s in X and s in base]
    print(f"== {arm} (n={len(S)})")
    for M in A.MS:
        c = {"slow": [0, 0, 0, 0], "kill": [0, 0, 0, 0]}          # base losses, arm losses, fixed, new
        for s in S:
            b = evaluate(base[s], M, .15, A.DELTA)[0]; x = evaluate(X[s], M, .15, A.DELTA)[0]
            for kind, lab in (("slow", "loss_race"), ("kill", "loss_kill")):
                c[kind][0] += b == lab; c[kind][1] += x == lab
                c[kind][2] += b == lab and x == "win_race"; c[kind][3] += b == "win_race" and x == lab
        print(f"  M{int(M)}: " + "  ".join(f"{k}: base {v[0]} -> {v[1]} (fixed {v[2]} / new {v[3]})" for k, v in c.items()))
