# PREREG — GW increment pricing: conditional split in the co-sim farm

**Registered 2026-08-20, BEFORE any row of the fresh seed block exists.** Owner-approved
priced step per `tools/nmi126/GW_INCREMENT_SPEC.md` (branch `nmi-bound-126`, this branch).
Prices the first GW increment — tie-only 2-candidate 1-ply deepening, copro-firmware-only,
replace-not-merge — as `effect(h) = P(completes | h) × value(move | granted)`, stratified
by h. Run locally, $0 cash, ≤ ~40 core-h (the "$4-equivalent" the spec budgeted).

## 1. Rig coverage map (gate-standard rule 10 — which component executes what)

| question | component that executes it |
|---|---|
| every game-line placement decision | **real RTL** — verilated CoproDrMario, fw `s20b` md5 `e970e9ab` (the shipped champion), via the committed co-sim farm |
| physics, garbage, capsule stream | faithful sim + NesPillSource + bursty v1.1 (committed farm rig, `game.py`) |
| trigger predicate (de-dup'd top-2 tie), deepening, rand/worst alternative selection | **fast-sim champion mirror** (`oracle_arm._champ_values` / `screen_gw` functions) — transfer-validated 100 % move agreement vs real RTL on 50 real-L11 boards (`cosim_farm/README.md`, n=50 ⇒ exact lower bound ~92.9 %, mid-game corpus) |
| P(completes \| h) — the left factor | **banked measured cost distribution**: 1,500 real per-decision copro-cycle costs (`/mnt/data/drmario_cosim/results/prestart_pilot.jsonl`, `lat[0]`, fw e970e9ab), against W(h)=264−16·h in BOTH clock domains (Pocket 909,652.11 cyc/f derived from 54.669358 MHz/60.0988; MiSTer ×1.57) |
| NOT covered | timing/seqlock/driver interaction (the farm is turn-based — [[dr-mario-cosim-farm-turnbased]]; that is WHY the split into two factors exists), silicon, h≥14 fast-search story (explicitly deferred by the spec) |

The farm's secret-perfect-prestart bias is common-mode across all arms (every arm plays the
settled post-garbage board) and cancels in paired deltas — the registered reason this lane
is priceable where DRPRESTART was not.

## 2. Seed blocks (fresh, recorded)

- **Precondition screen block: 52100–53099** (1,000 seeds), through the committed S0-A
  screen (`gw_design/screen_gw.py`, gated M-D1/M-D2/M-D3 + population mutant) with its own
  `lulu` pressure rig. Inside the S0 lane's own registered extension block 51100–59999
  (PREREG_S0A_v2 §C.1); this experiment is that lane's registered successor. 51100–52099
  ("left unspent" by the S0-B closure) is left untouched. All seeds < 65536 so
  seed == stream key; 2k≡2k+1 alias noted, block NOT halved (virus boards differ).
  Blocks 41100–50099 (H12), 50100–51099 (S0-A), 300–699, 60000+ (distill), 63000–63079,
  63900–63907 (soak) are consumed elsewhere and not touched.
- **Farm seeds:** N1 = the first **32** seeds of 52100–53099 in ascending order whose
  screen game contains ≥ 1 `kind=deepen, flip=1` row → arms **base** and **deepen**.
  N2 = the first **16** of those 32 → arms **rand** and **worst** additionally.
  Flip-enrichment is a game-level importance sample; the estimand (§5) conditions on a
  trigger occurring, so enrichment changes yield, not meaning. The chosen lists are
  recorded in the output manifest.

## 3. Precondition — argmax-flip rate (STOP/GO, reported to team-lead BEFORE the farm run)

**Reading rule, fixed now:** the spec's precondition ("measure the deepening's flip rate on
the tie population"; `dr-mario-spawn-lane-gate-probe` <2 % ⇒ untestable) is read as
**flips per de-duplicated surviving tie event** — the pricing instrument's own trigger
population. **GO iff flip rate ≥ 2 % AND n_tie ≥ 100** on the fresh block; else STOP and the
lane closes honestly. The per-ALL-plies flip dose (expected ≈ 0.3 %, i.e. below 2 % — the
already-registered reason a full-N endpoint is implausible and this pricing design exists)
is **reported for the MDE arithmetic but does not gate**; registering that here is what
prevents it being re-read as a STOP after the fact. S0-A's banked value on 50100–51099 was
33.8 % (381/1126); a fresh-block value in that range is the expectation, not the criterion.

## 4. Farm instrument (`run_gw_price.py`, new — gated per §7 before any real row is read)

One game = committed `game.py` semantics (exec="drop", pressure="bursty" v1.1, L11,
max_pills 300, fw s20b) plus an observer/intervention at post-garbage plies:

- **Trigger** at a decision with `post_garbage=1`: mirror champ values on the farm's own
  board → legal by CHAMP_ORDER → representatives de-duplicated BY RESULTING BOARD →
  top-2 reps exactly value-tied → `deepen()` (committed S0-A code: shared sampled
  next-next capsule, CRN) flips the pick → AND the RTL's own move produces the same board
  as rep0 (mirror/RTL mismatch ⇒ **no intervention in any arm**, counted
  `n_mirror_mismatch`; pricing VOID if mismatch > 10 % of tie plies).
- **Arms** at a trigger: `base` plays the RTL move; `deepen` plays the deepened pick;
  `rand` plays a uniform draw over de-dup'd representatives excluding rep0
  (`random.Random(seed*7919+ply)`); `worst` plays the minimum-value representative
  (tie-break: last in CHAMP_ORDER rank). All forks/clones use deepcopy-safe PillDraw
  objects; the parent stream is never advanced by the observer (gate G1).
- Identical prefixes ⇒ the FIRST trigger ply is common to all arms of a seed (asserted);
  later triggers are arm-local policy consequences, which is the shipped semantics.
- Logged per trigger: ply, h_hit (committed #124-fixed capture), rep values, picks, arm.

## 5. Readout — conditional split (decision rule fixed before data)

Unit: **per-seed paired delta (arm − base), among seeds with ≥ 1 trigger**; seeds with 0
triggers must show exactly zero delta (pairing check, hard assert). Primary metric
**Δviruses_cleared**; secondary Δwon, Δdies_ahead, Δpills. Mean + 95 % bootstrap CI
(10,000 resamples, rng seed 1). Stratified by FIRST-trigger `h_hit` bands
{≤7, 8–10, 11–13, ≥14} — operating-point table always, never a global stat alone
([[dr-mario-auc-operating-point-law]]).

**Ordering control (instrument validity, S0-B's handed-forward design):** GREEN iff
point(worst) < point(rand) < 0 on Δviruses_cleared AND CI_upper(worst) < 0. Not green ⇒
the deepen sign is NOT read (no verdict on d); the pricing table and MDE are still
delivered, labelled instrument-not-validated.

**Pricing product:** for each h band, effect(h) = P(3.0×C ≤ W(h)) × d(h), with
P from the banked 1,500-cost empirical distribution (3.0×C = base + 2-candidate 1-ply
deepening, the spec's budget), reported for BOTH Pocket and MiSTer domains.

**MDE statement** vs the registered H12 endpoint (clear rate at FULL N, anchors —
MDE ≈ 0.84 pp at H12's n=9,000 scale, PREREG_S0B_REFORK §1): projected endpoint effect =
measured triggers/game × measured per-trigger Δclear, at point and at CI bounds; plus the
n that would detect the measured d at 80 % power / α=0.05.

## 6. Verdict routing (registered)

| verdict | condition |
|---|---|
| **VOID** | any §7 gate red · ordering control mutant-invalid · < 10 triggered seeds scored in base∪deepen · mirror mismatch > 10 % of tie plies |
| **NO-GO — do not fund the full A/B** | ordering GREEN and (CI_upper(d) ≤ 0, or projected full-N endpoint effect at CI_upper < 0.84 pp) |
| **GO — fund the full A/B** | ordering GREEN and CI_lower(d) > 0 and projected effect at point ≥ 0.84 pp |
| **INDETERMINATE** | anything else — report the resolving n and the priced next step; not a launch licence |

A GO here licenses sizing the silicon A/B, not shipping; a NO-GO closes the increment at
the price of this run, which is the point of pricing first.

## 7. Gates (killed-mutant standard, run BEFORE reading any real farm row)

| gate | proves | mutant that must FAIL it |
|---|---|---|
| G1 non-perturbation | interventions OFF + observer ON reproduces stock `play_game` byte-identically (action trace, result, pills, viruses, clocks) on 3 seeds | M1: fork helper skips the PillDraw re-seat (the live `nes_pills` closure — [[dr-mario-deepcopy-pill-closure]]) |
| G2 population (rule 7) | de-dup'd tie population is non-degenerate | M2: dedup OFF ⇒ tie count must GROW ×4–12 (predicted ~7.5×); unconditional assert: surviving top-2 never same board |
| G3 arm selection | worst=min-value rep, rand excludes rep0, deepen plays `deepen()`'s pick (synthetic fixtures) | M3a: worst→max caught; M3b: rand pool includes rep0 caught |
| G4 second implementation | full-list de-dup's top-2 == committed `screen_gw.representatives` on ≥ 200 real post-garbage boards | divergence = red |
| G5 h_hit | committed `test_gw_hhit.py` green in this worktree (its own 6-scenario + tier-2 suite) | its own mutants |
| G6 analysis | verdict router driven with ≥ 6 synthetic tables straddling every §6 threshold | M6: router ignoring the MDE clause must return GO on a small-but-significant fixture where §6 says INDETERMINATE/NO-GO |
| G8 determinism | re-running one triggered (arm, seed) reproduces its row byte-identically | frozen-counter style drift = red |

Rule-12 note: interventions change BOARDS only; the farm has no time axis, so the
phase-dial/tempo confound class ([[d131-wedge-discriminator-f30]]) is structurally absent
in this rig — stated so the absence is a claim, not an oversight.

## 8. Ops

Long steps under `systemd-run --user` units `drm-gw-screen`, `drm-gw-farm` with analysis
chained inside the unit. JSONL to `/mnt/data/drmario_cosim/results/gw_price/`; verdicts and
manifests committed. Never touches live soak files or any SD. Commit+push after each
milestone with explicit remote+branch over SSH.
