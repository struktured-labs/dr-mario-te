#!/usr/bin/env python3
"""Read the tuck quality gate's own two operands off the RTL, per board.

The gate in tuck_v3.py's tre_loop is:

    skip this candidate unless   D_V1 >= TK2_BBV + THETA        (16-bit signed)
    then commit it     unless    D_V1 <= D_BV                   (running best)

Both operands live in copro zero page, invisible from outside, so the measured
invariant "publication does not move for THETA in {150 .. 20000} nor at -30000, on
two corpora" has several mechanisms that look identical from the mailbox. This reads
the operands directly, using two debug firmwares that repurpose the four readback
bytes (see tuck_v3.DBGPUB):

    ctl0  DBGPUB=0  the shipped image -- gives the per-board PUBLISH decision
    pub1  DBGPUB=1  $5085/86 = TK2_BBV,  $5087/88 = D_BV at exit
    pub2  DBGPUB=2  $5085/86 = TK2_BBV,  $5087/88 = max D_V1 over ALL candidates,
                                          taken BEFORE the gate

With those three, each board yields the actual margin the gate was asked to judge,
and the arithmetic can be replayed in Python against what the silicon really did.

Usage: gate_readout.py <hostdata.txt> [--out x.json] [--fw-root DIR]
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
from concurrent.futures import ThreadPoolExecutor

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from cosim import Cosim, read_hostdata  # noqa: E402

BUILD = os.environ.get("COSIM_FARM_BUILD", os.path.join(HERE, "build"))
FARM_BIN = os.path.join(BUILD, "obj_farm", "farm_vsim")

THETAS = (150, 250, 400, 600, 5000, 20000, -30000)   # every theta arm built so far


def s16(lo, hi):
    v = (hi << 8) | lo
    return v - 0x10000 if v & 0x8000 else v


def add16(a, b):
    """The firmware's own 16-bit add: ADC lo / ADC hi, no overflow check."""
    v = (a + b) & 0xFFFF
    return v - 0x10000 if v & 0x8000 else v


def run_arm(fw_dir, cases, label):
    rows = []
    t0 = time.time()
    with Cosim(FARM_BIN, fw_dir) as cs:
        md5 = cs.fw_md5
        for c in cases:
            rows.append(cs.decide(c["board"], c["cA"], c["cB"], c["nA"], c["nB"]))
    print(f"  {label}: fw={md5[:8]} {time.time()-t0:.0f}s", flush=True)
    return rows, md5


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("hostdata")
    ap.add_argument("--out")
    ap.add_argument("--fw-root", default="/mnt/data/drmario_cosim/fw")
    a = ap.parse_args()

    cases = read_hostdata(a.hostdata)
    n = len(cases)
    arms = {k: os.path.join(a.fw_root, v)
            for k, v in (("ctl0", "dbg_ctl0"), ("pub1", "dbg_pub1"), ("pub2", "dbg_pub2"))}

    # Three co-sims in parallel -- the cap the 2x2 leaves room for, and they are
    # independent processes, so this is 1 wall-clock arm rather than 3.
    with ThreadPoolExecutor(max_workers=3) as ex:
        futs = {k: ex.submit(run_arm, d, cases, k) for k, d in arms.items()}
        res = {k: f.result() for k, f in futs.items()}

    ctl, pub1, pub2 = res["ctl0"][0], res["pub1"][0], res["pub2"][0]
    boards = []
    for i in range(n):
        base1 = s16(pub1[i]["col"], pub1[i]["o4"])
        base2 = s16(pub2[i]["col"], pub2[i]["o4"])
        boards.append({
            "i": i,
            "published": ctl[i]["tcol"] != 0xFF,
            "ctl_col": ctl[i]["col"], "ctl_orient": ctl[i]["o4"],
            "base": base1,
            "base_agrees": base1 == base2,
            "best_final": s16(pub1[i]["tcol"], pub1[i]["trow"]),
            "max_all": s16(pub2[i]["tcol"], pub2[i]["trow"]),
        })

    # ---- consistency gates. A violation means the readout itself is wrong, and the
    # margins below must not be interpreted until it is explained.
    checks = {
        "base_agrees_across_builds": all(b["base_agrees"] for b in boards),
        "best_final_ge_base": all(b["best_final"] >= b["base"] for b in boards),
        "max_all_ge_best_final_when_committed":
            all(b["max_all"] >= b["best_final"]
                for b in boards if b["best_final"] > b["base"]),
        "publish_iff_best_final_gt_base":
            all(b["published"] == (b["best_final"] > b["base"]) for b in boards),
    }

    for b in boards:
        b["no_candidates"] = b["max_all"] == -32768        # running max never updated
        b["margin_best"] = b["best_final"] - b["base"]     # committed winner's margin
        b["margin_max"] = (None if b["no_candidates"] else b["max_all"] - b["base"])
        # Replay the gate for every theta ever built, in the firmware's own arithmetic.
        b["gate"] = {}
        for th in THETAS:
            thr = add16(b["base"], th)                     # what the 6502 computes
            true_thr = b["base"] + th                      # what it would compute in 32-bit
            b["gate"][str(th)] = {
                "wraps": thr != true_thr,
                "max_all_passes_actual": (None if b["no_candidates"] else b["max_all"] >= thr),
                "max_all_passes_true": (None if b["no_candidates"] else b["max_all"] >= true_thr),
            }

    out = {
        "hostdata": a.hostdata, "n_boards": n,
        "fw_md5": {k: res[k][1] for k in arms},
        "checks": checks,
        "boards": boards,
    }
    if a.out:
        with open(a.out, "w") as f:
            json.dump(out, f, indent=1)

    print(f"\n=== consistency ===")
    for k, v in checks.items():
        print(f"  {'PASS' if v else 'FAIL'}  {k}")
    pub = [b for b in boards if b["published"]]
    nocand = [b for b in boards if b["no_candidates"]]
    print(f"\npublished {len(pub)}/{n}   no candidates at all: {len(nocand)}/{n}")
    print(f"\n{'brd':>3} {'pub':>4} {'base':>7} {'maxall':>7} {'margin':>7} "
          f"{'th150':>6} {'th20000':>8} {'wrap150':>8} {'wrap20k':>8}")
    for b in boards:
        g150, g20k = b["gate"]["150"], b["gate"]["20000"]
        print(f"{b['i']:>3} {'Y' if b['published'] else '.':>4} {b['base']:>7} "
              f"{'-' if b['no_candidates'] else b['max_all']:>7} "
              f"{'-' if b['margin_max'] is None else b['margin_max']:>7} "
              f"{str(g150['max_all_passes_true']):>6} {str(g20k['max_all_passes_true']):>8} "
              f"{str(g150['wraps']):>8} {str(g20k['wraps']):>8}")
    if a.out:
        print(f"\nwrote {a.out}")


if __name__ == "__main__":
    main()
