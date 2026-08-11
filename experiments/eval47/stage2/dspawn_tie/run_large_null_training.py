#!/usr/bin/env python3
"""Run the frozen 1,200-seed mechanism-only null training block."""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

HERE = Path(__file__).resolve().parent
ORACLE = HERE.parent / "oracle"
for path in (str(HERE), str(ORACLE)):
    if path not in sys.path:
        sys.path.insert(0, path)

import calibrate_post_garbage_dspawn_v8 as C  # noqa: E402

SEEDS = range(71000, 72200)
OUTPUT = HERE / "out" / "post_garbage_large_null_training.json"
FORBIDDEN = {
    "res", "result", "won", "clear", "topout", "stall", "pills",
    "dies_ahead", "viruses_left", "t_to_end",
}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--workers", type=int, default=4)
    args = parser.parse_args()
    if not 1 <= args.workers <= 6:
        raise SystemExit("workers must be in 1..6")
    os.environ["DR_LULU_FIT"] = C.FIT
    t0 = time.monotonic()
    with ProcessPoolExecutor(max_workers=args.workers, initializer=C.init_worker) as ex:
        rows = list(ex.map(C.work, SEEDS))
    if [r.get("seed") for r in rows] != list(SEEDS):
        raise RuntimeError("ordered fit seed accounting failed")
    if any(FORBIDDEN & set(row) for row in rows):
        raise RuntimeError("endpoint field leaked into mechanism training")
    records = [z for row in rows for z in row["records"]]
    treatment = [r for r in records if r["kind"] == "treatment"]
    null = [r for r in records if r["kind"] == "null"]
    report = {
        "version": "post-garbage-large-null-training-v1",
        "endpoint_authority": False, "outcomes_retained": False,
        "seeds": [min(SEEDS), max(SEEDS)], "n_seeds": len(rows),
        "plies": sum(r["plies"] for r in rows),
        "active_plies": sum(r["active_plies"] for r in rows),
        "treatment_distinct": len(treatment), "null_opportunities": len(null),
        "per_seed_mechanism": rows,
        "seconds": round(time.monotonic() - t0, 2),
    }
    OUTPUT.write_text(json.dumps(report, indent=1) + "\n")
    print(json.dumps({k: v for k, v in report.items()
                      if k != "per_seed_mechanism"}, indent=1), flush=True)
    if len(treatment) < 500 or len(null) < len(treatment):
        raise SystemExit("NOT_TESTABLE_LARGE_TRAINING")


if __name__ == "__main__":
    main()
