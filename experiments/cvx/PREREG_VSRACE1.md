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
