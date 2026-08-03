# Player dossiers — index

Task #36. Goal: build per-player scouting reports (game-analysis only, respectful,
household-audience tone) from whatever footage/photos exist, as a step toward a real
(state, move) extraction pipeline — see [[dr-mario-player-data.md]] in the main repo's
memory for the longer-term program this feeds.

## Who's profiled, and data quality

| Player | File | Photos available | Readable board? | Confidence |
|---|---|---|---|---|
| struktured | `struktured.md` | 16 STUDY-pause stills (`~/Pictures/stomper_matches/`) + prior self-reports/match logs | Yes — all 16 | Medium: virus-count/timing analysis is solid (EXIF + on-screen counter); stack-level style reads are qualitative; rotation-slip claim still unconfirmed |
| roburrito | `roburrito.md` | 1 photo (DRMC Philadelphia, hands + controller) | No — no screen in frame | Very low: identity only |
| davesmithsays | `davesmithsays.md` | 1 photo (DRMC Philadelphia, player + out-of-focus CRT) | No — CRT present but out of focus | Very low: identity only |

`~/Pictures` was scanned for more DRMC/player-named images and Dr. Mario board photos.
Findings:
- Only two files are player-named (`DRMC Philadelphia 2026-40 roburrito.jpg`,
  `DRMC Philadelphia 2026-23 davesmithsays.jpg`), both from the same tournament, taken
  48 seconds apart (EXIF 2026-07-02 00:50-00:51).
- `IMG_0660.jpg` is a wide shot of the tournament floor itself (a "Smashadelphia"/VGC-USA
  branded con hall with rows of CRT stations, a "FREEPLAY" and "HIGH SCORE TOURNAMENTS"
  section) — confirms the event context but no individual board is legible at that scale.
- `Drmariote-20260719T220659Z-1-001.zip` and `drmario-on-tv.jpeg` turned out to be
  **household** photos (same checkered-pattern Pocket menu skin, "STUDY"/"MED" labels seen
  in the stomper_matches corpus), not additional DRMC tournament material — mentioned here
  so nobody re-discovers and re-investigates them as a new lead.
- No other DRMC-prefixed or otherwise player-tagged files exist in `~/Pictures` as of this
  scan.

## What the (state, move) extraction pipeline needs next
Vision-from-photo has a hard ceiling documented already in [[dr-mario-m2b-corpus-run]]
("VISION CANNOT MEASURE TUCKS") and confirmed again here: a still frame gives stack shape
and virus count but nothing about the *sequence* of placements that produced it, and
can't catch fast events (a tuck, a rotation slip) that resolve within a frame or two.
Concretely, to move past "identity + occasional board snapshot" toward real per-player
style data:
1. **Video, not stills** — the household session already has three unused clips
   (`~/Pictures/PXL_20260802_013409485.mp4`, `PXL_20260802_014130748.mp4`,
   `PXL_20260802_013954971.mp4`, also duplicated inside `Photos-1-001*.zip`). Frame
   extraction around each drop would let a rotation slip or tuck actually be observed
   instead of inferred from its aftermath.
2. **A DRMC-side ROM/capture path** — the [[dr-mario-romhack-survey]] entry notes the
   DRMC ROM is a playdm hack on our Rev0 base; if tournament footage or a stream capture
   exists at frame rate, the same tile-decoding approach used for the M2b corpus
   ([[dr-mario-tile-encoding]]) would apply directly and give real (state, move) pairs
   instead of single-frame board reads.
3. **More named-player photos** — right now roburrito and davesmithsays each have exactly
   one photo and neither shows a board. Any additional DRMC Philadelphia photos (or a
   pointer to where the full event album lives) would be the cheapest way to upgrade both
   from "identity only" to an actual style read.

## Notes on scope/tone
Per the brief: these are real community members. Dossiers are scouting-report style,
game-analysis only, and explicitly flag confidence level and assumptions (especially the
1P=human/2P=AI seat assumption used for struktured's board reads, and the total absence of
board data for the two DRMC players) rather than filling gaps with speculation.
