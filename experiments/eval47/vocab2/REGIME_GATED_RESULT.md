# Historical regime-gated `d_spawn_h` screen — no candidate graduates

Run 2026-08-11 under `PREREG_REGIME_GATED.md`, which was sealed on 2026-08-09.
This is the historical compact/cap-one policy and drip-pressure harness, not the
exact shipped-v8 policy and not the Lulu model.

## Gates

- 480/480 base games reproduced the frozen census exactly (zero result, pill,
  or viruses-left mismatches).
- Realised duty was 20.3% for K=2 and 40.2% for K=4, below the frozen 54% line
  at which the purported gate would collapse into the previously failed
  mostly-on intervention.
- The run completed all 2,400 games.  RNG, sampled seeds, raw seed lists, and
  all arm results are banked in `screen_regime_result.json` (SHA-256
  `bc44d7a0338c782b6e9d79d844840b57041ee7c7c51b49aed61bbe5fb663955c`).

## Result

Negative population net is beneficial.  None of the four registered arms had
a negative point estimate, so none graduates under the frozen decision rule.

| arm | duty | topout rescues / 240 | clear breakages / 240 | dies-ahead | games changed / 480 | population bad ends / 40k (95% bootstrap CI) |
|---|---:|---:|---:|---:|---:|---:|
| K2, wq30 | 20.3% | 105 | 5 | 234 -> 108 | 218 | **+406** [-227, +1,125] |
| K2, wq60 | 20.3% | 136 | 8 | 234 -> 77 | 261 | **+768** [-31, +1,712] |
| K4, wq30 | 40.2% | 140 | 7 | 234 -> 73 | 269 | **+594** [-168, +1,527] |
| K4, wq60 | 40.2% | 148 | 5 | 234 -> 60 | 302 | **+247** [-393, +1,005] |

The mechanism is useful but not deployable in this form: post-garbage spawn-lane
penalties rescue many selected historical topouts and reduce dies-ahead, while
changing 45.4%--62.9% of all sampled game outcomes/traces.  At the registered
population ratio, only 5--8 broken clears erase 105--148 rescued topouts.  This
is another direct measurement of the clean-game preservation problem, not
evidence that dies-ahead is immovable.

## Authority and limitation

The preregistration's literal outcome is **NO_GRADUATE_ALL_FOUR_POINT_WORSE**.
Do not promote any arm to the Lulu robustness screen and do not sweep more K/wq
doses from this result.

Do not use this run to close all sensor-directed or exact-v8 interventions.  It
predates the 2026-08-10 design law requiring a dose-matched, label-blind null,
and contains no such null; every bootstrap CI also includes zero.  It can reject
these four exact historical candidates against their base, but it cannot
attribute their churn to the direction carried by `d_spawn_h`, nor can its
compact-policy result be silently transferred to the cartridge-v8 policy.
