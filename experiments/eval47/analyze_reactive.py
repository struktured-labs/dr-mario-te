#!/usr/bin/env python3
"""Paired analysis for the GARBAGE-REACTIVE MODE SWITCH experiment.

Reads the per-seed JSON dumps pressure_rig.py --out writes (one file per
arm, each containing its own freshly-computed "ctrl" (wt=0 ws=0, no
reactive) and "arm" rows) and reports, for every reactive/volume arm vs a
chosen reference:
  - bad-ends (topout+stall), topout/stall split, dies-ahead count
  - avg viruses-left-at-death (bad-end games only) and avg viruses-left-at-end
    (all games, for direct comparability with BURSTY_V1_RESULTS.md's table)
  - paired-pills delta + bootstrap CI on both-won seeds (already computed by
    pressure_rig.compare(), reused here from the "summary" field)
  - exact McNemar (binomial, two-sided) on bad-end discordants vs a
    REFERENCE arm (default: the plain ws=20 arm, not the wt=0/ws=0 control --
    the question is "does reactive help beyond ws=20 alone", not "beyond
    nothing"), plus "moved N% of seeds" = (rescued+harmed)/n

Usage: analyze_reactive.py <ws20_repro.json> <reactive1.json> [reactive2.json ...]
       [--dripvol path/to/dripvol_ws20.json]
The first file's "arm" rows are used as the McNemar reference (ws=20-only).
Every file's own "ctrl" rows are also cross-checked byte-identical to each
other (same seeds/model/no-reactive => must be, and if they aren't that is a
correctness bug worth surfacing loudly, not silently averaging over).
"""
from __future__ import annotations

import sys
import json
import argparse
import statistics as st
from scipy.stats import binomtest

DIES_AHEAD_THRESHOLD = 12


def load(path):
    with open(path) as f:
        return json.load(f)


def bad_end(row):
    return bool(row["topout"] or row["stall"])


def mcnemar(ref, arm, seeds):
    rescued = harmed = 0
    for s in seeds:
        r_bad, a_bad = bad_end(ref[s]), bad_end(arm[s])
        if r_bad and not a_bad:
            rescued += 1
        elif a_bad and not r_bad:
            harmed += 1
    disc = rescued + harmed
    if disc == 0:
        return rescued, harmed, disc, float("nan")
    p = binomtest(rescued, disc, 0.5).pvalue
    return rescued, harmed, disc, p


def avg_viruses_at_death(rows, seeds):
    xs = [rows[s]["viruses_left_at_end"] for s in seeds if bad_end(rows[s])]
    return (st.mean(xs) if xs else float("nan")), len(xs)


def avg_viruses_at_end_all(rows, seeds):
    return st.mean([rows[s]["viruses_left_at_end"] for s in seeds])


def summarize(tag, ctrl, rows, seeds, ref_rows=None):
    n = len(seeds)
    won = sum(rows[s]["won"] for s in seeds)
    topout = sum(rows[s]["topout"] for s in seeds)
    stall = sum(rows[s]["stall"] for s in seeds)
    bad = topout + stall
    dies_ahead = sum(rows[s].get("dies_ahead", 0) for s in seeds)
    avd, n_bad = avg_viruses_at_death(rows, seeds)
    ave_all = avg_viruses_at_end_all(rows, seeds)
    gb = st.mean([rows[s]["garbage_injected"] for s in seeds])
    rf = st.mean([rows[s].get("reactive_fires", 0) for s in seeds])
    print(f"\n=== {tag} ===")
    print(f"  n={n}  won={won} ({won/n:.1%})  bad-ends={bad} ({bad/n:.1%})  "
          f"topout={topout}  stall={stall}  dies-ahead(v<={DIES_AHEAD_THRESHOLD})={dies_ahead} "
          f"({dies_ahead}/{topout+stall}={dies_ahead/bad:.1%} of bad-ends)" if bad else
          f"  n={n}  won={won} ({won/n:.1%})  bad-ends=0")
    print(f"  avg viruses-left-AT-DEATH (bad-ends only, n={n_bad}): {avd:.2f}")
    print(f"  avg viruses-left-at-end (ALL games, BURSTY_V1_RESULTS convention): {ave_all:.2f}")
    print(f"  avg garbage/game: {gb:.2f}   avg reactive_fires/game: {rf:.2f}")
    if ref_rows is not None:
        rescued, harmed, disc, p = mcnemar(ref_rows, rows, seeds)
        print(f"  McNemar vs REFERENCE: {rescued} rescued / {harmed} harmed "
              f"(moved {disc}/{n} = {disc/n:.1%} of seeds), exact binomial p = {p:.4g}")
    return dict(tag=tag, n=n, won=won, topout=topout, stall=stall, bad=bad,
                dies_ahead=dies_ahead, avg_viruses_at_death=avd, n_bad=n_bad,
                avg_viruses_at_end_all=ave_all, avg_garbage=gb, avg_reactive_fires=rf)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("ws20_repro", help="results/..._wt0_ws20.json (the ws=20-only reproduction arm)")
    ap.add_argument("reactive", nargs="*", help="reactive-arm json files")
    ap.add_argument("--dripvol", default=None, help="volume-matched drip ws=20 json")
    a = ap.parse_args()

    repro = load(a.ws20_repro)
    ctrl0 = {r["seed"]: r for r in repro["ctrl"]}
    ws20 = {r["seed"]: r for r in repro["arm"]}
    seeds = sorted(ctrl0)

    print(f"=== CONTROL (wt=0 ws=0, bursty, n={len(seeds)}) ===")
    summarize("control wt=0 ws=0", None, ctrl0, seeds)
    summarize("ws=20 (shipped, reproduction)", None, ws20, seeds, ref_rows=None)
    # ws20 vs control McNemar, for context (matches BURSTY_V1_RESULTS' own number)
    r, h, d, p = mcnemar(ctrl0, ws20, seeds)
    print(f"  [context] McNemar ws=20 vs control: {r} rescued / {h} harmed, p={p:.4g}")

    results = [summarize("ws=20 (shipped, reproduction) [self]", None, ws20, seeds)]
    for path in a.reactive:
        d = load(path)
        c = {r["seed"]: r for r in d["ctrl"]}
        arm = {r["seed"]: r for r in d["arm"]}
        mism = sum(1 for s in seeds if c.get(s) != ctrl0.get(s))
        if mism:
            print(f"  !! WARNING: {path}'s control differs from the reproduction's control "
                  f"on {mism}/{len(seeds)} seeds -- NOT a clean paired comparison !!")
        tag = d["summary"]["tag"]
        r = summarize(tag, c, arm, seeds, ref_rows=ws20)
        pd = d["summary"].get("pills_delta")
        ci = d["summary"].get("ci", [None, None])
        verdict = d["summary"].get("verdict")
        print(f"  paired pills (both-won vs OWN control): {pd if pd is not None else float('nan'):+.2f} "
              f"[{ci[0]:+.2f},{ci[1]:+.2f}] {verdict}")
        results.append(r)

    if a.dripvol:
        d = load(a.dripvol)
        c = {r["seed"]: r for r in d["ctrl"]}
        arm = {r["seed"]: r for r in d["arm"]}
        print(f"\n=== VOLUME-MATCHED DRIP (period tuned to ~bursty control volume) ===")
        summarize("drip-volume-matched control wt=0 ws=0", None, c, seeds)
        summarize("drip-volume-matched ws=20", None, arm, seeds)
        print(f"  [comparison] bursty ws=20 bad-ends: {sum(bad_end(ws20[s]) for s in seeds)}/{len(seeds)}  "
              f"vs drip-volume-matched ws=20 bad-ends: {sum(bad_end(arm[s]) for s in seeds)}/{len(seeds)}")


if __name__ == "__main__":
    main()
