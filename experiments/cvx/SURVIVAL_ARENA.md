# Survival arena

The two-board race (`vs_sim.py`) ends CLEAR on about 97–99% of games. Send-rule,
column, and halves-cap knobs do not move that mix anywhere near a human tape
(`arena15/RESULT.md`). Couch losses and the Hartford tape are tap-outs under
garbage bursts. Ranking candidates by race clear-rate is what let `k_clock=40`
win the arena and then fail gate (b) and MEGADOSE.

`survival_arena.py` is the pre-hardware screen for that failure mode. It plays
one brain against a garbage process, and it reports three numbers together:

- tap-out rate, with a 95% Wilson interval
- time-to-topout (median seconds and pills among games that tap out, with a
  bootstrap interval). Clears are censored. They are not scored as zero.
- clear rate, with a Wilson interval, so a saturated race is visible next to
  the tap-out rate

Dies-ahead (tap-out with 12 or fewer viruses left) is reported too. That is the
usual shape of these losses.

## The brain it is allowed to score

The shipped search is θ400: winner leaf, `DRCHAIN=180`, `DRSTRAND=20`, depth 3,
fixpoint cascades. Tucks and the veto are not in this model. `DRCHAIN=540` is a
candidate, not the default, and `screen` will not treat it as shipped.

| You want to measure | Arm | Accepted by `screen`? |
|---|---|---|
| Shipped brain | `fw_winner` | yes |
| Holes leaf on the shipped search | `fw_holes80` or `leaf:winholes80` | yes |
| Any other leaf already defined in `fast_rtl_x.variant`, still at chain 180 / strand 20 | `leaf:<name>` | yes |
| Unchained `VsPolicy` (`holes80`, `winner`, `kc40`, …) | those names | no, unless `--legacy` |

`holes80` with no chain is the search the holes leaf was originally validated
on. That search is not what ships. The tool rejects it unless you ask for the
diagnostic. `kc40` is the same kind of diagnostic: the clock term lived on the
unchained winner trunk.

This does not change firmware, RTL, or the coefficients in `fast_rtl_x`.

## Scenarios

Both scenarios are level 11, pill cap 600, garbage from pill 25, the same
travel-time clock as gate (b) (`0.6 + 0.35` seconds per row of fall).

**`owner`** — couch-footage bursts. Fire probabilities are the pooled
2026-08-04 fit committed in `experiments/eval47/results/` (61 volleys, 188
clears, 4 matches): 32.1% after a 4–6 cell clear, 74.1% after 7–10, 40% after
11 or more. Volley sizes are that fit's 61 observed sizes. This is the model
gate (b) used. The original footage order of those 61 sizes is not in the
pooled file, so a fresh game is distribution-matched, not seed-identical, to a
September row.

**`hartford`** — expert-tape sends. `NutmegModel` (779 arrivals / 4,599 clears
in the Top-8 tape) plus the clock stream at `TRATE=0.020` per second, which the
pinned calibration table calls the couch-equivalent rate. Every constant is in
`nutmeg_model.py` and in `gate_b.py`'s size draw, so this scenario does not
depend on a missing event order. `TRATE=0.025` is the harsher cell from that
table and is not the default.

MEGADOSE is not a scenario. It was 8 one-player level-11 games on a live ROM,
with no human garbage. It is an external check that `k_clock=40` lost a clear
(6/8 vs 7/8), not a burst distribution.

The race arena is not a scenario either.

## How to run

From the repo root, with `numba` and `numpy` installed:

```bash
# Pre-hardware screen: candidate leaf on θ400 vs fw_winner.
# Seeds start at 51000 so they do not overlap the gate (b) block.
python3 experiments/cvx/survival_arena.py screen \
  --arm fw_holes80 --scenario owner --n 200 --workers 4

python3 experiments/cvx/survival_arena.py screen \
  --arm fw_holes80 --scenario hartford --n 200 --workers 4

# One arm, jsonl out. Fresh seeds, not the gate (b) block.
python3 experiments/cvx/survival_arena.py run \
  --arm fw_winner --scenario owner --n 100 --seed0 51000 --workers 4 \
  --out /tmp/fw_winner.jsonl

# Replay the recorded gate (b) corpus (no search). Exact published rates.
python3 experiments/cvx/survival_arena.py retro

# Resimulate the gate (b) seed prefix. Declared reuse of 36734, step 2.
python3 experiments/cvx/survival_arena.py retro --live --n 120 --workers 4
```

`summary` reads jsonl and prints the same intervals.

A legacy replay, which is not a ship screen:

```bash
python3 experiments/cvx/survival_arena.py run \
  --arm kc40 --legacy --scenario hartford --n 200 --seed0 36734 --step 2
```

## How to use it before hardware

1. Put the idea on the shipped search. A new leaf weight is `leaf:<variant>`
   with chain 180 and strand 20 left alone. If the idea cannot be expressed
   that way, it is not this screen.
2. Run `screen` against `fw_winner` on **both** `owner` and `hartford`, same
   seeds for the pair. Do not use the race arena's win rate as the decision.
3. Read paired tap-out first. The bar carried from the firmware prereg: the
   upper end of the 95% interval on (candidate − `fw_winner`) tap-out is at
   most +2 percentage points. A faster clear or a higher race win does not
   cancel a tap-out regression.
4. Read time-to-topout second. A candidate that dies as often but much sooner
   is not a wash.
5. Size the run for the base rate. On the shipped brain, owner-model tap-out
   is about 3% (`fw_winner` 17/600). A 2–3 point effect was detectable at
   n=600 in the recorded corpus and is not detectable at n=40. Unchained arms
   die often enough that a smaller run can see a 15 point gap. Those arms are
   the diagnostic, not the ship screen.
6. A pass here is not a couch result. It is the check that should have existed
   before a week of hardware on a race-arena winner. Quartus, soak, and couch
   play stay outside this tool.

## Retroactive check

Full tables are in `RESULT_SURVIVAL_ARENA.md`. The short version:

- Re-scoring the recorded gate (b) jsonl matches the published tap-out rates
  to the game: holes80 24.33%, winner 40.50%, kc40 41.00%, and on the shipped
  search fw_holes80 − fw_winner = +2.67 points (p=0.026). kc40 ties the
  unchained winner (p=0.90) and loses to holes80 by +16.7 points. Median
  time-to-topout on that corpus is 756 s (holes80), 664 s (winner), 629 s
  (kc40). kc40 dies more often and sooner.
- Fresh `hartford` at n=80 lands on the pinned calibration table inside the
  intervals: kc40 42.5% vs 41.3%, holes80 32.5% vs 27%, winner 36.3% vs 42.3%.
  The kc40 − holes80 gap has the right sign (+10 pp) and the interval includes
  0 at this n.
- Fresh `owner` at n=120: kc40 is 40.8%, on the published 41%, and still above
  holes80 (+11.7 pp, interval excludes 0). holes80's own interval contains
  24.3%. About two thirds of unchained seeds end the same way as the recorded
  row. Do not treat one seed as a replay.
- Fresh firmware point estimates sit on the recorded ones (owner: 1.7% and
  5.8% vs 2.8% and 5.5%). At n=120 the paired interval still includes 0. A
  small fresh run will not see the holes-leaf harm that n=600 recorded. The
  shipped brain barely taps out under either scenario, so clear rate saturates
  again. The decision is the tap-out difference, and the run has to be large.
- `FirmwareBrain` is the in-repo reconstruction. The September
  `StrandedChainD3Decider` source is not in this checkout. The recorded fw_*
  jsonl is the exact historical measurement.
