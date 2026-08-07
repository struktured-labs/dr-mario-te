#!/usr/bin/env python3
"""Test the candidate fix for the spurious-WIN defect in the tuck ply-1 leaf.

DEFECT. `tuck_slot0_inject` uploads the tuck board with LEV_WSLOT=0 and then issues
CMD 2 (CUR <- slot[0]). But LeafEval.sv:47 documents wslot 0 as CUR, not a slot: a host
write with wslot==0 goes straight into `bcell` (line 386), and the slot dpram is written
only when wslot!=0 (line 177). So the upload has already put the board in CUR, and the
CMD 2 then OVERWRITES it with dpram region 0 -- which nothing ever fills. The LEAF that
follows scans that uninitialised region, sees no virus, and latches win <= !anyvir = 1.
Every tuck candidate therefore scores D_I1 + WIN on boards holding 44-48 viruses.

FIX (DRCOPRO_TUCKV3_FIXSLOT=1): drop the CMD 2. The board is already where the leaf
reads it.

This compares, on the same 30-board corpus:
  fixslot_pub2  DBGPUB=2 -> max D_V1 over all candidates, per board
  fixslot_ctl   DBGPUB=0 -> the publication decision
against the defective arm's numbers recorded in gate_readout_hz30.json.

PASS CRITERION, stated before running: if the defect is what the comment above says,
the candidate maxima must stop being pinned at the 30000 WIN sentinel and fall into the
same scale as `base` (order 10^3). If they stay at 30000 the diagnosis is wrong.
"""
from __future__ import annotations

import json
import os
import sys
from concurrent.futures import ThreadPoolExecutor

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from cosim import Cosim, read_hostdata  # noqa: E402

BIN = os.path.join(os.environ.get("COSIM_FARM_BUILD", os.path.join(HERE, "build")),
                   "obj_farm", "farm_vsim")
FW = "/mnt/data/drmario_cosim/fw"
CORPUS = "/mnt/data/drmario_cosim/gate/hostdata_l11_hz30.txt"
READOUT = "/mnt/data/drmario_cosim/results/gate_readout_hz30.json"
OUT = "/mnt/data/drmario_cosim/results/gate_fixslot_hz30.json"

WIN = 30000


def s16(lo, hi):
    v = (hi << 8) | lo
    return v - 0x10000 if v & 0x8000 else v


def run(fw, cases):
    with Cosim(BIN, os.path.join(FW, fw)) as cs:
        return cs.fw_md5, [cs.decide(c["board"], c["cA"], c["cB"], c["nA"], c["nB"])
                           for c in cases]


def main():
    cases = read_hostdata(CORPUS)
    old = json.load(open(READOUT))["boards"]

    with ThreadPoolExecutor(max_workers=2) as ex:
        f2 = ex.submit(run, "fixslot_pub2", cases)
        f0 = ex.submit(run, "fixslot_ctl", cases)
        (md5_pub2, r2), (md5_ctl, r0) = f2.result(), f0.result()

    rows = []
    for b, x2, x0 in zip(old, r2, r0):
        rows.append({
            "i": b["i"],
            "old_published": b["published"],
            "old_base": b["base"],
            "old_max": None if b["no_candidates"] else b["max_all"],
            "new_base": s16(x2["col"], x2["o4"]),
            "new_max": s16(x2["tcol"], x2["trow"]),
            "new_published": x0["tcol"] != 0xFF,
        })
    for r in rows:
        r["new_no_cand"] = r["new_max"] == -32768

    json.dump({"fw_pub2": md5_pub2, "fw_ctl": md5_ctl, "corpus": CORPUS, "rows": rows},
              open(OUT, "w"), indent=1)

    print(f"fixslot_pub2={md5_pub2[:8]}  fixslot_ctl={md5_ctl[:8]}\n")
    print(f"{'brd':>3} {'oldpub':>7} {'newpub':>7} {'old_max':>8} {'new_max':>8} "
          f"{'old_base':>9} {'new_base':>9}")
    for r in rows:
        om = "-" if r["old_max"] is None else r["old_max"]
        nm = "-" if r["new_no_cand"] else r["new_max"]
        print(f"{r['i']:>3} {str(r['old_published']):>7} {str(r['new_published']):>7} "
              f"{om:>8} {nm:>8} {r['old_base']:>9} {r['new_base']:>9}")

    o = [r["old_max"] for r in rows if r["old_max"] is not None]
    n = [r["new_max"] for r in rows if not r["new_no_cand"]]
    still = sum(1 for v in n if v >= WIN)
    print(f"\nOLD candidate maxima: n={len(o)} distinct={sorted(set(o))}")
    print(f"NEW candidate maxima: n={len(n)}" +
          (f" min={min(n)} max={max(n)}" if n else ""))
    print(f"still >= WIN({WIN}): {still} of {len(n)}")
    print(f"publication: OLD {sum(r['old_published'] for r in rows)}/{len(rows)}"
          f"   NEW {sum(r['new_published'] for r in rows)}/{len(rows)}")
    print(f"base unchanged by the fix (sanity -- the fix must not touch the base search): "
          f"{sum(r['old_base'] == r['new_base'] for r in rows)}/{len(rows)}")
    print("\nVERDICT: " + ("FIX CONFIRMED -- candidates are no longer WIN-pinned"
                           if still == 0 and n else
                           "NOT FIXED -- candidates still hit the WIN sentinel"))
    print(f"wrote {OUT}")


if __name__ == "__main__":
    main()
