# RESULT — survival arena vs the recorded losses

Screen: `experiments/cvx/survival_arena.py`. Games: `survival_retro/owner120_*.jsonl`,
`survival_retro/hart80_*.jsonl`. Recorded corpus: `experiments/cvx/gateb/`.
No firmware, RTL, or leaf coefficients were changed. No hardware and no Quartus.

## What "predictive" means here

Three different checks, not one number.

1. **Re-score the recorded gate (b) games.** Same rows that produced
   `RESULT_GATEB.md` and `RESULT_FWLEAF.md`. This asks whether the new
   reporter still says what those files said, and what time-to-topout was.
2. **Fresh `hartford` games.** Every constant is in this repo
   (`NutmegModel`, clock stream at 0.020/s). Compare to the pinned
   calibration table in `PREREG_GATEB.md` (n=300, TRATE 0.020): holes80
   27.0%, winner 42.3%, kc40 41.3%.
3. **Fresh `owner` games.** Same fire table as gate (b). The 61 volley sizes
   are the committed multiset, not the original footage order, so a seed is
   not required to replay its September row. `FirmwareBrain` is the in-repo
   reconstruction of the θ400 search (the September `StrandedChainD3Decider`
   module is not in this checkout).

Seeds for the fresh games are the gate (b) prefix, 36734 step 2. That is
declared reuse, for comparison, not a new holdout.

## 1. Recorded corpus, n=600 — exact

| arm | tap-out | Wilson 95% | clear | median seconds to tap-out (n deaths) |
|---|---|---|---|---|
| holes80 | 24.33% (146) | [21.07, 27.92] | 75.50% | 755.8 [729.0, 806.7] (146) |
| winner | 40.50% (243) | [36.64, 44.48] | 59.50% | 663.6 [642.4, 700.2] (243) |
| kc40 | 41.00% (246) | [37.13, 44.98] | 59.00% | 628.8 [598.2, 659.5] (246) |
| fw_winner | 2.83% (17) | [1.78, 4.49] | 96.17% | 331.3 [191.8, 434.2] (17) |
| fw_holes80 | 5.50% (33) | [3.94, 7.62] | 93.50% | 512.6 [336.7, 657.4] (33) |

Paired tap-out:

- kc40 − holes80 = **+16.67 pp [+11.67, +21.67]**, McNemar 78/178, p=3.7e-10.
  kc40 dies more often and, conditional on dying, sooner (629 s vs 756 s).
- kc40 − winner = **+0.50 pp [−4.67, +5.83]**, McNemar 123/126, p=0.90.
  The clock term does not buy survival on the unchained winner trunk.
- fw_holes80 − fw_winner = **+2.67 pp [+0.50, +5.00]**, McNemar 15/31, p=0.026.
  On the shipped search the holes leaf costs tap-outs. It does not help.

These rates match the published tables to the game. The time-to-topout column
was not in those tables; it is computed from the same rows. Clears are
censored, not treated as immediate deaths.

Dies-ahead is 90% of holes80 tap-outs and 97% of winner/kc40 tap-outs. That
is the couch shape (dead while still ahead on viruses), not a slow loss on
virus count.

## 2. Fresh hartford, n=80 — the regenerable scenario

| arm | this run | pinned table (n=300) | Wilson 95% of this run |
|---|---|---|---|
| holes80 | 32.50% (26/80) | 27.0% | [23.24, 43.36] |
| winner | 36.25% (29/80) | 42.3% | [26.57, 47.19] |
| kc40 | 42.50% (34/80) | 41.3% | [32.26, 53.43] |
| fw_winner | 0/80 | (not in that table) | [0.00, 4.58] |
| fw_holes80 | 2.50% (2/80) | (not in that table) | [0.69, 8.66] |

Every unchained point estimate's interval contains the pinned cell. kc40's
point (42.5%) sits on the table (41.3%). holes80 is a bit high (32.5 vs 27)
and winner a bit low (36.3 vs 42); neither disagreement survives the interval.

Paired, this sample:

- kc40 − holes80 = **+10.0 pp [−3.75, +23.75]**, p=0.23. Right sign (the table's
  gap is +14.3 pp). n=80 does not re-prove it.
- kc40 − winner = +6.3 pp [−7.5, +20.0], p=0.49. Not separated. The table has
  them essentially tied (41.3 vs 42.3).
- fw_holes80 − fw_winner = +2.5 pp [0.0, +6.3], 2 discordant deaths, p=0.5.
  Sign matches the recorded holes-leaf harm. Two deaths cannot carry it.

Median seconds to tap-out: holes80 789, winner 718, kc40 635. Same order as
the recorded owner corpus (safer arm dies later). kc40's 635 s is next to
the recorded 629 s.

## 3. Fresh owner, n=120 — distribution-matched, not seed-identical

| arm | this run | Wilson 95% | same 120 seeds, recorded | full recorded n=600 | how-agreement |
|---|---|---|---|---|---|
| holes80 | 29.17% (35) | [21.78, 37.84] | 20.83% | 24.33% | 80/120 |
| winner | 51.67% (62) | [42.81, 60.42] | 46.67% | 40.50% | 70/120 |
| kc40 | 40.83% (49) | [32.46, 49.78] | 39.17% | 41.00% | 74/120 |
| fw_winner | 1.67% (2) | [0.46, 5.87] | 3.33% | 2.83% | 112/120 |
| fw_holes80 | 5.83% (7) | [2.85, 11.55] | 5.00% | 5.50% | 102/120 |

kc40's 40.8% matches the published 41%. Its median time-to-topout is 622 s
versus 629 s on the full recorded corpus. holes80's median is 754 s versus
756 s. The clock, conditional on death, is calibrated even though only about
two thirds of unchained seeds end the same way.

The published 24.3% sits inside holes80's interval. The same-seed recorded
rate (20.8%) sits just outside it, so this draw is somewhat harsher on
holes80 than those 120 seeds were in September. Winner's 51.7% contains the
same-seed 46.7% and not the full-corpus 40.5%. The first 120 seeds of the
recorded block are themselves harsher on winner (46.7%) than the full 600.

Paired, this run:

- kc40 − holes80 = **+11.67 pp [+0.83, +21.67]**, McNemar 15/29, p=0.049.
  Same conclusion as gate (b): the clock arm dies more. The gap is smaller
  than +16.7 pp because this holes80 draw is high.
- kc40 − winner = −10.83 pp [−22.50, +0.83], p=0.098. This prefix does not
  show them tied. The recorded prefix doesn't either (39% vs 47%). The tie
  is a full-corpus fact (p=0.90 at n=600), not something n=120 of this prefix
  can see.
- fw_holes80 − fw_winner = **+4.17 pp [−0.83, +9.17]**, McNemar 2/7, p=0.18.
  Point estimates (1.7% and 5.8%) sit on the recorded 2.8% and 5.5%. The
  interval includes 0. A fresh n=120 would not have declared the holes leaf
  harmful. The recorded n=600 did (p=0.026).

Firmware how-agreement looks high because both arms clear most games. The
two recorded fw_winner deaths in this prefix were not the two fresh deaths.
Seed identity is not claimed for `FirmwareBrain`.

## What this does and does not catch

It catches the mistake that wasted the week, if you read tap-out rather than
clear rate:

- On the recorded games, kc40 is a race-arena winner with **no survival gain**
  over the unchained winner and a large survival loss against holes80, and it
  dies sooner. A fresh owner run at n=120 still has kc40 above holes80, with
  the interval excluding 0, and kc40's rate on the published 41%.
- On the recorded games, holes80 **hurts** on θ400 (+2.67 pp, interval excludes
  0). Fresh point estimates agree (owner 5.8 vs 1.7, hartford 2.5 vs 0). Fresh
  intervals at n=80–120 do **not** exclude 0. Using this screen at race-arena
  sample sizes on the shipped brain will miss that harm. The shipped brain
  only taps out a few percent of the time under either scenario, so clear rate
  is saturated again (owner fw_winner 96.7% clear, hartford fw_winner 100%
  at n=80). The metric has to be the tap-out difference, and the run has to
  be large.

It does not reproduce September seed-by-seed. Unchained how-agreement on the
owner draw is 58–67%. That is the volley-index order plus, for firmware, a
reconstructed search. Judge a fresh arm by its interval against `fw_winner`
on a seed block that is not 36734, sized for a few-percent base rate.

MEGADOSE (8 live one-player games, no garbage bursts) went 6/8 clears for
kc40 against 7/8 for k=0, and failed its 10 point bar. It is one missed
clear, not a tap-out measurement. It agrees only in the weak sense that
kc40 was not a strength win. This screen is the tap-out measurement MEGADOSE
was not.

## Pre-hardware rule used for the numbers above

`screen` refuses an arm that is not DRCHAIN=180 and DRSTRAND=20. The bar
copied from the firmware prereg: upper 95% of (candidate − fw_winner) tap-out
≤ +2 pp. n<200 prints a warning, because that bar is not estimable off a
handful of deaths. Race clear-rate is not the bar.
