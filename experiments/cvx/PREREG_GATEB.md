# PRE-REG (2026-09-23 AT LAUNCH, Claude): #17 gate (b) for kc40 + #16 pinned calibration table
Worker `gate_b.py` (pinned imports via import_pin; decider = VsPolicy.decide so k_clock is live;
same solo loop as clock_play.play_hartford with the garbage MODEL injectable).
**Gate (b) (#17):** arms {winner=kc0, kc40, holes80} × OWNER burst model (fit_struktured_20260804)
× no clock stream, L11, cap 600, n=600 CRN (seeds 36734.. step 2, DECLARED REUSE = run-16/18 block).
PRIMARY = paired tap-out kc40 vs holes80 (McNemar); also kc40 vs winner. Bar: kc40 tap-out <= holes80
=> candidate whole; kc40 ≈ winner (~19%) => VS-only gain, couch build stays holes80.
**Calibration (#16):** same three arms × NutmegModel × TRATE {0, 0.020, 0.025} × n=300, cap 600,
seeds 36734.. — ONE table on the pinned path so cross-session Hartford numbers reconcile.
Runs behind gate (b). Results posted to issues #17 / #16 and here.

# RESULT #16 calibration
**#16 RESULT — one pinned table (Claude, 2026-09-23).** `gate_b.py`, `import_pin`, `VsPolicy.decide` (ws=0), NutmegModel linked fire + clock stream, L11, cap 600, n=300/cell, seeds 36734.. (declared reuse). Files `experiments/cvx/calib/`.

| arm | TRATE=0 (linked only) | 0.020 | 0.025 |
|---|---|---|---|
| **holes80** | **2.3%** | **27.0%** | **32.0%** |
| winner (kc0) | 16.3% | 42.3% | **49.7%** |
| kc40 | 10.0% | 41.3% | 52.0% |

**Reconciled.** Grok's kc0 = 50.2% at 0.025 reproduces here (49.7%). My earlier 6%/20.7% holes80 numbers were on the UNPINNED path (the same path-soup `import_pin` fixed) — withdrawn; Grok's scale is the real one. Two more things the table says:
1. **Couch anchor:** gate (b) gives holes80 24.3% under the owner burst model; that lands between Hartford TRATE 0 and 0.020 — so **0.020 is the couch-equivalent rate on the pinned path**, 0.025 is somewhat harsher than the owner. Suggest TRATE=0.020 as the default Hartford yardstick going forward, with 0.025 as the stress cell.
2. **holes80 dominates winner/kc40 at every rate** (2.3 vs 16/10, 27 vs 42/41, 32 vs 50/52). Under linked-only fire kc40 actually beats winner (10.0 vs 16.3, the clock term helps when garbage is combo-driven) but loses that once the clock stream is on. Same story as #17: tempo term = right idea, needs the holes80 trunk.

Not run again by me; this is the table both sessions should cite.
