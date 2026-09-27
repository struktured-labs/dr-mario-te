# RESULT (2026-09-26): OPP1 — nothing we'd ship collapses against any opponent; the hsv-vs-LULU flip did NOT replicate

Pre-regs: `PREREG_OPP1.md` (`f5204d4`) and `PREREG_OPP1b.md` (`5bb068b`), each committed before its games.
- **Code:** `opp_models.py` (OwnerBursty, plus the Striker port of lulu147 `striker_model.py` @1049308),
  `opp_owner202609.py` and `opp_run.py`.
- **Seeds:** 37934–39132, 600 paired, declared reuse, disjoint from the hsv selection block.
- **Exactness:** 10/10 local-vs-Hetzner row md5s match. The OWNER-0804 path reproduces the banked gate_b rows 10/10.
- **Instrument:** gate (b), L11 MED, cap 600, steering ON (couch P2 driver, unified DRTAPP=2).

## Gate (b): build × opponent
Cells show whole-game tap-out / tap≤100 / clear; n = 600 each.

| opponent | base (REACH+TAP) | hsv512 | hsv − base tap-out | hsv − base tap≤100 |
|---|---|---|---|---|
| **OWNER-0804** (blind baseline, banked) | 23.8 / 4.3 / 76.2 | 23.0 / 3.3 / 77.0 | −0.83 [−5.17, +3.50] | −1.00 [−3.17, +1.00] |
| **OWNER-2026-09** (refit, renewal) | 21.8 / 3.8 / 78.2 | 21.8 / 2.0 / 78.2 | +0.00 [−4.33, +4.33] | **−1.83 [−3.50, −0.17]** |
| **STRIKER H5** | 25.0 / 4.2 / 75.0 | 24.5 / 4.7 / 75.5 | −0.50 [−5.00, +3.67] | +0.50 [−1.67, +2.83] |
| **STRIKER H6** | 25.0 / 4.8 / 75.0 | 24.2 / 3.2 / 75.8 | −0.83 [−5.50, +3.67] | −1.67 [−4.00, +0.67] |
| **STRIKER H8** | 24.3 / 4.2 / 75.7 | 25.5 / 3.7 / 74.5 | +1.17 [−3.50, +5.67] | −0.50 [−2.67, +1.83] |

**Opponent effect against the COMMON BLIND BASELINE (OWNER-0804)**, same build, paired, whole-game tap-out:

| opponent | base | hsv |
|---|---|---|
| OWNER-2026-09 | −2.00 [−6.50, +2.50] | −1.17 [−5.50, +3.17] |
| STRIKER H5 | +1.17 [−3.33, +5.50] | +1.50 [−2.83, +5.83] |
| STRIKER H6 | +1.17 [−3.50, +5.83] | +1.17 [−3.17, +5.50] |
| STRIKER H8 | +0.50 [−3.83, +4.83] | +2.50 [−1.83, +6.83] |

tap≤100 contrasts all lie within ±1.4 pp, and every CI spans 0.

**Reading (pre-declared):**
- **No COLLAPSE** in any cell. Every tap-out CI upper bound is < +7 pp against the +10 bar, and no tap≤100 cell
  rises.
- **hsv does NOT flip** against any gate-(b) opponent. Its tap≤100 edge holds under OWNER-2026-09, with a CI below 0.

**Striker behaved as designed:**
- 16–23 releases per game; 69–95% were height-triggered (H8 hits its timeout more often).
- Only 1–2% of earned cells were still banked at game end.

The striker's timing attack costs at most a few points, and the CIs cannot exclude a small +5 pp harm.

**OWNER-2026-09 is MILDER than OWNER-0804 in this sim:**
- It lands 0.32 garbage cells per eligible placement, against 0.42.
- It matches the couch volley rate (0.180 volleys per placement vs 0.184), but only 1.78 cells land per volley
  against 2.27 drawn, because volleys whose column top is full are skipped.
- So the refit does not make the sim harsher. The couch loss is not "the owner sends more".

## LULU (the racer): vs_race lam 2, bracket M 140/160/177 (n = 600 paired)

| δ | M | base win | hsv win | hsv − base |
|---|---|---|---|---|
| 2.65 | 140 | 88.7% | 84.8% | **−3.83 [−7.50, −0.50]** |
| 2.65 | 160 | 89.5% | 85.8% | **−3.67 [−7.00, −0.33]** |
| 2.65 | 177 | 89.8% | 86.7% | −3.17 [−6.50, +0.17] |
| 2.0 | 140 | 80.8% | 78.8% | −2.00 [−6.17, +2.00] |
| 2.0 | 160 | 85.2% | 82.2% | −3.00 [−6.83, +0.67] |
| 2.0 | 177 | 87.7% | 83.7% | **−4.00 [−7.67, −0.50]** |

Race-row tap-out is 9.2% for base and 12.7% for hsv: **+3.50 [+0.33, +6.83]**.

- **Where the bot starts winning (descriptive M sweep):** at δ 2.65, the bot wins ≥ 50% from M ≈ 70–75 s. Both
  builds beat a racer at M 140–177 about 85–90% of the time.
- **Pre-declared flag FIRED: "hsv flips vs LULU"** (upper CI < 0 at 3 of 6 bracket points).
- **Mechanism (descriptive):**
  - Most of the deficit is loss_race (54 → 73), i.e. the bot is slower. loss_kill moves only 14 → 18.
  - The hsv-only kills are LATE: median t_end 662 s, 3 viruses left. These are endgame failures in long games.
  - STEER5d's hsv win was measured at lam 6, where early tap-outs dominate. At lam 2 there are almost none (5 vs 5
    ≤ 100 pills), so the early-game benefit has nothing to act on.
- **Caveat:** OPP1 made ≈ 11 comparison families, so the flag needed an independent confirmation. It **did not
  replicate** (OPP1b below).

## OPP1b: confirmatory test of the LULU flip (2,166 disjoint seeds) — **NOT CONFIRMED**
Rows: `opp1b/`. Local 2,180 + Hetzner 2,152 = 4,332 games, all 2,166 pairs complete. Analysis: `analyze_opp1.py --b`.

| endpoint (lam 2) | base | hsv | hsv − base |
|---|---|---|---|
| **PRIMARY race win, M 140, δ 2.65** | 86.4% | 87.6% | **+1.15 [−0.60, +2.95]** → NOT CONFIRMED |
| race win, M 160 / 177, δ 2.65 | 87.1 / 87.5% | 88.8 / 89.6% | +1.75 [+0.00, +3.51] / +2.08 [+0.42, +3.83] |
| race win, M 140 / 160 / 177, δ 2.0 | 80.9 / 84.4 / 86.0% | 80.1 / 84.8 / 86.6% | −0.74 / +0.37 / +0.60 (all CIs span 0) |
| race-row tap-out | 11.3% | 9.1% | **−2.12 [−3.79, −0.51]**, the OPPOSITE sign to OPP1 |

- **Pooled OPP1 + OPP1b (descriptive, n = 2,766):**
  - race win at M 140: **+0.07 [−1.59, +1.66]**;
  - race-row tap-out: −0.90 [−2.39, +0.69];
  - loss_kill: **−1.30 [−2.21, −0.33]**;
  - loss_race: +1.23 [−0.14, +2.60].
  - So against a light-sending racer, hsv is race-neutral. It swaps some kills for slow finishes, and it does not
    lose.
- **Same seeds at lam 6 (banked STEER5d):** race win at M 140 is +3.23 [+0.65, +5.86], and tap-out is −3.51.
  - hsv's edge is larger under heavy sends, where there are early tap-outs to prevent.
  - Under light sends it shrinks to about 0.
  - This is a magnitude difference, not a sign flip.
- **Why OPP1 flagged:**
  - The 37934–39132 block is simply unfavourable to hsv; even at lam 6 its hsv − base was only +1.2 at M 177.
  - OPP1 made about 11 comparison families, so one false flag was about the expected count.
  - The pre-declared confirmation step did its job.

## Verdict
1. **Does anything we'd ship collapse against a deliberate opponent? NO.**
   - Opponents tested: the refit owner, the timing striker at H 5/6/8, and a racer from M 140 to 177.
   - Neither the shipping REACH+TAP build nor hsv512 moves more than +2.5 pp in tap-out against the blind baseline.
   - Every CI excludes the +10 pp collapse bar.
2. **hsv512 holds against every opponent.**
   - Its gate-(b) tap-out is neutral or better everywhere, and tap≤100 improves under OWNER-2026-09.
   - Against the racer it is neutral at lam 2 (pooled) and better at lam 6.
   - The OPP1 flip was a false positive: it did not replicate on 2,166 independent seeds.
3. **The racer is not the threat; our own tap-outs are.**
   - The bot beats a M 140–177 racer 85–90% of the time and wins ≥ 50% down to M ≈ 70–75 s.
   - Losses at lam 2 are mostly slow finishes and late endgame kills, not early tap-outs.
   - The striker's height-timed release is nearly harmless in this sim.
   - What still separates the sim from the couch is not modelled by any of these opponents (see STEER1: steering
     explains most of it).

**Limits:**
- All results are sim-only, under steering + the gate-(b) clock.
- LULU is a bracket, not a fit. No per-player send fit exists; the 0808 fit pools both players.
- PRO was skipped because the tape's send data is unusable.
- The striker is the lulu147 model, not an observed human policy.
