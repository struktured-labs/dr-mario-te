# PREREG TAPOUT (2026-10-13): what kills the AI vs dr. lulu, and do DANGER root penalties cut it?

- **Lane:** tapout (Grok). **Tree:** `grok-tapout-wt` `experiments/cvx`, branch `grok/tapout-study` off
  `h16-rollout-gated` (b18a251e). Sim only: no hardware, no RTL / firmware build.
- **Committed before:** any danger-arm game on any seed. Run before this commit: one 3-game identity smoke of
  `T_a16_u8` (== banked `S14_d16_u8` rows 44300/44302/44304 on every key; deleted). The characterisation replays
  (stage 0) were LAUNCHED before this commit; no trace was read before it.

## 1. Background (STEER14, b18a251e)
LULU race, n 5,100 (seeds 44300.., step 2): kill losses (tap-out before her finish, `vs_race.evaluate` loss_kill) are
307 (6.0 %) for today's FAIR2PLUS-equivalent (`S14_d4_k32`) and 356 (7.0 %) for the certified candidate A16 + u8
(`S14_d16_u8`). Tap-outs at any time: 577 / 478. Neither STEER14 lever reduces kills.

## 2. Questions
- **Q0 (descriptive, stage 0):** for every tap-out of both baselines on the main block (478 + 577 games, replayed
  under the trace wrapper `tapout_run.py`, identity-checked against the banked rows), and 200 random clears of each as
  controls: when (pill index, time, viruses left), the heights before death (spawn throat cols 2-5 and per column), the
  garbage received in the last 10 pills, the pills (colour pairs), whether the last pills locked before DONE (search cut
  short: `down_stab`), disarm, landing != final, and the dominant mechanism (classified by the rule in sec. 4).
- **Q1 (main):** does a DANGER root penalty cut the LULU kill rate of A16 + u8, without raising total LULU loss?
- **Q2:** same on today's FAIR2PLUS gate (k32), where present in the main set.

## 3. The knob family (`tapout_run.py`, root-side = firmware-only, the STEER10 `pen` path)
`spawn`: pen[a] = P x max(0, Hs(b1(a)) - h0), Hs = max height of columns 2..5; `spawnq`: P x excess^2; optional gate
trig (root Hs >= trig). Stage 1 SCREEN grid on A16 + u8 (vk 16), 600 seeds of a fresh block 47000.. (step 2), disjoint
from the main block:
  D1 spawn P 60 h0 11 | D2 spawn P 200 h0 11 | D3 spawn P 200 h0 13 | D4 spawnq P 40 h0 10 | D5 spawn P 500 h0 12 trig 11
  plus `T_a16_u8` on the same 600 seeds.
**Screen rule (written before any screen row):** rank arms by LULU loss (total) on the 600 seeds; take the best
up-to-3 arms whose tap-out-any count is below the baseline's on those seeds; ties by fewer kills. If none qualifies,
the main phase runs D2 alone and the result says so.

## 4. Main phase and analysis
- Each selected arm on the full main block (5,100 seeds, 44300.. step 2), paired against the banked `S14_d16_u8`
  rows (identity: the wrapper reproduced them; re-checked on 50 seeds before analysis). The best arm (lowest kill on
  the main block) is also run at today's gate k32 on 2,000 seeds vs `S14_d4_k32` (descriptive, Q2).
- **Primary:** paired difference in LULU kill rate, arm - A16+u8; 95 % paired bootstrap (10,000 resamples over
  seeds), **Bonferroni over the selected arms (K <= 3, two-sided alpha 0.05/K)**. HELPS if the Bonferroni upper < 0.
- **Co-primary guard:** total LULU loss difference, same method; a recommended arm must have Bonferroni upper
  bound <= +1.0 pp (no meaningful harm) and the point estimate <= 0.
- **Secondary (descriptive):** tap-out any time, slow losses, pills/time per game, rule activity (fired/changed),
  META pen mismatch count (must be < 1 % of decisions, else the arm's tempo is suspect and is flagged).
- **Classification rule for Q0** (on the last 8 pills before death): GARBAGE-DRIVEN if >= 4 garbage tiles landed in
  that window; THROAT if Hs reached >= 14 at least 3 pills before death with no garbage; CUT-SHORT if >= half of the
  window's pills locked by stability (before DONE) and none of the above; otherwise OTHER. Descriptive only.

## 5. Not decided here
Hardware, copro RTL or cart builds; couch tests. Owner fairness rule is untouched (penalties change choices only).

## Addendum A (2026-10-14, before any guard game of a danger arm): the STEER14 guards on D4 and D1
- **Why:** RESULT_TAPOUT recommends D4 (D1 the fallback) without the two STEER14 guards.
- **Guards:** defined exactly as STEER14 (`steer14_jobs`):
  - owner race: `race ARM 2.36 hartford`, scored with `vs_race.evaluate` at M 239.5;
  - gate b: `gb ARM owner202610`, scored on won / topout / stall.
- **Arms:** T_D4_u8 and T_D1_u8 vs A16 + u8, on the full main block (5,100 seeds 44300.. step 2), paired by seed.
  - Base rows: the banked `rc14_/gb14_S14_d16_u8` (1,000 seeds), plus `T_a16_u8` under this wrapper for the remaining
    4,100 seeds.
  - Wrapper identity: the race was shown 1,455/1,455 in stage 0; gate b is 2/2 on banked seeds (smoke, deleted).
- **Today's gate (descriptive):** T_D4_k32 and T_D1_k32 on both guards, 1,000 seeds vs the banked `S14_d4_k32` guard rows.
- **Endpoints:**
  - owner race: kill / loss / slow;
  - gate b: loss (1 − won) / tap-out / stall.
  - Paired bootstrap 10,000 with Bonferroni K = 2 (the two arms).
- **Harm rule (as STEER14):** gate-b tap-out UP (Bonferroni lower > 0) or owner-race loss UP (Bonferroni lower > 0).
  An arm with harm is not recommended.
- **Machines:** blackmage only. rivalmage is a 2-core / 492 MB MiSTer, not usable for this sim. No route to the
  Hetzner box was found.
