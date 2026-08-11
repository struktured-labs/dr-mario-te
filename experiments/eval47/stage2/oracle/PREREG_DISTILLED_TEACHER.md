# Preregistration: compact oracle-teacher screen

**Frozen 2026-08-11 before any registered endpoint game.** The one prior game,
seed 51299, was an explicitly non-authoritative end-to-end implementation smoke.

## Question and authority

Can a firmware-sized policy distilled from the historical H15 oracle's actual
root choices preserve *directed* endpoint value under candidate-independent
pressure?

This is an **E0 implementation and dose screen**, not a ship gate and not an
endpoint verdict.  Its 60 pairs are far too small to close or validate the
lane.  Endpoint fields are logged because the runner contract requires them,
but they can only nominate a larger preregistered run.

## Frozen policy pair

- Artifact: `oracle_teacher_dt2_v1.json`, SHA-256
  `9ae58f0d9c0d69dfc3d781fbca16b126bed254517589a7ae8a1d6312b10b9b32`.
- Teacher corpus: 125 previously seen, legacy self-coupled ORACLE-CLAIR pilot
  games; 6,215 gated decisions and 489 oracle flips.
- Gate: current-board `d_spawn_h >= 12 OR viruses <= 8`.
- Candidate set: champion ranks 1--4.  The champion is rank 1.
- `true`: a depth-2 tree predicts whether to leave rank 1; a second depth-2
  tree chooses among ranks 2--4.  The boundary leaf is thinned by the frozen
  `(seed, ply)` hash to exactly 489/6,215 training decisions.
- `null`: the identical architecture and exact 489/6,215 training dose, fit to
  flip locations and alternative ranks shuffled without endpoint labels.
- Offline evidence is exploratory: grouped-CV trigger AUC/AP is
  0.7563/0.1769 for true versus 0.4945/0.0778 for null; alternative accuracy
  on real oracle flips is 0.5399 versus 0.3088.

The endpoint screen compares three arms on every seed: unchanged champion,
`true`, and `null`.  The true and null policies are frozen; no threshold or
feature may be tuned from E0 endpoints.

## Environment and seeds

- Candidate-independent `exo_lulu_v1` complete pressure offers, whose E1--E5
  implementation/dose gate already passed at 60 seeds.
- Level 11, real NES capsule stream, 300-pill cap, shipped `wt=0, ws=20`
  champion.
- Seeds **51300..51359**, N=60, ascending and triple-paired.
- Four workers; per-flip provenance enabled.
- The earlier implementation smoke seed 51299 is excluded.

## E0 gates

Run and print these before displaying endpoints:

1. **Identity:** the base arm is the oracle runner's proven constant-label
   champion path; all arms use zero forward forks.
2. **Activity:** true and null each make at least one change and emit complete
   provenance for every change.
3. **Churn ceiling:** neither arm may change more than 15% of all scored plies.
4. **Dose match:** `true_flips / null_flips` must be in **[0.80, 1.25]** and
   the same ratio for flip rate per scored ply must be in [0.80, 1.25].
   Failure makes every endpoint contrast **VOID**.  An endpoint-blind
   recalibration may use only aggregate trigger/ply counts from this block;
   it requires a new artifact, hash and preregistration on disjoint seeds.
5. **Pressure sanity:** mean landed garbage per scored ply for true versus null
   must be within [0.80, 1.25].  This is not equal-game pressure—trajectory
   lengths differ—but catches a broken environment path.
6. **Stall parity:** `bad_end = topout OR stall`; no endpoint display may omit
   stalls or topout↔stall transitions.

## Endpoint nomination rule (non-authoritative)

Only after E0 gates pass, print paired transitions for bad-end, clear,
dies-ahead, topout and stall, plus true-minus-base, null-minus-base and the
difference-in-differences.  A larger run may be nominated only if:

- true does not increase bad-end versus base;
- true clear rate is no more than 2/60 below base; and
- true-minus-null bad-end DiD is at most -1/60.

Passing merely nominates an adequately powered run.  Failing does not close
teacher distillation; it says this frozen compact candidate did not earn more
games.  No cart or firmware change may be promoted from E0.

## Checks that must fail on wrong input

`test_distilled_teacher.py` must pass feature-builder identity and must reject
(a) reversed tree branches and (b) a reordered feature contract.  The E0 gate
analyser must also carry killed mutants for the high-dose and dose-ratio
directions before its verdict is trusted.

