#!/usr/bin/env python3
"""dump_payload.py -- dump the EXACT bytes exactness_gate.py hashes, so a hash
mismatch can be localised to a field instead of guessed at."""
import sys
import json
import hashlib
import argparse

QA = "/home/struktured/projects/dr-mario-qa-wt/experiments"
sys.path.insert(0, QA + "/adversary")
sys.path.insert(0, QA + "/../experiments/hetzner")
import adversary_harness as AH  # noqa: E402

ap = argparse.ArgumentParser()
ap.add_argument("seed", type=int)
ap.add_argument("--out", required=True)
a = ap.parse_args()

r = AH.play_seed(a.seed)
payload = {
    "seed": r["seed"],
    "result": r["result"],
    "pills": r["pills"],
    "viruses_left": r["viruses_left"],
    "dies_ahead": r["dies_ahead"],
    "garbage_injected": r["garbage_injected"],
    "trace": [[int(i), int(x)] for i, x in r["trace"]],
    "board": r["first_topout_board"],
}
blob = json.dumps(payload, sort_keys=True, separators=(",", ":"))
print("sha256      :", hashlib.sha256(blob.encode()).hexdigest())
print("blob length :", len(blob))
print("board is None:", r["first_topout_board"] is None)
print("types       :", {k: type(v).__name__ for k, v in payload.items()})
with open(a.out, "w") as f:
    f.write(blob)
print("wrote", a.out)
