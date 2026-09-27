# PRE-REGISTRATION: REGIME-GATED d_spawn_h penalty

**Written and committed BEFORE the screen was run.** Date: 2026-08-09.
Rig: `screen_regime.py`, a copy of `screen_quick.py`'s loop with one change (below).
Same 240 topout + 240 clear census seeds (same `SCREEN_RNG = 20260812` sample), same
census-fidelity gate on the base arm, same endpoint and exchange rate as
`PREREG_PHASE2` / `PREREG_DOSE_EXT`.

## Why this shape and not another dose

The flat penalty is CLOSED at all four tested doses (wq 15/30/60/120; net population
bad-ends per 40k = +465 / +202 / +968 / +2381). The structural law from that result:
*any always-on penalty that perturbs clear-game behaviour AT ALL loses at population scale
unless breakage is essentially zero*, because the census ratio is 43 clears : 1 topout, so
one breakage (~159 pop-games) outweighs ~43 rescues (~3.7 each).

`dr-mario-vocab-wall-2` records exactly one shape the law does not cover: a **regime-gated**
penalty, active only under pressure. The hypothesis is that breakages occur in **unpressured**
stretches, where the penalty perturbs healthy play for no reason, while the rescues come from
**post-garbage** windows. Gating should keep the rescue regime and shrink the breakage surface.
**This is not dose fishing** — it is a different functional form, and it is the last shape the
prior verdict leaves open.

## The one change

    val -= wq * max(0, spawn_lane_h_post - 10)      # identical to the flat screen
    ... applied ONLY IF garbage actually landed within the last K placements.

"Actually landed" = `_inject_drip` returned **> 0 halves placed**. The injector silently skips
columns already full to row 0, so an injection event is not the same as garbage arriving;
gating on the schedule rather than on delivery would mis-state the regime on exactly the tall
boards this is aimed at.

Arms: **K ∈ {2, 4} × wq ∈ {30, 60}** = 4 arms, plus the base wq=0 fidelity arm.

## Endpoints — unchanged, fixed now

- **PRIMARY: `net_population_badends_per40k` = 38182·breakage_rate − 890·rescue_rate**
  (the registered exchange rate). **NEGATIVE = net benefit.**
- Bootstrap 95% CI on the net, resampling seeds within each class.
- Secondary: rescues, breakages, treated dies-ahead, changed-trace count.

**Decision rule:** net NEGATIVE at any arm ⇒ that arm graduates to the lulu-model robustness
screen before any further claim. Net POSITIVE at all four ⇒ the regime-gated shape is closed
too, and the penalty route is closed **entirely** — the learned lane (#84) is then the only
remaining route for d_spawn_h, and no further penalty variants should be tried without a new
mechanism, not a new dose.

## ★ DUTY-CYCLE STAT — required, and here is the number to beat

The garbage-reactive mode switch failed previously at **54-79% duty**: a "gate" that is open
most of the time is not a gate, and inherits the always-on failure. Drip injects on
`pills_placed % 8 == 0` (from `GARBAGE_MIN_PILLS`), so the *schedule-predicted* duty is
**K/8 = 25% (K=2) and 50% (K=4)**. Realised duty will be **lower**, because injections that
place 0 halves do not open the gate.

Reported per arm: `duty = fraction of decisions with the penalty ACTIVE`.
**A pre-registered sanity condition, not an endpoint:** if realised duty lands in the
54-79% band, the gate is not gating and the arm's result must be read as a flat-penalty
result, not a regime-gated one.

## Declared in advance

- Base arm (wq=0) must reproduce the census on all 480 seeds or the run is void.
- No new doses beyond {30, 60} and no new K beyond {2, 4} in this pass, whatever the result.
- A net-positive result is a CLOSURE, and will be reported as one.
