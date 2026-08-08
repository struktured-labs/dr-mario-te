#!/usr/bin/env python3
"""Positive control for the tuck quality gate: pick a THETA that MUST bind, predict
per board whether publication stops, then run it and check.

Every theta arm built so far (150 .. 20000, and -30000) left publication unmoved, which
was read as "the gate excludes nothing at any setting". gate_readout.py shows why: the
surviving tuck candidates score WIN-scale (D_V1 ~ 30000) against a base of a few
thousand, so a threshold of base+20000 is still far below them. NONE of those arms ever
put the threshold above the candidates -- so none of them tested whether the gate works.

The binding window is narrow and sits between two failure modes:

    base + theta > max_all      the gate should reject every candidate
    base + theta <= 32767       ... without the 16-bit add wrapping negative

Both bounds are per board, because `base` is. So this does not look for one theta that
binds everywhere -- it takes the theta given, computes for EACH board which of the three
regimes it lands in, and requires publication to match:

    wraps        -> threshold goes negative, gate admits everything -> UNCHANGED
    not binding  -> max_all still clears the threshold              -> UNCHANGED
    binding      -> every candidate is below the threshold          -> MUST STOP

A gate that works reproduces that pattern board for board. A gate that is bypassed
leaves publication unchanged in the binding rows too, and the disagreement names the
boards to disassemble.

Usage: gate_bind.py <readout.json> <hostdata.txt> --theta N [--out x.json]
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from cosim import Cosim, read_hostdata  # noqa: E402

BUILD = os.environ.get("COSIM_FARM_BUILD", os.path.join(HERE, "build"))
FARM_BIN = os.path.join(BUILD, "obj_farm", "farm_vsim")
PY = "/home/struktured/projects/dr_mario_rl/tmp/venv/bin/python"
FW = "/mnt/data/drmario_cosim/fw"

S20T3_ENV = {"DRCOPRO_TUCKBFS": "1", "DRCOPRO_TUCKBFS_TIER3": "1", "DRFIX": "1",
             "DRSTRAND": "20", "DRCHAIN": "180", "DRCOPRO_ARM": "1"}


def build_theta(theta):
    """Build the s20t3 arm at `theta`. THETA is emitted as a 16-bit literal, so a
    negative value must be handed over as its unsigned form."""
    name = f"s20t3_bind{theta}"
    out = os.path.join(FW, name, "copro_rom.hex")
    env = dict(os.environ, **S20T3_ENV)
    env["DRCOPRO_TUCKV3_THETA"] = str(theta & 0xFFFF)
    env["DRCOPRO_TUCKV3_DBGPUB"] = "0"          # normal publication behaviour
    subprocess.run([PY, os.path.join(HERE, "build_dbgpub.py"), out],
                   env=env, check=True, capture_output=True)
    return name, out


def predict(b, theta):
    """Regime for one board under `theta`, from its measured base/max_all."""
    if b["no_candidates"]:
        return "no_candidates"
    thr_true = b["base"] + theta
    if not -32768 <= thr_true <= 32767:
        return "wraps"
    return "binding" if b["max_all"] < thr_true else "not_binding"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("readout")
    ap.add_argument("hostdata")
    ap.add_argument("--theta", type=int, required=True)
    ap.add_argument("--out")
    a = ap.parse_args()

    ro = json.load(open(a.readout))
    boards = ro["boards"]
    cases = read_hostdata(a.hostdata)
    if len(cases) != len(boards):
        raise SystemExit(f"corpus/readout mismatch: {len(cases)} vs {len(boards)}")

    name, hexpath = build_theta(a.theta)
    fwdir = os.path.dirname(hexpath)
    print(f"built {name}: {a.theta} -> "
          f"{subprocess.run(['md5sum', hexpath], capture_output=True, text=True).stdout[:8]}")

    regimes = [predict(b, a.theta) for b in boards]
    n_bind = regimes.count("binding")
    print(f"predicted regimes: " + "  ".join(
        f"{r}={regimes.count(r)}" for r in ("binding", "not_binding", "wraps", "no_candidates")))
    if n_bind == 0:
        print("\nWARNING: this theta binds on ZERO boards -- it cannot test anything. "
              "Pick a theta inside some board's (max_all-base, 32767-base] window.")

    t0 = time.time()
    with Cosim(FARM_BIN, fwdir) as cs:
        md5 = cs.fw_md5
        rows = [cs.decide(c["board"], c["cA"], c["cB"], c["nA"], c["nB"]) for c in cases]
    print(f"ran {name} fw={md5[:8]} in {time.time()-t0:.0f}s")

    out_rows, n_ok, n_bad = [], 0, 0
    for b, reg, r in zip(boards, regimes, rows):
        pub_now = r["tcol"] != 0xFF
        expect = False if reg == "binding" else b["published"]
        ok = pub_now == expect
        n_ok += ok
        n_bad += (not ok)
        out_rows.append({"i": b["i"], "base": b["base"], "max_all": b["max_all"],
                         "regime": reg, "published_at_150": b["published"],
                         "published_now": pub_now, "expected": expect, "agrees": ok})

    verdict = ("GATE WORKS" if n_bad == 0 and n_bind > 0 else
               "GATE DOES NOT BIND" if n_bind > 0 else "INCONCLUSIVE (theta binds nowhere)")
    print(f"\n{'brd':>3} {'regime':>13} {'base':>7} {'maxall':>7} "
          f"{'pub@150':>8} {'pub@new':>8} {'expect':>7} {'ok':>4}")
    for r in out_rows:
        print(f"{r['i']:>3} {r['regime']:>13} {r['base']:>7} {r['max_all']:>7} "
              f"{str(r['published_at_150']):>8} {str(r['published_now']):>8} "
              f"{str(r['expected']):>7} {'.' if r['agrees'] else 'XX':>4}")
    print(f"\ntheta={a.theta}  binding boards={n_bind}  agree={n_ok}/{len(out_rows)}  "
          f"disagree={n_bad}\nVERDICT: {verdict}")

    if a.out:
        json.dump({"theta": a.theta, "fw_md5": md5, "arm": name,
                   "n_binding": n_bind, "n_agree": n_ok, "n_disagree": n_bad,
                   "verdict": verdict, "rows": out_rows}, open(a.out, "w"), indent=1)
        print(f"wrote {a.out}")


if __name__ == "__main__":
    main()
