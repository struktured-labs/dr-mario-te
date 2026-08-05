# #47 follow-up: does the height/spawn tax (wt) earn its keep under garbage pressure?

**Date:** 2026-08-04 · **Rig:** `pressure_rig.py` (verified SOUND, see below) · **n=120 seeds/arm, L11, H0=8**

## Rationale

The shipped config is `ws=20` (stranded-half tax) with **no** height tax (`wt=0`): in clean solo
play wt interfered (wt=6 alone cost +16 pills REAL; wt=2+ws=20 was worse than ws=20 alone on every
axis — `sweep_n120.log`). But in the field vs the human, the ws=20 build **self-topped-out while
ahead** in 3 confirmed sessions. Hypothesis under test: with garbage landing on the board, a small
wt earns its keep by keeping the spawn area survivable.

## Rig (1 para)

`pressure_rig.py` replays the ab47 paired-seed A/B (identical seeds, paired pills delta on
both-won seeds, bootstrap CI) but injects garbage into every game: from pill 25 onward, every 8
pills, k=2 random-column random-color half-cells drop onto the board (gravity + resolve applied),
keyed deterministically on `(seed, pills_placed)` so the injection schedule is identical across
arms while both games are alive. Control arm is **wt=0 ws=0** (no taxes). An independent
verification pass found no pairing-breaking or correctness defects (injection writes match the
validated `place_pill` path; rng drawn before the board-dependent skip so a skipped column cannot
shift the stream; end-condition ordering matches `env.step`; determinism + pairing confirmed
empirically by `micro_pressure_check.py` — two fresh-process control runs byte-identical). The
per-seed control rows saved by the first two completed runs were byte-identical, re-confirming
determinism; the later arms (0:20, 2:20) reused that verified control (`run_missing_arms.py`).

## Results (under pressure, n=120, garbage k=2/8 pills from 25)

| arm | deaths+stalls (PRIMARY) | topout/stall | clear | pills Δ vs pressure-control | stranded | funnelMM/g | garbage/g |
|---|---|---|---|---|---|---|---|
| control wt=0 ws=0 | **24** | 17 / 7 | 80.0% | — | 20.53 | 10.32 | 30.20 |
| **ws=20 only (shipped)** | **7** | 1 / 6 | 94.2% | −5.22 [−16.64, +5.99] WASH | 8.04 | 7.39 | 26.86 |
| wt=1 + ws=20 | **5** | 1 / 4 | 95.8% | −1.32 [−13.47, +10.90] WASH | 7.95 | 8.28 | 26.38 |
| wt=2 + ws=20 | **6** | 1 / 5 | 95.0% | +0.59 [−12.66, +14.18] WASH | 8.23 | 9.12 | 28.53 |
| wt=4 + ws=20 | **8** | 2 / 6 | 93.3% | +7.26 [−4.43, +19.19] WASH | 9.18 | 9.88 | 30.57 |

**wt=2-only (2:0) pressure arm: not run** (its launch died before producing output; with ws=20
already proven and staying shipped, the combo arms answer the actual question).

### Rig validity (pressure vs no-pressure)

No-pressure baseline (same eval family, ab47 clean sweep `sweep_n120.log`, n=120): control
wt=0 ws=0 = **5**/120 bad ends (clear 95.8%); ws=20 = **1**/120 (clear 99.2%). Under pressure the
no-tax control jumps 5 → **24**/120 (clear 95.8% → 80.0%, stranded 12.03 → 20.53) — well above the
~5/120 clean floor, so the rig genuinely elevates deaths. Requirement met.

### Paired per-seed tests (exact McNemar on bad-end discordants)

- control vs ws=20-only: 23 seeds rescued / 6 harmed, **p = 2.3e-3** — the stranded tax alone
  eliminates most pressure deaths.
- ws=20-only vs wt=1+ws=20: 6 rescued / 4 harmed, **p = 0.75** (n.s.)
- ws=20-only vs wt=2+ws=20: 5 / 4, **p = 1.0** (n.s.)
- ws=20-only vs wt=4+ws=20: 5 / 6, **p = 1.0** (n.s.)
- Paired pills (arm − ws20-only, both-won seeds): wt1 +1.53, wt2 +7.77, wt4 +12.82 — a
  monotone cost trend echoing the clean-play interference finding.

## Verdict: NO WINNER — hypothesis not supported by this rig

No wt dose reduces pressure-deaths vs ws=20-only beyond noise (7 → 5/6/8, all McNemar p ≥ 0.75;
120 seeds cannot distinguish these). Meanwhile the pills trend goes the wrong way as wt grows.
The survivability the hypothesis attributed to a height tax is **already delivered by the shipped
stranded-half tax**: ws=20 alone cuts pressure bad-ends 24 → 7 (p=2.3e-3), stranded 20.5 → 8.0,
and near-eliminates topouts (17 → 1). Keep shipping **ws=20, wt=0**.

Equally important negative: **this rig does not reproduce the field disease.** The shipped config
clears 94.2% under sustained k=2/8 garbage, yet self-topped-out while ahead in 3 human sessions.
Steady drip-feed garbage is evidently not what kills it — the dies-while-ahead failure needs a
different mechanism (and a different pressure model: bursty, combo-timed volleys landing while the
AI is committed/ahead, as a human delivers them).

## Next step (no-winner branch)

The dies-ahead disease needs a different mechanism, not a static eval tax:

1. **Garbage-reactive mode switch** — detect incoming/landed garbage above a height threshold and
   temporarily reweight (e.g. escalate ws, or activate clear-urgency) only while the condition
   holds; a conditional response cannot pay the constant clean-play interference price that killed
   static wt.
2. **Fix the rig first** — replay-derived volley timing (burst injections synchronized to the
   moments the AI is ahead / mid-cascade, from the 3 field sessions) so the failure is actually
   reproducible offline; re-run this same arm matrix under that model before building the switch.

## Provenance

- Rig: `pressure_rig.py` (verified unmodified), micro-test `micro_pressure_check.py`.
- Runs: `results/pressure_missing_wt0_ws20.json` (0:20), `results/pressure_1_20_wt1_ws20.json`,
  `results/pressure_missing_wt2_ws20.json` (2:20), `results/pressure_4_20_wt4_ws20.json` —
  each contains full per-seed control+arm rows; control rows byte-identical across all four.
- Arm re-runs driver: `run_missing_arms.py` (interpreter: `dr_mario_rl/tmp/venv/bin/python`,
  numba 0.66.0).
- Clean-play baseline: `sweep_n120.log` / `results/n120_*.json`.
