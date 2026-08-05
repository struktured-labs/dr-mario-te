# davesmithsays — player style profile

*DRMC handle: **davesmithsays** (badge reads "DSS" / "davesmithsays", VGC-branded lanyard)*
*DRMC Philadelphia 2026 tournament attendee. No style data yet — identity only.*

## Record vs the AI

Not applicable yet. davesmithsays has never played the Combo Stomper; the only material
we have is a single tournament photo unrelated to our AI.

## Observed style — board data now exists, but thin (footage-observed, 2026-08-05)

**Updates the n=0/photo-only status below.** Two DrMC 2024 Championship broadcast appearances
found this pass, both HIGH attribution confidence:

1. **VS-format (correct game mode, but data is too thin to use):** *nameplate "(44) Davesmithsays"
   matches the Green Bracket's `.description` roster line "44 - davesmithsays" exactly.* Footage:
   `youtube-drmc-official-2024/006_20241116_y60HICBTT8Q_THE_2024_DrMC_Championship_-_Green_Bracket.mp4`,
   t≈1330-1750s, bottom-pair slot of the 4-way-split broadcast, vs. Larvae (seed 12).
   Clear-event detection worked fine (n=110 clears, healthy volume) but the volley detector
   returned only **n=2** — far too thin for any P(volley|clear) or gap-timing claim. **Do not cite
   a pressure-conditional number for davesmithsays from this window** — the only safe claim is
   "a genuine VS-format broadcast appearance exists and is processable," not any tempo/style
   number. A follow-up pass with a different or wider window may recover more volleys (see
   `eval47/STYLE_ENSEMBLE_V1.md` §7).
2. **Speed-bracket format (14 appearances in `players.json`, mostly 2024-2025 Gold Speed
   Monthly):** confirmed **NOT usable** with the current fitting method — this is a solo
   level-climb race format (e.g. "Round 1 Levels 6-9"), not the continuous 2P VS match the
   volley/clear extractor needs. One such video (June 2025, vs. OOKtheLibrarian) was fit and
   produced garbage (449 spurious "clears" in 24 minutes); root-caused to level-transition
   virus-refill events and classification noise, not real gameplay signal. Documented as a
   negative in `eval47/STYLE_ENSEMBLE_V1.md` §5 (pass 1) — do not attempt to fit any of
   davesmithsays' other 13 Speed-bracket appearances without first solving that format-mismatch
   problem.

### Prior state (photo-only, kept for context)

Nothing beyond the photo. The one photo we have (`evidence/davesmithsays_drmc_philadelphia_2026.jpg`, EXIF
2026-07-02 00:50:55, ~48s before the roburrito photo — same event, same row of stations)
shows two players seated at a CRT: davesmithsays on the right, controller in both hands,
watching the screen off-frame; an unbadged player in a bucket hat/sunglasses to his left,
who may be his opponent or a bystander — not identifiable from this shot. The CRT itself
is in the foreground but badly out of focus; no playfield, virus count, or clear pattern
is legible. Nothing here supports a style claim.

## Why this matters to the project

Same as [[roburrito]]: confirms the tournament scene and a named player exist, and is a
candidate for the player-data program / M2b corpus pipeline (aggregate tourney
attack-given-clear rate 17.1%, `dr-mario-m2b-corpus-run`) once real footage is available.
No per-player number is computable from this photo.

## Evidence

- `evidence/davesmithsays_drmc_philadelphia_2026.jpg` — identity photo only, DRMC
  Philadelphia 2026 (EXIF 2026-07-02 00:50:55). CRT present but out of focus; no board
  content legible.

## Caveats

n=0 matches. Placeholder entry — nothing about play style is asserted. Next step: a
focused shot of his screen during play, confirmation of who the other seated player is,
or bracket/score data independent of a board read.
