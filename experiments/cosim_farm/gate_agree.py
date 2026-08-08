#!/usr/bin/env python3
"""VALIDATION GATE (b): the farm server must reproduce the STOCK co-sim's decisions.

The farm wraps the co-sim; it must not change it. This runs the same hostdata.txt corpus
through both binaries and requires bit-identical (col, orient) AND identical clocks= on
every board. Comparing clocks too is deliberate: a move can coincidentally match while
the search took a different path, and clocks is the project's own most diagnostic field
(run_gate.sh's header says so).

The two binaries differ in transport (file vs pipe), in lifetime (the farm holds one
instance across a whole game), and in C++ optimisation level (-O2 vs Verilator's default
-Os). Agreement here is what licenses all three.

Usage: gate_agree.py <fw_dir> <hostdata.txt> [--out result.json]
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
STOCK_BIN = os.path.join(BUILD, "obj_mister", "mister_vsim")


def run_stock(fw_dir, hostdata):
    """Run the stock one-shot binary, which reads ./hostdata.txt from its CWD."""
    dst = os.path.join(fw_dir, "hostdata.txt")
    if os.path.abspath(hostdata) != os.path.abspath(dst):
        with open(hostdata) as fh, open(dst, "w") as out:
            out.write(fh.read())
    t0 = time.time()
    proc = subprocess.run([STOCK_BIN], cwd=fw_dir, capture_output=True, text=True)
    elapsed = time.time() - t0
    rows = []
    for ln in proc.stdout.splitlines():
        if not ln.startswith("case "):
            continue
        # case K: copro=(C,O) oracle=(..,..) clocks=N (...) ok|MISMATCH
        copro = ln.split("copro=(")[1].split(")")[0]
        col, o4 = (int(x) for x in copro.split(","))
        clocks = int(ln.split("clocks=")[1].split()[0])
        rows.append({"col": col, "o4": o4, "clocks": clocks})
    return rows, elapsed


def run_farm(fw_dir, cases):
    t0 = time.time()
    rows = []
    with Cosim(FARM_BIN, fw_dir) as cs:
        fw_md5 = cs.fw_md5
        for c in cases:
            r = cs.decide(c["board"], c["cA"], c["cB"], c["nA"], c["nB"])
            rows.append(r)
    return rows, time.time() - t0, fw_md5


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("fw_dir")
    ap.add_argument("hostdata")
    ap.add_argument("--out")
    a = ap.parse_args()

    cases = read_hostdata(a.hostdata)
    print(f"corpus: {len(cases)} boards from {a.hostdata}", flush=True)

    farm, t_farm, fw_md5 = run_farm(a.fw_dir, cases)
    print(f"farm  : {t_farm:7.1f}s  ({t_farm/len(cases):.1f}s/decision)  fw={fw_md5}",
          flush=True)
    stock, t_stock = run_stock(a.fw_dir, a.hostdata)
    print(f"stock : {t_stock:7.1f}s  ({t_stock/max(1,len(stock)):.1f}s/decision)",
          flush=True)

    if len(stock) != len(cases):
        print(f"GATE FAIL: stock produced {len(stock)} rows for {len(cases)} boards")
        return 1

    bad = []
    for k, (f, s) in enumerate(zip(farm, stock)):
        if (f["col"], f["o4"], f["clocks"]) != (s["col"], s["o4"], s["clocks"]):
            bad.append({"case": k, "farm": f, "stock": s})

    n_tuck = sum(1 for f in farm if f["tcol"] != 0xFF)
    print(f"tuck descriptor published on {n_tuck}/{len(farm)} boards")

    res = {"gate": "agreement_farm_vs_stock", "fw_md5": fw_md5,
           "fw_dir": a.fw_dir, "hostdata": a.hostdata, "n": len(cases),
           "n_mismatch": len(bad), "mismatches": bad[:20],
           "n_tuck_published": n_tuck,
           "secs_per_decision_farm": t_farm / len(cases),
           "secs_per_decision_stock": t_stock / max(1, len(stock)),
           "speedup_farm_over_stock": t_stock / t_farm if t_farm else None,
           "farm_rows": farm, "stock_rows": stock}
    if a.out:
        os.makedirs(os.path.dirname(a.out), exist_ok=True)
        json.dump(res, open(a.out, "w"), indent=1)
        print(f"wrote {a.out}")

    if bad:
        print(f"GATE FAIL: {len(bad)}/{len(cases)} decisions differ")
        for m in bad[:5]:
            print("  ", m)
        return 1
    print(f"GATE PASS: farm == stock on {len(cases)}/{len(cases)} decisions "
          f"(col, orient AND clocks all identical)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
