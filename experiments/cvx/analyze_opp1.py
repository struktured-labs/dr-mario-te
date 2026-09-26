"""OPP1 analysis (PREREG_OPP1.md). Build x opponent table on seeds 37934-39132 (600 paired).

  python analyze_opp1.py            # prints the tables + pre-declared readings
"""
import sys, os, json, glob
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from vs_race import evaluate

SEEDS = list(range(37934, 39133, 2))
BUILDS = ("s4_base", "s5b_hsv512")
BNAME = {"s4_base": "base", "s5b_hsv512": "hsv"}
OPPS = ("owner0804", "owner202609", "striker5", "striker6", "striker8")
MS, DELTAS = (140.0, 160.0, 177.0), (2.65, 2.0)
B = 4000


def load(pattern, label=None):
    out = {}
    for f in glob.glob(pattern):
        for l in open(f):
            r = json.loads(l)
            if label and r.get("arm") != label:
                continue
            out[r["seed"]] = r
    return {s: out[s] for s in SEEDS if s in out}


def gb(build, opp):
    if opp == "owner0804":                                   # banked STEER5d rows = the common blind baseline
        return load(f"steer5d/*/gb_{build}_*.jsonl", f"fw540_steer_{build}")
    return load(f"opp1/*/gb_{build}_{opp}_*.jsonl", f"{build}@{opp}")


def boot(d, seed=0):
    d = np.asarray(d, float)
    rng = np.random.default_rng(seed)
    idx = rng.integers(0, len(d), size=(B, len(d)))
    m = d[idx].mean(1)
    return 100 * d.mean(), 100 * np.percentile(m, 2.5), 100 * np.percentile(m, 97.5)


def ep(rows, s):
    r = rows[s]
    return {"tap": r["topout"], "tap100": int(r["topout"] and r["pills"] <= 100), "clear": r["won"]}


def fmt(t):
    return f"{t[0]:+.2f} [{t[1]:+.2f}, {t[2]:+.2f}]"


def main():
    G = {(b, o): gb(b, o) for b in BUILDS for o in OPPS}
    print("GATE (b) cells (n, tap-out, tap<=100, clear, garbage cells/eligible pill):")
    for b in BUILDS:
        for o in OPPS:
            R = G[(b, o)]
            if not R:
                print(f"  {BNAME[b]:4s} {o:12s} n=0"); continue
            n = len(R); v = list(R.values())
            gp = sum(r["garbage"] for r in v) / max(1, sum(max(0, r["pills"] - 25) for r in v))
            extra = ""
            if o.startswith("striker"):
                rel = sum(r["opp"]["releases"] for r in v); h = sum(r["opp"]["height"] for r in v)
                und = sum(r["opp"]["banked_undelivered"] for r in v); ear = sum(r["opp"]["earned"] for r in v)
                extra = f"  releases/game {rel/n:.1f} height-triggered {100*h/max(1,rel):.0f}%  undelivered {100*und/max(1,ear):.1f}% of earned"
            if o == "owner202609":
                extra = f"  volleys/game {sum(r['opp']['volleys'] for r in v)/n:.1f}"
            print(f"  {BNAME[b]:4s} {o:12s} n={n:3d}  tap {100*np.mean([r['topout'] for r in v]):5.1f}%  "
                  f"tap<=100 {100*np.mean([r['topout'] and r['pills'] <= 100 for r in v]):4.1f}%  "
                  f"clear {100*np.mean([r['won'] for r in v]):5.1f}%  garb/pill {gp:.3f}{extra}")

    print("\nA. OPPONENT EFFECT vs the COMMON BLIND BASELINE (OWNER-0804), per build, paired:")
    flags = []
    for b in BUILDS:
        base = G[(b, "owner0804")]
        for o in OPPS[1:]:
            R = G[(b, o)]; S = [s for s in SEEDS if s in R and s in base]
            if not S: continue
            out = [f"  {BNAME[b]:4s} {o:12s} n={len(S)}"]
            for e in ("tap", "tap100", "clear"):
                d = [ep(R, s)[e] - ep(base, s)[e] for s in S]; t = boot(d)
                out.append(f"{e} {fmt(t)}")
                if e == "tap" and t[0] >= 10 and t[1] > 0:
                    flags.append(f"COLLAPSE {BNAME[b]} vs {o}: tap-out {fmt(t)}")
                if e == "tap100":
                    p0 = np.mean([ep(base, s)[e] for s in S]); p1 = np.mean([ep(R, s)[e] for s in S])
                    if t[0] >= 3 and t[1] > 0 and p1 >= 2 * p0:
                        flags.append(f"COLLAPSE {BNAME[b]} vs {o}: tap<=100 {fmt(t)} ({100*p0:.1f}->{100*p1:.1f}%)")
            print("  ".join(out))

    print("\nB. hsv - base PER OPPONENT, paired:")
    for o in OPPS:
        H, Bs = G[("s5b_hsv512", o)], G[("s4_base", o)]; S = [s for s in SEEDS if s in H and s in Bs]
        if not S: continue
        out = [f"  {o:12s} n={len(S)}"]
        for e in ("tap", "tap100", "clear"):
            t = boot([ep(H, s)[e] - ep(Bs, s)[e] for s in S]); out.append(f"{e} {fmt(t)}")
            if e in ("tap", "tap100") and t[1] > 0:
                flags.append(f"hsv FLIPS vs {o}: {e} {fmt(t)}")
        print("  ".join(out))

    print("\nC. LULU (the RACER): vs_race lam 2, win rate by pace median M and damage delta:")
    RC = {b: load(f"opp1/*/rc_{b}_*.jsonl", f"{b}~steer") for b in BUILDS}
    R6 = {b: load(f"steer5d/*/rc_{b}_*.jsonl", f"{b}~steer") for b in BUILDS}
    S = [s for s in SEEDS if all(s in RC[b] for b in BUILDS)]
    print(f"  n={len(S)} paired;  race-row tap-out: " + "  ".join(
        f"{BNAME[b]} {100*np.mean([RC[b][s]['how'] == 'topout' for s in S]):.1f}%" for b in BUILDS)
        + "  clear: " + "  ".join(f"{BNAME[b]} {100*np.mean([RC[b][s]['how'] == 'clear' for s in S]):.1f}%" for b in BUILDS))
    if S:
        t = boot([(RC['s5b_hsv512'][s]['how'] == 'topout') - (RC['s4_base'][s]['how'] == 'topout') for s in S])
        print(f"  race-row tap-out hsv-base {fmt(t)}")
    for dl in DELTAS:
        for M in MS:
            w = {b: [int(evaluate(RC[b][s], M, 0.15, dl)[0] == "win_race") for s in S] for b in BUILDS}
            t = boot(np.array(w["s5b_hsv512"]) - np.array(w["s4_base"]))
            print(f"  delta {dl:4.2f} M {M:5.0f}s  base {100*np.mean(w['s4_base']):5.1f}%  hsv {100*np.mean(w['s5b_hsv512']):5.1f}%  hsv-base {fmt(t)}")
            if t[2] < 0:
                flags.append(f"hsv FLIPS vs LULU at M{M:.0f} delta{dl}: {fmt(t)}")
    if S:                                                    # descriptive: where does the racer start winning?
        for b in BUILDS:
            cross = None
            for M in range(60, 178, 5):
                w = np.mean([evaluate(RC[b][s], float(M), 0.15, 2.65)[0] == "win_race" for s in S])
                if w >= 0.5 and cross is None:
                    cross = (M, w)
            curve = "  ".join(f"M{M}:{100*np.mean([evaluate(RC[b][s], float(M), 0.15, 2.65)[0] == 'win_race' for s in S]):.0f}%"
                              for M in (80, 100, 120, 140, 160, 177))
            print(f"  [descriptive M sweep, delta 2.65] {BNAME[b]}: {curve}  -> bot win >= 50% from M = {cross[0] if cross else '>177'} s")
    S6 = [s for s in SEEDS if all(s in R6[b] for b in BUILDS)]
    if S6:
        print(f"  reference (banked STEER5d lam 6, same seeds n={len(S6)}): " + "  ".join(
            f"M{M:.0f} base {100*np.mean([evaluate(R6['s4_base'][s], M, 0.15, 2.65)[0] == 'win_race' for s in S6]):.1f}% "
            f"hsv {100*np.mean([evaluate(R6['s5b_hsv512'][s], M, 0.15, 2.65)[0] == 'win_race' for s in S6]):.1f}%" for M in MS))

    print("\nPRE-DECLARED FLAGS:")
    for f in flags or ["none (no collapse, no hsv flip)"]:
        print("  " + f)


if __name__ == "__main__":
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    main()
