# Per-pill intended-vs-landed census (v4 Pocket human cart)

Owner field report (2026-08-08, v4 cart on Pocket): AI "still plays nonsensical vertical
dual-color capsules sometimes or even horiz backward". Question: for every pill, does the
LANDED placement (board delta at lock) match the copro's COMMITTED placement (mailbox)?

## Method
Mesen runs the EXACT on-card v4 binary (`pocket_human_v4_coldinit.nes`, md5 24dcd9dc,
manifest `roms/manifests/pocket-human-v4-coldinit.json`) remapped mapper 100 -> MMC1
(2 header nibbles; PRG/CHR byte-identical). The Lua script IS the copro (mailbox emulator
at $5000 per `patch_cartridge_copro.py` contract), so the committed placement is known
exactly — we serve it. Landed placement is recovered from the P2 board ($0500) delta at
lock, decoded via the tile encoding (high nibble 4/5=V top/bottom, 6/7=H left/right,
low nibble 0-based color).

Live artifacts + all logs: `/mnt/data/drmario/pocket-copro/mesen_copro_qa/census/`.

- `census_run.lua` — stable-target logger. Serves a d1 greedy brain's placement with
  configurable RLAT (frames to first mailbox publish; 2 ≈ measured running-best at ~2.6
  hooks) and DLAT (frames to DONE; 12 ≈ fast copro, 34 ≈ measured Pocket median).
  The served result never changes mid-pill => measured mismatches are pure
  driver-execution errors (lower bound on the field rate).
- `census_run_flip.lua` — flip arm: serves the runner-up placement until CEN_FLIPF frames
  after GO, then the final best (DONE certifies the final). Models running-best target
  flips mid-search — the pair-latch / early-read mechanism (m3 film review, b1).
- `decode_census.py` — ALL semantics live here (gate-able). Classes:
  e match / a wrong-column / b vertical-landed-H-committed / c_horiz+c_vert reversed
  color order / d horizontal-landed-V-committed / colormix / nocommit / undecodable.
  `--mutant swapped-colors|col-off1` for gate kills.
- `annotate_gate.py` — overlays decoded cells on lock screenshots (P2 playfield origin
  x=160+8c, y=72+8r), for the hand-verification gate.
- `aggregate.py` — batch roll-up split by DLAT arm.
- `launch_census.sh` / `launch_flip.sh` / `run_census_batch.sh` — serial launchers
  (SINGLE Mesen seat: they reap lingering instances first; Mesen2 single-instance
  forwarding corrupted a run before this guard existed).

## Instruments (deviations from pure cart behavior, disclosed)
- P1 KEEP-ALIVE: P1 board non-virus cells erased every frame (un-driven human side never
  tops out; P1 never attacks so P2's board delta stays pill-only).
- Menu drive: the v4 DRHUMAN cart's autonav holds VS-CPU state but never presses START
  (P0.4 gating) — the harness presses START and pokes L11/MED + per-round LCG seeds
  ($17/$18) at level-select. Effective seed logged at every round start.

## Decoder gate (project killed-mutant standard, 2026-08-08)
1. 20 pills hand-verified frame-by-frame against annotated screenshots
   (`logs/gate1/annotated/lock_001..020`): marker sits exactly on the locked pill,
   colors + orientation + column match the committed decode in all 20 (includes B-left
   reversed horizontals, B-top verticals, same-color pills).
2. Mutant swapped-colors: 55/55 color-order-expressible pills flagged class-c (100%),
   0 column-error side effects. Mutant col-off1: 92/92 flagged class-a. Both killed.
3. In-log driver-adoption cross-check: TGT_O2 == {0:3,1:1,2:0,3:2}[co4] and
   TGT_C2 == ccol on every logged pill (adds an independent check of the copro->game
   orient map against the driver's own state).
