"""eta_workload.py — ETA from WORKLOAD, not from games/h.

⚠ WHY: a games/h ETA is BIASED OPTIMISTIC for an `imap_unordered` pool. Cheap
games complete first BY CONSTRUCTION, so the completed set's mean cost rises
monotonically and the remaining pool is enriched for expensive games. The
extrapolation runs early and the error GROWS as the arm progresses.

Measured on PHASE 1 (2026-08-29): forks/game by completion third =
1,291 / 2,138 / 2,883 (+111% slope). The games/h ETA read 05:06-05:24 where
this method read 05:37.

Forks are invariant to completion order, so this is the number to quote
anywhere it matters. Usage:
    python3 scratch/eta_workload.py
"""
import datetime, glob, gzip, json, os, time, binascii
import numpy as np

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(HERE, "out", "labels_m1")
FORKS_PER_ADJ = 95.0        # measured on this arm


def held(s):
    return binascii.crc32(str(s).encode()) % 4 == 0


def fire_l20(H):
    return max(H[3], H[4]) >= 13


def main():
    need = {}
    for f in sorted(glob.glob(os.path.join(OUT, "L20", "seed_*.json.gz"))):
        r = json.load(gzip.open(f, "rt"))
        if r["smoke"] or not held(r["seed"]):
            continue
        need[r["seed"]] = sum(1 for _p, H in enumerate(r["heights_trace"])
                              if fire_l20(H))
    done, recent, now = {}, [], time.time()
    for f in glob.glob(os.path.join(OUT, "L20_unthin_held", "seed_*.json.gz")):
        r = json.load(gzip.open(f, "rt"))
        k = r["counters"]["tribunal_forks"]
        done[r["seed"]] = k
        recent.append((os.path.getmtime(f), k))
    adj_rem = sum(v for k, v in need.items() if k not in done)
    adj_done = sum(v for k, v in need.items() if k in done)
    fk_rem = adj_rem * FORKS_PER_ADJ
    rf = sum(k for t, k in recent if t > now - 3600)
    print(f"games {len(done)}/{len(need)}  adjudications done {adj_done} "
          f"remaining {adj_rem}")
    print(f"  => {adj_rem/max(adj_done,1):.2f}x the WORK remains on "
          f"{(len(need)-len(done))/max(len(need),1)*100:.0f}% of the GAMES "
          f"(this is why games/h runs early)")
    if not rf:
        print("  ⚠ no forks completed in the last hour — check the producer "
              "is alive before quoting any ETA")
        return
    hrs = fk_rem / rf
    eta = datetime.datetime.fromtimestamp(now + hrs * 3600)
    print(f"  forks remaining ~{fk_rem:,.0f} · throughput {rf:,.0f} forks/h")
    print(f"  WORKLOAD ETA: {hrs:.1f} h -> {eta.strftime('%a %d %H:%M')} local")


if __name__ == "__main__":
    main()
