#!/usr/bin/env python3
"""margin_reader.py -- ⛔ NOT AN ENDPOINT. Duration is EXCLUDED by the prereg.

*** DO NOT REGISTER OR REPORT THIS AS AN ENDPOINT (ruled 2026-08-23). ***
The original prereg excludes tempo/duration/latency endpoints deliberately: DRP1SLICE
has known tempo PHASE DIALS, so a difference in seconds-to-death can be the dial moving
rather than P1 surviving longer. Estimating it precisely does not fix that -- a
perfectly estimated confounded quantity is still confounded.

The tempo-invariant replacement (pills-to-top-out) does not rescue it either: every
WITHIN-MATCH quantity resets at the match boundary and so must be read AT the ending,
which is 12.5% capture. The only ~100%-capture quantities are the ones L9532_TOP_5
writes before it changes the mode -- $031E/$039E and $0309/$0389 (see e1_winner.py).
There is therefore NO secondary endpoint; the binary winner ships alone.

Kept for DIAGNOSTICS only (match pacing, harness health, sanity-checking the ring), and
because the clustering/quantisation figures below are cited in the lane's record.

Original docstring follows.

per-match TIME-TO-TOP-OUT.

Measurand (state it this way in the prereg, so the quantisation is part of the
DEFINITION rather than an unstated error term):

    the number of elapsed SAMPLE PERIODS between consecutive match-end records in
    the cart's DRPROBE ring ($6200), times the sample period.

Capture is 100%: the ring is append-only and records every match end whether or
not the sampler landed on it.  Contrast "virus count AT death", which needs the
sampler to land inside the ~2.5 s end window and is only 12.5% readable on
population A -- do not register that form.

MEASURED, POOLED / ARM-BLIND, population A (255 rows):
    989 endings = 254 first-in-cycle (excluded: a cycle starts at F1-restore, not
    at a match boundary -- structural, not length-related)
                + 734 measurable
                +   2 inside a multi-match gap (0.2%; excluding these censors the
                    SHORT tail, so it is a length bias -- but worst case it moves
                    the mean 83.1 -> 82.9 s)
    median 81 s, mean 83.1 s, sd 24.3 s (p10 61 s, p90 122 s)

*** TWO ANALYSIS REQUIREMENTS ***
1. CLUSTERING IS MATERIAL, unlike the primary. ICC ~0.316, design effect 1.60,
   effective n 458 of 734. Analyse at the CYCLE level or deff-adjust. The binary
   primary has a variance-inflation factor of 0.93 and needs NO discount -- do not
   apply one rule to both endpoints.
2. QUANTISATION. At SAMPLE_SECS=20 the period is 20.37 s, contributing sd 5.9 s;
   deconvolved true sd is 23.6 s. At SAMPLE_SECS=5 (6.50 s achieved) it falls to
   ~1.9 s at no wall-clock cost -- the cycle runs a fixed CYCLE_SECS either way.

Power at the registered 240 pairs (929 matches/arm -> 579 effective): minimum
detectable difference in mean duration 3.88 s = 4.7% of the mean.
"""
import glob, json, math, os, statistics, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import e1_winner as E

PERIOD_20 = 20.37     # measured median full-cycle period at SAMPLE_SECS=20
PERIOD_5 = 6.50       # measured at SAMPLE_SECS=5


def row_durations(adir, period):
    """-> (durations, n_first_in_cycle, n_in_multi_gap). Arm-blind by construction."""
    S, hint = [], None
    for f in sorted(glob.glob(os.path.join(adir, "s*.ss"))):
        blob = open(f, "rb").read()
        try:
            base = hint = E.find_base(blob, hint)
        except ValueError:
            continue
        S.append((blob, base))
    durs, first, multi, prev = [], 0, 0, None
    for i in range(1, len(S)):
        m = E.match_ends(*S[i]) - E.match_ends(*S[i - 1])
        if m <= 0:
            continue
        if m > 1:
            multi += m
        elif prev is None:
            first += 1
        else:
            durs.append((i - prev) * period)
        if m == 1 and prev is None:
            pass
        prev = i
    return durs, first, multi


def main(out_dir, period=PERIOD_20):
    per_cycle, first, multi = {}, 0, 0
    for d in sorted(glob.glob(os.path.join(out_dir, "artifacts", "*"))):
        dur, f, mu = row_durations(d, period)
        first += f; multi += mu
        if dur:
            per_cycle[os.path.basename(d)] = dur
    allд = [x for v in per_cycle.values() for x in v]
    if not allд:
        print("no measurable durations"); return
    mu = statistics.mean(allд); sd = statistics.stdev(allд)
    means = [statistics.mean(v) for v in per_cycle.values()]
    mbar = statistics.mean([len(v) for v in per_cycle.values()])
    icc = max(0.0, (statistics.pvariance(means) - statistics.pvariance(allд) / mbar)
              / statistics.pvariance(allд))
    deff = 1 + (mbar - 1) * icc
    sd_q = period / math.sqrt(12)
    print(f"cycles={len(per_cycle)}  measurable matches={len(allд)}  "
          f"excluded: first-in-cycle={first} multi-gap={multi}")
    print(f"duration: median {statistics.median(allд):.0f}s  mean {mu:.1f}s  sd {sd:.1f}s")
    print(f"clustering: ICC~{icc:.3f}  deff {deff:.2f}  effective n {len(allд)/deff:.0f}")
    print(f"quantisation sd {sd_q:.1f}s  -> deconvolved true sd "
          f"{math.sqrt(max(sd*sd - sd_q*sd_q, 1)):.1f}s")


if __name__ == "__main__":
    a = sys.argv[1:]
    main(a[0] if a else os.path.join(os.path.dirname(os.path.abspath(__file__)), "out"),
         float(a[1]) if len(a) > 1 else PERIOD_20)
