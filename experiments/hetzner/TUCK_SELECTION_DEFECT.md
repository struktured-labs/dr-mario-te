# The tuck selection defect: base gets the EH bonus, tucks don't

**Located by reading, not measuring. It is documented by its own author, and the
stated hard prerequisite was never applied.**

## The pincer that pointed here

```
best-in-set (this lane)   FW set BETTER   +202.9 (26v5, p=2e-4) / +348.7 (16v0, p<1e-4)
                          => the CANDIDATE SET is not the problem
execution (co-sim)        52% of executed tucks are NO-OPS; 0 executor bugs;
                          n_incoherent = 0 across 881 t3 tucks (counter proven live at 101 on v1)
                          => EXECUTION is not the problem
⇒ good set + clean execution + bad published pick = SELECTION
```

## The defect

`fpga/copro/tuck_validation/tuck_ply2_score.py:19-25`, verbatim:

> **NOT YET INTEGRATED** (documented, deferred — see tuck_score.py's
> emit_eh_terms_reuse_label): the EH_PLY1 excav+hang add-on (D_ADL/D_ADH,
> normally added at k_done in the shipped EH_PLY1=True build). Until this is
> wired in, **tuck-candidate values are NOT directly comparable to
> base-candidate values under an EH_PLY1=True build — the theta gate would be
> miscalibrated (base gets the eh bonus, tuck candidates don't)**. This block is
> correct and differentially tested for EH_PLY1=False; wiring the eh_terms_scan
> reuse before this graduates past scratch validation is a **hard prerequisite
> for an EH_PLY1=True build.**

**The prerequisite was not met, and the build is EH_PLY1=True:**

| fact | evidence |
|---|---|
| shipped build is EH_PLY1=True | `fpga/copro/build_copro_d3.py:51` — `D3.EH_PLY1 = True` |
| the wiring is NOT applied | `tuck_score.py:125` `emit_eh_terms_reuse_label()` **raises NotImplementedError**, its docstring says "**not-yet-applied**" and "**do not call this function**" |
| nothing calls it | zero callers repo-wide; the only two hits are the docstrings that describe it |
| the tuck path never JSRs it | no `jsr eh_terms_scan` is emitted anywhere in the tuck path; the string appears only in prose and in tests' label lookups |

## Why this produces exactly "selects badly from a good set"

The excav+hang bonus is added to BASE candidate values at `k_done` under
EH_PLY1=True. Tuck candidates never receive it. Two consequences, and the
second is the one the pincer isolates:

1. **The θ gate compares incomparable quantities.** It tests
   `tuck_val >= best_base_val + θ` where `best_base_val` carries the EH bonus
   and `tuck_val` does not — a systematic offset, exactly as the author warned.
   This is a plausible contributor to the co-sim's finding that the gate is
   **inert from θ=150 to θ=20000**: if the two sides are on different scales,
   moving θ within the wrong scale changes nothing.
2. **Within-set ranking is by a score missing a term.** The published tuck is
   the argmax of a *different objective* than the one that judges it. A set can
   therefore contain a better candidate — which this lane measured that it does
   — while the firmware publishes a worse one. That is the definition of a
   selection defect, and it is scoped to one routine.

## Status of the claim

**Strong**: the prerequisite is explicit, its non-application is verifiable in
three independent ways above, and the shipped flag is EH_PLY1=True.

**Not yet measured**: the DIRECTION and MAGNITUDE of the resulting mis-ranking.
The natural next experiment is the one already scoped — score the published pick
against best-in-its-own-set under the mirror ruler — and it now has a *predicted
mechanism* to confirm rather than an open question. Do not assume the sign
without measuring; the missing term biases the gate and the ranking, and those
need not push the same way.

**Scope**: this concerns the tuck-enabled build the co-sim exercised. Separately,
the deployed probe cart has no tuck executor at all
(`DRTUCK` absent from its manifest), so tuck descriptors are inert there
regardless.

## The fix

The author already wrote it down: a **one-line** addition to
`test_search_d3.py::_emit_eh_terms` — `a.label("eh_terms_scan")` immediately
before the existing `a.label("eh_xcol")` — after which the tuck path does
`jsr tuck_imm1 ; jsr eh_terms_scan` instead of `jsr eh_terms` (which would re-run
`cp_live_cur` and destroy the tuck's already-placed board). The note states this
is **byte-neutral for the base path**, since a label is symbolic until something
JSRs to it, so the flag-off byte-identity gate is unaffected.
