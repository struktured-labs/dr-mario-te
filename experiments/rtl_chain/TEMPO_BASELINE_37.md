# Task #37 baseline memo: closing the human tempo gap

Assembled read-only from existing data on disk. No new measurements were taken. Every
number below is cited to its source file; anything not on disk is marked **UNMEASURED**.

---

## 1. Current AI per-pill time budget at L11 (shipped `stomp180` / Combo Stomper arm)

Three components, all at 60.1 fps NES-frame time:

| component | value | source |
|---|---|---|
| natural-fall time, full-column drop (R≈13 rows × 13 f/row) | **169 f ≈ 2.81 s** | fall model, `dr-mario-mods/tmp/tempo/TEMPO_DESIGN.md` §2.1 (13 f/row measured zero-variance in Mesen, L11) |
| slam-path time (13 rows × 2 f/row) | **26 f ≈ 0.43 s** + overhead | same, soft-drop 2 f/row measured speed-invariant |
| search time (DONE latency, shipped `stomp180` arm, 69-board corpus) | median **48.3M clocks ≈ 33.7 f ≈ 0.562 s**; p90 59.2M≈41.3f/0.687s; p95 63.4M≈44.3f/0.738s; max 81.9M≈57.2f/0.953s | `dr_mario_rl/tmp/rtl_chain/donelat/dist69.log` + `dr-mario-qa-wt/experiments/rtl_chain/README.md` "DONE latency" table |

**Overlap:** the shipped driver is anytime (`DRNOFREEZE`/no-pin steering): while `ARMED2!=0`
(still searching) it weave-steers toward the live mailbox target **at natural gravity**,
never fast-dropping. So search time is *not* additive with fall time — it overlaps the
natural-gravity descent up to whatever row the pill has reached when DONE fires
(`patch_cartridge_copro.py:395-430` comments; `TEMPO_DESIGN.md` §1). Given the current
search medians (0.56 s) versus a full natural fall (2.8 s), search comfortably finishes
before the pill lands in the common case — the open question is what happens *after* DONE
fires, addressed in §2.

⚠ **Discrepancy worth flagging for the retune session.** `TEMPO_DESIGN.md`'s whole tempo
model (§2.3, §7 payoff table, the 34→56 PPM estimate) is built on an assumed `T_s ≈ 60 f ≈
1 s` ("README depth-3 steady state" at the time it was written, pre-chain). The now-measured
`stomp180` search is **faster** than that assumption (median 33.7 f ≈ 0.56 s), while the
README's own DONE-latency section separately states chain180 runs **~1.8x** the deployed
non-chain (`751b6ce9`) arm's latency. Both can be true if `TEMPO_DESIGN.md`'s 60f figure
predates a search-side speedup that happened independently of the chain engine; the point
for #37 is that **the confidence-gate payoff numbers in TEMPO_DESIGN.md were computed
against a different, unreconciled T_s than the one on disk today** and should be
recalculated from `dist69.log`'s stomp180 distribution, not carried over.

---

## 2. Current slam gating: constants, requirements, estimated arming fraction

Source: `dr-mario-mods-wt/driver-nav/patch_cartridge_copro.py` (search terms: FAST_HI, SLAM,
MIN_THINK, K_OPEN).

| constant | shipped value | meaning | line |
|---|---|---|---|
| `MIN_THINK` | 25 hooks | no lateral/orient commit until DONE or 25 hooks of search elapsed | :187 |
| `SLAM` | on (`DRSLAM=1` default) | confidence-gated-slam machinery is compiled in | :194 |
| `FAST_HI` (`DRSLAM_MATURE`) | 2 | arm slam iff **last** search DONE'd in < `FAST_HI*256` = 512 hooks | :218 |
| `K_OPEN` (`DRSLAM_KOPEN`) | **255** | opening/mid stability-K, in hooks — **255 = "require DONE"** | :413 |
| `K_END` (`DRSLAM_KEND`) | **255** | endgame stability-K — also "require DONE" | :414 |
| `K_CROSS` (`DRSLAM_KCROSS`) | 8 | stability-K **past the feasibility crossover** (capsule already low, Y<`CROSS_LOWY`) | :415 |
| `VC_ENDGAME` (`DRSLAM_VCEND`) | 10 | virus-count threshold splitting opening/mid vs endgame regime | :416 |
| `CROSS_LOWY` (`DRSLAM_LOWY`) | 8 | row threshold for the feasibility-crossover escape | :427 |

**The central finding for #37:** `TEMPO_DESIGN.md` designed and the driver *implements* a
confidence-gated slam (commit once the mailbox argmax has held stable for K hooks, rather
than waiting for full DONE) — but the two production stability gates, `K_OPEN` and `K_END`,
are both set to **255**, which the driver's own comment (`:402-406`) glosses as **"require
DONE."** Only `K_CROSS=8` (the late-drop feasibility escape, when the capsule is already
too low to keep waiting) uses a small, tempo-favoring K. Per that same comment block, this
is not an oversight — task #40's sweep found that a low K (tested at 40) at the *current*
fast copro cadence commits a "shallow decoy" before the search converges, causing a
strength regression; `K=255` was chosen to restore optimal placement quality
(`:405-407`, "K=255 lands optimal at ~v2 tempo"). **So the shipped AI today runs at
"slam-when-done" tempo, not confidence-gated tempo** — the ~0.56–0.68 s/pill savings modeled
in `TEMPO_DESIGN.md` §4/§7 are currently **not realized in the shipped configuration.**

**Estimated arming fraction (of the FAST_HI gate, not K_OPEN/K_END):** no direct log
evidence of measured on-hardware arm/disarm rates exists on disk — **UNMEASURED**. But the
driver's own audit comment (`:207-217`, dated 2026-08-01) computes the two relevant worst
cases against the 4.27 s (512-hook) `FAST_HI` threshold:

| platform | search time | fraction of `FAST_HI` threshold | arms? |
|---|---|---|---|
| MiSTer, chain180 @ 85.909 MHz | 0.78 s (quoted; consistent with `dist69.log`'s p90≈0.687s/max≈0.953s) | 18% | yes, comfortably |
| Pocket, chain180 @ 54.669 MHz | 1.23 s (projected, not measured) | 29% | yes, comfortably (projected) |

So `FAST_HI` should arm on essentially every pill at both platforms' current latencies —
the binding constraint is `K_OPEN=K_END=255`, not `FAST_HI`.

⚠ **Second discrepancy for the retune session — the hook-rate correction may not have
propagated everywhere.** The same file's 2026-08-01 audit (`:145-166`) established, by
tracing the single NMI call site, that **the driver hook runs 2×/frame, measured** —
correcting an older assumption of "~5 hooks/frame" that the comment says was previously
used to compute `FAST_HI`'s wall-clock meaning (old note: "512 hooks ≈ 1.7 s", corrected to
4.27 s). That correction was explicitly applied to `FAST_HI`. But `MIN_THINK`'s own
derivation comment (`:178-186`) and the `K_OPEN/K_END/K_CROSS` block's comment (`:396-399`)
**still read "~5 hooks/frame"** — e.g. "Default 25 (~5f)" for `MIN_THINK`, and "K is in
HOOKS... ~5 hooks/frame" for the K-gates. At the corrected 2 hooks/frame, `MIN_THINK=25`
hooks is **~12.5 f**, not ~5 f — 2.5x longer than the comment states. This should be
re-audited before #37 retunes any K constant, since the whole K-in-hooks-to-seconds
conversion depends on which rate is right, and only one of the three derivation comments in
this file has been corrected against the measured 2/frame rate.

---

## 3. The early-commit evidence: settle-fraction stats → theoretical earliest safe slam point

Source: `dr_mario_rl/tmp/rtl_chain/agree/AGREE_RESULT.txt` (69-board corpus, shipped
`stomp180` arm; two independent gates — non-perturbation max 48-clock peek residue, and
100% address-match on 69/69 — both PASS, so the convergence curve below is trustworthy).

- **Settle fraction** (clock of last change to the published move, as a fraction of total
  search time): min 0.0018, **median 0.0356**, p90 0.298, p95 0.470, max 0.774.
- **First-answer fraction** (clock the first candidate publishes): min 0.00178, median
  0.0333, p90 0.0371, max 0.0414 — i.e. a first candidate is on the mailbox by ~4% of the
  search, on every board sampled.
- **Publishes per search:** min 2, max 9, mean 3.9.
- **Agreement vs. completion fraction** (commit best-so-far at fraction f of the search,
  compare to the final DONE move):

  | f | agree | differ | % agree |
  |---|---|---|---|
  | 0.05 | 45 | 24 | 65.2% |
  | 0.20 | 57 | 12 | 82.6% |
  | 0.50 | 66 | 3 | 95.7% |
  | 0.70 | 68 | 1 | 98.6% |
  | 0.80+ | 69 | 0 | **100%** |

- **Pocket-budget check:** at the Pocket's 72.9M-clock deadline, 68/69 boards finish
  outright; the one that doesn't (board 58, 81.9M clocks) is 89.0% complete and **still
  commits the same move**. Forcing every board to that 89% completion fraction still gives
  69/69 agreement.

This is the independent, RTL-measured confirmation of `TEMPO_DESIGN.md`'s offline-sim
finding (§2.2, median stabilization at candidate 1 of 3.9 mean publishes, 80.6%
"wasted"/confirmatory search time): **the search commits to its final answer very early —
by 80% of the way through on every board sampled** — which is the empirical basis for a
confidence-gated slam being viable at all. The theoretical earliest safe point (where
disagreement first hits 0%) is **f≈0.80** on this 69-board sample; f≈0.30–0.50 already
buys 91–96% agreement, which is the range `TEMPO_DESIGN.md`'s K-sweep (§4.3, K=6 → 78%
exact-optimal / 72% search-time reclaimed / 0.2% win-throwing) explores from a different
angle (candidate-count K rather than time-fraction f). These two datasets (offline Python
sim vs. on-RTL AGREE trace) agree in direction and rough magnitude, which is useful
corroboration but they are not the same measurement — `AGREE_RESULT.txt` is move-identity
agreement at time-fraction f; `TEMPO_DESIGN.md`'s table is quality-loss (`gap` vs. final
eval value) at candidate-count K. #37 should pick one metric and re-run it against current
`stomp180` latencies before setting production K/f thresholds.

---

## 4. Human baseline

**No per-pill timing data for human play exists on disk.** Searched
`dr-mario-qa-wt/docs/`, `dr-mario-qa-wt/experiments/`, and broadly across
`dr_mario_rl/tmp/` and `dr-mario-mods*` for M2b, "frames per pill," "pills/min," "PPM," and
tournament-footage timing — nothing quantifies human spawn-to-lock time or placement
cadence. The M2b vision corpus that does exist
(`dr_mario_rl/.claude/worktrees/faithful-sim/tmp/vs_eval/decline_ab_visionm2b.py`,
referenced in memory as "M2b corpus run") measures **attack-given-clear rate** (17.1%, ~2x
the AI), not tempo — it has no frame-timing fields.

The one human-tempo data point on disk is a **bound, not a measurement**:
`TEMPO_DESIGN.md` §2.4 reports a 5.6-minute personal recording
(`/mnt/data/drmario/expert_vods/personal-recordings/…struktured_vs_bidwell.mov`) exists but
is marked **never-publish** (handheld off-screen footage, "hardest-tier OCR material" per
its own manifest) and OCR was explicitly skipped per the originating task's "skip if heavy"
guidance. In its place, §2.4 gives a **physics-derived** bound: a human on an obvious
placement ≈ the table's "immediate slam" column, **≈ R·2 frames + reaction ≈ 0.4–0.9 s
spawn-to-lock** for R = 8–15 rows. This is presented explicitly as the target the bot should
approach, not a measured human rate.

**UNMEASURED — what #37's bench session needs:** an actual per-pill cadence extracted from
either (a) OCR/frame-counting a publishable VOD (the personal recording is off-limits by its
own manifest), or (b) a live-timed human session against the emulator/cart, reading
spawn-to-lock frame counts directly. `TEMPO_DESIGN.md` §9 flags the same gap ("a rough
placements-over-match-duration cadence from the footage is available on request if wanted"
— that request was never made / no output exists on disk).

---

## 5. The gap estimate

Using `TEMPO_DESIGN.md`'s §2.3/§7 model (caveat: built on its own `T_s≈60f` assumption,
see the §1 discrepancy note above — treat these as directionally right, magnitude-soft
until re-derived from `dist69.log`):

| regime | shipped today (K_OPEN=K_END=255, i.e. "slam-when-done") | confidence-gate design target | human physics bound |
|---|---|---|---|
| typical mid-game (R=12, n=13 f/row) | **75 f ≈ 1.25 s/pill** | 34 f ≈ 0.56 s/pill | 24 f ≈ 0.40 s/pill |
| opening (R=15, n=19 f/row, speedup 0) | 81 f ≈ 1.35 s/pill (table) / up to 4.12s no-slam-equivalent early | 40 f ≈ 0.66 s/pill | 30 f ≈ 0.50 s/pill |
| late (R=8, fast gravity) | 67 f ≈ 1.11 s/pill (or collapses to no-slam past the feasibility crossover, §2.5) | 26 f ≈ 0.43 s/pill | 16 f ≈ 0.27 s/pill |

(Sources: `TEMPO_DESIGN.md` §2.3 table and §2.5 gravity-curve table; "shipped today" column
is that table's "slam-when-done (shipped v2)" row, which is what `K_OPEN=K_END=255`
currently reproduces on the real driver per §2 above.)

**Frames-per-10-pills tempo owed, mid-game regime:**
- Shipped-today vs. confidence-gate target: (75−34) f/pill × 10 = **410 frames ≈ 6.8 s per
  10 pills**.
- Shipped-today vs. human physics bound: (75−24) f/pill × 10 = **510 frames ≈ 8.5 s per 10
  pills**.
- Confidence-gate target vs. human physics bound (residual gap even if #37 fully lands
  Design A): (34−24) f/pill × 10 = **100 frames ≈ 1.7 s per 10 pills**.

`TEMPO_DESIGN.md` §7's own PPM estimate (34 PPM shipped-v2-equivalent → 56 PPM gated, +65%)
and race-to-clear estimate (≈44 s faster over a ~110-pill safe-first race, up to ≈75 s
full-aggressive) describe the same gap in match-clock terms. **Caveat, restated:** all of
these numbers assume the pre-chain `T_s≈60f` search latency; #37 should re-run this
arithmetic against the measured `stomp180` distribution (`dist69.log`: median 33.7f, p95
44.3f, max 57.2f) before treating any of these as tuning targets, and should re-derive the
hook→frame conversion for `MIN_THINK`/`K_OPEN`/`K_END`/`K_CROSS` at the corrected 2
hooks/frame rate (§2 above) rather than the ~5 hooks/frame figure baked into their existing
derivation comments.

---

## 6. OPEN MEASUREMENTS — what #37's bench session must measure first

1. **Re-run the `TEMPO_DESIGN.md` §2.2/§4.3 stabilization and K-sweep analysis against the
   `stomp180` search, not the pre-chain search it was originally built on.** The 69-board
   `AGREE_RESULT.txt` corpus already has move-identity agreement vs. time-fraction; what's
   missing is the *quality-loss* (`gap` vs. final eval value) at each K, on this specific
   arm's boards — `TEMPO_DESIGN.md`'s existing gap/K table (§4.3) is from a different,
   pre-chain engine's decisions.
2. **Re-derive `MIN_THINK`, `K_OPEN`, `K_END`, `K_CROSS` in real frames using the
   corrected 2-hooks/frame rate**, not the "~5 hooks/frame" figure still present in their
   derivation comments (`patch_cartridge_copro.py:178-186`, `:396-399`) — only `FAST_HI`'s
   comment has been updated to the measured rate.
3. **Measure whether `K_OPEN=K_END=255` (current shipped, DONE-only) can be safely lowered
   now that `stomp180`'s latency and the hook-rate are both re-baselined**, re-running
   task #40's sweep methodology (which found K=40 regressed quality) at the corrected
   hook-rate and current search-latency distribution — task #40's negative result may be
   an artifact of the same stale hook-rate assumption.
4. **A human per-pill cadence measurement.** Nothing on disk quantifies it. Either OCR/
   frame-count a publishable (non-never-publish) VOD, or run a live timed session — spawn
   frame vs. lock frame, several dozen placements, ideally split by game phase like the
   AI-side tables above so the comparison is apples-to-apples.
5. **Confirm the FPGA candidate-publish rate on hardware** (`TEMPO_DESIGN.md` §9 open
   question — "is ~2 f/candidate right on hardware?"), since the K→frames conversion for
   any confidence-gate retune depends on it and it was never confirmed against RTL, only
   assumed from the Python reference decider.
6. **Pocket-side DONE latency is still projected, not measured** (`1.23 s` figure in
   `patch_cartridge_copro.py:213` is explicitly "(projected)") — the Pocket's slower
   54.669 MHz clock means its `FAST_HI`-threshold headroom (29% vs. MiSTer's 18%) should be
   confirmed on real Pocket hardware before assuming the same slam-arming behavior across
   both platforms.

---

**Output:** `/home/struktured/projects/dr-mario-qa-wt/experiments/rtl_chain/TEMPO_BASELINE_37.md`
(this file — not committed, per instructions).
