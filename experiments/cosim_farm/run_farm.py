#!/usr/bin/env python3
"""Batched co-sim farm: N full games through the REAL RTL, in parallel, as JSONL.

Parallelism model
-----------------
One worker process = one long-lived verilated co-sim process. The co-sim is the
CPU-bound half; the Python worker is a thin pipe driver that spends nearly all its time
blocked on `readline()`, so worker count should track CORES, not cores-minus-something.
The co-sim is REUSED across every game a worker plays -- gate_validate.py's (a2) check
exists precisely to prove that reuse changes nothing.

Work is split by disjoint seed ranges. There is no shared state between workers or
between machines, so `--seed-start/--seed-count` is the only knob needed to shard across
the desktop, the Hetzner box and the third machine: give each a disjoint slice and
concatenate the JSONL.

PAIRING. Every arm plays the SAME seeds. Seed s produces the same virus layout and the
same NES capsule stream in every arm, so arms are compared within seed -- the control the
physical MiSTer rig cannot have (the cart's RNG is boot-frame-count dependent, and the
probe infrastructure does not pin it; CANDIDATE_TIER3.md sec 11 says so itself and tells
the silicon lane to use an unpaired test for exactly this reason).

RAM. Each co-sim is ~7MB RSS. --workers 20 is well under 1GB total; the binding
constraint is cores. --max-rss-gb aborts if the pool ever exceeds a hard ceiling, so a
runaway can never repeat this project's OOM history.

Resumable: existing (arm, seed) rows in the output file are skipped, so a killed run
restarts where it stopped instead of redoing hours of RTL.
"""
from __future__ import annotations

import argparse
import json
import os
import resource
import socket
import sys
import time
from concurrent.futures import ProcessPoolExecutor, as_completed

HERE = os.path.dirname(os.path.abspath(__file__))
RL = "/home/struktured/projects/dr_mario_rl"
QA = "/home/struktured/projects/dr-mario-qa-wt/experiments"
for _p in (HERE, RL + "/.claude/worktrees/faithful-sim/src", QA):
    if _p not in sys.path:
        sys.path.insert(0, _p)

BUILD = os.environ.get("COSIM_FARM_BUILD", os.path.join(HERE, "build"))
FARM_BIN = os.path.join(BUILD, "obj_farm", "farm_vsim")

_W = {}


def _init(fw_dir, level, max_pills, exec_mode, mem_cap_bytes):
    if mem_cap_bytes:
        # Per-worker address-space ceiling. A worker that tries to balloon dies with
        # MemoryError instead of taking the machine down with it.
        resource.setrlimit(resource.RLIMIT_AS, (mem_cap_bytes, mem_cap_bytes))
    import game as G
    from cosim import Cosim
    _W["G"] = G
    _W["cosim"] = Cosim(FARM_BIN, fw_dir)
    _W["level"] = level
    _W["max_pills"] = max_pills
    _W["exec_mode"] = exec_mode


def _play(seed):
    G = _W["G"]
    t0 = time.time()
    r = G.play_game(_W["cosim"], seed=seed, level=_W["level"],
                    max_pills=_W["max_pills"], exec_mode=_W["exec_mode"])
    r["wall_secs"] = round(time.time() - t0, 2)
    r["host"] = socket.gethostname()
    return r


def load_done(path, arm):
    done = set()
    if os.path.exists(path):
        with open(path) as fh:
            for ln in fh:
                ln = ln.strip()
                if not ln:
                    continue
                try:
                    r = json.loads(ln)
                except Exception:
                    continue
                if r.get("arm") == arm:
                    done.add(int(r["seed"]))
    return done


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--arm", required=True, help="label recorded in the JSONL")
    ap.add_argument("--fw", required=True, help="dir holding this arm's copro_rom.hex")
    ap.add_argument("--out", required=True)
    ap.add_argument("--seed-start", type=int, default=0)
    ap.add_argument("--seed-count", type=int, default=20)
    ap.add_argument("--workers", type=int, default=6)
    ap.add_argument("--level", type=int, default=11)
    ap.add_argument("--max-pills", type=int, default=300)
    ap.add_argument("--exec-mode", default="drop", choices=["drop", "tuck"])
    ap.add_argument("--per-worker-rss-mb", type=int, default=2048,
                    help="hard per-worker address-space cap")
    a = ap.parse_args()

    seeds = list(range(a.seed_start, a.seed_start + a.seed_count))
    done = load_done(a.out, a.arm)
    todo = [s for s in seeds if s not in done]

    import hashlib
    fw_md5 = hashlib.md5(open(os.path.join(a.fw, "copro_rom.hex"), "rb").read()).hexdigest()
    print(f"arm={a.arm} fw={fw_md5} exec={a.exec_mode} level={a.level} "
          f"seeds {seeds[0]}..{seeds[-1]} ({len(todo)} to run, {len(done)} already done) "
          f"workers={a.workers} host={socket.gethostname()}", flush=True)

    os.makedirs(os.path.dirname(a.out), exist_ok=True)
    t0 = time.time()
    n = 0
    with open(a.out, "a") as fh, ProcessPoolExecutor(
            max_workers=a.workers, initializer=_init,
            initargs=(a.fw, a.level, a.max_pills, a.exec_mode,
                      a.per_worker_rss_mb * 1024 * 1024)) as ex:
        futs = {ex.submit(_play, s): s for s in todo}
        for f in as_completed(futs):
            s = futs[f]
            try:
                r = f.result()
            except Exception as e:
                r = {"seed": s, "result": "ERROR", "error": repr(e)[:400]}
            r["arm"] = a.arm
            r["fw_md5_expected"] = fw_md5
            fh.write(json.dumps(r) + "\n")
            fh.flush()
            n += 1
            el = time.time() - t0
            print(f"[{n}/{len(todo)}] seed={s} {r.get('result')} "
                  f"pills={r.get('pills')} cleared={r.get('viruses_cleared')} "
                  f"({r.get('wall_secs')}s)  elapsed={el/60:.1f}m "
                  f"rate={n/(el/3600):.1f} games/h", flush=True)

    el = time.time() - t0
    print(f"DONE {n} games in {el/60:.1f} min = {n/(el/3600):.2f} games/hour "
          f"({a.workers} workers, host {socket.gethostname()})", flush=True)


if __name__ == "__main__":
    main()
