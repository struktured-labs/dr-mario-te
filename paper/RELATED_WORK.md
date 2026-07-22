# Related Work — adversarial prior-art sweep

> Purpose: survive the "first strong Dr. Mario AI" claim under hostile review. Every item
> below has a **threat rating** (does it undercut a novelty claim?) and a defense. Compiled
> 2026-07-22 from five focused web sweeps. Citations are in `REFERENCES.bib`. **Read the two
> "load-bearing corrections" first — they change what the project may claim publicly.**

## TL;DR for the author

- **"First AI of any kind for Dr. Mario" is FALSE — do not write it.** meatfighter (2017) is a
  real, real-time, 1P+2P-VS Dr. Mario AI. Nintendo shipped CPU opponents in 1994/2001.
- **"First *strong* Dr. Mario AI" is defensible only as a conjunction** (on-hardware /
  in-cartridge + depth-3 expectimax + quantified benchmarks), and only if we **cite
  meatfighter prominently and ideally beat it head-to-head.**
- **"No enhancement chip ran game-playing AI" is FALSE.** The Seta **ST010/ST011/ST018**
  chips ran racing-opponent and shogi AI *in the cartridge* (1993–1995). This must be
  corrected in `README.md`/`ROADMAP.md`; it *strengthens* the lineage once reframed.
- **Drop "first strong falling-block-*versus* AI."** Puyo Puyo has a 30-year competitive-AI
  scene (shipped counter-chain CPUs + strong open-source PvP bots).
- **Do not claim algorithmic novelty.** Depth-3 expectimax + hand-tuned linear eval is
  textbook falling-block AI. Novelty = game + hardware locus + fairness discipline + benchmark.
- **Fairness-by-constraint is established** (AlphaStar APM caps, OpenAI Five 200 ms floor,
  FightingICE 15-frame delay) — cite as precedent. The *novel* piece is the **CI gravity-pin
  audit** (build-failing frame-level anti-stall) + gravity-derived (not engineered) deadline.

---

## Load-bearing correction #1 — meatfighter's Dr. Mario AI (2017). THREAT: HIGH.

**Ref.** M. Birken (meatfighter), "Applying Artificial Intelligence to Dr. Mario," 2017.
https://meatfighter.com/drmarioai/

**What it is.** A Java program in the **Nintaco** NES emulator driving the *real NES Dr. Mario
ROM* via the Nintaco API. Algorithm: BFS over every lock placement of *current pill × next
pill* = **depth-2 lookahead**, weighted heuristic (virus count, consecutive same-color tiles,
virus-color adjacency, non-empty count, column-height). Demonstrated in **1P at Levels 20–24**
(24 = internal max) and, critically, in **2P VS controlling Player 2 against a human** under
normal gravity, no per-move pause.

**Why HIGH.** It kills several would-be differentiators outright: real NES ROM, real-time,
real gravity, no pause, *plays as a competitive P2 vs a human*. So none of "real gravity / no
pause / plays as second player" is novel on its own.

**Where we genuinely escape it (the C1 wording depends on all three):**
1. **Hardware locus** — ours runs *on console-class silicon as an in-cartridge coprocessor*
   (FPGA MiSTer/Pocket), no PC in the decision loop; meatfighter is a PC Java app in a
   software emulator. This is the cleanest, strongest axis.
2. **Search** — depth-3 **expectimax** over pill randomness vs deterministic depth-2 BFS.
3. **Rigor** — we report clear rates (L11 100% sim); meatfighter publishes *no* benchmarks.

**Required actions.** (a) Cite prominently in §2. (b) Reframe C1 to the conjunction in
`CLAIMS.md`. (c) **Run a head-to-head** (our depth-3 vs a re-implementation of its depth-2,
same levels/seeds) — this is the single experiment that converts C1 from arguable to shown.

## Load-bearing correction #2 — Seta ST-series AI-in-cart chips (1993–95). THREAT: HIGH (to the framing).

**Refs.** ST010 (NEC µPD96050 DSP ~10 MHz), *F1 ROC II: Race of Champions* (1994) —
opponent-car racing AI. ST011 — shogi AI. **ST018** (Seta, 32-bit ARMv3 core @ 21.47 MHz),
*Hayazashi Nidan Morita Shougi 2* (1995) — ran **Kazuro Morita's shogi engine** as the
opponent. https://sneslab.net/wiki/ST018 · https://snescentral.com/chips.php?chiptype=ST018 ·
https://en.wikipedia.org/wiki/F1_ROC_II:_Race_of_Champions · https://en.wikipedia.org/wiki/Kazuro_Morita

**Why this matters.** The project's public framing ("enhancement chips did graphics/math;
none ran game-playing AI — that's our twist") is **factually wrong**: the ST-series put
genuine game-playing AI (a racing opponent; a competitive shogi engine) in the cartridge
address space, on period hardware, as the opponent. A knowledgeable reviewer *will* raise
ST018. **Fix `README.md`/`ROADMAP.md` before the arXiv post.**

**Why it strengthens us once reframed.** ST018 is the *nearest neighbor* on three of our four
axes (in-cart coprocessor ✓, game-playing AI ✓, period hardware ✓). We differ on the fourth
and on architecture, and those differences are the real C2:
- **Independent, retrofitted, fair second player** on an *unmodified commercial action game*
  (Dr. Mario knows nothing about our coprocessor) — ST018 was the *shipped* opponent of a game
  *built around* its chip.
- **Custom RTL board-evaluation accelerator** (Deep-Blue-style hardware eval at the search
  leaves) — ST018 was a stock ARM running a software engine.
- **Real-time action game** with a true concurrent player — shogi is abstract/turn-based, where
  "compute the move" *is* the whole game (no separate falling-pill clock).
- **Reconfigurable FPGA logic** (MiSTer/Pocket, custom mapper 100) reproducing the
  enhancement-chip concept without fabbing an ASIC.

Recommended §2 sentence: *"Prior AI-in-cart chips (Seta ST010/ST018) ran a game's own
turn-based opponent as shipped software on a general-purpose coprocessor; ours is a
retrofitted, hardware-accelerated, independent fair second player on an unmodified real-time
action game, with a custom RTL evaluation accelerator."* Keep SA-1/Super FX as the *famous*
lineage and Deep Blue/Hydra as the hardware-evaluation ancestor.

---

## Thread A — Falling-block AI (the methodological lineage). THREAT: MEDIUM (to algorithm-novelty only).

The paper must **not** claim algorithmic novelty; depth-3 expectimax + linear hand-eval is the
textbook approach. Cite the lineage and move the novelty elsewhere.

- **StackRabbit** — G. Cannon. NES Tetris AI: search + value-iteration board eval; FCEUX-Lua
  client *and* a Raspberry-Pi "console_client" that drives a **real NES**; superhuman
  (L237 / 102,252,920 pts with human input limits removed).
  https://github.com/GregoryCannon/StackRabbit — **The closest "strong AI plays an NES
  falling-block game" analog and our most important comparison.** Overlaps us on real-NES +
  real-gravity; differs on (i) brain is a modern Pi/PC, not period silicon; (ii) it is a
  *superhuman soloist* (removes human input caps), not a *fair opponent*. THREAT: MEDIUM —
  concede the overlap, pivot to hardware-locus + fairness + game.
- **meatfighter Nintendo Tetris AI** (M. Birken) — "Applying AI to Nintendo Tetris" (FCEUX
  Lua, relaxed gravity) and "…Revisited" (real gravity, 17-feature PSO-tuned linear eval,
  Nintaco). https://meatfighter.com/nintendotetrisai/ · https://meatfighter.com/tetrisairevisited/
  — Precedent for "hand-eval under real gravity," still emulator-hosted. THREAT: LOW.
  *(Attribution: meatfighter = **Michael Birken**, not "Colin M." — do not conflate with Colin
  Fahey below.)*
- **Dellacherie's algorithm** / **Colin Fahey's StandardTetris benchmark (2003)** /
  **El-Tetris (I. ElNabarawy, 2013)** — the canonical hand-tuned linear-feature controllers
  (landing height, holes, row/column transitions, wells…). https://www.colinfahey.com/tetris/tetris.html
  (cert expired but canonical) · https://github.com/YuhanXiaoJY/Implementation-of-El-Tetris —
  Our eval's intellectual ancestors. THREAT: LOW (positioning), cite as lineage.
- **Learning-tuned Tetris**: Tsitsiklis & Van Roy (1996); Bertsekas & Tsitsiklis
  *Neuro-Dynamic Programming* (1996); Szita & Lörincz (noisy cross-entropy, 2006, ~350k
  lines); **Thiery & Scherrer BCTS (2009, ~910k lines, won 2008 RL Competition)**; Böhm/Kókai/
  Mandl (GA + 2-piece lookahead, 2005); de Farias & Van Roy (2006); **Gabillon/Ghavamzadeh/
  Scherrer CBMPI (NIPS 2013, ~51M lines)**. Survey: **Algorta & Şimşek, "The Game of Tetris in
  Machine Learning" (2019)** https://arxiv.org/abs/1905.01652 — anchors the whole thread in
  one cite and confirms "linear eval over hand-crafted features + lookahead" is *the* paradigm.
  THREAT: LOW — supports "we are a faithful member of a mature lineage; the learner is not the
  point, the features are."
- **Complexity**: **Demaine, Hohenberger, Liben-Nowell et al., "Tetris is Hard, Even to
  Approximate" (COCOON 2003 / IJCGA 2004).** https://erikdemaine.org/papers/Tetris_IJCGA/ —
  Justifies bounded-depth heuristic search over exact optimization. THREAT: NONE; cite *for* us.
- **Game Boy Tetris GA** — Silva & Parpinelli, "Playing the Original Game Boy Tetris Using a
  Real-Coded GA" (BRACIS 2017) — GA agent on the *actual* GB Tetris via emulator plugin.
  THREAT: LOW; another "real game, modern brain" data point.

**Synthesis (adversarial).** Decompose our claim into predicates: {hand-eval+search,
real-time gravity, real period hardware runs the game, **AI executes on period silicon**,
**fair opponent**}. The first three are all covered by StackRabbit/meatfighter. The last two
are covered by **no** falling-block work. Center the paper there.

## Thread B — Dr. Mario specifically (beyond meatfighter). THREAT: LOW–MEDIUM.

- **Nintendo's shipped CPU opponents** — *Tetris & Dr. Mario* (SNES, 1994) VS-COM Easy/Med/
  Hard; *Dr. Mario 64* (2001) Hard/S-Hard, anecdotally "too good."
  https://tetris.fandom.com/wiki/Tetris_%26_Dr._Mario · https://www.mariowiki.com/Dr._Mario_64 —
  Real Dr. Mario-playing agents predating us, but undocumented/un-benchmarked/entertainment-
  tuned. THREAT: MEDIUM — acknowledge so "first ever" is never implied. **Note: the original
  NES Dr. Mario (1990) has NO CPU opponent** (2P is human-vs-human), which is why an AI P2 for
  *the NES version* is a coherent frame — but that frame is held by meatfighter too.
- **Hobby clones/bots** — `Jonny5-5/Dr-Mario-AI` (SNES9x Python bot, undocumented);
  `fogleman/DrMario` (clone + dijkstra/genetic AI); `cbpetersen/dr-mario-engine` (clone engine
  w/ pluggable AI). THREAT: LOW — none is a strong benchmarked NES player; they only reinforce
  "don't claim first *of any kind*."
- **TAS** — TASVideos NES Dr. Mario runs (poco_cpp et al.). Human-authored frame-perfect input
  movies for a fixed seed; no perception/search/generalization. THREAT: LOW — but state the
  agent-vs-replay distinction explicitly (readers conflate "TASBot" with "AI").
- **Complexity of Dr. Mario is FORMALLY OPEN** — Tirmazi, Tirmazi & Tran, "Computational
  Complexity of Game Boy Games," arXiv:2412.15469 (2024): *"We leave the NP-hardness of Dr.
  Mario as an open problem"* (in the body, not the abstract — verified). https://arxiv.org/abs/2412.15469
  THREAT: NONE; high citation value ("principled strong play is non-trivial; hardness open").
- **Dr. Mario World** (2019 mobile) — human-vs-human VS, no documented AI; servers off 2021.
  THREAT: NONE.
- **Academic**: no paper presents *any* Dr. Mario-playing agent (RL, search, or otherwise).
  If we land, we are plausibly the **first academic write-up of a Dr. Mario agent** — a clean,
  safe claim.

## Thread C — AI on period hardware / enhancement chips (beyond the ST-series). THREAT: LOW.

- **SA-1** (65C816 @ 10.74 MHz, general game logic — *Super Mario RPG*, *Kirby Super Star*);
  **Super FX** (Argonaut/Jez San, polygon/2D accel, *Star Fox*); **DSP-1** (µPD77C25 math for
  Mode 7); **Cx4** (Capcom trig); **SVP** (Genesis *Virtua Racing* DSP); **NES MMC5** (on-cart
  hardware multiplier); **Game Boy MBCs** (bank-switch/RTC). The *famous* lineage — all
  graphics/math/storage, **no AI**. THREAT: NONE; cite as the lineage we invoke (and then
  distinguish from the ST-series that *did* run AI).
- **Deep Blue** (Hsu, "IBM's Deep Blue Chess Grandmaster Chips," IEEE Micro 1999 — 480 custom
  chips w/ hardware evaluation) and **Brutus/Hydra** (chess search on **FPGA** near the leaves).
  https://dl.acm.org/doi/10.1109/40.755469 — **The intellectual ancestor of our RTL leaf-eval
  accelerator** (game-tree search + board eval in dedicated/FPGA hardware). THREAT: NONE; cite
  as ancestor. Distinguish: room-sized dedicated machines, not in-console coprocessors.
- **TASBot / console-verification** (replay devices: true's device 2013, TAStm32/VeriTAS).
  Feeds a *precomputed* frame-perfect script into a real console. https://tasvideos.org/TASBot —
  Closest "input injection on real hardware," but **no perception/search/reaction**. THREAT:
  LOW — cite precisely so reviewers don't conflate replay with a reactive agent.
- **MarI/O** (SethBling, 2015) — NEAT learns *Super Mario World* as a **BizHawk-emulator** Lua
  script. Canonical "AI learns an NES/SNES game," but emulator + external host. THREAT: NONE.
- **nes-ai** (E. Pelli) — an MLP (MNIST, Q16.16, cc65) running on a **stock NES 6502 @ 1.79
  MHz**. https://github.com/ErikPelli/nes-ai — Closest "NN on the actual 6502," but a *digit
  classifier*, not a game player, not a coprocessor. THREAT: LOW; cite as nearest-neighbor on
  "AI on real 8-bit silicon."
- **"Nintendo Ninja" FPGA SMB AI** (Blum/Wright/Mitra, 2013) — Verilog vision-based FPGA plays
  SMB on a real NES via NTSC decode. https://github.com/jpwright/fpganes — "FPGA plays an NES
  game" is not new; our sharper claim is *in-cartridge coprocessor executing the search as a
  second CPU*, not external vision. THREAT: LOW–MEDIUM; cite to bound the hardware claim.
- **FA3C (ASPLOS 2019)** and FPGA-RL accelerators — FPGA *trains* RL agents against an
  emulator/PC; agent not embedded in the console. THREAT: NONE; "FPGA RL exists, but off-console."
- **MiSTer / openFPGA (Analogue Pocket)** — platform citations; community search finds **no**
  self-playing-AI cores. Good for novelty. https://en.wikipedia.org/wiki/MiSTer · https://www.analogue.co/developer

**Synthesis (adversarial).** (1) Game-playing AI *has* been put in a cartridge coprocessor
before — the ST-series. (2) Closest existing thing to "enhancement-chip AI coprocessor that
plays as a fair second player on period hardware" = **ST018 / Morita Shogi 2**. (3) The SA-1
framing is defensible and *richer* once the ST-series is acknowledged. Strongest single threat
to the framing: **ST018.**

## Thread D — Real-time fairness, anytime search, match-3/Puyo. THREAT: MEDIUM (to fairness-novelty & versus-first).

**Fairness-by-constraint — established; cite as precedent, do not claim to originate.**
- **AlphaStar** — Vinyals et al., *Nature* 575 (2019): camera-only interface, **≤22 actions /
  5 s** cap, observation delays, **pro-approved (TLO)** — the textbook fairness-by-limits case.
  https://www.nature.com/articles/s41586-019-1724-z
- **OpenAI Five** — Berner et al., arXiv:1912.06680: acts every 4th frame, **reaction time
  raised 80 ms→200 ms for fairness.** https://arxiv.org/abs/1912.06680
- **FightingICE / DareFightingICE** — 16.66 ms/frame budget + **mandatory 15-frame reaction
  delay**; a follow-up *enforces fairness in the harness* (latency equalization, arXiv:2312.16010)
  — precedent for "fairness as measured methodology," echoing (not duplicating) our CI audit.

**Real-time / anytime search — cite as the paradigm we instantiate.**
- **Dean & Boddy (AAAI-88)** coined "anytime"; **Zilberstein (AI Magazine 1996)** the canonical
  framing. **Korf, "Real-time heuristic search," AIJ 1990** (RTA*/LRTA*) — commit within bounded
  time under a limited horizon; our nearest classical ancestor. **ARA*** (Likhachev et al., NIPS
  2003) — anytime best-so-far with improving bound. **MCTS as anytime** (Browne et al. survey,
  IEEE TCIAIG 2012). **Real-Time RL** — Ramstedt & Pal (NeurIPS 2019, arXiv:1911.04448)
  formalizes "the world does not pause during action selection"; **"Finding the Time to Think"**
  (arXiv, 2026). — **Our "gravity is the budget" is a concrete, physics-derived instance of the
  real-time MDP**; say so and cite these, rather than claiming a new paradigm.
- Real-time budgets in game-AI benchmarks: **ALE** (Bellemare et al., JAIR 2013; Machado et al.
  2018) — 5-min episode cap but *unbounded per-frame compute*; **GVGAI** (Perez-Liebana et al.)
  — hard **40 ms/decision**; **Physical TSP** (Perez et al.) — action every 40 ms under physics.
  Contrast: these harnesses *can* wait for the agent; our gravity-pin forbids it against an
  unmodified ROM.

**Match-3 / Puyo — drop "first strong falling-block-versus AI."**
- **Puyo Puyo** is the canonical competitive falling-block color-match *versus* game with a
  **30-year AI scene**: shipped counter-chain CPU AI since 1991 (Tsu 1994 added offsetting);
  academic chain-search (IEEE CIG 2012, avg chain ~11) and MCTS (IEEE 2021); strong open-source
  PvP bots (`puyoai/puyoai`, `citrus610/ama`+`lys`, Mayah) that manage nuisance/garbage and
  counters; and meatfighter's Famicom Puyo AI. https://github.com/puyoai/puyoai · https://github.com/citrus610/ama
  — **Decisively undercuts any "first/only strong versus falling-block AI."** Cite Puyo as the
  closest commercial analog; claim novelty on *methodology + real-time-fairness on unmodified
  original hardware + Dr. Mario's distinct virus-clearing objective*, not on "a strong versus
  falling-block AI exists."
- Match-3 hardness: Gualà, Leucci & Natale, "Bejeweled, Candy Crush… are (NP-)Hard" (IEEE CIG
  2014). King's Candy Crush playtesting bots (Gudmundsson et al., IEEE CIG 2018). THREAT: LOW —
  single-player optimization, not real-time versus.

**Synthesis (adversarial).** (a) Fairness-via-human-limits is prior art (AlphaStar/OpenAI/
FightingICE) — cite it. (b) Deadline-bounded anytime commit is prior art (Korf/Zilberstein/
ARA*/Real-Time RL) — cite it. The **novel** methodological pieces, after targeted search with
no prior art found: **the CI gravity-pin audit that fails the build on any frame-level clock
stall**, and **deriving the deadline from the ROM's own variable gravity** while enforcing it
against the *unmodified* commercial game (not a configurable research harness). (c) Puyo owns
"strong versus falling-block AI" — reposition.

---

## The prior-art matrix (draft of Table T1 — the paper's most persuasive novelty artifact)

Rows = systems; columns = the predicates our claim conjoins. ✓ = yes, ✗ = no, ~ = partial.

| System | Plays Dr. Mario | AI executes on period silicon | In-cartridge coprocessor | Real gravity, no pause | Fair opponent (not superhuman soloist) | Quantified benchmark | Depth-3 expectimax |
|---|:--:|:--:|:--:|:--:|:--:|:--:|:--:|
| **Ours** | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| meatfighter Dr. Mario (2017) | ✓ | ✗ (PC/emu) | ✗ | ✓ | ✓ | ✗ | ✗ (depth-2 BFS) |
| Nintendo VS-CPU (SNES/N64) | ✓ | ✓ (main CPU) | ✗ | ✓ | ✓ | ✗ | ✗ (undocumented) |
| StackRabbit (NES Tetris) | ✗ | ✗ (Pi/PC) | ✗ | ✓ | ✗ (superhuman soloist) | ✓ | ~ (search+VI) |
| Seta ST018 / Morita Shogi 2 | ✗ | ✓ | ✓ | n/a (turn-based) | ~ (shipped opponent) | ✗ | ~ (shogi engine) |
| Puyo PvP bots (ama/lys/puyoai) | ✗ | ✗ (PC) | ✗ | ~ | ✓ | ✓ | ~ |
| TASBot (replay) | ✓ (replay) | ✓ | ✗ | ✓ | ✗ (not reactive) | ✗ | ✗ |
| Deep Blue / Hydra | ✗ | ✓ (custom/FPGA) | ✗ | n/a | ✓ | ✓ | ✓ (αβ) |

The row that matters: **no system has ✓ across {period silicon, in-cartridge, real-gravity,
fair opponent, benchmarked}** — that conjunction is ours. Every single-cell ✓ elsewhere is a
citation we must make, not a threat we must hide.

## The five closest prior-art threats (ranked, for the lead's report)

1. **meatfighter Dr. Mario AI (2017)** — the only prior *real* Dr. Mario agent; kills "first AI
   of any kind." Defense: hardware locus + depth-3 expectimax + benchmarks; head-to-head.
2. **Seta ST018 / Morita Shogi 2 (1995)** — kills "no enhancement chip ran AI." Defense: fair
   retrofitted second player on an unmodified real-time game + RTL evaluator; and *cite it*.
3. **StackRabbit** — the strong-NES-falling-block-AI analog; kills "first strong on real NES."
   Defense: AI on *period silicon in-cart* (not a Pi), *fair opponent* (not superhuman soloist).
4. **Puyo competitive-AI scene** — kills "first strong versus falling-block AI." Defense:
   reposition to methodology + unmodified original hardware + Dr. Mario's objective.
5. **AlphaStar / OpenAI Five fairness caps** — kills "we invented fairness-by-constraint."
   Defense: cite as precedent; claim only the CI gravity-pin audit + gravity-derived deadline.

## Action items this sweep generated

- [ ] Correct "no enhancement chip ran game-playing AI" in `README.md` and `ROADMAP.md`
      (ST-series). *(Flagged to team lead; owned by whoever maintains those docs.)*
- [ ] Add meatfighter, ST018, StackRabbit, Puyo, AlphaStar to `REFERENCES.bib` (done — see file).
- [ ] Scope a **head-to-head vs a depth-2 meatfighter-style baseline** (converts C1 to demonstrated).
- [ ] Fix the "Colin M." → **Michael Birken** attribution wherever meatfighter is referenced.
