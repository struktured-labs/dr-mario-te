# AUDIT — where else could a validity check be eating the phenomenon?

Requested by team-lead after the E1 error. **The shape: a "data quality" check
that encodes the same assumption as the fault does not clean the data, it
launders the bug into a null.** This is a sweep of every filter in the rig for
that shape, done now rather than after the next campaign.

## CONFIRMED — found, and fixed

### 1. `find_base()` corroboration deletes the match RESULT ★★★
`seedjit_ss.find_base()` refuses any state whose virus counters disagree with
the board contents. **The end-of-match animation IS that disagreement.** It
discarded ~15% of samples, and modes `$03` (clear) and `$07` (top-out) — the
only two states that name a winner — lived exclusively inside the discarded
ones. This is what produced the false "E1 is unadjudicable" verdict.
**Fixed:** use the empirically constant base (`0x102b08`) but VERIFY it by the
same NAV_MAGIC signature, falling back to the full scan. Undecodable went
**15.3% → 0.0%** on 4,589 samples.

### 2. `score_rows.py` had NEVER RUN TO COMPLETION ★★★
`find_base()` raises **`SystemExit`**, which `except Exception` does not catch.
The shipped scorer therefore ABORTED on the first awkward sample rather than
counting it unreadable. **Measured: it died after 3 of 255 rows** (exit 1).
So "no scorer output exists" was never "nobody ran it" — it *could not* run.
**Fixed:** now completes 4,589 rows, 0 unreadable, exit 0.

## LIVE HAZARD — did not fire here, but the shape is present

### 3. The boot-motion gate can VOID a genuine WEDGE ★★★
`run_arm` VOIDs a row as `no_cart_or_static_boot` when 2-3 consecutive boot
screenshots are byte-identical. **But E2's measurand IS absence of motion.** A
cart that boots and immediately wedges is indistinguishable, to this gate, from
a deployment failure — so the gate would discard exactly the event E2 exists to
count, and file it as an instrument fault.
**Status: it did NOT fire in population A** — 0 rows carry
`no_cart_or_static_boot` (the 154 boot VOIDs are `boot_motion_shots_failed`,
i.e. the screenshot files were never created, which was our `ls -t` defect).
So nothing was eaten in practice. The hazard remains live for any future run.
**Recommended:** before VOIDing on static frames, pull a save-state and check
whether the RNG/virus state is advancing. A frozen SCREEN with a live RAM state
is a capture fault; a frozen SCREEN with a frozen LFSR is a WEDGE and is data.
That is precisely the discriminator that adjudicated the 4 `wedge_suspect` rows
(2 real freezes, 2 capture artifacts) after the fact.

### 4. VOID rule 5 structurally suppresses a real cart-caused freeze ★★
Rule 5 says a "goes≈0 / no matches" cycle is not a cart property until a re-run
AND a same-runner positive control reproduce it. As a guard against the three
historical false positives that is correct. But it is also the reason the two
genuine ship-arm freezes cannot currently be called a cart property: the
positive control passes, and the re-run is unobtainable on a box now out of
bounds. **Not a defect — a documented tension worth naming**, because it means
the rule's cost is paid in exactly the case where the finding would be most
interesting.

### 5. The template validity gate shares hazard #1 ★
The same-seed / different-seed cell-set gate calls `board`, hence `find_base`.
A validity sample landing mid-clear-animation would fail the gate spuriously and
read as "the template is wrong". It did not happen (the old-box gate returned
47/47 and 37/37), but it is the same latent trap and now inherits the fix.

## Not a hazard, checked and cleared
- `wedge_suspect` (3 identical screenshot hashes) is a FLAG, not a filter — it
  discards nothing, and 2 of its 4 hits were correctly adjudicated away as
  capture artifacts by the RAM timeline.
- The cart/rbf hash gates halt rather than filter, and after the fix an
  unreadable hash is a separate retriable class from a real substitution.

## The transferable rule
**Before trusting a null, ask what the validity filter deletes, and whether the
phenomenon lives there.** Every check in this rig tested whether a sample looked
*normal*; the signal was, by nature, an *abnormal* sample.
