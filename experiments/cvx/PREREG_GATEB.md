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
