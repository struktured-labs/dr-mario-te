# Secondary reads — population A (n=126 pairs), clearly labelled

**Authorized by team-lead as a parallel secondary while the primary is in
question. Population A only, offline, zero box time.** These are NOT the
registered primary and do not substitute for it.

## E1b — near-death survival. READABLE, and it is a NULL

Readable from the banked artifacts **without catching a match ending**: a side
is near-death while it has occupied cells in playfield rows 0-2 (the prereg's
own key). An EXCURSION is a contiguous run of such samples inside one match;
it SURVIVED if `occ_top3` returns to 0 later in the same match, DIED if the
match ends while still above the line. Excursions open at cycle end are
censored, not scored.

**P1 — the side DRP1SLICE modifies:**

| arm | excursions | survived | died | survival |
|---|---|---|---|---|
| ship | 418 | 55 | 363 | 13.2% |
| slice | 413 | 58 | 355 | 14.0% |

Paired on the 124 seeds present in both arms: **ship 12.99% vs slice 14.00%,
difference +1.01 pp** in the hypothesised direction.

**Seed-clustered bootstrap (4,000 resamples of SEEDS, not excursions — 
excursions within a cycle are not independent): 95% CI [-2.59, +4.72] pp.**
70.5% of resamples favour slice. **The CI spans 0: this is a NULL**, directionally
consistent and nothing more. Reported as a null, not as a trend.

P2 for completeness: ship 55.9% (34), slice 64.1% (39) — small n, also null.

## E2 — safety monitor. ⚠ NOT the expected 0=0

The driver flagged 4 rows `wedge_suspect`. The prereg forbids deciding a wedge
from the heuristic, so each was adjudicated offline against the RAM timeline:

| row | distinct virus states | distinct LFSR | matches | verdict |
|---|---|---|---|---|
| 56561 ship | 5 | 2 | 1 | game ADVANCED — screenshot-identity was a capture artifact |
| 7207 ship | 11 | 3 | 2 | game ADVANCED — capture artifact |
| **48757 ship** | **1** | **1** | **0** | **frozen mid-play** |
| **45431 ship** | **1** | **1** | **0** | **frozen mid-play** |

The two real ones are **mid-play freezes, not failed boots**: both had already
been playing (48757 at 42/38 viruses, 45431 at 47/39 — both below the starting
48), and then the virus counters, the level, AND the RNG state are byte-identical
across all 18 samples = the full 360 s cycle. The game loop stopped.

**Both are on the SHIP arm; slice has none.** `ship 2/129, slice 0/126`,
**Fisher exact two-sided p = 0.498 — NOT significant.** Per prereg rule 8 this
is BOUNDED EXPOSURE and a witness count, not a rate.

⚠ **Rule 5 is only half-satisfied.** It requires (a) a re-run of the same arm
AND (b) a same-runner positive control before a low-goes reading is a cart
property. **(b) PASSES cleanly** — for both seeds the SLICE arm of the SAME seed
in the same session played normally (4 and 3 matches). **(a) is missing** and
cannot be obtained: the re-run would have to happen on a box that is now out of
bounds. So this is a well-characterised witness, **not** a demonstrated cart
property.

It is nonetheless the only signal in the corpus pointing the way the hypothesis
predicts — ship carries the NMI overrun tail, slice removed it, and the two
freezes are on ship. **Proposed, not taken unilaterally:** re-run seeds 48757
and 45431, both arms, on the old box — 4 cycles, ~30 min. That is a targeted
diagnostic, not population B. It cannot satisfy rule 5(a) as written (different
box = different population) but a reproduction would matter a great deal, and a
non-reproduction would too.

## E3 — descriptive only (tempo-adjacent; adjudicates nothing)

993 matches completed across 255 cycles, mean 3.89 per 360 s cycle
(ship 3.84, slice 3.94). Per the prereg's phase-dial rule, tempo deltas between
arms are EXPECTED and are not evidence either way.

Instrument health: `pull_fail` 1 and `shot_fail` 1 across 4,589 samples.
