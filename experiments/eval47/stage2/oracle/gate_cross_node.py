#!/usr/bin/env python3
"""GATE: the Hetzner node computes the SAME GAMES as blackmage.

The identity gate proves logging is inert on whichever CPU it runs on.  It does
NOT prove two different CPUs agree with each other — and the distillation
dataset is going to POOL rows from an Intel i9 and an AMD EPYC-Milan.  If the
two disagree even slightly, the pooled dataset is a mixture of two instruments
and every AUC computed on it is uninterpretable.

So: run the identity gate on BOTH nodes over the SAME SEEDS, then compare the
per-seed records here.  Agreement is required on every field that describes the
game — ply count, tie count, flip count, result — not just on the pass/fail bit.

This mirrors the precedent in HETZNER_NODE.md, where `exactness_gate.py` showed
i9-12900K and EPYC-Milan producing identical digests over complete per-seed
records.  That check is what made this node trustworthy in the first place; it
has to be re-earned for a new instrument.

Usage:
  gate_cross_node.py --local out/gate_dataset_identity_temporal.json \\
                     --remote out/gate_dataset_identity_hetzner.json
Exit 0 = PASS.
"""
import argparse
import json
import sys

FIELDS = ("identical", "n_ties", "n_plies", "res", "flips",
          "m1_diverged", "m2_diverged")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--local", required=True)
    ap.add_argument("--remote", required=True)
    a = ap.parse_args()

    L = json.load(open(a.local))
    R = json.load(open(a.remote))
    lrows = {r["seed"]: r for r in L["rows"]}
    rrows = {r["seed"]: r for r in R["rows"]}
    shared = sorted(set(lrows) & set(rrows))

    ok = True
    if not shared:
        print("FAIL: the two gates share NO seeds — nothing is being compared")
        return 1
    if not L.get("pass"):
        ok = False
        print("FAIL: the LOCAL gate did not pass")
    if not R.get("pass"):
        ok = False
        print("FAIL: the REMOTE gate did not pass")

    mismatches = []
    for s in shared:
        for f in FIELDS:
            if lrows[s].get(f) != rrows[s].get(f):
                mismatches.append((s, f, lrows[s].get(f), rrows[s].get(f)))
    for s, f, lv, rv in mismatches:
        ok = False
        print(f"FAIL seed {s}: {f} local={lv} remote={rv}")

    # A comparison over seeds that produced no tie plies would be vacuous: the
    # instrument under test only does anything at a tie.
    ties = sum(lrows[s]["n_ties"] for s in shared)
    if ties == 0:
        ok = False
        print("FAIL: the shared seeds contain ZERO tie plies — vacuous compare")

    print(f"\nshared seeds: {len(shared)}  ({shared[0]}..{shared[-1]})")
    print(f"tie plies compared: {ties}")
    print(f"field mismatches: {len(mismatches)}")
    for s in shared:
        print(f"  seed {s}: plies {lrows[s]['n_plies']} ties "
              f"{lrows[s]['n_ties']} flips {lrows[s]['flips']} "
              f"res {lrows[s]['res']} — "
              f"{'MATCH' if all(lrows[s].get(f) == rrows[s].get(f) for f in FIELDS) else 'DIFFER'}")
    print("\nCROSS-NODE GATE", "PASS" if ok else "FAIL")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
