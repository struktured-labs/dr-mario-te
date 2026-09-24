# PRE-REG (2026-09-24 AT LAUNCH, Claude solo): VS-RACE endpoint, first run
Spec: lulu-147 VS_RACE_ENDPOINT.md (2026-08-21). Built as `vs_race.py`, HARNESS_REV
`vsrace-r1 / vsharness-r1 / rom-attack-2026-08-01 (complete)`.
Champion C = VsPolicy (pinned path, ws=0) on a faithful board, ROM-true attack (cascade-summed combo,
2/3/4 tiles) and receive (merged store, released after C's placement, columns incl. 0/4, counter-attack).
Human L = pace T_L0 ~ lognormal(median M, sigma 0.15) per seed (arm-independent quantile) + Poisson
volleys lam/min (sizes 2:73% 3:17% 4:10%, Hartford fit) + damage delta s per tile C lands (ASSUMED).
C clock = cart pace: 45 + 2*fall_rows + 40*cascade_steps frames (clean mean 86.1 f vs measured 86.2 f).
Human pace anchor (NEW, this run): Hartford L11-class prelims, n=12 clears, median 177 s (p10 145, p90 209);
dr. lulu's one filmed race win ~190 s.
Arms: holes80, winner, kc40 (winner+k_clock40), h80kc20. lam in {1.2, 3.3, 6.0}/min. n=300 seeds,
36734.. step 2 (DECLARED REUSE = gate (b) block; paired with it). L11, cap 600.
PRIMARY: win rate vs a human of median pace 177 s at lam=3.3, delta=2.0, seed-clustered bootstrap CI;
paired arm differences. SECONDARY (always reported, never folded in): win_race/loss_race/loss_kill/
loss_cap counts; break-even human pace per arm (M where win rate = 50%); sensitivity over delta
{0,1,2,3} and sigma {0.10,0.25}. Scoring per spec: survive-but-slower and cap are LOSSES.
This is a MEASUREMENT of the existing builds against a human-shaped racer — the instrument the program
has lacked since 2026-08-21 — not a candidate search.

## AMENDMENT 1b (registered 2026-09-24 before any run-1 result was read): Combo Stomper arms
`vs_race.py` gained a board-decider path for the Stomper lineage (h2h_vs.py `chain<N>` arms:
`cascade_chain_x.ChainRewardD3Decider`, fixpoint cascade physics, `imm += w_chain*(chain-1)`).
The edit leaves the VsPolicy path bit-identical (same decide call), so in-flight run-1 workers are
unaffected. Arms: chain180 (the shipped Stomper, winner trunk), h80chain180 (holes80 trunk + Stomper
chain reward — the VS-native candidate), h80chain0 (same fixpoint decider, no chain reward — isolates
the chain term). Same lam grid, seeds, n=300, scoring. Smoke: chain arms send ~2-3x the tiles.
PRIMARY for 1b: h80chain180 vs holes80 win rate vs a 177-s human at lam=3.3, delta=2 (paired);
SECONDARY: h80chain180 vs h80chain0 (chain term alone), loss_kill counts (does attacking cost survival?).

## DELTA FIT (2026-09-24, from tape; recorded as SECONDARY — primary stays delta=2.0 as registered)
Hartford Top-8, 4fps garbage arrivals x 1fps virus counters: after a hit, experts clear 1.75 viruses
in 20 s vs 2.52 in matched same-side same-stage windows (n=181 hits, 2.29 tiles/hit) =>
**delta = 2.65 s per tile, 95% bootstrap [0.95, 4.13]** (`tmp/tourney/delta_fit.json`). Observational
(matched on side + virus stage); pre-registered delta=2.0 lies inside the CI. Report both.

## HOLDOUT (registered 2026-09-24 ~00:45Z, before run 1/1b full results were read; only a partial
holes80 table had been seen): replication on Hetzner rbm-train-2 (exactness gate PASSED: identical
md5 over full game timelines for holes80 + h80chain180, seed 36734, local vs remote).
All 7 arms, lam=3.3 only, seeds 40134.. step 2, n=200 (DECLARED REUSE, disjoint from run 1's
36734-37332). Same scoring. PURPOSE: any run-1/1b ranking claim at the primary cell must replicate
here in sign; a candidate is only "better than holes80" if its paired CI excludes 0 in BOTH blocks.
