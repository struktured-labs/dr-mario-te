# Paper outline — "A Fair, Real-Time Dr. Mario AI as an NES Enhancement-Chip Coprocessor"

> Founding skeleton for the publication lane. Target venue: **IEEE CoG 2027** full paper
> (8 pp, IEEE 2-column, double-blind) — see `VENUES.md`. Overflow lands in the **IEEE
> Transactions on Games** journal extension. Positioning and every "first" here are
> constrained by the prior-art sweep in `RELATED_WORK.md`; the headline claims are drafted
> in `CLAIMS.md`. Last updated 2026-07-22.

## Working title (candidates)

1. **"An Enhancement-Chip AI: Depth-3 Expectimax Dr. Mario on a Cartridge Coprocessor, Playing Fair"**
2. "Gravity Is the Budget: A Fair, Real-Time Dr. Mario AI on Period-Accurate Hardware"
3. "Dr. Mario in the Cart Slot: A Second-6502 Coprocessor That Plays as a Fair Opponent"

Recommendation: title #1 (leads with the two defensible novelties — in-cart coprocessor
and depth-3 expectimax — and the fairness hook). Keep "first" out of the *title*; earn it in
the contributions list with the qualifiers from `CLAIMS.md`.

## Abstract (≈200 words)

Dr. Mario (NES, 1990) is a competitive falling-block virus-clearing game with a live
30+-year tournament scene but — unlike its sibling Tetris — almost no AI literature. We
present a depth-3 expectimax player with a hand-tuned, Dr. Mario-specific evaluation, and,
more importantly, a *deployment*: the search runs on a **second 6502 core plus a custom RTL
board-evaluation accelerator, embedded as a coprocessor in the cartridge's address space**
(a custom NES mapper) and synthesized on two FPGA platforms (MiSTer, Analogue Pocket). The
AI plays as a legitimate second player under real gravity — **no pause, no world-stop**: the
falling pill's own descent time is the entire compute budget. We contribute (i) the first
Dr. Mario AI on period-accurate hardware and the first with quantified strong-play
benchmarks; (ii) a *fairness-as-methodology* discipline — gravity-as-budget, anytime commit,
and continuous-integration audits that fail the build if the agent ever stalls the game
clock — with two case studies where silicon validation caught cheating/bugs that green unit
tests missed; (iii) an eval-engineering ablation ladder (obvious-move agreement
66.5%→85.2%→93.6%) with honest negative results; and (iv) the first public benchmark corpus
for the game, drawn from a decade of championship footage. Solo, the player clears 100% of
Level-11 boards in cell-exact simulation.

## Contributions (the claim list — mirror `CLAIMS.md`, keep each survivable)

- **C1 — First strong Dr. Mario AI on original/period-accurate hardware.** Precisely: the
  first Dr. Mario agent to execute *on console-class silicon as an in-cartridge coprocessor*
  (no modern computer in the decision loop); the first to use *depth-3 expectimax* over pill
  randomness; and the first *quantified/benchmarked* player. Explicitly distinguished from
  meatfighter (2017), an emulator-hosted PC agent (see `RELATED_WORK.md` §Dr.Mario).
- **C2 — The enhancement-chip deployment model.** A retrofitted, hardware-accelerated,
  *independent fair second player* on an *unmodified commercial action game*, with a custom
  RTL leaf-evaluation accelerator. Extends the SA-1 / Super FX lineage and, more pointedly,
  the *AI-in-cart* Seta ST-series lineage (ST010 racing, ST018 shogi) it must cite.
- **C3 — Fairness as methodology.** Gravity-is-the-budget (a physics-derived real-time
  deadline), anytime best-so-far commit, frame-level gravity-pin audits in CI, and a
  four-stage validation hierarchy (py65 → Verilator → Quartus timing → silicon). Two case
  studies where silicon caught what green tests missed.
- **C4 — The DRMC expert corpus.** The domain's first benchmark: reconstructed brackets,
  a player/appearance database, and a plan for expert-agreement scoring.
- **C5 — The eval-engineering ladder.** Measured ablations *and* measured negatives
  (cascade-chasing, depth-4-at-current-weights, reflex fast-path, route-potential farming).
- **C6 — A competitive theory of Dr. Mario.** Regimes by virus-count × gravity-speed, three
  kill routes, drought investment, and a ROM-exact gravity/tempo analysis.

Note: C6 is the least "AI" of the six and the first to cut for length — it is the natural
core of the ToG journal extension. For an 8-page CoG paper, lead with C1–C3, summarize
C4–C5, and gesture at C6.

---

## Section-by-section skeleton

### 1. Introduction (≈1 col)
Dr. Mario: rules in two sentences (place two-color pills; four-in-a-line of a color clears;
erase all viruses to win; it is a *versus* game — clears send garbage). The puzzle: a game
with a 30-year competitive scene (DRMC) and effectively *no* AI, while its sibling Tetris has
a deep literature. Our answer is not just an algorithm but a *place to put it* — the
cartridge slot — and a *discipline* — fairness under real gravity. State C1–C6. One
paragraph explicitly pre-empting the closest prior art (meatfighter; Seta ST-chips;
StackRabbit; Puyo AI) so the reviewer sees we know the neighborhood.
- *Backs:* `README.md` (milestones), `ROADMAP.md` (north star), `RELATED_WORK.md`.

### 2. Background & Related Work (≈1.25 col)
Four threads, each a short paragraph, adversarially honest (see `RELATED_WORK.md`):
(a) **Falling-block AI** — the hand-eval+search lineage (Dellacherie/Fahey/El-Tetris;
CE/GA/ADP learning; StackRabbit as the strong NES-Tetris analog). (b) **Dr. Mario
specifically** — meatfighter 2017 (the one real prior agent), Nintendo's shipped CPU
opponents, TAS ≠ agent, complexity (Dr. Mario NP-hardness *open*, Tirmazi 2024). (c)
**AI on period hardware / enhancement chips** — SA-1/Super FX (graphics/math) vs the Seta
ST-series (AI-in-cart), Deep Blue/Hydra (hardware game-search ancestor), TASBot (replay ≠
reaction), MarI/O (emulator). (d) **Real-time fairness** — AlphaStar/OpenAI Five/FightingICE
(fairness-by-constraint precedent), anytime search (Dean&Boddy, Zilberstein, Korf, ARA*),
real-time RL (Ramstedt&Pal). Close by stating exactly what is left unclaimed by all of it.
- *Backs:* `RELATED_WORK.md` (every citation), `REFERENCES.bib`.

### 3. Dr. Mario as an AI Problem (≈0.75 col)
Formalize: board 8×16, viruses fixed at start, current pill + one-pill preview + uniform
random tail; objective = clear all viruses; *versus* = tempo + garbage. Why expectimax
(random next pill = chance node) and why depth is bounded (real-time deadline; combinatorial
objective — cite Tetris NP-completeness as the analogous justification). Define the
"obvious-move agreement" metric used later.
- *Backs:* `CLAUDE.md` (tile/mechanics), `tests/nes_d3_golden.py`, fuzz-suite schema.

### 4. The Player: Depth-3 Expectimax + Hand-Tuned Eval (≈1 col)
The algorithm (stated as a *faithful member of the falling-block lineage*, not an
innovation): progressive-deepening over a shallow-sorted shortlist; expectation over the
pill subset at the third ply; the evaluation terms (virus adjacency, buried/matched-cover,
readiness, excavation `g_excav`, hanging-half `g_hang`, temporal discount). Emphasize the
Dr. Mario-specific terms as the domain contribution. Report solo strength here (L11 100%
clear/win, cell-exact). Keep it honest: depth-3 expectimax + linear eval is textbook; the
novelty is downstream (§5–§6).
- *Backs:* `build_te_v8.py`/`build_copro_d3.py`, `fpga/copro/LeafEval.sv`, `tests/test_eval_terms.py`,
  `tests/test_leaf_d3.py`, `tmp/final_regress.out` (L11 100%, excav 8/8, dual 4/4),
  commits `c20d5f2` (excav/hang), `dde806d` (temporal discount).

### 5. Eval Engineering: An Ablation Ladder with Negatives (≈1 col) — *results-heavy*
The 236-scenario adversarial fuzz suite (edge-virus-match, dual-end-general, hang-general,
horiz-vs-vert-pref) as a *unit-testable proxy* for play strength. The ladder:
combo→+R4→+R4+R6→+R4+R6+R7, obvious-move take-rate **66.5%→85.2%→93.6% raw / 97.0% widened**,
L11 100% held throughout. Then the **negatives, reported as first-class results**: cascade
chained-resolve (100%→50% solo — combo-chasing topouts), depth-4 at current weights (horizon
effect), the reflex "complete-a-clear" fast-path (fires 67%, matches deep search only 19.4%),
route-potential farming. The thesis: in a data-poor domain, disciplined eval engineering with
published negatives is the honest substitute for large-scale learning.
- *Backs:* `tmp/r4r6r7_sweep.out`, `tmp/final_regress.out`, `tmp/fuzz_{edge-virus-match,
  dual-end-general,hang-general,horiz-vs-vert-pref,e1-endgame}.json`, `tmp/fuzz_user-examples.json`,
  README "known open items" (cascade rejected), ROADMAP "Parked" (depth-4, cascade),
  `TEMPO_DESIGN.md` §5 (reflex 19.4%), commit `86d9027`→combo (66.5→85.2), `fd8e495` (R47).

### 6. Fairness as Methodology (≈1.25 col) — *the paper's spine; lead contribution*
6.1 **Gravity is the budget.** No pause/freeze; the pill falls the whole time it thinks;
anytime firmware live-publishes best-so-far into the mailbox (`0xFF` = not-yet-valid); the
driver weave-steers under natural gravity and only slams post-commit. Frame this as a
concrete instance of the real-time MDP (Ramstedt & Pal) and anytime search (Korf, ARA*), not
a new paradigm — then state the genuinely novel part.
6.2 **Fairness as a tested invariant.** The `froze_hist` gravity-pin audit: a CI check that
records, per frame, whether the driver pinned the drop timer, and *fails the build* if the
agent ever stalls the clock to think. This is the novel methodological device — no prior
game-AI or real-time-RL work enforces a build-failing frame-level anti-stall audit.
6.3 **The validation hierarchy.** py65 (cell-exact search) → Verilator (RTL vs the same
goldens: 205/205 leaf, 250/250 node) → Quartus (timing closed at 85.9 MHz; MIF byte-verified)
→ silicon (MiSTer/Pocket A/B).
6.4 **Two case studies where silicon caught what green tests missed.** (a) The *pinned-gravity
first cut*: uninitialized `PEND1` boot garbage pinned P1 gravity — capsule stuck at top,
invisible to unit tests, seen only on Pocket hardware (`54c1e5f`). (b) The *cold-mailbox slam*:
v1 slammed the shallow-garbage argmax ~1 frame in → ~300 ms lock-suicides; fixed by the
anytime armed-guard (`51cef9a`→`822579e`); and the *DRROTFIX clear-regression* where a
decision-level test passed but the pill *landed* the wrong (unmapped) orientation and cleared
~0 on MiSTer — caught by A/B, then locked in by a full-pill *placed-orientation* macro test
(`8d7ba75`, macro added `1d6846a`). The argument: **the validation hierarchy is the
contribution; a green unit test is necessary, not sufficient, for a real-time on-hardware agent.**
- *Backs:* `tests/test_driver_fidelity.py` (the froze_hist audit + the macro gate — read it;
  it is the single best artifact for this section), `STUDY_PAUSE_NOTES.md`, README validation
  chain, commits `54c1e5f`, `51cef9a`, `822579e`, `6832cc0`, `8d7ba75`, `1d6846a`, `2efaa1f`.

### 7. The Enhancement-Chip Deployment (≈1 col) — *systems core; C2*
Mapper 100 = MMC1 banking + a second Arlet 6502 free-running at the 85.9 MHz master clock,
host register window `$5000–$51FF` (one per player; dual-copro so P1/P2 never time-share).
The **BoardEngine** RTL accelerator (`$7000–$70FF`): a single `NODE` command does
land+place+capped-resolve+full-leaf-eval + snapshot/restore — this is what made depth-3
practical (Deep-Blue-style hardware evaluation at the search leaves). The latency ladder
(400 s → 100 s → 50 s → 4 s → ~1 s/move). One canonical RTL source feeds MiSTer and the
Analogue Pocket (core trimmed 99%→65% ALM to fit the copro at 96%, timing closed). Position
against the ST-series: *they* shipped the game's own turn-based opponent as software on a
general CPU built into a purpose-designed cart; *we* retrofit an independent fair player onto
an unmodified real-time game, with a custom RTL evaluator, in reconfigurable logic.
- *Backs:* `README.md` (how-it-works + latency table), `INTEGRATION_SPEC.md`, `ROM_WIRING_PLAN.md`,
  `HARDWARE_COPRO_CART.md`, `POCKET_PORT.md`, `fpga/copro/CoproDrMario.sv`, `LeafEval.sv`,
  `copro6502.v`, `patch_cartridge_copro.py`, commits `1fb845a`, `750724f`, `62a3067`, `d382d42`, `37ebd1d`.

### 8. Tempo & the Competitive Regime (≈0.75 col) — *condense; C6 lives fully in the journal ext.*
The ROM-exact gravity curve (gravityTable `$A795`, speedBase LOW/MED/HI = 15/25/31; L11 MED
= 19→5 f/row over a game). The tempo result: 80.6% of search time is confirmatory; a
confidence-gated slam reclaims ~0.68 s/pill; and the *feasibility crossover* where, under
fast late gravity, the pill lands before depth-3 finishes — so anytime commit flips from
optimization to necessity. Regimes as f(virus_count, gravity-speed). This is where the
fairness constraint becomes a *competitive theory*.
- *Backs:* `tmp/tempo/TEMPO_DESIGN.md` (whole doc), `tmp/tempo/measure_fall.py`,
  `measure_stab.py`, `measure_gate.py`, `tmp/tempo/gate_rows.pkl`, `gravity-table` findings.

### 9. The DRMC Benchmark Corpus (≈0.5 col) — *C4*
A decade of championship footage (DRMC 2017–2026; 96 GB banked): reconstructed bracket
database (`brackets.json`), an 86-player appearance/champion database (`players.json`), and
the vision→(state,move) pipeline plan for expert-agreement scoring (the first quantitative
Dr. Mario benchmark). Ethics/sourcing note: local-transcript / no-scrape provenance;
personal recordings marked never-publish.
- *Backs:* `/mnt/data/drmario/expert_vods/{brackets.json,players.json,
  enumeration_drmc_channel_2025plus.txt}`, ROADMAP "Expert corpus", README "next programs".

### 10. Evaluation (≈0.75 col)
Solo: L11 100% clear/win in cell-exact sim (6 seeds, 89–153 pills). Suite: the 236-scenario
ladder. Hardware: pace confirmed live on MiSTer + Pocket; human-vs-AI validated on Pocket.
**The RWE Hartford (Sept 12–13, 2026) live human-eval session** is the headline evaluation —
pre-registered protocol (win/clear rate vs demonstrated-caliber humans, fairness/latency
telemetry, perceived-difficulty survey). Honest limitation: hardware match clear-rate OCR is
currently blind (README known item) — state it.
- *Backs:* `tmp/final_regress.out`, `tests/`, README known-open-items, ROADMAP Events,
  `CLAIMS.md` (what the demo must furnish).

### 11. Limitations & Future Work (≈0.4 col)
OCR clear-rate blindness; single-eval-family (no learned NNUE yet); depth-4/cascade
negatives; tuck generation; dual-copro parallel search; native-2A03 distillation; the
one-brain-N-personas program. Frame negatives as scoped, not failures.
- *Backs:* ROADMAP "Next up"/"Programs"/"Parked", README known items, `DISTILLATION_NOTES.md`.

### 12. Conclusion (≈0.25 col)
The cartridge slot is a legitimate place to put a game AI, and real gravity is a legitimate
budget. Restate C1–C3 as the durable contributions.

---

## Artifact → section map (quick index for the writing pass)

| Section | Primary repo artifacts (paths relative to repo root unless noted) |
|---|---|
| 1 Intro | `README.md`, `ROADMAP.md` |
| 2 Related work | `paper/RELATED_WORK.md`, `paper/REFERENCES.bib` |
| 3 Problem | `CLAUDE.md` (mechanics/tile encoding), `tests/nes_d3_golden.py`, fuzz-suite schema |
| 4 Player | `build_copro_d3.py`, `fpga/copro/LeafEval.sv`, `tests/test_eval_terms.py`, `tests/test_leaf_d3.py`, `tmp/final_regress.out` |
| 5 Eval ladder | `tmp/r4r6r7_sweep.out`, `tmp/final_regress.out`, `tmp/fuzz_*.json`, `TEMPO_DESIGN.md §5` |
| 6 Fairness | **`tests/test_driver_fidelity.py`** (froze_hist audit + macro gate), commits `54c1e5f`/`51cef9a`/`822579e`/`6832cc0`/`8d7ba75`/`1d6846a` |
| 7 Hardware | `INTEGRATION_SPEC.md`, `ROM_WIRING_PLAN.md`, `HARDWARE_COPRO_CART.md`, `POCKET_PORT.md`, `fpga/copro/{CoproDrMario,LeafEval}.sv`, `copro6502.v`, `patch_cartridge_copro.py` |
| 8 Tempo | `tmp/tempo/TEMPO_DESIGN.md` + `measure_{fall,stab,gate}.py` |
| 9 Corpus | `/mnt/data/drmario/expert_vods/{brackets,players}.json`, `enumeration_drmc_channel_2025plus.txt` |
| 10 Eval | `tmp/final_regress.out`, README known items, `CLAIMS.md`, ROADMAP Events |
| 11 Limitations | ROADMAP (Next/Programs/Parked), `DISTILLATION_NOTES.md` |
| dev record | `git log --all --oneline` (214 commits: Phase-0 RL → depth-2 cart → depth-3 FPGA copro → Pocket → fair driver → R47 brain) |

## Figures & tables to build (shot list)

- **F1** System block diagram: NES core ↔ mapper-100 window ↔ copro 6502 + BoardEngine RTL (the money figure).
- **F2** The validation hierarchy (py65→Verilator→Quartus→silicon) with the two case studies annotated as "caught here, not there."
- **F3** Latency ladder (400 s→~1 s/move) as a bar/step chart.
- **F4** The eval ablation ladder (66.5%→85.2%→93.6/97.0%) + the negatives as a companion panel.
- **F5** ROM-exact gravity curve (19→5 f/row) with the feasibility-crossover marked.
- **T1** Related-work matrix: {in-cart? on-period-silicon? real-gravity? fair-opponent? benchmarked?} × {ours, meatfighter, StackRabbit, ST018, Puyo bots, TASBot} — the single most persuasive table for the novelty claim (draft in `RELATED_WORK.md`).
- **T2** Solo L11 soak (seeds, pills, clear/win).
- **F6** A board photo from real MiSTer/Pocket play (the "it's really running on the console" shot).

## Open decisions for the team lead
- **8pp CoG vs go-long at ToG first?** Recommend CoG 2027 full paper as primary; ToG extension after (see `VENUES.md`).
- **Head-to-head vs meatfighter?** Strongly recommended — it is the one experiment that converts C1 from "arguable" to "demonstrated" (`CLAIMS.md`).
- **Correct the "no enhancement chip ran AI" line** in `README.md`/`ROADMAP.md` before the arXiv post (the ST-series refutes it; flagged to the lead separately).
