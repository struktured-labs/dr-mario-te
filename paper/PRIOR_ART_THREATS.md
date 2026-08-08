# Prior-Art Threat Register — adversarial synthesis of four sweeps

> **Status:** NEW FILE, 2026-07-28. Does **not** replace [`RELATED_WORK.md`](RELATED_WORK.md);
> it is the *delta plus re-ranking* produced by four independent sweeps (academic, code/bots,
> hardware/in-cart, fairness/claim-stress). §9 lists exactly what to merge back into
> `RELATED_WORK.md`, and §10 what to add to `REFERENCES.bib`.
>
> **Framing rule (standing, non-negotiable):** never disparage a prior author. State
> methodological differences factually and let the reader draw the conclusion. "His agent is
> not constrained by the falling-piece clock" — not "he cheats." This applies with extra force
> to §2.1 and §2.4, which describe *living, active, unpublished* contemporaneous work.
>
> **Link check:** every URL in §2 and §3 was HTTP-verified 2026-07-28. `drmario-native`
> confirmed **404 / private** — it must not be cited or characterized. Canaan et al. title,
> Guida & DeMaio title/authors/venue, and the Videopac C7010 processor fact were verified
> against source text; the C7010 "6 levels = 1–6 plies" figure was **not** reproducible from
> the two sources checked and is marked UNVERIFIED below.

---

## 1. Bottom line — what changed

`RELATED_WORK.md` (as of 2026-07-28) is *correct on everything it covers* and its two
load-bearing corrections stand. The problem is coverage. Four items that hit our top-ranked
claims hardest are **absent from it entirely**:

1. **Two active, contemporaneous Dr. Mario AI programs** (`EthanOConnor/drmc-rl`,
   `dmwit/nurse-sveta`+`dasyuridia`) — one with a live bridge for playing humans online, one
   with a real-NES hardware path. Neither has published. This converts several of our claims
   from "defensible" to "on a clock."
2. **StackRabbit at source level.** `RELATED_WORK.md` Thread A treats it as a distant Tetris
   analog. It is in fact input-only (`writebyte` count: 0), derives placement reachability
   from the ROM's own gravity, self-imposes reaction-time and tap-rate caps, and its
   `console_client` recovers board state from *video* on a real NES. On one fairness axis it
   is **stricter than we are.** It sits directly on top of `CLAIMS.md` §7 Differentiator 0.
3. **The in-cart-coprocessor lineage is 11 years older and 26 years more recent than we
   thought** — Philips Videopac C7010 (1982) at one end, SuperRT on a DE10-Nano wired to a
   SNES cart bus (2021) at the other. ST018 is the *middle* of that lineage, not its edge.
4. **A venue collision.** "AI on retro hardware, running on a physical NES cartridge" was
   presented at an **AIIDE workshop in Nov 2025** (our stated fallback venue), and the
   canonical AI-vs-human fairness taxonomy is a **CoG 2019** paper (our primary venue). Both
   are mandatory citations we currently do not make.

**Net effect on the paper's posture:** the centre of gravity must move off *capability*
("strong Dr. Mario AI") and off *fairness-as-property* ("input-only, real gravity") — both
are occupied — and onto **measurement + deployment locus + mechanized enforcement**, which
after four sweeps remain genuinely unoccupied.

---

## 2. Top 5 threats, ranked

Ranked by damage to the claims we currently lead with, not by how famous the work is.

---

### THREAT #1 — `EthanOConnor/drmc-rl` (public repo, active through 2026-07-03)
**Tier: CRITICAL. Novel dimension: this is a priority race, not static prior art.**
<https://github.com/EthanOConnor/drmc-rl> · companion `drmario-native` is **private (404)**

Independent, contemporaneous Dr. Mario work with near-total overlap on the software side:
SMDP-PPO over exactly-enumerated placements; exact reachability search with exact frame costs
(`drm_reach_bfs_v4`) and a CUDA planner reported bit-exact against it; γ^τ discounting over
frame durations; 1P **and 2P VS**; a PFSP league with exploiters; `tools/tournament.py` with
Elo/Wilson intervals and **SPRT change gates**; a documented human-corpus integration; and
checkpoints named at ~530M training steps. `docs/DESIGN_TOP_PLAY.md` is titled *"Beating
Strong Humans at Dr. Mario."* `docs/LIVE_BRIDGE_PROTOCOL.md` specifies a frontend-agnostic
per-frame bridge whose reference client targets **fcadefbneo (Fightcade)** — i.e. a
configuration for playing human opponents online, with reported p50 17 ms / p95 33 ms plan
latency. It reads Dr. Mario RAM per frame and applies per-frame controller buttons.

**Undercuts:**
- `OUTLINE.md` **C1** — "the first *quantified/benchmarked* player." Their tournament harness
  with SPRT gates is a benchmark; it is simply unpublished today.
- `OUTLINE.md` **C4** — "the domain's *first* benchmark" (DRMC corpus).
- `CLAIMS.md` §3 **Formulation C** — "the first documented instance of an AI beating a
  champion-caliber human at Dr. Mario." A Fightcade-connected agent can produce that result
  before RWE Hartford (Sept 12–13) without any hardware.
- `CLAIMS.md` §7 **Differentiator 2** — "built for competitive play, not solo survival" is
  stated only against meatfighter; a PFSP-league VS agent occupies it squarely.

**Defensible reformulation:**
> Drop "first" from every *strength/benchmark* claim and re-cast them as **first published**,
> with the date and the artifact named. Move C1's weight entirely onto the **deployment
> locus**: *"the search executes on console-class silicon inside the cartridge address space,
> with no general-purpose computer anywhere in the decision loop."* That predicate is
> untouched by drmc-rl, which is a host-side agent driving an emulator frontend over a bridge.
> Re-cast C4 from "the first benchmark" to **"a released, reproducible expert corpus derived
> from documented tournament brackets"** — and only if we actually release it.

**Actions:** (a) cite as independent contemporaneous work in the neutral, standard form — name,
repo, access date — and characterize **only** what the public repo contains; (b) do **not**
cite, name, or infer anything about the private `drmario-native`; (c) set a monitor on the
repo and on arXiv cs.AI/cs.LG for a Dr. Mario preprint; (d) treat the RWE date as a **release
deadline**, not a milestone — post the arXiv preprint on the solo floor + systems contribution
without waiting for human-versus results.

---

### THREAT #2 — StackRabbit (Greg Cannon, 2021), read at source level
**Tier: CRITICAL to our #1-ranked axis.**
<https://github.com/GregoryCannon/StackRabbit>

`RELATED_WORK.md` currently concedes only "overlaps us on real-NES + real-gravity." The source
review is materially worse for us than that:

| Property | StackRabbit, as implemented |
|---|---|
| RAM writes | **none** — `writebyte` count 0 in `src/fceux/stackrabbit.lua`; actuation is `joypad.set` only. The two `emu.pause()` calls are debug assertions on mis-prediction, not gameplay control. |
| Gravity | unmodified; plays past level 29 (1 frame/row) |
| Gravity-derived computation | `move_search.cpp` takes `gravity` from `getGravity(level)`, simulates `isGravityFrame`, terminates candidates on lock — **the reachable-placement set is derived from the game's own fall speed** |
| Human-fairness caps | self-imposed and parameterized: `REACTION_TIME_FRAMES = 18` (300 ms) plus an `INPUT_TIMELINE` tap-rate mask with 13 presets (10 Hz … 30 Hz) and DAS-charge modelling |
| Real hardware | `src/console_client/` drives a real console from a Raspberry Pi, recovering board state from **video capture** |
| Enforcement | **none** — the only workflow is an emscripten build-and-release; `move_search_test.ts` is not wired into CI |

**Undercuts:** `CLAIMS.md` §7 **Differentiator 0** — the axis the author ranks first, and the
one described as making "every *other* number we report mean something." Specifically it kills
*input-only*, *no RAM writes*, *real gravity*, and (half of) *gravity-derived* as novel
properties for a retro falling-piece agent.

**And it inverts one comparison against us.** We read game RAM to construct board state. On
Canaan et al.'s taxonomy (THREAT #5) that is an **input-fairness** concession, and
StackRabbit's console client — reconstructing state from video — is *stricter than us on that
axis*. A reviewer will find this. We must answer it in the paper, pre-emptively, on our terms.

**Defensible reformulation** (this is the narrowest form sweep 4 could not break, and it should
become the paper's stated fairness contribution verbatim):
> *A **wall-clock compute budget derived from the game's own fall timer, treated as a hard
> constraint on the agent rather than a property of the environment, and enforced as a
> merge-blocking invariant in CI** — alongside input-only actuation on unmodified hardware.
> Prior systems either front-load computation off the critical path and let the emulator block
> (StackRabbit issues its search as a synchronous HTTP call from inside the frame callback and
> precomputes during the previous piece's lock delay), enforce a *fixed* budget from the
> harness side with disqualification (GVG-AI, FightingICE), or state a constraint with no
> mechanized check (AlphaStar, OpenAI Five, GT Sophy).*

Note the distinction that does the work: StackRabbit's gravity-derivation constrains **which
placements are reachable**; ours constrains **how long the agent may think**. Different claims;
only the second is a hard real-time claim. Say it in exactly those words.

**Prepared answer on input fairness** (decide now, do not improvise at review):
> We take board state from the console's own RAM over the cartridge bus, which is what an
> in-cartridge coprocessor physically has access to; vision is not a meaningful abstraction for
> a device sitting on the address bus. We therefore claim **output fairness** (§Canaan) without
> qualification and report input access explicitly as a stated limitation, alongside a note
> that a vision front-end (cf. `dmwit/nostramario`) is orthogonal and out of scope.

**Action:** upgrade the StackRabbit entry in `RELATED_WORK.md` Thread A from a one-line
mention to a full entry with the table above, and name it explicitly in the abstract's
prior-art sentence. Omitting the closest input-only retro falling-piece agent while claiming
input-only would be read as a coverage failure.

---

### THREAT #3 — The in-cart AI-coprocessor lineage is far wider than ST018
**Tier: HIGH to C2 / `CLAIMS.md` §7 Differentiator 1.**

Three additions bracket the Seta chips on both sides:

**3a. Philips Videopac C7010 Chess Module (1982)** — *predates Seta by 11 years, and the
architectural rationale is identical to ours.*
<https://www.chessprogramming.org/Videopac_C_7010> ·
<https://www.computinghistory.org.uk/det/69190/Videopac-C7010-Chess-Module/>
A module entering the Videopac G7000 / Odyssey² through a dummy cartridge, carrying **its own
NSC800 (Z80-compatible) CMOS processor and its own RAM** (both verified at source), running the
*Gambiet 80* chess engine — because the host console lacked the memory and compute to run
chess itself. That is our exact pattern: host too weak → put a search processor in the cart.
*(The frequently repeated "six difficulty levels corresponding to search depth 1–6 plies" was
**not reproducible** from either source checked. Verify before citing the ply figure; the
architectural facts stand without it.)*

**3b. SuperRT (Ben Carter, 2021)** — *same board, same bus, same mailbox pattern as ours.*
<https://www.shironekolabs.com/posts/superrt/>
A custom SNES enhancement chip implemented on a **DE10-Nano — the MiSTer board** — wired to the
SNES cartridge bus, with a 32K program ROM and 32K of memory-mapped registers as the mailbox,
explicitly framed as a modern Super FX successor. "Modern FPGA coprocessor on a retro cartridge
bus" is therefore **not novel**. Only the payload — search-based game AI — is.

**3c. Broke Studio "Rainbow," NES 2.0 mapper 682** — *modern coprocessor in an NES cart.*
<https://github.com/BrokeStudio/rainbow-net>
A homebrew NES board with an **ESP8266 coprocessor addressable by the 6502** through a register
interface, shipped commercially in *Super Tilt Bro.* Payload is networking, not AI — but
"NES cart with a modern coprocessor talking to the 6502 through registers" is existing art.

**3d. Supporting fact, and it is a gift.** The MiSTer SNES core already implements **ST010** —
so "AI enhancement chip in an FPGA core" exists. But ST011 and ST018 are explicitly *not*
implemented, documented as being because the core "is already near the limit of what the
DE10-Nano's Cyclone V is capable of fitting."
<https://mister-devel.github.io/MkDocs_MiSTer/cores/highlights/snes/>
That is a citable, quotable frame that turns our **87% ALM single-copro fit with a new search
engine** from a routine number into a notable one. Use it in the systems section.

**3e. Supporting negative.** No Famicom/NES cartridge ever shipped a general-purpose game-logic
coprocessor; per the MMC literature the Japan-only Family Computer Network System is the sole
exception. NES cart enhancements were mappers, expansion audio, and fixed-function speech ICs.

**Undercuts:** any unqualified "first AI in a cartridge" (C7010 1982), "first real-time in-cart
game AI" (ST010's opponent-car AI, 1993), "first FPGA coprocessor on a retro cartridge bus"
or "first AI coprocessor on a DE10-Nano" (SuperRT 2021), "first AI coprocessor in a MiSTer
core" (ST010, already shipped), "first modern coprocessor in an NES cart" (Rainbow).

**Defensible reformulation** — replace `CLAIMS.md` §7 Differentiator 1's lineage sentence with
the **four surviving conjuncts**, each of which survived all four sweeps:
> 1. **First in-cartridge AI coprocessor for a Nintendo 8-bit system** (§3e is the supporting
>    negative result).
> 2. **First in-cart AI that plays as a *player* rather than as the game's own shipped
>    opponent.** Every Tier-1 predecessor computes the *game's own* scripted side — car AI,
>    shogi opponent — for a title designed around that chip. Ours retrofits a coprocessor onto
>    an unmodified commercial title released years earlier and drives the human-player interface.
> 3. **First revival of the category after 1995**, and the first outside a game publisher.
> 4. **First published, reproducible, weight-optimized evaluation function for an in-cart
>    engine.** The Seta chips are undocumented black boxes; even ST018's dumped ROM has, as
>    far as four sweeps could establish, never been analyzed as an AI.

---

### THREAT #4 — Daniel Wagner (`dmwit`): `nurse-sveta`, `dasyuridia`, and the Dr. Mario toolchain
**Tier: HIGH. The deepest body of Dr. Mario engineering outside ours, and it has a real-hardware path.**
<https://github.com/dmwit/nurse-sveta> · <https://github.com/dmwit/dasyuridia>

- **`nurse-sveta`** — the agent. Haskell + libtorch, 421 commits, created 2019-08, last push
  2026-05-06. Its bibliography directory (MuZero, MuZero Unplugged, EfficientZero, R2D2,
  evolution strategies) places it in the **AlphaZero/MuZero family: neural net + MCTS**, with a
  search budget rather than a fixed ply. Also ships an evolution-strategies module. No published
  strength numbers found.
- **`dasyuridia`** — the hardware path, and the part that matters most to us. "Tools for
  connecting a Dr. Mario AI to the NES implementation of Dr. Mario," with two backends: FCEUX
  (Lua, which pauses the emulator while the AI thinks) and **`--everdrive /dev/ttyACM0` — a real
  NES over USB via a Krikzz EverDrive N8 Pro.** Pause is explicitly unsupported on the EverDrive
  backend, so on silicon it must answer in real time. It is RAM-manipulating rather than
  input-only (it writes controller-state bytes at an MD5-keyed injection point) and requires a
  modified ROM exposing a comms protocol.
- Surrounding ecosystem: `maryodel` (pure-Haskell model of NES Dr. Mario), `nostramario`
  (PyTorch/OpenCV vision for Dr. Mario — parallel to our vision/OCR lane), `tomcats` (his MCTS
  library), `dr-mario-disassembly`, `damascus` (a networked Dr. Mario protocol spec that
  explicitly anticipates AI-backed clients), `mcmario` (rating system), `dr-mario-ngrams`.

**Undercuts:** "first strong Dr. Mario AI" (an active MuZero-lineage agent exists); "first
Dr. Mario AI to run against real hardware" (the EverDrive path); C1's *"first to use depth-3
expectimax over pill randomness"* — an MCTS agent with a search budget is not depth-limited at
3, so a depth-*number* claim is both fragile and uninteresting; and implicitly C4, since
`mcmario` is a Dr. Mario rating system.

**Defensible reformulation:**
> Drop the depth-number from C1 entirely. "Depth-3" is a *systems* fact about what fits in the
> ALM budget at frame cadence, not a research claim — present it that way and nowhere else.
> Reformulate the hardware conjunct precisely: *"the agent executes on console-class silicon
> **inside the cartridge**, against an **unmodified** ROM, with no host computer in the decision
> loop."* Each italicized word is doing work: `dasyuridia --everdrive` reaches real NES silicon,
> but the agent lives on a PC over USB and the ROM must be patched to expose a comms protocol.
> State that difference factually, in one sentence, without adjectives.

**Action:** cite `nurse-sveta`, `dasyuridia`, and `maryodel` in Thread B. This is the single
most credible reviewer in the space — he owns four of the twelve tools on the scene's canonical
tool list — and a related-work section on Dr. Mario AI that omits him is not a serious one.

---

### THREAT #5 — Venue-adjacent citations we currently do not make
**Tier: HIGH to framing and reviewer trust; LOW technically.**

**5a. Canaan, Salge, Togelius & Nealen, "Leveling the Playing Field: Fairness in AI Versus
Human Game Benchmarks," arXiv:1903.07008, CoG 2019** (title verified) — **at our primary
venue.** It defines seven fairness axes: input, output, experience, knowledge, compute,
psychological, common-sense. Our "input-only" *is* their **output fairness**; our RAM reads
land on their **input fairness**; "gravity is the budget" is their **compute fairness**. It is
purely taxonomic and proposes no enforcement — which is precisely the gap our CI audit fills.
A fairness-centred paper at CoG that does not place itself on this taxonomy will read as
unaware of its own subfield. **Mandatory cite; build a table mapping our constraints onto the
seven axes, including the axis where we concede.**

**5b. Guida & DeMaio, "The Nintendo Artificial Neural Network System," Joint AIIDE Workshop on
Experimental AI in Games (EXAG) + Intelligent Narrative Technologies, Nov 10–11 2025,
Edmonton; CEUR-WS Vol-4090** (authors/title/venue verified from the PDF) — **at our stated
fallback venue, one year ahead of us.** A 400→16→10 MLP, EMNIST-trained offline, ported to 6502
assembly with pretrained weights, fitting in 32 KB **on a physical cartridge running on real
NES hardware.** No coprocessor, no game AI, no search. But it establishes "AI on retro
hardware" as an existing accepted AIIDE-workshop category and, critically, it takes the phrase
"AI running on original NES hardware" as a *paper framing*.

**Undercuts:** `CLAIMS.md` §7 **Differentiator 5** ("the only configuration in this space that
would run on actual OG silicon"). Also relevant: **CNESS** (24 KB NES chess ROM, three AI levels
at 1.75 s / 3 s / 15 s average turn, stock hardware), **Super Tilt Bro.**'s in-ROM behavior-tree
opponent on stock 6502 (2017), `ErikPelli/nes-ai`, and `erodola/bigram-nes`.

**Defensible reformulation of Differentiator 5:**
> *"A distilled pure-6502 build that runs a **game-tree search agent for a commercial title** on
> stock NES silicon via IPS patch, at honestly-labelled reduced strength — distinguished from
> prior NES-native AI work, which is either offline-trained inference (digit classification,
> character bigrams), an in-ROM reactive opponent for a homebrew title, or a turn-based engine
> with seconds-per-move budgets."*

**Also add from this tier:** Volz & Naujoks, "Towards Game-Playing AI Benchmarks via Performance
Reporting Standards" (CoG 2020, arXiv:2007.02742) — a reporting-standards paper at our primary
venue that our EXPERIMENTS lane should simply comply with; GT Sophy (Nature 2022, 10 Hz action
rate + 100/200/250 ms perception-delay retraining vs pro 200–250 ms); Blade & Soul
(arXiv:1904.03821, 230 ms delay as a stated fairness condition); Machado et al. 2018 (sticky
actions); and, for the anytime thread, **situated temporal planning** (Dionne, Thayer & Ruml
2011; Shperberg et al., ICAPS 2021) — the formal framework for search bounded by an external
deadline with concurrent planning and execution, which is exactly what "gravity is the budget"
instantiates.

---

## 3. Deduplicated threat register (everything, ranked)

Items already fully covered by `RELATED_WORK.md` are marked **[in RW]**; the rest are new and
carry a merge instruction in §9.

### CRITICAL
| # | Item | Undercuts | Status |
|---|---|---|---|
| 1 | `EthanOConnor/drmc-rl` (2025–26, active) | C1 benchmark-first, C4, Formulation C | **NEW** |
| 2 | StackRabbit at source level (2021) | `CLAIMS.md` §7 Diff. 0 (input-only / real gravity) | **[in RW]** but far under-rated — upgrade |

### HIGH
| # | Item | Undercuts | Status |
|---|---|---|---|
| 3 | Videopac C7010 chess module (1982) | "first in-cart AI / in-cart search coprocessor" | **NEW** |
| 4 | SuperRT (2021, DE10-Nano on SNES cart bus) | "first FPGA coprocessor on a retro cart bus" | **NEW** |
| 5 | `dmwit/nurse-sveta` + `dasyuridia` | "first strong Dr. Mario AI"; "first vs real hardware"; depth claim | **NEW** |
| 6 | Canaan et al., CoG 2019 (fairness taxonomy) | framing; exposes our input-fairness concession | **NEW** |
| 7 | Guida & DeMaio, AIIDE EXAG 2025 | Diff. 5; "AI on real NES hardware" as a framing | **NEW** |
| 8 | Seta ST010 / ST011 / ST018 (1993–95) | "no enhancement chip ran AI" | **[in RW]** correction #2 |
| 9 | MiSTer SNES core ships ST010; ST011/ST018 excluded for Cyclone V capacity | "first AI chip in a MiSTer core" — *and supports the 87% ALM framing* | **NEW** |
| 10 | Thiery & Scherrer, BCTS (ICGA 2009) | "optimizing eval coefficients is novel"; also their variance warning ⇒ reviewers will demand CIs | **[in RW]** — but the *variance warning* is new and load-bearing |
| 11 | Hardware game-tree search: Belle (1980–82), HiTech, ChipTest, Deep Blue, Brutus/Hydra (FPGA leaf-side eval, IPDPS 2004) | "novel architecture" — root-in-software / leaves-in-FPGA is a named, 20-year-old design | **[in RW]** partially (Deep Blue, Brutus) — add Belle/HiTech/ChipTest |

### MODERATE
| # | Item | Undercuts | Status |
|---|---|---|---|
| 12 | Broke Studio "Rainbow" mapper 682 (ESP8266 coprocessor in an NES cart) | "modern coprocessor in an NES cart" | **NEW** |
| 13 | Puyo competitive-AI scene (`puyoai`, `citrus610/ama`, Mayah, meatfighter Puyo) | "first strong versus falling-block AI"; garbage/attack shaping as a research question | **[in RW]** |
| 14 | meatfighter Dr. Mario AI (2017), source-verified | "first Dr. Mario AI" (dead); bounds the fairness contrast | **[in RW]** correction #1 — no change needed |
| 15 | FPGA game-tree/MCTS accelerators (arXiv 2208.11208; FPGA'23; Blokus Duo; Connect6) | "FPGA search is novel" | **NEW** |
| 16 | Aaron Williams, Dr. Mario puzzle generation (JCDCG³ 2019) + Dr. Mario 64 generation (2021) | "Dr. Mario is academically unstudied" — **false**; and he is a plausible reviewer | **NEW** |
| 17 | Eto, Kiya & Ono, generalized Puyo Puyo hardness (JIP 33, 2025) — longest-chain NP-complete with 2 colors, inapproximable | the natural template/corollary objection to any Dr. Mario hardness result | **NEW** |
| 18 | Hanson, MCTS for Puyo Puyo (AISB50 2014) | search agents in competitive falling-block games | **NEW** |
| 19 | `leerieo/DrMarioAi_ThesisProject` (2022) — a university thesis extending meatfighter's `drmarioai` | "no academic derivative exists"; citable prior art | **NEW** |
| 20 | Nintendo Ninja / `jpwright/fpganes` (2013) | "FPGA AI plays a real Nintendo console" | **[in RW]** |
| 21 | Naming hazard: in 2026 MiSTer discourse, "AI core" reads as *LLM-generated HDL* ("AI slop cores") | not a claim threat — a **presentation** threat | **NEW** |

### LOW (catalogue for completeness; omitting them looks like we did not check)
| # | Item | Note | Status |
|---|---|---|---|
| 22 | `brownian-motion/Dr.-Mario-Reinforcement-Learning` (2018, Lua Q-learning/SARSA, `joypad.write` input-only) | kills "first Dr. Mario **RL** agent" | **NEW** |
| 23 | `fogleman/DrMario` (2012–13) — own clone + Dijkstra router + **`genetic.py` weight tuning** | kills "first *optimized* Dr. Mario eval weights" | **[in RW]** — but the GA detail is new and matters |
| 24 | `vhmatteussi/dr_mario_bot` (MATLAB/Octave Q-learning, active 2026-07) | live hobbyist work | **NEW** |
| 25 | `Jonny5-5/Dr-Mario-AI` (2023, screen-capture, pixels-only, input-only) | second independent DM agent | **[in RW]** |
| 26 | `KaiserKyle/DrMarioSolver` (offline solver), `CoreyGarvin/dr-mario-java`, `BCProgramming/BASeTris` DM-mode AI | not live players | **NEW** |
| 27 | Tirmazi et al. 2024 — Dr. Mario NP-hardness a *named open problem* | never write "complexity unexamined"; opportunity if we ever want a theory paper, credit them for posing it | **[in RW]** |
| 28 | Tetris complexity (Demaine et al. 2004; 8-column/4-row variant), match-3 hardness (Gualà et al. 2014) | mandatory background cites | **[in RW]** |
| 29 | Tetris learning lineage (Tsitsiklis & Van Roy, Szita & Lőrincz, Böhm et al., Gabillon et al.; Algorta & Şimşek survey) | method lineage | **[in RW]** |
| 30 | CNESS (NES chess ROM, 3 AI levels), Super Tilt Bro. in-ROM AI (2017), `ErikPelli/nes-ai`, `erodola/bigram-nes` | NES-native AI precedent | partial — only nes-ai **[in RW]** |
| 31 | Choe, curriculum learning for 2048/Tetris (2025); RL-vs-heuristics Atari Tetris (ESWA 2025) | pre-empts an RL pivot; also the frame in which our "imitation/compression fails — port the planner" negative becomes publishable | **NEW** |
| 32 | Flash carts with MCUs/FPGAs (PicoCart64, SummerCart64, sd2snes/FXPak) | emulate ROM/bus response; do not run game logic | **NEW** |
| 33 | TASBot / console verification; TASVideos input-only norms | replay ≠ reactive agent; but note TASVideos *owns* "input-only" as a verified community norm | **[in RW]** — add the norm point |

### SUPPORTING NEGATIVE RESULTS (these strengthen us; put them in the paper)
- `wiki.drmar.io/Tools` — the competitive scene's canonical tool list names exactly **one**
  playing AI (meatfighter's). Everything else is analysis/practice/netplay.
- speedrun.com Dr. Mario forums: stat-tracking Lua only; scripts banned; **no agent**.
- TASVideos: a Dr. Mario AGDQ 2014 TASBot demo exists, but it is scripted replay — **no Dr.
  Mario playing bot in the TAS community**.
- GitHub topic `dr-mario` (9 repos): zero AI/bot/solver.
- GitLab, itch.io, romhacking.net: no Dr. Mario release embeds a playing AI.
- **No other FPGA / on-cartridge / in-silicon Dr. Mario AI exists.** The only other real-hardware
  Dr. Mario AI path is `dasyuridia --everdrive`, where the agent is on a PC over USB and the
  ROM is patched.
- No Famicom/NES cart ever shipped a general-purpose game-logic coprocessor (§3e).
- No published analysis or benchmark of the ST010/ST011/ST018 AI could be found in four sweeps —
  if that holds, it is itself a citable gap and a natural baseline claim.

---

## 4. `CLAIMS.md` — DROP / NARROW / SURVIVES

Line-referenced against `CLAIMS.md` as of 2026-07-28.

### DROP outright
| Location | Text | Why | Killed by |
|---|---|---|---|
| §7 Diff. 0 | "**Input-only**… no RAM writes" *as a novelty axis* | true of us, but also true of StackRabbit (0 `writebyte`), `brownian-motion` (2018), `Jonny5-5`, and of ALE by construction; TASVideos owns it as a verified community norm | #2 |
| §7 Diff. 0 | "no gravity manipulation" *unqualified* | already flagged internally: our non-anytime freeze carts do `STA GRAV_P2`. Never state it tree-wide | RW correction #1 |
| §1 qual. 1 / §7 Diff. 0 | "**real gravity**" *as a novelty axis* | StackRabbit plays past L29 unmodified and derives reachability from gravity | #2 |
| C1 (OUTLINE) | "the first to use **depth-3 expectimax** over pill randomness" | unwinnable and uninteresting: MCTS agents (`nurse-sveta`) search deeper in expectation; no prior author publishes a ply number to be first against | #4 |
| §7 Diff. 1 | "**Lineage: Seta ST010/ST018**" *as the lineage's start* | the pattern is 1982 (C7010) and was restated in 2021 (SuperRT) on our exact board | #3 |
| §7 Diff. 3 | coefficient optimization *as a differentiator per se* | Thiery & Scherrer fit falling-block eval weights by cross-entropy in 2009; `fogleman/DrMario` did GA weight tuning for **Dr. Mario** in 2012 | #10, #23 |
| §4 | "**Clears 100%** of Level-11 MED boards solo" *as stated* | n=6. Thiery & Scherrer explicitly warn that falling-block metrics have large variance and that implementation details move scores materially — a reviewer will demand a CI, and n=6 cannot carry a headline | #10 |

### NARROW (keep the substance, change the wording)
| Location | Narrowed form |
|---|---|
| §7 Diff. 0 | → "a **gravity-derived wall-clock compute budget treated as a hard constraint on the agent**, enforced as a **merge-blocking CI invariant**." Add the StackRabbit distinction (reachability vs think-time) and the Canaan-axis table including our input-fairness concession. |
| §7 Diff. 1 | → the four conjuncts in §2 THREAT #3. |
| §7 Diff. 2 | → "explicit **attack/garbage shaping measured against a tournament corpus** (doubles rate at 83% of pro, take-rate at parity)" — a *measurement*, not a design posture; competitive falling-block AI is a mature field (Puyo, drmc-rl's PFSP league). |
| §7 Diff. 3 | → claim the **artifact and the validation protocol** (DRMC-derived corpus, held-out validation, paired-seed A/B), not the technique. |
| §7 Diff. 4 | → keep; add that MiSTer's SNES core already ships an AI enhancement chip (ST010) so the claim is "a self-playing agent core," and **rename the artifact** to avoid "AI core" (see #21). |
| §7 Diff. 5 | → the reformulation in §2 THREAT #5b. |
| §4 | → report clear rate **with a confidence interval and an explicit n**, per Volz & Naujoks reporting standards; raise n before the number is quoted anywhere. Same treatment for every standing negative flagged at n=10 in the sample-size audit. |
| C1 | → "first agent to execute **on console-class silicon inside the cartridge address space** against an **unmodified** ROM with no host computer in the decision loop; first **published** quantitative strength benchmark for Dr. Mario." |
| C4 | → "a **released, reproducible** expert corpus from documented tournament brackets" — drop "first," and only claim it if released. |
| §3 Form. C | → keep the formulation, but treat "first documented instance" as **time-sensitive**; a Fightcade-connected agent could produce the result before Sept 12 (#1). |

### SURVIVES unchanged
- §1 qualifiers 2–5 (console-accurate hardware, legitimate second player, stated level/speed,
  stated human caliber) — well-constructed and unthreatened.
- §2 caliber ladder anchored to `brackets.json` / `players.json`.
- §5 pre-registered RWE protocol, including "report negatives."
- §6 "claims to avoid" — all still correct; §5 below adds to it.
- The systems facts: mapper-100 in-cart coprocessor, RTL leaf evaluator, the four-stage
  py65 → Verilator → Quartus → silicon validation ladder. These are the paper's real spine.

### ADD to §6 "Claims to avoid"
- ❌ "first AI in a cartridge" → Videopac C7010, 1982
- ❌ "first hardware-accelerated game AI" → Belle, 1980
- ❌ "first real-time in-cart game AI" → Seta ST010 opponent-car AI, 1993
- ❌ "first FPGA coprocessor on a retro cartridge bus / on a DE10-Nano" → SuperRT, 2021
- ❌ "first AI coprocessor in a MiSTer core" → ST010 already ships in the SNES core
- ❌ "first AI running on original NES hardware" → Guida & DeMaio, AIIDE workshop 2025
- ❌ "Dr. Mario is academically unstudied" / "its complexity is unexamined" → Williams 2019/2021;
  Tirmazi et al. 2024 poses NP-hardness as a **named open problem**
- ❌ "first Dr. Mario RL agent" → brownian-motion, 2018
- ❌ "first optimized Dr. Mario eval weights" → `fogleman/DrMario` GA, 2012
- ❌ "input-only is our novelty" → StackRabbit, TASVideos, ALE
- ❌ any "first" phrased about **capability** rather than **locus, measurement, or enforcement**

---

## 5. Genuinely unclaimed / Arguable / Taken

### GENUINELY UNCLAIMED — no counterexample in four sweeps
1. **A wall-clock compute budget derived from the game's own fall timer, treated as a hard
   constraint on the agent, and enforced as a merge-blocking CI invariant.** Targeted search for
   *any* game-AI project or paper gating commits on a fairness/timing invariant returned nothing;
   all "CI + agent + latency budget" hits were 2024–26 LLM-agent eval tooling with no game or
   fairness framing. **This is the strongest single unoccupied claim we have.**
2. **First in-cartridge AI coprocessor for a Nintendo 8-bit system.**
3. **First in-cart AI that plays as a *player* on an unmodified, pre-existing commercial title**
   rather than being the game's own shipped opponent.
4. **First published quantitative strength benchmark of a Dr. Mario agent against documented
   tournament humans.** The entire prior art has no numbers. *Time-sensitive — see #1 in §2.*
5. **First revival of the in-cart game-AI-coprocessor category after 1995, and the first outside
   a game publisher.**
6. **First published, reproducible, weight-optimized evaluation for an in-cart engine** (the
   Seta chips are undocumented; ST018's dumped ROM appears never to have been analyzed as an AI).
7. **The measured negatives** — cascade-chasing, depth-4 at current weights, reflex fast-path,
   route-potential farming, regime weights at depth 3, imitation/compression vs porting the
   planner. Published negatives with paired-seed statistics are rare and are genuinely ours.
8. **Shipping the same agent as a MiSTer core, an openFPGA core, and a physical mapper cart.**

### ARGUABLE — defensible only with a precise qualifier, and expect to be probed
| Claim | Required qualifier |
|---|---|
| "First *strong* Dr. Mario AI" | only as a **conjunction** (in-cart silicon + measured + vs documented humans), and only with meatfighter, drmc-rl, and nurse-sveta cited in the same paragraph. Prefer to avoid the word "strong" as a first-claim. |
| "AI on period-accurate hardware" | say **"console-accurate FPGA"**; "original NES hardware" becomes claimable only for the distilled pure-6502 IPS build, and only once measured |
| "Fair second player" | claim **output fairness** unqualified; state the **input-fairness** (RAM read) position explicitly, on our terms, before a reviewer raises it |
| "First academic write-up of a Dr. Mario **agent**" | true as far as four sweeps establish — but Dr. Mario *is* peer-reviewed CS territory already (Williams; Tirmazi et al.). Scope the word "agent" and never generalize to "unstudied." |
| "First Dr. Mario benchmark/corpus" | → "first **released**"; drmc-rl has an internal human-corpus integration |
| "Depth-3 expectimax in silicon" | fine as a **systems** statement (what fits at frame cadence); not as a research first |

### TAKEN — do not claim in any form
First Dr. Mario AI (meatfighter 2017) · first Dr. Mario AI that plays a human head-to-head
(meatfighter 2P) · first Dr. Mario RL agent (2018) · depth search + weighted linear eval as a
method (Thiery & Scherrer 2009; meatfighter) · optimizing eval coefficients (2009; fogleman
2012) · FPGA-accelerated game-tree search (Belle 1980 → Brutus/Hydra 2004) · leaves-in-FPGA /
root-in-software split (Brutus/Hydra) · FPGA AI plays a real Nintendo console (Nintendo Ninja
2013) · FPGA coprocessor on a retro cartridge bus (SuperRT 2021) · AI in a cartridge (C7010
1982; Seta 1993–95) · real-time in-cart game AI (ST010 1993) · AI on real NES hardware as a
paper framing (Guida & DeMaio 2025) · fairness-by-constraint (AlphaStar, OpenAI Five,
FightingICE, GT Sophy) · input-only actuation (StackRabbit, TASVideos, ALE) · strong versus
falling-block AI (Puyo scene) · superhuman NES puzzle AI (StackRabbit).

---

## 6. The prior-art matrix — required corrections to Table T1

`RELATED_WORK.md`'s Table T1 has two cells that will not survive a reviewer who reads the
sources, plus four missing rows.

**Corrections:**
- **meatfighter Dr. Mario, "Real gravity, no pause" = ✓ → ✗.** Contradicts correction #1 in the
  same file (`stallDrop()` writes `FRAMES_UNTIL_DROP = 0xFF` every frame). Internal inconsistency;
  fix before anyone else finds it.
- **StackRabbit, "Fair opponent" = ✗ ("superhuman soloist").** Too coarse: it ships
  `REACTION_TIME_FRAMES` and a 13-preset tap-rate timeline, i.e. explicit, parameterized
  human-fairness caps. Change to **~** and footnote that the caps are configurable and that the
  headline superhuman result was produced with them relaxed.

**Missing rows to add:** `drmc-rl`, `nurse-sveta`+`dasyuridia`, Videopac C7010, SuperRT.

**One column to add — the column that actually carries the paper:**
**"Fairness constraint mechanically enforced (build/merge-blocking)"** — ✓ for us, ✗ for every
other row including StackRabbit, AlphaStar, and the competition harnesses (which enforce from
the *harness* side against a configurable research environment, not from the *agent* side
against an unmodified commercial ROM). That column is the one with a unique ✓.

---

## 7. Timing and priority risk

Two independent Dr. Mario programs are active and unpublished (#1, #4). One has a live bridge
for playing humans online today; the other has a real-hardware path and a public Twitch
audience. Neither owes us anything, and both could publish, post, or stream a headline result
at any time.

**Recommendation:** decouple the arXiv preprint from the RWE human-versus results.
- **Post now-ish** on what is already furnishable and unaffected by anyone else's timeline: the
  systems contribution (in-cart coprocessor, RTL leaf evaluator, four-stage validation ladder,
  the 87% ALM fit framed against the Cyclone V ST018 capacity note), the CI-enforced
  gravity-derived deadline, the measured negatives, and the solo floor **with proper CIs and an
  honest n**.
- **Fold the human-versus results in as a v2** after RWE, which is also when Formulation A/B can
  actually be evidenced.
- This ordering protects the two claims most exposed to being scooped (#1 in §5, and the
  published-benchmark claim) while costing nothing, since the human results do not exist yet.

---

## 8. Open verification follow-ups

1. **Videopac C7010 search depth.** "Six difficulty levels = 1–6 plies" was not reproducible from
   chessprogramming.org or computinghistory.org.uk. Confirm before citing the ply figure; the
   architectural claim stands without it.
2. **Has anyone ever analyzed or benchmarked the ST010/ST011/ST018 AI?** Four sweeps found
   nothing. If that holds it is a citable gap and a natural baseline claim. The Japanese-language
   literature on the Morita Shogi carts is where any strength measurement would live — a targeted
   Japanese-language sweep is the highest-value remaining search.
3. **Native-6502 in-cart game-tree AI.** Our claim here still rests on absence of evidence; the
   NESdev / romhacking hobbyist scene has not been searched directly and exhaustively.
4. **Monitor** `EthanOConnor/drmc-rl` and `dmwit/nurse-sveta` for releases, and arXiv cs.AI/cs.LG
   for a Dr. Mario preprint.
5. **Re-run the sample-size audit against every number CLAIMS.md quotes** before any of them
   appears in prose. The n=6 clear-rate and the n=10 negatives are the exposed ones.

---

## 9. Merge instructions for `RELATED_WORK.md`

Do not paste this file in. Apply these targeted edits:

**Thread A (falling-block AI)**
- [ ] Replace the one-line StackRabbit entry with the full §2 THREAT #2 entry, including the
      property table, the reachability-vs-think-time distinction, and the note that its console
      client is *stricter than us* on input fairness. Re-rate MEDIUM → **HIGH**.
- [ ] Add Thiery & Scherrer's **variance warning** (falling-block metrics have large variance;
      implementation details move scores) as a methodological requirement on our own reporting.
- [ ] Add Eto/Kiya/Ono Puyo hardness (2025), Hanson MCTS Puyo (2014), Choe curriculum-learning
      (2025), and the RL-vs-heuristics Atari Tetris paper (ESWA 2025).

**Thread B (Dr. Mario specifically)**
- [ ] **New entry, top of thread: `EthanOConnor/drmc-rl`** — independent contemporaneous work,
      public repo only, neutral characterization, explicit note that `drmario-native` is private
      and must not be characterized.
- [ ] **New entry: `dmwit`** — `nurse-sveta`, `dasyuridia` (incl. the `--everdrive` real-NES
      backend and its patched-ROM requirement), `maryodel`, `nostramario`, `tomcats`, `mcmario`.
- [ ] Add `leerieo/DrMarioAi_ThesisProject` (2022 thesis extending `drmarioai`),
      `brownian-motion` (2018 RL), `vhmatteussi` (2026), and the Tier-4 catalogue.
- [ ] Add `fogleman/DrMario`'s **`genetic.py` weight tuning** — currently listed without it, and
      it is what makes it a threat to Differentiator 3.
- [ ] **Add Aaron Williams** (JCDCG³ 2019 Dr. Mario puzzle generation; 2021 Dr. Mario 64
      generation) and rewrite the "Academic: no paper presents any Dr. Mario agent" line to scope
      the word **agent** — Dr. Mario is already peer-reviewed CS territory, and Williams is a
      plausible reviewer.
- [ ] Add the SUPPORTING NEGATIVE RESULTS block from §3 — it is the evidence base for our
      remaining "first"s and belongs in the paper, not just in a memo.

**Thread C (period hardware / enhancement chips)**
- [ ] **Add Videopac C7010 (1982)** ahead of the Seta entry and reframe correction #2 as the
      *middle* of a 1982→2021 lineage rather than its origin.
- [ ] **Add SuperRT (2021)** — same DE10-Nano, same cart bus, same mailbox pattern. This is the
      single most surprising omission in the current file.
- [ ] **Add Broke Studio Rainbow / mapper 682.**
- [ ] **Add the MiSTer SNES core facts**: ST010 implemented; ST011/ST018 excluded on Cyclone V
      capacity grounds. Use it to frame the 87% ALM result.
- [ ] Add the NES/Famicom negative (Family Computer Network System is the only NES cart
      coprocessor) as the supporting evidence for surviving conjunct #1.
- [ ] Add Belle / HiTech / ChipTest to the existing Deep Blue / Brutus-Hydra entry, and state
      plainly that **leaves-in-FPGA / root-in-software is a named, decades-old design** — we
      claim the constraint envelope, not the architecture.
- [ ] Add FPGA MCTS/alpha-beta accelerator literature (arXiv 2208.11208; FPGA'23).
- [ ] Add flash carts (PicoCart64 / SummerCart64 / sd2snes) with the note that they emulate
      ROM/bus response and do not run game logic.

**Thread D (fairness / anytime)**
- [ ] **Add Canaan et al. (CoG 2019) as the thread's anchor**, with a table placing each of our
      constraints on its seven axes — including the axis we concede.
- [ ] Add GT Sophy (Nature 2022), Blade & Soul (arXiv:1904.03821), Machado et al. sticky actions,
      Volz & Naujoks reporting standards (CoG 2020), and situated temporal planning
      (Dionne/Thayer/Ruml 2011; Shperberg et al. ICAPS 2021).
- [ ] Note that **TASVideos owns "input-only" as a verified community norm** — so input-only is
      a *compliance* statement for us, not a contribution.

**New Thread E — "AI on retro hardware" as an established venue category**
- [ ] Guida & DeMaio (AIIDE EXAG 2025, CEUR Vol-4090), CNESS, Super Tilt Bro. in-ROM AI,
      `ErikPelli/nes-ai`, `erodola/bigram-nes`. Frame: this category exists and is one year
      ahead of us at our own fallback venue; our distinction is *search-based agent for a
      commercial title*, not *inference on retro silicon*.

**Table T1**
- [ ] Apply the two cell corrections and four new rows in §6.
- [ ] Add the "**mechanically enforced fairness constraint**" column — the one with a unique ✓.

**Front matter**
- [ ] Update the TL;DR: the sweep count is no longer five, and the "first Dr. Mario benchmark"
      and "first strong Dr. Mario AI" bullets need the contemporaneous-work caveat from §7.

---

## 10. New `REFERENCES.bib` entries required

Not currently present. Grouped by thread; all URLs HTTP-verified 2026-07-28.

**Fairness / methodology (highest priority — venue-critical)**
- `canaan2019fairness` — Canaan, Salge, Togelius, Nealen, *Leveling the Playing Field: Fairness
  in AI Versus Human Game Benchmarks*, arXiv:1903.07008, CoG 2019
- `volz2020reporting` — Volz & Naujoks, *Towards Game-Playing AI Benchmarks via Performance
  Reporting Standards*, CoG 2020, arXiv:2007.02742
- `wurman2022gtsophy` — GT Sophy, *Nature* 601 (2022)
- `oh2019bladesoul` — *Creating Pro-Level AI for Real-Time Fighting Game*, arXiv:1904.03821
- `machado2018ale` — Machado et al., *Revisiting the ALE*, JAIR 2018, arXiv:1709.06009
- `dionne2011dda`, `shperberg2021situated` — deadline-aware / situated temporal planning

**Dr. Mario**
- `oconnor2026drmcrl` — E. O'Connor, `drmc-rl`, GitHub (independent contemporaneous work,
  accessed 2026-07-28)
- `wagner_nursesveta`, `wagner_dasyuridia`, `wagner_maryodel` — D. Wagner (`dmwit`)
- `williams2019drmariopcg` — A. Williams, *Dr. Mario Puzzle Generation: Theory, Practice &
  History (Famicom/NES)*, JCDCG³ 2019
- `williams2021drmario64` — Williams et al., *Try, Try Again: Randomly Generating (and
  Regenerating) Dr. Mario 64 Puzzles*, 2021
- `leerieo2022thesis` — `DrMarioAi_ThesisProject`
- `brownianmotion2018drmariorl`, `fogleman_drmario` (note: `genetic.py` weight tuning)

**Hardware / in-cart**
- `videopac_c7010` — Philips Videopac C7010 chess module, 1982
- `carter2021superrt` — B. Carter, SuperRT
- `brokestudio_rainbow` — NES 2.0 mapper 682
- `mister_snes_core` — MiSTer SNES core (ST010 implemented; ST011/ST018 excluded on capacity)
- `thompson_belle`, `berliner_hitech`, `hsu_chiptest`, `donninger2004brutus` — hardware
  game-tree search lineage
- `mcts_fpga_2022` (arXiv:2208.11208), `mcts_fpga_2023` (FPGA'23)

**Retro-hardware AI (new Thread E)**
- `guida2025nesann` — Guida & DeMaio, *The Nintendo Artificial Neural Network System*, Joint
  AIIDE EXAG + INT Workshop 2025, CEUR-WS Vol-4090
- `cness`, `supertiltbro_ai`, `erodola_bigramnes`

**Falling-block / complexity**
- `thiery2009controllers` — *Building Controllers for Tetris*, ICGA Journal 32(1) 2009 (distinct
  from the cross-entropy paper already in the file)
- `eto2025puyo` — *Hardness Results on Generalized Puyo Puyo*, JIP 33:1077–1091, 2025
- `hanson2014puyomcts` — AISB50 2014
- `citrus610_ama`, `birken_puyo`
- `choe2025curriculum`
