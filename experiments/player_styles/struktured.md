# Player dossier: struktured

Started 2026-08-02 (task #36). Sources: household Pocket matches vs Combo Stomper,
DRMC footage corpus, self-reports.

## Self-reported (2026-08-02)
- **Rotation-button confusion**: "I make lots of mistakes by hitting A instead of B or
  B instead of A. I grew up on just A." — single-button (A-only) rotation muscle memory;
  under time pressure the mirror rotation fires. Expect: flipped-orientation placements
  adjacent to otherwise-correct column choices = execution slip, not judgment error.
  Implication for coaching/handicap features: a practice mode or personality that
  punishes orientation slips less (or a single-rotate control option in TE) would
  target his actual error class.
- Plays "poor choices for fun" deliberately in casual sets; small Pocket screen is a
  real handicap ("hard to see, no tv").

## Match log (vs Combo Stomper, Pocket classic-tempo cart 982291ef)
- 2026-08-02 match 1: L11 MED. Arc 48-48 -> 43-36 -> 30-17 -> 18-04, loss. Stomper
  pulled ahead steadily (chain-engine grind). User: "I lost but ... several
  should-have-beens both directions."
- 2026-08-02 match 2: in progress, photo stream via shared album.
- 2026-08-02 match 2 (v4 fast+coldinit cart): Stomper won 3-1; ONE game the AI self-killed
  (topped out — consistent with the loss-autopsy garbage-channel price, ~45% of its losses
  are self-inflicted). User self-assessed as playing poorly; opening-quality verdict on v4
  "uncertain" from couch observation. Title-screen 2P pin noted by user (by design).

## Field-reported eval suspicion (2026-08-02, MiSTer duel observation)
- Y/R capsule hung over a gap above a BLUE virus (matches neither half), "not forced,
  strange choice". Suspect: g_hang / W_HANG_GAP implementation may credit hovering over a
  virus COLUMN (HANG_VIRUS_COL_ONLY) without enforcing the COLOR-match the delayed-drop
  concept requires — a mismatched hang buries the virus instead of clearing it.
  AUDIT: check the shipped hang term's color condition (LeafEval.sv S_DONE2 hang path +
  the 6502 eh_terms g_hang) against the definition; if color isn't checked, price the fix.

## Ops setup (2026-08-02, self-described)
- "Command seat": Pocket playable in-chair + PC session (Claude) + MiSTer monitor visible
  simultaneously. Human = live silicon observer; catches display/behavior anomalies the
  remote instruments miss (proven 3x tonight: title garble, rematch verticals, mismatched
  hang). Treat chair-side reports as first-class telemetry.

## Board-reading: household Pocket matches vs Combo Stomper (2026-08-03, task #36)

Source: `~/Pictures/stomper_matches/match_01.jpg`-`match_16.jpg`, 16 phone photos of the
Pocket's STUDY (pause) screen, all LEVEL 11/11 MED/MED. EXIF puts every shot in a single
~12-minute session on 2026-08-02, 19:36-19:48. **Working assumption**: 1P (left column,
or top column in the sideways-held shots) = the household human side, 2P = Combo Stomper.
This isn't independently confirmed from the stills (no controller-in-frame shot in this
set) but matches every prior log entry and the STUDY layout convention used elsewhere in
this corpus — flagging it as an assumption, not a fact.

### Two games reconstructed from EXIF + the on-screen virus counter
Sorting the 16 shots by capture time turns them into two short virus-count time series
(read as 1P|2P remaining):

- **Game A** 19:36:37→19:42:42: 40|31 → 30|17 (×2, same moment two angles) → 22|09 →
  22|05 → 21|04 → 20|04 → 18|04 → 17|03 (×2) → **16|03, 1P defeat** (`match_03.jpg` shows
  a red X stamped over a virus icon on the 1P side with "START" beneath — a topout/loss
  frame, not a clear). Over that span 1P cleared ~24 viruses, 2P cleared ~28 — comparable
  clear *rate*, but 1P still went down by topping out while 16 viruses remained on the
  board. Reads as burial/stack-height failure, not a race loss — matches the self-report
  "I lost but... several should-have-beens."
- **Game B** 19:46:32→19:48:06 (fresh rack, 48|48 → 47|42 → 43|36 → 41|32 → 40|31,
  unfinished in this photo set): over ~90s, 1P cleared 8 viruses, 2P cleared 17 — better
  than 2x. This one matches the "Stomper pulled ahead steadily" self-report more directly
  than Game A does.

Net: across both games the 2P/AI side is *always* at or below the 1P virus count once
play is underway — consistent with [[dr-mario-lnk1-vs-confirmed]]'s "wins by out-racing"
finding and the household match-log entries already in this file, now with photographic
+ timestamp corroboration rather than just post-game recollection.

### Rotation-slip check (A/B confusion self-report)
Looked for the flagged failure mode — a pill half in an implausible color position right
next to an otherwise-clean column, which would show a live orientation flip. **Inconclusive
from these stills**: phone-photo-of-CRT/LCD blur and JPEG compression make individual
cell colors unreliable to call at this resolution, and a STUDY pause frame only shows the
buried aftermath, not the drop that caused it — a flip is only visible in the instant it
happens. Two boards (`match_10.jpg` virus 40|31, `match_12.jpg` 41|32) show a single tall
near-monochrome column on the 1P side that *could* be a mis-rotated dump or could be
deliberate well-building; can't disambiguate from a still.
**Better source exists and is unused**: `~/Pictures/PXL_20260802_013409485.mp4`,
`PXL_20260802_014130748.mp4`, `PXL_20260802_013954971.mp4` (also bundled in the
`Photos-1-001*.zip` archives) are actual video from what looks like the same session —
frame-extracting around each drop would catch a rotation slip in the act, which no still
photo can. Recommend that as the next step before concluding anything stronger about the
A/B confusion claim.
