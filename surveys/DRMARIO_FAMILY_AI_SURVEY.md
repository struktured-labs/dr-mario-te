# Dr. Mario Family — CPU/AI Design Survey

Purpose: mine the entire Dr. Mario family (NES through mobile) for CPU-opponent and
personality-design ideas that feed our NES FPGA-coprocessor AI ("Combo Stomper").
Open workstreams this feeds: task #33 (personality-select knobs), attack/combo design,
benchmark opponents, and verifying the claim that Dr. Mario 64 shipped different
characters with different play styles.

Confidence tiers used throughout:
- **[CODE]** — read directly from a decompilation/disassembly source file (highest confidence)
- **[WIKI]** — community-documented (TCRF, Mario Wiki, strategy guides, reviews); usually accurate but unverified against the ROM
- **[INFER]** — our own inference/synthesis, flagged explicitly

Local disk check: `~/gaming/roms/` has NES Dr. Mario (US/EU/World/PC10/**VS arcade**/hacks),
GB has *no* Dr. Mario dump, SNES has `Tetris & Dr. Mario (USA).sfc` (the ROM behind our
parked [[tdm-snes-nav-wall]] study), and there is **no N64/GameCube/Wii/3DS/mobile Dr.
Mario dump anywhere on disk** — the N64 folder only has BIOS/boot ROMs. Everything below
on Dr. Mario 64 onward is sourced from public wikis/decomp repos, not a local ROM.

---

## 1. NES / Famicom Dr. Mario (1990)

**CPU opponent: none shipped.** [INFER, corroborated] Every source we found describes
exactly two modes — 1-Player (endless, virus count/level select) and 2-Player VS (two
controllers, human vs human). No search surfaced a CPU-opponent option, and our own
project's premise (building an FPGA coprocessor specifically *to add* a VS-CPU opponent to
this ROM — see [[dr-mario-fpga-coprocessor]]) is itself strong internal evidence: if
Nintendo had shipped one, we wouldn't have needed to build one. We could not fully verify
Famicom-vs-NES revision/timing differences beyond release dates (Japan: Famicom + Game Boy
simultaneously, July 1990; NA: NES, October 1990) and a TCRF claim that FDS BIOS routines
are still present in the final ROM, suggesting FDS-era origins — flagging this as an
unresolved documentation gap rather than a confirmed fact.

**VS. Dr. Mario (arcade, Nintendo VS. System + PlayChoice-10, Aug 1990)** [WIKI]: an
arcade port, present on disk as `NES/VS/Dr Mario (VS).nes` and `NES/PC10/Dr Mario
(PC10).nes`. Difference from the home ROM: **no Slow speed setting, only Normal and Fast**
(arcade-museum.com via search synthesis). Still no CPU opponent — VS. System cabinets ran
two linked screens for human-vs-human, and PlayChoice-10 ran single-player-only timed
credits. This is the *closest* thing to an "official CPU Dr. Mario" search turned up for
the 8-bit era, and it isn't one.

Sources: [Dr. Mario (game) - Super Mario Wiki](https://www.mariowiki.com/Dr._Mario_(game)), [Vs. Dr. Mario - Museum of the Game](https://www.arcade-museum.com/Videogame/vs-dr-mario), [Nintendo VS. System - Wikipedia](https://en.wikipedia.org/wiki/Nintendo_VS._System), [Dr. Mario (NES) - TCRF](https://tcrf.net/Dr._Mario_(NES)), [famicomworld.com forum](https://www.famicomworld.com/forum/index.php?topic=6091.0)

## 2. Game Boy Dr. Mario (1990)

**CPU opponent: none.** [WIKI, direct] 2-Player Vs. mode exists but strictly requires a
physical Game Link Cable between two Game Boys running two cartridges — no single-unit CPU
option. Matches the NES pattern exactly: the entire pre-1994 Dr. Mario line shipped with
*zero* CPU opponents, full stop.

Sources: [Dr. Mario (game) - Super Mario Wiki](https://www.mariowiki.com/Dr._Mario_(game)), [Game Boy Instruction Manuals: Dr. Mario](https://world-of-nintendo.com/manuals/game_boy/dr_mario.shtml)

## 3. SNES Tetris & Dr. Mario (1994)

**First Dr. Mario title with a CPU opponent**, confirmed by two independent search
summaries: *"This installment... was also the first to introduce a computer opponent."*
[WIKI] Three fixed CPU difficulty tiers in Dr. Mario mode, sold to the player as **virus
color**, not a text label: Blue = Easy, Yellow = Medium, Red = Hard. Tetris VS.COM mirrors
this with Easy/Medium/Hard. One source claims "the CPU adapts to player performance,"
though no mechanism was documented — treat as unverified marketing-copy-adjacent language,
not a confirmed rubber-band system (contrast with Dr. Mario 64's genuinely documented
mercy mechanic in §5).

This confirms and extends our own prior research: task [[tdm-snes-nav-wall]] already
verified the ROM (SHA-256 `3cdebbd8...`, clean USA LoROM/FastROM), matched the
Easy/Medium/Hard↔Blue/Yellow/Red mapping against household scouting, and found a real PAR
code (`7E1E7203`) unlocking a **cut options menu at WRAM `$7E1E72`** that TCRF documentation
says includes deeper computer-difficulty configuration than what shipped — a genuine
unexploited RAM foothold if the study resumes. That study is parked at a menu-navigation
wall (Game Select cursor won't leave Tetris across 7 input variants); the resume recipe is
saved in that memory and not repeated here.

We could not get a direct TCRF fetch to succeed for the T&DM page during this survey
(tooling issue, not a missing page — search snippets suggest a page exists); the existing
[[tdm-snes-nav-wall]] memory remains the authoritative source for the cut-menu claim.

Sources: [Tetris & Dr. Mario - Super Mario Wiki](https://www.mariowiki.com/Tetris_%26_Dr._Mario), [Hard Drop Tetris Wiki](https://harddrop.com/wiki/Tetris_&_Dr._Mario), [MobyGames](https://www.mobygames.com/game/17499/tetris-dr-mario/)

## 4. Dr. Mario 64 (N64, 2001) + Nintendo Puzzle Collection (GameCube, JP-only, 2003) — PRIORITY

**Confirmed: yes, different characters have different CPU play styles**, and this is now
backed by actual decompiled source, not just wiki description.

### 4a. Story-mode roster [WIKI]

Playable protagonists: **Dr. Mario** and **Wario** (story: "Dr. Mario and the Cold
Caper" — Mad Scienstein, acting on orders from the shadowy **Rudy the Clown**, steals
Dr. Mario's Megavitamin supply to fuel the virus outbreak; both protagonists chase him to
Rudy's castle across 8 stages).

Opponent/selectable cast, drawn from **Wario Land 3**'s enemy roster (see §4c on why):
Spearhead, Webber, Silky, Appleby, Jellybob, Octo, Helio, Lump, Hammer-Bot, **Mad
Scienstein**, and final boss **Rudy the Clown**; secret Stage 9 (Hard-or-above only) unlocks
**Vampire Wario** and **Metal Mario**. [WIKI — giantbomb.com 403'd our fetch; list is
synthesized from Super Mario Wiki + Mario Fandom search results, cross-checked against the
dedicated Mad Scienstein Super Mario Wiki page, which independently confirms: he appears in
*Wario Land 3*, *Wario Land 4*, *Dr. Mario 64*, and the *Super Mario-kun* manga; is Rudy's
minion; and **is explicitly playable in multiplayer mode** — i.e., he's a selectable
CPU/human character with his own difficulty rating, not just a cutscene NPC.]

### 4b. Difficulty structure [WIKI]

Four global difficulty levels gate virus count and drop speed (Easy/Normal/Hard/S-Hard,
roughly 12–28/24–40/48–64/40–64 viruses respectively per one source's examples — treat the
exact numbers as indicative, not verified against ROM). Independently, **each character
carries a 1–5 star CPU-strength rating**, extendable to 6 stars under a Hard-difficulty
toggle and 7 stars under an "S-Hard" toggle — i.e., difficulty and character-identity are
two separate, multiplicative knobs, not one slider.

### 4c. AI source — [CODE], from active decompilation projects

Two matching-decompilation repos exist and share a lineage:

- **`AngheloAlf/drmario64`** — N64 original, in progress, has `src/main_segment/aiset.c`
  and `include/{ai,aiset}.h`. Requires the user's own `baserom.us.z64` to build (no ROM
  redistribution). Also has `cn` and `gw` region configs, suggesting China/prototype
  variants exist in the decomp's scope — not investigated further here.
- **`NewGBAXL/drmario64-gc`** — the GameCube "Nintendo Puzzle Collection" port (`GPZJ01`,
  JP Rev 0), in progress, has the *same* `aiset.c`/`aiset.h`/`ai.h` **plus** an
  `aidata.c` — but `aidata.c` is a **0-byte placeholder** in the repo (confirmed via
  direct `curl`, HTTP 200, 0 bytes). This matches standard decomp-project convention:
  copyrighted per-character numeric tables aren't committed, and are presumably extracted
  from the user's own ROM at build time. **The tables' existence is confirmed by the
  header (`aiset.h`); their literal values are not published anywhere we found.**

We pulled and read `aiset.c` (4,027 lines) directly. It ships a comment block listing
**recovered original function names** (from debug symbols), which are Japanese-romanized
and genuinely informative:

| Function | What it evidently does |
|---|---|
| `aifPlaceSearch` / `aifMoveCheck` / `aifTRecur` / `aifTRecurUP` / `aifYRecur` / `aifYRecurUP` | BFS-style reachability search over the board's T-shaped and Y-shaped landing edges — i.e., enumerates every placement the CPU could drop a capsule into, split by "T edge" vs "Y edge" contact geometry |
| `aifRensaCheckCore` / `aifRensaCheck` / `aifSearchLineMS` | **"Rensa" = Japanese for chain/combo.** The CPU explicitly searches ahead for chain-combo setups before committing a placement — not just reactive line-clearing |
| `aiSetCharacter` | Reads current board state (`aiFieldData`) and derives a per-character behavioral parameter set — the literal function that turns "which character is this" into "how does it play" |
| `aiCOM_MissTake` | **Rubber-band mercy, verified line-by-line:** `PlayTime` increments every call; once `PlayTime > 18000` (5:00 at 60fps), `MissRate = (PlayTime - 18000) / 720` — the CPU's mistake rate climbs roughly **+1 unit every 12 seconds after the 5-minute mark.** This is a genuine, code-confirmed "the CPU gets worse the longer the match runs" mechanic — not community folklore. |
| `aiWall` / `aiGoalX` / `aiGoalY` | An explicit defensive "wall" concept plus explicit X/Y target-cell goal-seeking, separate from the chain search |
| `fool_mode`, `s_hard_mode` | Two more boolean difficulty/personality toggles beyond the star system |
| `BadLineRate[][8]`, `WallRate[][8]`, `bad_point[]`, `bad_point2[]`, `pri_point[]` | An explicit weighted-scoring eval-table system — structurally the same idea as our own project's tuned eval constants (`vrdy8`/`buried48`/`rdyext8`/`setup32`/`matched48`, see [[dr-mario-coef-opt]]) |
| `aiVirusLevel[][3]`, `aiDownSpeed[][3]`, `aiSlideFSpeed[][3]`, `aiSlideSpeed[][3]` | 3-column tables (matching the Easy/Med/Hard tiers) for per-difficulty virus count and drop/slide speed |
| `struct_ai_char_data` (16 entries, `AI_CHAR_DATA_LEN`) with `speed`, `performance[8]`, plus several 16-length behavior arrays; `struct_ai_param[6][8]` | **This is the personality-knob table, confirmed in the header even though the data itself isn't published.** 16 character slots × an 8-wide performance vector × a further 6-tier × 8-parameter matrix. Nintendo's own engineers built exactly the "few named characters, each a coefficient vector, gated by a difficulty matrix" design our task #33 is aiming for. |

TCRF also documents (via search synthesis, not a direct successful fetch — see caveat
below) unused content consistent with a scrapped-and-repurposed roster: an unused Vampire
Wario animation frame, an unused SM64-style coin, and **unused Japanese names for cut
characters — Peach, Bowser, Magikoopa, Piranha Plant, Boo, Wiggler, Shy Guy, Cheep Cheep,
Bob-omb, Koopa Troopa** — plus a debug-menu reference to "Nurse Peach." Read together with
the shipped roster being Wario Land 3 enemies, this strongly suggests **the original plan
was a traditional Mario-cast roster that got swapped for the Wario Land 3 cast**
mid-development. [INFER, moderate confidence — the individual facts are WIKI-sourced, the
synthesis connecting them is ours.]

**Caveat on this survey's own tooling:** two separate `WebFetch` attempts at `tcrf.net`
pages (Dr. Mario 64, and Tetris & Dr. Mario) returned garbled/unrelated content ("this page
discusses file-system manipulation instructions for LLM agents") rather than 403/404 —
distinct from the clean 403 GiantBomb gave us. We could not get a real TCRF page body this
session; the TCRF-attributed facts above come from `WebSearch` result *summaries* of TCRF
content, which is one hop less reliable than a direct fetch. Flagging so nobody treats
those specific claims as CODE-tier.

### 4d. GameCube "Nintendo Puzzle Collection" version [WIKI]

Direct port, JP-exclusive, differences are cosmetic only: logo drops "64", copyright-years
formatting, "PRESS ANY KEY" replaces "PRESS ANY BUTTON," Nintendo logo font changed. No
gameplay or AI differences found. A third repo, `theboy181/drmario64_recomp_plus`, builds a
native recompilation on top of the decomp — potentially the easiest way to get a
scriptable, hookable Dr. Mario 64 binary for benchmark automation (see §7c).

Sources: [Dr. Mario 64 - Super Mario Wiki](https://www.mariowiki.com/Dr._Mario_64), [Mad Scienstein - Super Mario Wiki](https://www.mariowiki.com/Mad_Scienstein), [Dr. Mario 64 - TCRF (via search)](https://tcrf.net/Dr._Mario_64), [Nintendo Puzzle Collection - Super Mario Wiki](https://www.mariowiki.com/Nintendo_Puzzle_Collection), [AngheloAlf/drmario64](https://github.com/AngheloAlf/drmario64), [NewGBAXL/drmario64-gc](https://github.com/NewGBAXL/drmario64-gc), [decomp progress](https://angheloalf.github.io/drmario64/), [theboy181/drmario64_recomp_plus](https://github.com/theboy181/drmario64_recomp_plus)

## 5. Dr. Mario Online Rx (WiiWare, 2008)

**CPU opponent: yes.** [WIKI] Vs. CPU mode offers three tiers — Easy/Normal/Hard — selected
directly as "CPU Level" rather than by adjusting drop speed (speed control is disabled
against the CPU, implying tier controls speed internally, matching the SNES/N64 pattern of
tier bundling multiple parameters together rather than exposing them separately).

Sources: [Dr. Mario Online Rx - Super Mario Wiki](https://www.mariowiki.com/Dr._Mario_Online_Rx), [Dr. Mario Online Rx - MiiWiki](https://miiwiki.org/wiki/Dr._Mario_Online_Rx)

## 6. Dr. Mario Express (DSiWare, 2009)

**CPU opponent: yes**, with two notable design details beyond a difficulty picker. [WIKI]
Easy/Normal/Hard as usual, but the game separately exposes **"CPU field difficulty"** as
its own setting, and — distinctively — **shows the CPU's live playfield on the DSi's other
screen**, so the human player watches the opponent's board in real time during play. Attack
rule: clearing multiple matches in one move sends up to **4 garbage capsules**, scaled by
match count, with garbage color tied to which color(s) were matched.

Sources: [Dr. Mario Express - Super Mario Wiki](https://www.mariowiki.com/Dr._Mario_Express), [Dr. Mario Express - NintendoWiki](https://niwanetwork.org/wiki/Dr._Mario_Express)

## 7. Dr. Luigi (Wii U, 2013) — including Operation L

**CPU opponent: yes**, available in both **Operation L** and **Retro Remedy** modes.
[WIKI] Operation L's headline mechanic swaps the standard 2-piece capsule for a **4-piece
L-shaped tetromino-style piece**, which changes the placement action space substantially —
"makes it easier to vanquish viruses and speed up progress" per official copy. We found no
documentation of *distinct CPU personalities* here (unlike Dr. Mario 64); it reads as a
straight difficulty-tiered CPU bolted onto a mutated piece-shape ruleset, not a
character-driven system.

Sources: [Dr. Luigi - Super Mario Wiki](https://www.mariowiki.com/Dr._Luigi), [Nintendo Dr. Luigi manual PDF](https://www.nintendo.com/eu/media/downloads/games_8/emanuals/wii_u_6/dr__luigi/ElectronicManual_WiiU_DrLuigi_EN.pdf)

## 8. Dr. Mario: Miracle Cure (3DS, 2015)

**CPU opponent: yes**, in Vs. CPU mode. [WIKI] Difficulty and drop speed are bundled again:
Easy=Slow, Normal=Medium, Hard=High. Modes are **Miracle Cure Laboratory**, **Custom
Clinic**, and **Virus Buster** — note the team lead's brief speculated a "Retro Remedy"
mode here, but that name belongs to **Dr. Luigi (Wii U)**, not Miracle Cure; we found no
"Retro Remedy" mode in any Miracle Cure source. Flagging the correction explicitly since it
was named in the task brief.

Sources: [Dr. Mario: Miracle Cure - Super Mario Wiki](https://www.mariowiki.com/Dr._Mario:_Miracle_Cure), [Gaming Nexus review](https://www.gamingnexus.com/Article/4836/Dr-Mario-Miracle-Cure/)

## 9. Dr. Mario World (mobile, 2019–2021)

**No CPU opponent in the traditional sense — and the game is dead.** [WIKI] Versus Mode
(unlocked at player level 20) is exclusively live PvP: random matchmaking or "Vs. Friends"
via Facebook/LINE. The game **required a permanent internet connection** and had **no
offline mode of any kind**; it was **shut down October 31, 2021** and cannot be played or
benchmarked today at all.

What *is* personality-adjacent here, as the brief flagged, is the **Doctor + Assistant
loadout system** — a genuinely different design axis from every other title in the family.
Playable "Doctors" each carry unique active/passive skills; players separately equip an
"Assistant" (mostly generic Mario enemies — Pokey, Koopa Troopa, Bob-omb, etc.) that grants
a small passive bonus (e.g., Pokey: 10% chance of +3 seconds in timed stages; Koopa Troopa:
+50 points per capsule remaining at stage end; Bob-omb: +800 points in Stage mode, a
different effect in Versus). **This is a data-driven cosmetic/stat-loadout system, not a
behavioral-AI personality system** — it changes what bonuses a human player gets, not how
any CPU plays. Worth naming as a *contrasting* design pattern in the synthesis below: two
totally different ways the franchise has expressed "character personality" (DM64's
behavioral AI parameters vs. World's loadout stat-bonuses).

Sources: [Dr. Mario World - Super Mario Wiki](https://www.mariowiki.com/Dr._Mario_World), [Dr. Mario World Doctors & Assistants - Gamer Journalist](https://gamerjournalist.com/dr-mario-world-doctors-assistants/), [Dr Mario World Offline Modes - GameRevolution](https://www.gamerevolution.com/guides/564865-dr-mario-world-offline-modes-play-offline-online)

## 10. Fan/homebrew AI work beyond meatfighter

Search turned up three more items worth recording, none previously known to us:

- **`pollyzoid`'s "Dr. Mario NES AI decompiled" gist** — despite the name, this is a
  **fan-made single-player automation bot**, not an analysis of official CPU code (the NES
  game has none, per §1). It's Java, drives an NES emulator via the **Nintaco remote API**,
  and plays by reading the playfield, running a **breadth-first search over pill
  placements/rotations, evaluating 2 plies ahead** with a heuristic (virus count, color
  clustering, tile heights, empty space). Structurally similar in shape to our own
  depth-2/depth-3 planner — worth a skim as an independent-invention cross-check, not a
  prior-art dependency. [Gist](https://gist.github.com/pollyzoid/a42002feabcf3f7fc7483365cdd04d31)
- **`Jonny5-5/Dr-Mario-AI`** — a Python bot targeting **SNES9x** (built, per the author, "to
  beat my dad in Dr. Mario"), so it's almost certainly automating **Tetris & Dr. Mario**
  (the only SNES Dr. Mario). Documentation is thin (no README detail on technique — vision
  vs. memory-read vs. search); we could not confirm whether it plays against the SNES's own
  VS.COM CPU or just automates single-player. Worth a deeper look only if the project wants
  SNES-side prior art beyond meatfighter. [GitHub](https://github.com/Jonny5-5/Dr-Mario-AI)
- **No academic RL papers target Dr. Mario specifically.** Multiple search passes for
  "Dr. Mario reinforcement learning," "Dr. Mario gym environment," and "Dr. Mario AI
  testbed" returned only generic *Super Mario Bros.* platformer RL papers (Mario AI
  Benchmark, RAMario, various DQN/PPO Super Mario Bros. papers) — none touch the puzzle
  game. This is a genuine negative finding: our [[dr-mario-paper-lane]] arXiv ambition
  appears to be uncontested ground, at least among what's indexed and findable via search.

meatfighter's own NES AI (already known — see [[dr-mario-meatfighter-prior-art]], notably
that it suspends gravity via `stallDrop` RAM writes, i.e. it is *not* input-only) remains
the only prior art with real technical depth that we're aware of; nothing found this
session changes that assessment.

---

## Synthesis

### S1. Dr. Mario 64's roster as a concrete personality-knob menu

The decompiled `aiset.c` structure (§4c) validates, in a shipped commercial Nintendo game,
almost exactly the design shape our task #33 is reaching for: a small number of *named*
characters, each a coefficient vector, gated by an orthogonal difficulty matrix rather than
one continuous slider. Mapping DM64's recovered concepts onto our own project's existing
eval knobs (see [[dr-mario-coef-opt]], [[dr-mario-chain-attack-channel]],
[[dr-mario-tempo-chew]]):

| DM64 concept [CODE] | Our nearest existing knob | Notes |
|---|---|---|
| `aifRensaCheck` (chain-ahead search) | `w_chain` / the chain180 vs chain360 vs lnk1 arm choice | DM64 proves "search for chains before committing" is worth dedicating real engine time to, not just scoring chains opportunistically at the leaf |
| `ai_char_data.speed` field | Our tempo/slam-gate constants (`K_OPEN`, slam confidence gates) | Direct 1:1 mapping — "how fast/aggressively does this personality drop" |
| `aiWall`, `aiGoalX/aiGoalY` | `buried`/`matched`/`setup` weights | DM64 splits "avoid burying" (wall) from "aim at a specific cell" (goal) as two separate mechanisms; we currently fold both into leaf-eval weights — worth trying as two separate root-search biases instead |
| `BadLineRate`/`WallRate`/`bad_point`/`pri_point` tables | `vrdy8`/`buried48`/`rdyext8`/`setup32`/`matched48` | Same idea (a tuned weighted-badness table), different granularity — DM64's is 8-wide per difficulty tier, ours is a flat 5-constant vector; a tier-indexed table is a plausible upgrade path if we want difficulty *and* personality to vary independently the way DM64 does |
| `fool_mode` / `s_hard_mode` / star rating | Discrete arm-select (chain180/chain360/lnk1) as "presets" | DM64 validates presenting personality as a short discrete menu (character × difficulty) rather than exposing raw sliders to players — matches our current arm-select framing better than a continuous-knob UI would |
| **`aiCOM_MissTake`** (time-gated mercy) | **Nothing — this is new** | See S4 below; this is the one mechanism in the whole survey we don't have an analog for at all |

### S2. Attack-rule variations worth simulating

- **Match-size-scaled garbage with color-tied identity** (Dr. Mario Express, §6): sends 1–4
  garbage capsules scaled by match count, garbage color tied to the matched color(s). This
  is a *different* rule from our own ROM-verified NES attack rule (`comboCounter` sums
  across cascade steps — see [[dr-mario-rom-attack-rule]]), but since we've already proven
  the NES rule is ROM-true and that "fixing" it toward other plausible rules regressed
  performance, this is a **note for context, not a change to make** — the family diverges
  on attack rules across titles and we're correctly anchored to *our* platform's actual rule.
- **Dual-visible opponent field** (Dr. Mario Express): showing the CPU's live board on a
  second screen is a spectator/UX idea, not an attack-rule idea, but worth flagging for any
  future dual-display or stream-overlay work — it's a legibility feature the family already
  validated works for puzzle VS.
- **4-piece L-shaped capsules** (Dr. Luigi Operation L, §7): a fun mutator for spectacle/
  benchmark variety, but not portable to our NES-ROM-faithful action space without leaving
  ROM-true territory — filed as a "not for the real cart" curiosity only.

### S3. Benchmark-opponent opportunities, ranked by practicality

1. **HIGH — SNES Tetris & Dr. Mario VS.COM.** ROM already owned and hash-verified, 3 fixed
   difficulty tiers keyed to virus color, same publisher/era-adjacent puzzle mechanics.
   Blocked entirely on the parked navigation wall ([[tdm-snes-nav-wall]]) — resuming that
   study (untested leads: shoulder/face buttons for the Game Select cursor;
   cross-core check via snes9x-gtk/retroarch to rule out a Mesen2-specific input bug) is the
   single highest-leverage next step to unlock a real, tiered, franchise-native benchmark
   opponent.
2. **MEDIUM — Dr. Mario 64 via the community decomp.** A genuine matching decompilation
   with recovered AI function names exists for both the N64 original and the GameCube port,
   plus a recompilation project (`drmario64_recomp_plus`) that could make scripting/hooking
   far easier than raw N64 emulator automation. This is the *richest* personality benchmark
   in the family (8+ named characters × 4 difficulty tiers × per-character star ratings),
   but requires (a) the user to own a legal N64 or GC ROM — **currently absent from
   `~/gaming`**, so this is gated on acquisition, not just engineering — and (b) real
   engineering to wire automated input + state-reading against an unfamiliar 3D-engine
   codebase, even though the puzzle logic itself is flat 2D.
3. **LOW — Wii/DSiWare/Wii U/3DS titles.** Dolphin emulates Wii/Wii U well and is
   Lua-scriptable, so Dr. Mario Online Rx and Dr. Luigi are *technically* automatable if
   owned — but none of them have decomp prior art, so the CPU stays a black box (you'd only
   ever get "win rate vs. a named difficulty," not DM64's rich style diversity). No
   ownership confirmed for any of these on this box.
4. **NOT PRACTICAL — Dr. Mario World.** Servers shut down permanently on 2021-10-31; the
   client cannot connect, cannot be benchmarked, full stop.

### S4. What challenges our current design assumptions

- **`aiCOM_MissTake` is a mechanism we don't have any analog for.** Every knob in our
  current design (chain weight, tempo gates, garbage cadence, defensive weights) is about
  *how strong* the AI plays. DM64 ships a orthogonal, code-confirmed **honesty/mercy**
  mechanic: the CPU's mistake rate climbs the longer a match runs (past 5:00, +1 unit every
  12 seconds). Given our own [[dr-mario-tv-dignity-bar]] standard (no self-topouts, no
  marooned halves, wins-by-clearing, before any living-room demo) and the general goal of
  being a *good host* for casual human play rather than the strongest possible engine, a
  time-gated softening is a concrete, Nintendo-precedented, low-risk mechanism worth
  prototyping as a distinct "guest-friendly" personality tier for task #33 — genuinely new
  relative to anything currently in our knob set.
- **DM64's shipped design externally validates our current direction**, not just as
  inspiration but as confirmation: "a handful of named characters, each a coefficient
  vector, gated by an independent difficulty matrix" is exactly what a AAA-era Nintendo
  team built for this exact game, which is reassuring evidence against second-guessing the
  discrete-arm-select framing already in place.
- **The family-wide absence of any CPU before 1994 reframes our own project's marketing
  angle.** Every 8-bit-era Dr. Mario (NES, Famicom, arcade VS./PlayChoice-10, Game Boy)
  shipped with *zero* CPU opponents — the first one appears on SNES, five years later, on
  hardware roughly 15x more powerful. Combo Stomper isn't "yet another Dr. Mario CPU" — it's
  the first CPU opponent to ever run on the original 1990 NES/Famicom hardware, full stop.
  Worth stating explicitly in any public-facing framing of the project.
- **No competing academic work exists.** Multiple search angles for Dr. Mario + RL/AI
  testbed research came back empty except generic Super Mario Bros. platformer papers — the
  [[dr-mario-paper-lane]] arXiv target remains genuinely open ground as far as this survey
  could determine.
