# CLEAN-BOARD gate, ITERATION 2 spot check: reach32t divergence-by-height + reachfull2 tuck-value sign

**Date:** 2026-08-05 · **Rig:** `reach_root_ab.py` (control=base32, n=40, L11,
no pressure) + companion `reach_divergence2.py` (same-state divergence
instrumentation, new file, `reach_divergence.py`'s original reach32-vs-base32
version untouched). n=40 per the task's own sizing ("n=40 seeds is enough
here").

## 1. reachfull2 keeps the tuck-value sign

| arm | pills Δ vs base32 (both-won pairs) | 95% CI | verdict |
|---|---|---|---|
| reach32t | +0.00 | [+0.00,+0.00] | WASH |
| **reachfull2** | **-11.15** | **[-19.03,-3.23]** | **REAL** |
| reachfull2t | -11.15 | [-19.03,-3.23] | REAL (identical to reachfull2) |

`reachfull2`'s clean-board cost reproduces the pre-fix `reachfull`'s clean
value (`REACH_ROOT_CLEAN.md`: -10.61 [-15.66,-5.80], n=120) in sign and
similar magnitude — expected, since the fix only changes behavior on boards
where base32's own argmax is unreachable, and clean L11 play essentially
never builds that structure (see part 2 below). This is the acceptance bar
item 3c asked for: the tuck value's sign survives the fix.

`reachfull2t` is byte-identical to `reachfull2` here (same delta, same CI,
`fired_tuck` identical 3.725/game both) — the time-budget filter added
nothing and removed nothing on these 40 seeds.

## 2. reach32t divergence-by-height: ZERO on clean boards, at every height

Companion instrumentation (`reach_divergence2.py`): drives each of 40 seeds
with `reach32t` (its own decisions), and at every decision additionally
computes what `base32` AND `reach32` would have chosen on the IDENTICAL
board/pill state (never used to drive, pure comparison).

| board height | decisions | divergent vs base32 | divergent vs reach32 | fallback_time |
|---|---|---|---|---|
| 0-3 | 20 | 0 (0.00%) | 0 (0.00%) | 0 |
| 4-6 | 411 | 0 (0.00%) | 0 (0.00%) | 0 |
| 7-9 | 1200 | 0 (0.00%) | 0 (0.00%) | 0 |
| 10-12 | 2425 | 0 (0.00%) | 0 (0.00%) | 0 |
| 13-16 | 118 | 0 (0.00%) | 0 (0.00%) | 0 |

**Total: 4174 decisions, 0 divergent from base32, 0 divergent from reach32,
0 fallback_time events, at EVERY height bucket including the tallest (13-16).**

This does NOT satisfy the task's own prediction ("reach32t must diverge from
base32 ONLY on high boards") in the form expected — it diverges NOWHERE, not
even on the tallest boards in this sample. Read together with the M3 case
study (also 0/6 divergence for the time filter) and the bursty-gate diagnostic
(`REACH_ROOT_BURSTY2.md`), the pattern is consistent: under the CORRECTED
DAS constants (`DIST_DASEDGE=12`, `DIST_GRAVROW=30` — see `reach_root.py`'s
own constants comment), the time budget saturates to its 7-edge maximum by
row 3, and the worst-case column distance on an 8-wide board is only 3 edges
— so on STATIC/CLEAN boards (heights measured at decision time, not
mid-fall), the filter has essentially no board shape left to bind on. It
only shows measurable bite under bursty pressure's injected-garbage board
shapes (`REACH_ROOT_BURSTY2.md`), and there it trends HARMFUL, not neutral —
see that report.

## Files

- `reach_root_ab.py` (arms reach32t/reachfull2/reachfull2t added this
  iteration; base32/reach32/reachfull code paths untouched)
- `reach_divergence2.py` (new; same-state divergence-by-height for reach32t,
  parallel to `reach_divergence.py`'s reach32 version)
- `results/reach_root_clean_n40_iter2_{reach32t,reachfull2,reachfull2t}.json`
- `results/reach_divergence2_n40.json`
