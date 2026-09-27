# RESULT (2026-09-25, Claude solo): STALL BREAKER screen: ALL FIVE ARMS FAIL. No holdout.
Pre-reg: `PREREG_STALLBREAK1.md`. Base = fw540 (CHAIN540 brain). Paired seeds 36734.. step 2.

| arm | gate-b tap-out | paired Δ vs fw540 [95% CI] | stall% | VS win (177 s, δ 2.65) | paired Δ VS [95% CI] | verdict |
|---|---|---|---|---|---|---|
| fw540 (base) | 2.33% | — | 1.00 | 95.3% | — | |
| sb_chain0 | 3.50% | +1.17 [−0.17, +2.67] | 0.83 | 95.7% | +0.3 [−1.7, +2.3] | FAIL primary |
| sb_spawn | 2.67% | +0.33 [−0.67, +1.33] | 1.33 | 95.0% | −0.3 [−1.7, +1.0] | FAIL primary |
| sb_virus | 2.50% | +0.17 [−0.67, +1.00] | 1.33 | 95.0% | −0.3 [−2.0, +1.3] | FAIL primary |
| sb_all | 3.17% | +0.83 [−0.33, +2.00] | 1.00 | 92.3% | **−3.0 [−5.0, −1.0]** | FAIL both |
| sb_all_early | 3.67% | +1.33 [−0.33, +3.00] | 1.00 | 91.3% | **−4.0 [−7.0, −1.0]** | FAIL both |

Gate b n=600 per arm, VS n=300. Bar: tap-out Δ < 0 with the CI excluding 0. No arm has a negative point
estimate. The combined arms also cost VS wins beyond the 2 pp guard.

## Why: the trigger misses 6/14 deaths, and where it fires dig does not rescue (`sb1_trigger_diag.py` → `sb1_trigger_diag.json`)
Every fw540 tap-out (14/600) was replayed through `StallBreakerDecider` with zero dig effect. All 14 are
byte-identical to the banked rows, so the replay is valid. It logs whether dig *would* have fired:
- **6/14 deaths are invisible to the trigger.** The spawn lane is already 13–15 rows while viruses are
  still clearing, so the "placements since a virus cleared" counter keeps resetting (max ≤ 7 < S=8).
  These are fast deaths (50–75 pills, 8–26 viruses left).
- **8/14 do trigger, often for a long time.** In 6 of the 8, the dig condition held for 20–86 pills
  before the death (the other two: 4 and 5 pills). The longest are endgames with 1–3 viruses left
  (stall 54/62). So the trigger does fire there, and switching dig on in those stretches still does not
  lower tap-outs on average.
- **The dig arms churn outcomes.** Each fixes some fw540 deaths and causes more new ones:
  chain0 6 fixed / 13 new · spawn 3/5 · virus 3/4 · all 5/10 · all_early 10/18. The harder the
  intervention, the more churn in *both* directions, which is the signature of perturbing a chaotic
  trajectory, not of a systematic fix.

## What this does and does not say
- It does **not** refute "spawn-lane towers kill". The spawn lane is 14–15 rows at death in all 14.
  What fails is **stall-gated** intervention: the danger builds while the bot is making progress.
- The couch G2 death (36 s with no virus cleared, tower standing) matches the *triggering* class. The
  screen says a dig mode switched on at that point does not rescue the game on average.
- Prior art to check before any follow-up: `dr-mario-endgame-is-a-dig-problem` (burial pricing, run 17),
  `dr-mario-spawnplug-verdict` (every topout is a spawn plug; no quick AI fix), maxh24 CLOSED.
  A spawn-height-only (ungated) penalty is close to experiments already closed there, so it should not be
  re-screened without a reason those closures don't cover.

## Provenance
`gateb/sb_*_N.jsonl`, `vsrace4/sb_*_l6.0_N.jsonl`; analyzer `analyze_sb1.py` (keys on each row's own
`arm` label, because the `sb_all_*` glob also matches `sb_all_early_*`).
