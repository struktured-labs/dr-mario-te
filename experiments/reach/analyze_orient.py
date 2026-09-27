#!/usr/bin/env python3
"""Tabulate orient_harness.py rows: orientation-at-lock vs the LATEST target the driver was given, by frames since that
target last changed, split PROPH / non-PROPH and single-answer / changed-answer pills; plus the missed-spawn-edge class.
  analyze_orient.py 'tmp/orient/f_t2_s*.jsonl' ['tmp/orient/f_t0_s*.jsonl' ...]
"""
import collections, glob, json, sys


def bucket(a):
    return "none" if a is None else ("0-2" if a <= 2 else "3-5" if a <= 5 else "6-9" if a <= 9 else "10+")


def main(patterns):
    for pat in patterns:
        files = sorted(glob.glob(pat))
        T = collections.defaultdict(collections.Counter); E = collections.defaultdict(collections.Counter)
        prev_row0 = collections.Counter(); n = 0
        for fn in files:
            rows = [json.loads(l) for l in open(fn)]
            for i, r in enumerate(rows):
                n += 1
                pk = "PROPH" if r["proph"] else "nonP"
                o = None if r["trot"] is None else ("ok" if r["rot"] == r["trot"] and r["x"] == r["tcol"] else
                                                     "180" if r["rot"] == (r["trot"] ^ 2) and r["x"] == r["tcol"] else "other")
                if not r["spawn_edge"]:
                    E[pk][o] += 1
                    prev_row0[rows[i - 1]["row"] == 0 if i else None] += 1
                    continue
                if r["trot"] is None:
                    continue
                avail = None if r.get("chg_age") is None else r["age"] - r["chg_age"]
                orient = "ok" if r["rot"] == r["trot"] else ("180" if r["rot"] == (r["trot"] ^ 2) else "90")
                T[(pk, "changed" if r.get("nchg", 0) > 1 else "single", bucket(avail))][orient] += 1
        print(f"== {pat}: {len(files)} files, {n} pills")
        print("  SPAWN-EDGE DETECTED: orientation at lock vs the latest published target, by frames since it last changed")
        for k in sorted(T):
            c = T[k]; m = sum(c.values())
            print("    %-5s %-7s avail=%-5s n=%-5d ok=%-5d 180=%-4d 90=%-4d err=%.1f%%" %
                  (k[0], k[1], k[2], m, c["ok"], c["180"], c["90"], 100 * (m - c["ok"]) / m))
        print("  SPAWN-EDGE MISSED (driver never saw the new pill): cell+orient vs the stale answer")
        for k in sorted(E):
            c = E[k]; m = sum(c.values())
            print("    %-5s n=%-5d exact=%-4d 180=%-4d other=%-4d" % (k, m, c["ok"], c["180"], c["other"]))
        print("    previous pill locked at row 0 (Y=$0F): %s" % dict(prev_row0))


if __name__ == "__main__":
    main(sys.argv[1:])
