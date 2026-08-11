# Per-ply flip provenance

**P0 from CHAMPION_ITER_PLAN.md.** The stage-2 rollout produced a NO_GO over
15,000 games with **zero mechanism**, because `flips` was logged as a bare
integer: no ply index, no `t_to_end`, no tie-vs-decided tag. 301 games the
champion cleared and the treatment did not were undiagnosable. This makes them
diagnosable.

**Mandatory for every future rollout arm.** It is on by default.

---

## What is emitted

One CSV row per **argmax flip** (treatment choice != base choice), appended as
games complete. Default path is `<--out stem>.flips.csv`; `--flips PATH`
overrides, `--no-flips` disables.

| column | meaning |
|---|---|
| `seed` | paired-seed id — joins directly to the `ab_*.jsonl` row |
| `arm` | arm tag (`trt`, `shuf`, …) |
| `ply` | 0-based decision index within the game |
| `t_to_end` | plies remaining until the game ends; the **last** decision is 0 |
| `viruses` | viruses on the board at the decision point |
| `maxh` | max column height at the decision point |
| `d_spawn_h` | taller of spawn columns 3 and 4 at the decision point |
| `tie` | 1 iff the base choice was tied on champion value with ≥1 other candidate |
| `champ_rank_chosen` | the champion's own preference position of the treatment's pick (0 = the base pick, so a flip is always ≥1) |
| `base_action` | slot the champion chose |
| `trt_action` | slot the treatment chose |
| `val_gap` | champion value the flip gave up (`best - vals[trt_action]`); 0.0 ⇒ the flip was free in champion units |
| `res` | terminal result of the game the flip occurred in |

`tie`, `champ_rank_chosen` and `val_gap` are the three that separate the two
hypotheses the NO_GO could not: *the term is re-ranking within noise* (`tie=1`,
rank 1, `val_gap=0`) versus *the term is overriding real champion judgement*
(`tie=0`, high rank, large `val_gap`).

`t_to_end` is stamped at end of game, not at the decision point — it is not
knowable earlier.

Rows for one seed are emitted in ascending `ply` order. The first row is
therefore the **first policy divergence** and needs no separately stored marker.
That distinction matters: before the first row, treatment and matched base are
on the same trajectory; after it, `base_action` means “what the champion would
choose on the treatment arm's current board,” not the action taken by the
separately played matched-base game.

The stable cross-arm header is:

```
seed,arm,ply,t_to_end,viruses,maxh,d_spawn_h,tie,champ_rank_chosen,base_action,trt_action,val_gap,res
```

Real shared-schema rows (`--seed-start 31000 --seed-count 24`):

```
31003,trt,100,3,1,8,4,1,2,23,21,2.0,clear
31000,trt,58,66,13,16,8,1,1,20,21,0.0,clear
31002,trt,62,150,15,13,10,0,1,29,22,1.0,clear
```

### Schema convergence with the oracle lane

The evaluator and oracle originally used three same-looking fields with
different meanings. The shared definitions are now explicit:

- `t_to_end = n_plies - 1 - ply`; the last decision is 0.
- `tie` means a tie in the **champion root values**, not a tie in the
  treatment arm's own labels or scores. An arm that also needs the latter logs
  it separately as `tie_score`.
- `val_gap` is always champion points surrendered by `trt_action`.

These definitions make the common columns poolable across arms. Arm-specific
fields (for example the oracle's fork labels and `tie_score`) may follow them.

## Cost — measured, not asserted

| | number |
|---|---|
| bytes/game (new schema, 24 real paired seeds / 47 rows) | **89.2 B** at 1.96 flips/game (including the one-time header) |
| projected size at 15,000 paired games | **~1.34 MB at that flip rate**; scales linearly with flips/game |
| flip rate observed | 1.96–2.98 records/game |
| CPU cost of the instrument | **11.1 µs/call × 2.12 flips/game = 0.024 ms/game = 0.00055 % of a 4.27 s game** |
| end-to-end wall A/B (8 games × 6 ABBA blocks, single process) | −0.82 % (i.e. below this box's noise floor) |

**Therefore it is ALWAYS ON.** The `--no-flips` escape hatch exists but the cost
does not justify using it.

A caution on how that number was obtained, because the first attempt was wrong:
a naive two-pool wall-clock A/B on this shared box read **+17.3 %**, and a first
in-process ABBA run read **+5.78 %**, while a second identical run read
**−0.82 %**. Both large numbers were other lanes' load, not the instrument.
The trustworthy figure is the direct one — time the only code the flag adds, on
real captured arguments, and multiply by the observed flip rate.
`bench_flip_provenance.py` does all three and prints all three.

`bench_flip_provenance.py` also asserts the instrument is **passive**: with
provenance ON and OFF the arm produces a byte-identical action sequence.

## Killed-mutant discipline

`test_flip_provenance.py` — a check that cannot fail is not a check, so it is
built to go red in **both** directions:

- **T1 null direction.** base policy == treatment policy (Delta identically
  zero) over 5 whole real games, 1,095 plies. The log must hold **zero**
  records. A second assertion confirms the games were non-trivial, so the zero
  is a measurement and not an empty run.
- **T2 positive direction.** A Delta that is zero everywhere except one
  candidate at one **injected** ply forces exactly one flip, at a known ply, to
  a known action. Exactly one record must appear, at exactly that ply, with
  `base_action` = the champion's own pick and `trt_action` = its rank-1
  alternative.
- **T3 field correctness.** Every field is re-derived by an independent probe
  on a pure-champion replay, deliberately in a *different idiom* (plain-Python
  board scans, not the numpy helpers the logger uses) so a wrong-plane or
  wrong-axis mutant cannot pass by symmetry.
- **T4** CSV round-trip.

`mutate_flip_provenance.sh` proves the gate actually fails on a broken logger.
It snapshots `arm_lut.py`, applies one defect at a time, runs the gate, and
restores. **Clean tree passes before and after; all 8 mutants go red:**

| mutant | gate result | which check went red |
|---|---|---|
| clean (control) | **pass** | — |
| M1 log every ply, not just flips | fail | T1 `records=1095 plies=1095`; T2 `n=214` |
| M2 ply index off by one | fail | T2 `ply=4 expected=3`; T3 t_to_end `209 vs 210` |
| M3 swap base_action / trt_action | fail | T2 base `logged=12 champion=13`; treatment `logged=13 expected=12` |
| M4 maxh uses `H.min()` | fail | T3 maxh `logged=8 probe=11` |
| M8 d_spawn_h scans columns 0/1 | fail | T3 d_spawn_h `logged=10 probe=11` |
| M5 viruses counts the colour plane | fail | T3 viruses `logged=50 probe=45` |
| M6 t_to_end = ply (elapsed, not remaining) | fail | T3 t_to_end `3 vs 210` |
| M7 champ_rank_chosen hard-coded 0 | fail | T3 rank `rank=0` |
| clean re-run (restore worked) | **pass** | — |

> Note for anyone extending this script: its restore **snapshots the working
> file**, it does not `git checkout --`. An earlier version used git checkout
> and silently deleted the uncommitted instrumentation it was supposed to be
> testing — every mutant then "failed" for the wrong reason and the final
> control caught it. Keep the trailing clean re-run.

## Reproduce

```bash
PY=/home/struktured/projects/dr_mario_rl/tmp/venv/bin/python
cd experiments/eval47/stage2/rollout
$PY test_flip_provenance.py          # the gate
bash mutate_flip_provenance.sh       # the gate's own gate (~15 min)
$PY bench_flip_provenance.py         # the cost
$PY run_ab.py --model lulu --term recommended \
    --seed-start 31000 --seed-count 24 --workers 4 --out tmp/dflt.jsonl
#   -> tmp/dflt.flips.csv
```

Input not tracked in git: `experiments/eval47/results/dr_lulu_20260808_fit.json`
(see task #19, "make experiments/ reproduce from a clean clone").
