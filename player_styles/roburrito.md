# roburrito — player style profile

*DRMC handle: **roburrito** (per the tournament name-tag/file naming; not independently confirmed)*
*DRMC Philadelphia 2026 tournament attendee. No style data yet — identity only.*

## Record vs the AI

Not applicable yet. roburrito has never played the Combo Stomper; the only material we
have is a single tournament photo unrelated to our AI.

## Observed style — board data now exists (footage-observed, 2026-08-05)

**Updates the n=0/photo-only status below.** *Attribution: HIGH confidence — on-screen nameplate
"(17) Rob Burrito" matches the Red Bracket's own `.description` roster line ("17 - Rob Burrito")
exactly.* Footage:
`youtube-drmc-official-2024/003_20241113_wgiLIw19TFA_THE_2024_DrMC_Championship_-_Red_Bracket.mp4`,
t≈350-650s, top-pair slot of the 4-way-split broadcast, vs. Jenny G (seed 48). Located by
pixel-diff matching the pre-existing reference frame `captions/hud_frame_2024_Red_Championship.png`
against every extracted 1fps frame (best match at t=500s, mean abs pixel diff 6.05/255). Part of
the style-ensemble program (`eval47/STYLE_ENSEMBLE_V1.md`), not the standard metric battery
(declined-clear rate, rotation/lateral correction, latency, endgame seal — still not run).

**UPDATE 2026-08-05 (pass 3): per-player separation applied.** The n=18 pooled number above summed
Rob Burrito's AND Jenny G's events together. Refactored to a per-player SENDING profile (see
`eval47/STYLE_ENSEMBLE_V1.md` §5-7 for method + self-test): **Rob Burrito alone: n=12 volleys —
LOW-CONFIDENCE** (below the n=20 line). Own clears n=49.
- volley size mean 2.67 cells — close to struktured's own per-player number (2.68)
- inter-volley gap 21.5s — close to struktured's own (27.4s)
- P(counter-volley within 5s | clear 4-6 cells) = 25.6% (n=39); P(... | clear 7-10 cells) = 30.0%
  (n=10)

For comparison, Jenny G's own per-player profile is UNINFORMATIVE (n=6): gap 37.4s (much slower),
P(4-6)=17.6% (n=34). **Rob Burrito's own numbers sit noticeably closer to struktured's typical
range than the pooled match suggested** — the pooled match's "lower than struktured" read (pass 2)
may have been driven more by Jenny G's slower response than by Rob Burrito's own tempo. A
hypothesis worth testing with more footage, not a settled trait at n=12.

### Prior state (photo-only, kept for context)

None beyond the photo. The one photo we have (`evidence/roburrito_drmc_philadelphia_2026.jpg`) is a
close-up on hands and a wired NES-style controller, resting in the player's lap — no
playfield, no virus counter, no STUDY/pause screen, nothing to read. The only thing
visible is grip: two-handed hold, right-hand index/middle fingers pre-staged over both A
and B rather than parked on one. That's a hand-posture detail, not a gameplay one, and is
too thin to write down as a style claim (contrast with [[dr_lulu]], where n=4 real matches
support several concrete claims).

## Why this matters to the project

Nothing yet, beyond confirming that a tournament scene exists with named, photographable
players — a candidate future data source for the player-data program
(`dr-mario-player-data`) and the M2b corpus approach (tourney footage → (state, move)
pairs, `dr-mario-m2b-corpus-run`, which measured an aggregate attack-given-clear rate of
17.1% across tourney players — roughly 2x our AI at the time it was measured). Nothing in
this file lets us compute roburrito's own number against that baseline; that requires
actual gameplay footage, not a still of hands on a controller.

## Evidence

- `evidence/roburrito_drmc_philadelphia_2026.jpg` — identity photo only, DRMC
  Philadelphia 2026 (EXIF 2026-07-02 00:51:43). No board content.

## Caveats

The photo-only section above (n=0 matches, hand-posture guess only) is superseded by the
2026-08-05 footage-observed section — Rob Burrito now has one LOW-CONFIDENCE (n=12) pressure
profile from real Red Bracket gameplay. Still thin: one ~5-minute window, per-player-separated but
not yet cross-validated against a second match. Next step: additional Red Bracket segments for
Rob Burrito (same video, other rounds, unexplored) to push n toward the OK-confidence line.
