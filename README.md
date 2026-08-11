# Dr. Mario NES — FPGA AI Coprocessor

> **ROM-hack release:** [Dr. Mario Training Edition v8.2](release/RELEASE_NOTES_V8_2.md) —
> [download the BPS patch](release/drmario_te_v8_2.bps). A stability release that fixes a
> hard freeze and level-select corruption present in every prior Training Edition (v6–v8);
> a [v6.1 backport patch](release/drmario_te_v6_1.bps) exists for anyone on the published v6.
> **v9 is at release-candidate** ([notes](release/RELEASE_NOTES_V9.md),
> [submission kit](release/SUBMISSION_v9d.md)): it restores the 2-player STUDY pause —
> both players' previews, lifted STUDY banner, BCD-correct virus counters.

A hardware-accelerated depth-3 AI that plays Dr. Mario (NES) on a real
[MiSTer](https://github.com/MiSTer-devel/Main_MiSTer/wiki) FPGA **and on the Analogue
Pocket** (custom openFPGA core). A custom mapper drops a
**second 6502 core plus an RTL board-engine** into the NES core; a companion cartridge
auto-navigates into a VS-CPU match and lets the coprocessor drive a player — no controller,
no host PC in the loop. It is a self-running demo of an expectimax search running on silicon
alongside the game it is playing.

## Current champion status — 2026-08-11

The north star is not a simulator score: it is **best-in-the-world play under original-NES
rules and real-time execution**. Dr. Lulu is the current on-prem human milestone, not the
definition of success. The project is close, but the present cart still makes occasional
obvious, locally myopic moves that keep it below that bar.

| Track | Evidence-backed state |
| --- | --- |
| **v8 REMATCH cart** | Shipped, gated and hardware-faithful (`c0082cb34259007854120d3d4ab9fa27`). It adds crash hardening and execution fidelity; it does **not** claim a strength gain over the champion Dr. Lulu has already beaten. |
| **Exact policy fidelity** | Full firmware co-sim matches 19/19 decisions and all 542/542 legal-candidate values, in debug and non-debug builds. |
| **Learned evaluator** | Stage-2 is **NO_GO**. Its −0.80 pp dies-ahead estimate crossed zero, and a dose-matched shuffled-label null did just as well. Changing 1.8% of plies reshuffled roughly 20% of outcomes: churn was real, direction was not. |
| **`d_spawn_h` tie resolver** | **NO_GO** at N=9,000: dies-ahead became 0.200 pp worse, 95% paired CI [+0.022, +0.378], p=0.03846. It will not be swept on those seeds. |
| **Next strength probe** | A narrow K4 spawn-lane penalty only after garbage actually lands now has an independently validated, distinct-state dose-matched null. Its preregistered N=9,000 endpoint is the current test; no result is claimed here before it completes. |
| **Pocket θ400** | A full clean seed-8 fit passes at 18,262/18,480 ALMs (218 free), +1.682 ns setup slack, with both 16,384-byte firmware-content proofs exact. Hardware runtime/value A/B is still required. |
| **Seed-30011 freeze** | Pre-existing, deterministic, and reproduced at identical frames on the unhardened cart. It is not a v8 regression; the current pause-vs-wedge discriminator remains unresolved. |

Promotion now requires converging evidence: fewer identifiable blunders, no broad clean-play
regression, improvement over a dose-matched label-blind null, stronger opponent results, and
hardware-representative execution. Offline AUC or a py65-only win is not enough.

## Milestone — depth-3 on hardware at ~1 second per move

The AI runs a **depth-3 expectimax search** (current pill + preview pill known, third pill
averaged over a pill subset) with a coefficient-optimised evaluation. In pure simulation the
shipped decision function clears **~96%** of L11 boards solo on the real NES capsule stream
(115/120 in the latest paired baseline). The whole pipeline — search → firmware →
cycle-accurate sim → Quartus → hardware — is validated cell-exact at each stage.

**Latency, start of port → now:**

| Build | First-pill decision | What changed |
| --- | --- | --- |
| initial | ~400 s | copro fed the 21.5 MHz NES clock (never the intended 85.9 MHz) |
| `clk85` | ~100 s | dual-clock fix: 6502 + engine on the master clock |
| 4-pill | ~50 s | 4-pill expectimax subset (measured 100% solo, no quality loss) |
| LeafEval | ~4 s | full leaf evaluation in RTL (~1.5k cycles vs ~50k on the 6502) |
| **BoardEngine** | **~1 s** | land + place + resolve + leaf + board copies all in RTL; 6502 is pure search control |

Steady-state moves are sub-second — the demo is now paced by the game's own pill-drop and
clear animations, not by the AI.

## Milestone 2 — Analogue Pocket port + the honest (anytime) AI

The same coprocessor now ships on a **handheld**: a single-copro variant of the mapper
lives inside a trimmed [agg23/openfpga-NES](https://github.com/agg23/openfpga-NES) core
(mapper farm stripped to MMC1 + mapper 100 — the stock core is 99% ALM-full; the trim
reclaims ~6.2K ALMs and the copro fits at ~96% with timing closed at the full 85.9 MHz).
Human-vs-AI on the couch: **you are P1 on the Pocket's buttons, the depth-3 copro is P2.**

The AI itself crossed from "solver with pause privileges" to **honest real-time player**:

- **Anytime search** — the firmware live-publishes its best-so-far move into the result
  mailbox as the search runs (orient `0xFF` = not-yet-valid sentinel; zero RTL change).
  The driver never freezes the pill: it weave-steers toward the current best while the
  search refines, and only fast-drops after DONE. **The pill's own fall time is the AI's
  time budget.** Hardware A/B (P1 freeze vs P2 anytime, same match): anytime cleared
  viruses at 2× the rate with no mid-air pauses.
- **Temporal discount** (`val = imm + leaf + (deep−leaf)/2`) — fixes a search pathology
  where deferring an obvious placement is value-neutral in the model ("procrastination"),
  found by a human player in one game. Also worth ~14% solo pill-efficiency.
- **Household-coached eval terms** — `g_excav` (scaffolding credit for clearing junk off
  buried viruses) and `g_hang` (a hovering capsule half whose gap-drop lands on a matching
  color pairs automatically when its partner clears — the delayed-drop setup). Computed by
  the 6502 once per ply-1 candidate on top of the RTL leaf; py65-gated bit-exact.
- **Deterministic match entry** — the auto-nav writes coherent VS-CPU state
  (`$0727=2, $04=1`) on every title hook, holds the title against the attract demo, and
  gates START on `$04` (the only discriminator that isolates VS-CPU; gating on `$0727==2`
  alone fires one toggle early into 2P-human and was refuted on silicon).
- **Human-challenge carts** — `DRHUMAN=1` builds leave P1 as a pure human passthrough
  (`drmario_copro_human.nes` for MiSTer, `DRPOCKET=1` single-window variant for Pocket),
  with a driver-drawn STUDY pause overlay: both previews and the letters survive the pause
  in 1P and 2P because the driver, not the evacuated ROM tail, owns those OAM slots.

One canonical RTL source (`fpga/copro/`) feeds both platforms: the Pocket tree vendors it
via `fpga/copro/sync_to_pocket.sh`. Platform images may intentionally carry different,
byte-proved firmware variants (for example θ150 and θ400); manifests identify the exact
firmware instead of assuming one `copro_rom.hex` ships everywhere.

## Milestone 3 — "Combo Stomper": a chain-building champion, and a self-healing cart

The evaluation grew a **chain-attack term** (`chain180`): credit for building multi-clear
structures, priced against the ROM-true VS attack rule (the combo counter SUMS across
cascade steps, so cascades of singles attack too — verified against the disassembly).
Head-to-head on the real capsule stream it beats the previously shipped champion
**70.9%** of matches — and the win is *garbage-mediated*: with attacks disabled the same
eval only takes 54.0%, so the chains it builds are doing the winning, not generic board
quality. A link-plane upgrade (`lnk1`, the first holdout-confirmed VS gain) rides along at
**60.2%** on held-out seeds. The VS mechanism is out-racing, not defense: the winner
absorbs ~46% more incoming volleys per ply and clears through them. This build runs live
on the MiSTer as `NES_stomper180` — the standing house duel.

The cartridge driver is now **self-healing** on real silicon, each guard reproduced from a
captured hardware failure before it was fixed, and each gated by a py65 test that
simulates the defect rather than asserting the guard exists:

- **Menu-escape watchdog** (`DRNAVESC`) — a screen stuck ~10 s awaiting a START the nav
  never sent gets a raw START burst (never during live play, never in the intro).
- **Bounded search retry** (`DRWRETRY` + `DRPENDBOUND`) — a timed-out coprocessor search
  re-queues once per pill instead of forever; kills a recurring ~4-minute stick/heal cycle.
- **Play-stall watchdog** (`DRSTALLWD`) — a P2 pose frozen ~20 s mid-play with viruses
  alive triggers a scoped search re-arm that preserves the committed targets.
- **Stale-BUSY escape** (`DRBUSYESC`) — the re-entrancy guard's latch lives in sticky
  FPGA BRAM and survives core reloads; a reload that interrupted an in-flight invocation
  used to soft-brick the driver on every subsequent boot. 255 consecutive bails (~2 s)
  now force-free the latch.
- **Human-tempo retune** — measured dose-response on the slam gates (`MIN_THINK=12`,
  `K_OPEN=32`): 62.0 frames/pill vs 68.0 shipped with zero wrong-column commits. The
  rest of the human tempo gap is routing, not gate latency: ~52.5 f/pill is irreducible
  for this executor (settle + DAS steer + slam descent).

**Updated 2026-08-11: the tuck enumerator is ported, wired, RTL-verified, and the θ400
Pocket image now fits cleanly — but value is still unproven on Pocket hardware.** The v3
offline proof (−10.0 pills at L11, L20 clear rate 96.2%→99.2%,
p=0.039) converged on a **TE-free BFS enumerator** (512 states, one 64-byte visited plane),
now running as real 6502 firmware on the coprocessor: bit-exact against its Python
reference (0/1490 corpus candidates), ~1 frame per board at the copro's clock, 58% of its
ROM window. Its execution vocabulary was the surprise cost — the shipped descriptor could
only express 45% of reachable tuck placements, and a tier sweep priced the recovery: a
**tier-3 motion vocabulary** (any approach column, ≤1 lateral direction change) reaches
100% of them for ~1.1 KB. Against today's shipped vocabulary it cuts bad-ends 19→11 and
lifts clear rate 68.3%→81.7% (n=60, p=0.077 — directional, not yet conclusive), and it
changes real decisions on real RTL (4/12 boards, reproduced across two independent build
paths). The large offline headline does not transfer automatically: the closest
cart-executor value measurement is −4.16 pills. The Pocket θ400 build has passed fit,
timing, synthesis-MIF and post-fit-netlist proofs; runtime play and a Pocket-specific A/B
remain open. A proposed approach-column fall-budget guard returned mechanism **NO_GO**:
the old final-column mutant removed the same four observed mislands, so that stream could
not discriminate the predicates.

**Also 2026-08-05 — a fidelity caveat worth stating plainly:** py65 (the CPU simulator most
offline experiments run through) agrees with the real RTL on only ~13% of *base-search*
move choices on real L11 boards. Tuck-logic gates that compare py65 against a Python
reference are unaffected and remain sound, but no py65-only result should be read as
predicting the silicon's actual move. Silicon A/Bs decide.

## How it works

- **Mapper 100** (`fpga/copro/CoproDrMario.sv`) = MMC1 banking + this block. A second 6502
  (`copro6502.v`, Arlet core) free-runs at the core master clock, with a host register
  window at `$5000–$51FF`. The game CPU writes the board + pill colors, pulses GO, polls
  DONE, reads back the chosen column + orientation. The shipping MiSTer core is
  **single-copro** (P2): the P1 window turned out to be stripped by the core integration
  (open bus — P1 was never actually wired), and the single-copro variant fits the DE10
  timing-clean at ~87% ALM. P1 in the CPU-vs-CPU duel carts is instead a deliberately
  slower **native 6502 depth-1 AI** (`DRP1NATIVE`) so matches stay watchable and unequal.
- **BoardEngine** (`fpga/copro/LeafEval.sv`) is the RTL accelerator at `$7000–$70FF`: a single
  `NODE` command does landing + placement + a capped targeted resolve + the full leaf eval,
  plus single-command snapshot/restore of the working boards. This is what collapsed the
  per-search-node cost and made depth-3 practical on hardware.
- **The cartridge** (`patch_cartridge_copro.py` → `drmario_copro.nes`) is a patched ROM whose
  every-frame hook auto-navigates to VS-CPU L11 and, in play, uploads each locked pill to the
  coprocessor and executes the returned move. It also carries a per-player **seeded tie-break**
  so the two same-strategy copros desync into distinct games (same evaluation, different
  near-tie resolution — not a strategy divergence).

## Validation chain

Every acceleration step is proven the same way before it reaches hardware:

1. **py65** — the 6502 search vs a Python golden (`tests/`, cell-exact).
2. **Verilator** — the RTL block vs the same board-suite goldens the 6502 primitives passed
   (`fpga/copro/tb_leafeval.cpp`: 205/205 leaf, 250/250 node), and the full mapper vs an oracle
   (`fpga/copro/sim_mister.cpp`).
3. **Quartus** — timing closed at 85.9 MHz; the generated firmware MIF is byte-verified against
   `copro_rom.hex` before every deploy.
4. **Hardware** — deployed to the MiSTer, pace + play confirmed live.

## Build / deploy

```bash
# SHIPPED firmware (depth-3 4-pill BoardEngine, CMD-6/7 DELTA engine) -> fpga/copro/copro_rom.hex
#   md5 c87e60a1; validated cell-exact vs the base build by the Verilator co-sim gate:
.venv/bin/python fpga/copro/dbg_build.py all 0   # writes copro_rom.hex (the ship firmware)
./fpga/copro/run_gate.sh                          # co-sim: delta moves == base moves (cell-exact)
# BASE reference only (py65-validates the search LOGIC vs decide_d3; NOT what ships):
.venv/bin/python fpga/copro/build_copro_d3.py     # writes copro_rom.base.hex (py65 gate). See FIRMWARE.md.

# auto-nav cartridge (level/speed via env)
DRLEVEL=11 DRSPEED=1 .venv/bin/python patch_cartridge_copro.py   # -> drmario_copro.nes

# FPGA core: copy copro_rom.hex into the NES_MiSTer tree, then
#   quartus_sh --flow compile NES   -> output_files/NES.rbf
# deploy NES.rbf + drmario_copro.nes to the MiSTer and launch.
```

The RTL sources here (`fpga/copro/CoproDrMario.sv`, `LeafEval.sv`) are the source of truth;
they are mirrored into a local `NES_MiSTer` checkout for Quartus synthesis.

## Further reading

- `INTEGRATION_SPEC.md`, `ROM_WIRING_PLAN.md` — cartridge/mapper wiring
- `DEPTH2_BUILD.md`, `DEPTH2_FEASIBILITY.md` — the depth-2 predecessor
- `VS_CPU_PLAN.md` — auto-nav VS-CPU demo design
- `CLAUDE.md` — memory map, tile encoding, mechanics reference

## Known open items

- **Root-action tucks (v3) — Pocket fit is proved; runtime/value is not.** The firmware,
  CANDLIST wiring, tier-3 vocabulary, RTL evidence, and θ400 Pocket clean fit are in (see
  “Updated” above). What remains is hardware runtime confirmation and the on-hardware
  comparison against the shipped brain. The leaf-gated shortcut was
  empirically refuted (+7.11 pills *worse*) — cross-column reach scored at full depth is
  the only design that survives. The fall-budget sensor rewrite needs a stream containing
  predicate-discriminating events before another value arm is justified.
- **Soak-rig display wedge (test harness only, not yet a play defect)** — the old “within
  6–30 minutes” claim is retracted. Both endpoints came from a watchdog now proven to fire
  on healthy play; 30 minutes was its rate limiter and 6 minutes was near its configured
  threshold floor. The only screenshot-confirmed recurrence interval is about 65 minutes.
  The v8 seed-30011 hold also reproduces on the unhardened cart at identical frames, but
  `srchGapMax=1199` cannot distinguish a pause from a wedge. Auto-reboot remains disabled
  until a killed-mutant discriminator works; recovery is operator-driven.
- **Cascade-resolve in the search: tested, rejected** — a full chained resolve halved solo
  clear-rate chasing combos into topouts; the capped resolve is the better player. (The
  *eval-side* chain credit is a different mechanism — that one ships in Combo Stomper.)
- **Personality knobs** — style presets (aggression, chain appetite, tempo) as first-class
  cart options for the final release build.
- **Next programs** — finish the ideal oracle-ceiling calibration; evaluate the
  post-landed-garbage response against its matched null; prove θ400 runtime on Pocket; and
  continue expert-player data work (DRMC footage → state/move pairs). Learned evaluators
  do not receive another dies-ahead arm until the oracle establishes that root re-ranking
  has measurable endpoint headroom.

Resolved since the last README revision, kept for the record: the v4 AB-cart stall family
is closed (a chain of driver defects, each reproduced and gated — see the `DRNAVESC` /
`DRWRETRY` / `DRPENDBOUND` / `DRSTALLWD` / `DRBUSYESC` flags in `patch_cartridge_copro.py`),
and hardware match state is now read exactly (save-state RAM capture: board, driver
mailbox, and watchdog state in one frame) instead of via screenshot OCR.
