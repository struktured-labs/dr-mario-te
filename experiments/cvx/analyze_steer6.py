"""STEER6 screen analysis (PREREG_STEER6.md).

  python analyze_steer6.py
"""
import sys, os, json, glob
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from vs_race import evaluate

SEEDS = list(range(37934, 39133, 2))
ARMS = ("s6_dist_end60", "s6_rowsup_end180", "s6_dist_stall60", "s6_dist_target60", "s6_dist_hsv60")
B = 4000


def load(pattern, label):
    out = {}
    for f in glob.glob(pattern):
        for l in open(f):
            r = json.loads(l)
            if r.get("arm") == label:
                out[r["seed"]] = r
    return {s: out[s] for s in SEEDS if s in out}


def boot(d, seed=0):
    d = np.asarray(d, float); rng = np.random.default_rng(seed)
    m = d[rng.integers(0, len(d), size=(B, len(d)))].mean(1)
    return 100 * d.mean(), 100 * np.percentile(m, 2.5), 100 * np.percentile(m, 97.5)


def fmt(t):
    return f"{t[0]:+.2f} [{t[1]:+.2f}, {t[2]:+.2f}]"


def tap100(r):
    return int(r["topout"] and r["pills"] <= 100)


def stall_pills(r, n=10):
    return sum(b[2] for b in r["stuck"]["bep"] if b[0] == 1 and b[2] >= n)


def endgame_stall_death(r):
    if not r["topout"]:
        return 0
    return int(any(b[0] == 1 and b[5] == 5 and b[2] >= 20 and b[3] <= 4 for b in r["stuck"]["bep"]))


def main():
    GB = load("steer6/measure/*/gb_owner0804_*.jsonl", "s5b_hsv512@owner0804")      # == STEER5d rows (identity)
    RC = load("steer5d/*/rc_s5b_hsv512_*.jsonl", "s5b_hsv512~steer")
    print(f"BASELINE ANTIBODY: gate b n={len(GB)} tap<=100 {100*np.mean([tap100(r) for r in GB.values()]):.2f}%  "
          f"tap-out {100*np.mean([r['topout'] for r in GB.values()]):.2f}%   race n={len(RC)} win "
          f"{100*np.mean([evaluate(r, 177., .15, 2.65)[0] == 'win_race' for r in RC.values()]):.2f}%")
    for arm in ARMS:
        G = load(f"steer6/screen/*/gb_{arm}_*.jsonl", f"{arm}@owner0804")
        R = load(f"steer6/screen/*/rc_{arm}_*.jsonl", f"{arm}~steer")
        S = [s for s in SEEDS if s in G and s in GB]; SR = [s for s in SEEDS if s in R and s in RC]
        if not S:
            print(f"\n{arm}: no rows"); continue
        t100 = boot([tap100(G[s]) - tap100(GB[s]) for s in S])
        ttop = boot([G[s]["topout"] - GB[s]["topout"] for s in S])
        win = lambda r, dl=2.65: int(evaluate(r, 177., .15, dl)[0] == "win_race")
        trc = boot([win(R[s]) - win(RC[s]) for s in SR]) if SR else (np.nan,) * 3
        trc2 = boot([win(R[s], 2.0) - win(RC[s], 2.0) for s in SR]) if SR else (np.nan,) * 3
        c1 = (t100[2] < 0 and ttop[2] <= 1.0) or (ttop[2] < 0 and t100[2] <= 1.0)
        c3 = SR and trc[1] >= -2.0
        verdict = "PASS" if (c1 and c3 and len(S) == 600 and len(SR) == 600) else ("pending" if len(S) < 600 or len(SR) < 600 else "fail")
        print(f"\n{arm}: gate b n={len(S)}  race n={len(SR)}   -> {verdict}")
        print(f"  tap<=100 {100*np.mean([tap100(G[s]) for s in S]):5.2f}%  d {fmt(t100)}")
        print(f"  tap-out  {100*np.mean([G[s]['topout'] for s in S]):5.2f}%  d {fmt(ttop)}")
        if SR:
            print(f"  race win {100*np.mean([win(R[s]) for s in SR]):5.2f}%  d {fmt(trc)}   (delta 2.0: {fmt(trc2)})")
        fixed = sum(1 for s in S if GB[s]["topout"] and not G[s]["topout"])
        new = sum(1 for s in S if not GB[s]["topout"] and G[s]["topout"])
        print(f"  churn on tap-out: fixed {fixed} / new {new}  (base failures {sum(GB[s]['topout'] for s in S)})")
        sp = boot([stall_pills(G[s]) - stall_pills(GB[s]) for s in S])
        print(f"  MECHANISM: act-stall(>=10) pills/game base {np.mean([stall_pills(GB[s]) for s in S]):.1f} arm "
              f"{np.mean([stall_pills(G[s]) for s in S]):.1f}  d {sp[0]/100:+.1f} [{sp[1]/100:+.1f}, {sp[2]/100:+.1f}]")
        es = boot([endgame_stall_death(G[s]) - endgame_stall_death(GB[s]) for s in S])
        print(f"  endgame-stall deaths (terminal stall>=20 from <=4 viruses): base {100*np.mean([endgame_stall_death(GB[s]) for s in S]):.2f}% "
              f"arm {100*np.mean([endgame_stall_death(G[s]) for s in S]):.2f}%  d {fmt(es)}")
        pl = [G[s]["pills"] - GB[s]["pills"] for s in S if G[s]["won"] and GB[s]["won"]]
        print(f"  pills to clear (both won, n={len(pl)}): d mean {np.mean(pl):+.1f}")


if __name__ == "__main__":
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    main()
