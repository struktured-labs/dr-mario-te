#!/usr/bin/env python3
"""Resumable runner for the sealed N=9,000 post-garbage endpoint arm."""
from __future__ import annotations

import argparse
import hashlib
import importlib
import json
import os
import sys
import time
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

os.environ.setdefault("NUMBA_CACHE_DIR", "/tmp/dr-mario-te-numba-cache")
Path(os.environ["NUMBA_CACHE_DIR"]).mkdir(parents=True, exist_ok=True)

HERE = Path(__file__).resolve().parent
ORACLE = HERE.parent / "oracle"
for path in (str(HERE), str(ORACLE)):
    if path not in sys.path:
        sys.path.insert(0, path)

import oracle_arm as O  # noqa: E402
import post_garbage_dspawn_v8 as P  # noqa: E402

FIT = ("/home/struktured/projects/dr-mario-te/source/experiments/eval47/results/"
       "dr_lulu_20260808_fit.json")
TABLE = HERE / "out" / "post_garbage_large_stratified_null.json"
TABLE_SHA = "c64ce845e3e7d19242a359f868012bd04623c1bbee21d139202722f686e9c82d"
GATE = HERE / "out" / "post_garbage_endpoint_gate.json"
START, COUNT = 80000, 9000
_W = {}


def sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def manifest():
    O.init_rig("exo_lulu")
    names = (
        "post_garbage_dspawn_v8", "dspawn_tie_v8", "firmware_v8_policy",
        "oracle_arm", "pressure_rig", "p0_ab", "bursty_model",
        "exogenous_pressure", "cascade_chain_x", "cascade_link_x",
        "cascade_stranded_x", "fast_rtl_x", "fast_sim_x", "nes_pills",
        "drmario.faithful_env", "drmario.faithful_game",
    )
    files = {
        "runner": str(Path(__file__).resolve()), "fit": FIT,
        "prereg": str(HERE / "PREREG_POST_GARBAGE_V8_ENDPOINT.md"),
        "table": str(TABLE), "gate": str(GATE),
    }
    for name in names:
        files[name] = str(Path(importlib.import_module(name).__file__).resolve())
    docs = {name: {"path": path, "sha256": sha256(path)}
            for name, path in files.items()}
    rolled = hashlib.sha256("".join(
        f"{name}:{doc['sha256']}" for name, doc in sorted(docs.items()))
        .encode()).hexdigest()
    return {"rolled": rolled, "files": docs, "python": sys.version.split()[0]}


def load_cutoffs():
    if sha256(TABLE) != TABLE_SHA:
        raise RuntimeError("frozen stratified-null table hash mismatch")
    doc = json.loads(TABLE.read_text())
    if [row["cell"] for row in doc["cells"]] != list(range(40)):
        raise RuntimeError("frozen table cell accounting mismatch")
    return [int(row["cutoff_u64"]) for row in doc["cells"]]


def init_worker(cutoffs):
    os.environ["DR_LULU_FIT"] = FIT
    C, model = O.init_rig("exo_lulu")
    _W.update(C=C, model=model, cutoffs=tuple(cutoffs))


def work(seed):
    out = {}
    for name in ("base", "treatment", "null"):
        arm = P.PostGarbageArm(
            name, provenance=True,
            cell_cutoffs=_W["cutoffs"] if name == "null" else None)
        row = P.play_one(seed, arm, _W["C"], _W["model"])
        row.pop("_actions", None)
        row.pop("calibration_log", None)
        out[name] = row
    return {"seed": int(seed), **out}


def require_gate():
    if not GATE.exists():
        raise RuntimeError("run gate_post_garbage_endpoint.py first")
    gate = json.loads(GATE.read_text())
    if not gate.get("pass") or gate.get("prereg_commit") != "85d7898":
        raise RuntimeError("sealed endpoint gate did not pass")
    if gate.get("table_sha256") != TABLE_SHA:
        raise RuntimeError("endpoint gate used a different table")
    expected_sources = {
        "post_garbage_dspawn_v8": sha256(P.__file__),
        "endpoint_runner": sha256(__file__),
        "endpoint_gate": sha256(HERE / "gate_post_garbage_endpoint.py"),
        "endpoint_analyzer": sha256(HERE / "analyze_post_garbage_v8_endpoint.py"),
    }
    if gate.get("source_sha256") != expected_sources:
        raise RuntimeError("endpoint gate is stale for current runtime sources")
    return sha256(GATE)


def load_rows(outdir):
    rows = {}
    for path in sorted(Path(outdir).glob("seg_*.jsonl")):
        for lineno, line in enumerate(path.open(), 1):
            try:
                row = json.loads(line)
            except Exception as exc:
                raise RuntimeError(f"{path.name}:{lineno}: malformed JSON: {exc}")
            seed = int(row["seed"])
            if seed in rows:
                raise RuntimeError(f"duplicate endpoint seed {seed}")
            rows[seed] = row
    return rows


def summary(rows):
    out = {"n_pairs": len(rows)}
    for arm in ("base", "treatment", "null"):
        out[arm] = {key: sum(int(r[arm][key]) for r in rows)
                    for key in ("won", "topout", "stall", "dies_ahead",
                                "raw_action_flips")}
        out[arm]["plies"] = sum(int(r[arm]["plies"]) for r in rows)
        out[arm]["active_plies"] = sum(int(r[arm]["active_plies"]) for r in rows)
    return out


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--workers", type=int, default=4)
    parser.add_argument("--segment", type=int, default=250)
    parser.add_argument("--outdir", default=str(HERE / "out" / "post_garbage_endpoint" / "evaluation"))
    args = parser.parse_args()
    if not 1 <= args.workers <= 6 or args.segment <= 0:
        raise SystemExit("workers must be 1..6 and segment positive")
    os.environ["DR_LULU_FIT"] = FIT
    cutoffs, gate_sha = load_cutoffs(), require_gate()
    outdir = Path(args.outdir); outdir.mkdir(parents=True, exist_ok=True)
    meta = {
        "version": "post-garbage-v8-endpoint-v1",
        "prereg_commit": "85d7898", "table_sha256": TABLE_SHA,
        "gate_sha256": gate_sha,
        "policy_semantics": "firmware_v8/p2_surrogate",
        "pressure": "exo_lulu", "seeds": [START, START + COUNT - 1],
        "n_seeds": COUNT, "segment": args.segment,
        "runtime_manifest": manifest(),
    }
    meta_path = outdir / "META.json"
    if meta_path.exists() and json.loads(meta_path.read_text()) != meta:
        raise RuntimeError("refusing resume under changed endpoint META")
    if not meta_path.exists():
        meta_path.write_text(json.dumps(meta, indent=1) + "\n")
    done = load_rows(outdir)
    seeds = list(range(START, START + COUNT)); todo = set(seeds) - set(done)
    print(f"endpoint pairs={COUNT} done={len(done)} todo={len(todo)} "
          f"workers={args.workers} manifest={meta['runtime_manifest']['rolled']}", flush=True)
    with ProcessPoolExecutor(max_workers=args.workers, initializer=init_worker,
                             initargs=(cutoffs,)) as ex:
        for offset in range(0, COUNT, args.segment):
            block_all = seeds[offset:offset + args.segment]
            block = [seed for seed in block_all if seed in todo]
            if not block:
                continue
            tag = f"seg_{block_all[0]:06d}"; path = outdir / f"{tag}.jsonl"
            t0 = time.monotonic()
            with path.open("a") as fh:
                for i, row in enumerate(ex.map(work, block), 1):
                    fh.write(json.dumps(row) + "\n"); fh.flush()
                    if i % 25 == 0:
                        print(f"{tag} {i}/{len(block)} "
                              f"{(time.monotonic()-t0)/60:.1f}min", flush=True)
            complete = load_rows(outdir)
            rows = [complete[seed] for seed in block_all if seed in complete]
            report = {"tag": tag, **summary(rows)}
            (outdir / f"{tag}.summary.json").write_text(
                json.dumps(report, indent=1) + "\n")
            print("SEGMENT " + json.dumps(report), flush=True)


if __name__ == "__main__":
    main()
