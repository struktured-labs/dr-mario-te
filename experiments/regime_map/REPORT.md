# regime-141 — Champion failure-regime map (INTERIM: prereg + gates, burn running)

Status 2026-08-21 ~01:20 UTC: prereg committed (9dfe0ed) BEFORE any map row;
instrument gates green; the chained farm is burning under
`systemd-run --user --unit drm-regime-farm` (22 workers, all local, $0).

## What this lane answers

Where does the champion actually FAIL on the real RTL, and how often — the
measurement every future survival-flavored experiment needs after the GW
pricing VOID-by-saturation (96/96 clears under honest bursty v1.1 at L11).

## Design (PREREG_REGIME_MAP.md, committed before data)

6 cells, pressure variant x level, all decisions by the REAL RTL (verilated
CoproDrMario, champion fw s20b `e970e9ab`, farm_vsim `3e6569f1`):

| cell | pressure | level | note |
|---|---|---|---|
| c1_L11_bursty | bursty v1.1 (honest human fit) | 11 | reference; gw saw 0/96 here |
| c2_L11_x2 | v1.1 fire-prob x2 (synthetic dial) | 11 | intensity sensitivity |
| c3_L11_aim | v1.1 aimed at spawn cols 3,4, volume-neutral | 11 | tier-3-scheduler analog |
| c4_L20_clean | none | 20 | load control |
| c5_L20_bursty | bursty v1.1 | 20 | load x honest pressure |
| c6_L20_aim | v1.1 aimed | 20 | expected hardest |

Fresh EVEN seeds 30000-32998 (stride 2 — seed low bit is dead; blocks
documented consumed). No mirror pre-selection or de-dup of any kind (the
mirror-fidelity finding forbids it). Stage 1 n=50/cell; stage 2 budget 400
games by a REGISTERED deterministic allocator (code, not judgment): cells with
>=2 stage-1 failures topped to n=250, priority |rate-0.10| ascending;
registered fallbacks for <2 eligible and all-zero. Endpoint: failure =
topout|stall, exact Clopper-Pearson CIs (1 game = 1 independent unit).
max_pills 300/L11, 400/L20 with a registered censoring flag. Usability bar for
"home regime": CI lower bound >= 3%.

## Instrument gate sheet (all green before the burn)

| gate | what | result |
|---|---|---|
| (e) orientation | VAR_OF_O4 vs RING_OF_O4, all 4 codes | PASS |
| (d) physics | 10,554 fall_from cases vs resting_position | PASS |
| (a1) determinism | same seed, two fresh co-sims | PASS |
| (a2) determinism | fresh vs REUSED long-lived co-sim | PASS |
| g1 | x2 amplifier binds (fire prob exactly min(1,2p)) | PASS |
| g1-M1 | mutant: alpha inert — detector rejects | KILLED |
| g2 | aim binds (spawn-cols-first, volume-neutral) | PASS |
| g2-M2 | mutant: aim inert — detector rejects | KILLED |
| g3 | aim replay-determinism (game.py re-sample coherent) | PASS |
| g4 | level binds: L11=48, L20=84 viruses | PASS |
| g4-M3 | mutant: level inert — detector rejects | KILLED |
| g5 | reader alive: edited row moves the summary | PASS (M4 killed) |
| g6 | population gate accepts clean baseline | PASS |
| g6-M5a | POPULATION mutant: out-of-block seed | KILLED |
| g6-M5b | POPULATION mutant: mislabeled pressure | KILLED |
| g6-M5c | POPULATION mutant: wrong firmware | KILLED |
| g6-M5d | POPULATION mutant: duplicate row | KILLED |
| g6-M5e | POPULATION mutant: unaimed volley in aim cell | KILLED |
| g7/g8 | end-to-end RTL variant + L20 games | in chain (stage 3), gated |

The population audits (g6 family) also run inside the FINAL analysis on every
row — a bad row fails the run, not just the gate fixture.

Process guards inherited from today's masked-crash lesson: `set -eo pipefail`
in the unit, every stage gated on the previous stage's success marker
(`command grep -a`, NUL-safe), per-seed atomic rows + banked-seed resume,
stage-2 cells run in allocator priority order so an early cut costs the least
informative cells first. Hard analysis cut 2026-08-21 20:00 UTC.

## Wall estimate

Median RTL game 1123 s at L11 (measured, gw farm) — stage 1 ~6-7 h,
stage 2 <= ~12 h at the cap, 22 workers, ~2 cores free.

## Final results

(to be filled by the final analysis — `out/final_map.json` / `out/final_map.txt`)
