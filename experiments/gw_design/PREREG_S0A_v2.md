# PREREG — S0-A v2: argmax-flip screen over DE-DUPLICATED candidates

**Registered 2026-08-18, BEFORE any screen data exists.** Supersedes `PREREG_S0A.md`, which
is VOID and kept unedited as the record. Task #117 step 1.

**v1 inherits unchanged** except where §A below says otherwise: the population (§2), the
stratification (§4), the decision rule (§5), the secondary readout (§6), the void conditions
(§7), the logging requirement (§9) and the cost/stopping rules (§10) all carry over verbatim.
Read v1 for those; this document states only what changed and why.

---

## A. WHY v1 WAS VOIDED — the arm was comparing a board with itself

v1 §3 defined the candidate pair as the top-2 champion actions at an exact value tie. The
gate measured what that population actually contains (12 seeds, 359 post-garbage plies):

| observation | value |
|---|---|
| the two candidates produce a **literally identical board** | **87.1%** (108/124) |
| tie events whose capsule is a **double** (`cur.a == cur.b`) | 89.5% |
| identical successor value spectra (max / sorted vector / top-3 / mean) | 94-96% |
| identical legal-move count | **100%** |

**Mechanism, and it is arithmetic.** A capsule is a double one time in three; a double is
symmetric under 180°, so orientations 0 and 2 are the same placement and so are 1 and 3. The
action space collapses 32 → 16 and every placement appears twice with exactly equal value.
The "exact top-2 tie" predicate therefore fires overwhelmingly on a placement and its own
mirror, and **no deepening can discriminate two identical boards**.

⚠ **Nothing in v1's gate caught this.** Non-vacuity passed (n > 0). M-D1 passed (disabled
deepening flips 0). M-D2 passed (unpaired futures moved the rate — *because independent
noise moves it even when the boards are identical*, which is the tell I initially misread as
reassurance). A gate can be fully green while the instrument measures nothing: **every
mutant tested the plumbing, none tested whether the population was degenerate.**

---

## B. CHANGE 1 — candidates are de-duplicated by RESULTING BOARD

Replaces v1 §3's first line. At a post-garbage ply:

1. enumerate legal actions in `CHAMP_ORDER`, descending champion value;
2. apply each to a clone and key it by the resulting board;
3. keep the **first** action reaching each distinct board (deterministic: highest value, then
   `CHAMP_ORDER` index) — call these the **representatives**;
4. the ply enters the primary population **iff the top-2 representatives have exactly equal
   champion value**;
5. the deepening (v1 §3 steps 1-4, unchanged) runs on those two representatives.

**Silicon note, registered so the offline rig is not mistaken for the shipping cost:** the
cart needs no board comparison. `if cur.a == cur.b: skip orientations 2 and 3` is one byte
compare and a branch, and it captures the entire effect. The 32-board canonicalisation here
is an offline convenience that also catches any non-double coincidences.

## C. CHANGE 2 — the expected population is ~7.5× smaller, and that is registered up front

MEASURED on the same corpus:

| | of post-garbage plies | of all plies |
|---|---|---|
| raw top-2 tie (v1) | 39.8% | 6.86% |
| **de-duplicated top-2 tie (v2)** | **5.29%** | **0.911%** |

⇒ trigger population ≈ 0.911% × 52.4% affordable ≈ **0.48% of plies**, against H12's
measured **1.98%** accepted-flip dose. **The comparator's population is ~4× smaller than
H12's dose.** This is registered as an expectation so that a small `n` in the result is read
as *predicted*, not as evidence of a broken run.

⚠ **Consequence for v1 §7.1's coverage void.** At 0.911% of plies and ~50 high-fill
post-garbage plies per 1,000 seeds, the registered `MIN_HIGH_FILL = 100` may not be reachable
at 1,000 seeds. **The threshold is NOT relaxed** — it is a real requirement, and if the run
misses it the honest outcome is VOID with a stated seed count that would reach it.

## C.1 SEED BLOCK — corrected before any row exists: **50100-51099**

v1 registered **110000-110999**. That block is unclaimed *by seed number* but **collides in
stream space**, and the h13-gate lane caught it:

> `NesPillSource` keys on **16 bits**. Verified, not assumed: seed 110000 and seed 44464
> (= 110000 & 0xFFFF) produce **identical** capsule streams; likewise 110999 ↔ 45463. So
> 110000-110999 maps to stream keys **44464-45463**, lying entirely inside the H12 endpoint
> block 41100-50099.

The virus boards would still differ (drawn from `numpy.default_rng(seed)`, which uses the
full seed), so the games are genuinely different — but the **pill streams would be
byte-identical to a block the certified H12 endpoint already consumed.** If this screen were
ever pooled with or compared against H12 endpoint data, that shared-stream correlation would
be real and invisible.

⇒ **Registered block is now 50100-51099** (1,000 seeds), in the gap between the H12 endpoint
and the distill block at 60000. Below 65536, so **seed == stream key** and the registry stays
readable by inspection. Extension block, registered in advance for the coverage-VOID case:
**51100-59999** (8,900 contiguous seeds, same property).

⚠ **Carried, and it must NOT be "fixed":** within any contiguous block, seeds `2k` and `2k+1`
share the identical capsule stream — the low bit is dead — so 1,000 contiguous seeds is ~500
distinct streams. **Do not halve the block to "remove duplicates":** virus boards come from
the full seed, so twins play different boards (measured twin-pair correlation of paired
differences r = −0.077). Halving would cut coverage without removing redundancy, and that
trap has been sprung on this project before.

★ Registered **before any screen row exists**, which is the only reason this is an amendment
rather than a void.

## D. CHANGE 3 — one added mutant, and it is the one that would have caught this

Added to v1 §8's set:

| id | mutation | must be caught by |
|---|---|---|
| **M-D3** | **de-duplication disabled** (v1's raw top-2) | the population must **grow ≈7.5×** AND the share of tie events whose two candidates yield an identical board must jump from ~0% to ~87%. Both are asserted. |

**M-D3 is a population check, not a plumbing check** — that is the whole lesson of §A. The
gate now also reports, unconditionally, the fraction of screened tie events whose candidates
produce identical boards; under v2 that number must be **0** by construction, and the gate
asserts it. A screen whose candidates can be identical is not measuring a deepening.

## E. What does NOT change

The decision rule (v1 §5) is untouched: CLOSE if `U < 2%` on either the overall or the
≥45%-fill population; PROCEED only if `L(≥45% fill) > 2%`; INDETERMINATE otherwise; VOID
first. The 2% floor, the Wilson intervals, the stratification, the secondary re-derivation of
the 50.5%, and the no-interim-peeking rule all carry over.

## F. Note for the design document and for H12

- **H12 is not invalidated.** Its trigger is the same raw predicate, so its `tie_plies` is
  inflated identically — but identical candidates produce identical fork labels, so its
  θ-margin gate (`margin_sum ≥ 3`) rejects them automatically. Its certified effect stands.
  What is overstated is `tie_plies` **used as a dose statistic**, which is exactly the use I
  made of it in `GARBAGE_WINDOW_DESIGN.md` §1.6 and have now retracted in §1.6b.
- **A free tempo win falls out** (task #114): for a double capsule the mirrored orientations
  are the same placement but not the same cost to reach — the executor is CCW-only, so orient
  1 costs three rotations from spawn where orient 3 costs one. Canonicalising to the
  cheapest-to-reach member is a pure tempo gain with provably zero board effect.
