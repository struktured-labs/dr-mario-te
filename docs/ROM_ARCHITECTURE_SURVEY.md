# Dr. Mario (NES) ROM Architecture Survey

**Purpose.** Mine the community's accumulated knowledge of the Dr. Mario (NES) ROM to
build an architecture map for the TE v9 roadmap, and to identify the DRMC tournament
build (issue #4). Primary evidence: the two public disassemblies, the Dr. Mario
Community wiki, and **byte-level diffs of the community IPS patches applied to our exact
base ROM**.

**Our base ROM.** `drmario.nes`, md5 `d3ec44424b5ac1a4dc77709829f721c9`. This is
bit-identical to brianhuffman's `drmario.nes` reference, i.e. **Dr. Mario (Japan, USA)
Rev 0** (the common USA cart). Rev A is a *different* ROM (md5 `8181d696…`); the
Nostaljipi disassembly builds Rev A, brianhuffman builds both. Every community NES patch
surveyed here applies cleanly to our Rev 0 base at sensible code offsets, so they are all
built against the same ROM we ship on.

**Method / access note.** `romhacking.net` (RHDN) now sits behind a Cloudflare
challenge; neither WebFetch nor curl can scrape its game/hack pages, and archive.org is
also blocked to our fetcher. The RHDN census below is therefore assembled from search
snippets plus cross-references, and is *best-effort* on descriptions. The architecture and
patch-footprint sections do **not** depend on RHDN — they come from the GitHub
disassemblies, Data Crystal, the drmar.io wiki, and direct IPS diffing, which are stronger
sources than RHDN prose anyway. Reproduce the diffs with `tools/ipsdiff.py` (committed).

---

## 1. Census — hacks, disassemblies, tools

### 1a. NES ROM hacks

Two distribution channels exist and only partly overlap: **romhacking.net** (older,
general-audience hacks) and **playdm.net** (the Dr. Mario Championship community's own
patch host, curated on `wiki.drmar.io`). The competitive/tournament-relevant work lives on
playdm.net, not RHDN.

| Hack | Source | What it changes | Roadmap interest |
|---|---|---|---|
| **DR. MARIO TE (Training Edition)** #9292 | RHDN (ours) | Pause → study mode | ours |
| **Dr. Mario Turbo** #6158 | RHDN + playdm | Halves clear/drop time, adds **hard-drop (Up)**, SNES RNG, better VS garbage; expands ROM to 128K+128K, new CHR | speed/garbage mechanics |
| **Dr. Mario NROM Hack** #7640 | RHDN | MMC1→NROM mapper conversion (tilesets/anims dropped) | mapper reference |
| **Dr. Mario – no punish** #3330 | RHDN | Removes VS punishment blocks on 2+ combos | garbage logic |
| **Dr. Mario – 2 Players Inverse** #2792 | RHDN | Same virus layout both sides, colors swapped per side | virus-placement mirror |
| **Dr. Mario Combo Levels** #5922 | RHDN | Combo-oriented level set | level tables |
| **Dr. Wario** #647 | RHDN | WarioWare "Dr. Wario" reskin | cosmetic |
| **Super Dr. Mario Bros.** #6962 | RHDN | *SMB1* hack (platformer), not the DM engine | out of scope |
| **Dr. Mario DX** #5281 | RHDN | Cosmetic/QoL DX-style hack | cosmetic |
| **DrMC (seed + speed)** `Dr._Mario_-_DrMC_v1.0.ips` | **playdm.net** | **Seed select+display, fine-speed display, ULT speed, disables music select** | **the tournament build — see §4** |
| **Seed mod** `Dr._Mario_-_Seed.ips` | playdm.net | Seed select+display via menu ("Down" from music), deterministic pills | seed UI |
| **Speed display mod** | playdm.net (Discord CDN) | Shows combined/fine speed instead of LOW/MED/HI | SPD readout |
| **Level cap mod** | playdm.net (Discord CDN) | Removes the level-24 cap | extended study |
| **SNES RNG mod** `Dr_Mario_SNES_RNG.ips` | playdm.net | Swaps NES pill RNG for the SNES algorithm | RNG swap |
| **God speed** `Dr_Mario_IL_Stars_Japan_USA.ips` | playdm.net | Seeds pinned to per-level world-record seeds | seed pinning |
| **Self-garbage / Combo-rollback / Combo-only** | playdm.net | VS-garbage-to-self; retry on non-combo; reset-unless-full-clear | training variants |
| **Versus Trainer v1 / v2** | playdm.net | AI-opponent practice, difficulty via 2P level select | AI-practice |

SNES-only community hacks (for completeness): **Statistics mod**, **Seed+Stats mod**
(playdm.net) — in-game timers (Throw/Drop/Land/Clear/Fall) and seed select.

> **Disambiguation for issue #4:** RHDN **#8245 "Dr. Mario Tournament Edition" is a
> SNES/SFC hack** (updated Nov 2023), unrelated to the DRMC NES broadcast build. Do not
> confuse it with the NES tournament ROM.

### 1b. Disassemblies (the highest-value architecture resource)

| Project | Builds | Toolchain | Notes |
|---|---|---|---|
| **Nostaljipi/dr-mario-disassembly** | Rev A | ASM6f | Fully labeled, modular: `defines/` (RAM, ZP, constants, registers), `data/drmario_data_game.asm` (all tables), `prg/` split by subsystem (game_logic, level_init, level_end, visual_*, audio_*), and an **`unused/` dir documenting every free region** ($CED5, $D2CC, $FAFD, $FF32, $FFD9, EU $FC29). This is the reference to port our planner/AI against. |
| **brianhuffman/drmario** | Rev 0 **and** Rev A | ca65 | `make all` / `make test` with md5 verification; `drmario.nes.md5` == our base. Good for byte-exact rebuilds and revision checks. |

RHDN forum thread **#33836 "Dr.Mario NES Disassembly"** (Nostaljipi, Nov 2021) is the
announcement for the first project.

### 1c. Tooling ecosystem (all by **dmwit** unless noted — the community's technical anchor)

| Tool | What it is |
|---|---|
| **dmvs** (`github.com/dmwit/dmvs`) | fceux Lua for online 1v1 (host/connect). The netplay layer; also the natural place a broadcast memory-overlay would hook. |
| **dr-mario-ngrams** | Exact reimplementation of the NES pill-generation RNG + statistics |
| **seed map** (`dmwit.com/dr_mario_seed_map.bin`) | Successive-seed data; index = `65534*level + (seed & ~1) - 2` |
| **Granivore** (`tools.drmar.io/granivore`) | Identifies the exact seed from a board state |
| **Identify** (`tools.drmar.io/identify`) | ROM-variant validator (patches are ROM-specific) |
| **DM Glampers** | Level-range calculator for timed races/tournaments |
| **MC Mario** | Elo-style rating + handicap for 2P |
| **Bo Krif Ulse** | fceux maneuver-trainer (custom boards, repeat scenarios) |
| **DM Effects** | fceux "crowd-control" random-challenge mod |
| **meatfighter AI** (`meatfighter.com/drmarioai/`) | The 2017 Dr. Mario AI our roadmap already credits |

---

## 2. Architecture knowledge map (mechanism → known → address → source)

Addresses are CPU/RAM unless noted "file". Sources: **[DC]** Data Crystal, **[N]**
Nostaljipi disasm, **[Δ]** proven by our IPS diffs, **[mem]** our existing notes.

### 2a. RAM map — player state (`p1_RAM $0300`, `p2_RAM $0380`, `$30` bytes each) [N][DC]

| Addr (P1 / P2) | Meaning |
|---|---|
| `$0301-0304 / $0381-0384` | Falling pill colors, 1st–4th half (00=Yellow 01=Red 02=Blue) |
| `$0305 / $0385` | Falling pill X · `$0306 / $0386` Falling pill Y |
| `$030A / $038A` | **speedUps** (increments every 10 pills; capped) |
| `$030B / $038B` | **speedSetting** (LOW/MED/HI; frames form, 0x26 fast … 0x85 slow) |
| `$0312 / $0392` | **speedCounter** (compared against gravity table) |
| `$0316 / $0396` | **level** |
| `$031A-031B / $039A-039B` | **Next-pill preview** colors (1st/2nd half) — broadcast next-pill panel source |
| `$0320 / $03A0` | **speedIndex** ← the fine "SPD" number shown on the DRMC broadcast |
| `$0324 / $03A4` | **virusLeft** — broadcast "VIR" panel source |
| `$0325 / $03A5` | **fallingPillRotation** (00=orig 01=CCW 02=180 03=CW) — reconciles [mem]'s `$03A5`; DC's `$00A5` is the zero-page working copy |
| `$0327 / $03A7` | pillsCounter · `$0328/$03A8` virusToAdd · `$0329` attackColors(4B) |
| Playfield | P1 board `$0400-$047F` (8 cols × 16 rows = `$80` cells) [DC] |

Global/ZP [N][DC]: `$17` rng0, `$18` rng1, `$89` **rngSeed** (2 bytes), `$42`
spritePointer, `$43` frameCounter, `$46` mode, `$65` game-option cursor, `$F5/$F6` P1/P2
buttons pressed, `$F7/$F8` P1/P2 held, `$0727` number-of-players, `$0731` music type,
`$0740` anti-piracy flag (FF=on).

### 2b. Pill-generation RNG [Δ][N]

- **Entry the community replaces: `JSR $B771`**, called from exactly **4 sites** —
  `$82AD, $99DD, $9D0B, $9D3E` (file `0x2BD, 0x19ED, 0x1D1B, 0x1D4E`). Proven because
  `SNES_RNG.ips` and `Turbo.ips` redirect precisely these four `20 71 B7` instructions.
- Low-level primitive `randomNumberGenerator` (~`$B78B` [N]) rotates zp `rng0/rng1`
  ($17/$18); seed byte is `rngSeed $89`. Virus placement reads `rng0` for height, `rng1`
  for column/color, forcing one virus of each color per 4 (`rndColorQty=$01`).
- The **SNES RNG mod** is an 84-byte drop-in: 4 call-site redirects + a new generator at
  `$FB00`. This is the cleanest template for swapping RNG.

### 2c. Speed / gravity [Δ][N][mem]

- **Gravity table at `$A795`** (`LDA $A795,X`). Drop cadence: `speedUps ($030A) →
  speedIndex ($0320)`; the running `speedCounter ($0312)` must exceed `table[index]` for
  the pill to fall one row. `speedUps_max = $31` (49) caps the ramp.
- **The broadcast "SPD" number is `speedIndex $0320` / the `$A795` index** — DrMC hooks
  the table read at **`$8D8D`** (`LDA $A795,X` → `JSR $FC60`) to render it, and blanks the
  coarse LOW/MED/HI text (see §3). The broadcast "Speed Guide" maps SPD 32→Tetris L7 …
  80→L29.

### 2d. Levels, viruses, field geometry (constants) [N]

`selectableLvCap=$14` (20), `lvCap=$18` (24, the level-cap mod's target),
`finalCutsceneLv=$14`; `match_length=$04`; field `rowSize=$08 × heightSize=$10 =
fieldSize=$80`; `pillStartingX=$03 pillStartingY=$0F`; `attackSize_min/max=$02/$04`;
`demo_virus=$44 demo_level=$0A`. Level init/virus placement: `toLevel $817E`,
`initData_level $8216`.

### 2e. Text / HUD tile data (file offsets) [DC][Δ]

Congrats screen `0x20CC` "CONGRATULATIONS-", `20DC` VIRUS, `20E1` LEVEL, `20E7` SPEED.
In-game coarse speed labels `0x224D/2251/2255` LOW/MED/HI (`$A23D`, **blanked by DrMC**).
Menu `0x3E49` "1 PLAYER GAME", `0x4075` MUSIC TYPE, `0x40E0/40E7/40EE` FEVER/CHILL/OFF
(**overwritten by DrMC** to reclaim space). Title logo GFX `0x3A29-0x3AC3`; title tilemap
bottom row `0x3B06` (our branding anchor — **collides with Turbo**). HUD label tile runs
[N]: VIRUS=`$88-8C`, LEVEL=`$8E-92`, SPEED=`$C8-CC`, value tiles `$95`/`$D4`.

### 2f. Community free-space convention [Δ][N]

**Every** community NES hack parks its new code in the **fixed-bank tail `$FB00-$FFFF`**
(file `0x7B10-0x7FFF`), which the disassembly documents as unused (`$FAFD/$FF32/$FFD9`).
DrMC uses `$FB00-$FFAF`, Seed `$FB00-$FC5x`, SNES-RNG `$FB00-$FB2A`, GodSpeed
`$FB00-$FB51`, Turbo `$FB00-$FC44`. **This is the single most important compatibility
fact** (see §3).

---

## 3. Overlap / conflict analysis vs OUR footprint

### 3a. Our patch footprint (measured)

| Build | Region | File / CPU | Notes |
|---|---|---|---|
| **TE v5** (#9292, 30 B) | Pause routine | `0x17CA/0x17D4-D6/0x17DC` (`$97BA/$97C4/$97CC`) | keep-bg-on, drop OAM-clear, STUDY Y-pos |
| | Sprite table | `0x2969-0x2979` (`$A959`) | STUDY tiles |
| | CHR | `0x0AA18-0x0AA38` | STUDY letters |
| **v6/v7 branding** | Title tilemap | **`0x3B06` (`$BAF6`)** | STRUK LABS footer / subtitle anchor |
| | Footer hook | `0x0C34` (`$8C24`) | `JSR $88F6` → `JSR $BE56` |
| | Footer routine / data | `0x3E66` (`$BE56`) / `0x2008` (`$A1F8`) | |
| **STUDY v3.3** | Pause edits `$97B6-$97F3` + **5-part chain** | `$D2CC → $9FF8 → $A371 → $BE56 → $BC26` | uses **`$D2CC`** unused region + nametable gaps |

### 3b. Conflicts

1. **Turbo × our branding — DIRECT COLLISION.** Both rewrite title tilemap **file
   `0x3B06`**. TE expects the base bytes `42 FC FC…` there; Turbo overwrites with
   `16 17 18…`. **TE branding + Turbo cannot be naively stacked**; the title edit would
   need relocating. (Turbo also expands the ROM and stamps a `DiskDude!` header — it is a
   whole-ROM replacement, not a small IPS.)
2. **`$FB00` free block — NO collision with our core.** Published TE v5 and STUDY v3.3
   deliberately live in the **pause routine + `$D2CC` + nametable gaps**, *not* `$FB00`.
   So TE's engine coexists with DrMC/Seed/SNES-RNG/GodSpeed, which all occupy `$FB00`.
   **This is a genuine, bankable compatibility win** and should be preserved.
3. **Nametable data block `$BB00-$BE10` — adjacency, verify per-combo.** DrMC writes
   `$BB57-$BBC0` and `$BD5E`; Seed writes `$BDAA-$BE10`. Our STUDY part3c is `$BC26` and
   our footer/part3b routine is `$BE56` — interleaved in the same block but at distinct
   offsets. Likely non-overlapping, but any TE+DrMC or TE+Seed combo must be byte-checked
   here (use `tools/ipsdiff.py`).
4. **Pause routine `$978E-$97F3` — uncontested.** No community hack touches it; TE owns
   this region outright.
5. **Internal note:** our own v6/v7 footer routine and STUDY v3.3 part3b both target
   `$BE56` (deconflicted in the combined DRROTFIX build) — keep that in mind when layering
   TE features.

---

## 4. DRMC-ROM identification verdict (issue #4)

**DRMC = the *Dr. Mario Championship*** — an annual in-person **NES** tournament (2025:
Nov 7-9, Arcade Legacy, Cincinnati; matches our known live-events list). Its patches are
hosted on **playdm.net** and curated on `wiki.drmar.io`.

**Verdict:** The broadcast build is the community **"DrMC" NES hack**
(`playdm.net/ips/Dr._Mario_-_DrMC_v1.0.ips` lineage) applied to the **standard USA NES
Dr. Mario Rev 0 — the exact ROM we already ship on** (md5 `d3ec4442…`). Its on-ROM
features are **settable/displayed RNG seed** and a **fine on-screen SPD number**
(it blanks LOW/MED/HI and hooks the `$A795` gravity read at `$8D8D`; it also disables
music select to reclaim menu/CHR space). Confirmed by diffing the patch against our base.

**The styled per-player VIR/SPD/next-pill panels + "Speed Guide" are an OBS broadcast
overlay** (smooth non-NES fonts, bracket-colored boxes) layered on top, fed from game RAM:

- **SPD** ← `speedIndex $0320` (= the `$A795` index the DrMC hack surfaces)
- **VIR** ← `virusLeft $0324 / $03A4`
- **next-pill** ← `$031A/$031B` (P1) and `$039A/$039B` (P2)
- **seed** ← `rngSeed $89`, exposed by the hack itself

Given the community's fceux-Lua tooling (dmvs, bokrifulse, DM Effects are all fceux Lua),
the overlay is almost certainly **fceux running the DrMC ROM + a memory-reading Lua
overlay + OBS**. *Confidence:* ROM identity and RAM sources — **high, proven**; the exact
capture pipeline (fceux-Lua vs hardware+reader) — **high inference, not confirmed from a
public rules page** (no such page is linked from the wiki; worth a Discord/organizer
confirmation as the only open sub-question).

**Not the DRMC ROM:** RHDN #8245 "Tournament Edition" is **SNES**.

**Seed-compatibility takeaway for TE:** adopt the DRMC seed encoding directly —
`rngSeed $89` + the dmwit seed-map (`65534*level + (seed&~1) - 2`) — so TE seeds are
directly comparable to tournament seeds. Granivore/Identify define the interop contract.

---

## 5. Techniques worth stealing for TE v9 (seed/SPD first)

Ordered by value for a *study* edition. All of these fit our free-space discipline
(reuse `$FB00`-family or `$D2CC`) and are proven to apply to our exact base.

1. **Fine SPD display** (from DrMC / Speed-display mod). Hook `$8D8D`
   (`LDA $A795,X` → `JSR <new>`), render `speedIndex $0320` as two digits, blank the coarse
   LOW/MED/HI at `$A23D`. Highest study value: a study cart should show the *exact* speed.
2. **Seed display + set** (from Seed.ips / DrMC). Menu-cursor hook at `$65`/`$9A31` for a
   seed-entry UI writing `rngSeed $89`; draw the seed on the field. Makes every study run
   reproducible **and comparable to DRMC seeds** — directly closes issue #4's seed ask.
3. **VIR/SPD HUD panels** mirroring the broadcast, using HUD label tiles (`$88-8C` VIRUS,
   `$C8-CC` SPEED) + values `$0324/$0320`. Optional cosmetic parity with the tournament.
4. **Level-cap removal** (level-cap mod): defeat the `lvCap=$18` check to study levels >24.
5. **SNES-RNG toggle** (84-byte swap of the `$B771` entry): let TE optionally match SNES
   pill distribution for cross-version study.
6. **Stack, don't fork.** Keep TE's engine off `$FB00` (it already is) so TE can be
   **layered on top of the DrMC/Seed patches** to study the actual tournament ROM. Ship TE
   explicitly against **Rev 0** and publish the md5 (patches are ROM-specific; use the
   community `Identify` discipline).
7. **Port against the disassembly.** Use **Nostaljipi** (labeled Rev A source) +
   **brianhuffman** (Rev 0/A buildable) as the reference for any 6502-side AI/planner port
   — real labels for `$B771` RNG, `$A795` gravity, `toLevel $817E`, virus placement.

---

*Reproduce all patch footprints:* `./tools/ipsdiff.py <patch.ips>` (diffs against the
Rev 0 base). Community IPS files are hosted at `playdm.net/ips/`.
