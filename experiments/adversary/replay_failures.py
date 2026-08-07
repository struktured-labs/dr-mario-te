#!/usr/bin/env python3
"""replay_failures.py -- for every TOPOUT/STALL seed seen by census_run.py,
replay it ONE more time (single call, keeping trace + fatal board this time --
the census's parallel pass drops those per-row via _play_one to keep IPC
light) and attach the opening-board + pill-prefix signature features.

Reads:  census/failures_seen.jsonl  (seed,result,pills,viruses_left,... rows
        appended live by census_run.py -- may contain the same seed at most
        once since the census consumes a shuffled seed order without
        repeats)
Writes: census/failures_with_boards.json
"""
from __future__ import annotations

import sys
import os
import json

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

import adversary_harness as AH
import signature as SG

CENSUS_DIR = os.path.join(HERE, "census")
FAILURES_SEEN = os.path.join(CENSUS_DIR, "failures_seen.jsonl")
OUT_PATH = os.path.join(CENSUS_DIR, "failures_with_boards.json")


def load_failure_seeds():
    seeds = []
    seen = set()
    if not os.path.exists(FAILURES_SEEN):
        return seeds
    with open(FAILURES_SEEN) as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            r = json.loads(line)
            if r["seed"] not in seen:
                seen.add(r["seed"])
                seeds.append(r["seed"])
    return seeds


def main():
    seeds = load_failure_seeds()
    print(f"[replay_failures] {len(seeds)} unique failure seeds to replay", flush=True)
    out = []
    for i, seed in enumerate(seeds):
        r = AH.play_seed(seed)  # single-process, full fixture: trace + fatal board
        rec = SG.opening_and_pills(seed, n_pills=20)
        feats = SG.features_from_opening(rec)
        out.append({
            "seed": seed,
            "result": r["result"],
            "pills": r["pills"],
            "viruses_left": r["viruses_left"],
            "dies_ahead": r["dies_ahead"],
            "fatal_board": r["first_topout_board"],
            "trace_len": len(r["trace"]),
            "opening_board": rec["opening_board"],
            "pills_prefix": rec["pills_prefix"],
            "features": feats,
        })
        if (i + 1) % 25 == 0 or (i + 1) == len(seeds):
            print(f"[replay_failures] {i+1}/{len(seeds)} replayed", flush=True)

    with open(OUT_PATH, "w") as f:
        json.dump(out, f, indent=2)
    print(f"[replay_failures] wrote {OUT_PATH} ({len(out)} records)", flush=True)


if __name__ == "__main__":
    main()
