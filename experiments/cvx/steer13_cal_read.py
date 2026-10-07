"""STEER13 q_B calibration readout: PILLS / EXECUTION ONLY (no race outcome is computed or printed).
overhead = mean(pills - ex_perfect pills) over the seeds where both cleared (ex_perfect = banked STEER12 main rows,
same seeds). RULE (declared before the run, PREREG_STEER13 sec. 3): q_B = the q at which the anytime-1488 arm's overhead
equals A_fair_q04's (linear interpolation over q 0/2/3/4 %), rounded to 0.5 %."""
import json, glob, os, numpy as np
os.chdir(os.path.dirname(os.path.abspath(__file__)))
CAL = [39134 + 2 * i for i in range(400)]


def load(pat, lab):
    d = {}
    for f in glob.glob(pat):
        for l in open(f):
            r = json.loads(l)
            if r.get("arm") == lab:
                d[r["seed"]] = r
    return d


P = load("steer12/main/lulu12_ex_perfect_*.jsonl", "ex_perfect~steer")
out = []
ov = {}
for a in ("A_fair_q04", "B_14886_q00", "B_14886_q02", "B_14886_q03", "B_14886_q04"):
    D = load(f"steer13/cal/lulu13_{a}_*.jsonl", f"{a}~steer")
    S = [s for s in CAL if s in D and s in P and D[s]["how"] == "clear" and P[s]["how"] == "clear"]
    o = np.array([D[s]["pills"] - P[s]["pills"] for s in S])
    rng = np.random.default_rng(3); bs = [o[rng.integers(0, len(o), len(o))].mean() for _ in range(2000)]
    k = {kk: sum(D[s]["knob"][kk] for s in D) for kk in D[CAL[0]]["knob"]}
    dec = max(k["dec"], 1)
    ov[a] = o.mean()
    out.append(f"{a:12s} n {len(D)} both-clear {len(S)}: overhead {o.mean():+6.2f} pills [{np.percentile(bs, 2.5):+.2f}, "
               f"{np.percentile(bs, 97.5):+.2f}]; landed on the brain's final {100 * k['landed_final'] / dec:.1f}% of pills; "
               f"misses {100 * k['miss'] / dec:.2f}%" + (f"; non-final commits {100 * k['nonfinal_commit'] / dec:.1f}%, "
               f"late publishes {k['late'] / dec:.3f}/pill, adopted {k['adopt'] / dec:.3f}, refused {k['refuse'] / dec:.3f}, "
               f"tempo {k['tempo_f'] / dec:+.2f} f/pill" if a.startswith("B") else ""))
qs = np.array([0.0, 2.0, 3.0, 4.0]); ys = np.array([ov[f"B_14886_q{int(q):02d}"] for q in qs])
target = ov["A_fair_q04"]
o = np.argsort(ys)
qb = float(np.interp(target, ys[o], qs[o]))
qb_r = round(qb * 2) / 2
out.append(f"target overhead (A_fair_q04) {target:+.2f}; anytime-1488 overhead by q {dict(zip(qs.tolist(), np.round(ys, 2).tolist()))} "
           f"-> q_B = {qb:.2f}% -> rounded {qb_r:.1f}%")
out.append(f"couch reference: 10/05 AI pills landing on the brain's choice = 1025/1256 = 81.6%")
print("\n".join(out)); open("steer13/cal/qb.txt", "w").write("\n".join(out) + "\n" + json.dumps({"QB": qb_r / 100}) + "\n")
