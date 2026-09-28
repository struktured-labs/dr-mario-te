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


HO_GB = sorted(set(range(39134, 40933, 2)) | set(range(33000, 34199, 2)))
HO_RC = sorted(set(HO_GB) | set(range(26280, 26959, 2)) | set(range(60348, 60999, 2)))
HO_ARMS = ("s6_dist_end60", "s6_dist_stall60", "s6_dist_target60")
RTL_ORDER = ("s6_dist_target60", "s6_dist_end60", "s6_dist_stall60")        # cheapest first (PREREG_STEER6b)


def _load(pattern, label, seeds):
    out = {}
    for f in glob.glob(pattern):
        for l in open(f):
            r = json.loads(l)
            if r.get("arm") == label:
                out[r["seed"]] = r
    return {s: out[s] for s in seeds if s in out}


def boot_q(d, lo, hi, seed=0):
    d = np.asarray(d, float); rng = np.random.default_rng(seed)
    m = d[rng.integers(0, len(d), size=(B, len(d)))].mean(1)
    return 100 * d.mean(), 100 * np.percentile(m, lo), 100 * np.percentile(m, hi)


def holdout():
    """STEER6b (PREREG_STEER6b.md): Bonferroni 98.33% CIs; CONFIRMED iff tap-out upper < 0, race lower >= -2,
    tap<=100 upper <= +1."""
    GB = _load("steer5d/*/gb_s5b_hsv512_*.jsonl", "fw540_steer_s5b_hsv512", HO_GB)
    RC = _load("steer5d/*/rc_s5b_hsv512_*.jsonl", "s5b_hsv512~steer", HO_RC)
    win = lambda r, dl=2.65: int(evaluate(r, 177., .15, dl)[0] == "win_race")
    print(f"BASELINE ANTIBODY (STEER5d rows): gate b n={len(GB)} tap<=100 {100*np.mean([tap100(r) for r in GB.values()]):.2f}% "
          f"tap-out {100*np.mean([r['topout'] for r in GB.values()]):.2f}%   race n={len(RC)} win {100*np.mean([win(r) for r in RC.values()]):.2f}%")
    confirmed = {}
    for arm in HO_ARMS:
        G = _load(f"steer6/holdout/*/gb_{arm}_*.jsonl", f"{arm}@owner0804", HO_GB)
        R = _load(f"steer6/holdout/*/rc_{arm}_*.jsonl", f"{arm}~steer", HO_RC)
        S = [s for s in HO_GB if s in G and s in GB]; SR = [s for s in HO_RC if s in R and s in RC]
        if not S or not SR:
            print(f"\n{arm}: gate b n={len(S)} race n={len(SR)} (incomplete)"); continue
        dtop = [G[s]["topout"] - GB[s]["topout"] for s in S]
        d100 = [tap100(G[s]) - tap100(GB[s]) for s in S]
        drc = [win(R[s]) - win(RC[s]) for s in SR]
        tb, t1, tr = boot_q(dtop, 0.8333, 99.1667), boot_q(d100, 0.8333, 99.1667), boot_q(drc, 0.8333, 99.1667)
        t95, r95 = boot_q(dtop, 2.5, 97.5), boot_q(drc, 2.5, 97.5)
        complete = len(S) == len(HO_GB) and len(SR) == len(HO_RC)
        ok = tb[2] < 0 and tr[1] >= -2.0 and t1[2] <= 1.0
        v = ("CONFIRMED" if ok else "NOT CONFIRMED") if complete else "incomplete"
        if ok and complete:
            confirmed[arm] = tb[0]
        print(f"\n{arm}: gate b n={len(S)}  race n={len(SR)}   -> {v}")
        print(f"  tap-out  base {100*np.mean([GB[s]['topout'] for s in S]):.2f}%  arm {100*np.mean([G[s]['topout'] for s in S]):.2f}%  "
              f"d {fmt(tb)} (98.33%)   95%: {fmt(t95)}")
        print(f"  tap<=100 base {100*np.mean([tap100(GB[s]) for s in S]):.2f}%  arm {100*np.mean([tap100(G[s]) for s in S]):.2f}%  d {fmt(t1)} (98.33%)")
        print(f"  race win base {100*np.mean([win(RC[s]) for s in SR]):.2f}%  arm {100*np.mean([win(R[s]) for s in SR]):.2f}%  "
              f"d {fmt(tr)} (98.33%)   95%: {fmt(r95)}   delta 2.0 95%: {fmt(boot_q([win(R[s], 2.0) - win(RC[s], 2.0) for s in SR], 2.5, 97.5))}")
        fixed = sum(1 for s in S if GB[s]["topout"] and not G[s]["topout"]); new = sum(1 for s in S if not GB[s]["topout"] and G[s]["topout"])
        print(f"  churn fixed {fixed} / new {new} (base failures {sum(GB[s]['topout'] for s in S)})   "
              f"arm stall pills/game {np.mean([stall_pills(G[s]) for s in S]):.1f}  arm endgame-stall deaths {100*np.mean([endgame_stall_death(G[s]) for s in S]):.2f}%")
        # pooled with the screen (descriptive)
        GS = load(f"steer6/screen/*/gb_{arm}_*.jsonl", f"{arm}@owner0804"); BS = load("steer6/measure/*/gb_owner0804_*.jsonl", "s5b_hsv512@owner0804")
        P = [GS[s]["topout"] - BS[s]["topout"] for s in SEEDS if s in GS and s in BS] + dtop
        print(f"  POOLED screen+holdout tap-out (descriptive, n={len(P)}): {fmt(boot_q(P, 2.5, 97.5))}")
    if confirmed:
        best = min(confirmed.values())
        rec = next(a for a in RTL_ORDER if a in confirmed and confirmed[a] <= best + 1.5)
        print(f"\nRECOMMENDATION (pre-declared rule: cheapest RTL within 1.5 pp of the best confirmed): {rec}")
    else:
        print("\nno arm confirmed")


def dlat():
    """STEER6c (PREREG_STEER6c.md): arm @ +DLAT frames vs ANTIBODY @ nominal (95% CIs), + the latency cost arm@D - arm@0."""
    GB = load("steer6/measure/*/gb_owner0804_*.jsonl", "s5b_hsv512@owner0804")
    RC = load("steer5d/*/rc_s5b_hsv512_*.jsonl", "s5b_hsv512~steer")
    win = lambda r: int(evaluate(r, 177., .15, 2.65)[0] == "win_race")
    frac = "--dfrac" in sys.argv
    runs = ((("s6_dist_target60", "0.17"), ("s6_dist_end60", "1.25")) if frac else
            (("s6_dist_target60", 1), ("s6_dist_end60", 2), ("s6_dist_stall60", 18)))
    for arm, d in runs:
        if frac:
            G = load(f"steer6/dfrac/gb_{arm}_f{d}_*.jsonl", f"{arm}@owner0804"); R = load(f"steer6/dfrac/rc_{arm}_f{d}_*.jsonl", f"{arm}~steer")
        else:
            G = load(f"steer6/dlat/*/gb_{arm}_d{d}_*.jsonl", f"{arm}@owner0804"); R = load(f"steer6/dlat/*/rc_{arm}_d{d}_*.jsonl", f"{arm}~steer")
        G0 = load(f"steer6/screen/*/gb_{arm}_*.jsonl", f"{arm}@owner0804"); R0 = load(f"steer6/screen/*/rc_{arm}_*.jsonl", f"{arm}~steer")
        S = [s for s in SEEDS if s in G and s in GB and s in G0]; SR = [s for s in SEEDS if s in R and s in RC and s in R0]
        if not S or not SR:
            print(f"\n{arm} @ +{d} f: gate b n={len(S)} race n={len(SR)} (no/partial rows)"); continue
        ttop = boot([G[s]["topout"] - GB[s]["topout"] for s in S]); t100 = boot([tap100(G[s]) - tap100(GB[s]) for s in S])
        trc = boot([win(R[s]) - win(RC[s]) for s in SR])
        ok = ttop[2] < 0 and trc[1] >= -2.0 and t100[2] <= 1.0
        full = len(S) == 600 and len(SR) == 600
        if frac:
            act = [G[s].get("lat_active", 0) for s in S]; ext = [G[s].get("lat_extra_f", 0) for s in S]
            print(f"\n[POST-HOC fractional, active decisions only] gate b: active decisions/game {np.mean(act):.1f}, extra frames/game {np.mean(ext):.2f}")
        print(f"\n{arm} @ +{d} f (vs ANTIBODY @ nominal): gate b n={len(S)} race n={len(SR)} -> "
              + (("GAIN SURVIVES" if ok else "GAIN DOES NOT SURVIVE") if full else "incomplete"))
        print(f"  tap-out  {100*np.mean([G[s]['topout'] for s in S]):5.2f}%  d {fmt(ttop)}    tap<=100 d {fmt(t100)}")
        print(f"  race win {100*np.mean([win(R[s]) for s in SR]):5.2f}%  d {fmt(trc)}")
        print(f"  LATENCY COST (arm@+{d} - arm@0): tap-out {fmt(boot([G[s]['topout'] - G0[s]['topout'] for s in S]))}  "
              f"race {fmt(boot([win(R[s]) - win(R0[s]) for s in SR]))}")


if __name__ == "__main__":
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    if "--dlat" in sys.argv or "--dfrac" in sys.argv:
        dlat(); sys.exit(0)
    if "--holdout" in sys.argv:
        holdout()
    else:
        main()
