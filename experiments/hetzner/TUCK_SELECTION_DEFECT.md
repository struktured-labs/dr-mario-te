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

---

# MEASURED: the ranking consequence is NULL. The gate consequence stands.

`tuck_published_vs_best.py` models the firmware's ranking exactly as the
documented difference — `_root_value` takes `w_excav`/`w_hang` as parameters, so
"the score without the EH add-on" is not an approximation of the firmware, it IS
the documented delta — gates at θ=150 against the base reference WITH EH, and
compares the published pick's true value against the best in its own set.

| seed block | gated tuck decisions | published == best-in-set | mean loss |
|---|---|---|---|
| 7000-7005 | 16 | **16/16 (100%)** | 0.0 |
| 7100-7121 | 48 | **48/48 (100%)** | 0.0 |
| **combined (disjoint)** | **64** | **64/64** | **0.0** |

## ⚠ THIS REFUTES CONSEQUENCE (2), WHICH WAS MY OWN PREDICTION

I predicted two consequences of the missing EH term and said explicitly they
need not push the same way. They don't:

- **(2) within-set MIS-RANKING — REFUTED.** The missing term does not change the
  argmax on any of 64 gated decisions across two disjoint seed blocks. Plausible
  reason: the excav+hang term is near-constant across different tuck placements
  of the same pill on the same board, so it shifts every candidate equally and
  cancels in the argmax.
- **(1) θ-GATE MISCALIBRATION — STANDS, and is untested here.** It compares
  `tuck_val` (no EH) against `best_base_val` (with EH) — different placements
  entirely, so the term does NOT cancel. Consistent with the observed rarity:
  only **64 gated tuck decisions in ~1,800**, ≈2.7%.

## Verdict for the pincer

```
candidate SET     BETTER   (this lane, p=2e-4)
SELECTION rank    CLEAN    (64/64, zero loss)
EXECUTION         CLEAN    (co-sim: 0 executor bugs, n_incoherent=0 / 881)
⇒ remaining suspect: the ROOT-PLACEMENT OVERWRITE
```
The EH defect is real and worth fixing — it biases the gate and is a mechanism
for the co-sim's θ-inertness — but it is **not** what makes arm D catastrophic.
It suppresses how OFTEN tucks fire, not WHICH tuck fires.

## Team convention adopted here: STATUS files

Four report/check crossings in one evening is a protocol problem, not luck, and
polling `ps` only detects *stalled*, never *finished-but-unreported* — which bit
twice tonight. Every long job now writes, next to its results:

    STATUS: RUNNING <pid> <expected artifact>      (at launch)
    STATUS: DONE <artifact> <n> <one-line headline> (at completion)

One `cat` then distinguishes running / stalled / done-unreported without a
round-trip. `tuck_published_vs_best.py` writes `STATUS.tuck_published_vs_best`.

---

# THE EH SIGN: it is a BONUS. The gate gets HARDER, not easier.

The proposed chain — "EH are penalties ⇒ base deflated ⇒ gate easier ⇒ no-op
tucks slip through" — **breaks at the sign step.**

`_g_excav_ship` docstring: "**credit** min(run,3)**2 of the same-color non-virus
run at the TOP of a pile that covers a buried virus." `_g_hang_ship`: "an
occupied non-virus cell with EMPTY directly below whose gap-drop lands on a
matching color -> **+1**." Both are non-negative counts, applied as
`val += w_excav*g_excav + w_hang*g_hang` with `W_EXCAV=24`, `W_HANG=40` — both
positive. **These are bonuses.**

**Measured over 10,800 real base candidates:**

    EH term:  mean +237.4   median +216   min 0   max 728
              fraction > 0: 100.0%    fraction < 0: 0.0%

⇒ base candidates carry a bonus averaging **+237**; tuck candidates carry **0**.
⇒ `best_base_val` is **INFLATED**, so the gate `tuck_val >= best_base_val + θ`
   is effectively `tuck_val >= true_base + ~237 + 150` — an **effective θ of
   ~387 against a nominal 150**, i.e. ~2.6x too strict.
⇒ **The EH omission cannot be what admits no-op tucks. It suppresses firing.**

## The no-op discriminator agrees

Prediction under a correct gate: no-op tucks should be **0%**, since a no-op
tuck's value IS a base placement's value, hence ≤ best_base < best_base + θ.
(That part of the chain is sound and worth keeping — it means the observed 52%
is proof the gate is not functioning *as arithmetic*, not merely mis-tuned.)

Measured on published tucks under the modelled gate, 18 seeds:

    PUBLISHED TUCKS: 41    NO-OPS: 2  =  4.9%

Near-zero, as predicted — **not the co-sim's 52%.** So the co-sim's no-ops come
from something this model does not contain. The model contains: the true
candidate set, the true eval, the documented EH omission, and the θ=150 gate.
What it does NOT contain is the firmware's 16-bit comparison arithmetic.

## ⇒ THE OVERFLOW HAZARD IS PRIME SUSPECT

This is the branch the team lead named: "if instead they're bonuses … something
else is admitting the no-ops — in which case the overflow hazard moves back to
prime suspect." The sign is a bonus, so that is where this lands.

It also explains the θ-inertness that a merely-mis-tuned gate cannot: sweeping
θ from 150 to 20000 changing **0/20 placements** is what a comparison whose
arithmetic saturates or wraps looks like, not what a strict-but-working
threshold looks like (which would monotonically starve tucks).

## Revised causal picture

| component | status | effect |
|---|---|---|
| candidate SET | **better** than the proof enumerator (p=2e-4) | not the problem |
| SELECTION rank | **clean**, 64/64 zero loss | not the problem |
| EH omission | **real**, effective θ ≈ 387 vs 150 | suppresses HOW OFTEN tucks fire |
| θ gate arithmetic | **suspect** — 16-bit overflow | admits candidates that cannot pass; the likely arm-D cause |
| execution | **clean** (co-sim, n_incoherent=0/881) | not the problem |
| root-placement overwrite | **delivery mechanism** | faithfully enacts a bad descriptor |

Fix order: the overflow first (it admits the no-ops), the EH one-liner second
(it restores the intended firing rate). Fixing EH alone would make tucks fire
*less* while still admitting bad ones.
