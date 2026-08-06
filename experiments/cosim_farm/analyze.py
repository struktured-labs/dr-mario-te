#!/usr/bin/env python3
"""Paired analysis of co-sim farm arms.

PAIRING IS THE POINT. Every arm plays the same seed set, and seed s fixes both the virus
layout and the NES capsule stream, so arm differences are compared WITHIN seed. That
removes the between-game variance that swamped the physical MiSTer A/B (12 vs 13 games,
sd~10 on viruses-cleared, CI [-2.1,+13.3]). Only seeds present in BOTH arms are used, and
the count of dropped seeds is reported -- an arm that crashed on hard seeds would
otherwise flatter itself by disappearing from its own denominator.

Tests, chosen to match what each metric actually is:
  clear rate      McNemar exact (binomial on discordant pairs). The paired analogue of a
                  two-proportion test; the silicon lane was told to use an UNPAIRED test
                  precisely because it could not pin the cart's RNG. Here we can.
  pills-to-clear  paired bootstrap on seeds where BOTH arms cleared. Restricting to
                  mutual clears is a real limitation, not a detail: it conditions on
                  outcome, so it is reported alongside -- never instead of -- clear rate.
  viruses cleared paired bootstrap over ALL common seeds (no conditioning, so this is the
                  metric to trust when clear rates differ).
  topout/dies-ahead  McNemar, same reasoning as clear rate.

dies-ahead = topped out with <= 12 viruses left, matching reach_root_ab.py's
DIES_AHEAD_VIRUS_THRESHOLD exactly (not re-chosen here).

Usage: analyze.py results.jsonl --a s20b --b s20t3 [--out summary.json]
"""
from __future__ import annotations

import argparse
import json
import math
import os
import random
import statistics as st
import sys
from collections import defaultdict

DIES_AHEAD_VIRUS_THRESHOLD = 12


def load(path):
    arms = defaultdict(dict)
    n_err = defaultdict(int)
    with open(path) as fh:
        for ln in fh:
            ln = ln.strip()
            if not ln:
                continue
            try:
                r = json.loads(ln)
            except Exception:
                continue
            arm = r.get("arm")
            if r.get("result") == "ERROR":
                n_err[arm] += 1
                continue
            arms[arm][int(r["seed"])] = r
    return arms, n_err


def mcnemar_exact(b, c):
    """b = A-only successes, c = B-only successes. Two-sided exact binomial p."""
    n = b + c
    if n == 0:
        return 1.0
    k = min(b, c)
    tail = sum(math.comb(n, i) for i in range(k + 1)) / (2 ** n)
    return min(1.0, 2 * tail)


def boot_ci(deltas, n_boot=20000, seed=12345):
    if not deltas:
        return (float("nan"), float("nan"))
    rng = random.Random(seed)
    n = len(deltas)
    means = []
    for _ in range(n_boot):
        means.append(sum(deltas[rng.randrange(n)] for _ in range(n)) / n)
    means.sort()
    return (means[int(0.025 * n_boot)], means[int(0.975 * n_boot)])


def rate_block(name, A, B, seeds, pred):
    a = sum(1 for s in seeds if pred(A[s]))
    b = sum(1 for s in seeds if pred(B[s]))
    disc_a = sum(1 for s in seeds if pred(A[s]) and not pred(B[s]))
    disc_b = sum(1 for s in seeds if pred(B[s]) and not pred(A[s]))
    p = mcnemar_exact(disc_a, disc_b)
    n = len(seeds)
    return {"metric": name, "n": n,
            "a_count": a, "a_rate": a / n if n else float("nan"),
            "b_count": b, "b_rate": b / n if n else float("nan"),
            "delta_rate": (b - a) / n if n else float("nan"),
            "discordant_a_only": disc_a, "discordant_b_only": disc_b,
            "mcnemar_p": p}


def paired_block(name, A, B, seeds, field):
    d = [B[s][field] - A[s][field] for s in seeds]
    if not d:
        return {"metric": name, "n": 0}
    lo, hi = boot_ci(d)
    return {"metric": name, "n": len(d),
            "a_mean": st.mean(A[s][field] for s in seeds),
            "b_mean": st.mean(B[s][field] for s in seeds),
            "paired_delta_mean": st.mean(d),
            "paired_delta_sd": st.pstdev(d) if len(d) > 1 else 0.0,
            "ci95_lo": lo, "ci95_hi": hi,
            "n_moved": sum(1 for x in d if x != 0),
            "frac_moved": sum(1 for x in d if x != 0) / len(d)}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("jsonl")
    ap.add_argument("--a", required=True, help="control arm label")
    ap.add_argument("--b", required=True, help="candidate arm label")
    ap.add_argument("--out")
    args = ap.parse_args()

    arms, n_err = load(args.jsonl)
    if args.a not in arms or args.b not in arms:
        print(f"missing arm: have {sorted(arms)}")
        return 1
    A, B = arms[args.a], arms[args.b]
    common = sorted(set(A) & set(B))
    only_a, only_b = sorted(set(A) - set(B)), sorted(set(B) - set(A))

    print(f"=== {args.b} (candidate) vs {args.a} (control) ===")
    print(f"paired seeds: {len(common)}   "
          f"{args.a}-only {len(only_a)}   {args.b}-only {len(only_b)}   "
          f"errors A={n_err.get(args.a,0)} B={n_err.get(args.b,0)}")
    fw_a = {A[s]["fw_md5"] for s in common if "fw_md5" in A[s]}
    fw_b = {B[s]["fw_md5"] for s in common if "fw_md5" in B[s]}
    ex_a = {A[s].get("exec_mode") for s in common}
    ex_b = {B[s].get("exec_mode") for s in common}
    print(f"firmware  A={sorted(fw_a)} exec={sorted(ex_a)}")
    print(f"firmware  B={sorted(fw_b)} exec={sorted(ex_b)}")
    if len(fw_a) > 1 or len(fw_b) > 1:
        print("!! an arm mixes firmware images -- results are not interpretable")
    if not common:
        print("no paired seeds")
        return 1

    blocks = [
        rate_block("clear",       A, B, common, lambda r: r["won"] == 1),
        rate_block("topout",      A, B, common, lambda r: r["topout"] == 1),
        rate_block("stall",       A, B, common, lambda r: r["stall"] == 1),
        rate_block("dies_ahead",  A, B, common,
                   lambda r: r["topout"] == 1
                   and r["viruses_left"] <= DIES_AHEAD_VIRUS_THRESHOLD),
    ]
    print()
    for bl in blocks:
        print(f"{bl['metric']:<12} A {bl['a_count']:>4}/{bl['n']} ({bl['a_rate']:6.1%})   "
              f"B {bl['b_count']:>4}/{bl['n']} ({bl['b_rate']:6.1%})   "
              f"delta {bl['delta_rate']:+6.1%}   "
              f"discordant {bl['discordant_a_only']}/{bl['discordant_b_only']}   "
              f"McNemar p={bl['mcnemar_p']:.4f}")

    pb = [paired_block("viruses_cleared", A, B, common, "viruses_cleared"),
          paired_block("pills(all seeds)", A, B, common, "pills"),
          paired_block("n_tuck_published", A, B, common, "n_tuck_published")]
    both = [s for s in common if A[s]["won"] and B[s]["won"]]
    if both:
        pb.append(paired_block(f"pills-to-clear (both cleared, n={len(both)})",
                               A, B, both, "pills"))
    print()
    for bl in pb:
        if bl.get("n", 0) == 0:
            continue
        print(f"{bl['metric']:<38} A {bl['a_mean']:8.2f}  B {bl['b_mean']:8.2f}  "
              f"paired delta {bl['paired_delta_mean']:+7.2f} "
              f"[{bl['ci95_lo']:+.2f},{bl['ci95_hi']:+.2f}]  "
              f"moved {bl['frac_moved']:.0%}")

    moved_any = sum(1 for s in common
                    if (A[s]["result"], A[s]["pills"], A[s]["viruses_cleared"])
                    != (B[s]["result"], B[s]["pills"], B[s]["viruses_cleared"]))
    print(f"\nseeds where the two arms played differently at all: "
          f"{moved_any}/{len(common)} ({moved_any/len(common):.1%})")

    out = {"control": args.a, "candidate": args.b, "n_paired": len(common),
           "n_only_a": len(only_a), "n_only_b": len(only_b),
           "errors": dict(n_err),
           "fw_a": sorted(fw_a), "fw_b": sorted(fw_b),
           "exec_a": sorted(x for x in ex_a if x), "exec_b": sorted(x for x in ex_b if x),
           "rate_blocks": blocks, "paired_blocks": pb,
           "seeds_moved": moved_any}
    if args.out:
        os.makedirs(os.path.dirname(args.out), exist_ok=True)
        json.dump(out, open(args.out, "w"), indent=1)
        print(f"\nwrote {args.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
