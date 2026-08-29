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
