# Pre-registration: exogenous-pressure sensitivity for the oracle ceiling

**Frozen 2026-08-11 before this pressure mode was implemented or run.**  The
already-running 9,000-pair ORACLE-CLAIR job remains sealed at `29fc72c`; this
document neither edits it nor gives a new pilot retrospective authority.

## Why this sensitivity is required

The existing solo "Lulu" rig does not have a second board.  It therefore feeds
the receiver AI's **own** clear size into a model whose literal conditioning
variable is the **opponent sender's** clear size.  Its random key is common at a
given `(seed, pills_placed)`, but the firing probability is not:

```text
p_fire = lulu_model.fire_probability(receiver_own_clear_size)
```

The receiver policy controls that clear size.  Once two arms choose different
moves, they no longer face a common pressure schedule.  The oracle forks have
the same problem: a candidate can change the attack realization it is being
scored against.  This contradicts the "pure function of `(seed,
pills_placed)`" statements in `PREREG_ORACLE.md`, `oracle_arm.py`, and
`run_oracle.py`.

The fitted dr. lulu table makes the issue capable of changing decisions, not
merely nomenclature: its observed firing probabilities are 0.40764 for a 4--6
cell clear, 0.56250 for 7--10, and 0.0 for 11+ (the last bin has only n=2).
Those are sender-style estimates.  Applying them to the receiver makes its own
large clear suppress its next incoming volley.

This sensitivity asks a narrower, causal question: **does the oracle signal
survive when both arms and all top-4 forks receive the same offered pressure at
the same pill index?**

## Frozen exogenous schedule (`exo_lulu_v1`)

For every eligible receiver placement (`pills_placed >= 25`), construct one
immutable pressure offer from only:

```text
(schedule version, game seed, pills_placed)
```

The receiver board, receiver action, receiver clear size, candidate identity,
arm, and terminal label are not inputs.

1. A stable SplitMix64 key produces an integer in `[0, 1_000_000)`.  A volley
   is offered iff it is below **187,891**.
2. On a firing pill, independently keyed deterministic draws sample the volley
   size from the fitted dr. lulu empirical `volley_sizes`, the number and set of
   columns with the existing `BurstyPressureModel.sample` rule, and all offered
   cell colours up front.
3. Applying an offer may land fewer cells when a receiver column is physically
   full.  That is a response of the receiver state to the same external offer,
   not a changed schedule.  Skipping one full column must not change the colour
   offered to another column.
4. Settle and resolve with the same board physics used by the current bursty
   hook.

The firing dose was fixed from trace fields that existed before this document,
not from any treatment endpoint: 89,220 of 474,851 eligible decisions in the
local stage-2 corpus landed nonzero garbage, **0.1878905172**.  The frozen
rational is the nearest six-decimal value.  The three source NPZ SHA-256 values
are:

```text
ctrl  35589afd668b0ccc311264fe4a2232f5fe1b0f2d28a05671492b845905458d91
fail  9bced8814e54e14af78fe9a3e5d99dfa59e7f86f950da1cd16c8f33cd961ed21
stall db9f7a5a92fb27fc8be72049b9612092f63fc2820ab0b1ea8a49e97c977752f6
```

This matches event dose, not labels.  Class selection in that corpus can bias
the rate, so this is a sensitivity environment, not a claim to have recovered
dr. lulu's real-time cadence.

## Gates, including red sides

All must pass before any endpoint pilot is read.

1. **E1 schedule determinism/exogeneity.** Repeated calls and distinct
   receiver-clear annotations at the same `(seed, pill)` produce an identical
   complete offer.  A deliberately wrong coupled-clear mutant must produce at
   least one different fire decision over clear sizes `{4, 7, 11}` at a common
   key.
2. **E2 colour precommitment.** Applying one offer to boards that differ only
   by a full offered column may change the landed count, but it must not change
   any other column's offered colour.  A deliberately wrong apply-time colour
   draw (whose RNG consumption skips full columns) must fail this check.
3. **E3 OFF identity.** `exo_lulu_v1` base is deterministic on repeat, and the
   const-label oracle reproduces its own champion reference action-for-action
   and endpoint-for-endpoint.  A reversed tie-order mutant must fail, as in the
   sealed oracle gate.
4. **E4 dose sanity.** On the frozen block **seeds 50,000--50,059 (N=60),**
   run the const-label champion once under coupled Lulu and once under
   `exo_lulu_v1`; print offered-event rate,
   offered cells/eligible ply, landed cells/eligible ply, and the coupled
   reference.  This is descriptive.  If the exogenous landed dose is outside
   0.90--1.10x the coupled dose, endpoint comparison is `DOSE_INVALID` until the
   firing threshold is re-registered; it may not be interpreted as a pressure
   sensitivity.
5. **E5 paired environment.** At every pill index reached by both arms, their
   offer hashes must match.  An arm-keyed schedule mutant must fail.

## Endpoint authority and interpretation

The first run is a smoke/pilot only and cannot produce GO.  A full endpoint run
must pre-register its seed block, N, paired power, true/shuffled flip-dose
calibration, and clear/stall/topout verdict rules separately.

The running coupled ORACLE-CLAIR result is interpreted as an ideal re-ranker in
the historical self-coupled pressure proxy.  It does **not** close root
re-ranking for real head-to-head play, regardless of sign.

If the coupled and exogenous directions disagree, the proxy is mechanism-
sensitive and no lane-closing claim is allowed until a powered exogenous or
ROM-true two-board experiment resolves it.  If they agree, that is robustness
evidence but still not a proof over candidates outside top-4, horizons beyond
15, or actual dr. lulu gameplay.

The north-star gate remains ROM-true, side-swapped head-to-head win rate against
a fixed opponent.  `exo_lulu_v1` repairs causal pairing in the existing solo
endpoint; it does not replace that north star.
