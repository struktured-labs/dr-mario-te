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

HERE = os.path.dirname(os.path.abspath(__file__))
QA = "/home/struktured/projects/dr-mario-qa-wt/experiments"
sys.path.insert(0, QA + "/adversary")
sys.path.insert(0, HERE)

import adversary_harness as AH  # noqa: E402
import code_manifest  # noqa: E402


def pill_stream_colours(seed):
    """How many distinct COLOURS this seed's 128-capsule buffer can deliver.

    Fewer than 3 means the seed cannot clear all three virus colours, so no
    policy could win it. Exactly ONE seed in 65,536 is affected -- seed 1, which
    NesPillSource maps to LFSR state (0,1); that steps straight into the
    ABSORBING state (0,0), after which the low nibble is 0 forever and every
    capsule is id 0 = (1,1). Verified exhaustively by audit_pill_streams.py.
    """
    from nes_pills import gen_sequence, PILL_COLORS
    s0, s1 = (seed >> 8) & 0xFF, seed & 0xFF
    if (s0, s1) == (0, 0):
        s0, s1 = 0x89, 0x88          # NesPillSource's own substitution
    ids, _, _ = gen_sequence(s0, s1)
    cols = set()
    for i in set(ids):
        a, b = PILL_COLORS[i]
        cols.add(a)
        cols.add(b)
    return len(cols)


def classify_degenerate(trace, n_colours):
    """Is this row a NON-GAME rather than a loss? Returns a reason, or None.

    Two independent checks, on purpose:
      * INPUT side -- the capsule stream cannot deliver all three colours, so no
        policy could have won. Exact, and knowable a priori.
      * OUTPUT side -- the trace collapses onto one or two moves. Defence in
        depth: it catches a no-progress cycle whose CAUSE we have not
        anticipated, which is precisely what the input check would miss.

    A degenerate row is RELABELLED, not discarded: it stays on disk with its
    evidence so the call is auditable, it simply must never be pooled into a
    failure count. A non-game counted as a loss both inflates the failure rate
    and destroys real structure (the genuine clean failures all end at the LAST
    virus; a bogus row with 48 left would bury that signature).
    """
    if n_colours < 3:
        return f"pill stream delivers only {n_colours} colour(s)"
    if len(trace) < 20:
        return None
    counts = {}
    for _i, a in trace:
        counts[a] = counts.get(a, 0) + 1
    if len(counts) <= 2:
        return f"only {len(counts)} distinct move(s) over {len(trace)} plies"
    top = max(counts.values())
    if top / len(trace) >= 0.8:
        return f"one move is {100 * top / len(trace):.0f}% of {len(trace)} plies"
    return None


def _play(seed):
    """Worker: full game, prune fixtures on success. Returns a JSON-ready row."""
    r = AH.play_seed(seed)
    trace = [[int(i), int(a)] for i, a in r["trace"]]
    n_colours = pill_stream_colours(seed)
    row = {"seed": r["seed"], "result": r["result"], "pills": r["pills"],
           "viruses_left": r["viruses_left"], "dies_ahead": r["dies_ahead"],
           "n_moves": len(trace), "n_pill_colours": n_colours}

    reason = classify_degenerate(trace, n_colours)
    if reason is not None:
        row["result"] = "degenerate"
        row["degenerate_reason"] = reason
        row["original_result"] = r["result"]
        row["dies_ahead"] = False

    if row["result"] != "clear":
        # the valuable artifact: fatal board + exact replay trace
        row["board"] = r["first_topout_board"]
        row["trace"] = trace
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

    # Stamp the code that produced this data, at START. A 30h census outlives
    # several edits to the tree it started from; without this the rows cannot be
    # tied to the code that made them. AH is already imported, so from_imports()
    # records the files actually resolved, not the ones assumed.
    AH._lazy()
    rolled = code_manifest.stamp(os.path.join(a.out, "manifest.json"),
                                 extra={"lo": a.lo, "hi": a.hi,
                                        "workers": a.workers, "chunk": a.chunk})
    print(f"[census] code manifest {rolled[:16]} -> {a.out}/manifest.json", flush=True)

    done = load_done(census_path)
    todo = [s for s in range(a.lo, a.hi) if s not in done]
    total = a.hi - a.lo
    print(f"[census] block {a.lo}..{a.hi - 1} ({total} seeds), "
          f"{len(done)} already done, {len(todo)} to go, {a.workers} workers",
          flush=True)

    t_start = time.monotonic()
    n_done_run = 0
    # "degenerate" is tracked SEPARATELY from the failure classes on purpose --
    # it is a non-game, not a loss, and must never be pooled into a failure rate.
    counts = {"clear": 0, "topout": 0, "stall": 0, "degenerate": 0, "dies_ahead": 0}
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
                  f"stall={counts['stall']} dies_ahead={counts['dies_ahead']} "
                  f"degen={counts['degenerate']}",
                  flush=True)

            with open(prog_path, "w") as f:
                json.dump({"lo": a.lo, "hi": a.hi, "done": n_block,
                           "total": total, "counts": counts,
                           "games_per_sec": rate, "eta_hours": eta_h,
                           "updated": time.time()}, f, indent=2)

    print(f"[census] BLOCK COMPLETE {a.lo}..{a.hi - 1}  counts={counts}", flush=True)


if __name__ == "__main__":
    main()
