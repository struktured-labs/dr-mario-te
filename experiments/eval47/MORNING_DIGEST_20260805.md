# Morning digest — overnight campaign, 2026-08-04 22:00 → 2026-08-05 03:50

One night, seven agent-lanes, every headline verified before it was believed.
Everything below is committed and pushed; per-item pointers inline.

## THE SILICON MANIFEST (the one build the night converged on)

1. **Tuck-BFS integration with the TIER-3 descriptor** — the night's prize.
   The 6502 BFS port went bit-exact (200/200), got wired behind
   DRCOPRO_TUCKBFS (byte-identical off), fired real tucks in a full game and
   WON by full clear. The execution-vocabulary collapse (offline win didn't
   transfer to the executable subset) was diagnosed and priced: **tier-3
   motion vocabulary (any approach column, ≤1 direction change) recovers
   100% of the oracle, bit-for-bit, for ~150-250B code + 128B RAM.**
   Path-playback (tiers 4/5) proven worthless on three corpora — never build.
   Honest scope: cite the mechanism + the pills value (−23.5 REAL under
   pressure); the pressure-DEATH cure vs honest human cadence is a wash at
   n=120 — that question re-runs under dr_lulu's fitted model.
   (branch tuck-bfs-6502; REACH_ROOT_VERDICT.md iterations 1-5)
2. **Stale-ARMED2 driver fix** (freeze remedy, unchanged priority).
3. **Black-screen family instrument** — NEW: pre-death RAM snapshot ring or
   core watchdog. The soak measured 6 freezes/32h: 4 mid-play, 2 black-screen
   (the latter clustered late-uptime → leak hypothesis, REBUILD.md).
4. **Build-provenance stamping** — DONE in driver-nav already: manifests now
   snapshot the full flag env (future default changes can't break replay);
   DRBUILDID puts "V6BH F5F0"-style artifact-derived tags on screen.
5. NOT in the manifest: DRDISTGATE (demoted to insurance — only binds at
   Y=0 under measured constants), reactive reweight (clean negative, duty-
   cycle collapse), static spawn-time veto (actively harmful).

## THE M3 SUICIDE — the elimination cascade's final state

Not the eval (proxy: its own search ranked the fatal move 24/24). Not a
missing fix (byte fingerprint: the latch fix was in every Pocket cart ever
built; canonical's fix-less driver copy = provenance hazard only, now
structurally closed). Not movement physics (measured from footage: DAS = 12
hooks/edge not 32; the "impossible" 3-column journey costs 36 vs ~40
available). Co-sim: search latency convicts ONLY the final commit (DONE ate
92.5% of its window); commits 1/2/4/5 had 2-12x the needed time and still
parked — **residual mystery, two suspects instrumented but unfinished when
the session limit hit: the Pocket core's true clock (partial:
m3_latency_pocket.json in dr-mario-cosim-wt) and running-best steering
(sim_mister_trace.cpp, unfinished).** First items after reset.

## PRESSURE SCIENCE — three corrections that made the numbers honest

- **Bursty v1 was pool-contaminated**: its volleys included the AI's own
  (the AI is the fastest sender — 90.9% follow-through, matching the ROM
  rule analytically = end-to-end proof the extractor reads true). v1.1
  (human-only): **honest dies-ahead baseline = 7.5%, not 13.3%**; bursty ≈
  2x volume-matched drip SURVIVES; ws=20 helps-not-cures SURVIVES (and
  reads stronger). Failure signature unchanged: ~70% of deaths at the
  doorstep.
- **Per-player separation**: pooled fits were blending opponents (Bidwell's
  "slow match" was Missy; his own follow-through is the ensemble's highest).
  Only struktured's fit clears OK-confidence; ensemble gate NOT ready.
- **DRMC broadcast footage under-detects volleys** structurally: tournament
  SPD outruns 1fps sampling (multi-placement seconds). Fix architecture
  chosen: M2b seed-recovery + analytic ROM rule (#68, daytime).
  ⚠ UNFINISHED (limit): the SPD validity gate for refit_dr_lulu.py — add
  before her session, or eyeball the cells/sec distribution after extraction.

## PLAYER PROGRAM

- jarsdad + bidwell dossiers created (user request) and upgraded same night:
  both found in 2024 Championship White Bracket broadcast footage with
  per-player pressure numbers (properly caveated, LOW-CONF pending more
  segments).
- dr_lulu turnkey kit ready: refit_dr_lulu.py --mkv <file> --suggest-windows
  → fit + side-by-side + first 95%-ladder number. (SPD gate caveat above.)

## CART / SD STATE (user-facing)

- **On the Pocket SD now**: v6 (boardhold) — final board stays visible after
  EVERY match incl. the last, START to advance; settings-screen garble fixed
  (it was our STUDYCOUNTS sprites leaking, not corruption). py65-proven, NOT
  silicon-tested; ~40% frame-budget cost during play — if it hitches, v4 is
  untouched beside it.
- v6b (buildid) staged, not deployed: on-screen "V6BH F5F0" build tag,
  drift-proof by construction. User's call on card churn.
- v5_distgate staged, deploy cancelled (demoted mechanism).
- All cart features merged to driver-nav; test suites made path-portable and
  re-verified green post-merge.

## ALSO SHIPPED TONIGHT

TE v9 published to romhacking.net (user) with verified kit + native-res
screenshot URLs + one-shot release pipeline (/te-release) for next time;
Dr. Mario family AI survey (DM64's decompiled per-character coefficient
tables = the #33 personality design, Nintendo's own; Combo Stomper = first
CPU opponent ever on real NES hardware); main branch consolidated (3
workstreams merged); film-review scorecard + quantitative dossier rebuild
(earlier in the evening).

## OPEN WHEN CAPACITY RESETS (3:50am)

1. cart-fix-builder: finish Pocket clock rescale + convergence trace (the
   4/6 mystery — LAST unknown in the m3 case).
2. tuck-bfs-port: collect the 4 background trajectory games' fire counts
   (processes were nohup'd — results on disk regardless).
3. reactive-mode: SPD validity gate into refit_dr_lulu.py (BEFORE her
   session tonight).
4. Assemble + schedule the silicon session per the manifest above.

---

# DAY UPDATE (2026-08-05 evening) — two lanes, one open number each

## STABILITY: the wedge is OURS, not the platform's (and not the brain's)

Elimination chain, each step verified by screenshot-timeout ground truth:
1. **Our own IPC exonerated** — wedge recurs with tracker + preventive loop
   fully stopped.
2. **Idle exonerated** — 9h19m at MENU, zero wedges. It needs active play.
3. **s20b / CMD-8 exonerated** — the PRE-STRAND20 shipped champion
   (71d2de37) wedged in **6m15s** under identical conditions. Not a
   regression from the #47 work.
4. **MiSTer framework exonerated** — stock NES core + a commercial ROM ran
   clean at 6.5 min, 15 min, and a 3-frame motion test at 17 min. No
   pinned-firmware workaround needed.
⇒ Remaining split, running now: copro core + a NON-CvC human cart. Survives
⇒ the CvC driver's busy pattern (driver fix; booth inherently safe, humans
don't run autonav). Wedges ⇒ copro/mapper-100 RTL (real work before Sept).

★ METHOD RULES adopted (each after a real misdiagnosis): a returned
screenshot proves the display path ALIVE — a wedge is proven by TIMEOUT,
never by frame content; when content is ambiguous, MOTION (3 captures
seconds apart, distinct hashes) is the tiebreaker. Also: the probe's
busy_frac/consec heuristic FIRES ON HEALTHY PLAY — it is an alert, never a
verdict.

## BRAIN: tier-3 candidate built, one gate outstanding

Tier-3 execution vocabulary (any approach column, ≤1 direction change)
ported to 6502 and wired: bit-exact 0/1490 corpus + 0/15 through the real
CANDLIST path; ROM 3581B of 6144B (58%) — tier-2 fallback unnecessary;
3x fire rate vs tier-1 on a matched seed incl. a tier-3-only case; a full
BFS-driven game fired 5 verified tucks and won by full clear.
**Offline A/B vs today's shipped tier-1 vocabulary: bad-ends 19→11, clear
rate 68.3%→81.7%, McNemar p=0.077, pills a wash — DIRECTIONAL, NOT
CONCLUSIVE at n=60.** Residual vs the theoretical oracle: 3/60 seeds, all
losses, cause named (2.3% late-rotation descriptor miss; a 3-phase
descriptor would cost several hundred bytes — next generation, not this
ship). Candidate image `12a0906b…`, shipped hex restored and verified clean.
OUTSTANDING GATE: the tier1-vs-tier3 RTL move diff (smoke test alone was
recorded as sufficient; sent back — "it runs" is not "it acts", a lesson
this program has now paid for twice).

## HONEST STATUS OF THE CHAMPION CLAIM

Not yet a champion. The candidate is built and mostly gated; its offline
evidence is promising but under-powered; and the silicon A/B that would
settle it cannot run until the wedge is fixed — a box that dies every
6-30 minutes under continuous play cannot measure a brain delta.

---

# ⚠⚠ RETRACTION (2026-08-06): THE s20b-vs-s20t3 HARDWARE A/B WAS INVALID

The A/B reported as "a wash, candidate possibly worse" (12.5 vs 18.2 viruses
cleared per 20-min slice) DOES NOT MEASURE THE TIER-3 VOCABULARY. Two
independent confounds, both found by the co-sim agent reading the artifacts
rather than the docs:

1. **THE DEPLOYED CART HAS NO TUCK EXECUTOR.** The probe cart's own manifest
   (roms/manifests/latch-converged-native-probe.json) does not set DRTUCK;
   the emitter at that commit defaults it OFF and gates the whole executor
   behind it — verified by matching the manifest's recorded emitter md5.
   So the driver never reads the tuck descriptor at $5087/$5088.
   ⇒ WORSE THAN INERT for tier-3 specifically: tuck_v3 overwrites
   D_BC/D_BO with the winning tuck's target column, so the cart steers to
   the tuck's column and then PLAIN-DROPS — landing at the straight-drop
   rest instead of the deeper cell the search scored. That is precisely the
   hazard tuck_scan.py's own docstring warns about ("publishing a tuck the
   executor cannot perform is strictly worse than no tuck"). The s20b arm's
   tuck-v1 never touches D_BC/D_BO, so it is a clean no-op.
   ⇒ The candidate arm was running a DEGRADATION MECHANISM. A wash was
   about the best result it could have produced.
2. **THE FLASHED CANDIDATE FIRMWARE WAS MISSING FLAGS.** Hash 12a0906b
   reproduces from DRCOPRO_TUCKBFS=1 + DRCOPRO_TUCKBFS_TIER3=1 ONLY — it
   does NOT carry DRSTRAND=20 or DRCOPRO_ARM=1. So the candidate also lost
   the #47 stranded-half fix and arm-select relative to s20b. The
   matched-flag build is 5d010f62.

**STATUS OF THE TIER-3 QUESTION: UNANSWERED, not negative.** Nothing about
the tier-3 vocabulary's value was measured. The correct comparison needs
(a) the matched-flag firmware 5d010f62, and (b) either a cart rebuilt with
DRTUCK=1 or an explicit two-mode co-sim measurement: `drop` mode
(silicon-faithful — what today's cart does) versus `tuck` mode
(counterfactual — what a DRTUCK=1 cart would buy). The second prices whether
tier-3 justifies a cart rebuild at all.

**Also corrected:** NES_MiSTer-winner/copro_rom.hex was left holding
04b66009 (a tier-1-only fallback probe build) — a stale vendor that would
have silently embedded the wrong firmware in the next fit. Restored to the
committed shipped hash e970e9ab.

LESSON (third manifest-class defect in 48h, after the canonical fix-less
driver copy and the DRBUILDID default drift): **a build's FLAGS are part of
its identity. Verify an artifact's flag provenance from its manifest and its
emitter hash before running any experiment on it — the docs describing a
build are not the build.**
