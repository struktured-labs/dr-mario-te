# Style Ensemble v1: fitting the bursty pressure model beyond one player

**Date:** 2026-08-05 · **Rule (user, tonight):** one player's fitted pressure model must
never be the only exam — ship gates need a family of styles.

## 0. TL;DR

**Ensemble gate: NOT READY.** Two usable fits exist (struktured 20260804, Red Bracket 2024
Jenny G/Rob Burrito), one confirmed unusable (documented negative below). Two points is enough
to prove the rule ("not just one exam") but not enough to cluster into archetypes or build a
confident multi-model gate — needs more footage, specifically **more independent VS-format
sources**, not more analysis of what's already been pulled. Full inventory, calibration
methodology, both fits, the negative finding, and what's needed next are below.

## 1. Inventory: `/mnt/data/drmario/expert_vods/`

Top-level layout (sizes via `du -sh`):

| dir | size | content | quality tier |
|---|---|---|---|
| `personal-recordings/` | 2.6G | struktured's own off-broadcast phone/camera footage | **ENTIRE SUBDIR `never_publish: true`** per its `manifest.json` + `README_NEVER_PUBLISH.txt` — internal analysis only, confirmed excluded from fitting (see §2) |
| `youtube-drmc-official-2017` .. `-2026`, `-2024-regionals` | 802M–36G each | official DrMC YouTube channel bracket VODs, yt-dlp archived (`.mp4` + `.info.json` + `.description`) | **clean broadcast** — native digital overlay render, not filmed. Two distinct production templates found (see §3): "Championship VS-bracket" (2024) and "Speed-bracket" (2025) |
| `twitch-thedrmc-vods/`, `twitch-thedrmc2-vods/` | 357M / 12K | Twitch VOD archive, mostly small/sparse | not explored this pass (time-boxed) |
| `tetrisinterest-archive/`, `watch_ct2026/` | 756K / 20K | metadata/text only, no video | not applicable |
| `captions/`, `logs/`, `tools/`, `scripts/` | 7.9M / 103M / 393M / 399M | transcripts, cron logs, archiver tooling | infrastructure, not footage |
| `players.json`, `brackets.json` | — | roster + appearance index (114 players, 825 source files scanned) | used to locate named-roster matches (§4) |

**`personal-recordings/` detail** (never_publish, not touched for fitting, listed for
completeness per the inventory ask):
- `20260628_tmg2026_struktured_vs_bidwell.mov` — the flagged hard-mode handheld TMG asset
  (h264 1920x1080, 337s, "CAMERA footage (handheld, off-screen) ... perspective, glare, rolling
  shutter" per its own manifest note). Confirmed future-work-only per task instruction; not
  attempted.
- `20250629_drmc/*.mp4` (4 files) — Samsung/Pixel phone clips, TooManyGames 2025 Oaks PA. One
  explicitly flagged `"CRT-camera moire/checkerboard interference visible — hardest-tier OCR
  material"` (the `20250629_143542.mp4` file — matches the task's own "hardest-tier" callout).
  Another is stored rotated 90° with no display-matrix metadata. Not attempted this pass;
  confirmed correctly out of scope, not silently skipped.

No manifest anywhere flags `never_publish` on the `youtube-drmc-official-*` trees — those are
public YouTube uploads, fair game for fitting.

## 2. Sources picked / dropped

| source | format | picked? | reason |
|---|---|---|---|
| `youtube-drmc-official-2025/20250728_xH8Jyz5cl3I_..._DaveSmithSays_vs_OOKtheLibrarian.mp4` | 2025 "Speed Bracket" | picked, then **DROPPED as a confirmed negative** | see §5 — wrong game mode for this extractor, not a calibration failure |
| `youtube-drmc-official-2024/003_..._Red_Bracket.mp4` (Jenny G vs Rob Burrito segment, t≈350-650s) | 2024 "Championship VS-bracket" | **picked, fit-worthy** | genuine head-to-head VS mode; Rob Burrito is on the named roster; clean digital render |
| `personal-recordings/*` | camera/CRT | not picked | never_publish (§1); also the flagged hardest-tier/handheld cases per task instruction |
| Everything else in `youtube-drmc-official-*` (~9 years of brackets) | mixed | not picked (time-boxed) | 1-3 sources was the ask; see §7 for what to pull next and why |

## 3. Calibration

Both new sources needed fresh geometry + color thresholds — reused film_review_20260804's
vision.py **method** (band-edge scanning for grid geometry, patch-fraction color classification,
dark-fraction virus/pill split), NOT its numbers, which don't transfer (both broadcast sources
render at a different resolution/style than a direct NES-composite capture, with a more
saturated-but-still-source-specific palette).

**`vision_speed2025.py`** (2025 Speed-bracket template — vector-art bottle graphics, purple
checkerboard bg, webcam PIPs): geometry found via full-RGB vertical/horizontal scans through
known-empty and known-border regions (not just a single cyan-mask pass — an early pass missed a
thick purple outer border layer beyond the cyan trim line and put y0 ~30px too high; caught by
re-scanning with the full RGB channel, not just cyan). Verified via ASCII-vs-frame comparison on
3 frames (t=60s, t=400s, t=800s of the DaveSmithSays/OOKtheLibrarian VOD) — board silhouettes
matched the visible stack shapes in each source frame. **This calibration is SOUND** — see §5 for
why the source using it still got dropped (a data problem, not a vision problem).

**`vision_champ2024.py`** (2024 Championship VS-bracket template — 4-way-split screen, clean
digital render, VIR/pill-preview/SPD header per player): geometry found the same way; the exact
video+timestamp was located by pixel-diff matching the archived reference frame
`captions/hud_frame_2024_Red_Championship.png` against every extracted 1fps frame of the Red
Bracket VOD (best match at t=500s, mean abs pixel diff 6.05/255 — consistent with one frame of
normal gameplay motion between adjacent seconds, confirming this is the right video and
timestamp). Verified via ASCII-vs-frame comparison at t=500s — board shapes (dense bottom 2/3,
near-full bottom row) matched the reference image. **LOWER CONFIDENCE than the Speed-2025
calibration on the exact top-row (y0) placement** — no distinct top border color was found by
scanning (the region was already solid black at the top of the scanned range), so y0 was set by
back-computing from the confirmed bottom border and an assumed near-square cell aspect, not an
independently-confirmed top edge. Flagged, not hidden; the resulting board silhouettes still
looked structurally correct on manual review (§4), so this is graded "usable, not
gold-standard," not "defeated."

No source was dropped for calibration reasons this pass — both templates classified sensibly.

## 4. Fits

### struktured (20260804, reference — already shipped, included for the comparison table)

n_matches=4, n_volleys=**61**, n_clears=188. Not low-confidence (≥20 volleys).

### Red Bracket 2024 — Jenny G vs Rob Burrito (pooled both sides, one ~300s window)

Window t=350-650s of `003_..._Red_Bracket.mp4`, located via the reference-frame pixel match
(§3). **Rob Burrito is on the named DrMC roster** (`players.json` "Rob Burrito", 2024 DrMC
Championship TORG Columbus, seed 17) — confirmed in-frame via the HUD nameplate. n_volleys=**18**
— **LOW-CONFIDENCE** (below the n=20 threshold agreed for this pass). n_clears=86. A cleanup
pass excluded 1 volley + 4 clears with implausible sizes (>20 cells in one second — real Dr Mario
events don't do that; these read as scene-adjacent artifacts, not real board state) before
fitting — see `fit_ensemble_source.py` (new file, does NOT modify `bursty_model.py`; the raw
extractor is correct, this is source-specific data cleaning, documented inline).

**Not fit per-player.** Both sides are pooled into one model, matching `bursty_model.py`'s own
design (`from_footage`'s docstring: "pooled n_cells per volley (all sides/matches)") and
struktured's own precedent fit (also both-sides-pooled). Isolating "Rob Burrito's individual
firing behavior" specifically would need re-deriving the P(volley|clear) conditioning by sender
identity, which the current pooled design doesn't cleanly expose — not attempted this pass, noted
as a real gap against the "per-PLAYER where possible" ask, not silently skipped.

### Side-by-side parameter table

| metric | struktured (n=61 volleys) | Red Bracket 2024, JennyG/RobBurrito (n=18, LOW-CONF) |
|---|---|---|
| n_matches | 4 | 1 |
| n_volleys | 61 | 18 |
| n_clears | 188 | 86 |
| volley_size_mean | 2.54 [2.33, 2.79] | 2.44 [2.06, 2.89] |
| inter_volley_gap_mean_s | 22.70 [17.19, 28.55] | 26.44 [15.81, 38.38] |
| P(volley≤5s \| clear 4-6 cells) | 32.1% (n=156, hits=50) | 21.9% (n=73, hits=16) |
| P(volley≤5s \| clear 7-10 cells) | 74.1% (n=27, hits=20) | 25.0% (n=12, hits=3) |
| P(volley≤5s \| clear 11+ cells) | 40.0% (n=5) | 0.0% (n=1) — **uninformative, n=1** |

Files: `results/style_ensemble_v1/red_bracket_2024_jennyg_robburrito_fit.json` (full fit incl.
`fit_summary()`), struktured's own fit reproduces from `bursty_model.fit_struktured_20260804()`
unchanged (not re-saved here — already committed at `results/bursty_n120_wt0_ws20.json`'s
provenance and `BURSTY_V1_RESULTS.md`).

## 5. Negative finding: DaveSmithSays vs OOKtheLibrarian (2025 Speed Bracket) — DO NOT USE

Calibration (`vision_speed2025.py`) was sound (§3) and produced structurally plausible ASCII
boards. The FIT was garbage — 449 raw "clears" in a 24-minute VOD, several "volleys" of 24-49
cells (a real volley tops out around 6 cells per struktured's own fit). Root-caused by direct
frame inspection, not assumed:

1. **Format mismatch.** The "Speed Bracket" is a solo race through sequential levels (this VOD's
   title bar literally says "Round 1 Levels 6-9") — NOT the continuous single-level 2P VS match
   `extract_clears`/`extract_volleys` were built and validated against. Confirmed on-frame: at
   t=105s davesmithsays' board shows a "STAGE CLEAR / TRY NEXT" screen (level 6→7 transition);
   at t=106s the board is refilled with 32 fresh viruses. That single-second 0→32 jump gets
   misdetected as a giant volley/clear. This is a genuine game-mode incompatibility, not noise.
2. **Even after excluding those large outliers (>20 cells), n_clears stayed at 433/1482s** — still
   absurd (~1 "clear" every 3.4 seconds, sustained for 24 minutes). Manually inspected several
   `cells_removed==4` events frame-by-frame (e.g. t=73s): the "removed" cells were spatially
   SCATTERED (a vertical pair at the top of the board, an unrelated single cell at the far right,
   another unrelated single cell mid-board) — not a contiguous same-color match-4, which is what a
   real Dr Mario clear always is. This is classification jitter (falling-pill boundary artifacts +
   isolated frame-to-frame noise), not gameplay signal.

**Contrast with the Red Bracket 2024 fit**, which used the SAME general calibration methodology:
there, a spot-checked `cells_removed==4` event (t=376s) showed a genuine spatially-coherent
3-in-a-row same-color loss, and only 5 of ~90+19 raw events needed excluding as outliers — a
5% cleanup rate vs. this source's near-total corruption. The difference is the game mode, not the
vision pipeline: **this extractor needs a continuous single-level 2P VS match to work.** Any
future Speed-bracket source needs either (a) a level-transition detector to gate out resets, or
(b) is simply out of scope for this fitting method. Recommend (b) — pull more Championship/VS-
format sources instead, not more Speed-bracket ones.

File kept for the record at `results/style_ensemble_v1/dsms_vs_ook_2025speed_fit_NEGATIVE_DO_NOT_USE.json`
— filename makes the status explicit; not wired into anything downstream.

## 6. Archetype read

**Cannot honestly cluster on n=2.** Two pooled per-match fits is enough to prove struktured's
session is not the only exam (the rule this task exists to satisfy), and enough to say the two
fits *look directionally different* — Red Bracket 2024's volley size is close to struktured's
(2.44 vs 2.54, consistent typical volley scale) but its P(volley|clear) firing rates run
noticeably lower across both real bins (21.9% vs 32.1% at 4-6 cells; 25.0% vs 74.1% at 7-10 cells,
though n=12 there is thin) — i.e. this match's players return pressure less reflexively than
struktured's session did. That is a real, reportable pairwise difference. It is **not** a
"rusher/chainer/staller" archetype grid — that requires a player-level style corpus (not
match-pooled) across enough independent matches to see clusters rather than one pairwise
contrast. Forcing three archetypes out of two match-level data points would be exactly the kind
of fabricated ensemble the task's honesty rules warn against; this report doesn't do that.

## 7. Ensemble-gate recipe (for when there's enough data)

Not ready to specify a real multi-model gate on n=2. What it needs to look like once there is
enough data, and the concrete next step to get there:

- **Gate structure (proposed, unvalidated):** a ship candidate should be evaluated against the
  FULL set of independent fits (struktured + every other fit-worthy source), not just the
  best/worst one — e.g. require a non-regression (or an improvement) on bad-end rate under EACH
  fitted model individually, not just on average across them, so a candidate can't overfit to one
  player's specific timing profile. Low-confidence fits (n<20 volleys) should be reported
  alongside the gate result but not block on their own until re-confirmed with more footage.
- **Next step to get there:** pull 2-4 MORE Championship/VS-format sources (not Speed-bracket —
  see §5), reusing `vision_champ2024.py`'s calibration wherever the production template repeats
  (2024 Championship videos share one template across brackets per the reference frames reviewed
  — Immunity Pool used the same general style as Red Bracket). Prioritize matches featuring named
  roster players still unattributed this pass: davesmithsays (14 tracked appearances, all
  unfortunately in the incompatible Speed-bracket format — would need the SAME format-mismatch
  problem solved, so lower priority until §5's caveat is addressed), Jarsdad and Chris Bidwell
  (both listed in the SAME 2024 Championship bracket description as Rob Burrito — likely
  extractable from Championship-format brackets already on disk, reusing this pass's exact
  calibration, no new vision work needed).

## Provenance

- Vision modules: `vision_speed2025.py`, `vision_champ2024.py` (new, source-specific geometry +
  thresholds; classification method matches `film_review_20260804/vision.py`).
- Fitting: `fit_ensemble_source.py` (new; event-size-capped fit, does not modify `bursty_model.py`).
- Fits: `results/style_ensemble_v1/red_bracket_2024_jennyg_robburrito_fit.json` (usable),
  `results/style_ensemble_v1/dsms_vs_ook_2025speed_fit_NEGATIVE_DO_NOT_USE.json` (documented
  negative, not for use).
- Reference frames used for calibration/localization: `captions/hud_frame_2024_Red_Championship.png`,
  `captions/hud_frame_2024_Immunity_Pool.png`, `captions/hud_frame_2025_Gold_Jan_Final.png`,
  `captions/hud_frame_2025_Silver_Jun_Final.png` (all pre-existing on disk, not generated this
  pass — used to identify broadcast templates and localize the Red Bracket timestamp).
- Roster cross-reference: `/mnt/data/drmario/expert_vods/players.json`.
- struktured's reference fit: `bursty_model.fit_struktured_20260804()` (unchanged), see
  `BURSTY_V1_RESULTS.md`.
