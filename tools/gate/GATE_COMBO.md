# GATE SHEET — combined cart #140: DRPRESPIPE(Q=3) + DRP1SLICE, hardened class

**Cart** `roms/combo-hardened-pp3sl-20260820.nes` md5 `2b806db8792ba525d77014f4260b84e1`
= prespipe-hardened-q3 flag snapshot + `DRP1SLICE=1`, `DRBUILDID=0`, romgen manifest
`roms/manifests/combo-hardened-pp3sl-20260820.json`. Base ROM `7d307c30`.
Branch collision-140. 2026-08-20.

Class compatibility: the hardened class already carries `DRP1NATIVE=1` (and
`DRSTARTGUARD=1`), so `DRP1SLICE=1` is structurally legal on it — no TCVC
fallback needed. Prerequisite: the #140 `$61BB` relocation (FC_STAB → `$61C4`),
since STARTGUARD+P1SLICE is exactly the collision config.

## The finding

One hook runs the full driver body for BOTH players, so a pp phase (~10.7k)
and a p1 slice tick (~6k) could share a hook: naive sound bound **35,844 >
29,780** — OVER by ~6k behind two green per-lane certificates (each lane's
scenario model assumed the other machine absent).

## Enforcement: PP_RAN interlock ($61C5)

pre_tick sets the latch on every pipeline-work hook (edge family incl.
swallow/teardown, every phase, bail, commit); the slice dispatch
(`p1s_ppguard`) skips the tick on it; `p1s_idle` clears it unconditionally
each hook. Slice cost while a volley pipeline is in flight: <= PP_NM+2 hooks
of stall (spectator side, anytime-steering class).

## Static gates — tests/test_combo_cart.py (in run_cart_gates.sh, ~0.5 s)

| gate | result |
|---|---|
| C1a DRP1SLICE=0 vs certified 7e73d4a3 | PASS — exactly the 3 FC_STAB operand lows ($61BB→$61C4), nothing else |
| C1b tcvc-p1slice rebuild | PASS — byte-exact 010f4ffe (relocation + interlock invisible on that class) |
| C1c combo deterministic rebuild | PASS — == shipped bytes 2b806db8 |
| C2 interlock premise from the IR | PASS — guard between dispatch and JSR; exactly 5 PP_RAN writers (2 set, 1 clear, 2 init) |
| C3 admissible-frame certificate | PASS — worst 26,587 of 29,780 (89.3%), margin +3,193 [pp_spawn+pp_idle], slice-bearing pairs enumerated |
| C4 cut binds | PASS — tick-cut idle drops by 6,040 ≈ tick bound (not vacuous) |
| C5 M1 guard deleted | KILLED — premise check fails |
| C5 M2 pt_edge set-site deleted | KILLED — premise check fails |
| C5 M3 retired per-lane certification | KILLED — pp-only 23,648 green, naive combined 35,844 OVER |

Companion sheets still green on the new emitter: test_prespipe ALL PASS
(24,854 margin 4,926; unpipelined arm still OVER 35,596), test_p1slice ALL
PASS (tick 1,868 <= 6,029; pair 26,659 < 29,780), test_prg_ram_map ALL PASS
(M1-M4 + M4m), cart hazard gates ALL PASS.

## Play battery — tools/gate/run_combo_battery.sh (drm-coll-battery)

Stage 1: probe6 18k A/B — control prespipe-hardened-q3 (7e73d4a3) vs combo
(2b806db8), marker discipline. Stage 2: forced-release dual liveness
(probe_combo_live.lua, FR=6000): control (sl counters must be ZERO), combo
(pp+sl live, viol==0), NOGUARD byte-patched mutant (viol MUST fire).

### Stage 1 — probe6 18k A/B: GREEN

| | control 7e73d4a3 | combo 2b806db8 |
|---|---|---|
| matches started/ended/clean | 14/14/14 | 15/14/14 |
| goes/dones/pills | 181/173/167 | 179/173/164 |
| MIXED_total / MIXED_PRG_nonboot / brk_a02e | 0/0/0 | 0/0/0 |
| ABORT_4to0 (wedges) | 0 | 0 |
| soft8036 / wipes | 2/13 | 2/14 (normal family) |
| tuck live | pub=1 D1=1 D2=1 | pub=1 D1=1 D2=1 |

Same shape, no drift — the slice flag costs nothing visible at 18k.

### Stage 2 — forced-release dual liveness (FR=6000, poke grid EVERY=600)

| | control | combo | noguard mutant |
|---|---|---|---|
| pokes → release_edges | 6 → 6 | 6 → 6 | 6 → 6 |
| pp starts/completes/aborts | 6/6/0 | 6/6/0 | 6/6/0 |
| GO_near_edge | 6 | 6 | 6 |
| sl starts/completes/ticks | **0/0/0** ✓ | 17/17/252 | 17/17/252 |
| ppran sets/clears | 0/0 ✓ | 30/4229 | 30/4229 |
| viol | 0 | 0 | **0 ⚠ VACUOUS** |
| fc_stuck / wedges | 0 | 0 | 0 |

Control is the perfect reverse-positive (sl and ppran identically zero while
pp lives). BUT the NOGUARD mutant arm came back **byte-identical to combo with
viol=0**: on this workload no pipeline hook ever landed while a slice search
was active (6 pokes vs ~15-hook slice episodes ≈ 4% overlap odds each), so the
interlock was never exercised and the witness never had a chance to fire — the
#126 vacuity lesson, again, caught by the mutant arm doing exactly its job.

### Stage 2b — overlap-FORCED rerun (run_combo_force2.sh: PS_SLONLY=1 pokes
only while SL_PH != 0, PS_EVERY=120; probe reports ov_hooks so zero
opportunity reads VOID, not PASS)

RESULTS PENDING (drm-coll-force2).

## LAST LINE

PENDING STAGE 2b (stage 1 green; stage 2 green except the interlock witness,
which was vacuous on the plain grid and is being re-run overlap-forced).
