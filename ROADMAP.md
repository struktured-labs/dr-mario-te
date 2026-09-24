# Dr. Mario AI — Roadmap

> **North star:** the strongest NES-native Dr. Mario player in the world, under a real
> time budget — no pause/freeze cheating. The brain lives in the cartridge's address
> space (enhancement-chip model: a coprocessor in the cart slot, SA-1/SuperFX lineage),
> playing as a legitimate second player on console-accurate hardware.
>
> Maintained by the project's AI coordinator; updated at every milestone.
> Last full pass: **2026-07-19**. Strength-program status revised **2026-09-24**
> from `h16-rollout-gated` tip `32ab3f30`. Numbers and file paths below are on that
> branch. This file does not merge that branch.

## Strength status — 2026-09-24

Detail, tables, and per-claim citations are in the README section **Current champion
status — 2026-09-24**. Short form:

- **Standing configuration:** winner leaf (`R_HOLES=20`) + θ400 firmware
  (`DRCHAIN=180` + `DRSTRAND=20`). Recommended for the couch core in
  `experiments/cvx/RESULT_FWLEAF.md` (`e675fbb7`). At the branch tip the matching
  couch image (`AA_DRMARIO_WINNER.mgl`) was staged and not loaded
  (`experiments/cvx/AGENT_STATE.json`, `32ab3f30`).
- **`k_clock` closed.** Race-arena holds at 60.0% vs the winner trunk (`5c9e0179`)
  and 67.1% vs holes80 (`3395dce4`). Then MEGADOSE **FAIL** (−12.5 pp, 6/8 vs 7/8,
  n=8; `e5c4154b`) and gate (b) shows no survival gain on the winner trunk (41.00%
  vs 40.50% tap-out) and monotonic harm on the holes80 trunk (35.17 / 42.33 /
  50.17% vs 24.33%; `experiments/cvx/RESULT_GATEB.md`).
- **holes80 leaf closed on the shipped chain brain.** Pooled gate (b) tap-out
  +2.6 pp worse than the winner leaf (n=1000, p≈0.007) and −10.7 pp in VS-race
  (`RESULT_FWLEAF.md`). Earlier no-chain holes80 gains, including the L11 transfer
  (`RESULT_HOLES_L11.md`), are not the ship ranking.
- **CvC freeze classed as the #131 soak-cart artifact** (issue #19;
  `AGENT_STATE.json` at `32ab3f30`). Couch TE cart `6c3c3168` (`DRHUMAN`) is the
  cart the issue thread says is not exposed. No `RESULT_*.md` carries this writeup.
- **`DRCHAIN=540` is the pending firmware candidate.** VS-race +7.3 pp on the
  screen (n=300) and +8.5 pp on the holdout (n=200); gate (b) tap-out not worse
  (`experiments/cvx/RESULT_DOSEKNEE.md`, `9018627d`). Awaiting an owner-approved
  Quartus build and hardware soak. Not built in this record.
- **Pocket θ400 runtime A/B still not run.** August fit proof stands (README,
  `5ddc320d`). `pocket-tuck-theta400` tip is `4b542f10` (2026-08-16).

### Open decisions / next hardware steps

1. Owner approves or declines Quartus of `DRCHAIN=540` on the Childproof/winner
   recipe, then soak and couch A/B against `DRCHAIN=180`.
2. Boot the already-staged `AA_DRMARIO_WINNER.mgl` for the couch check the
   firmware-leaf result still lists as pending.
3. Run the Pocket θ400 runtime and value A/B, or leave it explicitly deferred.
   September did not advance it.
4. Do not reopen `k_clock`, the holes80 leaf on the θ400+chain brain, arena win
   rate as the ship metric, or the CvC freeze as a core defect, without a new
   pre-registration.

Items under **Active**, **Next up**, and **Programs** were last edited 2026-07-19.
Where they disagree with this section, this section wins. They were not re-audited
against the September tree.

## Platform targets (both first-class)

| Platform | Status |
|---|---|
| **Analogue Pocket** (agg23.NES fork + copro, mapper 100) | ✅ Shipped — human-vs-depth-3 on real silicon |
| **MiSTer** (NES core + copro) | ✅ Shipped — CPU-vs-CPU duel live; human play awaits BliSSTer Rev.3 |
| Physical FPGA-in-cart for stock NES | 🔭 Someday — the literal SA-1 move |
| **P2-port peripheral** (vision → brain → controller; stock console, stock cart) | 🔭 Someday, bottom of list — enabled by the vision pipeline |

## Shipped milestones

- **2026-07-11** — FPGA coprocessor: depth-3 expectimax on a second 6502 @ 85.9 MHz
  in the cart's address space; zero-input demo cart plays VS-CPU L11 on MiSTer.
- **2026-07-18** — Analogue Pocket port (core trim 99%→65% ALM, +copro = 96%);
  human-vs-AI validated on real hardware. **Anytime/no-freeze steering** (v2): AI
  plays under real gravity, no pauses — 2× throughput vs freeze, A/B-proven.
- **2026-07-18** — Household-coached eval terms: temporal discount, excavation,
  hanging-half (all py65-gated, cross-validated, in firmware).
- **2026-07-19** — **Combo brain**: color-aware buried (stop taxing correct covers)
  + retuned excavation/readiness weights. Obvious-move take-rate **66.5% → 85.2%**
  (236-scenario adversarial suite), L11 regression clean. Live on both platforms.
- **2026-07-19** — **Study mode (TE lineage) complete**: pause shows frozen board +
  falling capsule + **both players' next-pill previews** + STUDY text, per-mode
  positioned (1P/2P/VS all validated). **TE v6 published on romhacking.net.**
- **2026-07-19** — **Fair driver shipped**: zero gravity pins (strictly fairer than
  every prior build), rotation pre-phase, feasibility-gated retargeting, orientation
  map fix — validated by hardware A/B after the unit tests missed a placement bug the
  silicon caught. Patcher divergence root-caused (nav gate); quarantine lifted;
  clean builds from `copro-canonical` are the ship path again.
- **2026-07-19** — **R4–R7 brain validated**: obvious-move take-rate **93.6% raw /
  97.0% widened** (clears the 95% gate), L11 100%. Cell-exact RTL + firmware port.
- **2026-07-22** — **R47 on silicon**: the 85.9 MHz timing wall (field freeze on
  Pocket) solved structurally — copro moved to its own clock domain (21.47 MHz,
  SDRAM keeps 85.9 exclusively; +2.2 ns margin) on Pocket; score-combine pipeline
  recovers full speed on MiSTer. **TE v7 (Codex)**: title-screen TRAINING EDITION
  branding + STRUK LABS credit footer.

## Active (in flight)

> Strength-program status as of 2026-09-24 is the section above, not this July list.

- **TE v8.2**: shipped. See `release/RELEASE_NOTES_V8_2.md`. v9 remains a release
  candidate (`release/RELEASE_NOTES_V9.md`), unchanged by the September strength
  campaign.
- **Driver rev 2**: confidence-gated slam (commit when the search's answer is
  stable, not when it's exhaustively confirmed) + speed-aware gates — closes the
  human tempo gap on obvious placements and the late-game search-vs-gravity
  crossover; primary commit mechanism at the Pocket's new clock.
- **E1 endgame regime**: route-aware kill costs (dig / scaffold-through /
  under-clear) with regime switching by virus count × gravity speed — the fix for
  deep-buried endgame stalls.
- **Expert corpus (DRMC 2017–2026)**: **96 GB banked** (2024 championship + most
  of 2025 + regionals + 2021); champions table 2017–2024 complete; full bracket
  database reconstructed (brackets.json); remaining years rate-limit-walled.
- **LLAPI/BliSSTer runway**: port branch ready for real-controller P1 vs AI P2 on
  MiSTer (board arrived; install pending).

## Next up

- **Incremental leaf eval in firmware** (validated 6.1×/leaf, not yet deployed) —
  recovers the Pocket clock change and dissolves the late-game crossover entirely.
- **Vision pipeline**: broadcast footage → (board, move) pairs at scale.
  Calibrated OCR exists; needs a learned cell classifier. Unblocked (2024 footage
  is complete); the gate to everything below.
- **Tuck generation**: the pro move space (weave down, last-second snap) — new
  placement class for the search + driver.
- **Publication**: paper lane (enhancement-chip AI, fairness framework, the
  DRMC benchmark) — arXiv → IEEE CoG 2027. Positioning note: prior art exists
  and is credited — meatfighter's 2017 real-time depth-2 Dr. Mario AI (emulator
  brain; ★ source review 2026-07-28: it SUSPENDS GRAVITY while manoeuvring and
  writes capsule state into RAM, so "fair/input-only under the falling-piece
  deadline" is OURS to claim — see paper-lane `RELATED_WORK.md` #1, re-rated
  HIGH→MODERATE), and Seta's ST010/ST018 cart chips that shipped game AI in the
  90s; our conjunction (in-cart, hardware-accelerated depth-3, fair second
  player, benchmarked) is the claim, not "first AI."

## Programs (longer horizon)

- **Expert-agreement scoring**: ship brain vs champions' actual tournament moves —
  the first benchmark corpus for competitive Dr. Mario play. Then pattern mining
  (principled term weights) and personalized coaching reports (the household loop,
  industrialized, pointed both ways).
- **One brain, N personas**: universal trunk trained on the full corpus (the
  "beats all styles" mainline) + small per-player style heads (NNUE/LoRA-scale),
  selectable at runtime via a mailbox byte. One FPGA image, pick your opponent.
  Companion: a Quarto deck with LLM-written scouting reports per persona.
- **Native-AI distillation**: shrink/memoize/port the copro brain down to the pure
  2A03 budget so the IPS-patchable TE release offers real AI on stock hardware and
  every emulator. (Publishes only past the author's embarrassment bar.)
- **Release channels**: TE patches on romhacking.net (everyone) · FPGA cores on
  GitHub (MiSTer/Pocket faithful) · custom emulator core implementing the copro
  (RetroArch crowd, medium effort, spec in hand).

## Events

- **Retro World Expo, Hartford CT — Sept 12–13, 2026** (date has passed): studio
  showcase (this project + Quintra + Penta Dragon DX + Cowardly Irregular).
  Couch ledgers from that weekend are on `h16-rollout-gated` (`85aec35d`). They
  predate the 2026-09-23 firmware-leaf reversal, so they are not the standing
  strength ranking. Same venue hosted the DrMC 2025 Connecticut Regional.

## Parked

- Dual-copro parallel search (multicore) — until MiSTer controllers (BliSSTer).
- Cascade-aware node-resolve — measured negative (chasing combos = topouts).
- Depth-4 at current eval weights — measured negative (horizon effect).
- **Closed in September 2026** (evidence on `h16-rollout-gated`; see the README
  results index): `k_clock` after the race-arena holds; holes80 leaf on the
  θ400+chain brain; static leaf gradient (11/11 axes); time-priced leaf shapes;
  expert shape muxes; buried96; spawn-lane `winsc2`; convex height. Opponent-aware
  chain dosing was null (`RESULT_ADAPTIVE1.md`). `DRCHAIN=540` is the dose that
  stayed open, and it is waiting on hardware rather than on another offline arm.
