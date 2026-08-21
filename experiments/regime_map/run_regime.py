#!/usr/bin/env python3
"""Failure-regime map farm driver (regime-141).

A thin adaptation of experiments/cosim_farm/run_farm.py: same worker model (one
long-lived verilated co-sim per worker), same per-seed atomic JSONL rows, same
banked-seed resume, same code manifest. Differences, all registered in
PREREG_REGIME_MAP.md:

  * --pressure takes the regime_pressure.VARIANTS set (clean / bursty /
    bursty_x2 / bursty_aim). game.py still sees only "clean"/"bursty"; the
    variant lives in the MODEL wrapper (regime_pressure.wrap_model), so the
    injector's draw and game.py's verification re-sample stay coherent.
  * every row records pressure_model = the VARIANT name (not just "bursty").
  * seeds are EVEN ONLY (seed low bit is dead — dr-mario-seed-space-is-32767);
    the driver refuses odd seeds rather than silently burning duplicates.

Component per measurement (rule 10): every placement decision is the REAL RTL —
verilated CoproDrMario (farm_vsim), champion firmware s20b — via the committed
co-sim farm. Game state, pill stream, and garbage injection are the faithful
Python env, as in every prior farm result.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import resource
import socket
import sys
import time
from concurrent.futures import ProcessPoolExecutor, as_completed

HERE = os.path.dirname(os.path.abspath(__file__))
FARM = os.path.normpath(os.path.join(HERE, "..", "cosim_farm"))
RL = "/home/struktured/projects/dr_mario_rl"
QA = "/home/struktured/projects/dr-mario-qa-wt/experiments"
QA47 = QA + "/eval47"
for _p in (HERE, FARM, RL + "/.claude/worktrees/faithful-sim/src", QA, QA47):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from regime_pressure import VARIANTS, wrap_model  # noqa: E402

BUILD = os.environ.get("COSIM_FARM_BUILD", os.path.join(FARM, "build"))
FARM_BIN = os.path.join(BUILD, "obj_farm", "farm_vsim")

_W = {}


def _build_base_model():
    """bursty v1.1 (NOT v1 — the contaminated pool), meta-stripped after build."""
    import run_bursty_v1_1_validity as V11
    m = V11.build_v1_1()
    m.meta = {k: v for k, v in m.meta.items() if k != "raw_events"}
    return m


def _init(fw_dir, level, max_pills, exec_mode, mem_cap_bytes, variant):
    if mem_cap_bytes:
        resource.setrlimit(resource.RLIMIT_AS, (mem_cap_bytes, mem_cap_bytes))
    import game as G
    from cosim import Cosim
    _W["G"] = G
    _W["cosim"] = Cosim(FARM_BIN, fw_dir)
    _W["level"] = level
    _W["max_pills"] = max_pills
    _W["exec_mode"] = exec_mode
    _W["variant"] = variant
    base = _build_base_model() if variant != "clean" else None
    _W["model"], _W["pressure"] = wrap_model(base, variant)


def _play(seed):
    G = _W["G"]
    t0 = time.time()
    # trace=True: failure autopsies need the move list; ~10KB/row is cheap.
    r = G.play_game(_W["cosim"], seed=seed, level=_W["level"],
                    max_pills=_W["max_pills"], exec_mode=_W["exec_mode"],
                    pressure=_W["pressure"], model=_W["model"], trace=True)
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
    ap.add_argument("--arm", required=True, help="cell label recorded in the JSONL")
    ap.add_argument("--fw", required=True, help="dir holding this arm's copro_rom.hex")
    ap.add_argument("--out", required=True)
    ap.add_argument("--seed-start", type=int, required=True)
    ap.add_argument("--seed-count", type=int, required=True,
                    help="number of EVEN seeds to play starting at --seed-start "
                         "(stride 2: start, start+2, ...)")
    ap.add_argument("--workers", type=int, default=22)
    ap.add_argument("--level", type=int, default=11)
    ap.add_argument("--max-pills", type=int, default=300)
    ap.add_argument("--exec-mode", default="drop", choices=["drop", "tuck"])
    ap.add_argument("--pressure", required=True, choices=list(VARIANTS))
    ap.add_argument("--per-worker-rss-mb", type=int, default=2048)
    a = ap.parse_args()

    if a.seed_start % 2:
        raise SystemExit("--seed-start must be EVEN (seed low bit is dead; odd "
                         "seeds duplicate their even neighbour's capsule stream)")
    seeds = [a.seed_start + 2 * i for i in range(a.seed_count)]
    done = load_done(a.out, a.arm)
    todo = [s for s in seeds if s not in done]

    def _md5(p):
        return hashlib.md5(open(p, "rb").read()).hexdigest()

    fw_md5 = _md5(os.path.join(a.fw, "copro_rom.hex"))
    manifest = {"farm_vsim": _md5(FARM_BIN), "copro_rom_hex": fw_md5,
                "regime_pressure.py": _md5(os.path.join(HERE, "regime_pressure.py")),
                "run_regime.py": _md5(os.path.abspath(__file__))}
    for _src in ("game.py", "cosim.py"):
        manifest[_src] = _md5(os.path.join(FARM, _src))
    manifest["rolled"] = hashlib.sha256(
        "".join(f"{k}={manifest[k]}" for k in sorted(manifest)).encode()).hexdigest()[:16]
    print("code manifest: " + "  ".join(f"{k}={v[:8]}" for k, v in manifest.items()),
          flush=True)
    print(f"arm={a.arm} fw={fw_md5} exec={a.exec_mode} pressure={a.pressure} "
          f"level={a.level} max_pills={a.max_pills} seeds {seeds[0]}..{seeds[-1]} "
          f"stride2 ({len(todo)} to run, {len(done)} already done) "
          f"workers={a.workers} host={socket.gethostname()}", flush=True)

    os.makedirs(os.path.dirname(a.out), exist_ok=True)
    t0 = time.time()
    n = 0
    with open(a.out, "a") as fh, ProcessPoolExecutor(
            max_workers=a.workers, initializer=_init,
            initargs=(a.fw, a.level, a.max_pills, a.exec_mode,
                      a.per_worker_rss_mb * 1024 * 1024, a.pressure)) as ex:
        futs = {ex.submit(_play, s): s for s in todo}
        for f in as_completed(futs):
            s = futs[f]
            try:
                r = f.result()
            except Exception as e:
                r = {"seed": s, "result": "ERROR", "error": repr(e)[:400]}
            r["arm"] = a.arm
            r["fw_md5_expected"] = fw_md5
            r["manifest"] = manifest["rolled"]
            r["bin_md5"] = manifest["farm_vsim"]
            r["pressure_model"] = a.pressure
            r["max_pills_cap"] = a.max_pills
            fh.write(json.dumps(r) + "\n")
            fh.flush()
            n += 1
            el = time.time() - t0
            print(f"[{n}/{len(todo)}] seed={s} {r.get('result')} "
                  f"pills={r.get('pills')} cleared={r.get('viruses_cleared')} "
                  f"garbage={r.get('garbage')} ({r.get('wall_secs')}s) "
                  f"elapsed={el/60:.1f}m rate={n/(el/3600):.1f} games/h", flush=True)

    el = time.time() - t0
    print(f"DONE arm={a.arm} {n} games in {el/60:.1f} min = "
          f"{n/(el/3600):.2f} games/hour ({a.workers} workers)", flush=True)
    print("RUN_REGIME_OK", flush=True)


if __name__ == "__main__":
    main()
