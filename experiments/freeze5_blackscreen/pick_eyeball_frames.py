#!/usr/bin/env python3
"""pick_eyeball_frames.py — choose which frames a human must actually LOOK at.

The validation claim is not "the watchdog logged ALIVE 180 times". It is "the watchdog's
verdict matched what was really on screen". That requires eyes on the hard cases, chosen by a
rule fixed in advance rather than by which frames happen to look convincing:

  1. every non-ALIVE verdict (SUSPECT / WEDGED / capture failure), plus its neighbours
     -- these are the alarm-adjacent frames; a wrong call here is a false positive;
  2. every frame whose screen_class is NOT in_match
     -- the between-match / title / level-select screens, i.e. the legitimately-static
        candidates, which are the hardest case for a duration-based rule;
  3. the N frames with the SMALLEST changed_frac
     -- the closest the window ever came to the static floor, i.e. the nearest miss;
  4. the N frames with the LARGEST changed_frac
     -- whole-screen changes, which is what a match transition looks like;
  5. first and last frame (window endpoints).
"""

from __future__ import annotations

import argparse
import json


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--watch-log", required=True)
    ap.add_argument("--n-extreme", type=int, default=4)
    a = ap.parse_args()

    recs = []
    with open(a.watch_log) as fh:
        for line in fh:
            line = line.strip()
            if line:
                recs.append(json.loads(line))
    recs.sort(key=lambda r: r["seq"])
    by_seq = {r["seq"]: r for r in recs}

    picks: dict[int, list[str]] = {}

    def add(seq: int, why: str) -> None:
        if seq in by_seq:
            picks.setdefault(seq, []).append(why)

    for r in recs:
        if r["verdict"] not in ("ALIVE", "INIT"):
            add(r["seq"], f"verdict={r['verdict']}:{r['reason']}")
            add(r["seq"] - 1, "neighbour_of_non_alive")
            add(r["seq"] + 1, "neighbour_of_non_alive")
        if not r.get("capture_ok", True):
            add(r["seq"], "capture_failed")
        if r.get("screen_class") not in ("in_match", None):
            add(r["seq"], f"screen_class={r.get('screen_class')}")
        if r.get("note"):
            add(r["seq"], f"note={r['note']}")

    withcf = [r for r in recs if r.get("changed_frac") is not None]
    for r in sorted(withcf, key=lambda r: r["changed_frac"])[: a.n_extreme]:
        add(r["seq"], f"min_changed_frac={r['changed_frac']}")
    for r in sorted(withcf, key=lambda r: -r["changed_frac"])[: a.n_extreme]:
        add(r["seq"], f"max_changed_frac={r['changed_frac']}")
        add(r["seq"] - 1, "before_large_change")
    add(recs[0]["seq"], "window_first")
    add(recs[-1]["seq"], "window_last")

    out = []
    for seq in sorted(picks):
        r = by_seq[seq]
        out.append({"seq": seq, "ts": r["ts"], "verdict": r["verdict"],
                    "reason": r["reason"], "changed_frac": r.get("changed_frac"),
                    "screen_class": r.get("screen_class"),
                    "chrome_match_frac": r.get("chrome_match_frac"),
                    "black_frac": r.get("black_frac"),
                    "why": sorted(set(picks[seq]))})
    print(json.dumps(out, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
