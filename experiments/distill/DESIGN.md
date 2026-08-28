# DESIGN — Distilling H16's whether-to-act discipline into the next coproc
distill-coproc lane · 2026-08-26 · CHECKPOINT DRAFT — no compute spent beyond
banked-data reads + seed-registry checks. Every spend tier gated on sign-off (§E).

## 0. Frame
- **TEACHER**: H16, promoted software champion 2026-08-26 (PROMOTION.md md5
  0dd5d897; h16_arm.py c098f56d — read-only, never edited). GO: d=−2.67pp
  CI[−4.67,−0.50] p=0.0098 on 600 pressured pairs; inert on clean play
  (0/91,130 plies); fires 0.16% of plies.
- **MOTIVATION**: owner vs dblcanon 3-2 (2026-08-26). Both owner wins were the
  chip's SPAWN-COLUMN-PLUG suicides — literally H16's trigger class
  (d_spawn_h = max(H[3],H[4])). The chip cannot run rollouts.
- **BASELINE BEING REPLACED** (the LAW, score-against-the-baseline-you-replace):
  **champion-const** — the software mirror of what the chip plays. Every
  candidate is scored against IT, on-policy. H16 is the teacher and reference
  ceiling, NOT the baseline.
- **CAPACITY**: ~90% ALM, +0.6% breaks timing ⇒ **RTL/ALM budget = 0**. The
  copro is a 6502 (85.9 MHz, 16KB fw ROM, 4KB WRAM) idle 100% of the garbage
  window ⇒ the distilled artifact must be **FIRMWARE-ONLY** (cycles + ROM
  bytes). fw ROM headroom + candidate-board residency = M0 measurements.
  (The ≈11,900 cyc/frame budget is the NES-ROM-only lane's constraint; a gated
  guard amortizes there too — cascade step 3 reuses this bank, one line, later.)

## A. Tracks
### Track A (PRIMARY): the danger guard — a gated WHETHER(+WHICH) decider
Firmware pre-pass mirroring H16's shape, replacing the tribunal with a fitted
function g over post-placement candidate boards:
- TRIGGER: registered static trigger (dsh≥13 at L20; L11-MED variant from M0
  re-ROC — a registered constant, never a free knob).
- VETO/OVERRIDE: fire iff g(champ_pick) reads FATAL and some candidate reads
  SAFE with a decisive margin; play best by (g, champion value). Non-decisive ⇒
  exact champion behaviour. Rule-25 form: failure mode = status quo ante.
- Degraded-but-useful variant priced separately in M2: WHETHER-only (veto the
  plug, take champion's next-best that passes g) — both match deaths were
  single-placement wedges, so this may hold most of the prize (hypothesis;
  M2 measures it, nothing asserts it).

### A2. Why this is not a 24/24 corpse (the required escape argument)
The static-decider closure killed HOW-to-rank substitutes **at H12's exact-tie
plies**, where harm-per-override was negative 24/24 and corr(transfer, dose)
= −0.987. The guard differs on each load-bearing axis, and each difference is
measurable offline before any game spend:
1. **Population**: it acts at danger plies where survival DISCRIMINATES —
   H16 overrides only when surv6 gap ≥3/6 and the champion's pick dies in most
   forks (median champ-best value gap 405 units; not marginal re-ranks).
   The tie channel stays closed; we propose nothing there (37.3% bar untouched).
2. **Function class**: WHETHER-to-act with a veto structure, trained on
   tribunal verdicts (rollout-informed labels), not outcome broadcasts and not
   survival-at-saturated-ties (the two label defects behind the LUT's 6.8%).
   H15's close names this successor class: "conditional or rollout-based
   integration = a new program". This is that program's distillation step.
3. **Honesty**: off-policy reproduction of H16's verdicts is an UPPER BOUND
   (a decider chooses its own trigger set) ⇒ the M2 screen can only KILL,
   never promote. Promotion evidence comes solely from the M3 registered
   on-policy A/B vs champion-const, with a dose-matched label-shuffle mutant
   that must NOT read GO. **H0 = the 6.8% function-class wall.**

### Track B (SECONDARY, offline-only this phase): evaluator retrain labels
Same label bank, second consumer: fit candidate evaluator terms on H16
PROGRESS labels (the corrected target — H12/H16 key on progress; survival
saturates except exactly where H16 fires). Scope: offline screens only; any
GO spawns its own registration. Silicon reality: per-leaf eval changes are
RTL/ALM-bound (budget 0) ⇒ Track B's only deployable form converges with
Track A (root-level, gated, firmware) or serves the NES-only port.

### NOT DOING (each closed by evidence, cited in the memory store)
Tie substitutes (24/24 + 37.3% bar) · always-on leaf refit (coef-opt,
scaling-law refutation, H15 all-doses, LUT 6.8%) · endgame planner
(do-not-build) · planner imitation (closed) · more teacher forks (R40:
split-sample plateau at k≈4) · any RTL change (+231 ALM broke timing).

## B. Label generation plan
- **Source policy**: champion-const trajectories (the baseline's own states —
  where the guard must first act), L20 honest-lulu bursty, max_pills=400
  (cap-mismatch memory), + an L11-MED pressured stratum (the silicon regime).
  Strata never pooled.
- **Teacher dose**: full promoted-H16 tribunal semantics per adjudicated state
  — screen 2×ALL dedup'd candidates + confirm 6×top-8(+champ), H=25, lulu
  injection, CRN dist_seed keys; bank surv AND prog per fork per candidate
  (prog is free — h16_arm already computes and discards it).
- **State selection**: trigger plies with cooldown DISABLED for labelling
  (denser coverage, same on-trajectory states; deployment keeps its cooldown —
  distribution caveat stated) + a dsh∈[10,12] band for threshold learning +
  healthy-tall controls (guard must learn NOT to fire; maxh saturation trap).
- **Silicon import stratum (read-only, ~free)**: the 2 match death boards +
  loss-corpus competitive losses (17) + pop-A grinds (15) via the proven
  e1_winner import path; labelled at the same spec. Used for M0 ROC + the
  spawn-plug suite, never for training.
- **Volumes/cost**: ~700 L20 + ~400 L11-MED games → ~4,000–5,500 adjudicated
  states → ~450–550k forks at 1.1–1.9 cpu-s ⇒ **~140–290 cpu-h**.
  Siting: blackmage first (guard workers freed), redmage gated work only after
  the byte-equal cross-box gate (campaign procedure; MEGADOSE loop untouched),
  Hetzner cpx62 fallback ≈ **€3–6**. Wall ~1–2 days.
- **Gates at launch**: killed-mutant import sheet (m1–m5 pattern) · CRN
  split-half calibration rho · schema-versioned segments, per-file schema
  assert (R54) · per-state atomic + resumable · registry entry added at launch.
- **Seeds (registry-checked today)**: **17700..20898 step 2 = 1,600 streams,
  PASS** (keys 8850–10449). Registered on approval, not before.
  ⚠ Registry gap found & fixed en route: T1-a's played block 17440–17658 was
  absent from CONSUMED and --suggest was offering it; entry added, validated
  both directions (self-collides now; fresh block passes).

## C. Function class + silicon fit
- **Features** (all 6502-computable on a resolved candidate board): post-move
  spawn-lane height + delta (dsh relief) · throat occupancy rows 0–3 cols 2–5 ·
  a_topout_dist, e_escape_routes (already in the shipped feature vocabulary) ·
  adjacent-column height deltas (narrow-tower shape) · cur/next colours vs
  lane. g_center/g_attack directions are prediction-validated (garbage-labels)
  — their INTEGRATION failed only as always-on linear terms; conditional use
  is exactly the untried class.
- **Model**: integer thresholds/weights — small ruleset or int-linear + margin,
  distilled to constants; target ≤2KB fw ROM, ≤~100k cycles per fired ply
  (~1.2ms at 85.9MHz, inside the 0.15–0.35 s/pill envelope and dwarfed by the
  garbage window). Talk-to-constraints numbers audited at M0: fw ROM free
  bytes, WRAM residency of resolved ply-1 boards, per-candidate feature cost.
- **Fit procedure**: WHETHER = classify tribunal verdict {override, stand} at
  adjudicated plies; WHICH = rank shortlist by fitted g with champion value
  tiebreak, scored on realized surv-gain vs THE CHAMPION'S PICK (the baseline,
  per the LAW — never vs random, never vs slot indices; boards not slots,
  duplicate-slot hazard). Operating-point tables mandatory, AUC never quoted
  alone (distill-pivot rule).
- **Evaluator-is-the-lever context**: NES lane 2×2: evaluator +71.6pp at d2 vs
  depth +1.2pp with a good leaf; coproc decomposition: eval 85% / horizon 15%
  of regret. Depth work stays closed; this design spends nothing on it.

## D. Registered evaluation design (M3 — registration written before launch,
commit records data-absence, R28)
- **Arms**: A = champion-const · B = champion-const + fitted guard (frozen
  constants, hash-pinned). Both fork-free ⇒ ~12–25 core-s/pair.
- **PRIMARY**: failure (topout|stall) rate, L20 honest-lulu, paired seeds,
  McNemar exact one-sided, **GO iff p<0.05 AND d<0**. L20 keeps comparability
  with H16's own registration and every banked reference number.
- **Power (R45/R47 — effect chosen first, N follows; ψ prior 0.08 from H16's
  realized 7% discordance, guard dose will run hotter)**:
  | MDE @80% (2.8·SE) | N pairs | note |
  |---|---|---|
  | −1.34pp (50% of H16) | ~3,500 | minimum honest run |
  | **−1.09pp** | **~6,000** | **recommended** |
  | −1.00pp | ~7,900 | seed-space heavy |
  Achieved-MDE recomputed from realized discordance, travels with the verdict.
  Seed block requested at M3 registration (fresh, registry-checked; note:
  only 13,781 streams remain free — N is an owner-visible seed-space decision).
- **Futility interims**: wired IN the runner, recurring (n=1,500/3,000),
  greppable stat+decision line, able to stop the unit (R43a/55). Futility-only.
- **GUARD rider**: 1,000 clean L11 pairs; trip iff d>+1.0pp or 95% LB>0 ⇒
  NO-PROMOTION. Activity counters shipped with every number (R26): overrides>0
  on pressured sheet seeds, rate reported on clean.
- **Mutant/degeneracy sheet** (all pass before e1): m-neverfire ⇒ bit-identity
  + liveness · m-ident · m-swap · **dose-matched label-shuffle guard (fitted g
  replaced by a permuted-table g at matched realized override rate) must NOT
  read GO** · R51/52: not-all-labels-identical filter explicit + counted ·
  R53: two-sided plausibility bands on every gate stat · at-cap fraction PER
  ARM primary diagnostic + length-matched sensitivity (differential censoring).
- **SPAWN-PLUG SUITE (pre-registered mechanism secondary, design-gate only)**:
  the 2 owner-match death boards + loss-corpus + pop-A pre-death states —
  guard must veto the fatal placement on a pre-registered fraction, AND a
  matched healthy-tall control set must show false-veto below a pre-registered
  bound (the half that can fail, R36). Passing this never substitutes for the
  primary; failing it while the primary passes is a reportable mechanism gap.
- **SECONDARY (silicon-facing, reported with honest power, not gated)**:
  600 L11-MED pressured pairs — the regime the chip actually dies in.
- No autopromote. Verdict counts by direct file count, never printed prefixes.

## E. Milestones, spend tiers, checkpoints (sign-off before each tier)
- **M0 — €0, ~half a day (banked reads + emu only)**:
  (a) **in-regime trigger re-ROC** on the silicon death class (match boards,
  loss corpus, pop-A) + healthy L11-MED false-fire rate; select/registry the
  L11 trigger variant. GATE: catches ≥2/3 of the silicon death class at
  acceptable false-fire, else STOP — distilling as-is fixes the lab, not the
  chip. (b) firmware audit: fw ROM headroom, board residency, feature cycle
  cost. (c) this DESIGN signed off; label block registered.
- **M1 — labels, tier ≤€6 cloud (or €0 local), 1–2 days**: §B campaign.
  GATE: import mutants + CRN calibration green; yield ≥3,000 usable states.
- **M2 — offline distill + screen, ≤€1**: preregistered bars stated as
  fractions of MEASURED instrument headroom (R38): floor = label-shuffle fit,
  ceiling = split-sample tribunal self-transfer (R40 discipline). Forbidden
  predictions: fitted g must beat (i) do-nothing (champion pick) on realized
  surv-gain at its own firing set, and (ii) the best single raw feature (dsh
  relief), else the machinery is unjustified (S3 lesson). KILL ⇒ wall located,
  report; total sunk ≤~€7. GO ⇒ licenses writing the M3 registration only.
- **M3 — registered A/B, tier ≤€10 cloud (or local), ~2 days**: §D. GO ⇒ M4.
  R1 RIDERS (team-lead 2026-08-28, deployed-trigger re-scope): (a) the
  false-VETO ceiling is stated NUMERICALLY in the M3 registration, derived on
  reference data (R62 habit) before anything runs; (b) the M0 silicon-catch
  requirement binds on the DEPLOYED COMPOSITE trigger×g — g's contribution to
  end-to-end catch gets its own measured gate, never an assumption riding on
  E-M1a's 63/63. M3 registration drafting waits for A5's L11M ceiling
  re-measure (team-lead sequencing rule).
  Promising-but-short ⇒ ONE pre-declared DAgger round (relabel on guard-on
  trajectories) then one re-run of M3 on fresh seeds; no third pass.
- **M4 — silicon port (separately costed, owner sign-off)**: firmware
  implementation, in-regime validation, hardware A/B. Not licensed by this doc.
  R1 RIDER (c) (team-lead 2026-08-28): the deployed trigger's 26% L11M fire
  rate priced as compute must be priced in FIRMWARE terms — fire-rate ×
  guard-eval cycles against the copro budget — in the M4 design doc.
  RISK-REGISTER ITEMS CARRIED IN (from M0, 2026-08-26): (a) fw ROM headroom of
  1,756 B was measured on the CANONICAL delta build — the shipped dblcanon fw
  b03a586e is a DIFFERENT build; re-measure ITS headroom before any M4 work
  (copro-build-provenance trap); (b) the guard's deployed trigger for L11-MED
  is the M1-validated variant, not the sealed dsh13 — the silicon trigger
  constant must trace to E-M1a/b's passed bars.
**Total this design**: ≤~€17 cloud (mostly substitutable with local boxes),
~4–7 days wall including checkpoint latency.

## Risks (ranked)
1. **REGIME TRANSFER (top)**: trigger+effect are L20-lab-validated; the chip
   dies at L11-MED; banked warning: L11 edge-tower pre-death boards fire
   dsh≥13 at only 0.18/0.11. The match deaths are centre-plugs (dsh's home
   ground), but that is a hypothesis until M0 measures it — for €0, first.
2. **Function-class wall (H0)**: the tribunal may not compress — 6.8% LUT
   precedent. M2 kills it for ≤~€7 total sunk if so.
3. **Off-policy→on-policy gap**: the LAW; screen = upper bound; only M3
   promotes. Post-flip distribution shift handled by the single pre-declared
   DAgger round, not ad-hoc iteration.
4. **Teacher label noise**: 6-fork verdicts are coarse — but H16's GO proves
   this verdict class suffices at this dose, and fork-count is at the R40
   plateau; noise prices into the M2 ceiling measurement, not into hope.
5. **Seed space**: 42.1% free; full-power M3 consumes ~half of that. N is
   surfaced as an explicit owner decision at the M3 checkpoint.
