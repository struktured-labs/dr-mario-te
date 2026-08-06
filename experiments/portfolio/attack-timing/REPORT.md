# attack-timing: does holding a ready clear for a better moment beat cashing in immediately?

**Task #15-adjacent (opponent-aware VS evaluation).** Verdict: **DEAD.**

## Hypothesis (falsifiable)

The champion decide path (`cascade_stranded_x.StrandedChainD3Decider`, `w_chain=180 ws=20` on
`fast_rtl_x.variant("winner")` — h2h_vs.py's `strand180_20` arm, the `NES_stomper180s20` build
shipped to silicon per memory `dr-mario-eval47-stranded-win`) is purely greedy about attack
**timing**: whenever its top move fires a ROM-true attack (comboCounter sum >= 2, `rom_attack_rule`),
it plays it immediately, with no notion of the opponent's board state. Humans hold a completed
clear and cash it in when the opponent's stack is tall and their spawn lane is congested. **This
could be false**: if a decider that holds a ready clear for up to `K` pills (only while the
opponent's tallest column is below a height `threshold`) never beats `K=0` (the unmodified
champion) in paired VS play at any `(threshold, K)`, the champion's greedy timing is already
optimal against this opponent class, and that is a real, useful negative.

## Method

**Champion under test**: `cascade_stranded_x.StrandedChainD3Decider` (chain180 root reward +
g_stranded ws=20 stranded-half cost), built via `fast_rtl_x.variant("winner")` — identical
weights/arm to h2h_vs.py's `strand180_20`.

**Harness**: `tmp/vs_aware/vs_harness.py::play_match` — THE sanctioned ROM-true VS loop (per its
own docstring: "the only sanctioned match loop"). Real NES pill stream (`NesPillSource`), L11,
max_pills=300, garbage ON. Deciders are opponent-aware, `(board, cur, nxt, opp_board) -> action`.

**HoldingDecider** (`hold_decider.py`) wraps the champion, unmodified:
1. Ask the champion for its top action `a0`.
2. Determine whether `a0` fires a ROM-true attack using the **same** call chain
   `vs_harness.probe_placement` uses — `attack.lines_per_step` (destructive resolve on a board
   clone) -> `rom_attack_rule.combo_from_cascade` -> `rom_attack_rule.attack_size` >=
   `ATTACK_SIZE_MIN`. (`probe_placement` itself needs an `env` object for `_decode`, which
   deciders don't get; `_decode_local` is a byte-identical copy of `FaithfulDrMarioEnv._decode`,
   not a reimplementation of the attack rule.)
3. If `a0` doesn't attack, or the opponent's tallest column (`opp_board.column_heights().max()`,
   same units as `terms47.g_tower`'s height convention) is already `>= threshold`, or the hold
   budget for this streak is exhausted (`K` holds used): **cash in** — play `a0`.
4. Otherwise **hold**: enumerate the up to 32 legal root actions with the champion's own
   first-ply leaf scorer (`cascade_chain_x._leaf_chain`, same `variant("winner")` weights — the
   literal primitive the champion's own root loop calls, imported not reimplemented), keep only
   non-attacking ones, and play the highest-leaf-value one. If none exists, cash in.

This is a first-ply-greedy hold policy (not a full re-run of the d3 search on the held
alternative) — deliberately cheap, matching the "cheapest kill first" brief.

**Reused, not rewritten**: `vs_harness.play_match`, `rom_attack_rule.{combo_from_cascade,
attack_size, ATTACK_SIZE_MIN}`, `attack.lines_per_step`, `cascade_chain_x.{_base_scan,
_leaf_chain}`, `cascade_stranded_x.StrandedChainD3Decider`, `fast_rtl_x.variant`,
`h2h_vs.{boot_ci, attacks_sent}` for the paired-seed statistics.

**Stats**: h2h_vs.py's convention exactly — every seed played both sides (side-swap), scored
`s in {0, 0.5, 1}` per seed, percentile bootstrap CI over seeds (10000 iters), and the
"decisive" fraction (seeds where the pair did NOT score exactly 0.5 — the outcome the arm being
identical to itself scores every time by construction, so a non-0.5 seed is one where the knob
changed the outcome).

**Thresholds swept**: 8 and 11, chosen from this project's own eval vocabulary — `H0=8` is where
`terms47.g_tower`'s height tax starts (bottom-half territory), 11 is near the top-danger regime
(`maxh=12`, `toprisk` terms). Both are in the same units as `column_heights()`.

## Cheapest-kill pass: n=20 seeds, 6 arms

seeds 500-519, side-swapped (40 matches/arm), `--workers 4`.

| threshold | K | winrate | 95% CI | margin | margin CI | held/match | atk cand v ref | moved |
|---|---|---|---|---|---|---|---|---|
| 8 | 1 | 47.5% | [42.5%, 50.0%] | -0.40 | [-0.95, +0.05] | 1.20 | 13.32 v 14.12 | 5% |
| 8 | 2 | 50.0% | [42.5%, 57.5%] | -0.28 | [-1.05, +0.53] | 1.65 | 13.47 v 14.45 | 10% |
| 8 | 3 | 47.5% | [42.5%, 50.0%] | -0.60 | [-1.18, -0.12] | 1.90 | 13.35 v 14.30 | 5% |
| 11 | 1 | 37.5% | [22.5%, 52.5%] | -3.12 | [-5.50, -0.88] | 7.50 | 9.25 v 13.30 | 55% |
| 11 | 2 | 40.0% | [27.5%, 52.5%] | -4.10 | [-6.85, -1.50] | 8.80 | 8.57 v 12.40 | 40% |
| 11 | 3 | 37.5% | [25.0%, 50.0%] | -4.28 | [-7.10, -1.57] | 9.40 | 9.18 v 13.43 | 45% |

**Every single one of the 6 settings is <= 50% winrate.** `K=0` (the unmodified champion vs
itself) is the analytic 50%-by-construction baseline (h2h_vs.py's own documented sanity fact) —
not run, nothing to measure. None of the 6 tested holding policies ever beats it. This alone
satisfies the task's kill criterion.

There is also a clean, monotonic **dose-response in the harmful direction**: at threshold=8 the
opponent is already tall most of the time an attack fires (so the hold rarely activates —
held/match 1.2-1.9, `vuln_cash` dominates `forced_cash`) and the effect is small and mostly not
significant. At threshold=11 the hold activates far more (held/match 7.5-9.4) and the effect
becomes large and significant (margin CIs entirely below zero in all 3 K's), and the holder's
total attacks sent drops sharply (`atk_cand` ~8.6-9.3 vs `atk_ref` ~12.4-13.4) — **holding
doesn't re-time damage, it suppresses it**. More license to hold makes the champion worse, not
better.

## Confirmatory run: threshold=11, K=1, n=60 (the mildest of the negative arms)

seeds 500-559, side-swapped (120 matches), `--workers 4`, 558s wall.

```
thr=11  K=1  winrate  28.3%  95% CI [20.8%, 35.8%]  margin -4.43 [-5.59,-3.25]
n=60  held/match 7.62  vuln_cash 454 forced_cash 122  atk 9.67 v 13.57  moved 53%
of decisive seeds, the holder won only 9.4%
```

At n=60 the effect is not just present but **sharper**: winrate fell from 37.5% (n=20) to 28.3%
(n=60), and the margin CI `[-5.59, -3.25]` is tight and nowhere near zero. Of the 53% of seeds
the hold policy actually moved, it **won only 9.4% of them** — i.e. when holding changes the
outcome at all, it is losing the outcome. This is the mildest of the four significantly-negative
arms (K=1 is the smallest hold budget of the threshold=11 group); the other three (K=2, K=3, and
threshold=8/K=3) are corroborating at n=20 and were not re-run at n=60 because widening a
confirmed-harmful arm would only spend compute without changing the direction of the answer —
consistent with "if it dies, report the negative and STOP."

## Mechanism: why holding hurts instead of helping

`atk_cand` (holder's total attacks sent per match) is consistently **lower** than `atk_ref` (the
plain champion's) across every threshold=11 arm — roughly 9 vs 13-14, a ~30% reduction in total
garbage delivered. The champion's own eval (`terms47.g_stranded`, `w_chain`, buried/setup/matched
terms) already prices board quality highly; forcing it onto a first-ply-greedy non-attacking
alternative for up to `K` pills lets the board drift — new pills fall, the deferred structure can
get buried, occluded, or overtaken by a bigger but differently-shaped opportunity the champion
would rather take instead once it's finally allowed to cash in. The "held" clear is not a fixed
asset waiting in a queue; it is a moving target on a board that keeps changing underneath it, and
the champion's own greedy choice at each pill is already tuned to not waste tempo. The net effect
is fewer total attacks landed, not the same attacks landed at a better moment — the mechanism the
hypothesis proposed (bank the clear, wait for vulnerability, cash in bigger/better-timed) does not
survive contact with a real, continuously-evolving board.

## What this does and doesn't settle

- Settled: for this champion, this attack-detection rule, and first-ply-greedy alternative
  selection, delayed cashing-in **never** helps and reliably **hurts**, growing worse the more
  license (threshold, K) it is given. Four of six cheap-pass arms already had margin CIs
  excluding zero at n=20; the confirmatory n=60 run on the mildest of them tightened the CI
  further in the same direction.
- Not settled: whether a **smarter** hold-alternative selector (full d3 value instead of
  first-ply leaf) or a different vulnerability signal (spawn-lane congestion specifically,
  rather than max column height; or the BURSTY v1.1 pressure model's opponent-state features)
  could recover a positive effect. Given the mechanism above — the held structure decaying
  under a moving board, not a ranking-quality problem — this looks unlikely to flip the sign,
  but it is a genuinely different, cheaper-to-test hypothesis than the one killed here and is
  not addressed by this result.
- Related but distinct: `REACTIVE_MODE_RESULTS.md` (garbage-reactive defensive reweighting,
  boost `ws` after receiving garbage) is a different mechanism (defense, not attack timing) and
  was also a no-ship — both results point the same general direction for this champion: ad hoc
  temporary deviations from its tuned greedy policy tend to cost more than they buy.

## Files

| file | what |
|---|---|
| `hold_decider.py` | `HoldingDecider`, `would_attack`, `best_nonattacking`, `make_champion`/`make_holder` |
| `sweep.py` | paired seed-swap VS runner (h2h_vs.py stats reused), `run_arm`/CLI sweep over threshold x K |
| `smoke.py` | single-match sanity check (holder vs champion, prints hold-decision stats) |
| `sweep_cheap_n20.json` | 6-arm n=20 cheap-kill pass, machine-readable |
| `sweep_confirm_thr11_K1_n60.json` | n=60 confirmatory run on threshold=11, K=1 |
| `log/*.log` | raw run logs |

Reproduce:
```bash
PY=/home/struktured/projects/dr_mario_rl/tmp/venv/bin/python
$PY sweep.py --thresholds 8,11 --Ks 1,2,3 --seed0 500 --seeds 20 --workers 4 --out sweep_cheap_n20.json
$PY sweep.py --thresholds 11 --Ks 1 --seed0 500 --seeds 60 --workers 4 --out sweep_confirm_thr11_K1_n60.json
```
