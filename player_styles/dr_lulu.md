# dr. lulu — player style profile

*DRMC handle: **dr. lulu***
*First human ever to KO the Combo Stomper. Reigning household champion.*

## Record vs the AI (as of 2026-08-01, night one)

| opponent | result | notes |
|---|---|---|
| Combo Stomper (stomp180, tucks+chain, Pocket docked, L11 MED, human P1 vs copro P2) | **series: dr. lulu UNDEFEATED — the Stomper has never won a match; its best is a 3–2 loss** | includes ≥1 KO of the AI — the first topout in Stomper history (0 in 4,000 lab matches). Both AI wins were crush-outs; user's live call on game 5: "could have been 3-2 tho" |

The AI's single win was a textbook combo-stomp: KO'd her from a 25–07 virus lead
(photo evidence). When it beat her, it beat her in-character; when she beat it, she
beat it in ways the lab never produced.

## Observed style (film study, n=4 matches — qualitative)

- **Low, flat stack discipline.** Keeps her stack ≤ ~4 rows through the midgame.
  Denies incoming garbage anything tall to top off, and keeps her own topout risk
  near zero. This is the strongest anti-Stomper posture we know of, arrived at either
  deliberately or instinctively on her first night against it.
- **Patient, steady clear tempo.** In the 47 s film-study clip she cleared 4 viruses to
  the Stomper's 2 while it was mid-construction — she out-races it during exactly the
  phase it concedes tempo.
- **Times her pressure.** Working hypothesis for the KO: she banks doubles and releases
  garbage while the Stomper's scaffold is tall — a *timed* strike at its most fragile
  window. No lab opponent times attacks (they send on their own schedule, blind); this
  is the capability our harness does not contain.
- **Comeback capability.** Beat it after it was ahead at least once (photo series).
  Does not tilt when trailing.
- **Known loss mode.** When she allows the scaffold to complete — or spends too long
  banking rather than pressuring — the avalanche converts and buries her from ahead
  (the 25–07 KO). Her games are won or lost in the construction window.

## Why this matters to the project

- The loss autopsy (task #32) concluded the Stomper "never dies — it only loses
  footraces." That held for 400 AI-vs-AI losses across two levels. **dr. lulu falsified the
  universal reading in one evening**: the claim is true of untimed opponents only.
- The construction-window vulnerability she exploits is the precise complement of the
  strategy's strength. Any future opponent-aware work (task #15) should model *attack
  timing*, not just attack volume — she is the existence proof that timing beats volume.
- **"Beat dr. lulu" is a better north star than any win rate vs our own bots.** She is the
  strongest opponent the champion has faced, and the only one with a winning record.

## Evidence

- `experiments/rtl_chain/field_evidence_wife_KO_20260801.pdf` — the first Stomper KO
  (X on P2's bottle, virus dance, 10|10 board state).
- Photo archive: 205-file series (Pixel, 2026-08-01 evening) + W-screen burst
  (25–07 KO, three crowns) + 47 s film-study clip. Ingested from Google Photos zips.
- Capture-card video pending (device on hand, not yet configured) — will convert her
  matches to (state,move) pairs per the player-data program for quantitative profiling.

## Caveats

n=4 matches, one evening, one level/speed (L11 MED), Pocket dock input path. All style
claims are qualitative reads of footage, not yet decoded board data. Update this file
as the sample grows — especially once capture-card recordings allow real
attack-timing measurements.

## Night-one closing state (2026-08-01)

The final match went the distance — **dr. lulu won it 3–2**. The decider itself went
uncaptured (citation: the user's testimony, same night; the capture card exists and was
not yet configured — never again). The Stomper's two crowns in that match are documented
(`evidence/stomper_stage_clear_2crowns_20260801.jpg`, STAGE CLEAR at VIRUS 02|00 — it
out-raced her to a full clear). **Night one final: dr. lulu undefeated, every completed
match won, including the 3–2 thriller.** The machine's consolation: it made the household
champion go five games.

## Execution-consistency addendum (frame-level film study, 2026-08-03)

This is a first, small down payment on the "capture-card video... convert to (state,move)
pairs" plan above, done early using found footage rather than the capture card: the
`~/Pictures/PXL_20260802_013409485.mp4` (47.77s) and `PXL_20260802_013954971.mp4` (93.67s)
clips are two of the videos from her night-one session (see provenance note below), both
120fps slow-motion recordings of the Pocket screen, legible enough after cropping to the
1P playfield to read individual pill-half colors frame by frame.

**Method**: for each spawn, read the 2-color preview icon's left/right order, then track
that specific pill through its descent to see whether it locked horizontal (order
necessarily unchanged — no ambiguity possible) or vertical (top/bottom order is only
meaningful, and only readable, when the two halves are different colors).

**Result**: one fully unambiguous example, captured at 15fps around t≈5s of the first
clip. Preview showed pink (left) / blue (right); the piece rotated to vertical during
its descent and locked as pink (top) / blue (bottom) — an exact, unflipped translation
of the preview order. No inconsistent (flipped) placement was confidently identified in
either clip.

**Honest limits on this result**: n=1 is not a rate, it's a single data point. Roughly
40 additional seconds of footage were traced across 5 more high-frame-rate windows in
both clips without producing a second equally-confident read — about half the pill pairs
sampled happened to be same-color (pink|pink, yellow|yellow, light-blue|light-blue),
which can't test rotation handedness at all since both halves look identical regardless
of orientation, and several other candidates were lost to motion blur during the
rotation animation itself, fast piece-cycling at this level/speed, or camera jostle.
This isn't a claim about her execution accuracy — it's a claim that the pipeline works
(a clean spawn-to-lock transition is readable) and that the one clean trial available
showed no flip. A real rate needs either more, steadier footage of two-different-color
drops, or the capture card's cleaner signal.

**Provenance note**: these two clips were originally checked while investigating
struktured's self-reported A/B rotation confusion (see `struktured.md`), on the mistaken
assumption — from filename date alone — that they were his footage. They're actually
hers: embedded video `creation_time` is UTC, and converting it (this whole corpus's
JPEG EXIF is local, +4h/EDT) places both clips at 2026-08-01 ~21:34-21:41 local, matching
this file's night-one window; the first clip's 47.77s duration also matches the "47 s
film-study clip" already cited above almost exactly. Struktured's own rotation-slip
question remains open and untested — no footage of his session exists yet.
