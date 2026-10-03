"""STEER6e screen analysis (PREREG_STEER6e.md).

  python analyze_steer6e.py
"""
import sys, os, json, glob
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from vs_race import evaluate
from analyze_steer6 import tap100, stall_pills, endgame_stall_death

SEEDS = list(range(37934, 39133, 2))
ARMS = ("s6e_chain0", "s6e_fin")
BASE = "s6_dist_target60"
B = 4000


def load(pattern, label):
    out = {}
    for f in glob.glob(pattern):
        for l in open(f):
            r = json.loads(l)
            if r.get("arm") == label:
                out[r["seed"]] = r
    return {s: out[s] for s in SEEDS if s in out}


def boot(d, seed=0, scale=1.0):
    d = np.asarray(d, float)
    if len(d) == 0:
        return (np.nan,) * 3
    rng = np.random.default_rng(seed)
    m = d[rng.integers(0, len(d), size=(B, len(d)))].mean(1)
    return scale * d.mean(), scale * np.percentile(m, 2.5), scale * np.percentile(m, 97.5)


def fmt(t, p=2):
    return f"{t[0]:+.{p}f} [{t[1]:+.{p}f}, {t[2]:+.{p}f}]"


def eg_stall(r):
    """pills in board-level act-stalls >= 10 that START at <= 4 viruses"""
    return sum(b[2] for b in r["stuck"]["bep"] if b[0] == 1 and b[2] >= 10 and 0 <= b[3] <= 4)


def win(r, dl=2.65):
    return int(evaluate(r, 177., .15, dl)[0] == "win_race")


def exactness():
    bad = 0; n = 0
    for kind, lab in (("gb", f"{BASE}@owner0804"), ("rc", f"{BASE}~steer")):
        banked = load(f"steer6/screen/*/{kind}_{BASE}_*.jsonl", lab)
        mine = load(f"steer6e/screen/{kind}_{BASE}_*.jsonl", lab)
        for s, r in mine.items():
            n += 1
            b = banked[s]
            rr = {k: v for k, v in r.items() if k != "eg"}
            if rr != b:
                bad += 1
                print(f"  EXACTNESS MISMATCH {kind} seed {s}: {[k for k in rr if rr.get(k) != b.get(k)]}")
    print(f"EXACTNESS identity arm vs banked STEER6 screen rows: {n - bad}/{n} identical")
    return bad == 0


def main():
    ok = exactness()
    G0 = load(f"steer6e/screen/gb_{BASE}_*.jsonl", f"{BASE}@owner0804")
    R0 = load(f"steer6e/screen/rc_{BASE}_*.jsonl", f"{BASE}~steer")
    print(f"BASELINE {BASE}: gate b n={len(G0)} tap-out {100*np.mean([r['topout'] for r in G0.values()]):.2f}%  "
          f"race n={len(R0)} win {100*np.mean([win(r) for r in R0.values()]):.2f}%")
    fa = sum(r['eg']['fin_avail'] for r in G0.values()); ft = sum(r['eg']['fin_taken'] for r in G0.values())
    print(f"  baseline brain finishing take rate (gb, <=4 viruses): {ft}/{fa} = {100*ft/max(1,fa):.1f}%")
    for arm in ARMS:
        G = load(f"steer6e/screen/gb_{arm}_*.jsonl", f"{arm}@owner0804")
        R = load(f"steer6e/screen/rc_{arm}_*.jsonl", f"{arm}~steer")
        S = [s for s in SEEDS if s in G and s in G0]; SR = [s for s in SEEDS if s in R and s in R0]
        if not S:
            print(f"\n{arm}: no rows"); continue
        bw = [s for s in S if G[s]["won"] and G0[s]["won"] and G[s]["eg"]["k4"] is not None and G0[s]["eg"]["k4"] is not None]
        e1 = boot([(G[s]["pills"] - G[s]["eg"]["k4"]) - (G0[s]["pills"] - G0[s]["eg"]["k4"]) for s in bw])
        e1s = boot([(G[s]["elapsed_s"] - G[s]["eg"]["t4"]) - (G0[s]["elapsed_s"] - G0[s]["eg"]["t4"]) for s in bw])
        bw1 = [s for s in bw if G[s]["eg"]["k1"] is not None and G0[s]["eg"]["k1"] is not None]
        lv = boot([(G[s]["pills"] - G[s]["eg"]["k1"]) - (G0[s]["pills"] - G0[s]["eg"]["k1"]) for s in bw1])
        e3 = boot([G[s]["topout"] - G0[s]["topout"] for s in S], scale=100)
        t100 = boot([tap100(G[s]) - tap100(G0[s]) for s in S], scale=100)
        e2 = boot([win(R[s]) - win(R0[s]) for s in SR], scale=100) if SR else (np.nan,) * 3
        e2b = boot([win(R[s], 2.0) - win(R0[s], 2.0) for s in SR], scale=100) if SR else (np.nan,) * 3
        c1 = e1[2] < 0; c2 = SR and e2[1] >= -2.0; c3 = e3[2] <= 2.0
        full = len(S) == 600 and len(SR) == 600
        verdict = ("PASS" if (c1 and c2 and c3) else "fail") if (full and ok) else ("pending" if not full else "VOID (exactness)")
        print(f"\n{arm}: gate b n={len(S)}  race n={len(SR)}   -> {verdict}   [E1 {c1} E2 {bool(c2)} E3 {c3}]")
        print(f"  E1 endgame pills (k4 -> clear, both won n={len(bw)}): base mean "
              f"{np.mean([G0[s]['pills'] - G0[s]['eg']['k4'] for s in bw]):.1f}  d {fmt(e1)}   (sim s: {fmt(e1s, 1)})")
        print(f"     last-virus pills (k1 -> clear, both won n={len(bw1)}): base mean "
              f"{np.mean([G0[s]['pills'] - G0[s]['eg']['k1'] for s in bw1]):.1f}  d {fmt(lv)}")
        print(f"  E2 race win {100*np.mean([win(R[s]) for s in SR]):5.2f}%  d {fmt(e2)}   (delta 2.0: {fmt(e2b)})")
        print(f"  E3 tap-out  {100*np.mean([G[s]['topout'] for s in S]):5.2f}%  d {fmt(e3)}   tap<=100 d {fmt(t100)}")
        fixed = sum(1 for s in S if G0[s]["topout"] and not G[s]["topout"])
        new = sum(1 for s in S if not G0[s]["topout"] and G[s]["topout"])
        print(f"  churn on tap-out: fixed {fixed} / new {new}  (base failures {sum(G0[s]['topout'] for s in S)})")
        es = boot([eg_stall(G[s]) - eg_stall(G0[s]) for s in S])
        print(f"  endgame stall-pills/game (act-stall>=10 starting at <=4 viruses): base {np.mean([eg_stall(G0[s]) for s in S]):.1f} "
              f"arm {np.mean([eg_stall(G[s]) for s in S]):.1f}  d {fmt(es, 1)}")
        sp = boot([stall_pills(G[s]) - stall_pills(G0[s]) for s in S])
        print(f"  all act-stall(>=10) pills/game: d {fmt(sp, 1)};  endgame-stall deaths d "
              f"{fmt(boot([endgame_stall_death(G[s]) - endgame_stall_death(G0[s]) for s in S], scale=100))}")
        if SR:
            bwr = [s for s in SR if R[s]["how"] == "clear" and R0[s]["how"] == "clear" and R[s]["eg"]["t4"] is not None
                   and R0[s]["eg"]["t4"] is not None]
            rs = boot([(R[s]["t_end"] - R[s]["eg"]["t4"]) - (R0[s]["t_end"] - R0[s]["eg"]["t4"]) for s in bwr])
            ts = boot([R[s]["tiles_sent"] - R0[s]["tiles_sent"] for s in SR])
            print(f"  race endgame seconds (t4 -> clear, both cleared n={len(bwr)}): d {fmt(rs, 1)};  tiles sent/game d {fmt(ts, 2)}")
        fa = sum(G[s]['eg']['fin_avail'] for s in S); ft = sum(G[s]['eg']['fin_taken'] for s in S)
        da = sum(G[s]['eg']['dred_avail'] for s in S); dt = sum(G[s]['eg']['dred_taken'] for s in S)
        print(f"  brain finishing take rate (gb): {ft}/{fa} = {100*ft/max(1,fa):.1f}%;  D-reducing take rate {dt}/{da} = {100*dt/max(1,da):.1f}%")


if __name__ == "__main__":
    main()
