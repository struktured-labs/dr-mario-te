#!/usr/bin/env python3
"""run_autopsy.py — label the backward scan of every clean census failure.

Per-seed atomic and resumable (one .json.gz per seed, written via a tmp file
+ rename), so a kill at any moment loses at most one seed.  Consumes the
census JSONL as a STREAM: whatever failures exist when a worker picks up work
get labeled, and coverage is reported from the census's own progress file.

Registered by PREREG_AUTOPSY §4 (scan rule) and AMENDMENT A1 (dose).
"""
from __future__ import annotations

import argparse
import gzip
import json
import os
import sys
import time
from concurrent.futures import ProcessPoolExecutor, as_completed

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import autopsycore as AC   # noqa: E402

OUT = os.path.join(HERE, "out")
LABELS = os.path.join(OUT, "labels")
CENSUS = os.path.join(OUT, "census", "census.jsonl")


def scan_offsets():
    """§4: k = 1..8 every ply, 10..24 every 2, 28..48 every 4."""
    ks = list(range(1, 9)) + list(range(10, 25, 2)) + list(range(28, 49, 4))
    return sorted(set(ks))


def failure_rows(path=CENSUS):
    """Every non-clear, non-degenerate census row, ascending seed."""
    out = []
    if not os.path.exists(path):
        return out
    with open(path) as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                r = json.loads(line)
            except json.JSONDecodeError:
                continue          # torn tail
            if r.get("result") in ("topout", "stall"):
                out.append(r)
    out.sort(key=lambda r: r["seed"])
    return out


def _anchor_and_virus_trace(seed, C, row):
    """Replay once (gated) to get per-ply virus counts and the anchor ply.

    anchor = death ply for topouts; for stalls the LAST ply at which the virus
    count changed (§4 — the flat tail of a stalled game buys nothing).
    """
    vir = []
    sink = {}
    for ply, env, _vals, _a in AC.replay_census_game(seed, C, row, sink=sink):
        vir.append(int(env.board.virus_count()))
    if row["result"] == "topout":
        return row["n_moves"] - 1, vir, sink
    last_change = 0
    for i in range(1, len(vir)):
        if vir[i] != vir[i - 1]:
            last_change = i
    return last_change, vir, sink


def label_seed(seed):
    """Whole-seed unit.  Returns (seed, n_states, elapsed) or raises."""
    import adversary_harness as AH
    AH._lazy()
    C, _b = AC.init_rig()
    t0 = time.time()
    row = _ROWS[seed]
    anchor, vir, term = _anchor_and_virus_trace(seed, C, row)
    want = sorted({anchor - k for k in scan_offsets() if anchor - k >= 0})
    stall = (row["result"] == "stall")
    H = AC.H_STALL if stall else AC.H_TOPOUT

    states = []
    for ply, env, vals, a in AC.replay_census_game(seed, C, row,
                                                   want_plies=set(want)):
        ents = AC.label_state(env, C, seed, ply, H, clair=True, swap=True,
                              extend_cap=stall)
        cl = (AC.claim_stall if stall else AC.claim_topout)(ents, a, vals)
        states.append({
            "ply": ply, "k": anchor - ply, "a_champ": int(a),
            "vir_here": vir[ply],
            "vals": [None if not (v == v) else round(float(v), 6) for v in vals],
            "cands": ents,
            "claim": cl,
        })

    doc = {"seed": seed, "result": row["result"], "pills": row["pills"],
           "viruses_left": row["viruses_left"], "dies_ahead": row["dies_ahead"],
           "n_moves": row["n_moves"], "anchor": anchor,
           "scan_k": scan_offsets(), "plies_scanned": want,
           "plies_available": row["n_moves"], "H": H,
           "n_samples": AC.N_SAMPLES, "terminal": term, "states": states,
           "elapsed_s": round(time.time() - t0, 1)}

    tmp = os.path.join(LABELS, f".tmp_{seed}.json.gz")
    dst = os.path.join(LABELS, f"autopsy_{seed}.json.gz")
    with gzip.open(tmp, "wt") as f:
        json.dump(doc, f, separators=(",", ":"))
    os.replace(tmp, dst)                       # atomic
    return seed, len(states), doc["elapsed_s"]


_ROWS = {}


def _init(rows):
    global _ROWS
    _ROWS = rows
    import adversary_harness as AH
    AH._lazy()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--workers", type=int, default=4)
    ap.add_argument("--limit", type=int, default=0)
    a = ap.parse_args()
    os.makedirs(LABELS, exist_ok=True)

    rows = {r["seed"]: r for r in failure_rows()}
    done = {int(f.split("_")[1].split(".")[0])
            for f in os.listdir(LABELS) if f.startswith("autopsy_")}
    todo = sorted(s for s in rows if s not in done)
    if a.limit:
        todo = todo[:a.limit]

    # STARTUP ASSERTS (registered discipline): the gates must be green and the
    # work list must be exactly the failures the census has found so far.
    gpath = os.path.join(OUT, "gate_autopsy.json")
    assert os.path.exists(gpath), "gate_autopsy.json missing — gates not run"
    g = json.load(open(gpath))
    for k in ("G1", "G2", "G3", "G4", "G5"):
        assert g[k]["pass"], f"gate {k} not green"
    assert all(rows[s]["result"] in ("topout", "stall") for s in todo)
    print(f"[autopsy] gates green; {len(rows)} failures known, {len(done)} done, "
          f"{len(todo)} to label, {a.workers} workers", flush=True)
    if not todo:
        print("AUTOPSY_IDLE (no new failures)", flush=True)
        return

    t0 = time.time()
    n = 0
    with ProcessPoolExecutor(max_workers=a.workers,
                             initializer=_init, initargs=(rows,)) as ex:
        futs = {ex.submit(label_seed, s): s for s in todo}
        for fut in as_completed(futs):
            seed = futs[fut]
            try:
                s, nst, el = fut.result()
            except Exception as exc:                      # noqa: BLE001
                print(f"[autopsy] seed {seed} FAILED: {type(exc).__name__}: "
                      f"{str(exc)[:200]}", flush=True)
                continue
            n += 1
            el_tot = time.time() - t0
            print(f"[autopsy] {n}/{len(todo)} seed {s} ({rows[s]['result']}) "
                  f"{nst} states in {el:.0f}s  |  wall {el_tot / 60:.1f}m",
                  flush=True)
    print(f"AUTOPSY_OK labeled={n}/{len(todo)}", flush=True)


if __name__ == "__main__":
    main()
