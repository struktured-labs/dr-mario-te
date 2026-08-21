# collision-140 lane report (2026-08-20/21) — FINAL, all four tasks done

Branch `collision-140`, worktree `/home/struktured/projects/dr-mario-collision-wt`.
Interim report also sent via SendMessage; this file is the routing-loss backup.

## Task 1 — merge prestart-pipeline-138 into v8-rematch: DONE

Clean merge, pushed as `e842cad` on origin/v8-rematch. `run_cart_gates.sh` ALL
PASS twice (manual + pre-push hook). collision-140 based on the merge.

## Task 2 — the $61BB collision: DONE (commit 9721e25)

Mechanism CONFIRMED empirically before fixing — THREE independent blind spots,
not one (the pipeline lane's reading was right in substance, incomplete):
1. `declared()` kept ONE symbol per address via `dict.setdefault` — SL_PH
   (second declarant) silently dropped; the share was UNREPRESENTABLE in the
   deriver's own data structure.
2. `collisions()` skips every ABSOLUTE store (`if lo == hi: continue`) — all 6
   writers at $61BB were absolute, so even a correct owner map couldn't flag them.
3. No derived config enabled DRSTARTGUARD or DRP1SLICE — the emitted view never
   saw a $61BB writer ("declared, never written" in the map).

Fix: FC_STAB relocated $61BB → $61C4 (single byte, single declaration site;
SL_* block stays contiguous). Deriver: multi-owner declared view, `dup_declared`
finding fails `--check`, 4 new configs (startguard / p1slice / startguard-p1slice
/ prespipe-p1slice). Killed mutants M4 (synthetic two-symbols-one-address fires)
+ M4m (the RETIRED one-owner implementation kept as a named mutant, must be
BLIND). Verified the new check fires on the PRE-relocation emitter. Map: 0
collisions / 0 dups / 0 unbounded. test_prg_ram_map wired into run_cart_gates.sh
(0.1 s). probe_sg.lua default, GATE_HARDENED.md, NMI126_BOUND_REPORT.md updated.

## Task 3 — combined cart DRPRESPIPE(Q=3)+DRP1SLICE: DONE, CERTIFIED

Class check: hardened class carries DRP1NATIVE=1 (and DRSTARTGUARD=1) ⇒
DRP1SLICE structurally legal on the hardened class; no TCVC fallback needed.
The combo IS the $61BB collision config — task 2 was the prerequisite.

**FINDING — the uncovered pairing was a real hazard.** Naive sound
admissible-frame bound on the combined image: **35,844 > 29,780 (OVER by
~6k)** — one hook runs both players' work, so a pp phase (~10.7k) and a slice
tick (~6k) share hooks. Both lanes' certificates were green because each
assumed the other machine absent.

**Enforcement: PP_RAN interlock ($61C5)** — pre_tick latches on every
pipeline-work hook; the slice dispatch skips the tick on the latch; p1s_idle
clears it per hook. Census combined scenarios (guard-proven fallof cut, h2_cp
shape) + slice-bearing pair enumeration: **worst admissible frame 26,587
(89.3%), margin +3,193**.

Cart `roms/combo-hardened-pp3sl-20260820.nes` md5 `2b806db8`, romgen manifest,
DRBUILDID=0. Byte-identity: DRP1SLICE=0 differs from certified 7e73d4a3 in
EXACTLY the 3 FC_STAB operand lows (the relocation), nothing else;
tcvc-p1slice 010f4ffe rebuilds byte-exact; hardened-prestart snapshot rebuild
= 4ac725cf mod the same 3 sites. (The literal "DRPRESPIPE=0 vs
hardened-prestart" comparison is ill-posed — DRNAVDWELL differs between those
snapshots; the snapshot-faithful rebuild above is the valid form of the check.)

Gate `tests/test_combo_cart.py` (wired into run_cart_gates.sh): C1-C5 ALL
PASS, killed mutants incl. the RETIRED per-lane certification (C5 M3) and the
guard-deletion mutants. test_prespipe + test_p1slice still ALL PASS. See
tools/gate/GATE_COMBO.md.

C1a upgraded per team-lead ruling: the flags-off diff set is bound to the
IR-DERIVED FC_STAB operand set (count AND positions, delta-consistency-checked
— not a hardcoded 3); 010f4ffe asserted exact.

Battery results (full tables in tools/gate/GATE_COMBO.md):
- probe6 18k A/B GREEN: combo 15/14/14 matches vs control 14/14/14, both
  MIXED 0 / ABORT_4to0 0 / brk_a02e 0, same goes/pills shape, tuck live.
- Forced-release dual liveness: control arm reverse-positive (pp 6/6 with
  sl/ppran identically ZERO); combo pp+sl both live, viol=0, no wedges.
- ⚠ First witness run was VACUOUS — the NOGUARD mutant arm came back
  byte-identical to combo (no pipeline hook ever overlapped a slice episode
  on the 600-frame poke grid). The mutant arm caught its own vacuity, per its
  job. Stage 2b (PS_SLONLY=1 pokes only while SL_PH!=0, EVERY=120, new
  ov_hooks opportunity counter so zero-opportunity stamps VOID):
  **combo ov_hooks=8 viol=0; NOGUARD ov_hooks=7 viol=6 — witness fires on the
  mutant, holds on the ship candidate.** Abort path also exercised (1 each).

VERDICT: combo-hardened-pp3sl-20260820 (2b806db8) CERTIFIED as the
next-generation hardened-class candidate.

## Task 4 — worktree-relative gate scripts: DONE (commit cfcc8c2)

run_probe6_hardened.sh's hardcoded D was one of **52** scripts with the same
latent binding (targets: v8-wt, pipeline-wt, rotexec-wt, dispatch131-wt,
hygiene-wt, pockettuck-wt). All now resolve
`D=$(git -C "$(dirname "${BASH_SOURCE[0]}")" rev-parse --show-toplevel)` with
an emitter-exists liveness check (wrong resolution fails loud). bash -n clean
on all; resolution demonstrated from both collision-wt and v8-wt copies.
score_d115.sh's /tmp/d115 suffix preserved.

## Commits

- e842cad merge prestart-pipeline-138 → v8-rematch (pushed to origin/v8-rematch)
- 9721e25 $61BB fix + deriver dup detection + killed mutants
- cfcc8c2 52-script worktree-relative sweep
- 5e1f744 combined cart + PP_RAN interlock + certificate + test_combo_cart
- b39de46 battery rig (probe_combo_live.lua + run_combo_battery.sh)
- bee3cc9 C1a bound to the IR-derived FC_STAB operand set
- (next) battery results + overlap-forced witness (run_combo_force2.sh) + final sheet
