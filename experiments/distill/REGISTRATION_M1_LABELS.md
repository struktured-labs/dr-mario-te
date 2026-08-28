# REGISTRATION — M1 label campaign (distill-coproc lane)
Status: REGISTERED 2026-08-26 (team-lead GO with numeric-bar rider, applied in
§5). Launch order: §7 smoke -> gates green -> seed block to CONSUMED ->
campaign. Timing proof at launch: the seed block below is untouched by any run
and `out/labels_m1/` does not exist (logged at launch per R28). R49 rider:
no interim label-game numbers quoted to anyone until segments bank.

## 1. Purpose and registered consumers (label-quality law: name the consumer)
One bank, two consumers, registered in advance:
- **Track A (primary)**: fit + screen the danger-guard g (M2) — WHETHER
  (tribunal override/stand verdict) and WHICH (per-candidate surv6/prog).
- **Track B (secondary)**: progress-label evaluator screens (offline only).
No promotion evidence comes from this bank; it licenses M2's screens only.

## 2. Position source (on-policy for the baseline being replaced)
Champion-const games (the chip's software mirror), honest-drlulu bursty,
provenance ON, `max_pills=400`, per-seed atomic + resumable segments.
- **Stratum L20** (teacher-comparability): ~700 games at L20.
- **Stratum L11M** (silicon regime): ~400 games at L11-MED.
Strata never pooled.

## 3. State selection within games (labelling dose)
At each decision ply, a state is ADJUDICATED (tribunal run + banked) iff its
stratum trigger fires, with NO cooldown for labelling (denser coverage; the
deployed guard has its own cooldown — deployment-distribution caveat stated),
plus band and control quotas per game capped to bound cost:
- L20 trigger: `dsh >= 13` (the teacher's own registered trigger).
  Band: `dsh in [10,12]` (max 2/game, earliest). Controls: 1/game healthy-tall
  ply (maxh >= 10, sampled mid-game) + 1/game random ply.
- L11M trigger: **`wide12 = max(H[2..5]) >= 12`** (blessed PROVISIONAL by
  team-lead 2026-08-26; validated by §5's numeric bars). Band: `max(H[2..5])
  in [10,11]` (max 2/game). Controls as above, with the random-ply quota
  raised to 2/game on L11M (feeds E-M1c's trigger-independent recall sample).
- Per-ply trigger values (all five §5 variants + per-column heights) are
  banked for EVERY ply of EVERY game, both strata — E-M1a/b/c compute from
  these traces, not from adjudicated states.
- Adjudications per game capped at 30 (budget guard; cap hits are counted and
  reported — an estimand-defining filter, explicit + counted per R51).

**AMENDMENT A1 (2026-08-26, BEFORE any label game ran — smoke not yet
started, `out/labels_m1/` absent):** the no-cooldown trigger class fires
~15-28 plies/game at L20 (champ145 bank: 11.95% of plies, uncooled 29/game on
doomed) — at ~98 forks/state that projects ~900 core-h, 3-6x the §8 estimate
and over tier. Fix: the TRIGGER class is THINNED — each trigger ply is
adjudicated with probability `THIN_P` (L20 0.12, L11M 0.20; seeded per-game
rng, reproducible), targeting ~3 trigger adjudications/game, unbiased within
game. Cap lowered 30→15. Thinned-out plies are counted (`thinned`). NOT
thinned: the random quota (E-M1c's unbiasedness), bands, healthy controls, and
the per-ply height traces (so E-M1a/b/c estimands are untouched — this is a
label-VOLUME knob, not an endpoint knob). The smoke's G-cost gate re-projects
from measured s/fork and still STOPs if over tier.

## 4. Labels (the promoted teacher's exact tribunal semantics)
Per adjudicated state: enumerate dedup'd-by-board candidates; SCREEN 2 CRN
forks x ALL; CONFIRM 6 fresh forks x top-8 (+ champion's entry); H=25; drlulu
injection live in forks; CRN keys `dist_seed(seed, ply, sample)` samples 0-7.
Banked per candidate: per-fork `surv` AND `prog` (8 each), H12 value, slots.
Banked per state: champion pick, the WHETHER verdict under the promoted rule
(override iff surv6(champ)<=3 AND best-champ>=3), trigger values (dsh, wide,
maxh, per-column heights), ply, virus count, `schema: "m1v1"` (R54: readers
assert schema per segment and refuse mixed).

## 5. Registered endpoints computed FROM the bank (before M2 fitting)
wide12 is in-sample best-of-9 and gets NO benefit of the doubt (team-lead
rider, R53/R58): each bar below is a pre-stated pass/fail NUMBER; a miss is a
STOP back to trigger design, never a threshold slide.
- **E-M1a PRIMARY, wide12 catch (well-powered, free from the per-ply height
  traces banked for every game)**: fraction of L11M TOPOUT games in which
  wide12 fires with >= 5 plies of pre-death lead.
  **PASS iff >= 0.70** (H16's L20 analog: dsh13 = 0.812 in k in [10,25]).
  dsh13's value on the same games is reported alongside as the comparator.
- **E-M1b PRIMARY, wide12 false-fire ceiling**: per-ply fire rate on L11M
  CLEARED-game plies (the H16 healthy-play convention).
  **PASS iff <= 0.15** (grounding: L20 registered trigger = 0.0655 healthy;
  L11 maxh>=13 census = 0.136 "affordable"; M0 sample rate 4%).
  **Plausibility band (two-sided, R53): a rate < 0.01 is a defect signal**
  (contradicts M0's 4% sample rate) => INVESTIGATE the instrument before any
  PASS is read; not an auto-pass.
- **E-M1c SECONDARY (recorded, not gated)**: (i) lead-time-at-first-fire
  distribution on L11M topout games, in plies and seconds (team-lead: lead
  time is the number that matters for a veto guard; M0 measured 75-100 s on
  the match suicides); (ii) tribunal-danger recall — on danger states
  (surv6(champ) <= 3) discovered via the RANDOM-ply quota only (the
  trigger-independent sample; trigger-discovered danger states are biased
  toward the trigger and reported separately with the bias stated), recall of
  wide12-fired-at-or-before, with binomial CI — expected n is small (~20-60),
  quoted with its CI or not at all (R49); (iii) fire rates of {dsh13, dsh12,
  wide12, wide13, maxh13} on ALL plies per stratum.
- **E-M1d yield**: adjudicated states, danger states, degenerate states
  (all-candidate labels identical — counted, kept, flagged per R52), cap-hit
  counts, adjudications/game distribution.

## 6. Gates at launch (wired IN the runner, recurring, able to stop the unit)
1. **G-CRN calibration**: split-half (forks 0-3 vs 4-7) per-candidate surv
   correlation on the first 30 adjudicated states per stratum; BLOCK if
   rho < 0.5 (campaign precedent 0.66-0.72). Recurring every 200 states.
   **AMENDMENT A4 (2026-08-27 ~00:50, after BOTH strata blocked at
   n≈200)**: the implemented statistic (shortlist confirm-halves 3v3) was
   proven MIS-SCOPED by replaying it on the known-good labels146 bank — it
   reads 0.222 there against the certified full-width 4v4's 0.66-0.72
   (range restriction: the shortlist is pre-selected BY screen survival;
   plus the campaign population is 62-80% saturation, spread<=1). The
   campaign LABELS are healthy on the same-form full-width statistic:
   L20 0.356 / L11M 0.445 vs the known-good bank's own 0.300 (n=799).
   Replacement (machinery + this dated amendment, NOT a bar slide): G-CRN =
   full-width screen-half rho (s1 fork0 vs fork1, all candidates), bar =
   0.6 x the independent reference 0.300 = **0.18**, two-sided
   (INVESTIGATE-HIGH at rho>0.8, implausible for 1-fork halves, R53);
   shuffle mutant permutes fork-1 across candidates (verified: null
   0.00+/-0.03, real 0.356/0.445). All banked segments KEPT — producer
   module unchanged, labels validated above the certified reference.
   This is the imported-calibration trap ("an instrument's calibration is
   not part of the instrument") caught by the lane's own wired gate at
   ~EUR 0.35 of compute.
2. **G-mutant-shuffle**: same statistic with labels shuffled across candidates
   must land near 0 (|rho| < 0.2) — the control must be able to fire.
   Run once at smoke, banked.
3. **G-pressure-live**: injection counters > 0 in game path AND fork path
   (banked per segment; a zero is UNRUN, not neutral — R26 family).
4. **G-activity**: adjudications > 0 by seed 3 of the smoke; overrides > 0
   somewhere in the smoke (else the bank cannot train a WHETHER decider).
5. **G-schema**: every segment carries `schema: "m1v1"`; the reader refuses
   files without it.
6. Status: `STATUS: RUNNING <pid> <expected>` at launch; recurring greppable
   line `[m1] stratum=<s> games=<n> states=<n> danger=<n> ...`; monitor exits
   on result-banked OR unit-not-active (R43: watch the failure path).

## 7. Smoke (allowed pre-launch)
2 seeds per stratum from the block head; all §6 gates must pass; per-fork
cpu-s measured and banked (cost anchor for the tier check). Smoke rows carry
`smoke: true` and are excluded from §5 endpoints.

**SMOKE #1 RESULT + AMENDMENTS A2/A3 (2026-08-26, before campaign launch):**
ran clean (exit 0, printed PASS) but was NOT accepted: (A3) the G-mutant-
shuffle control was VACUOUS — permuting whole per-candidate fork vectors
preserves the within-candidate half-to-half pairing the statistic measures,
and it returned the identical rho 0.926; fixed to permute the second
half-sums independently, nulled over 20 draws (R38a). (A2) overrides=0 in 4
games — no banked positive WHETHER record; smoke extended to 4 seeds/stratum
(campaign = block minus 4/stratum head). Cost anchors from smoke #1 stand:
0.82 s/fork, 716 forks/game, projection 178 core-h ≈ EUR 2.73 — inside tier.

## 8. Seeds and cost
- Block (approved, registered in CONSUMED at launch, owner tag
  "distill-coproc M1 labels"): **17700..20898 step 2 = 1,600 streams**.
  Split: L20 = 17700..19098 (700) · L11M = 19100..19898 (400) ·
  contingency/reserve 19900..20898 (500, untouched unless a stratum
  under-yields; use logged before consumption).
- Cost model: ~98 forks/adjudication x (8.3-30)/game x 1.1-1.9 cpu-s/fork.
  Tier cap EUR 6 cloud (or local-only). If the smoke's measured cost projects
  the campaign above tier, STOP and report before launching (R45: budget must
  not silently pick N — the cap triggers a conversation, not a quiet shrink).
- Siting: blackmage systemd unit (Nice=10, MemoryMax=24G, 8 workers);
  redmage gated work only after byte-equal cross-box gate; Hetzner cpx62
  fallback via /cloud.

## 9. Out of scope
No fitting, no screens, no A/B, no silicon work. The match-board / corpus
silicon stratum is read-only reuse (already banked) for the M2 spawn-plug
suite — no fresh silicon import here.
