#!/usr/bin/env python3
"""scan_winner.py -- exhaustive hunt for a MATCH-WINNER encoding in the state.

Runs over the complete cached corpus (0 samples dropped -- the earlier pass lost
~15% to find_base's counter/board corroboration check, which could break a
monotone counter and hide exactly what we are looking for).

Test: a per-side win counter must, in EVERY row, be non-decreasing across the
cycle and gain exactly one per completed match. We locate match boundaries from
the virus counters (either side's count INCREASING = a new match began) and then
ask which byte offsets behave like that. An offset that only works in some rows
is not a winner byte.
"""
import pickle, sys, collections
import numpy as np

def load(cache):
    rows = pickle.loads(open(cache, "rb").read())
    return {k: v for k, v in rows.items() if v and all(s is not None for s in v)}

def boundaries(samples):
    b = []
    for i in range(1, len(samples)):
        if samples[i]["vp1"] > samples[i-1]["vp1"] or samples[i]["vp2"] > samples[i-1]["vp2"]:
            b.append(i)
    return b

def main(cache):
    rows = load(cache)
    print(f"rows with a fully decodable timeline: {len(rows)}")
    WIN = len(rows[next(iter(rows))][0]["win"])
    # per-offset tally of "behaved like a win counter in this row"
    ok_tally = np.zeros(WIN, dtype=np.int32)
    monotone_tally = np.zeros(WIN, dtype=np.int32)
    considered = 0
    tot_bounds = 0
    for key, samples in rows.items():
        bnds = boundaries(samples)
        if len(bnds) < 2:
            continue
        considered += 1; tot_bounds += len(bnds)
        arr = np.frombuffer(b"".join(s["win"] for s in samples), dtype=np.uint8).reshape(len(samples), WIN).astype(np.int16)
        d = np.diff(arr, axis=0)
        mono = (d >= 0).all(axis=0)
        monotone_tally += mono
        gained = d.sum(axis=0)
        ok_tally += mono & (gained == len(bnds))
    print(f"rows used (>=2 boundaries): {considered}   total boundaries: {tot_bounds}")
    print(f"offsets non-decreasing in ALL {considered} rows: {(monotone_tally==considered).sum()}")
    hits = np.where(ok_tally == considered)[0]
    print(f"offsets that gain EXACTLY one per match in ALL {considered} rows: {len(hits)}")
    for h in hits[:20]:
        a = f"${h:04x}" if h < 0x800 else f"${0x6000+h-0x800:04x}"
        print(f"   offset {a}")
    # near-misses: works in most rows
    near = np.where(ok_tally >= considered * 0.8)[0]
    print(f"offsets working in >=80% of rows: {len(near)}")
    for h in near[:20]:
        a = f"${h:04x}" if h < 0x800 else f"${0x6000+h-0x800:04x}"
        print(f"   offset {a}  rows={ok_tally[h]}/{considered}")

if __name__ == "__main__":
    main(sys.argv[1])

def scan_flag(cache):
    """A 'last winner' FLAG rather than a counter: a byte that is constant
    WITHIN a match, changes only AT boundaries, and takes very few values."""
    rows = load(cache)
    WIN = len(rows[next(iter(rows))][0]["win"])
    good = np.zeros(WIN, dtype=np.int32); considered = 0
    nvals = collections.defaultdict(set)
    for key, samples in rows.items():
        bnds = set(boundaries(samples))
        if len(bnds) < 2: continue
        considered += 1
        arr = np.frombuffer(b"".join(s["win"] for s in samples), dtype=np.uint8).reshape(len(samples), WIN)
        changed = arr[1:] != arr[:-1]                      # change observed AT sample i+1
        idx = np.arange(1, len(samples))
        at_b = np.isin(idx, list(bnds))
        # must never change off a boundary, and must change at least once
        never_off = ~(changed[~at_b].any(axis=0))
        changes_on = changed[at_b].any(axis=0)
        good += (never_off & changes_on)
        for o in np.where(never_off & changes_on)[0]:
            nvals[o].update(arr[:, o].tolist())
    print(f"\n=== 'last winner' FLAG scan (constant within a match, changes only at boundaries)")
    print(f"rows used: {considered}")
    hits = np.where(good == considered)[0]
    print(f"offsets with that behaviour in ALL rows: {len(hits)}")
    for h in hits[:25]:
        a = f"${h:04x}" if h < 0x800 else f"${0x6000+h-0x800:04x}"
        print(f"   {a}  distinct values seen: {sorted(nvals[h])[:8]}")
    near = np.where(good >= considered*0.9)[0]
    print(f"offsets with that behaviour in >=90% of rows: {len(near)}")
    for h in near[:25]:
        a = f"${h:04x}" if h < 0x800 else f"${0x6000+h-0x800:04x}"
        print(f"   {a}  rows={good[h]}/{considered}  values={sorted(nvals[h])[:8]}")
