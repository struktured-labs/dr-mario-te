# dr. lulu — player style profile

*DRMC handle: **dr. lulu***
*First human ever to KO the Combo Stomper. Reigning household champion.*

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
