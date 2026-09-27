#!/usr/bin/env python3
"""Killed-mutant gate for balanced-prefix banking and resume summaries."""
from __future__ import annotations

import inspect
import json
import os
import sys
import tempfile
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

import run_oracle as R


def delayed(seed):
    # Completion order is deliberately reverse-ish from registered order.
    time.sleep((4 - seed) * 0.01)
    return seed


def main():
    seeds = [1, 2, 3]
    with ThreadPoolExecutor(max_workers=3) as ex:
        ordered = list(ex.map(delayed, seeds))
    with ThreadPoolExecutor(max_workers=3) as ex:
        futures = [ex.submit(delayed, seed) for seed in seeds]
        mutant = [f.result() for f in as_completed(futures)]

    source = inspect.getsource(R.main)
    runner_uses_ordered_map = "ex.map(_work, block)" in source
    old_mutant_breaks_prefix = mutant != seeds

    with tempfile.TemporaryDirectory() as td:
        path = os.path.join(td, "seg.jsonl")
        with open(path, "w") as fh:
            for row in ({"seed": 3, "value": "three"},
                        {"seed": 1, "value": "first"},
                        {"seed": 1, "value": "duplicate"},
                        {"seed": 2, "value": "two"}):
                fh.write(json.dumps(row) + "\n")
        loaded = R._load_segment(path)
    resume_summary_input_ok = ([r["seed"] for r in loaded] == seeds
                               and loaded[0]["value"] == "first")

    checks = {
        "executor_map_yields_registered_order": ordered == seeds,
        "runner_calls_ordered_map": runner_uses_ordered_map,
        "as_completed_mutant_breaks_prefix": old_mutant_breaks_prefix,
        "resume_loads_full_deduped_sorted_segment": resume_summary_input_ok,
    }
    for name, value in checks.items():
        print(f"  {name:46s} {value}")
    ok = all(checks.values())
    print("RUNNER BANKING MUTATION GATE:", "PASS" if ok else "FAIL")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
