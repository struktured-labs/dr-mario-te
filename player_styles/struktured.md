# struktured — player style profile

*DRMC handle: **struktured** (user-confirmed 2026-08-03 — same as his name here).*
*Household co-pilot on this project; also the AI's primary test opponent.*

**Status: QUANTITATIVE as of 2026-08-04.** This profile was rebuilt from the
first fully recorded set (25 min, 1080p60, OBS/DeckLink) processed by an
11-agent film-review workflow: 331 pills individually tracked at 60 fps,
tracker independently verified against raw frames (5 tracker bugs found and
fixed by the verifier before the numbers below were accepted). Earlier
qualitative reads (photo stills, self-reports) are retained in the history
sections and superseded where they conflict. Full reports:
`FILM_REVIEW_20260804_SCORECARD.md`, `FILM_REVIEW_20260804_m3_suicide.md`,
and `~/projects/dr_mario_rl/tmp/film_review_20260804/analysis/*.md`.

## Measured profile (2026-08-04 recorded set, n=331 pills)

| dimension | measurement | reading |
|---|---|---|
| Decision latency | reactive median 250 ms, p75 367 ms, p90 512 ms; 23.6% of pills pre-planned (input <100 ms); straight drops rare (2.7%) | Quick, deliberate player. No chronic slowness. |
| Latency tail | slowest 1.87 s (three separated same-color clusters); next-slowest cluster in tight endgame stacks | Stalls are rare and specific: optimizer-bait boards. |
| Rotation corrections | 7.25 per 100 pills all classes (reversal 0.60, overshoot 3.02, late-flurry 4.83) | Execution largely clean. Overshoots are the expensive class (~37 frames each). |
| A/B retrain cost | A/B-class events = 50% of all correction events (12/24), ~3.6/100 pills; both reversals in m2 | Real, visible, small. This is the two-button retrain baseline — track per session. |
| Phase behavior | corrections by phase: early 7.04 / mid 11.11 / endgame 5.85 per 100; endgame latency RISES 150→233 ms; endgame reversals 0.00% | Under endgame pressure he gets SLOWER AND CLEANER, not sloppier. |
| Style vs AI | board at the m4 decisive moment: junk 18 vs 65, mean height 4.5 vs 10.9, stranded halves 2 vs 16 | Dramatically cleaner builder than the AI. Wins structure, loses race-closings. |

## The endgame, precisely (the m4 case study)

His self-model was "endgame speed panic — it gets way faster." The tape says:

- The structural lead was real and huge: at t=1360 he sat at 2 viruses with a
  low clean board while the AI had 7 on a junk mountain (18 vs 65 junk cells).
- The equalization was real: over the final ~90 s his junk ballooned 19→51
  while the AI excavated 70→46 and cleared out. Final score 01–00 — one virus
  from a set-leveling win.
- The mechanism was NOT panic-execution: latency rose (careful), corrections
  fell to their set-wide minimum, zero reversals. And the game did not
  objectively speed up — the AI's own placement interval lengthened too
  (1.54→2.13 s). The subjective "faster" is time pressure felt during frozen
  deliberation.
- The real siege, counted (settled-material seal episodes over his remaining
  viruses, m4 close): **21 total — 8 self-inflicted, 13 from AI volleys.** He
  kept winning the digs: nearly every sealed virus shows a later RE-OPENED
  state. One virus, (13,3), was sealed four separate times.
- The kill shot: **t=1348, a single self-placement sealed three viruses at
  once** — (13,2)/(14,2)/(13,3) — and (13,2) never re-opened. That is the
  final `01` on the counter, and the "closed out my one good option" moment.
  His post-set estimate "I made probably 3 or more [closing blunders]" was an
  UNDERCOUNT (8 self-seals), but the majority of burial pressure was incoming
  fire, and he out-excavated it until the triple-seal.
- Player refinement (post-scorecard): one irreversible closing blunder "really
  messes with your psyche" — and the tape agrees on the signature: tilt
  expresses as OVER-CAUTION (latency up, corrections down), not flailing.

**Training target (the highest-leverage one on record): last-2-virus closing
lines — excavation sequencing under incoming volleys — plus a pre-commit habit
of asking "does this placement seal a target?", weighted highest when one
placement can seal multiple adjacent columns. Not nerve control; his nerves
measurably hold.**

## Blunder taxonomy — five self-reported classes, adjudicated blind

Method commitment (user-requested): the film review was BLIND-FIRST — analysis
agents received zero self-report content; his claims were tested against their
numbers afterward. Divergences are first-class findings.

| # | class | verdict |
|---|---|---|
| 1 | A/B rotation slips ("~1/3 of my blunders"), deliberate two-button retrain | **CONFIRMED in proportion** (50% of correction events), small absolutely (~3.6/100 pills). Measure per-session as the retrain curve; do NOT remap (his explicit call). |
| 2 | Decision latency ("not acting fast enough") | **PARTIAL** — true only in a rare tail that clusters on multi-cluster boards; bulk tempo is fine. |
| 3 | Endgame speed panic | **OUTCOME CONFIRMED, MECHANISM REFUTED** — see case study above. Tilt-as-overcaution, closing technique is the gap. |
| 4 | Over-setup tendency | **CONFIRMED** (closed 2026-08-05): declines **47.9% of available immediate clears** (102/213, engine-verified reconstruction, 4/5 spot-checks visually confirmed) — and the rate is FLAT across matches (44.8–53.3%) and phases (44.2–51.0%): a stable style trait, not a lapse. Time-to-cash median 1 pill but tail to 28. His self-model was right. |
| 5 | Generic sequence fumbles | **MINOR — and REFUTED as the m2 mechanism** (closed 2026-08-05): credible lateral classes (reversal + post-softdrop) net 9.97/100 pills; the biggest raw class (land-then-patch, 20.5/100) failed its own control (touch rate flat ~31–32% with or without a preceding clear) and is noise. m2 — the match he attributed to fumbling around — has the LOWEST credible rate of all four (4.26/100); m2's errors were rotation-class, not sequence-class. |

## Record vs the AI

| date | opponent build | result | how |
|---|---|---|---|
| 2026-08-02 "Set A" | Stomper v3 classic-tempo (982291ef), Pocket | AI 3–2 | his topouts; 16-photo EXIF series covers 2 games |
| 2026-08-02 "Set B" | Stomper v4 fast+coldinit, Pocket | AI 3–1 | incl. the AI's first self-topout vs him |
| 2026-08-03 | Stomper v4, Pocket | **struktured 3–2** — first human SET WIN on record | ALL FIVE games self-topouts, zero clears either side; set decided by junk-debt maturity. His two losses = fatigue unforced errors ("all my own topouts were human blunders"). AI won zero games on its own merits. |
| 2026-08-04 early | **strand20** (the #47 fix), Pocket on TV | **struktured 3–0 sweep**, game 3 by FULL CLEAR (00–02) | first recorded human full-clear win over any Stomper build; AI topped out AHEAD 33–11 in game 1 |
| 2026-08-04 late | strand20, Pocket Dock, RECORDED | **AI 3–1 — its first set win over him** | m1 AI full-clear (him at 3); m2 his topout ("messing around" — SUPPORTED: highest correction rate + the set's only reversals); m3 his win via AI suicide; m4 AI clear with him at 01 |

## How each side wins (mechanisms, now measured)

- **He beats the AI by out-lasting**: stay clean, survive the early race, let
  the AI's junk debt mature. Confirmed across 2026-08-03 (three AI
  self-topouts) and the m4 structure numbers. Consistent with
  [[dr-mario-lnk1-vs-confirmed]] — the AI wins by out-racing, never by
  out-building.
- **The AI beats him late**: its structurally best phase (fixed compute
  latency, volley pressure while excavating) coincides with his closing-skill
  gap. m1's kill was surgical-looking on tape — a col-7 lane open for ~70 s
  re-buried by the final two volleys — though m1's verdict is MIXED ~60%
  earned: his execution never degraded; the damage volume was 3.4:1
  self-placed vs garbage.
- **The AI's losses to him are self-inflicted**: five self-topouts vs him
  across builds versus ZERO in 400 logged CvC losses — the failure mode is
  human-specific. The m3 recorded suicide was adjudicated **H1: commit-path
  defect (~75%)** — the shipped search wanted open columns in 5/6 death
  commits (final commit ranked 24/24, gap 1224) while the tape shows in-place
  locks with no lateral movement; the eval was REFUTED as the cause. His
  counter-pressure contributes (a 4-wide volley seeded the congestion) but
  did not pull the trigger. Repair owner: task #49 (pair-latch audit).

## Why this matters to the project

- His pressure profile is the missing simulator input: the pressure-tax
  workflow proved drip garbage cannot reproduce his kills — the bursty,
  combo-timed volley model must be fit FROM this replay corpus.
- He is the reference opponent for opponent-aware VS work (#15) and the
  measuring stick for "feels good to lose to" (TV dignity bar).
- The A/B retrain curve and the closing-drill target are candidate TE
  features (rotation-drill mode; last-N-virus practice scenarios).
- Contrast with [[dr_lulu]] (undefeated, wins via timed pressure) still gives
  two distinct human baselines on the same hardware family.

## Provenance & corrections (kept per the no-silent-rewrites rule)

- 2026-08-03: earlier draft mis-attributed `~/Pictures/PXL_*.mp4` clips to his
  session — filenames encode UTC (+4h EDT); they are 2026-08-01 footage,
  very likely [[dr_lulu]]'s. No video of his own sessions existed before the
  capture pipeline.
- 2026-08-03: removed an uncitable "0-3 vs stomp180" record-table row
  (no orphan scores in dossiers).
- 2026-08-03: a photo was twice misread as SNES T&DM (once from menu labels,
  once from a console visible in the cabinet). Player challenge + palette
  re-read settled both: NES Dr. Mario, our cart. Console in frame ≠ console
  playing.
- 2026-08-04: "SAVE TO STATE 4" on the MiSTer was the duel tracker's own ring
  capture, not a player hotkey.
- 2026-08-04 scorecard corrections to earlier reads: m1 ended with him at 3
  viruses (not 5); m3 tracker initially fabricated a phantom pill (removed by
  the verifier).
- The 2026-08-02 qualitative film study (16 stills, two time-series games,
  topout-not-race-loss read) is superseded by the recorded-set numbers but
  retained in git history; its 1P-attribution logic (cart-build tags
  982291ef/v4 absent from dr_lulu's corpus) still stands.

## Evidence index

- Recorded set: `~/Videos/drmario_sessions/20260804_1955_pocket_dock.mkv`
  (+ backup `~/projects/dr_mario_rl/tmp/session_20260804_first_recorded_set.mkv`)
- Film-review working set: `~/projects/dr_mario_rl/tmp/film_review_20260804/`
  (1 fps frames, 60 fps crops, `events/*.csv` per-pill logs, `analysis/*.md`,
  `recon/` proxy test + VERDICT.md, `vision.py` + `tracker.py`)
- Photo evidence: `evidence/struktured_topout_gameA_20260802.jpg`,
  `evidence/struktured_gameB_freshrack_20260802.jpg`,
  `evidence/drm_2p_20260803_win2.jpg`, `evidence/drm_2p_20260803_game3_loss.jpg`,
  `evidence/drm_2p_20260803_game4_loss.jpg`; fuller sets in
  `~/Pictures/stomper_matches/`
- Scorecard: `FILM_REVIEW_20260804_SCORECARD.md` (tagged
  `film-review-scorecard`); m3 autopsy: `FILM_REVIEW_20260804_m3_suicide.md`
  (tagged `film-review-m3-autopsy`)
