# hardened-prestart-20260820 — DRPRESTART=1 variant gate sheet (2026-08-20, variant lane)

Cart: `roms/hardened-prestart-20260820.nes` md5 **4ac725cffe84c547b358e3700e6df04d**
(98320 bytes), manifest `roms/manifests/hardened-prestart-20260820.json`.
Recipe: `tools/build_hardened.sh hardened-prestart-20260820 DRPRESTART=1` at d14e869 —
i.e. the 70a857cc hardened-all flag set (DRVERFIX+DRUNPAUSE+DRSTARTGUARD+DRROTDIR=1,
DRBUILDID=0, base 7d307c30) with the single delta **DRPRESTART=1**, built after #136
returned SURVIVES (spawn-ready 97.99% [97.22, 98.68] vs bar 89.4). #136 certifies the
latency BUDGET only; no measurement rig runs the DRPRESTART driver code — this sheet's
play gates on the flag-ON build are the functional evidence (rule 6).
romgen determinism verified (two builds byte-identical). dirty:true = the same ten
pre-existing untracked non-input files as 2026-08-19 (MANIFEST_ERRATA.md, 20260820 entry).
**70a857cc (hardened-all-20260819.nes) untouched** — keep-versions; it remains the
DRPRESTART=0 ship candidate.

## Battery (raw lines in GATE_PRESTART_20260820_raw.md; params identical to the
## 70a857cc final battery; run under systemd unit drm-variant-battery, gates serialized)

| gate | verdict | vs 70a857cc reference |
|---|---|---|
| G1 probe6 18,000f (leak-patched, W=$5200, D135 guard ON) | **PASS** — matches 15 started / 14 ended / 14 clean, ABORT_4to0=0 (wedges 0); D135 blocked=10 leaked=0 (bound, non-vacuous); MIXED_total=0 MIXED_PRG_nonboot=0 brk_a02e=0; soft8036=2 wipes=14 (normal family); goes=178 dones=172 pills=163; tuck live (tuck_pub=1, TUCK_EXEC_D1=1, TUCK_EXEC_D2=1) | 179/173/164 — same shape, no drift |
| G2 probe_sg pause2e 9,000f | **PASS** — PAUSED_THEN_RESUMED (entryHits=1, pauseIters=240, exitTaken=1, distinctP2Y=6) | identical numbers |
| G3 hgate `unpause` o3 s114 4,000f | **PASS** — RESUMED (exitTaken=1, distinctP2Y=7, pauseIters=304, wedgeFrame=1471) | wedgeFrame identical (1471) — the #131 wedge phase did NOT move under DRPRESTART=1, so rule 12's phase-dial concern is moot for this arm; navStartHits 34 vs 6 = the expected DRPRESTART mid-board nav starts, not a fault |
| G4 probe9 arm 9,000f + captured wedge tail (wedge129_ram.hex) | **PASS** — NO_WEDGE (fc_values=256, step/field move at +2f, mode_left_at=-1) | identical shape (goes=47 dones=45 both) |

Rule 12 note: DRPRESTART is a tempo-shifting flag (phase dial). No run wedged, so the
f%30==1 discriminator had nothing to adjudicate; recorded here so a future wedge on this
cart is checked against it before the flag is blamed.

## Not proven (STAGED only — this cart goes on NO SD)

- **Silicon**: everything above is Mesen (driver-only rig; the Lua copro serves the
  mailbox — copro firmware never executes here, rule 10). The DBLCANON-core pairing is
  untested on hardware for this cart.
- #136's latency margin is a budget certificate on the shipped firmware generation, not
  an execution of the DRPRESTART driver path on silicon.
- Everything the 70a857cc sheet lists as unproven (site 2 end-to-end pause hazard,
  site 3 liveness) is equally unproven here.

**Disposition: STAGED. 70a857cc remains the ship candidate; this variant is a
gate-green candidate awaiting owner promotion.**
