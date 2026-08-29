"""verdict_eta.py — ETA for the VERDICT, not for a stage.

The verdict is ONE read on the enlarged bank (A5 §5.2 registers no interim),
so it needs BOTH arms: PHASE 1 -> handoff -> census at 15 workers -> fit2.
A stage-completion time is NOT this number and must never be quoted as it.

⚠ TWO ERRORS THIS SCRIPT EXISTS TO AVOID, both made once:
 1. games/h is biased OPTIMISTIC for an imap_unordered arm (cheap games finish
    first, so the remaining pool is enriched for expensive ones). Work in FORKS.
 2. The uncertainty on a SUM over N games is sqrt(N)*sd — NOT the per-game
    p25/p75 spread. Applying a per-game quantile to all N games assumes perfect
    correlation and gave a 5-hour window where the truth is about one hour
    (±10% vs ±45%). Same family as quoting a per-game rate as a fleet rate.
"""
import binascii, datetime, glob, gzip, json, os, time
import numpy as np

H = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(H, "out", "labels_m1")
FPA, CENSUS_N, WORKERS_NOW, WORKERS_AFTER = 95.0, 128, 12, 15


def held(s):
    return binascii.crc32(str(s).encode()) % 4 == 0


def trig(rec):
    return sum(1 for _p, h in enumerate(rec["heights_trace"])
               if max(h[3], h[4]) >= 13)


def main():
    now = time.time()
    need, allg = {}, []
    for f in sorted(glob.glob(os.path.join(OUT, "L20", "seed_*.json.gz"))):
        r = json.load(gzip.open(f, "rt"))
        if r["smoke"]:
            continue
        allg.append(trig(r))
        if held(r["seed"]):
            need[r["seed"]] = trig(r)
    done, recent = set(), []
    for f in glob.glob(os.path.join(OUT, "L20_unthin_held", "seed_*.json.gz")):
        r = json.load(gzip.open(f, "rt"))
        done.add(r["seed"])
        recent.append((os.path.getmtime(f), r["counters"]["tribunal_forks"]))
    rate = sum(k for t, k in recent if t > now - 3600)
    if not rate:
        print("⚠ no forks in the last hour — check the producer before quoting")
        return
    p1_h = sum(v for k, v in need.items() if k not in done) * FPA / rate
    cen_left = CENSUS_N - len(
        glob.glob(os.path.join(OUT, "L20_census_fresh", "seed_*.json.gz")))
    a = np.array(allg, float)
    tot, se = cen_left * a.mean(), np.sqrt(cen_left) * a.std(ddof=1)
    r15 = rate * WORKERS_AFTER / WORKERS_NOW
    fmt = lambda t: datetime.datetime.fromtimestamp(t).strftime("%a %H:%M")
    print(f"PHASE 1 ends ~{fmt(now + p1_h*3600)}   (COUNTED from traces)")
    print(f"census {cen_left} games: {tot:,.0f} +/- {se:,.0f} trigger plies "
          f"(ESTIMATED — those seeds are UNPLAYED, no traces exist)")
    for lab, t in (("-1 SE", tot - se), ("CENTRAL", tot), ("+1 SE", tot + se)):
        eta = now + p1_h * 3600 + t * FPA / r15 * 3600 + 0.5 * 3600
        print(f"  {lab:>8}  VERDICT {fmt(eta)}")
    print("  (+0.5 h features+fit2 included; census workload is the soft spot,")
    print("   replaced by a MEASURED rate once drm-census-eta reports)")


if __name__ == "__main__":
    main()
