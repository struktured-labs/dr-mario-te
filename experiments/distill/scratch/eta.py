"""eta.py — re-derive an arm's ETA from segment mtimes, at the OBSERVED rate.

⚠ EXISTS BECAUSE A STATIONARY ETA IS A SMELL. On 2026-08-29 this lane quoted
"~05:00" for ninety minutes without re-deriving it. It stayed correct only
because throughput happened to hold at 17.6 games/h — an accidentally-right
answer, which is not a property of the method (R57). Had the rate degraded the
stale number would have shipped with full confidence.

Run it; do not remember its output. Quote results as "at the observed rate".

  python3 scratch/eta.py out/labels_m1/L20_unthin_held 173
"""
import datetime, glob, os, sys, time


def eta(d, total):
    ts = sorted(os.path.getmtime(f)
                for f in glob.glob(os.path.join(d, "seed_*.json.gz")))
    if len(ts) < 2:
        print(f"{d}: {len(ts)} segments — too few to derive a rate")
        return
    now, n = time.time(), len(ts)
    rem = total - n
    hhmm = lambda t: datetime.datetime.fromtimestamp(t).strftime("%H:%M")
    span = (ts[-1] - ts[0]) / 3600
    print(f"{os.path.basename(d)}: banked {n}/{total}  remaining {rem}  "
          f"newest {hhmm(ts[-1])} ({(now-ts[-1])/60:.1f} min ago)")
    rates = [("overall", n / span)]
    for k in (20, 40):
        if n > k:
            rates.append((f"last {k}", k / ((ts[-1] - ts[-1 - k]) / 3600)))
    for lab, r in rates:
        print(f"  {lab:>8}: {r:5.1f} games/h" +
              (f"   ETA {hhmm(now + rem / r * 3600)}" if rem > 0 else "  DONE"))
    # a stalled producer makes every rate above a lie about the future
    if (now - ts[-1]) / 60 > 45:
        print(f"  ⚠ newest segment is {(now-ts[-1])/60:.0f} min old — the rate "
              f"above is HISTORICAL; check the producer is alive before "
              f"quoting an ETA from it")


if __name__ == "__main__":
    eta(sys.argv[1], int(sys.argv[2]))
