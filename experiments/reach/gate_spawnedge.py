#!/usr/bin/env python3
"""GATE for DRSPAWNEDGE (the missed new-pill edge after a Y=$0F lock), on the orient_harness closed loop (couch cart
flags + DRTAPP=2, forced throat/ledge regime, answer flips on). Counts new-pill edge FIRINGS per pill by watching the
new-pill block's own `STA DELAY2 <- 15` store.
  off    (DRSPAWNEDGE=0): the DEFECT must be exercised -- some pill gets NO edge, and every such pill follows a
                          pill that locked at Y=$0F (test the defect, not the fix).
  on     (DRSPAWNEDGE=1): EXACTLY ONE edge for every pill.
  mutants (DRSPAWNEDGE_MUT=nostore / nofell): must be KILLED (some pill gets more than one edge). The harness models
                          each board reset as a ROUND START (level init: counter += 2, Y = $0F, no live capsule, then
                          the throw), which is where nofell double-fires.
Exit 0 iff all three hold.  Usage: gate_spawnedge.py [--frames N] [--seeds 1 2 ...]
"""
import argparse, collections, json, sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import orient_harness as H


def arm(overlays, frames, seeds):
    rows = []
    for s in seeds:
        _, _, r = H.run(2, frames, s, 0.5, 0.6, overlays, trace_n=0)
        rows += [(s, i, x, r[i - 1] if i else None) for i, x in enumerate(r)]
    return rows


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--frames", type=int, default=40000)
    ap.add_argument("--seeds", type=int, nargs="*", default=[1, 2, 3])
    a = ap.parse_args()
    ok = True
    off = arm({"DRSPAWNEDGE": "0"}, a.frames, a.seeds)
    hist = collections.Counter(min(r["n_edges"], 3) for _, _, r, _ in off)
    missed = [(r, p) for _, _, r, p in off if r["n_edges"] == 0 and p is not None]
    prev0 = sum(1 for r, p in missed if p["row"] == 0)
    print(f"off   : {len(off)} pills, edges/pill {dict(sorted(hist.items()))}, missed {len(missed)} "
          f"(previous pill locked at row 0 / Y=$0F: {prev0}/{len(missed)})")
    if not (missed and prev0 == len(missed)):
        print("GATE_SPAWNEDGE FAIL: the defect is not exercised (or a missed edge has another cause)"); ok = False
    on = arm({"DRSPAWNEDGE": "1"}, a.frames, a.seeds)
    hist = collections.Counter(min(r["n_edges"], 3) for _, _, r, _ in on)
    bad = sum(1 for _, _, r, _ in on if r["n_edges"] != 1)
    print(f"on    : {len(on)} pills, edges/pill {dict(sorted(hist.items()))}, pills != 1 edge: {bad}")
    if bad:
        print("GATE_SPAWNEDGE FAIL: fixed cart does not give exactly one edge per pill"); ok = False
    mut = arm({"DRSPAWNEDGE": "1", "DRSPAWNEDGE_MUT": "nostore"}, a.frames, a.seeds)
    hist = collections.Counter(min(r["n_edges"], 3) for _, _, r, _ in mut)
    multi = sum(1 for _, i, r, _ in mut if r["n_edges"] > 1)
    print(f"mutant nostore: {len(mut)} pills, edges/pill {dict(sorted(hist.items()))}, pills with > 1 edge: {multi} "
          f"-> {'KILLED' if multi else 'SURVIVED'}")
    if not multi:
        print("GATE_SPAWNEDGE FAIL: the nostore mutant survived"); ok = False
    mut2 = arm({"DRSPAWNEDGE": "1", "DRSPAWNEDGE_MUT": "nofell"}, a.frames, a.seeds)
    hist = collections.Counter(min(r["n_edges"], 3) for _, _, r, _ in mut2)
    multi = sum(1 for _, i, r, _ in mut2 if r["n_edges"] > 1)
    print(f"mutant nofell : {len(mut2)} pills, edges/pill {dict(sorted(hist.items()))}, pills with > 1 edge: {multi} "
          f"-> {'KILLED' if multi else 'SURVIVED'} (the round-start throw double edge)")
    if not multi:
        print("GATE_SPAWNEDGE FAIL: the nofell mutant survived"); ok = False
    print("GATE_SPAWNEDGE", "PASS" if ok else "FAIL")
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
