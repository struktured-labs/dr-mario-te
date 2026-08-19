# PREREG_ROTDIR v3 — amendment, registered BEFORE any v3 run exists

v2 (`PREREG_ROTDIR_V2.md`, rot-exec) ran and returned **NO-VERDICT** under its own rules:
seed 4014's ON cell was MISSING, and 3 of 4 mutants were UNSCORED-therefore-surviving because
their cells were eaten by #131 wedges. #131 is now fixed and adopted (#135), so the blocker
v2 escalated to is gone and the ladder can be re-run.

**This file does not reinterpret v2's data.** It registers a corrected *execution*; the
decision rules are inherited verbatim.

## INHERITED FROM v2, UNCHANGED — do not re-derive

- **Scope.** WIN orient only (copro 1, delta 1). The three control orients are settled by
  exact byte-equality between arms and are NOT re-run.
- **Seeds.** 4001–4016, the same 16.
- **Inclusion.** A cell is scored iff **both** arms report `wedges == 0`.
- **Power bar.** Score only if **≥ 8 of 16** pairs survive; else NO-VERDICT.
- **P1.** mean(ON f/pill) − mean(OFF f/pill) ≤ **−1.5 f/pill**, paired 95% CI (t, n−1) upper
  bound **< 0**.
- **P3.** Every surviving pair: OFF `pressB == 0` and `pressA > 0`; ON `pressB > 0.5 × pills`
  and `pressA == 0`.
- **Mutants.** m1, m2b, m3b, m4 re-scored on the surviving seed set by the same predicates. A
  mutant passing P1 is a SURVIVING mutant and **voids the verdict**. Unscored counts as
  surviving — absence is not a kill.
- **Verdict routing.** Unchanged (GO / CI-includes-0 / P3-fails-NO-GO / <8-pairs-NO-VERDICT).

## WHAT v3 ADDS — registered before data

**A. NO POOLING WITH v2. All 16×2 main cells are re-run on the patched harness.** v2's clean
cells are NOT carried forward and NOT merged. The harness changed between them, and mixing
pre-fix and post-fix cells is exactly the error #124 named ("pre/post jsonl must not pool").
v2's numbers appear in the report only as a labelled prior, never in the v3 statistic.

**B. HARNESS VALIDITY CENSUS, per arm.** Every cell must report `leaked == 0` **and**
`blocked ≥ 1` from the probe's own census. Rationale: `wedges == 0` is only meaningful if the
guard was actually exercised — an arm that never blocked anything did not earn its clean sheet
([[dr-mario-tuck-mailbox-vacuous-gate]]). A cell failing this is dropped as **INVALID** and
reported in a column SEPARATE from wedge-drops, because "the instrument didn't run" and "the
cart wedged" are different facts and must not be summed.

**C. RULE-12 MECHANISM CHECK, before P1 is read.** Gate-standard rule 12 (born from #115
today): a mutant or arm can die of the harness. DRROTDIR is a **tempo-shifting flag**
(~0.34 f/pill), and a tempo shift moves the restart phase, which is what drove the #131 wedge.
So: **the f/pill effect must arrive WITH its mechanism.** A P1 pass is only read as a flag
effect if P3's press census also holds on the same pairs (OFF = A-presses only, ON = B-presses
only). A tempo delta WITHOUT the press signature is reported as a phase/tempo artifact, not as
DRROTDIR working. This is a pre-registered *interpretation* constraint, not a new threshold.

**D. WEDGE COUNTS STAY EXPLORATORY.** v2 §"Secondary" already forbade banking a wedge-rate
difference as a DRROTDIR benefit, on exactly the phase argument rule 12 later generalised.
That stands, and with the leak fixed the expectation is 0 wedges in both arms — if any cell
still wedges, that is a NEW finding for #131/#133, not evidence about this flag.

**E. OVERLAP LABEL (non-additive).** Any f/pill number from this ladder is measured on a
DRDBLCANON core and is **NOT additive with #123's 0.96 s/game**. Every reported figure carries
that label inline so the number cannot travel without it
([[caveat-next-to-data-not-number]]).

**F. THIS IS A MEASUREMENT, NOT AN UN-PARK.** #114's park bar ("it rides, it doesn't drive")
is the owner's call. Whatever this produces goes on the decision list as evidence. Even a full
GO under the inherited routing is a *recommendation to consider*, not a ship.

## Rig, fixed before launch

- Probe: `tools/gate/probe_rotwedge.lua` on branch **hygiene-135** — carries #131's live-mode
  guard AND the census from (B). ⚠ NOT rot-exec's copy (md5 `0c640972`, UNPATCHED — that is
  the copy that produced v2's wedges).
- Carts: `rot-exec/roms/rotdir_{off,on}.nes`, md5-checked per run; OFF must be `9fefaedb`.
- 12,000 frames, orient 1, matching v2 so the comparison is like-for-like.

## Proof of timing

Committed with `tmp/d114/` absent, no v3 run directories, and no v3 results file on disk. The
commit that adds this file contains no data. A pre-registration nobody can date is just an
assertion ([[dr-mario-gate-standard-killed-mutants]]).

## ADDENDUM G — mutant seed-set size (registered before the surviving set is known)

v2 says the mutants are "re-scored on the same surviving seed set" without fixing its SIZE.
Taken literally that is 4 mutants × 2 orients × up to 16 seeds = up to 128 cells, which does
not fit tonight's window. Rather than decide that after seeing the survivors, it is fixed here:

**Mutants are scored on the FIRST 3 SURVIVING SEEDS in ascending numeric order**, on both
halves (orient 1 = the win, orient 0 = the delta-3 control).

Why a subset is legitimate here, and why it is the SAFE direction: a mutant is killed by
FAILING a predicate on the cells it is scored on. Fewer seeds can only make a mutant HARDER to
kill, never easier — an unkilled mutant counts as SURVIVING and VOIDS the verdict (v2). So this
choice is conservative with respect to the conclusion I would prefer, and it cannot manufacture
a GO. If any mutant survives its 3 seeds, the registered response is to widen that mutant to
the full surviving set before reading anything, NOT to declare it killed.

Committed while the main sheet is still running and before any mutant cell exists: at this
commit `tmp/d114/` contains only `d114_{off,on}_o1_*` directories and no `d114_m*` directory.
