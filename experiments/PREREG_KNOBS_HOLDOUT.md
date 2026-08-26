# PRE-REGISTRATION — fresh-seed holdout confirmation of the DA re-screen winners (#86)

**Written before the run was launched; no holdout result existed at this commit.**
Date: 2026-08-09. Rig: `experiments/holdout_knobs.py` (reuses `sweep_knobs.evaluate`
unchanged). Reference arm: `WINNER` pinned by value in `h2h_vs.py`.

## Why a holdout at all

The DA re-screen (`tmp/selfplay/screen_da2_20260808.jsonl`) swept **30 arms** and produced
the first two candidates in 40+ VS-tuning attempts whose winrate CI excluded 50%:

| arm | screen winrate | screen CI | atk | DA |
|---|---|---|---|---|
| rdyext=16 | 54.1% | [50.3, 57.7] | 9.59 v 7.72 | — |
| maxh=6 | 54.2% | [51.2, 57.3] | — | 0 v 1 |
| vrdy=12 | — | — | — | 0 v 4 (null margin) |

Screening 30 arms and reporting the best is exactly the setting where the winner's curse
bites: with 30 draws, some CI excludes 50% by chance alone. A fresh-seed confirmation is
the only thing that separates a real effect from a selection artifact.

## Seeds — disjoint, and stride 2 on purpose

Screen used **70000..70319**. Holdout uses **300000, 300002, … 301998** — 1000 seeds,
disjoint from the screened range.

★ **Stride 2, and here is the measured reason.** `NesPillSource` gives seeds `2k` and
`2k+1` the **identical capsule stream** (verified: 200 consecutive seeds yield only 100
distinct streams). The virus layout does NOT collapse — boards for `2k` and `2k+1` differ —
so consecutive seeds are **correlated, not duplicates**, and the screen's CIs are not
invalidated by this. But the correlation is free to remove, so the holdout takes every
other seed and buys fully independent capsule streams at zero cost.

## Arms and endpoints — fixed now

| arm | primary endpoint | pass condition | secondary |
|---|---|---|---|
| `rdyext=16` | winrate | **≥52% AND CI excludes 50%** | DA (cand vs ref) |
| `maxh=6` | winrate | **≥52% AND CI excludes 50%** | DA (cand vs ref) |
| `vrdy=12` | **DA discordant pairs** | DA_cand < DA_ref, discordant-pair sign test | winrate (descriptive only) |

`vrdy=12` showed 0 v 4 on DA at a null winrate margin, so its primary endpoint is DA, not
winrate — pre-registered here so that reading its winrate afterwards cannot become the
result.

## Declared in advance

- n = 1000 seeds per arm = 2000 matches per arm (each seed played both ways, swap 0/1).
- Rule `rom` (the ROM-true attack rule); level 11; real NES capsules; garbage on.
- The NULL control (candidate == reference) must return exactly 50.0% / +0.00 margin.
  If it does not, the run is void and no arm is read.
- Arms run **sequentially**, one process pool, 6 workers.
- **A miss is a miss.** An arm that lands under 52%, or whose CI includes 50%, is reported
  as not confirmed. No re-slicing by phase, level, or sub-range, and no re-run at a larger
  n to chase significance.
