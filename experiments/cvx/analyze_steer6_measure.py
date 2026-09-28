"""STEER6 phase 2 analysis (MEASURE_STEER6.md): stuck-virus episodes and board stalls on ANTIBODY in sim.

  python analyze_steer6_measure.py
"""
import sys, os, json, glob
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from vs_race import evaluate

SEEDS = set(range(37934, 39133, 2))
KINDS = ("str", "act", "mask")
ENDS = ("cleared_own", "cleared_garbage", "unlocked_own", "unlocked_garbage", "unlocked_pill", "end")
CONDS = (("gb-0804", "gb_owner0804_*"), ("gb-09", "gb_owner202609_*"), ("gb-lulu", "gb_lulu202609_*"), ("race-4.7", "rc47_*"))


def load(pat):
    out = {}
    for f in glob.glob(f"steer6/measure/*/{pat}.jsonl"):
        for l in open(f):
            r = json.loads(l)
            if r["seed"] in SEEDS:
                out[r["seed"]] = r
    return [out[s] for s in sorted(out)]


def stalls(r, kind, n):
    ki = KINDS.index(kind)
    return [b for b in r["stuck"]["bep"] if b[0] == ki and b[2] >= n]


def outcome(r, race):
    if not race:
        return "topout" if r["topout"] else ("clear" if r["won"] else "stall")
    return evaluate(r, 140.0, 0.15, 2.65)[0]


def pct(x):
    return f"{100*x:5.1f}%"


def main():
    for name, pat in CONDS:
        R = load(pat); race = name.startswith("race")
        if not R:
            print(name, "no rows"); continue
        n = len(R)
        print(f"\n=== {name}  n={n}  " + ("tap-out " + pct(np.mean([r['how'] == 'topout' for r in R])) + "  race win@M140 " +
              pct(np.mean([outcome(r, True) == 'win_race' for r in R])) if race else
              "tap-out " + pct(np.mean([r['topout'] for r in R])) + "  clear " + pct(np.mean([r['won'] for r in R]))))
        for kind in KINDS:
            for N in (10, 20):
                S = [stalls(r, kind, N) for r in R]
                has = np.mean([len(s) > 0 for s in S])
                per = np.mean([len(s) for s in S])
                L = [b[2] for s in S for b in s]
                frac = sum(r["stuck"]["in_stall"][kind][str(N)] for r in R) / max(1, sum(r["stuck"]["ndec"] for r in R))
                ends = np.bincount([b[5] for s in S for b in s], minlength=6)
                v0 = [b[3] for s in S for b in s]
                print(f"  BOARD stall {kind:4s} N>={N:2d}: games with one {pct(has)}  per game {per:4.2f}  "
                      f"len p50/p90/max {np.percentile(L,50) if L else 0:.0f}/{np.percentile(L,90) if L else 0:.0f}/{max(L) if L else 0}  "
                      f"decisions in stall {pct(frac)}  vleft@start p50 {np.median(v0) if v0 else 0:.0f}  "
                      f"ends " + " ".join(f"{ENDS[i]}={ends[i]}" for i in range(6) if ends[i]))
        # outcomes vs stalls (act, N>=20 and N>=10)
        for kind, N in (("act", 10), ("act", 20), ("str", 20)):
            groups = {}
            for r in R:
                o = outcome(r, race)
                g = groups.setdefault(o, [0, 0, 0])
                g[0] += 1; s = stalls(r, kind, N)
                g[1] += int(len(s) > 0)
                g[2] += int(r["stuck"]["open_stall_at_end"][kind] >= N)
            print(f"  outcome x {kind} stall>={N}: " + "  ".join(
                f"{o} n={g[0]} contain {pct(g[1]/g[0])} in-stall-at-end {pct(g[2]/g[0])}" for o, g in sorted(groups.items())))
        # tempo cost in wins
        won = [r for r in R if outcome(r, race) in ("clear", "win_race")]
        if won:
            dec = [sum(b[2] for b in stalls(r, "act", 10)) for r in won]
            sec = [sum(b[7] for b in stalls(r, "act", 10)) for r in won]
            tot = [r["pills"] for r in won]
            print(f"  WINS: pills in act stalls>=10 mean {np.mean(dec):.1f} of {np.mean(tot):.0f} pills ({pct(np.sum(dec)/np.sum(tot))}); "
                  f"seconds mean {np.mean(sec):.1f}")
        # endgame lingering virus episodes (virus-level, vleft0 <= 4)
        for kind in ("str", "act"):
            ki = KINDS.index(kind)
            E = [e for r in R for e in r["stuck"]["vep"] if e[0] == ki and e[6] <= 4]
            if E:
                ends = np.bincount([e[8] for e in E], minlength=6)
                L = [e[5] for e in E]
                print(f"  endgame lingering virus ({kind}, vleft0<=4): {len(E)/n:.2f}/game  len p50/p90 {np.percentile(L,50):.0f}/{np.percentile(L,90):.0f}  "
                      f"ends " + " ".join(f"{ENDS[i]}={ends[i]}" for i in range(6) if ends[i]))


if __name__ == "__main__":
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    main()
