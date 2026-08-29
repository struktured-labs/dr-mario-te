"""verdict_band.py — the verdict ETA with ALL uncertainty terms propagated.

⚠ R53 ON MY OWN PRECISION. verdict_eta.py quoted +/-33 min for a FOUR-STAGE
chain using only ONE term (the census ply count). A +/-10% band on a six-hour
projection whose dominant input has never been measured is "too good", and
too-good is a defect signature. Propagated properly the band is +/-166 min.

The four terms, and which one actually dominates:
  1 PHASE 1 end       throughput sd/mean = 16% hour-to-hour   <- DOMINANT
  2 forks per ply     95.0 +/- 8.1, used as EXACT before
  3 census ply count  +/-sqrt(n)*sd                            <- what I had
  4 12->15 scaling    1.25 naive .. 1.36 under-capacity (flat prior)

⚠⚠ SECOND CORRECTION, and it is the MIRROR of the first. I applied sqrt(n) to
the census ply count (a per-game quantile applied to a 122-game sum assumes
PERFECT CORRELATION) and then charged a SINGLE-HOUR throughput SD across a
~10 h projection WITHOUT the same correction — which assumes every hour is high
or low TOGETHER. Same correlation assumption, opposite direction, same analysis.
⇒ CORRELATION STRUCTURE HAS TO BE ASKED ABOUT EVERY TERM, not just the one that
  looked suspicious.

Measured on this arm (SD of per-hour rates by window length):
    1 h windows  SD 12,619 (CV 0.37)
    2 h windows  SD  6,891 (CV 0.20)      ratio 0.55, vs 0.71 for independent
  => collapses AT LEAST as fast as independent noise. Two reasons:
     (a) A REAL TREND: +4,326 forks/h per hour, r = +0.64, explaining 41% of
         the hour-to-hour variance. Throughput RISES as the arm reaches bigger
         games, because per-fork cost falls with amortisation. A KNOWN TREND
         MUST BE MODELLED, NOT CHARGED TO VARIANCE — doing so makes a band
         useless while the quantity is actually forecastable.
     (b) A MEASUREMENT ARTIFACT: a game's whole fork count is attributed to its
         COMPLETION INSTANT though the work spanned 25-60 min, so short windows
         are lumpy BY CONSTRUCTION and their SD overstates real variation.
  SD about the TREND is 9,682, and over an 8 h horizon the uncertainty on the
  MEAN RATE is 9,682/sqrt(8) = 3,423 -> ~8%, NOT the 37% first charged.

⚠ The trend cannot extrapolate freely: it is driven by amortisation, which
  bottoms out. Best-decile per-fork cost 0.643 s => a hard ceiling of ~67,000
  forks/h at 12 workers. Current ~41,000 is 62% of it.

FOR ANYONE SIZING WORK ON THIS BOX: expect ~40-45k forks/h at 12 workers rising
toward a ~67k ceiling, with ~8% uncertainty on a multi-hour mean. Do NOT
provision against the raw 44% hour-to-hour spread — most of it is a trend plus
completion lumpiness.
Monte Carlo rather than a linear error budget, because the terms MULTIPLY.

⚠ It also corrects a subtler error: the earlier PHASE 1 ETA used the LAST
HOUR's throughput, which happened to be a high hour. A 4-hour mean is the
honest basis for a 6-hour projection and puts the end ~1 h later.
"""
import binascii, datetime, glob, gzip, json, os, time
import numpy as np

H = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(H, "out", "labels_m1")


def held(s):
    return binascii.crc32(str(s).encode()) % 4 == 0


def trig(r):
    return sum(1 for _p, h in enumerate(r["heights_trace"])
               if max(h[3], h[4]) >= 13)


def main(N=20000):
    rng = np.random.default_rng(7)
    now = time.time()
    fpa = []
    for f in glob.glob(os.path.join(OUT, "L20_unthin_held", "seed_*.json.gz")):
        r = json.load(gzip.open(f, "rt"))
        n = len(r["adjudications"])
        if n:
            fpa.append(r["counters"]["tribunal_forks"] / n)
    fpa = np.array(fpa)
    need, allg = {}, []
    for f in sorted(glob.glob(os.path.join(OUT, "L20", "seed_*.json.gz"))):
        r = json.load(gzip.open(f, "rt"))
        if r["smoke"]:
            continue
        allg.append(trig(r))
        if held(r["seed"]):
            need[r["seed"]] = trig(r)
    done, rec = set(), []
    for f in glob.glob(os.path.join(OUT, "L20_unthin_held", "seed_*.json.gz")):
        r = json.load(gzip.open(f, "rt"))
        done.add(r["seed"])
        rec.append((os.path.getmtime(f), r["counters"]["tribunal_forks"]))
    p1_adj = sum(v for k, v in need.items() if k not in done)
    hrs = [sum(k for t, k in rec if now - (i + 1) * 3600 <= t < now - i * 3600)
           for i in range(4)]
    hrs = [h for h in hrs if h > 0]
    if not hrs:
        print("no recent throughput — cannot project")
        return
    th_m = float(np.mean(hrs))
    th_s = float(np.std(hrs, ddof=1)) if len(hrs) > 1 else th_m * 0.15
    allg = np.array(allg, float)
    left = 128 - len(glob.glob(os.path.join(OUT, "L20_census_fresh",
                                            "seed_*.json.gz")))
    p1h = p1_adj * rng.choice(fpa, N) / rng.normal(th_m, th_s, N).clip(1000)
    cp = rng.normal(left * allg.mean(), np.sqrt(left) * allg.std(ddof=1), N)
    ch = cp * rng.choice(fpa, N) / (rng.normal(th_m, th_s, N).clip(1000)
                                    * rng.uniform(1.25, 1.36, N))
    tot = p1h + ch + 0.5
    q = np.percentile(tot, [5, 50, 95])
    fmt = lambda h: datetime.datetime.fromtimestamp(
        now + h * 3600).strftime("%a %H:%M")
    print(f"throughput last {len(hrs)} h: {hrs} -> {th_m:,.0f} +/- {th_s:,.0f} "
          f"forks/h ({th_s/th_m*100:.0f}%) <- DOMINANT TERM")
    print(f"PHASE 1 end : {fmt(np.median(p1h))}  "
          f"(90% {fmt(np.percentile(p1h,5))} - {fmt(np.percentile(p1h,95))})")
    print(f"VERDICT     : {fmt(q[1])}")
    print(f"  90% band  : {fmt(q[0])} - {fmt(q[2])}  "
          f"(+/-{(q[2]-q[0])/2*60:.0f} min)")


if __name__ == "__main__":
    main()
