# Style Ensemble v1: fitting the bursty pressure model beyond one player

**Date:** 2026-08-05 · **Rule (user, tonight):** one player's fitted pressure model must
never be the only exam — ship gates need a family of styles.

## 0. TL;DR

**Ensemble gate: NOT READY, but the picture is much wider now.** Five match-level fits exist
(struktured, plus four new named-roster matches), one confirmed unusable (documented negative,
unchanged from pass 1). All five fits remain **match-pooled** (both players' events summed per
match, matching `bursty_model.py`'s own design and struktured's own precedent) — this pass did
NOT add per-player separation, so what follows are five match-level pressure profiles, not five
independent player profiles. That's real progress (5 points show real spread — inter-volley gaps
range 16.4s to 31.5s, P(volley|clear 7-10) ranges 0% to 74%) but still not a clean archetype
clustering; see §6.

**Correction to the prior report to team-lead:** I incorrectly said Jarsdad and Chris Bidwell
were in the same Red Bracket as Rob Burrito. They are not — checked against every 2024
Championship bracket's `.description` file this pass (not assumed): **Jarsdad (seed 35) and
Chris Bidwell (seed 19, playing "as Robert Smith") are both in the White Bracket**
(video `009_..._White_Bracket.mp4`), a *different* video from Rob Burrito's Red Bracket. Also
found **davesmithsays (seed 44) in the Green Bracket** (video `006_..._Green_Bracket.mp4`) — a
genuine VS-Championship-format appearance, distinct from his Speed-bracket footage (§5 of pass 1).
§7 of the pass-1 report repeated this error in its "next step" recommendation — superseded by §7
below.

## 1-3. Inventory / source selection / calibration method — unchanged from pass 1

See the original sections (not reproduced here) for the `/mnt/data/drmario/expert_vods/`
inventory, the never-publish confirmation on `personal-recordings/`, and the calibration
methodology (band-edge scan + patch-fraction color + dark-fraction virus split, reusing
`film_review_20260804/vision.py`'s method with source-specific geometry/thresholds).

**New this pass:** the 2024 Championship template is a **4-way split screen** (2 concurrent
1v1 matches stacked top/bottom), confirmed by directly viewing extracted frames — pass 1's
`vision_champ2024.py` only had geometry for the TOP pair (`P1`/`P2`). Added `P1B`/`P2B` for the
BOTTOM pair by the same band-edge method: `P1B=(x0=689, y0=559, W=32.75, H=31.5)`,
`P2B=(x0=969, y0=559, W=32.75, H=31.5)` — same W/H as the top pair (found by scanning for the
bottom pair's own top border, ~y=555-559, right below the top pair's bottom border at ~y=524; a
tight ~30px gap between the two match rows). Not yet folded back into `vision_champ2024.py` as a
committed change — the ad-hoc dict is inline in the fit scripts below; flagged as cleanup debt,
not hidden.

## 4. Player attribution — confidence stated separately from fit confidence

All four new identifications this pass are **HIGH attribution confidence**: each was confirmed by
an exact on-screen nameplate + seed number match against the bracket's own `.description` roster
file (not inferred from timing or guessed from partial text):

| player | video | seed | on-screen nameplate | roster line (`.description`) |
|---|---|---|---|---|
| Jarsdad | White Bracket | 35 | "(35) Jarsdad" | "35 - Jarsdad" |
| Chris Bidwell | White Bracket | 19 | "(19) Robert Smith" | "19 - Chris Bidwell (as Robert Smith)" — the description itself cross-references the on-screen alias, removing any doubt |
| davesmithsays | Green Bracket | 44 | "(44) Davesmithsays" | "44 - davesmithsays" |
| Rob Burrito (pass 1, restated) | Red Bracket | 17 | "(17) Rob Burrito" | "17 - Rob Burrito" |

No UNATTRIBUTED cases this pass — every match window used had a clean nameplate confirmation.
(The opponents in each match — Missy, dmhero, Larvae, Jenny G — are not on the named roster this
task tracks; their events are still in the pooled fit, per the pooling caveat above, but no
dossier is being written for them.)

## 5. Fits (all match-pooled; see §4 for attribution confidence, separate from fit confidence below)

| match | video, window | n_volleys | fit confidence | n_clears | volley_size_mean | inter_volley_gap_mean_s | P(vol\|clear 4-6) | P(vol\|clear 7-10) |
|---|---|---|---|---|---|---|---|---|
| struktured 20260804 (pass 1) | film_review, 4 matches pooled | 61 | **OK** (≥20) | 188 | 2.54 [2.33,2.79] | 22.70 [17.19,28.55] | 32.1% (n=156) | 74.1% (n=27) |
| Red Bracket: Jenny G / **Rob Burrito** (pass 1) | Red_Bracket.mp4, t=350-650 | 18 | LOW-CONF (<20) | 86 | 2.44 [2.06,2.89] | 26.44 [15.81,38.38] | 21.9% (n=73) | 25.0% (n=12) |
| White Bracket: **Jarsdad** / dmhero | White_Bracket.mp4, t=200-480, bottom pair | **26** | **OK** (≥20) | 92 | 2.77 [2.15,3.73] | 16.42 [12.25,21.04] | 35.4% (n=82) | 60.0% (n=10) |
| White Bracket: **Chris Bidwell** ("Robert Smith") / Missy | White_Bracket.mp4, t=200-480, top pair | 13 | LOW-CONF (<20) | 62 | 2.31 [2.00,2.69] | 31.55 [17.45,46.55] | 33.3% (n=57) | 33.3% (n=3, too small to read) |
| Green Bracket: Larvae / **davesmithsays** | Green_Bracket.mp4, t=1330-1750, bottom pair | **2** | **UNINFORMATIVE** (n=2) | 110 | 5.5 [4,7] (n=2, not meaningful) | 214s (n=1, not meaningful) | 1.0% (n=97) | 0% (n=9) |

Each fit's raw JSON is at `results/style_ensemble_v1/{red_bracket_2024_jennyg_robburrito,
white_bracket_2024_jarsdad_dmhero, white_bracket_2024_bidwell_missy,
green_bracket_2024_larvae_davesmithsays}_fit.json`. Same cleanup as pass 1: events >20 cells
(scene-artifact-sized) excluded before fitting; every fit dropped a small, healthy fraction (0-6
events), nothing like the DaveSmithSays-Speed-bracket near-total corruption from §5 of pass 1.

**davesmithsays' VS-format fit is the honest outlier here — n_clears is healthy (110) but
n_volleys=2 is not usable for anything beyond "the extractor ran and found real clear activity."**
The settled-cover volley detector needs a specific geometric signature (two columns exactly
`NCOLS//2=4` apart both gaining a new same-row cell in the same second) — this match window
apparently just didn't produce many of those in 420s, which could be genuine (this pairing traded
fewer coordinated multi-column volleys) or could be an artifact of window placement (see §7).
Either way: **do not put this number in davesmithsays' dossier as a pressure-profile claim** —
report the n and stop, per the honesty rules.

## 6. Archetype read (revisited at n=5 match-pooled fits)

**Still not a real archetype clustering — now for a more specific reason than "only 2 points."**
All five rows above are **match-level pooled fits** (sender+receiver combined), not independent
player observations. A real archetype grid needs either (a) genuine per-player attribution
(splitting which side of each match generated which volleys/clears — not done, see §3 of pass 1's
caveat, still unaddressed) or (b) enough *independent* matches per named player to characterize
them individually. Right now every named player has exactly ONE match window, pooled with a
different, uncontrolled opponent each time — Jarsdad's "fast, high-follow-through" numbers could
be Jarsdad's style, dmhero's style, or an interaction between them, and this data cannot
distinguish those cases.

**What CAN be said honestly:** the four new match-level profiles show real, measurable spread
against struktured's:
- **Jarsdad/dmhero's match is the most reflexive** of the set: shortest inter-volley gap (16.4s
  vs struktured's 22.7s and Bidwell's 31.5s) and the second-highest big-clear follow-through
  (60.0% at 7-10 cells, behind only struktured's 74.1%) — and it's the only new fit with enough
  volleys (26) to trust that number at face value.
- **Bidwell/Missy's match is the slowest**: longest inter-volley gap (31.5s) of any fit including
  struktured's, though LOW-CONFIDENCE (n=13) — a real spread, not yet a confident claim.
- **Rob Burrito's match sits in between** on gap timing but noticeably lower on both
  follow-through bins than struktured's (§0 of pass 1).

This is a genuine, reportable spread in match-level pressure dynamics — useful evidence the style
space is wide, which is what tonight's rule cares about — but forcing it into "Jarsdad = rusher,
Bidwell = staller" would be exactly the fabricated-ensemble the honesty rules warn against, since
none of these numbers are isolated to one player yet.

## 7. Ensemble-gate recipe — updated next step (supersedes pass 1 §7, which had the wrong bracket)

Gate structure proposal unchanged from pass 1 (evaluate a ship candidate against every fitted
model individually, not averaged; LOW-CONFIDENCE fits reported alongside, not gating alone).

**Concrete next step, corrected:**
1. **Per-player separation is now the higher-leverage move than more sources.** Five match-pooled
   fits with uncontrolled opposite-side opponents can't resolve whose style is whose. Splitting
   `extract_match_events`' output by SENDER side before fitting (i.e. fit "the sender's clears
   trigger the receiver's volleys" directionally, per side, instead of pooling both directions)
   would let Jarsdad's 26-volley match actually say something about Jarsdad specifically, not
   about "this match." Scoped as new work, not attempted this pass (time-boxed).
2. If pulling more sources instead: Rob Burrito, Jarsdad, and Bidwell's brackets (Red, White) each
   cover "Rounds 1, 2, 3" with 6 players — each named player likely has 2-3 match segments in
   their existing downloaded video, not just the one window fit this pass. Re-scanning the
   already-downloaded Red/White Bracket videos for additional segments (same nameplate-diff
   localization technique used this pass) would extend existing players' data without touching
   new video files.
3. davesmithsays' n=2 result (§5) suggests his particular VS match may need a longer window or a
   different segment within Green Bracket (only one ~420s window was tried) before concluding
   anything about volley behavior specifically — his clear-rate data (n=110) is fine, the volley
   detector just didn't fire much in this slice.

## Per-player dossier paragraphs (for merge into `player_styles/`)

Footage-observed tier, each citing video + timestamp + attribution confidence + fit confidence
per the honesty rules. Drafted here for team-lead/dossier-owner to merge; not yet applied to the
`.md` files directly by this pass (see final message).

**jarsdad** (attribution: HIGH — nameplate "(35) Jarsdad" matches White Bracket roster exactly):
First gameplay-derived data point, upgrading the dossier from n=0. Footage:
`youtube-drmc-official-2024/009_..._White_Bracket.mp4`, t≈200-480s, bottom-pair slot vs. dmhero
(6-player White Bracket, Rounds 1-3). Fit confidence OK (n=26 volleys, above the n=20 line). Note
this is a MATCH-POOLED fit (Jarsdad + dmhero's events summed, not separated) — treat the following
as "this match's" profile, not confirmed Jarsdad-specific: inter-volley gap 16.4s (the fastest of
the whole style-ensemble sample so far, versus struktured's 22.7s), volley size mean 2.77 cells,
and the second-highest big-clear follow-through in the sample (60.0% of 7-10-cell clears drew a
counter-volley within 5s, n=10). Directionally reads as a high-tempo, high-follow-through match;
whether that's Jarsdad, dmhero, or their interaction is not resolved by this data.

**bidwell** (attribution: HIGH — nameplate "(19) Robert Smith" cross-referenced against "19 -
Chris Bidwell (as Robert Smith)" in the White Bracket roster description; **supersedes the
dossier's current note that the only footage is the never-publish TMG handheld clip** — broadcast
footage of Bidwell exists and was usable). Footage: same White Bracket video, t≈200-480s,
top-pair slot vs. Missy. Fit confidence LOW (n=13 volleys, below n=20 — report, don't treat as
settled). Match-pooled, same caveat as above: longest inter-volley gap in the entire sample so far
(31.5s, vs struktured's 22.7s and Jarsdad's match's 16.4s), volley size mean 2.31 (smallest in the
sample), P(volley|clear 4-6)=33.3% similar to struktured's 32.1%, P(volley|clear 7-10)=33.3% but
n=3 — too thin to read. Directionally the slowest-tempo match fit so far; same per-player caveat
as Jarsdad's entry.

**roburrito** (attribution: HIGH, restated from pass 1 — nameplate "(17) Rob Burrito" matches Red
Bracket roster). Footage: `009...` — correction, `003_..._Red_Bracket.mp4`, t≈350-650s, top-pair
slot vs. Jenny G. Fit confidence LOW (n=18, just under the n=20 line). Match-pooled. Volley size
mean 2.44 (close to struktured's 2.54 — similar typical volley scale) but both follow-through
bins run markedly lower than struktured's (21.9% vs 32.1% at 4-6 cells; 25.0% vs 74.1% at 7-10
cells, n=12) — this specific match returned pressure less reflexively than struktured's session
did. First gameplay-derived data point for this dossier, upgrading it from n=0/photo-only.

**davesmithsays** (attribution: HIGH — nameplate "(44) Davesmithsays" matches Green Bracket
roster; a SEPARATE finding from the already-reported Speed-bracket format-incompatibility
negative). Footage: `006_..._Green_Bracket.mp4`, t≈1330-1750s, bottom-pair slot vs. Larvae. This
IS the correct game mode (continuous VS, not the solo Speed-bracket race) and the clear-detection
side worked fine (n=110 clears, healthy). **But volley detection returned only n=2 — too thin to
report ANY pressure-conditional number for this dossier entry.** What's dossier-safe to say: a
genuine VS-format broadcast appearance exists and is processable (upgrade from photo-only), the
clear-size activity was substantial, but no P(volley|clear) or gap-timing claim should be made
from n=2. Flagged for a follow-up pass with a wider/different window (§7).

## Provenance

- Vision: `vision_speed2025.py`, `vision_champ2024.py` (P1/P2, top pair; P1B/P2B for the bottom
  pair used this pass are inline in the fit invocations, not yet folded into the module — see §3).
- Fitting: `fit_ensemble_source.py` (unchanged from pass 1).
- New fits: `results/style_ensemble_v1/white_bracket_2024_jarsdad_dmhero_fit.json`,
  `results/style_ensemble_v1/white_bracket_2024_bidwell_missy_fit.json`,
  `results/style_ensemble_v1/green_bracket_2024_larvae_davesmithsays_fit.json`.
- Bracket rosters cross-checked against every 2024 Championship `.description` file on disk
  (`003`-`010_*.description`), not assumed from a single reference frame this time — this is what
  caught pass 1's Red-Bracket misattribution.
- Player dossiers read before writing (per task instruction):
  `dr-mario-playerstyles-wt/player_styles/{jarsdad,bidwell,roburrito,davesmithsays}.md`.
