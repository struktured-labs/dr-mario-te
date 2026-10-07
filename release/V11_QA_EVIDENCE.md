# TE v11 — QA evidence

All checks ran on the shipping bytes: the ROM that `release/drmario_te_v11.ips` produces from the
clean base, md5 `4ce1622aa27e91e54694099b6f9df163`. Controls run on the same scripts:
- TE v10 (`512b815b`), which v11 extends; its 1P game over is stock;
- the published v9 (`0f8f5d89`), the 2P sign/wipe positive control;
- the stock base.

## 1. What the stock 1P game over does (measured, Mesen, v10)

| frame (from top state 7) | event |
|---|---|
| top-out | `action_sendPill` cannot place the new capsule; `confirmPlacement` writes it into the field anyway (so the "falling capsule's final state" is field RAM) and sets the fail flag; top state 4 → 5 → 7 |
| +1 … +192 | waits 64 + 128 frames; board on screen (`fieldKept`, `ntEqField`), no sprites in the bottle |
| +193 | one frame: `$95CE` fills `$0400-$05FF` with `$FF`, `renderGameOver` writes the GAME OVER box into field rows 2-8 of both fields, both status bytes `$0F` |
| +194 … +209 | the NMI redraws the bottle row by row |
| +192 → | START loop `$9607` (first exec measured at +192); START sprite blinks at Y `$C3` X 109-141, **inside the bottle over the bottom board row** |
| START | 6 frames later: both fields `$FE`, top state 1 (options), high-score check |

A START pressed during the waits (+100) is ignored, in stock and in v11 alike.

## 2. Static gates (`build_te_v11.py`, `te_release_gates.py`, `tests/test_te_v11_release.py`)

| check | result |
|---|---|
| build reproduces | v10 rebuilt first (`512b815b`, v10 gates re-run), then v11 md5 `4ce1622a…` pinned |
| delta vs v10 | exactly 10 bytes: PRG `$95D5 $95D6 $95DC $95E8 $9615 $9616` + 4 bytes of one stamp tile |
| writes land on stock code | all 6 sites equal the base ROM |
| START Y pair | `$D4D2/$D4D3` = `D8 D3` stock; 2P entry `$D3` == `$A105[2]`; `$A105` itself untouched |
| reachability | the only branch/jump into `$95C9-$9606` is the nbPlayers≠2 `BNE` at `$959A` (whole-PRG superset decode; the one other hit is an `LDA #$10` operand) |
| patch shape | `start_y=None` = the 4 board bytes; refuses a ROM without the 2P DRSTUDYEND and a second application |
| KIL / garble sites vanilla | `$BC26 $BE56 $9FF8 $A371 $C0A9 $C0EF $CF00` **+ `$A01A-$A057`** (the rest of the `$9FF8` cutscene table, newly gated) == base |
| printing-table walk | 0 changed bytes inside any `RB6C2_PRINT` read-set; the published v6 still fails |
| IPS | 94 records, 0 unchanged base bytes carried, header never touched |

## 3. Patch round-trips (base `/home/struktured/projects/dr-mario-canonical-wt/drmario.nes`, md5 `d3ec4442…`)

| applier | IPS | BPS |
|---|---|---|
| Floating IPS (built from source, `ff216a7`) | `4ce1622a…` | `4ce1622a…` |
| freshly written IPS applier (`_evidence_v11/roundtrip/my_ips.py`, shares no code with the repo) | `4ce1622a…` (94 records) | n/a |
| `tools/ipsdiff.py`, `tools/te_release_kit.py`, `make_bps.py` decoders | `4ce1622a…` | `4ce1622a…` |
| No-Intro NES 2.0-headered base | header kept, body == v11 (`8891cfc2…`) | refused (expects `B1F7E3E9`) |

## 4. py65 (the real `playerLoses_endScreen`, NMI wait stubbed)

- **1P:** v10 and v11 both reach the START loop after 192 frames.
  - v10 wipes both fields and stamps GAME OVER (1,136 field writes).
  - v11 writes 0 field bytes before START, then the stock `$FE` fill.
  - At the loop, RAM differs only in the fields and `$00/$01`; after START it is identical.
  - START prompt Y: `$C3` in v10, `$D8` in v11.
- **2P match final:** P1 and P2 winning, blink and no-blink frame. v10 and v11 have an identical write
  trace and RAM, and START Y is `$D3`.

## 5. Mesen 2 full-game QA (`tools/te_release_qa/`)

Run: `tools/te_release_qa/run_release_qa.sh <v11.nes> <v10.nes> <v9.nes> <base.nes>`, about 20 min.
The script honours `dr_mario_rl/tmp/te1p/PAUSE` and the shared `PAUSE_ALL` between runs.

New scenarios:
- **`go1p`:** five 1P games, at (level, speed) (0,LOW) (5,MED) (12,HI) (20,MED) (9,HI).
  - Each is topped out, then the end screen is watched frame by frame for 600 frames: field RAM, the
    drawn bottle, sprites over the bottle, and when the START loop starts.
  - Three games also press START at +100.
  - Then START, and every next game must start clean.
- **`clear1p`:** the solver clears level 0, then STAGE CLEAR, START and level 1, then a top-out and game
  over.
- `onep`, `shots` and `soak` now check every 1P game over the same way.

### Result

**TE v11 Mesen QA summary — 95/95 PASS**

| result | check | detail |
|---|---|---|
| PASS | base_onep_np: completed, no freeze | DONE=0 frames=3699 ramExec=0 maxClockStall=2 [] |
| PASS | v10_clear1p: completed, no freeze | DONE=0 frames=12550 ramExec=0 maxClockStall=2 [] |
| PASS | v10_clearwin: completed, no freeze | DONE=0 frames=29080 ramExec=0 maxClockStall=2 [] |
| PASS | v10_cpuidle: completed, no freeze | DONE=0 frames=6061 ramExec=0 maxClockStall=2 [] |
| PASS | v10_go1p: completed, no freeze | DONE=0 frames=8937 ramExec=0 maxClockStall=2 [] |
| PASS | v10_onep: completed, no freeze | DONE=0 frames=3818 ramExec=0 maxClockStall=2 [] |
| PASS | v10_onep_np: completed, no freeze | DONE=0 frames=3699 ramExec=0 maxClockStall=2 [] |
| PASS | v10_twop: completed, no freeze | DONE=0 frames=9561 ramExec=0 maxClockStall=2 [] |
| PASS | v11_clear1p: completed, no freeze | DONE=0 frames=12550 ramExec=0 maxClockStall=2 [] |
| PASS | v11_clearwin: completed, no freeze | DONE=0 frames=29080 ramExec=0 maxClockStall=2 [] |
| PASS | v11_cpuidle: completed, no freeze | DONE=0 frames=6061 ramExec=0 maxClockStall=2 [] |
| PASS | v11_go1p: completed, no freeze | DONE=0 frames=8937 ramExec=0 maxClockStall=2 [] |
| PASS | v11_go1p_rndram: completed, no freeze | DONE=0 frames=9253 ramExec=0 maxClockStall=1 [] |
| PASS | v11_onep: completed, no freeze | DONE=0 frames=3818 ramExec=0 maxClockStall=2 [] |
| PASS | v11_onep_np: completed, no freeze | DONE=0 frames=3699 ramExec=0 maxClockStall=2 [] |
| PASS | v11_shots: completed, no freeze | DONE=0 frames=7413 ramExec=0 maxClockStall=2 [] |
| PASS | v11_soak_rndram: completed, no freeze | DONE=0 frames=40359 ramExec=0 maxClockStall=1 [] |
| PASS | v11_soak_zero: completed, no freeze | DONE=0 frames=52198 ramExec=0 maxClockStall=2 [] |
| PASS | v11_twop: completed, no freeze | DONE=0 frames=9561 ramExec=0 maxClockStall=2 [] |
| PASS | v11_twop_rndram: completed, no freeze | DONE=0 frames=9545 ramExec=0 maxClockStall=1 [] |
| PASS | v11ni_go1p: completed, no freeze | DONE=0 frames=8937 ramExec=0 maxClockStall=2 [] |
| PASS | v11ni_twop: completed, no freeze | DONE=0 frames=9561 ramExec=0 maxClockStall=2 [] |
| PASS | v9d_twop: completed, no freeze | DONE=0 frames=9565 ramExec=0 maxClockStall=2 [] |
| PASS | v11_clearwin: every end screen keeps both final boards, no sign | 4 end screens (2 match finals); signSprites=0 wipes=0 gameOverFills=0 |
| PASS | v11_clearwin: drawn bottles == board RAM at +150 | 4 end screens |
| PASS | v11_clearwin: next match starts clean | clean=1 dirty=0 |
| PASS | v11_cpuidle: every end screen keeps both final boards, no sign | 3 end screens (0 match finals); signSprites=0 wipes=0 gameOverFills=0 |
| PASS | v11_cpuidle: drawn bottles == board RAM at +150 | 3 end screens |
| PASS | v11_shots: every end screen keeps both final boards, no sign | 4 end screens (1 match finals); signSprites=0 wipes=0 gameOverFills=0 |
| PASS | v11_shots: drawn bottles == board RAM at +150 | 4 end screens |
| PASS | v11_soak_rndram: every end screen keeps both final boards, no sign | 22 end screens (6 match finals); signSprites=0 wipes=0 gameOverFills=0 |
| PASS | v11_soak_rndram: drawn bottles == board RAM at +150 | 22 end screens |
| PASS | v11_soak_rndram: next match starts clean | clean=5 dirty=0 |
| PASS | v11_soak_zero: every end screen keeps both final boards, no sign | 23 end screens (7 match finals); signSprites=0 wipes=0 gameOverFills=0 |
| PASS | v11_soak_zero: drawn bottles == board RAM at +150 | 23 end screens |
| PASS | v11_soak_zero: next match starts clean | clean=6 dirty=0 |
| PASS | v11_twop: every end screen keeps both final boards, no sign | 8 end screens (2 match finals); signSprites=0 wipes=0 gameOverFills=0 |
| PASS | v11_twop: drawn bottles == board RAM at +150 | 8 end screens |
| PASS | v11_twop: next match starts clean | clean=1 dirty=0 |
| PASS | v11_twop_rndram: every end screen keeps both final boards, no sign | 8 end screens (2 match finals); signSprites=0 wipes=0 gameOverFills=0 |
| PASS | v11_twop_rndram: drawn bottles == board RAM at +150 | 8 end screens |
| PASS | v11_twop_rndram: next match starts clean | clean=1 dirty=0 |
| PASS | v11ni_twop: every end screen keeps both final boards, no sign | 8 end screens (2 match finals); signSprites=0 wipes=0 gameOverFills=0 |
| PASS | v11ni_twop: drawn bottles == board RAM at +150 | 8 end screens |
| PASS | v11ni_twop: next match starts clean | clean=1 dirty=0 |
| PASS | v11_clearwin: virus-clear round ends keep the loser's board, no sign | 6 clear-win round ends |
| PASS | v11_soak_rndram: virus-clear round ends keep the loser's board, no sign | 4 clear-win round ends |
| PASS | v11_soak_zero: virus-clear round ends keep the loser's board, no sign | 8 clear-win round ends |
| PASS | v9d_twop (positive control, published v9): sign/wipe/GAME OVER detected | signSprites=16 wipes=16 gameOverFills=2 |
| PASS | v11_onep: STUDY pause (text, per-player previews, frozen board, clean resume) | 2 pauses (2 1P / 0 2P), 2 resumes |
| PASS | v11_shots: STUDY pause (text, per-player previews, frozen board, clean resume) | 2 pauses (1 1P / 1 2P), 2 resumes |
| PASS | v11_soak_rndram: STUDY pause (text, per-player previews, frozen board, clean resume) | 5 pauses (0 1P / 5 2P), 5 resumes |
| PASS | v11_soak_zero: STUDY pause (text, per-player previews, frozen board, clean resume) | 6 pauses (1 1P / 5 2P), 6 resumes |
| PASS | v11_twop: STUDY pause (text, per-player previews, frozen board, clean resume) | 2 pauses (0 1P / 2 2P), 2 resumes |
| PASS | v11_twop_rndram: STUDY pause (text, per-player previews, frozen board, clean resume) | 2 pauses (0 1P / 2 2P), 2 resumes |
| PASS | v11ni_twop: STUDY pause (text, per-player previews, frozen board, clean resume) | 2 pauses (0 1P / 2 2P), 2 resumes |
| PASS | v11_clear1p: 1P game over keeps the final board until START, then stock | 1 game overs (level,speed) [(1, 0)]; held to +600; START loop from +192; 0 bottle sprites; fields $FE + options after START [] |
| PASS | v11_clear1p: every 1P game starts clean (after a held game over too) | clean=1 dirty=0 |
| PASS | v11_go1p: 1P game over keeps the final board until START, then stock | 5 game overs (level,speed) [(0, 0), (5, 1), (9, 2), (12, 2), (20, 1)]; held to +600; START loop from +192; 0 bottle sprites; fields $FE + options after START [] |
| PASS | v11_go1p: START during the stock 192-frame wait is ignored (as stock) | 3 game overs with START pressed at +100 |
| PASS | v11_go1p: every 1P game starts clean (after a held game over too) | clean=6 dirty=0 |
| PASS | v11_go1p_rndram: 1P game over keeps the final board until START, then stock | 5 game overs (level,speed) [(0, 0), (5, 1), (9, 2), (12, 2), (20, 1)]; held to +600; START loop from +192; 0 bottle sprites; fields $FE + options after START [] |
| PASS | v11_go1p_rndram: START during the stock 192-frame wait is ignored (as stock) | 3 game overs with START pressed at +100 |
| PASS | v11_go1p_rndram: every 1P game starts clean (after a held game over too) | clean=6 dirty=0 |
| PASS | v11_onep: 1P game over keeps the final board until START, then stock | 2 game overs (level,speed) [(0, 1), (5, 1)]; held to +400; START loop from +192; 0 bottle sprites; fields $FE + options after START [] |
| PASS | v11_onep: every 1P game starts clean (after a held game over too) | clean=2 dirty=0 |
| PASS | v11_onep_np: 1P game over keeps the final board until START, then stock | 2 game overs (level,speed) [(0, 1), (5, 1)]; held to +400; START loop from +192; 0 bottle sprites; fields $FE + options after START [] |
| PASS | v11_onep_np: every 1P game starts clean (after a held game over too) | clean=2 dirty=0 |
| PASS | v11_shots: 1P game over keeps the final board until START, then stock | 1 game overs (level,speed) [(10, 1)]; held to +400; START loop from +192; 0 bottle sprites; fields $FE + options after START [] |
| PASS | v11_shots: every 1P game starts clean (after a held game over too) | clean=1 dirty=0 |
| PASS | v11_soak_rndram: 1P game over keeps the final board until START, then stock | 2 game overs (level,speed) [(1, 1), (4, 1)]; held to +400; START loop from +192; 0 bottle sprites; fields $FE + options after START [] |
| PASS | v11_soak_rndram: every 1P game starts clean (after a held game over too) | clean=2 dirty=0 |
| PASS | v11_soak_zero: 1P game over keeps the final board until START, then stock | 2 game overs (level,speed) [(6, 1), (10, 1)]; held to +400; START loop from +192; 0 bottle sprites; fields $FE + options after START [] |
| PASS | v11_soak_zero: every 1P game starts clean (after a held game over too) | clean=2 dirty=0 |
| PASS | v11ni_go1p: 1P game over keeps the final board until START, then stock | 5 game overs (level,speed) [(0, 0), (5, 1), (9, 2), (12, 2), (20, 1)]; held to +600; START loop from +192; 0 bottle sprites; fields $FE + options after START [] |
| PASS | v11ni_go1p: START during the stock 192-frame wait is ignored (as stock) | 3 game overs with START pressed at +100 |
| PASS | v11ni_go1p: every 1P game starts clean (after a held game over too) | clean=6 dirty=0 |
| PASS | v10_clear1p (positive control, v10 = stock 1P): wipe + GAME OVER box + START over the bottle detected | 1 game overs: wiped at +193, box, 5 START sprites inside the bottle |
| PASS | v10_go1p (positive control, v10 = stock 1P): wipe + GAME OVER box + START over the bottle detected | 5 game overs: wiped at +193, box, 5 START sprites inside the bottle |
| PASS | v10_onep (positive control, v10 = stock 1P): wipe + GAME OVER box + START over the bottle detected | 2 game overs: wiped at +193, box, 5 START sprites inside the bottle |
| PASS | v10_onep_np (positive control, v10 = stock 1P): wipe + GAME OVER box + START over the bottle detected | 2 game overs: wiped at +193, box, 5 START sprites inside the bottle |
| PASS | v11_shots: the 1P START prompt is drawn below the bottle (Y=$D8) | OAM [(216, '0D', 109), (216, '0F', 117), (216, '0B', 125), (216, '14', 133), (216, '0F', 141)] |
| PASS | v11_clear1p: 1P stage clears (STAGE CLEAR, START, next level) still work | 1 clears, next levels [('clr1', 1)] |
| PASS | 2P v11_twop == v10 on every frame (full RAM) | 9561 frames; 8 end screens |
| PASS | 2P v11_cpuidle == v10 on every frame (full RAM) | 6061 frames; 3 end screens |
| PASS | 2P v11_clearwin == v10 on every frame (full RAM) | 29080 frames; 4 end screens |
| PASS | 1P v11_go1p == v10 except the boards during each held game over | 8937 frames, mode sequence identical; RAM outside the fields $0400-$05FF, $00/$01 and the 5 START-letter OAM Y bytes identical on every frame; full-RAM differences only inside the 5 holds [+193, START) (2053 frames) and identical again from START |
| PASS | 1P v11_onep == v10 except the boards during each held game over | 3818 frames, mode sequence identical; RAM outside the fields $0400-$05FF, $00/$01 and the 5 START-letter OAM Y bytes identical on every frame; full-RAM differences only inside the 2 holds [+193, START) (420 frames) and identical again from START |
| PASS | 1P v11_onep_np == v10 except the boards during each held game over | 3699 frames, mode sequence identical; RAM outside the fields $0400-$05FF, $00/$01 and the 5 START-letter OAM Y bytes identical on every frame; full-RAM differences only inside the 2 holds [+193, START) (421 frames) and identical again from START |
| PASS | 1P v11_clear1p == v10 except the boards during each held game over | 12550 frames, mode sequence identical; RAM outside the fields $0400-$05FF, $00/$01 and the 5 START-letter OAM Y bytes identical on every frame; full-RAM differences only inside the 1 holds [+193, START) (410 frames) and identical again from START |
| PASS | No-Intro NES 2.0 header (v11ni_twop) == classic header on every frame | 9561 frames |
| PASS | No-Intro NES 2.0 header (v11ni_go1p) == classic header on every frame | 8937 frames |
| PASS | stock base vs v11 (1P, informational) | first RAM difference f9 (title: footer sprites in the OAM shadow); mode sequence identical=True; differing frames by mode {0: 232, 1: 4, 4: 11, 7: 421, 8: 1} |
| PASS | v11_soak_rndram: >= 36,000 frames (10 min) of mixed play | 40359 frames = 11.2 min; 2 1P games (2 held game overs), 6 2P matches (6 finals, 26 round ends), 5 STUDY pauses |
| PASS | v11_soak_zero: >= 36,000 frames (10 min) of mixed play | 52198 frames = 14.5 min; 2 1P games (2 held game overs), 7 2P matches (7 finals, 31 round ends), 6 STUDY pauses |

### Runs

| run | rom md5 | frames | DONE |
|---|---|---|---|
| base_onep_np | d3ec44424b5ac1a4dc77709829f721c9 | 3699 | 0 |
| v10_clear1p | 512b815b9a2944754af3b28e9852d4ed | 12550 | 0 |
| v10_clearwin | 512b815b9a2944754af3b28e9852d4ed | 29080 | 0 |
| v10_cpuidle | 512b815b9a2944754af3b28e9852d4ed | 6061 | 0 |
| v10_go1p | 512b815b9a2944754af3b28e9852d4ed | 8937 | 0 |
| v10_onep | 512b815b9a2944754af3b28e9852d4ed | 3818 | 0 |
| v10_onep_np | 512b815b9a2944754af3b28e9852d4ed | 3699 | 0 |
| v10_twop | 512b815b9a2944754af3b28e9852d4ed | 9561 | 0 |
| v11_clear1p | 4ce1622aa27e91e54694099b6f9df163 | 12550 | 0 |
| v11_clearwin | 4ce1622aa27e91e54694099b6f9df163 | 29080 | 0 |
| v11_cpuidle | 4ce1622aa27e91e54694099b6f9df163 | 6061 | 0 |
| v11_go1p | 4ce1622aa27e91e54694099b6f9df163 | 8937 | 0 |
| v11_go1p_rndram | 4ce1622aa27e91e54694099b6f9df163 | 9253 | 0 |
| v11_onep | 4ce1622aa27e91e54694099b6f9df163 | 3818 | 0 |
| v11_onep_np | 4ce1622aa27e91e54694099b6f9df163 | 3699 | 0 |
| v11_shots | 4ce1622aa27e91e54694099b6f9df163 | 7413 | 0 |
| v11_soak_rndram | 4ce1622aa27e91e54694099b6f9df163 | 40359 | 0 |
| v11_soak_zero | 4ce1622aa27e91e54694099b6f9df163 | 52198 | 0 |
| v11_twop | 4ce1622aa27e91e54694099b6f9df163 | 9561 | 0 |
| v11_twop_rndram | 4ce1622aa27e91e54694099b6f9df163 | 9545 | 0 |
| v11ni_go1p | 8891cfc2cafcd468f8766e8fc8b977f0 | 8937 | 0 |
| v11ni_twop | 8891cfc2cafcd468f8766e8fc8b977f0 | 9561 | 0 |
| v9d_twop | 0f8f5d89dcf938144d24977d4faf2628 | 9565 | 0 |

### Full-RAM diff during a hold (`_evidence_v11/fullram_v10_vs_v11/`, `QA_FULL` dumps, go1p game 1)

Every non-stack RAM byte that differs between v10 and v11 from f1960 to f2000 and from f2370 to
f2400:
- the two fields (122 cells, from +193);
- `$01` (one frame, the stock fill's pointer);
- `$0200/$0204/$0208/$020C/$0210`, the OAM-shadow Y of the 5 START letters, on prompt frames only.

From the START frame (f2384) on, there are 0 differences. The QA's "no-board" hash excludes exactly
these bytes, and it is identical on every frame of every 1P comparison.

## 6. nes-py cross-check

`tools/te_release_kit.py --bps release/drmario_te_v11.bps --expect-md5 4ce1622a… --prev-title
release/screenshots/v10/01_title.png` (dry run): hash gate OK, native 256×240 captures, VS CPU arming OK,
STUDY not blanked, the stamp CHANGED vs v10 → **RELEASE-READY**.

## 7. Existing suites

- `tests/test_te_v11_release.py` A-G and `tests/test_te_v10_release.py` A-F: all pass. v10 still
  reproduces `512b815b`.
- `tests/test_title_screen.py` (10), `tests/test_studyend.py` (A-G, couch emitter), `tests/test_study2p.py`,
  `tests/test_gated_flags.py`, `tests/test_studycounts_leak.py`, `tests/test_buildid.py`: all pass.

## Not covered here

- Real hardware for this ROM. The 6 new bytes have run only in emulation; every 2P byte is v10's.
- Draw rounds (both players top out on the same frame). They are 2P-only and untouched.
