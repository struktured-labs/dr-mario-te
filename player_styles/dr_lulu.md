# dr. lulu — player style profile

*DRMC handle: **dr. lulu***
*First human ever to KO the Combo Stomper. Reigning household champion.*

## Style at a glance

- **The apex opponent: undefeated against every AI build** — full Stomper series won, then 3-0 over the strand180_20 champion (2026-08-08, first captured session).
- **Low, flat fortress**: keeps her stack <=~4 rows through the midgame; gives incoming garbage nothing tall to finish.
- **Timed, relentless small-ball pressure**: converts 4-6-cell clears to volleys **40.8%** (fitted, n=157 — highest measured in the household; struktured 32.1%), tight 21.9s cadence, smaller volleys — a steady drip aimed at the construction window.
- **Wins by harvesting AI edge cases, not out-racing the search**: 2 of 3 night-two wins were the AI dying while AHEAD on viruses.
- **Known loss mode**: letting the scaffold complete — the one time the AI beat her was a 25-07 avalanche KO.

## Record vs the AI (running)

| opponent | result | notes |
|---|---|---|
| Combo Stomper (stomp180, tucks+chain, Pocket docked, L11 MED, human P1 vs copro P2) | **series: dr. lulu UNDEFEATED — the Stomper has never won a match; its best is a 3–2 loss** | includes ≥1 KO of the AI — the first topout in Stomper history (0 in 4,000 lab matches). Both AI wins were crush-outs; user's live call on game 5: "could have been 3-2 tho" |
| strand180_20 champion (core a0d5190f + v4-coldinit cart 24dcd9dc, Pocket docked, L11 MED, 2026-08-08 scouting session) | **dr. lulu 3–0** | first FULLY CAPTURED session (1080p60). 2 of 3 wins were AI dies-while-ahead topouts — she harvested the known edge cases, she did not out-race the search. See "Night two" below |

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

## Night two (2026-08-08) — scouting session, first fully captured

Deliberate data-collection session: she played the current champion (strand180_20 core
a0d5190f, v4-coldinit cart — v6-boardhold benched for a live flicker defect) so her play
could be recorded. **dr. lulu 3–0.** Capture:
`~/Videos/drmario_sessions/20260808_162820_dr_lulu.mkv` (genuine Matroska, 1080p60,
verified by ffprobe before arming — the Aug-4 mkv-named-MP4 trap is fixed at the OBS
config level).

### The three losses, from the film (crown-counter boundaries, exact)

| match | ends | virus (her \| AI) | loss mode |
|---|---|---|---|
| m1 | 4:20 | 14 \| **06** | **dies-ahead** — AI up 8, twin-column tower to the bottle neck, topped out |
| m2 | 9:09 | 05 \| **02** | **dies-ahead** — AI up 3, four-column comb vs her near-empty board |
| m3 | 12:19 | **02** \| 06 | race loss — she out-cleared it; final frame shows a queued volley incoming; owner's read: the AI could have untangled its endgame faster (declined-clear/pair-latch family) |

**2 of 3 wins are dies-while-ahead topouts — the champion's known 82x pressured failure
mode, now confirmed on silicon against the target human.** The strategic read: she is not
beating the search head-to-head; she is harvesting its edge cases (tower geometry under
timed pressure, late decisions, slow endgame conversion). Owner's couch observations,
same session: (1) time-budget failures — visibly late moves; (2) pills wasted clearing
dangerous columns; (3) nonsensical vertical drops (v4 HAS the tempo retune
DRMINTHINK=12/DRSLAM_KOPEN=32, so these are genuine decision latency, not the solved
slam-gate regression). Also observed: one clean last-moment horizontal snap into the
rightmost column — a natural slam-tuck from the nav driver (this cart has NO tuck
executor), proof the input pipeline can execute late rotations on silicon.

### Quantitative profile (first fitted model — replaces the qualitative-only read)

Fitted from all 3 matches by `refit_dr_lulu.py`
(`eval47/results/dr_lulu_20260808_fit.json` + `_fit_report.md`): 59 volleys, 175 clears.

| metric | struktured 20260804 | dr. lulu 20260808 |
|---|---|---|
| volley_size_mean | 2.541 | 2.390 |
| inter_volley_gap_mean_s | 22.70 | 21.85 |
| p(volley \| 4–6-cell clear) | 32.1% (n=156) | **40.8%** (n=157) |
| p(volley \| 7–10-cell clear) | 74.1% (n=27) | 56.2% (n=16) |

Signature: **she converts bread-and-butter clears into pressure ~27% more often than the
model the champion was tuned against**, with a slightly tighter volley cadence and
smaller volleys — steady drip, not spikes. Consistent with the night-one hypothesis
(banks doubles, times strikes at the construction window). Caveats: 3 matches, no
event-CSV annotations (lock_crosscheck 0/59), single level/speed (L11 MED), v4 cart only.
Same-night rig run (n=120, champion under HER fitted pressure) was launched immediately —
dies-ahead number lands in `eval47/tmp/dr_lulu_20260808_refit.log`.

### AI-side (P2) frame-level pass, m3 — one result, two metrics BLOCKED (2026-08-08)

Ran the standing tracker pipeline against the **AI side** of night two's m3 window
(555-739 s), the window the owner flagged as "could have untangled faster".

**PREREQUISITE THAT DID NOT EXIST.** The session dir held only `frames/` (1 fps) — no
`p1/p2_60fps` crops, no `events/`. Generated the P2 60 fps crops myself for m1/m2/m3
(40,980 frames, origin (1088,348) 440x704 = `refit_dr_lulu.py`'s derived P2 mirror) and
wrote `experiments/eval47/film_20260808/tracker_p2.py`, which reuses every pure function
from the 20260804 `tracker.py` unchanged, exactly as `tracker_p2_death.py` does.
Crop geometry is VERIFIED, not assumed: classifying a full frame with the full-frame P2
grid and its crop with the crop-local grid give identical boards on 3 sampled frames, and
an origin wrong by 8 px is detected.

**✅ THE LAST-MOMENT SNAP INTO THE RIGHTMOST COLUMN — FOUND AND TIMESTAMPED.**

| | |
|---|---|
| when | **t = 596.35 s** absolute (m3 + 41.35 s), frame 2481 of the m3 60 fps crop |
| what | horizontal (HF) capsule, **lateral col 5 → 6** so it occupies cols **6-7** |
| how late | **13 frames = 0.22 s before lock** |
| lands | (8,6)+(8,7), colours B-R |

Visually confirmed frame-by-frame (f2470 → f2494). This is a genuine late lateral on
silicon from a cart with **no tuck executor** — the nav driver's own steering, i.e. the
input pipeline can execute a last-moment horizontal placement. Three further late moves
reach col 7 in m3 (t = 645.05, 681.90, 689.58 s) but all three are **vertical** capsules
entering the column, not horizontal snaps; 7 clean pills made any lateral reaching col 7.

**❌ DECLINED-CLEAR RATE AND PILLS-PER-CLEAR: NOT MEASURED — the instrument fails its
control on this footage.** Two independent failures, both quantified before I stopped:

1. **19.4 % of tracked P2 pills (18/93) "lock" at the spawn cell (0,3)+(0,4)** with a
   0-2-frame lifetime — i.e. the tracker never followed the piece. The same tracker on the
   20260804 corpus gives **0.0 / 0.0 / 3.6 / 0.0 %** across P1 m1-m4 and 6.2 % on the P2
   death clip. The failures are not uniform: **33-50 % in the first 80 s of the window,
   3-4 % after t≈637 s**, so excluding them would bias exactly the early-window behaviour
   the owner asked about.
2. **The classifier's virus count disagrees with the game's own on-screen counter.** At
   t = 567 s the VIRUS box reads **41** for P2; the classifier finds **28** virus cells —
   a ~30 % undercount. Declined-clear requires engine-verified board reconstruction, and a
   board that mis-reads a third of its viruses cannot support it.

Per the metric battery's own rule — *a metric that can't fail its control is noise* — no
declined-clear or pills-per-clear number is published here. What is needed first is a
P2-side tracker validated against the on-screen VIRUS counter as ground truth (it is
readable every frame and is the free control this pipeline has never used). The crops are
on disk (`eval47/tmp/dr_lulu_20260808/p2_60fps/`, gitignored) so the re-run costs no
re-extraction.

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
