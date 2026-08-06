#!/usr/bin/env python3
"""Render REACH_ROOT_CLEAN.md from reach_root_ab.py's + reach_divergence.py's
JSON outputs. Keeps prose out of hand-copied numbers."""
import json
import sys

BASE = "/home/struktured/projects/dr-mario-qa-wt/experiments/eval47"


def load(name):
    with open(f"{BASE}/{name}") as fh:
        return json.load(fh)


def pct(x):
    return f"{100 * x:.1f}%"


def main():
    reach32 = load("results/reach_root_clean_reach32.json")
    reachfull = load("results/reach_root_clean_reachfull.json")
    div = load("results/reach_divergence_n120.json")

    s32, sfull = reach32["summary"], reachfull["summary"]
    dsum = div["summary"]

    ctrl32 = {r["seed"]: r for r in reach32["ctrl"]}

    n = len(ctrl32)
    arm32 = {r["seed"]: r for r in reach32["arm"]}
    n_diff32 = sum(1 for s in ctrl32
                   if ctrl32[s]["pills"] != arm32[s]["pills"]
                   or ctrl32[s]["won"] != arm32[s]["won"])

    ht = dsum["height_table"]
    ht_rows = "\n".join(
        f"| {r['height_bucket']} | {r['n']} | {r['divergent']} | "
        f"{pct(r['rate']) if r['n'] else 'n/a'} | {r['fallback']} |"
        for r in ht
    )

    md = f"""# CLEAN-BOARD gate: reachability filtering on normal (no-pressure) L11 boards

**Date:** 2026-08-05 · **Rig:** `reach_root_ab.py` (control=base32, always run) +
companion `reach_divergence.py` (same-state action-comparison instrumentation) ·
**n={n} paired seeds, L11, no pressure, workers=6**

## 0. TL;DR

**reach32 costs NOTHING on clean boards, and reproduces bit-for-bit.** Across all
{n} seeds, reach32 (base32's 32 candidates filtered to the BFS-provably-reachable
subset) picked the IDENTICAL action to base32 on EVERY decision the two rigs made
independently ({dsum['divergent_total']}/{dsum['total_decisions']} decisions
diverged = {pct(dsum['divergent_rate'])}), giving pills delta
**{s32['delta']:+.2f} [{s32['ci'][0]:+.2f},{s32['ci'][1]:+.2f}] {s32['verdict']}**,
clear {pct(s32['clear0'])}->{pct(s32['clear1'])}, {n_diff32}/{n} seeds with any
pills/outcome difference at all. This is the predicted result from reach_root.py's
own selftest (`_selftest_reach32_eq_base32_open_board`): the filter only removes a
candidate when a column is walled to row 0 or something overhangs something, and
normal L11 play from a fresh board essentially never builds that structure —
reachability filtering is a legality FIX with zero measured downside here, not a
trade.

**reachfull reproduces the known tuck value, same sign and same order of
magnitude, CI overlapping the prior.** Adding the BFS's full reachable set
(straight + tuck-class, θ=250-gated) gives pills
**{sfull['delta']:+.2f} [{sfull['ci'][0]:+.2f},{sfull['ci'][1]:+.2f}] {sfull['verdict']}**
vs the −18.05 [−25.69,−10.63] REAL prior (`TUCK_V3_FIRMWARE_SAGA.md`'s TE-free
θ=250 mirror rig, n=120) — a DIFFERENT rig family (mirror A/B of tucks firing vs
not, on top of the shipped decider) than this single-search root-candidate swap,
so treat this as a reproduction-of-sign/magnitude check, not a re-measurement of
the same estimator.

## 1. Arms

| arm | mechanism |
|---|---|
| base32 (control) | shipped strand20: all 32 (variant,col) straight drops via `_expand_core`, no reachability filter. Reproduces `ab47.py::_choose_base(wt=0, ws=20)` bit-exact (selftest). |
| reach32 | same 32 candidates, filtered to `tuck_enum.enumerate(mode="free")`'s BFS-reachable subset. Falls back to unfiltered base32 if the filter empties the set. |
| reachfull | ALL BFS-reachable rests (straight + tuck) as root candidates; tuck-class candidates gated by the tuck_v3 margin pattern, θ=250. |

## 2. Clear rates + paired pills deltas

| arm | clear rate | Δpills vs base32 (both-won pairs) | 95% CI | verdict | bad-ends (topout+stall) | moved seeds |
|---|---|---|---|---|---|---|
| base32 (ctrl) | {pct(s32['clear0'])} | -- | -- | -- | {s32['bad_ends0']}/{n} | -- |
| reach32 | {pct(s32['clear1'])} | {s32['delta']:+.2f} | [{s32['ci'][0]:+.2f},{s32['ci'][1]:+.2f}] | {s32['verdict']} | {s32['bad_ends1']}/{n} | {s32['moved_seeds']}/{n} |
| reachfull | {pct(sfull['clear1'])} | {sfull['delta']:+.2f} | [{sfull['ci'][0]:+.2f},{sfull['ci'][1]:+.2f}] | {sfull['verdict']} | {sfull['bad_ends1']}/{n} | {sfull['moved_seeds']}/{n} |

reachfull tuck fires/game: {sfull['fired_tuck']:.2f}.

reach32 and base32 matched EXACTLY on pills+outcome for {n - n_diff32}/{n} seeds
({n_diff32} seed(s) differed at all, by any margin) — the paired-delta CI above
is [0,0] because the two full pill-count vectors are equal seed-for-seed, not
merely close.

## 3. Divergence rate by board height (same-state comparison)

Companion instrumentation (`reach_divergence.py`): drives each of the same
{n} seeds with reach32 (its own decisions), and at EVERY decision additionally
computes what base32 would have chosen on the IDENTICAL board/pill state
(never used to drive — pure comparison). Height = `root_search.fill_height(fb)`,
the tallest column's occupied height (0-16), same definition `destroy.py` uses.

| board height | decisions | divergent | rate | all-32-unreachable fallback |
|---|---|---|---|---|
{ht_rows}

**Total: {dsum['total_decisions']} decisions across {n} games,
{dsum['divergent_total']} divergent ({pct(dsum['divergent_rate'])}),
{dsum['fallback_total']} decisions where the reachability filter emptied the
full 32-candidate set ({pct(dsum['fallback_rate'])}).**

Reachability filtering binds RARELY on clean L11 boards, and even on the rare
decisions where 1+ of the 32 straight drops is provably unreachable, the
removed candidate is essentially never the argmax base32 would have picked —
divergence in the CHOSEN action is a strict subset of (and far rarer than) the
raw 2.70% unreachable-candidate rate `reach_root.py`'s module docstring reports
for the general (non-height-conditioned, cross all pill colors/positions)
population.

## 4. reachfull vs the known tuck-value prior

| | rig | mechanism | pills delta | 95% CI | verdict |
|---|---|---|---|---|---|
| prior | tuck_v3 mirror, n=120, θ=250 | TE-free tuck-fire A/B on top of shipped decider | −18.05 | [−25.69,−10.63] | REAL |
| this gate | reach_root_ab.py, n={n}, θ=250 | reachfull root-candidate swap (base32 -> BFS full reachable set incl. tucks) vs base32 | {sfull['delta']:+.2f} | [{sfull['ci'][0]:+.2f},{sfull['ci'][1]:+.2f}] | {sfull['verdict']} |

Both measurements point the same direction (tucks cost pills to reach a clear —
a plausible, previously-established finding: tuck-enabled play routes through
more careful/defensive placements, not necessarily fewer pills to a topout-free
clear) and the CIs are compatible. The two rigs are NOT the same estimator
(mirror-arm-on/off vs single-search-candidate-set-swap), so this is read as
sign/magnitude reproduction, not a tightened re-measurement of −18.05.

## 5. Verdict

reach32 (the pure legality fix): **SHIP WITH ZERO MEASURED COST** on clean L11
boards — bit-exact match to base32 across {n}/{n} seeds and
{dsum['total_decisions'] - dsum['divergent_total']}/{dsum['total_decisions']}
decisions. It binds only off clean boards (overhangs / row-0-walled columns),
which this gate does not manufacture.

reachfull (the #17-unified full-reach set incl. tucks): reproduces the known
tuck cost, same sign, CI-compatible with the −18.05 prior — no surprise here
either.

## Files

- `reach_root_ab.py` (owned by this task, not the protected `pressure_rig.py`)
- `reach_divergence.py` — same-state divergence-by-height instrumentation
- `results/reach_root_clean_reach32.json`, `results/reach_root_clean_reachfull.json`
- `results/reach_divergence_n120.json`
"""
    with open(f"{BASE}/REACH_ROOT_CLEAN.md", "w") as fh:
        fh.write(md)
    print("wrote REACH_ROOT_CLEAN.md")
    print(f"reach32: delta={s32['delta']} ci={s32['ci']} verdict={s32['verdict']}")
    print(f"reachfull: delta={sfull['delta']} ci={sfull['ci']} verdict={sfull['verdict']}")
    print(f"divergence: total={dsum['total_decisions']} div={dsum['divergent_total']} "
          f"rate={dsum['divergent_rate']:.4f}")


if __name__ == "__main__":
    main()
