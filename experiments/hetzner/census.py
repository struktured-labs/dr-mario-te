#!/usr/bin/env python3
"""census.py -- grind the champion decide path over a contiguous block of the
16-bit seed space and classify every outcome.

This node owns the UPPER HALF (32768..65535); the local adversary agent owns
the lower half, so the two never collide and the two JSONLs concatenate into
a full-space census.

DESIGN NOTES (why it looks like this):
  * Resumable by construction. Every completed seed is one JSONL line, and
    startup reads back what's already there and skips it. Killing this process
    at any moment loses at most one chunk, and re-running resumes -- there is
    no separate checkpoint file to fall out of sync with the data.
  * Fixtures only for failures. play_seed() can return the fatal board and the
    full move trace, but shipping those back from every worker costs real IPC
    at 32k games. Clears are pruned to a light row inside the worker; failures
    keep board + trace, because those boards ARE the deliverable (adversarial
    fixture material) and failures are rare.
  * Chunked so throughput is observable while running, and so a stall shows up
    as a missing progress line rather than silence.

Usage:
    census.py --lo 32768 --hi 65536 --workers 4 --out results/upper
"""
from __future__ import annotations

import sys
import os
import json
import time
import fcntl
import argparse
from concurrent.futures import ProcessPoolExecutor, as_completed

QA = "/home/struktured/projects/dr-mario-qa-wt/experiments"
sys.path.insert(0, QA + "/adversary")

import adversary_harness as AH  # noqa: E402


def _play(seed):
    """Worker: full game, prune fixtures on success. Returns a JSON-ready row."""
    r = AH.play_seed(seed)
    row = {"seed": r["seed"], "result": r["result"], "pills": r["pills"],
           "viruses_left": r["viruses_left"], "dies_ahead": r["dies_ahead"],
           "n_moves": len(r["trace"])}
    if r["result"] != "clear":
        # the valuable artifact: fatal board + exact replay trace
        row["board"] = r["first_topout_board"]
        row["trace"] = [[int(i), int(a)] for i, a in r["trace"]]
    return row


def acquire_lock(out_dir):
    """Exactly one census process may own an output directory.

    NOT hypothetical: two runners (an orphaned setsid tree and a systemd unit)
    once appended to the same census.jsonl and produced 400 rows covering 200
    seeds -- every seed duplicated, and silently, because both were making
    "progress". A resumable appender MUST be single-writer. The lock is held
    for the life of the process and released by the kernel on exit, so a hard
    kill cannot leave a stale lock behind (unlike a pidfile).
    """
    path = os.path.join(out_dir, ".census.lock")
    f = open(path, "w")
    try:
        fcntl.flock(f.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError:
        sys.exit(f"[census] REFUSING TO START: another census process already "
                 f"owns {out_dir} (lock {path}). Two writers corrupt the JSONL.")
    f.write(f"{os.getpid()}\n")
    f.flush()
    return f    # keep referenced: closing would drop the lock


def load_done(path):
    """Seeds already recorded. Tolerates a torn final line from a hard kill."""
    done = set()
    if not os.path.exists(path):
        return done
    with open(path) as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                done.add(json.loads(line)["seed"])
            except (json.JSONDecodeError, KeyError):
                continue   # torn tail -- that seed simply gets redone
    return done


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--lo", type=int, default=32768)
    ap.add_argument("--hi", type=int, default=65536)   # exclusive
    ap.add_argument("--workers", type=int, default=4)
    ap.add_argument("--chunk", type=int, default=200)
    ap.add_argument("--out", required=True)
    a = ap.parse_args()

    os.makedirs(a.out, exist_ok=True)
    _lock = acquire_lock(a.out)          # noqa: F841 -- must stay referenced
    census_path = os.path.join(a.out, "census.jsonl")
    prog_path = os.path.join(a.out, "progress.json")

    done = load_done(census_path)
    todo = [s for s in range(a.lo, a.hi) if s not in done]
    total = a.hi - a.lo
    print(f"[census] block {a.lo}..{a.hi - 1} ({total} seeds), "
          f"{len(done)} already done, {len(todo)} to go, {a.workers} workers",
          flush=True)

    t_start = time.monotonic()
    n_done_run = 0
    counts = {"clear": 0, "topout": 0, "stall": 0, "dies_ahead": 0}
    # re-count what's already on disk so the running tally is whole-block
    if done:
        with open(census_path) as f:
            for line in f:
                try:
                    r = json.loads(line)
                except json.JSONDecodeError:
                    continue
                counts[r["result"]] = counts.get(r["result"], 0) + 1
                if r.get("dies_ahead"):
                    counts["dies_ahead"] += 1

    with ProcessPoolExecutor(max_workers=a.workers, initializer=AH._lazy) as ex:
        for i in range(0, len(todo), a.chunk):
            chunk = todo[i:i + a.chunk]
            t0 = time.monotonic()
            rows = []
            futs = [ex.submit(_play, s) for s in chunk]
            for fut in as_completed(futs):
                rows.append(fut.result())

            rows.sort(key=lambda r: r["seed"])
            with open(census_path, "a") as f:
                for r in rows:
                    f.write(json.dumps(r, separators=(",", ":")) + "\n")
                f.flush()
                os.fsync(f.fileno())    # survive a box-level kill, not just a process one

            for r in rows:
                counts[r["result"]] = counts.get(r["result"], 0) + 1
                if r.get("dies_ahead"):
                    counts["dies_ahead"] += 1
            n_done_run += len(rows)

            dt = time.monotonic() - t0
            elapsed = time.monotonic() - t_start
            rate = n_done_run / elapsed if elapsed > 0 else 0.0
            remaining = len(todo) - n_done_run
            eta_h = remaining / rate / 3600 if rate > 0 else float("inf")
            n_block = len(done) + n_done_run
            print(f"[census] {n_block}/{total} ({n_block / total:.1%})  "
                  f"chunk {len(rows)} in {dt:.1f}s  "
                  f"rate {rate:.2f} g/s  ETA {eta_h:.1f}h  "
                  f"clear={counts['clear']} topout={counts['topout']} "
                  f"stall={counts['stall']} dies_ahead={counts['dies_ahead']}",
                  flush=True)

            with open(prog_path, "w") as f:
                json.dump({"lo": a.lo, "hi": a.hi, "done": n_block,
                           "total": total, "counts": counts,
                           "games_per_sec": rate, "eta_hours": eta_h,
                           "updated": time.time()}, f, indent=2)

    print(f"[census] BLOCK COMPLETE {a.lo}..{a.hi - 1}  counts={counts}", flush=True)


if __name__ == "__main__":
    main()
