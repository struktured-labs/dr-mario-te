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

## Current champion status — 2026-09-24

The north star is **best-in-the-world play under original-NES rules and real-time execution**.
This section records the strength program as of `h16-rollout-gated` tip `32ab3f30`
(2026-09-24). That branch holds the September campaign (55 commits from 2026-09-08 through
the tip). The result files cited here live on that branch. This update does not merge its
code, RTL, or firmware.

The on-prem human milestone named in the 2026-08-11 status (`5ddc320d`) is unchanged.
September did not land a new shipped image on `main`.

### Standing configuration

**Evidence-backed champion configuration:** winner leaf (`R_HOLES=20`) on the θ400 firmware
recipe `DRCHAIN=180` + `DRSTRAND=20` (Combo Stomper chain on the Childproof lineage).
`experiments/cvx/RESULT_FWLEAF.md` (`e675fbb7`) recommends that pair for the couch/booth
core and still lists a couch check as pending.

That recommendation is the experiment record, not a completed hardware promotion. At tip
`32ab3f30`, `experiments/cvx/AGENT_STATE.json` says `AA_DRMARIO_WINNER.mgl` (winner-leaf
image md5 `cd1fa389`, TE study cart `6c3c3168` from `100423d8`) was **staged and not
loaded**.

**Pending firmware candidate, not the champion:** `DRCHAIN=540` (`a_chw = 135`) on the same
winner leaf + strand20. Screen and holdout both pass. It awaits an owner-approved Quartus
build, hardware soak, and couch check (`experiments/cvx/RESULT_DOSEKNEE.md`, `9018627d`;
state commit `32ab3f30`).

Both of those results use `StrandedChainD3Decider`. The writeups state that tucks and veto
are not modelled.

Rulings from `5ddc320d` (2026-08-11) that this campaign did not reopen:

| Track | Evidence-backed state |
| --- | --- |
| **v8 REMATCH cart** | Shipped, gated and hardware-faithful (`c0082cb34259007854120d3d4ab9fa27`). Crash hardening and execution fidelity. No new strength claim over the human milestone already on record. |
| **Exact policy fidelity** | Full firmware co-sim matches 19/19 decisions and all 542/542 legal-candidate values, in debug and non-debug builds. |
| **Learned evaluator** | Stage-2 is **NO_GO**. Its −0.80 pp dies-ahead estimate crossed zero, and a dose-matched shuffled-label null did just as well. Changing 1.8% of plies reshuffled roughly 20% of outcomes. |
| **`d_spawn_h` tie resolver** | **NO_GO** at N=9,000: dies-ahead 0.200 pp worse, 95% paired CI [+0.022, +0.378], p=0.03846. |
| **py65 vs RTL** | py65 agrees with RTL on about 13% of base-search move choices. Tuck gates against a Python reference stay sound. Silicon A/B decides strength. |
| **Seed-30011 freeze** | Pre-existing, deterministic, identical frames on the unhardened cart. September result docs do not close its pause-vs-wedge question. The CvC freeze below is a separate classification. |

The 2026-08-11 "next strength probe" (spawn-lane penalty) finished **null**. `winsc2` vs the
then-champion: clear-rate +1.12 pp, 95% CI [−1.6, +3.8], McNemar p=0.4709, n=800. Not a
champion (`experiments/cvx/RESULT_SPAWNCOL.md`, `2e66ec65`).

### September 2026 results index

Ship calls after 2026-09-23 use **tap-out under the owner burst model** (gate b) and a
VS-race endpoint against a modelled 177-second human. Arena win rate stays a race metric:
`662e0c58` / issue #15 found that send, column, and halves knobs leave `vs_sim` at a maximum
**4.4% topout**.

#### `k_clock` — closed

The arm won the race arena, then failed tap-out, MEGADOSE, and gate (b).

| Check | Result | Where |
| --- | --- | --- |
| Race vs winner trunk | `k_clock=40` is 480/800 = **60.0%** (n=400). Python only. The same commit quotes a Hartford tap-out move of 50.2% → 42.8%; issue #16 later withdrew unpinned Hartford figures. The pinned table is the one to use (next row). | `5c9e0179` |
| Race vs holes80 | 537/800 = **67.1%** (seats 67.8% / 66.5%). Recorded as a hold: the clock term kept the race. | `3395dce4` |
| Pinned Hartford table | n=300/cell, `experiments/cvx/calib/`. Top-out at TRATE 0 / 0.020 / 0.025: holes80 **2.3 / 27.0 / 32.0%**, winner **16.3 / 42.3 / 49.7%**, kc40 **10.0 / 41.3 / 52.0%**. TRATE 0.020 is the documented couch-equivalent yardstick. | `2450e1c3`, issue #16 |
| Live MEGADOSE | L11 MED, seeds 40–47, n=8. k=0 cleared **7/8**, k=40 cleared **6/8**, delta **−12.5 pp**. Pre-registered bar was "not worse than −10 pp". **FAIL**. The writeup treats n=8 as one extra miss. | `experiments/cvx/PREREG_MEGADOSE.md`, `experiments/cvx/megadose_SUMMARY.json`, `e5c4154b` |
| Gate (b), winner trunk | Tap-out: holes80 **24.33%**, winner **40.50%**, kc40 **41.00%** (n=600). kc40 vs winner McNemar p=0.90. Median elapsed 613 s → 523 s. Speed, no survival gain. | `experiments/cvx/RESULT_GATEB.md`, `f81d9806` |
| Gate (b), holes80 trunk | holes80 + k_clock {10, 20, 40} tap-out **35.17 / 42.33 / 50.17%** vs holes80 24.33%. Monotonic harm. **Closed at the root and at the leaf** for the couch objective. | same file, `c66fe780` |

`RESULT_GATEB.md`'s earlier paragraph says the couch build should stay holes80. The
firmware-leaf result the same night replaces that ship call. The flashed CLOCK40 image
(rbf md5 `9e6ed9f5`, winner leaf, `DRCLOCK=14`; `experiments/cvx/CLOCK40_CVC.md`) is a
stability soak of that clock build and is not couch-eligible.

#### holes80 leaf on the θ400 + chain brain — harm

`experiments/cvx/RESULT_FWLEAF.md` (`e675fbb7`). Firmware-faithful arms, `DRCHAIN=180` +
`DRSTRAND=20`, gate (b), owner burst model, L11, cap 600:

| Block | n | winner tap-out | holes80 tap-out | holes80 − winner |
| --- | --- | --- | --- | --- |
| primary, seeds 36734+ | 600 | 2.83% | 5.50% | +2.67 pp [+0.50, +4.83], 15/31, p=0.026 |
| holdout, seeds 40134+ | 400 | 4.50% | 7.00% | +2.50 pp [−0.50, +5.75], 15/25, p=0.15 |
| pooled | 1000 |  |  | **+2.6 pp**, 30/56, p≈0.007 |

VS-race, n=300, 177 s human: winner leaf **88.0%** vs holes80 leaf **77.3%** (−10.7 pp
[−16.0, −5.3]). The holdout tap-out block alone is p=0.15; the file's reading uses the
pooled test together with the race loss. Same-seed context in that file: no-chain holes80
24.3% / winner 40.5% / chain180 **6.8%** / holes80+chain180 **13.0%** tap-out.

holes80 (`R_HOLES` 20→80) was measured earlier on a search **without** that chain term,
including an L11 transfer of tap-out 3.25% → 1.00% (−69%, n=2000, p<1e-5;
`experiments/cvx/RESULT_HOLES_L11.md`, `9449e6d0`). On the brain the θ400 firmware carries,
the leaf costs survival and race. Couch ledgers from 2026-09-12 (`85aec35d`) predate this
reversal.

#### CvC freeze — #131 soak-cart artifact

`AGENT_STATE.json` at `32ab3f30` records the Childproof CvC soak as a known **#131-class
wedge**. Issue #19 (closed 2026-09-24) is the mechanism writeup: deterministic freezes on
`drmario_cvc_tuckguard_08211ef4.nes`, classed as the #131 phase-dependent START-leak from
CvC autonav. Reported cycles in that thread: holes80 about 73 min (frame `d2f7200dffd7`),
Childproof about 22.5 min (frame `e2450dd338d6`). The couch TE cart `6c3c3168` is built
`DRHUMAN=1` and does not autonav START, so the thread's couch-relevance ruling is that the
couch cart is not exposed. There is no `RESULT_*.md` for this classification. The same
thread notes one inconsistency left open: a delivered START did not release the wedge on a
cart that carries `DRUNPAUSE`. The closing comment treats a CPU trace as optional and does
not call this a core defect.

#### `DRCHAIN=540` — screen and holdout pass, hardware still open

`experiments/cvx/RESULT_DOSEKNEE.md` (`9018627d`). Winner leaf + strand20, VS-race vs a
177 s human, 6 volleys/min, delta 2.65:

| Block | Race n | fw180 | fw540 | paired diff | Gate (b) tap-out |
| --- | --- | --- | --- | --- | --- |
| screen, seeds 36734+ | 300 | 88.0% | 95.3% | **+7.3 pp** [+3.3, +11.3] | 2.83% → 2.33% (−0.50 pp [−2.17, +1.00], n=600) |
| holdout, seeds 40134+ | 200 | 85.5% | 94.0% | **+8.5 pp** [+3.5, +14.0] | 4.50% → 3.00% (−1.50 pp [−4.25, +1.00], n=400) |

fw270 (+3.3 pp) and fw360 (+2.7 pp) were not significant on the screen. Opponent-aware chain
dosing is **null** (`experiments/cvx/RESULT_ADAPTIVE1.md`, `3177a5af`). The result file's
silicon path is a pinned-seed rebuild of the Childproof recipe (theta400dblcanon veto2fixa,
seed 13) at `DRCHAIN=540`, then soak and couch check. No such Quartus build is claimed.

#### Pocket θ400 runtime A/B — still not run

The 2026-08-11 fit proof stands: 18,262/18,480 ALMs (218 free), +1.682 ns setup slack, both
16,384-byte firmware-content proofs exact (`5ddc320d`). No commit on `h16-rollout-gated`
from 2026-09-08 through `32ab3f30` records a Pocket runtime or value A/B. Branch
`pocket-tuck-theta400` tip remains `4b542f10` (2026-08-16 22:44 −0400).

#### Other closed arms on the same branch

Early offline gains below were scored without the firmware chain term. They are not the
current ranking.

| Arm | Verdict | Where |
| --- | --- | --- |
| Convex height | Screen +5.0 pp reversed to −2.5 pp on validation. Closed with the winner's-curse note. | `RESULT_SPAWNCOL.md`; lane open `4a1a5c54` |
| Spawn-lane `winsc2` | Null. Not a champion. | `RESULT_SPAWNCOL.md`, `2e66ec65` |
| `wincombo` | Offline clear-rate GO: +2.20 pp, n=2000, p=0.016, L20 drip, on the then-champion leaf. | `RESULT_COMBO.md`, `9574e04c` |
| holes80 dose, no chain | L20 tap-out peaked at 80 (`ebff6c24`). L11 transfer is the row above. Superseded for shipping by `RESULT_FWLEAF.md`. | `ebff6c24`, `9449e6d0` |
| buried96 | Harm. Commit message: tap-out 13.0% → 21.7%, p<1e-4. No separate `RESULT_*.md` under `experiments/cvx/`. | `2b53036a` |
| Expert shape muxes | Harm or null. Family closed even with time priced into the leaf. | `ddfc7a92`, `RESULT_TIME1.md` |
| Time-priced leaf shapes | **Closed.** Travel time has to live in the search. | `RESULT_TIME1.md`, `b97e121c` |
| Static leaf gradient | 11/11 axes, 24 arms, zero improvements around the holes80 constants. | `RESULT_GRAD2.md`, `d7877f15` |

### Open decisions / next hardware steps

1. **Owner decision on `DRCHAIN=540`.** Approve or decline a Quartus build of the
   Childproof/winner recipe at that dose, then a hardware soak and a couch A/B against the
   standing `DRCHAIN=180` image. Offline screen and holdout are done. Silicon is not.
2. **Load the staged winner image.** `AA_DRMARIO_WINNER.mgl` was already staged at
   `32ab3f30` and had not been booted. That is the couch check `RESULT_FWLEAF.md` still
   lists as pending. It does not require the 540 dose.
3. **Pocket θ400 runtime and value A/B.** Fit and timing are the August proof. Play on the
   Pocket is still open.
4. **Leave closed unless a new pre-registration says otherwise:** `k_clock`; the holes80
   leaf on the θ400+chain brain; arena win rate as a ship criterion; the CvC freeze as a
   core or couch-cart defect.

Promotion still requires converging evidence: fewer identifiable blunders, no broad
clean-play regression, a gain over a dose-matched null, stronger opponent results, and
hardware-representative execution. A race-arena win, a py65-only win, or an offline pass
that omits the firmware chain term is not a ship.

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
  comparison against the shipped brain. As of 2026-09-24 that Pocket runtime/value A/B is
  still unrun: no commit on `h16-rollout-gated` through `32ab3f30` records one, and
  `pocket-tuck-theta400` is still `4b542f10` (2026-08-16). The leaf-gated shortcut was
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
  **2026-09-24:** a separate deterministic freeze on the holes80 and Childproof CvC soaks
  was classed as the #131 START-leak phase wedge on the soak cart
  (`drmario_cvc_tuckguard_08211ef4.nes`). The committed pointer is
  `experiments/cvx/AGENT_STATE.json` at `32ab3f30`; the repro times and the couch-cart
  ruling (TE cart `6c3c3168` is `DRHUMAN` and is not exposed) are issue #19. That
  classification does not close the seed-30011 pause-vs-wedge question above.
- **Cascade-resolve in the search: tested, rejected** — a full chained resolve halved solo
  clear-rate chasing combos into topouts; the capped resolve is the better player. (The
  *eval-side* chain credit is a different mechanism — that one ships in Combo Stomper.)
- **Personality knobs** — style presets (aggression, chain appetite, tempo) as first-class
  cart options for the final release build.
- **Next programs** — the open hardware steps in the 2026-09-24 status above: an owner
  decision on Quartus for `DRCHAIN=540`, a couch check of the staged winner-leaf θ400
  image, and the still-unrun Pocket θ400 runtime/value A/B. Learned evaluators stay
  **NO_GO** on the Stage-2 result already recorded (`5ddc320d`). Expert-player footage
  work continued on `h16-rollout-gated` (tourney-tape pipeline, `610f9123`) and is not
  re-summarized here.

Resolved since the last README revision, kept for the record: the v4 AB-cart stall family
is closed (a chain of driver defects, each reproduced and gated — see the `DRNAVESC` /
`DRWRETRY` / `DRPENDBOUND` / `DRSTALLWD` / `DRBUSYESC` flags in `patch_cartridge_copro.py`),
and hardware match state is now read exactly (save-state RAM capture: board, driver
mailbox, and watchdog state in one frame) instead of via screenshot OCR.
