# Bursty-v1: does the fitted human-volley model reproduce the dies-while-ahead disease?

**Date:** 2026-08-04 · **Rig:** `pressure_rig.py --model bursty` (new; drip mode preserved as default)
· **Model:** `bursty_model.py` `BurstyPressureModel` v1, fit from `film_review_20260804` footage
· **n=120 seeds/arm, L11, workers=6**

## 1. Integration

Added `--model {drip,bursty}` to `pressure_rig.py` (default `drip`, unchanged behavior — verified
byte-for-byte identical code path when `--model` is omitted). New pieces:

- `_init()` now takes `model_kind` / `bursty_model_obj` and stashes them in the worker-global `_C`.
- `main()` fits the model once in the parent process (`bursty_model.fit_struktured_20260804()`),
  strips the heavy per-frame `meta['raw_events']` ledger (not needed by the sampler, just pickling
  weight), and passes the slim fitted model to every worker via `ProcessPoolExecutor` initargs.
- `play()`: for `model_kind=="bursty"`, after each successful placement it computes
  `clear_size = occ_before + 2 - occ_after` (occupied-cell count before the placement, +2 for the
  landed pill, minus occupied-cell count after `env.step()` resolves) — the same occupied-cell-drop
  convention `bursty_model.extract_clears()` uses on footage. **This is the AI's own clear this
  placement, not an opponent's** — a solo rig has no second board to source the model's literal
  "opponent clear" conditioning variable from, so the AI's own clear (the only clear event a
  solo rig can observe) stands in for it, per task direction. `clear_size==0` (no clear) is
  explicitly skipped rather than calling `fire_probability(0)`, because `fire_probability`'s
  no-matching-bin fallback returns the *pooled unconditional* rate — calling it on a non-event
  would silently fire volleys uncorrelated with anything.
- When `clear_size>0`, calls `bursty_model.inject_bursty_garbage(board, model, seed, pills_placed,
  clear_size)` — this already does `board._apply_gravity()` + `board.resolve()` internally after
  dropping halves (the REQUIRED gotcha from the task: floating halves fake topouts if you check
  `spawn_blocked()` before gravity settles them). `pressure_rig.py`'s own post-injection checks
  (`virus_count()==0` → clear, `spawn_blocked()` → topout) run after that, unchanged from drip.
- Determinism: `inject_bursty_garbage`/`model.sample()` seed `random.Random(seed*1000+pills_placed)`
  — the same per-call convention `_inject_garbage` (drip) uses. Pairing across arms (same seed,
  different wt/ws) is preserved for *drip* exactly as before (garbage is gameplay-independent there).
  For *bursty* it cannot be byte-identical across arms by construction — the trigger is the arm's own
  clear timing, which differs once wt/ws changes what the AI plays — but the RNG draw at any given
  `(seed, pills_placed, clear_size)` is itself fully deterministic and reproducible.
- New per-game metric: `dies_ahead` = topout with `viruses_remaining <= 12` at the moment of death
  (`DIES_AHEAD_VIRUS_THRESHOLD = 12`), plus `viruses_left_at_end` on every row. `compare()` and the
  summary printer now report `dies-ahead` counts alongside `deaths+stalls`.

Smoke-tested at n=8 and n=12 before the full run (`tmp_logs` smoke output, not kept) — ran clean,
plausible numbers, no exceptions, RSS ~2.5–3.2GB total across 6 workers (well under the OOM
history threshold).

## 2. Fitted model (carried forward from `bursty_model.py`'s own `fit_summary()`)

```
n_matches=4  n_volleys=61  n_clears=188
volley_size_mean=2.54 cells [CI 2.33, 2.79]  (hist: 2→42, 3→9, 4→7, 5→2, 6→1)
inter_volley_gap_mean=22.70s [CI 17.19, 28.55]  (n=53 gaps)
p(volley within k=5s | opponent clear size):
  4-6 cells:   32.1% [25.0%, 39.7%]  n=156, hits=50
  7-10 cells:  74.1% [55.6%, 88.9%]  n=27,  hits=20
  11+ cells:   40.0% [0%, 80.0%]     n=5,   hits=2
lock_crosscheck_annotated_of_total = 33/61
```

Re-verified in this session: `python bursty_model.py` reproduces this exact fit standalone
(model_path below), and `main()`'s in-rig fit log line (`tmp_logs/bursty_n120.log:1`) matches it
number-for-number — the rig is drawing from the real fitted model, not a stub.

## 3. Rig results (L11, n=120 seeds, workers=6)

Source: `results/bursty_n120_wt0_ws20.json` (full per-seed rows both arms), driver log
`tmp_logs/bursty_n120.log`.

| arm | won (clear) | bad ends (topout+stall) | topout / stall | **dies-ahead (v≤12 at death)** | dies-ahead / topout | avg viruses left at end | avg garbage/g (halves) |
|---|---|---|---|---|---|---|---|
| **control** wt=0 ws=0 | 68/120 (56.7%) | **52/120 (43.3%)** | 42 / 10 | **37/120 (30.8%)** | 37/42 = **88.1%** | 1.91 | 58.56 |
| **ws=20 (shipped)** | 88/120 (73.3%) | **32/120 (26.7%)** | 21 / 11 | **16/120 (13.3%)** | 16/21 = **76.2%** | 1.44 | 63.62 |

Paired-seed tests:
- Pills delta on both-won seeds (n=50, ws=20 − control): **+13.52 [−3.04, +30.50] WASH**
  (CI straddles 0; drip's equivalent was −5.22 [−16.64, +5.99] WASH — both wash, opposite sign,
  neither meaningfully different from noise).
- McNemar-style bad-end discordants: **38 rescued / 18 harmed, exact binomial p = 0.0105** — ws=20
  still nets a real reduction under bursty pressure, but far leakier than under drip (drip: 23
  rescued / 6 harmed, p=2.3e-3 — 4x fewer seeds harmed there).

### Caveat: bursty injects ~2x drip's garbage volume

Control garbage/g is 58.56 halves here vs. drip's 30.20 (`PRESSURE_TAX_RESULTS.md`) — almost double.
This is a real consequence of the fitted firing rates (32–74% chance per own-clear, and clears are
frequent at L11 once material builds), not a bug, but it means part of the elevated death rate below
is attributable to raw volume, not purely to the burstiness/timing the model was built to capture.
Flagged for whoever tunes v2 (e.g. capping total halves/game to isolate the timing effect from the
volume effect) — not corrected here since the task asked to wire the fitted model as-is.

## 4. Verdict

**Bursty-v1 kills the control at more than 2x drip's rate**: 52/120 (43.3%) bad ends vs. drip's
24/120 (20.0%) — materially higher, as the task asked to check.

**ws=20 does NOT cure it the way it cured drip.** Drip: ws=20 cut bad-ends 24→7 (71% relative
reduction, clear rate 80.0%→94.2%, near-total immunity). Bursty: ws=20 cuts bad-ends only 52→32
(38% relative reduction, clear rate 56.7%→73.3%) — the shipped build still loses roughly 1 game in
4 under bursty pressure, ~4.6x drip's cured failure rate (26.7% vs 5.8%).

**The dies-ahead signature is real and dominant, and it survives on the shipped build.** 88.1% of
control topouts (37/42) and 76.2% of shipped-build topouts (16/21) happen with ≤12 viruses left;
the average virus count at the moment of *any* game's end (win or loss) is just 1.91 (control) /
1.44 (ws=20) — i.e. these are not games lost early or badly, they are games lost on the doorstep of
clearing, exactly the qualitative field pattern ("mechanically faster, dies ahead"). Under drip this
metric was never even elevated enough to be worth computing (control topout was only 17/120, and
ws=20's was 1/120 — too few events to characterize a "how close were they" distribution).

**reproduces_disease = YES.** Bursty-v1 reproduces both halves of the field disease drip could not:
(a) a materially higher control kill rate (2.2x drip's), and (b) a shipped-build (ws=20) failure mode
that is specifically dies-*while*-*ahead* (13.3% of all shipped-build games, 76.2% of its topouts) —
this is the first offline rig in which the shipped config visibly still loses the way the 3 field
sessions showed it losing. One honest limit: there is no field denominator (total human sessions
played, not just the 3 confirmed self-topout ones) to size-match the *magnitude* of 13.3% against —
so this confirms the *mechanism* and that it survives in the shipped build at a rig-measurable rate,
not a calibrated field-equivalent probability. Given that, the injection *model* is now a demonstrated
lever (drip could not show any of this); task #49's commit-path defect is not ruled out as an
*additional* contributor, but it is no longer the only candidate — bursty alone, with nothing from
#49, already reproduces the disease pattern on the shipped weights.

## Provenance

- Model: `/home/struktured/projects/dr-mario-qa-wt/experiments/eval47/bursty_model.py`
  (`fit_struktured_20260804()`, same call used for the fit reported in §2).
- Rig: `/home/struktured/projects/dr-mario-qa-wt/experiments/eval47/pressure_rig.py`
  (`--model bursty` new; `--model drip`/default unchanged).
- Run command: `pressure_rig.py --seeds 120 --workers 6 --level 11 --model bursty --arms 0:20
  --out results/bursty_n120`
- Raw results: `results/bursty_n120_wt0_ws20.json` (full per-seed control+arm rows, incl. new
  `dies_ahead` / `viruses_left_at_end` fields).
- Driver log: `tmp_logs/bursty_n120.log`.
- Drip comparison baseline: `PRESSURE_TAX_RESULTS.md` (control 24/120, ws=20 7/120, garbage/g
  30.20/26.86).
