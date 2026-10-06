"""STEER12 miss-dose calibration readout: PILLS ONLY (paired overhead vs ex_perfect on seeds where both cleared).
No race outcome / win rate is computed or printed (the race endpoints are not looked at before the prereg)."""
import json, os, numpy as np
os.chdir(os.path.dirname(os.path.abspath(__file__)))
L = {}
for a in ("ex_perfect", "q00", "ex_q01", "ex_q02", "ex_q03", "ex_q04", "ex_q06", "ex_q08"):
    L[a] = {r["seed"]: r for r in map(json.loads, open(f"steer12/qcal/lulu12_{a}.jsonl"))}
P = L["ex_perfect"]
out = []
for a, D in L.items():
    both = [s for s in D if s in P and D[s]["how"] == "clear" and P[s]["how"] == "clear"]
    ov = [D[s]["pills"] - P[s]["pills"] for s in both]
    mr = sum(D[s]["knob"]["miss"] for s in D) / max(sum(D[s]["knob"]["dec"] for s in D), 1)
    rng = np.random.default_rng(3); bs = [np.mean(rng.choice(ov, len(ov))) for _ in range(2000)] if ov else [0]
    out.append(f"{a:10s} n {len(D)} both-clear {len(both)}: overhead {np.mean(ov) if ov else 0:+6.2f} pills "
               f"[{np.percentile(bs, 2.5):+.2f}, {np.percentile(bs, 97.5):+.2f}], realised miss rate {100 * mr:.2f}%")
print("\n".join(out)); open("steer12/qcal/overhead.txt", "w").write("\n".join(out) + "\n")
