# Lulu-proxy striker A/B — pre-registered endpoints (2026-08-08)

Written BEFORE any measured arm ran. Smoke/gate-demo runs (n<=12) are
excluded from inference by design; they exist to validate the machinery and
to demonstrate the killed-mutant gate.

## Hypothesis

dr. lulu's dossier mechanism — garbage released exactly when the AI's
scaffold is tall (the construction window) — is more lethal to the shipped
champion (s20b python image: wt=0, ws=20) than the SAME volleys delivered
blind. REACTIVE_MODE_RESULTS.md already showed clustered > smooth at matched
volume; this sharpens it to height-TIMED > randomly-timed at matched volume.

## Arms (paired seeds, per H)

- **striker**: volleys earned with the exact bursty-v1 fire/size draws
  (fit_struktured_20260804) on the AI's own clears, banked, released ALL-AT-
  TRIGGER when defender max stack height >= H, H in {5, 6, 8}; bank timeout
  9 placements (= mean inter-volley gap 22.7s / ~2.5s per L11 placement —
  one natural sending interval; derivation in striker_model.py docstring).
  Column policy: random (timing-only test; spawn-targeting is a separate,
  already-proven lever and deliberately NOT conflated here).
- **blind control (the confound killer)**: the IDENTICAL per-seed multiset
  of released volley sizes, at uniform-random placement indices over
  [25, striker-game horizon], deterministic per seed
  (Random(seed*99991+7)). Volume equality asserted by construction
  (volume_check) per seed.

## Release policy (fixed now, not tuned later)

ALL banked volleys release at the trigger (not one-per-placement). Timeout
releases are logged separately (reason="timeout") and remain in the volley
multiset the blind control replays.

## Endpoints

- **Primary**: dies_ahead count (topout with viruses<=12) and bad-end
  (topout+stall) count, striker vs blind, exact-binomial McNemar on
  discordant pairs (reach_root_ab convention). Counts, never adjectives.
- **Secondary**: clear rate, pills (both-won paired mean), exposure =
  fraction of decisions made with own max height >= 6 while a volley is
  banked/pending, and h_at_release for every volley impact.

## Sample

n=200 per arm: seeds = [s for s in range(201) if s != 1] (seed 1 is the
degenerate constant pill stream). Level 11. Workers capped at 3 (live jobs
own the box).

## Gauntlet deciders

1. champion baseline (wt=0, ws=20 — s20b python image, bit-exact prior-A/B
   entry point pressure_rig._choose_base)
2. t3tuck theta=150 (firmware DRCOPRO_TUCKV3_THETA default)
3. t3tuck theta=400 (the #85 brake dose)

t3tuck arms are enumerator-consumed tuck execution (run_2x2 arm-D style):
a perfect-vocabulary upper bound, NOT a ship signal
(dr-mario-tuck-armD-enumerator-not-firmware.md).

## Gate (must pass before any number is believed)

check_release_log: every release height-justified (h_at_release >= H) or
timeout-justified (age >= 9). Demonstrated to FAIL on: (a) inverted
predicate (fires at h<=2 — non-equivalent by construction: it produces
releases at heights the real predicate cannot), (b) random-height release
mutant (p=0.15/placement), (c) the blind control's own log. `run_striker_ab.py
--gate-demo` runs all four and exits nonzero if any mutant survives.

## Confound notes

- Volley-count confound: dead by construction (blind replays same
  count+sizes per seed).
- Trajectory divergence after the first differing injection is inherent to
  any injection A/B here and identical in kind to REACTIVE_MODE_RESULTS'
  drip-vs-bursty comparison; per-seed volley volume stays matched, landed
  halves may differ only via full-column skips (reported per run).
- Blind volleys undelivered because the blind game ended earlier than the
  striker horizon are counted and reported (blind_undelivered_volleys).

## AMENDMENT 2026-08-08 (before any measured run; only the excluded n=12
## smoke existed when this was written)

The n=12 smoke measured blind under-delivery of 48.4 vs 68.2 halves/game
(92 undelivered volleys) with blind indices drawn over
[25, striker FINAL pills]: indices landing after the blind game's own end
are never delivered, which resurrects the volume confound the control
exists to kill. Amended BEFORE the measured runs:

1. Blind indices are drawn uniform over [25, striker's LAST RELEASE pill]
   (the striker's actual delivery window), not the game's final pill.
2. Residual undelivered volleys are reported split by blind outcome:
   undelivered-because-won is post-outcome (cannot have caused the win);
   undelivered-because-died marks the pair volume-suspect.
3. Per-pair garbage volumes for every DISCORDANT dies-ahead pair are dumped
   into the summary (discordant_dies_ahead_garbage) so the volume story is
   inspectable exactly where the primary endpoint is decided.

Endpoints, arms, H sweep, timeout, seeds, and gate are unchanged.
