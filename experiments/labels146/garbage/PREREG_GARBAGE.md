# PREREG_GARBAGE — counterfactual labeling campaign on GARBAGE/PRESSURE boards
(labels-146 branch, 2026-08-23, owner-directed: "ok do the labeling campaign on
garbage boards then")

Registered BEFORE any label data exists. Timing proof for the commit message:
`experiments/labels146/garbage/out/` contains zero `labels_*.jsonl.gz` and zero
`claims_*` files at commit time. This file inherits PREREG_LABELS.md's sealed
machinery and restates every inherited rule it relies on.

## 0. Purpose and registered consumer

The champion's competitive failure is one shape: it stops clearing and builds a
committal tower under MILD garbage contamination, dying with 15-27 viruses left
(champ-loss-autopsy; clean failure <0.2% vs 16.7% pressured). This campaign
produces dense per-(state, candidate-placement) labels by ROLLOUT SURVIVAL UNDER
CONTINUED PRESSURE on the champion's actual death distribution.

REGISTERED NEXT CONSUMER: evaluator feature work + fit — contamination-adjacency
/ clearability-under-occlusion features in the g_stranded mold, fitted against
this label bank. Match play is the exam, not the teacher. The label bank is its
OWN POPULATION: never pooled with population-A silicon statistics, never pooled
across strata (§1), never pooled with the labels-146 end−25..−1 bank.

## 1. Board sources — three strata, sizes fixed here, NEVER POOLED

| stratum | source | selection rule (mechanical) | pilot | campaign cap |
|---|---|---|---|---|
| **A** (silicon, pop A) | the 15 autopsied competitive grinds (champ-loss-autopsy buckets a+b), artifacts `~/projects/dr-mario-sileval-wt/experiments/sileval/out/artifacts/<row>/s*.ss` | the pre-death samples the autopsy itself identified, FROZEN at commit time in `sources_A.txt` (parsed from `classify_all.txt`, ≤3 per row); each must additionally pass all §3 import gates | first 12 states by (row asc, sample desc) | all that pass (≤45) |
| **B** (silicon, fresh corpus) | `/mnt/data/drmario_corpus/loss_ledger_20260823.jsonl`, loss rows with `boundary_suspect == false AND order_ambiguous == false AND ends_in_bracket == 1 AND champion_losses == 1` (17 losses, FROZEN in `sources_B.txt`) | per loss: samples s(b−1), s(b−2), s(b−3) where s(b) = `sample_bracket` (strictly pre-death), each passing §3 gates | first 12 states by (seed asc, sample desc) | all that pass (≤51) |
| **C** (lab, replayable) | champ145 bank `states_*.jsonl.gz` (L20 lulu home regime), topout games | first 25 topout games in ascending seed order with n_plies ≥ 60; target plies end−k, k ∈ {30, 40, 50} (MID-GAME: upstream of labels-146's end−25..−1 window, no overlap, where the tower is BUILT) | first 12 states (game asc, k asc) | 75 states |

Stratum A/B pre-death states are the champion's (P2) board decoded from MiSTer
save-states. The A-list of grind rows is fixed at commit time in
`grind_rows_popA.txt` (the 15 rows named in the autopsy memory table, buckets
a+b).

## 2. Rig — the HOME REGIME (unchanged from PREREG_LABELS §1)

level=20, model=lulu (honest bursty v1.1), ws=20, wt=0, champion-const
continuation, sealed champion-145 oracle lineage (`oracle_arm.py` content
d3cb836). No new decider, no new physics.

## 3. Silicon board import (strata A/B only) — gates, each a VOID class

Decode: base via `e1_winner.find_base` (re-verified per file, never a constant);
board = 128 bytes at `$0500`, tile decode incl. LINK PLANE via
`transfer_check.nes_to_board`'s mapping (memory dr-mario-tile-encoding);
cur pill = `$0381/$0382`, next = `$039A/$039B`, lab color = nes+1.

- **G-I1 mode**: `$46 == 4` (active play), else VOID(mode).
- **G-I2 counter**: BCD `$03A4` == virus-tile count of the decoded board, else
  VOID(counter) (the find_base cross-address invariant, re-asserted).
- **G-I3 settle**: `_apply_gravity()` on the imported board must be a NO-OP
  (memory dr-mario-transcribed-board-settle-gate). Anything moves → VOID(settle).
  We never "fix" a moved board.
- **G-I4 bail (dangling links)**: any half-link whose partner cell does not hold
  the reciprocal link → VOID(links) — bail, don't model (memory
  dr-mario-garbage-orphans-a-linked-half).
- **G-I5 pills**: cur/nxt bytes each in 0..2, else VOID(pills). One-time
  instrument check before the pilot: cur/nxt decode visually confirmed against
  ≥2 banked PNGs (preview capsule colors).

VOID-RATE THRESHOLD (rule 15): if >30% of candidate states in a stratum VOID, or
stratum A or B yields <8 usable states, STOP and report — instrument problem,
not data. Every VOID is recorded with its class (relabel, never delete).

Import-gate KILLED MUTANTS (must FAIL, run before the pilot; rule 16 — prove the
gates can reject): (m1) board byte corrupted → G-I2 fails; (m2) a tile lifted
one row → G-I3 fails; (m3) hand-built dangling `$6x` with no `$7x` partner →
G-I4 fails; (m4) mode byte forced to 7 → G-I1 fails.

## 4. Label definition (FIXED)

For each state: candidates = ALL legal placements de-dup'd by RESULTING-BOARD
sha1 (`enumerate_candidates`, rule-7 unconditional assert — 87% raw ties are the
same placement, and de-dup by move is NOT board-neutral). Per unique candidate:
**N = 8 CRN forks, horizon H = 25** champion-const plies under the §2 pressure
model. Label = (`surv[8]` ∈ {0,1}, `prog[8]` = viruses cleared), the labels-146
encoding. Per-state summary stat = surv count of 8 (binomial, SE ≤ 0.177).

Fork futures:
- **Stratum C**: exactly `labelcore.label_state` after a `labelcore.replay_game`
  gated walk (recomputed 32-value vector + argmax == banked row at EVERY ply;
  mismatch aborts the seed). True capsule stream continues;
  `dist_seed(seed, ply, s)` keys injection. CRN across candidates by
  construction.
- **Strata A/B**: env built from the imported board; `env.cur`/`env.nxt` pinned
  from RAM (visible at the decision); `pills_placed` initialized to 60 (≥
  GARBAGE_MIN_PILLS=25 so pressure is live; the bursty model keys on clears, not
  pill periodicity); max_pills = 60+400. Per-sample future s: capsule stream
  SWAPPED after cur/nxt via the autopsy A1.1 `_swap_stream` construction AND
  injection, both keyed by `fseed = dist_seed(source_key, 0, s)` where
  `source_key = (stratum_id << 24) | (seed << 8) | pre_idx` (injective; stratum
  A=1, B=2; seed < 65536; pre_idx < 256). Candidate-independent ⇒ CRN holds.
- Deepcopy pill-cursor independence (memory dr-mario-deepcopy-pill-closure) is
  guaranteed by the oracle's PillDraw and re-asserted in the G-CRN control.

REGISTERED CAVEAT (travels with the bank): for A/B the label is "survival under
continued HOME-REGIME pressure from this board", not a replay of the silicon
opponent; the rollout policy is the silicon champion's lab MIRROR (~88%
move-agreement near death, dr-mario-cosim-farm). Fidelity is regime-dependent;
these strata are feature-fitting fuel, not silicon ground truth.

## 5. Claim rule (inherited PREREG_LABELS §5, restated)

CLAIM = state where `max_c surv_c − surv_champ ≥ 3` (of N=8) with
`surv_champ ≤ 5`. Champion's pick = lab-champion argmax on the state (for A/B
that is the MIRROR's pick — claims there are reported as mirror-champ claims).
Claimed action = argmax_c surv_c, ties by champion value then scan order.

## 6. Controls BEFORE scale (pilot; ANY failure ⇒ STOP AND REPORT, no campaign)

1. **G-replay** (C): 2 banked topout seeds replay end-to-end, zero mismatches.
2. **M-stale** (C): one skipped action MUST abort at the gate (liveness).
3. **Import-gate killed mutants** (§3 m1-m4): each MUST fail its gate.
4. **G-CRN/determinism**: labeling one state twice ⇒ byte-equal JSON; fork
   seeds for sample s equal across candidates.
5. **M-mimic**: labeler = champion's own values on all pilot states ⇒ MUST
   yield 0 claims, required verdict line `MIMIC FAIL_NO_CLAIMS`.
6. **M-shuffle**: per-state label permutation (seeded rng, recorded) ⇒ nonempty
   claim set; on stratum C validation it must NOT outperform true labels'
   rescue−break; if it does, the instrument is broken and NOTHING promotes.
7. **G-pressure-live** (the competitive-loop launch-gate analog, memory
   dr-mario-cvc-harness-never-delivers-garbage): aggregate injection events
   across pilot forks MUST be > 0, AND a severed-injection control on 3 pilot
   states (same fseeds, injection disabled) must not DECREASE mean surv
   (expected: surv_no_inj ≥ surv_inj, strictly greater somewhere). If severing
   injection changes nothing anywhere, the pressure is not binding on this
   window ⇒ STOP (a garbage campaign whose garbage does nothing is vacuous —
   the GW-pricing-void failure shape).

## 7. Validation + promotion gate

- **Stratum C claims**: forced-move game-rescue exactly as PREREG_LABELS §5
  (arm A = banked outcome; arm B = gated replay to the claim ply, force the
  claimed action, champion-const continuation under the TRUE injection,
  max_pills=400; endpoint = game failure). PROMOTION GATE for the campaign
  label bank feeding the evaluator step, restated for this population:
  **≥150 fresh claims at k ≥ 8 plies before death** (rescue mechanically
  possible per the lock-in boundary), **Fisher one-sided p < 0.05** rescued vs
  broken, **rescue−break rate ≥ 0.15**, **positive calibration slope**
  (predicted Δsurv vs realized rescue rate). NOTE: at the §1 window (k=30..50)
  every C claim is k≥8 by construction; the 150-claim bar is a CAMPAIGN-SCALE
  bar and may require extending stratum C's game count — extension is by the
  same mechanical rule (next topout games in seed order), never by re-sampling
  windows.
- **Strata A/B**: game-rescue is impossible (no banked lab game). Registered
  endpoint: (i) label bank + per-stratum claim-rate report; (ii) calibration:
  split forks 0-3 vs 4-7, across candidates within each state the 0-3 surv must
  positively predict 4-7 surv (pooled within-state Spearman > 0, per stratum).
  These strata feed feature fitting; they do not by themselves promote anything.
- Pilot claim/validation numbers are REPORT-ONLY (pilot n cannot pass the gate;
  the pilot cannot be read as its own confirmation).

## 8. Compute + resumability

Local box only until the H14 verdict frees blackmage (do NOT touch
drm-champ-endpoint / drm-autopsy-label / either MiSTer / Hetzner c5). ≤8
workers, `runcapped` (systemd-run scope, MemoryMax, MemorySwapMax=0), nice.
Per-state rows appended atomically (`labels_<stratum>.jsonl` + fsync-rename
segments); the harvester SKIPS states already labeled ⇒ segmented/resumable and
movable to blackmage mid-campaign. CLOSE-OUT = ledger audit: labeled-state count
vs registered target list, per stratum, printed (clean exit ≠ completion).

## 9. Output format (the label bank)

`out/labels_<stratum>.jsonl.gz`, one row per state:
`{stratum, source:{row|seed, box?, sample?, ply|k}, board_c64, board_v64,
board_l64 (b64 planes incl. link), cur:[a,b], nxt:[a,b], pills_placed,
champ_slot, ents:[{slots, rep_slot, key, planes, surv[8], prog[8]}],
gates:{...}, fseed_base}` — self-describing for the feature-fit consumer.
Void rows go to `voids_<stratum>.jsonl` with their class.

## 10. Cost (registered as ratio, not wall-clock)

Prior: 0.718 cpu-s/fork (labels-146 pilot). Pilot ≈ 36 states × ~20 candidates
× 8 forks ≈ 5.8k forks ≈ 1.2 cpu-h. Campaign ≤ ~171 states ≈ 27k forks ≈ 5.5
cpu-h. Report the realized cpu-s/fork against the 0.718 prior.
