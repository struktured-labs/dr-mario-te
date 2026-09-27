# hardened-129-133-134 — per-change gate/mutant sheet (2026-08-19)

Cart family (romgen, base `drmario_v28cs.nes` 7d307c30, DRBUILDID=0, manifests in
`roms/manifests/hardened-*.json`, recipe `tools/build_hardened.sh` = tuck-cvc-mister
flag snapshot + deltas):

| cart | md5 | deltas vs ship (9fefaedb) |
|---|---|---|
| hardened-ctrl-ship-20260819 | `9fefaedb…` | none (control == the live-soak CvC tuck cart) |
| hardened-c1-verfix-20260819 | `deeb7d89…` | DRVERFIX=1 (exactly 3 bytes, file 0x14A1-3) |
| hardened-c2-unpause-20260819 | `a359878b…` | DRUNPAUSE=1 |
| hardened-c3-startguard-20260819 | `f6e1671b…` | DRSTARTGUARD=1 |
| **hardened-all-20260819** | **`70a857cc…`** | DRVERFIX+DRUNPAUSE+DRSTARTGUARD+DRROTDIR=1, DRPRESTART=0 |

Every default-off rebuild is byte-identical: `romgen rebuild tuck-cvc-mister.json` →
9fefaedb and `rotdir_on.json` → d1db55ba under the modified emitter. `run_cart_gates.sh`
hazard suites ALL PASS (and gate the pre-push hook).

## Change 1 — #129 DRVERFIX (stock checkVerMatch vertical-scan bound)

3-byte stock edit by unique anchor: `AND #$F8 / BEQ` → `CMP #$80 / BCS` (same length,
branch target byte untouched).

| gate | ctrl | fix | verdict |
|---|---|---|---|
| structural diff vs ship cart | — | exactly 3 bytes at 0x14A1-3 | PASS (asserted) |
| offline A: captured wedge field + $8F r11/r12 (`gate_verfix_sim.py`, predicate **decoded from the cart bytes**) | HANG ×3 | done ×3 | PASS |
| offline B: 4000 random legal boards | — | 4000/4000 byte-identical to ctrl | PASS |
| offline C: legit vertical matches incl. bottom row 12-15 | — | all clear | PASS |
| offline D: edge 4-chain + colour-matching tail byte | ctrl stomps tail (documented original defect) | tail byte untouched, chain clears | PASS |
| offline mutants | m_bound88 → killed by D (after D was REDESIGNED — its first form was vacuous because chains starting below row 12 are never scan starts; the survival was the finding) · m_bcc, m_bne → killed by C | | 3/3 killed |
| real ROM (probe9, arms differ ONLY in $0580-$05FF) | ship+capturedTail **WEDGE** (step pinned 6, field frozen, NMI alive 256 fc values); ship+zeroTail NO_WEDGE | fix+capturedTail **NO_WEDGE** (step/field move at +2f); fix+zeroTail NO_WEDGE, trajectory-identical to ship ctrl (goes=43 dones=41 mode_left=4567 both) | PASS |
| binds in final artifact | — | hardened-all + capturedTail → NO_WEDGE | PASS |

## Change 2 — #133 DRUNPAUSE (stock START semantics for P1)

act_p1 head: raw-latch bit 4 set → write `$F5 = $10` exactly (the byte both pause entry
and the $97D6 exit compare require), skip the synthesized command that hook. Dead code
with no pad attached (soak-neutral).

| gate (probe_d131gate, orient 3 seed 114 — the known #131 wedge phase) | verdict |
|---|---|
| ship + real edged START (`unpause` arm) | STILL_WEDGED (exitTaken=0) — defect reproduced |
| c2 + same intervention | **RESUMED** (exitTaken=1, distinctP2Y=7, goes 11→13) |
| c2 + no intervention (`leak` arm) | STILL_WEDGED — it is the START value, not the cart |
| rule-12 tempo check | wedgeFrame **identical (1471)** in all three arms — no phase-dial confound |
| end-to-end real pad (probe_sg `pause2e`) | c2 and hardened-all: **PAUSED_THEN_RESUMED** (pause on edge 1, ~240 pause iters, resume on edge 2, play continues); ship: **NEVER_PAUSED** (entryHits=0 — the defect cart cannot even pause by pad) |

## Change 3 — #134 DRSTARTGUARD (START injection site guards)

The #131 lesson: a press permitted at the hook-time mode does not protect against the same
frame's 8→4 transit — exclude the predecessor mode.

**Site 1 — autonav `inject()`** (guard: skip the store when live $0046 reads 4 OR 8):

| arm (probe_sg `site1`, mode forced at the guard's own read, restored at an_st_ret) | verdict |
|---|---|
| c3 forced mode 4 | GUARD_HELD (guardHits=301 liveness, staForced=0) |
| c3 forced mode 8 | GUARD_HELD (301, 0) |
| ship forced mode 4 (pre-fix behaviour = the named mutant) | STA_UNDER_FORCE (58/58) — killed |
| hardened-all forced mode 4 | GUARD_HELD |

**Site 2 — fc_clear stage-clear dismiss** (guard: FC_STAB=$61BB must count 4 stable fc
hooks before the first press; cleared every go_ai play hook):

| arm (probe_sg `site2`, VC1 poked to 0 mid-play, NAV_T poked to an open press window at fc entry — adversarial phase) | verdict |
|---|---|
| c3 | **DELAYED_PRESS** (first press hook 33, delay 32 ≥ 4; fcStabMax=4) |
| ship (named mutant) | **IMMEDIATE_PRESS** (first press hook 1, delay 0) — killed |
| function preserved | stage clear dismissed in BOTH arms at identical fcHits=228 — the guard cost the dismiss zero frames here (the blocking wait accepts no press that early anyway) |
| hardened-all | DELAYED_PRESS (same numbers as c3) |

⚠ **What site 2 does NOT show**: pausedDuringFC=0 on the ship arm too — the end-to-end
hazard (an fc press pausing a live match frame) did not reproduce; RB24F's blocking wait
appears to consume the press before any pause check runs. The guard is defense-in-depth
with a suppression-level kill, not a demonstrated-pause-level kill.

**Site 3 — DRNAVESC**: no code change. Structural argument: it already excludes mode 8
(intro hands-off) and fires only after ESC_N (1200) hooks of a completely frozen
($0046,$F8,$0386) state, so it cannot land on a live-play or transit frame; at a frozen
mode 4 its exact-$10 own-the-frame write is the unpause idiom (recovery). **Rule 8: this
site's liveness was NOT re-exercised in this lane** — its original evidence is task #38's
silicon freezes. Named unexercised, deliberately.

⚠ Instrument defect found and fixed mid-gate (commit 615a6d4): Mesen exec callbacks are
**bank-blind** — driver-PC counters included phantom stock-bank executions (ship site1:
566 raw → 58 qualified). All driver-address callbacks now qualified by the DRRTIVEC bank
probe byte ($A02E == $40). Memory: dr-mario-mesen-exec-callbacks-bank-blind.

## Change 4 — DRROTDIR=1 (#114 v3 GO)

In-tree flag, gated on branch rot-exec (PREREG_ROTDIR_V3.md; VERDICT_ROTDIR_V3.txt:
−1.976 f/pill). This cart flips it ON; emission verified (flag in snapshot; 569-byte
delta vs c3). Rule-12 note: DRROTDIR is a tempo shifter = phase dial — any future wedge
on this cart must be checked against the f%30==1 discriminator before blaming a flag.

## Final battery — hardened-all-20260819 (70a857cc)

18,000 frames, leak-patched probe6 (md5 68825189), W=$5200, D135 census guard ON:

- `matches_started=15 matches_ended=14 clean_ends=14 ABORT_4to0=0` — matches cycled the
  whole run, no stall, **wedges 0** (the 15th match was in flight at the frame cap)
- `D135 blocked=10 leaked=0` — the harness-side START-leak guard bound (non-vacuous) and
  leaked nothing
- `MIXED_total=0 MIXED_PRG_nonboot=0 brk_a02e=0 soft8036=2 wipes=14` — no MMC1 straddle,
  no stray BRK; soft8036/wipes in the normal family
- `goes=179 dones=173 pills=164` — healthy search cadence; tuck path live
  (`tuck_pub=1 TUCK_EXEC_D1=1 TUCK_EXEC_D2=1`)
- plus, same cart: probe9 arm NO_WEDGE · `unpause` RESUMED · site1 GUARD_HELD ·
  site2 DELAYED_PRESS · pause2e **PAUSED_THEN_RESUMED** (the end-to-end demo)

## Not proven (staging only — this cart goes on NO SD tonight)

- Silicon behaviour: everything above is Mesen (driver-only rig — the Lua copro serves the
  mailbox; copro firmware is NEVER executed here, rule 10). Pairs with the DBLCANON cores
  (b03a586e firmware) but that pairing is untested on hardware.
- Site 2's end-to-end pause hazard (see above) and site 3's liveness (see above).
- DRPRESTART stays 0 pending #136's latency verdict.
- DRUNPAUSE on a HUMAN cart is deliberately not emitted (HUMAN_P1 already passes through).
