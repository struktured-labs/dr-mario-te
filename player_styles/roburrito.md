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

**Fit confidence LOW** (n=18 volleys, just under the n=20 confidence line). **Match-pooled**
(events summed with Jenny G's, not separated by sender/receiver — see the style-ensemble report
for why per-player separation isn't done yet): volley size mean 2.44 cells [2.06, 2.89] — close to
struktured's reference session (2.54) — but both counter-volley follow-through rates run
markedly lower than struktured's: P(volley|clear 4-6)=21.9% (n=73) vs struktured's 32.1%;
P(volley|clear 7-10)=25.0% (n=12) vs struktured's 74.1%. Directionally: similar typical volley
scale to struktured's session, but this match returned pressure less reflexively. Not resolved
whether that's Rob Burrito's trait, Jenny G's, or the pairing's.

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

n=0 matches. This is a placeholder, not a profile — every claim above is either "we don't
know" or a hand-posture guess flagged as too weak to use. Do not treat the absence of
style notes here as "plays plainly"; it means no data exists. Next step: any photo/video
with the actual screen in frame, or tournament bracket/score data that doesn't require a
board read at all.
