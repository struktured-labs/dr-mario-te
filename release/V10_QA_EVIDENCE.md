# TE v10 — QA evidence

All checks ran on the shipping bytes: the ROM that `release/drmario_te_v10.ips` produces from the
clean base, md5 `512b815b9a2944754af3b28e9852d4ed`. The published v9 ROM (`0f8f5d89`, the
romhacking.net release v10 replaces) and the stock base were run on the same scripts as controls.

## 1. Static gates (`build_te_v10.py`, `te_release_gates.py`, `tests/test_te_v10_release.py`)

| check | result |
|---|---|
| build reproduces: base + committed v9 BPS + DRSTUDYEND + stamp | md5 `512b815b…` pinned; the build refuses on any drift |
| delta vs published v9 | exactly 35 bytes: the 15 DRSTUDYEND bytes + 20 bytes in 4 stamp CHR tiles |
| DRSTUDYEND writes only stock bytes | all 15 sites equal the base ROM before patching |
| DRSTUDYEND port == shipped cart | `apply_studyend(c960dd49)` == `8c6e4196` byte for byte |
| KIL / garble sites vanilla | `$BC26 $BE56 $9FF8 $A371 $C0A9 $C0EF $CF00` == base |
| printing-table walk (`RB6C2_PRINT`, 21 tables, base and v10) | 0 changed bytes inside any read-set; walker self-check: TITLE ends at `$BD7C` and reads `$BC26` |
| two-sided | the same gates FAIL the published v6 build (4 sites, 58 bytes inside print tables) |
| IPS encoder edge cases | RLE records, "EOF" offset `0x454F46`, 0xFFFF split, resize refused |
| IPS carries no base bytes | 0 unchanged bytes in any record |

## 2. Patch round-trips

| applier | IPS | BPS |
|---|---|---|
| Floating IPS (Alcaro/Flips @ `ff216a7`, built from source) | `512b815b…` | `512b815b…` |
| `tools/ipsdiff.py` (independent reader) | `512b815b…` | n/a |
| `tools/te_release_kit.py` / `make_bps.py` decoders | n/a | `512b815b…` |
| Flips on the **No-Intro NES 2.0-headered** base | OK, header kept, body == v10 (`6724286d…`) | refused: "Expected checksum B1F7E3E9, got 556AE5C3" |

## 3. Mesen 2 full-game QA (`tools/te_release_qa/`)

`te_release_qa.lua` drives **both controllers** through real games: no RAM writes, every input goes
through the controller ports. It records a per-frame RAM hash for cross-ROM diffs and stops with a
FREEZE if any of these hold:
- the NMI clock `$43` stalls for more than 120 frames;
- any instruction executes from `$0000-$07FF` (the v6 KIL ran `$0301`);
- the capsule counters stop for 3000 frames of play.

Run: `tools/te_release_qa/run_release_qa.sh <v10.nes> <v9.nes> <base.nes>`, about 25 min.

Scenarios:

| scenario | what |
|---|---|
| `onep` | two 1P games, each with a STUDY pause and resume, played to game over |
| `twop` | human vs human. Match 1: P1/P2 alternate losing, 5 rounds to a 3-2 final. Match 2: 3-0. STUDY pauses mid-round. Checks the next match. |
| `clearwin` | rounds won by **clearing every virus**, the common real-play case, incl. a match final decided by a clear. A small solver plays the winning side; the other side stacks to the walls. |
| `shots` | level 10 vs 10 match for the screenshot set, plus a 1P STUDY pause |
| `cpuidle` | the inherited SELECT×2 VS CPU mode at level 0 with P1 idle |
| `soak` | at least 40,000 frames rotating 1P games (random level, random pauses), 2P matches (random levels and losers), clear-win matches and VS CPU matches |

Header and RAM variants:
- the `v10ni_*` runs use the same bytes behind the No-Intro NES 2.0 header (mapper 1, submapper 5);
- the `*_rndram` runs use `RamPowerOnState = Random`.

### Result

**TE v10 Mesen QA summary — 64/64 PASS** (`tools/te_release_qa/summarize_qa.py`; each assertion that rules something out is paired with a v9 positive control)

| result | check | detail |
|---|---|---|
| PASS | base_onep_np: completed, no freeze | DONE=0 frames=3204 ramExec=0 maxClockStall=2 [] |
| PASS | v10_clearwin: completed, no freeze | DONE=0 frames=29080 ramExec=0 maxClockStall=2 [] |
| PASS | v10_cpuidle: completed, no freeze | DONE=0 frames=6061 ramExec=0 maxClockStall=2 [] |
| PASS | v10_onep: completed, no freeze | DONE=0 frames=3376 ramExec=0 maxClockStall=2 [] |
| PASS | v10_onep_np: completed, no freeze | DONE=0 frames=3188 ramExec=0 maxClockStall=2 [] |
| PASS | v10_shots: completed, no freeze | DONE=0 frames=7428 ramExec=0 maxClockStall=2 [] |
| PASS | v10_soak_rndram: completed, no freeze | DONE=0 frames=51175 ramExec=0 maxClockStall=1 [] |
| PASS | v10_soak_zero: completed, no freeze | DONE=0 frames=52203 ramExec=0 maxClockStall=2 [] |
| PASS | v10_twop: completed, no freeze | DONE=0 frames=9561 ramExec=0 maxClockStall=2 [] |
| PASS | v10_twop_rndram: completed, no freeze | DONE=0 frames=9545 ramExec=0 maxClockStall=1 [] |
| PASS | v10ni_onep: completed, no freeze | DONE=0 frames=3376 ramExec=0 maxClockStall=2 [] |
| PASS | v10ni_twop: completed, no freeze | DONE=0 frames=9561 ramExec=0 maxClockStall=2 [] |
| PASS | v9d_clearwin: completed, no freeze | DONE=0 frames=29088 ramExec=0 maxClockStall=2 [] |
| PASS | v9d_cpuidle: completed, no freeze | DONE=0 frames=6061 ramExec=0 maxClockStall=2 [] |
| PASS | v9d_onep: completed, no freeze | DONE=0 frames=3376 ramExec=0 maxClockStall=2 [] |
| PASS | v9d_onep_np: completed, no freeze | DONE=0 frames=3188 ramExec=0 maxClockStall=2 [] |
| PASS | v9d_shots: completed, no freeze | DONE=0 frames=7424 ramExec=0 maxClockStall=2 [] |
| PASS | v9d_twop: completed, no freeze | DONE=0 frames=9565 ramExec=0 maxClockStall=2 [] |
| PASS | v10_clearwin: every end screen keeps both final boards, no sign | 4 end screens (2 match finals); signSprites=0 wipes=0 gameOverFills=0 |
| PASS | v10_clearwin: drawn bottles == board RAM at +150 | 4 end screens |
| PASS | v10_clearwin: next match starts clean | clean=1 dirty=0 |
| PASS | v10_cpuidle: every end screen keeps both final boards, no sign | 3 end screens (0 match finals); signSprites=0 wipes=0 gameOverFills=0 |
| PASS | v10_cpuidle: drawn bottles == board RAM at +150 | 3 end screens |
| PASS | v10_shots: every end screen keeps both final boards, no sign | 4 end screens (1 match finals); signSprites=0 wipes=0 gameOverFills=0 |
| PASS | v10_shots: drawn bottles == board RAM at +150 | 4 end screens |
| PASS | v10_soak_rndram: every end screen keeps both final boards, no sign | 25 end screens (7 match finals); signSprites=0 wipes=0 gameOverFills=0 |
| PASS | v10_soak_rndram: drawn bottles == board RAM at +150 | 25 end screens |
| PASS | v10_soak_rndram: next match starts clean | clean=6 dirty=0 |
| PASS | v10_soak_zero: every end screen keeps both final boards, no sign | 24 end screens (7 match finals); signSprites=0 wipes=0 gameOverFills=0 |
| PASS | v10_soak_zero: drawn bottles == board RAM at +150 | 24 end screens |
| PASS | v10_soak_zero: next match starts clean | clean=6 dirty=0 |
| PASS | v10_twop: every end screen keeps both final boards, no sign | 8 end screens (2 match finals); signSprites=0 wipes=0 gameOverFills=0 |
| PASS | v10_twop: drawn bottles == board RAM at +150 | 8 end screens |
| PASS | v10_twop: next match starts clean | clean=1 dirty=0 |
| PASS | v10_twop_rndram: every end screen keeps both final boards, no sign | 8 end screens (2 match finals); signSprites=0 wipes=0 gameOverFills=0 |
| PASS | v10_twop_rndram: drawn bottles == board RAM at +150 | 8 end screens |
| PASS | v10_twop_rndram: next match starts clean | clean=1 dirty=0 |
| PASS | v10ni_twop: every end screen keeps both final boards, no sign | 8 end screens (2 match finals); signSprites=0 wipes=0 gameOverFills=0 |
| PASS | v10ni_twop: drawn bottles == board RAM at +150 | 8 end screens |
| PASS | v10ni_twop: next match starts clean | clean=1 dirty=0 |
| PASS | v10_clearwin: virus-clear round ends keep the loser's board, no sign | 6 clear-win round ends |
| PASS | v10_soak_rndram: virus-clear round ends keep the loser's board, no sign | 6 clear-win round ends |
| PASS | v10_soak_zero: virus-clear round ends keep the loser's board, no sign | 3 clear-win round ends |
| PASS | v9d_clearwin (positive control, published v9): sign/wipe/GAME OVER detected | signSprites=4 wipes=4 gameOverFills=2 |
| PASS | v9d_cpuidle (positive control, published v9): sign/wipe/GAME OVER detected | signSprites=6 wipes=6 gameOverFills=0 |
| PASS | v9d_shots (positive control, published v9): sign/wipe/GAME OVER detected | signSprites=8 wipes=8 gameOverFills=1 |
| PASS | v9d_twop (positive control, published v9): sign/wipe/GAME OVER detected | signSprites=16 wipes=16 gameOverFills=2 |
| PASS | v10_onep: STUDY pause (text, per-player previews, frozen board, clean resume) | 2 pauses (2 1P / 0 2P), 2 resumes |
| PASS | v10_shots: STUDY pause (text, per-player previews, frozen board, clean resume) | 2 pauses (1 1P / 1 2P), 2 resumes |
| PASS | v10_soak_rndram: STUDY pause (text, per-player previews, frozen board, clean resume) | 6 pauses (1 1P / 5 2P), 6 resumes |
| PASS | v10_soak_zero: STUDY pause (text, per-player previews, frozen board, clean resume) | 6 pauses (1 1P / 5 2P), 6 resumes |
| PASS | v10_twop: STUDY pause (text, per-player previews, frozen board, clean resume) | 2 pauses (0 1P / 2 2P), 2 resumes |
| PASS | v10_twop_rndram: STUDY pause (text, per-player previews, frozen board, clean resume) | 2 pauses (0 1P / 2 2P), 2 resumes |
| PASS | v10ni_onep: STUDY pause (text, per-player previews, frozen board, clean resume) | 2 pauses (2 1P / 0 2P), 2 resumes |
| PASS | v10ni_twop: STUDY pause (text, per-player previews, frozen board, clean resume) | 2 pauses (0 1P / 2 2P), 2 resumes |
| PASS | clear-win rounds == published v9 until the clear-win match final | RAM identical through 4 virus-clear round ends; first difference f11419 = inside the final (state 7 from f11354, after its 64-frame wait) |
| PASS | 1P v10_onep == published v9 on every frame | 3376 frames, full RAM incl. stack identical |
| PASS | 1P v10_onep_np == published v9 on every frame | 3188 frames, full RAM incl. stack identical |
| PASS | 2P v10 == published v9 until the first round end; same match results after | first RAM difference at f739 = the first round-end frame f739; 8 rounds with identical winners/finals; mode transitions 46 vs 46, the first 38 on the same frame; frames 9565 vs 9561 (later drift = one-frame input-latch / NMI-phase shifts after the lighter round-end frame -- stock behaviour, PR #28 EVIDENCE.txt section 5) |
| PASS | No-Intro NES 2.0 header (v10ni_twop) == classic header on every frame | 9561 frames |
| PASS | No-Intro NES 2.0 header (v10ni_onep) == classic header on every frame | 3376 frames |
| PASS | stock base vs v10 (1P, informational) | first RAM difference f9 (title: footer sprites in the OAM shadow); mode sequence identical=False; differing frames by mode {0: 232, 1: 3, 4: 377, 5: 1, 7: 185, 8: 1} |
| PASS | v10_soak_rndram: >= 36,000 frames (10 min) of mixed play | 51175 frames = 14.2 min; 2 1P games, 7 2P matches (7 finals, 31 round ends), 6 STUDY pauses |
| PASS | v10_soak_zero: >= 36,000 frames (10 min) of mixed play | 52203 frames = 14.5 min; 2 1P games, 7 2P matches (7 finals, 27 round ends), 6 STUDY pauses |

#### Runs

| run | rom md5 | frames | DONE |
|---|---|---|---|
| base_onep_np | d3ec44424b5ac1a4dc77709829f721c9 | 3204 | 0 |
| v10_clearwin | 512b815b9a2944754af3b28e9852d4ed | 29080 | 0 |
| v10_cpuidle | 512b815b9a2944754af3b28e9852d4ed | 6061 | 0 |
| v10_onep | 512b815b9a2944754af3b28e9852d4ed | 3376 | 0 |
| v10_onep_np | 512b815b9a2944754af3b28e9852d4ed | 3188 | 0 |
| v10_shots | 512b815b9a2944754af3b28e9852d4ed | 7428 | 0 |
| v10_soak_rndram | 512b815b9a2944754af3b28e9852d4ed | 51175 | 0 |
| v10_soak_zero | 512b815b9a2944754af3b28e9852d4ed | 52203 | 0 |
| v10_twop | 512b815b9a2944754af3b28e9852d4ed | 9561 | 0 |
| v10_twop_rndram | 512b815b9a2944754af3b28e9852d4ed | 9545 | 0 |
| v10ni_onep | 6724286dc8d0167c52c51184a76bcb85 | 3376 | 0 |
| v10ni_twop | 6724286dc8d0167c52c51184a76bcb85 | 9561 | 0 |
| v9d_clearwin | 0f8f5d89dcf938144d24977d4faf2628 | 29088 | 0 |
| v9d_cpuidle | 0f8f5d89dcf938144d24977d4faf2628 | 6061 | 0 |
| v9d_onep | 0f8f5d89dcf938144d24977d4faf2628 | 3376 | 0 |
| v9d_onep_np | 0f8f5d89dcf938144d24977d4faf2628 | 3188 | 0 |
| v9d_shots | 0f8f5d89dcf938144d24977d4faf2628 | 7424 | 0 |
| v9d_twop | 0f8f5d89dcf938144d24977d4faf2628 | 9565 | 0 |

### Notes

- **v10 and v9 are identical until the first round end.**
  - 1P runs, with and without pauses, are byte-identical every frame, including the stack page.
  - 2P runs first differ on the first round-end frame (`anyPlayerLoses`). After that, the end screen
    does less CPU work (no 64-cell wipe), so the NMI/DMC phase shifts. A few later play frames then
    latch an input one frame apart, which shows up in `$48/$49` scratch and `$5B/$5C/$F5-$F8`.
  - Round winners and finals stay identical. The stock ROM shows the same drift when a START press
    moves by one frame (PR #28 `experiments/studyend/EVIDENCE.txt` section 5).
- **Virus-clear rounds:**
  - Non-final clear rounds stay in top state 4 (STAGE CLEAR box, wait for START). DRSTUDYEND does not
    touch them; v10 == v9 byte for byte through 4 of them.
  - A match won by a clear enters state 7 directly (`$9BB4`), so it **does** go through the
    rewritten final block. v10 keeps both boards there; v9 stamps GAME OVER.
  - The winner's last clear stays drawn as outlined "pops", because the frame froze mid-animation.
    Expected, and documented in the readme.
  - These clear-win cases were not exercised by PR #28, whose finals were all top-outs.
- **Stock base vs v10 (1P)** first differs at frame 9: the title footer sprites in the OAM shadow
  (branding).
  - Gameplay RAM is then identical from leaving the title until a one-frame input-latch shift at
    f1339.
  - That shift is already in v9 (v9 == v10 there) and comes from TE's extra per-frame work.
- **Harness fix found on the way.** Mesen2's `emu.setInput(t, 1)` silently drives controller 1: the
  port is read from the 3rd argument. `te_release_qa.lua` passes `emu.setInput(t, 0, port)` with every
  button explicit. A 2-argument harness never actually drove P2.

## 4. nes-py cross-check

`tools/te_release_kit.py --bps release/drmario_te_v10.bps --expect-md5 512b815b… --prev-title
release/screenshots/native/01_title.png` (dry run): hash gate OK, native 256×240 captures, STUDY not
blanked, the title stamp CHANGED vs the v9 capture → **RELEASE-READY**.

## 5. Existing suites

- `tests/test_te_v10_release.py`: A-F pass.
- `tests/test_title_screen.py`: all pass. The new "1" glyph is additive; the V7/V8 layouts are
  unchanged.
- `tests/test_studyend.py`, `tests/test_study2p.py`, `tests/test_gated_flags.py`,
  `tests/test_studycounts_leak.py`, `tests/test_buildid.py`: all pass.
- `tools/gate/run_cart_gates.sh` (the pre-push gate): all pass.

## Not covered here

- Real hardware for this exact ROM. The same 15 bytes passed on MiSTer in the couch cart on
  2026-10-03.
- Draw rounds (both players lose on the same frame). DRSTUDYEND leaves that path (`R9682_DRAW_GAME`)
  untouched, but it was not exercised.
