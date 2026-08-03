# Player dossiers — index

Task #36. Goal: build per-player scouting reports (game-analysis only, respectful,
household-audience tone) from whatever footage/photos exist, as a step toward a real
(state, move) extraction pipeline (`dr-mario-player-data`).

This is the canonical location (`player_styles/` on `main`), matching the format
[[dr_lulu]] established. An earlier, more exploratory pass at this same task lives at
`experiments/player_styles/` on the `copro-qa-harness` branch — kept there rather than
deleted, since it has some analysis (per-frame stack-shape notes) not repeated here.

## Who's profiled, and data quality

| Player | File | Photos / footage | Readable board? | Confidence |
|---|---|---|---|---|
| dr. lulu | `dr_lulu.md` | 205-photo series + 2 film-study clips + evidence photo, 2026-08-01 | Yes | Highest in this set: n=4 matches, undefeated, one confirmed AI KO, plus one frame-level execution data point (2026-08-03 addendum) |
| struktured | `struktured.md` | 16 STUDY-pause stills (2 games, 2026-08-02) + 2 self-reported set summaries (Set A 3-2, Set B 3-1) | Yes for the 16 stills | Medium: solid EXIF/virus-counter reconstruction for the photographed games; DRMC handle confirmed ("struktured") |
| roburrito | `roburrito.md` | 1 identity photo, DRMC Philadelphia 2026 | No — no screen in frame | Very low: identity only |
| davesmithsays | `davesmithsays.md` | 1 identity photo, DRMC Philadelphia 2026 | No — CRT present but out of focus | Very low: identity only |

## Open questions blocking further work
- **struktured's rotation-slip claim (self-reported A/B confusion)** — still untested.
  No video of his own session exists in `~/Pictures`; the only candidate clips turned out
  to be dr. lulu's (see below). Needs either a fresh recording of his session or the
  capture-card device.
- **Capture-card device** — on hand per the task brief, not yet configured for either
  struktured or dr. lulu. Once live, both dossiers upgrade from film-study prose to
  measured attack-timing/tempo stats, same plan as `dr_lulu.md`'s "Capture-card video
  pending" note. The 2026-08-03 execution-consistency addendum to `dr_lulu.md` is a
  small early down payment on this using found footage instead.

## `~/Pictures` scan for more DRMC/player material
Confirmed only two player-named files exist (`DRMC Philadelphia 2026-40 roburrito.jpg`,
`DRMC Philadelphia 2026-23 davesmithsays.jpg`), both from the same tournament, 48 seconds
apart (EXIF 2026-07-02 00:50-00:51). A wide venue shot (`IMG_0660.jpg`, a
Smashadelphia/VGC-USA branded con hall) confirms the event context but is too wide to
read any individual board — not copied into evidence/ since it isn't tied to a specific
player. Two other candidates (`Drmariote-...zip`, `drmario-on-tv.jpeg`) turned out to be
struktured's own household TV (same STUDY/MED skin as the stomper_matches corpus), not
DRMC tournament material — noted here so nobody re-chases that lead.

## What the (state, move) extraction pipeline needs next
Vision-from-photo has a hard ceiling already documented in `dr-mario-m2b-corpus-run`
("VISION CANNOT MEASURE TUCKS") and confirmed again across every dossier in this
directory: a still frame gives stack shape and virus count but nothing about the
*sequence* of placements that produced it, and can't catch fast events (a tuck, a
rotation slip) that resolve within a frame or two. Concretely:
1. **Capture-card video, not stills** — the single highest-leverage upgrade for both
   household players once the device is configured.
2. **Checked, and it's not struktured's** — `~/Pictures/PXL_20260802_013409485.mp4`,
   `_014130748.mp4`, `_013954971.mp4` looked like unused footage of his 2026-08-02
   session by filename, but their embedded `creation_time` is UTC while every JPEG EXIF
   in this corpus is local (+4h/EDT) — converting puts all three at 2026-08-01
   ~21:34-21:41 local, matching [[dr_lulu]]'s night-one window and her cited "47 s
   film-study clip" almost exactly (duration 47.77s). **Trap for future sessions**:
   Pixel video filenames/`creation_time` encode UTC; Pixel JPEG EXIF encodes local time.
   The same calendar date in a filename can be the previous evening once you cross a
   4-hour offset past midnight UTC — verify with `ffprobe -show_entries
   format_tags=creation_time` and convert before trusting a video's date-in-name.
   No footage of struktured's actual session exists yet in `~/Pictures`. Redirected the
   pipeline to the correct player instead: `dr_lulu.md`'s 2026-08-03 addendum used it to
   get one confirmed clean spawn-to-lock read (n=1, no flip) — see that file for the
   full method and honest limits (roughly half the sampled pill pairs were same-color and
   structurally can't test rotation handedness at all).
3. **DRMC-side capture** — the M2b corpus (`dr-mario-m2b-corpus-run`) measured an
   aggregate tourney-player attack-given-clear rate of 17.1% (~2x our AI at the time).
   Neither roburrito nor davesmithsays has a per-player number computed against that
   baseline — would need actual gameplay footage of either, which we don't have yet.
   The DRMC ROM is a playdm hack on our Rev0 base (`dr-mario-romhack-survey`); the same
   tile-decoding approach used for the M2b corpus (`dr-mario-tile-encoding`) would apply
   directly to any tournament stream/VOD capture if one surfaces.
4. **More named-player photos** — roburrito and davesmithsays each have exactly one photo
   and neither shows a board. Any additional DRMC Philadelphia material would be the
   cheapest way to upgrade both from "identity only" to an actual style read.

## Notes on scope/tone
Per the brief: these are real community members and household members. Dossiers are
scouting-report style, game-analysis only, and explicitly flag confidence level and
assumptions rather than filling gaps with speculation.
