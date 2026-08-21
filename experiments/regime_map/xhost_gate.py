#!/usr/bin/env python3
"""Cross-host bit-exactness gate for the c5 precision extension (hetzfarm-143).

Plays the two registered instrument seeds (33000, 33002) under the FULL c5
config on THIS host and writes {seed: sha256(canonical_row)}. Canonical row =
the row dict with host-varying keys removed ({wall_secs, host}), serialized
with sorted keys. Pooling with the local c5 rows is allowed ONLY if both
hashes match across hosts (PREREG_C5_PRECISION_EXT.md sec 6).

  xhost_gate.py --fw <dir> --out xhost_<host>.json
  xhost_gate.py --compare a.json b.json      # exits nonzero on any mismatch
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import socket
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
FARM = os.path.normpath(os.path.join(HERE, "..", "cosim_farm"))
RL = "/home/struktured/projects/dr_mario_rl"
QA = "/home/struktured/projects/dr-mario-qa-wt/experiments"
for _p in (HERE, FARM, RL + "/.claude/worktrees/faithful-sim/src", QA, QA + "/eval47"):
    if _p not in sys.path:
        sys.path.insert(0, _p)

SEEDS = (33000, 33002)          # registered instrument seeds, outside all blocks
LEVEL, MAX_PILLS, VARIANT = 20, 400, "bursty"
STRIP = ("wall_secs", "host")


def canonical_hash(row):
    r = {k: v for k, v in row.items() if k not in STRIP}
    blob = json.dumps(r, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(blob.encode()).hexdigest()


def run(fw, out):
    import game as G
    from cosim import Cosim
    from regime_pressure import wrap_model
    import run_bursty_v1_1_validity as V11
    base = V11.build_v1_1()
    base.meta = {k: v for k, v in base.meta.items() if k != "raw_events"}
    model, pressure = wrap_model(base, VARIANT)
    bin_path = os.path.join(os.environ.get("COSIM_FARM_BUILD",
                                           os.path.join(FARM, "build")),
                            "obj_farm", "farm_vsim")
    res = {"host": socket.gethostname(),
           "farm_vsim_md5": hashlib.md5(open(bin_path, "rb").read()).hexdigest(),
           "hashes": {}, "results": {}}
    with Cosim(bin_path, fw) as cs:
        for s in SEEDS:
            r = G.play_game(cs, seed=s, level=LEVEL, max_pills=MAX_PILLS,
                            exec_mode="drop", pressure=pressure, model=model,
                            trace=True)
            res["hashes"][str(s)] = canonical_hash(r)
            res["results"][str(s)] = {"result": r.get("result"),
                                      "pills": r.get("pills"),
                                      "garbage": r.get("garbage"),
                                      "fw_md5": r.get("fw_md5")}
            print(f"seed {s}: {r.get('result')} pills={r.get('pills')} "
                  f"hash={res['hashes'][str(s)][:16]}", flush=True)
    with open(out, "w") as f:
        json.dump(res, f, indent=1)
    print("XHOST_RUN_OK", flush=True)


def compare(a_path, b_path):
    a, b = json.load(open(a_path)), json.load(open(b_path))
    ok = True
    if a["farm_vsim_md5"] != b["farm_vsim_md5"]:
        print(f"BINARY MISMATCH: {a['farm_vsim_md5']} vs {b['farm_vsim_md5']}")
        ok = False
    for s in map(str, SEEDS):
        ha, hb = a["hashes"].get(s), b["hashes"].get(s)
        same = ha is not None and ha == hb
        print(f"seed {s}: {a['host']}={str(ha)[:16]} {b['host']}={str(hb)[:16]} "
              f"{'MATCH' if same else 'MISMATCH'}")
        ok = ok and same
    print("XHOST_GATE_" + ("PASS" if ok else "FAIL"))
    sys.exit(0 if ok else 1)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--fw")
    ap.add_argument("--out")
    ap.add_argument("--compare", nargs=2)
    a = ap.parse_args()
    if a.compare:
        compare(*a.compare)
    else:
        if not (a.fw and a.out):
            ap.error("--fw and --out required to run")
        run(a.fw, a.out)


if __name__ == "__main__":
    main()
