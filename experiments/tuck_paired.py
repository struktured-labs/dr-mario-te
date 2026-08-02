#!/usr/bin/env python3
"""Paired re-analysis of the TUCK override on the REAL NES capsule stream.

The aggregate rig (tuck_ab.py) prints a POOLED endgame p/v -- sum(pills)/sum(viruses)
across all games. That statistic is dominated by the handful of disaster games: a topout
contributes ~300 pills and almost no endgame virus clears, so at n=120 with ~3% topout
roughly 4 games drive the headline. That is the likely reason endgame p/v flips sign
across levels on the NES stream (+0.18 / -0.52 / +0.69 / -0.52) while median pills
improves 5/5 in the same runs. Two metrics on the same data cannot both be honest.

This script keeps the seeds PAIRED (tuck_ab already runs range(seeds) for both arms) and
reports, on the NES stream only:

  1. paired pill delta on seeds where BOTH arms cleared (uncensored comparison), with a
     bootstrap CI -- nobody has ever put an interval on this number
  2. per-game mean p/v alongside the pooled ratio, to size the pooling artefact
  3. pooled p/v with topouts excluded, to test the disaster-game leverage directly
  4. regime composition: does tuck ON enter the endgame with a HARDER residual? If it
     converts faster in open/mid, endgame p/v inflates for a benign reason and the metric
     is confounded for any override that fires across all regimes (tuck: ~4.8/game),
     unlike the endgame-gated planner (2.2/game) where it was a clean read.

Usage: tuck_paired.py --seeds 360 --level 11 --workers 6
"""
import sys, json, argparse, random, statistics as st
from concurrent.futures import ProcessPoolExecutor, as_completed
ROOT = "/home/struktured/projects/dr_mario_rl"
sys.path.insert(0, ROOT + "/tmp/champion")
import tuck_ab as TA


def boot_ci(xs, stat=st.mean, n=10000, seed=12345):
    """Percentile bootstrap CI. Fixed seed so the interval is reproducible."""
    if not xs:
        return (float("nan"), float("nan"))
    rng = random.Random(seed)
    k = len(xs)
    reps = []
    for _ in range(n):
        reps.append(stat([xs[rng.randrange(k)] for _ in range(k)]))
    reps.sort()
    return reps[int(0.025 * n)], reps[int(0.975 * n)]


def pooled_pv(rows, k="end"):
    p = sum(r["seg"][k][0] for r in rows)
    v = sum(r["seg"][k][1] for r in rows)
    return p / v if v else float("nan")


def pergame_pv(rows, k="end"):
    """Per-game p/v, skipping games that cleared no virus in the regime (undefined)."""
    vals = [r["seg"][k][0] / r["seg"][k][1] for r in rows if r["seg"][k][1] > 0]
    return (st.mean(vals) if vals else float("nan")), vals


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--seeds", type=int, default=360)
    ap.add_argument("--level", type=int, default=11)
    ap.add_argument("--workers", type=int, default=6)
    ap.add_argument("--P", type=int, default=12)
    a = ap.parse_args()

    R = {}
    for tuck in (0, 1):
        rows = []
        with ProcessPoolExecutor(max_workers=a.workers, initializer=TA._init,
                                 initargs=(a.level, tuck, 1, a.P)) as ex:   # nes=1 always
            for f in as_completed([ex.submit(TA.play, s) for s in range(a.seeds)]):
                rows.append(f.result())
        R[tuck] = {r["seed"]: r for r in rows}
        print(f"  arm tuck={tuck} done ({len(rows)} games)", flush=True)

    off, on = R[0], R[1]
    seeds = sorted(set(off) & set(on))
    out = f"{ROOT}/tmp/champion/logs/tuck_paired_L{a.level}_n{a.seeds}.json"
    with open(out, "w") as fh:
        json.dump({"level": a.level, "seeds": a.seeds,
                   "off": [off[s] for s in seeds], "on": [on[s] for s in seeds]}, fh)

    print(f"\n=== TUCK on the REAL NES stream, PAIRED (L{a.level}, n={len(seeds)}) ===\n")

    # 1. paired pill delta, both-cleared only (avoids censoring at max_pills=300)
    both = [s for s in seeds if off[s]["won"] and on[s]["won"]]
    d = [on[s]["pills"] - off[s]["pills"] for s in both]
    lo, hi = boot_ci(d)
    better = sum(1 for x in d if x < 0)
    worse = sum(1 for x in d if x > 0)
    print(f"1. PAIRED PILLS (both arms cleared, n={len(both)} of {len(seeds)})")
    print(f"   mean delta {st.mean(d):+.2f} pills   95% CI [{lo:+.2f}, {hi:+.2f}]")
    print(f"   median delta {st.median(d):+.1f}   better {better} / worse {worse} / tie {len(d)-better-worse}")
    print(f"   => {'REAL (CI excludes 0)' if hi < 0 or lo > 0 else 'WASH (CI spans 0)'}\n")

    # 2. clear rate, paired
    c_off = sum(off[s]["won"] for s in seeds) / len(seeds)
    c_on = sum(on[s]["won"] for s in seeds) / len(seeds)
    disc = [(off[s]["won"], on[s]["won"]) for s in seeds if off[s]["won"] != on[s]["won"]]
    won_only_on = sum(1 for o, n in disc if n)
    print(f"2. CLEAR RATE  off {c_off:.1%} -> on {c_on:.1%}")
    print(f"   discordant pairs: {len(disc)}  (tuck-only wins {won_only_on}, tuck-only losses {len(disc)-won_only_on})\n")

    # 3. the pooling artefact
    print("3. ENDGAME p/v -- pooled vs per-game")
    for lbl, rows in (("off", [off[s] for s in seeds]), ("ON ", [on[s] for s in seeds])):
        pm, _ = pergame_pv(rows)
        nc = [r for r in rows if r["won"]]
        print(f"   {lbl}: pooled {pooled_pv(rows):5.2f}   per-game mean {pm:5.2f}   "
              f"pooled(cleared only) {pooled_pv(nc):5.2f}")
    pv_off = [off[s]["seg"]["end"][0] / off[s]["seg"]["end"][1] for s in both if off[s]["seg"]["end"][1] > 0]
    pv_on = [on[s]["seg"]["end"][0] / on[s]["seg"]["end"][1] for s in both if on[s]["seg"]["end"][1] > 0]
    k = min(len(pv_off), len(pv_on))
    dpv = [pv_on[i] - pv_off[i] for i in range(k)]
    lo2, hi2 = boot_ci(dpv)
    print(f"   paired per-game endgame p/v delta {st.mean(dpv):+.3f}  95% CI [{lo2:+.3f}, {hi2:+.3f}]")
    print(f"   => {'REAL' if hi2 < 0 or lo2 > 0 else 'WASH'}\n")

    # 4. composition: where does the work move?
    print("4. REGIME COMPOSITION (mean per game: pills / viruses cleared)")
    print(f"   {'regime':>7} {'pills off':>10} {'pills ON':>9} {'vir off':>8} {'vir ON':>7}")
    for k in ("open", "mid", "end"):
        po = st.mean([off[s]["seg"][k][0] for s in seeds])
        pn = st.mean([on[s]["seg"][k][0] for s in seeds])
        vo = st.mean([off[s]["seg"][k][1] for s in seeds])
        vn = st.mean([on[s]["seg"][k][1] for s in seeds])
        print(f"   {k:>7} {po:10.1f} {pn:9.1f} {vo:8.2f} {vn:7.2f}")
    print("\n   If tuck ON clears MORE viruses in open/mid, the endgame it reaches is a")
    print("   harder residual and its p/v inflates for a benign reason -- the metric is")
    print("   confounded for an all-regime override, and paired pills is the sound read.")
    print(f"\n   fires/game {st.mean([on[s]['fired'] for s in seeds]):.1f}")
    print(f"\nwrote {out}")


if __name__ == "__main__":
    main()
