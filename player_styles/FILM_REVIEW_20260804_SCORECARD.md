# Film review 2026-08-04 — FULL SCORECARD (blind pass vs the five self-reports)

Method: 11-agent workflow over the recorded set. 331 pills tracked at 60 fps
(m1=92, m2=47, m3=55, m4=137), tracker independently verified the hard way —
the verifier found 5/8 hand-checked pills mismatched, diagnosed five distinct
tracker bugs, patched, re-ran all windows, re-verified 9/9 clean plus 3
regression baselines. Analysis agents were given ZERO self-report content
(blind protocol held). Reports: `analysis/{rotations,latency,endgame,m1_verdict}.md`,
`recon/{proxy_results.json,VERDICT.md}` under
`~/projects/dr_mario_rl/tmp/film_review_20260804/`.

## The AI side (context for everything below)

**m3 suicide = H1 commit-path defect (~75% confidence), eval REFUTED as cause.**
Shipped-config proxy on the reconstructed death boards: search wanted cols
0/6/7 in 5 of 6 commits (margins 44–464); tape shows zero lateral movement in
4 of 6; final commit ranked 24/24, gap 1224. Weekend-default cross-check
agrees (so not a strand20 artifact). Non-monotonic timing rules out simple
"ran out of time" → structural pair-latch race (ORIENT early / COLUMN@DONE).
Action: audit whether the pair-latch fix is actually present in the Pocket
a0d5190f lineage.

## Scorecard

| # | Self-report | Verdict | Evidence |
|---|---|---|---|
| 1 | "~1/3 of my blunders are hitting A vs B" | **CONFIRMED in proportion, small in absolute terms** | A/B-class corrections (reversal 2 + overshoot 10) = 12 of 24 total correction events = 50% of measurable execution errors; but only ~3.6 per 100 pills. Both reversals sit in m2. Overshoots cost ~37 frames each — the expensive class. |
| 2 | "Not acting fast enough to do a reasonable thing" | **PARTIAL — true in the tail, not the bulk** | Reactive median 250 ms (fine); p90 512 ms; slowest = 1867 ms on a 3-cluster board (m1 p20), next-slowest cluster in m4's tight endgame stack. 23.6% of pills pre-planned. The stalls are real but rare, and they cluster exactly on optimizer-bait boards. |
| 3 | "Endgame speed panic — it gets way faster" | **OUTCOME CONFIRMED, MECHANISM REFUTED** | The equalization was real (clean board + 2-left at t=1360 → junk 19→51 in the last 90 s while Stomper dug out). But execution shows the OPPOSITE of panic: latency rises 150→233 ms (careful, not frantic), corrections are LOWEST in endgame (5.85/100), reversals 0.00%, straight-drops vanish, soft-drop hold lengthens. And the game does NOT objectively speed up — the AI's own interval lengthens too (1.54→2.13 s). The endgame problem is CLOSING TECHNIQUE (both final viruses already buried by t=1360; excavation under incoming volleys failed), not nerves. |
| 4 | "Over-setup tendency" | **NOT ADJUDICATED this pass** | Needs clear-event semantics (declined singles, structure holds). Circumstantial only: slowest decisions sit on multi-cluster boards; the m4 approach buried his own last two targets — consistent but not proof. Queued. |
| 5 | "Plain execution errors — messed-up button sequences" | **BOUNDED, not isolated** | Total correction events of ALL kinds: 7.25/100 pills — execution is largely clean. Lateral-direction fumbles need a per-frame lateral post-pass (tracker now supports it after the verifier's patches). Queued. |

## Match-account checks

- **m1 "I blundered quite a bit but I also made up for it"** → verdict **MIXED,
  ~60% EARNED by the AI**. His execution never degraded (latency flat
  252→246 ms, 0 panic-drops); 12 garbage volleys (26 cells) hit him, 58% in the
  final 90 s, and the decisive one re-buried a col-7 lane that had sat open for
  ~70 s — killed in the last 20 seconds. Correction: he ended at 3 viruses, not
  5 (earlier read was off by two).
- **m2 "clearly me just messing around"** → **SUPPORTED**: highest correction
  rate of the set (10.64/100) and the only two reversal events on the whole tape.
- **m4 structural claim (added mid-review): "my board was much cleaner; panic
  equalized it"** → cleanliness CONFIRMED decisively (junk 18 vs 65, mean
  height 4.5 vs 10.9, stranded 2 vs 16 at t=1360); the equalization mechanism
  refined per #3 above.

## Biggest divergence between self-perception and tape

He believes his endgame collapses into sloppy panic. The tape shows a player
who gets SLOWER and CLEANER under endgame pressure and still can't close —
because the targets are buried and the close-out plan (excavation sequencing
under fire) is the missing skill, and because the approach phase buries its
own last targets. Training implication: drill closing sequences (last-2-virus
excavation lines), not nerve control. His instinct that the AI is
structurally strongest exactly then (fixed-latency, panic-immune) is correct.

## Player refinement post-scorecard (2026-08-04, user commentary)

"If you make just one endgame blunder it really messes with your psyche (like
closing out the one good option to clear the last viruses)." — This reconciles
the #3 verdict cleanly: the tape's m4 shows exactly that irreversible-blunder
class (own last targets sealed by t=1360), and the post-blunder signature is
TILT-AS-OVERCAUTION (latency up, corrections down, straight-drops gone), not
flailing. The subjective "it gets way faster" = time pressure felt during
frozen deliberation, not objective game speed (AI interval lengthened too).
Training target confirmed: last-2-virus closing lines + a pre-commit habit of
checking "does this placement seal my only clear path?"
