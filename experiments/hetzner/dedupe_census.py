#!/usr/bin/env python3
"""dedupe_census.py -- repair a census.jsonl that has duplicate seeds, and
verify the duplicates AGREE before collapsing them.

Written after two census processes briefly shared one output file. The naive
repair is `sort -u`, but that would throw away the interesting part: the two
writers computed the same seeds independently and concurrently, so comparing
their rows is a free determinism check ON THIS BOX, under real contention. If
duplicate rows for a seed ever disagree, that is a much worse problem than
duplication and must not be silently collapsed.

Usage: dedupe_census.py results/upper/census.jsonl
"""
from __future__ import annotations

import sys
import json
import shutil
from collections import defaultdict


def key(r):
    """Everything that must match. Board/trace included when present."""
    return json.dumps({k: r[k] for k in sorted(r) if k != "seed"},
                      sort_keys=True, separators=(",", ":"))


def main(path):
    rows = defaultdict(list)
    n = 0
    with open(path) as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                r = json.loads(line)
            except json.JSONDecodeError:
                continue
            rows[r["seed"]].append(r)
            n += 1

    dupes = {s: v for s, v in rows.items() if len(v) > 1}
    disagree = {s: v for s, v in dupes.items()
                if len({key(r) for r in v}) > 1}

    print(f"rows read      : {n}")
    print(f"unique seeds   : {len(rows)}")
    print(f"duplicated     : {len(dupes)}")
    print(f"DISAGREEING    : {len(disagree)}   <-- must be 0")
    if disagree:
        for s in list(disagree)[:5]:
            print(f"  seed {s}:")
            for r in disagree[s]:
                print(f"    {key(r)[:160]}")
        sys.exit("REFUSING to collapse: duplicate rows disagree. This is a "
                 "determinism failure, not a duplication problem.")

    if dupes:
        print(f"\nAll {len(dupes)} duplicated seeds produced IDENTICAL rows "
              f"across two concurrent processes -- determinism holds under "
              f"contention on this box.")

    shutil.copy(path, path + ".bak")
    with open(path, "w") as f:
        for s in sorted(rows):
            f.write(json.dumps(rows[s][0], separators=(",", ":")) + "\n")
    print(f"wrote {len(rows)} deduped rows to {path} (backup {path}.bak)")


if __name__ == "__main__":
    main(sys.argv[1])
