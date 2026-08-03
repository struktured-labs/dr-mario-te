# struktured — player style profile

*DRMC handle: **struktured** (user-confirmed 2026-08-03 — same as his name here).*
*Household co-pilot on this project; also the AI's primary test opponent.*

## Record vs the AI

| opponent | result | notes |
|---|---|---|
| Combo Stomper (v3 "classic-tempo" cart, 982291ef, Pocket, L11 MED, 2026-08-02 evening, "Set A") | **Stomper won 3–2** | final game: he "busted at 46" — self-reported blunders + a played-for-fun caveat (team-lead, 2026-08-03). The 16-photo EXIF reconstruction below covers 2 of this set's games directly (not necessarily including the "busted at 46" game specifically) |
| Combo Stomper (v4 fast+coldinit cart, Pocket, L11 MED, 2026-08-02 evening, "Set B", later than Set A) | **Stomper won 3–1** | one of the 4 games ended in an AI self-topout (consistent with the loss-autopsy's ~45% self-inflicted-loss rate); no photos for this sub-session, self-reported same night |

Unlike [[dr_lulu]], no KO of the AI is recorded for struktured yet in either the
photographed corpus or self-reports. The one detailed loss we can reconstruct from
photos (Game A below, part of Set A) ended in *his* topout, not the AI's — the inverse
of dr. lulu's KO pattern.

## Observed style (film study, n=16 stills across 2 games, 2026-08-02 — qualitative)

Source: `~/Pictures/stomper_matches/match_01.jpg`-`match_16.jpg`, phone photos of the
Pocket's STUDY (pause) screen. Sorting all 16 by EXIF capture time and reading the
on-screen virus counter turns them into two short time series instead of 16 disconnected
snapshots:

- **Game A** (19:36:37→19:42:42): 40|31 → 30|17 → 22|09 → 22|05 → 21|04 → 20|04 → 18|04 →
  17|03 → **16|03, topout** (`evidence/struktured_topout_gameA_20260802.jpg` — a red X
  stamped over a virus icon on the 1P side, "START" beneath: a loss frame, not a clear).
  Over that span he cleared ~24 viruses to the Stomper's ~28 — a comparable clear *rate* —
  but still went down with 16 viruses on the board. Reads as burial/stack-height failure,
  not a race loss. This matches this session's own contemporaneous self-report ("I lost
  but... several should-have-beens both directions") and the "match 1" arc already logged
  above (48-48→43-36→30-17→18-04) — which turns out, once sorted by EXIF, to actually
  splice together the tail of Game A with the head of Game B below; the text log
  compressed two resets into one described arc, which this photo pass now separates out.
- **Game B** (19:46:32→19:48:06, fresh rack — `evidence/struktured_gameB_freshrack_20260802.jpg`
  is the 48|48 opening frame): 48|48 → 47|42 → 43|36 → 41|32 → 40|31 (unfinished in this
  photo set). Over ~90s he cleared 8 viruses to the Stomper's 17 — worse than 2x — a
  closer match to the "Stomper pulled ahead steadily" self-report than Game A.
- **Net across both games**: the AI side is at or below his virus count in every
  mid-to-late frame — consistent with [[dr-mario-lnk1-vs-confirmed]]'s "wins by
  out-racing" finding, not by out-building or superior stack quality.
- **Rotation-slip (A/B confusion) check** — self-reported ("I make lots of mistakes by
  hitting A instead of B... I grew up on just A"). **Still inconclusive, and still no
  video of his own session**: phone-photo-of-screen blur and JPEG compression make
  individual cell colors unreliable to call at STUDY-still resolution, and a pause frame
  only shows the buried aftermath, not the drop that caused it — a flip is only visible
  in the instant it happens. Two boards (virus 40|31 and 41|32, not pictured here) show a
  single tall near-monochrome column that could be a mis-rotated dump or could be
  deliberate well-building; can't disambiguate from a still.
  **Correction (2026-08-03)**: an earlier draft of this section claimed
  `~/Pictures/PXL_20260802_013409485.mp4`, `_014130748.mp4`, `_013954971.mp4` were "the
  same session" as his 2026-08-02 photos and proposed frame-extracting them. That was
  wrong — checked and reverted. Those filenames encode the date/time in **UTC**
  (confirmed by cross-checking a Motion Photo whose JPEG EXIF gives local time while its
  filename encodes the same instant in UTC, a fixed +4h/EDT offset), while the
  `stomper_matches` STUDY-photo EXIF is already local. Converting: all three clips were
  shot **2026-08-01 ~21:34-21:41 local — the previous evening**, not his 2026-08-02
  session. Duration (47.77s) and the visibly clean/flat 1P stack in that footage line up
  with [[dr_lulu]]'s "47 s film-study clip" citation almost exactly — this is very likely
  her footage, not his. **No video of struktured's own session exists in `~/Pictures` as
  of this check** (nothing else in the tree carries a UTC timestamp matching his
  ~19:36-19:48 EDT / ~23:36-23:48 UTC window on 2026-08-02). The rotation-slip claim
  remains genuinely untested — confirming or refuting it needs either a fresh recording
  of his own session or the capture-card device once configured, not a re-scan of
  existing files.

## Why this matters to the project

- struktured is both the AI's designer and its most frequent human opponent — his losses
  are the project's clearest window into "does the shipped champion feel good to lose to,"
  separate from win-rate metrics. The topout-not-race-loss pattern in Game A is a UX signal
  (burial under time pressure), not a strength signal for the AI.
- The self-reported A/B rotation confusion, if confirmed on video, would be a concrete,
  narrow target for a coaching/practice mode or a single-rotate control option in TE —
  worth confirming before building anything, per [[test-defect-not-fix]] (simulate the
  fault, don't just assert the guard).
- Contrast with [[dr_lulu]] (household champion, undefeated, wins via timed pressure) gives
  the project two very different human baselines from the same hardware/cart family —
  useful for any opponent-aware VS evaluation work (task #15).

## Evidence

- `evidence/struktured_topout_gameA_20260802.jpg` — Game A's loss frame (16|03, red X).
- `evidence/struktured_gameB_freshrack_20260802.jpg` — Game B's fresh-rack opening (48|48).
- Full 16-photo set remains at `~/Pictures/stomper_matches/` (not all copied into the
  repo); a fuller placement-by-placement writeup of the same analysis lives at
  `experiments/player_styles/struktured.md` on the `copro-qa-harness` branch of this repo
  (task #36's first pass, done before this file's location/format was corrected to match
  [[dr_lulu]]'s convention).
- Capture-card video pending (device on hand per the task brief, not yet configured) —
  will convert his matches to (state, move) pairs per the player-data program
  (`dr-mario-player-data`) for quantitative profiling, same plan as dr_lulu.md.

## Caveats

n=16 stills covering 2 games from one evening (2026-08-02), plus 2 self-reported
set summaries (Set A 3-2, Set B 3-1) without photos of their own. All style claims
above are qualitative reads of footage or self-report, not decoded board data. The
1P=struktured attribution for the 2026-08-02 photos rests on the pre-existing
first-person self-reports tied to the same date and cart-build tags (982291ef / v4
fast+coldinit) — those tags don't appear anywhere in [[dr_lulu]]'s corpus (stomp180,
2026-08-01), so the two players' sessions don't overlap.

**Correction (2026-08-03)**: an earlier draft of this file carried a third record-table
row, "0-3 vs stomp180, tonight," sourced from the task-assignment message itself. Asked
team-lead directly — they have no such score in their own session data, and it isn't
a citable source. Removed per the "no orphan scores in dossiers" rule rather than
guessing at where it came from.
