# H16 → STANDING SOFTWARE CHAMPION

**Promoted 2026-08-26 ~17:10 EDT by team-lead, on the owner's explicit decision
("H16: do it") following the GO verdict. NO earlier experiment is retroactively
altered: sealed baselines (h12_arm.py md5 dd5358191b824d38ac144f5d3594bd0b in
eval47/stage2/oracle) remain sealed and authoritative for their registrations.**

## What is promoted (fingerprints)
| artifact | md5 |
|---|---|
| `h16_arm.py` (the champion definition) | c098f56d4d0fb3f897fe5dcf63a187ae |
| `run_h16.py` (trial runner, provenance) | a485fd5a21613bf70bad65e907901089 |
| `REGISTRATION_H16.md` (the registration it passed) | f75e400ef2dbfe90a4300ba64cca7f74 |

## What H16 is (from its own header)
Certified H12, **bit-identical when quiet**, plus one additive pre-pass:
- **TRIGGER** `d_spawn_h >= 13`, cooldown 5 (re-fires early iff dsh grew)
- **SCREEN** every dedup'd-by-board candidate × 2 CRN forks, H=25
- **CONFIRM** top-8 (+ evaluator's pick) × 6 fresh forks
- **OVERRIDE** iff surv6(champ) ≤ 3 AND surv6(best) − surv6(champ) ≥ 3
Otherwise identical H12 behaviour; certified tie machinery untouched.

## The verdict it passed (2026-08-26 17:02 EDT)
- **PRIMARY** e1, 600 pressured pairs: fail 34.17% → 31.50%,
  **d = −2.67pp, CI [−4.67, −0.50], McNemar p = 0.00976** (29/13 discordant)
- **NULL** e2, 600 dose-matched: d = +0.50pp, p = 0.7288; override-ratio 1.096
  in band; **mutant_reads_GO = no**
- **GUARD** 1,000 clean games: 0.0000 / 0.0000; fires on 0.158% of plies
- Verified: both arms 600/600 by direct file count; futility count 0;
  achieved MDE ±3.02pp quoted alongside the effect.

## What "champion" means from today
1. **Teacher / label source** for the distillation cascade (supergod → coproc →
   NES-only). New label generation defaults to H16.
2. **Baseline for future trials**: successors register against H16.
3. **Software only.** The FPGA port is out of registration scope and the chip is
   full; the silicon champion remains the shipped dblcanon core.
4. Sealed past experiments keep their sealed baselines. The screening bar from
   the substitution closure (candidates must clear cap(CHAMP)=37.3% off-policy)
   is measured against the CHAMPION SUBSTRATE's tiebreak and is unchanged.

## Why it coheres (same-day evidence)
The substitution closure proved static how-to-rank substitutes lose in
proportion to how often they act (24/24). H16 is the WHETHER-to-act existence
proof: a gated, rollout-informed trigger at 0.16% of plies, +GO. One law, both
directions, one day.
