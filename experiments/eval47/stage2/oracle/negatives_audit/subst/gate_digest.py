#!/usr/bin/env python3
"""Bit-exactness COMPARATOR — turns exactness_gate.py from a measurement into a GATE.

`exactness_gate.py` computes a digest on whatever CPU it runs on and exits 0 regardless.
A digest with nothing to compare against can never fail. This script supplies the missing
half: it compares the remote digest to a banked reference and EXITS NON-ZERO on mismatch,
and on mismatch it diffs `env` and `code` so you immediately know whether it was the CPU,
the pins, or the code.

    python3 gate_digest.py --remote gate_remote.json --reference gate_local.json
"""
import argparse, json, sys


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--remote", required=True)
    ap.add_argument("--reference", required=True)
    a = ap.parse_args()
    R = json.load(open(a.remote)); L = json.load(open(a.reference))
    dr, dl = R.get("digest"), L.get("digest")
    print(f"reference {a.reference}\n  digest {dl}")
    print(f"remote    {a.remote}\n  digest {dr}")
    if dr == dl and dr:
        print(f"\nseeds {R.get('n_seeds')} vs {L.get('n_seeds')}")
        print("BIT-EXACTNESS GATE: PASS — new CPU reproduces the banked reference exactly")
        return 0
    print("\n*** BIT-EXACTNESS GATE: FAIL — DO NOT COUNT ANY ROW FROM THIS NODE ***")
    for field in ("env", "code"):
        rv, lv = R.get(field) or {}, L.get(field) or {}
        if rv == lv:
            print(f"  {field}: identical -> not the cause")
            continue
        print(f"  {field}: DIFFERS")
        for k in sorted(set(rv) | set(lv)):
            if rv.get(k) != lv.get(k):
                print(f"    {k}: remote={rv.get(k)!r}  reference={lv.get(k)!r}")
    # first differing seed, if per-seed detail exists
    pr, pl = R.get("per_seed") or {}, L.get("per_seed") or {}
    if isinstance(pr, dict) and isinstance(pl, dict):
        for k in sorted(set(pr) & set(pl)):
            if pr[k] != pl[k]:
                print(f"  first differing seed {k}: remote={pr[k]} reference={pl[k]}")
                break
    return 1


if __name__ == "__main__":
    sys.exit(main())
