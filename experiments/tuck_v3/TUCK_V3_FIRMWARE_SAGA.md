# Tuck v3 firmware saga (task #17, stage 3)

## End position

**The root-action tuck design is validated under the true evaluation. The
firmware implementation does not reproduce that validation. The gap between
them is behavioral, not statistical** — more data will not close it; a
mechanism will.

`TUCK_V3_OFFLINE.md`'s phase-2 recommendation (θ\*=150, "unconditional go on
the offline evidence") was computed under `fast_rtl_x.py`'s `variant("winner")`
eval weights. Those weights are NOT the weights the real firmware runs (the
real leaf eval lives entirely in RTL, `LeafEval.sv` S_DONE2, ported faithfully
to python in `fpga/copro/leaf_r47.py`). When the SAME offline root-action
design is re-scored under the RTL-faithful leaf, it is REAL at every θ tested
(0, 150, 250, 400) — the design itself is sound. When the REAL ASSEMBLED
FIRMWARE runs the identical design at θ=150 with n extended to 240 real
capsule-stream games, it is a POWERED WASH, and that wash's confidence
interval EXCLUDES the mirror's own −12.94 point estimate. The two facts
cannot both be explained by insufficient sample size. Something in the
firmware's actual behavior — not just its evaluation weights — differs from
what the mirror (and the offline proof before it) assumed.

This document is the complete arc: what was measured, in what order, every
real defect found along the way (there were many, spanning both the design
and the harnesses used to test it), and the open question for the next
session.

## Timeline

### 1. Stage 2 → stage 3 handoff

Stage 2 (firmware CORRECTNESS: enumeration, full-depth-3 scoring, the θ gate,
the publish contract, slot isolation — see `TUCK_V3_FIRMWARE_DESIGN.md`) was
complete and differentially proved on synthetic boards. Stage 3's job was to
run the DECISIVE gate: a within-firmware A/B (`DRCOPRO_TUCKV3=0` vs `=1`, both
arms real assembled 6502 bytes) rather than trusting `root_search.py`'s python
approximation's absolute values.

Before any stage-3 compute, the team lead required promoting the stage-2 gate
suite (`test_tuck_ply2_score.py`, `test_tuck_root_extension.py`,
`test_tuck_slot_isolation.py`) to `EH_PLY1=True` — the real shipped config —
since a config gap there (missing `cp_live_cur` reset) had already survived
undetected once. All three promoted, `run_all.py` (8/8 green).

### 2. Sanity runs — the arm-plumbing bug

Three sanity-8 runs were needed before pass 1 could launch, each catching a
real, distinct defect:

- **v1/v2**: a pill-colour off-by-one (`firmware_decider.decide()` passed
  `ca/cb/na/nb` in the 1–3 convention straight into `build_image()`, which
  expects 0–2) and a `candidate_cells()` 4-tuple unpacked as a 2-tuple
  (confused with the DIFFERENT `land_place_at.cell_offsets()`). Both fixed.
- **v3**: the missing `cp_live_cur` reset inside `tuck_root_extension`'s
  per-candidate loop — `land_place_at` only writes its own 2 cells and
  assumes the rest of CUR already holds the correct board; without the
  reset, CUR held whatever the PREVIOUS operation left there. Fixed by
  adding the same reset the base search's own `eh_terms` rebuild already
  used. A recoloured cave-board confound (the test board's lip shared the
  target colour, letting a base action "cheat" through it) was caught twice
  along the way, in two different test files.
- **v3 (still)**: `FirmwareDecider.__init__` hardcoded
  `os.environ["DRCOPRO_TUCKV3"] = "1"` UNCONDITIONALLY, clobbering whatever
  `ab_root_firmware.py`'s per-worker `_init()` had just set from its own
  `tuck` argument — every worker, off-arm or on-arm, always built the SAME
  tuck-enabled image. Diagnosed from sanity-8 v3's own summary being
  internally contradictory (paired-pills delta exactly 0.00 across all
  pairs, yet fires/game=3.12 — impossible if the arms actually differ).
  Confirmed via image hash (identical pre-fix, divergent post-fix) before
  touching the fix. Fixing it exposed a SECOND, previously-masked bug: with
  the off-arm genuinely building `EMIT_TUCK_V3=False`, the tuck mailbox
  (`$6139/$613A`) is never written at all (that init is deliberately gated
  off to keep the shipped byte-identical image unchanged), so
  `firmware_decider.decide()` was reading uninitialised RAM and
  misinterpreting it as a published tuck. Fixed by trusting the build's own
  `EMIT_TUCK_V3` flag instead of inspecting mailbox bytes. A standing
  **image-hash divergence assert** was folded into `ab_root_firmware.py`
  itself afterward, so this bug class fails in 2 seconds on any future run
  instead of producing a silent degenerate result hours later.
  Sanity-8 v4 passed clean: paired pills −14.00 [−44.14,+19.86] (right
  direction, wide CI at n=7), clear 87.5%↔87.5% (within noise of the ~95.8%
  offline reference), fires 3.12/game.

### 3. Pass 1 — L11 n=120 wash

`ab_root_firmware.py --pass1 --workers 8`. Result: **WASH**, −3.84
[−10.14, +2.51], clear 98.3%→98.3%, fires/game 4.38. Off-arm cross-validation
clean (98.3% vs offline ~95.8% reference) — the harness itself is healthy;
per standing terms, L20 was correctly NOT auto-launched (the L11 gate failed
to reproduce the offline-favourable direction).

### 4. θ mini-sweep (firmware) — all-wash

θ=150 was calibrated in `fast_rtl_x`'s python eval units; the firmware speaks
different units (already-documented `W_VRDY`/`W_MATCHED_COVER` gap), so a wash
at θ=150 alone triggered a mini-sweep rather than a verdict. n=40 slices
(seeds 0–39, a strict prefix of pass-1's own seed set), on-arm only per θ,
against pass-1's own off-arm:

| θ | delta | 95% CI | verdict | fires/g |
|---|---|---|---|---|
| 150 | −2.44 | [−15.23, +10.31] | WASH | 4.38 |
| 250 | +0.87 | [−12.38, +13.97] | WASH | 2.27 |
| 400 | +2.64 | [−3.87, +9.26] | WASH | 1.02 |

Interpolated θ at fires/game≈2.8 (the offline θ\*=150 reference rate): ≈225.
All three θ washed — per standing instruction, this triggered DIAGNOSIS, not
another θ guess.

### 5. 20-board component localization — leaf1 pinned as the diverging term

Harvested 20 real capsule-stream boards (theta=0, offline decider) where the
offline model chose a tuck with the largest margin over the best base action.
For each board, read back imm1 / leaf1 / best2 (ply-2 raw) / DISC-blend /
eh-add-on / total from BOTH the offline python and the REAL FIRMWARE (via an
extended `DEBUG_VAL1` ring, `DBG_RING2`, added this session — carrying
imm1/leaf1/eh per ply-1 candidate; kept as a SECOND 8-byte-stride ring rather
than widening the existing one to 16 bytes, because the 6502's 8-bit X
register would overflow at 31 candidates×16=496), for both the base argmax
and the specific tuck candidate.

**First run had a real bug**: `tuck_ta`/`tuck_tb` (the tuck's placed-cell
colours) were written straight into `LA_CA`/`LA_CB` without the same `-1`
conversion `ca0/cb0/na0/nb0` correctly got — caught from the tell in the
summary line itself (`imm1` matched EXACTLY for base but was systematically
wrong for tuck — a colour bug signature, not a model divergence). Fixed and
re-run. Corrected result:

- **Base-action agreement** (firmware's own winner == offline argmax): 11/20.
- **imm1 and eh matched almost exactly** on both base and tuck (mean diff
  ≈0, ≈+5) once the colour bug was fixed.
- **leaf1 (and consequently best2/blend/total) diverges substantially and
  roughly SYMMETRICALLY** for base and tuck (mean total diff: base −1238.4,
  tuck −1157.5) — the pre-fix run had shown an asymmetric −1238/−1916 gap,
  which was RETRACTED as a harness artifact once the colour bug was fixed,
  not a real anti-tuck bias.
- **Sign flips** (offline tuck-favourable → firmware base-favourable):
  1/20 post-fix.

Conclusion at this stage: the leaf evaluation itself — not imm1, not eh, not
the DISC blend arithmetic — is the diverging component, and it is the
already-documented "goldens-vs-shipped" gap (`fast_rtl_x.variant("winner")`'s
weights vs the real RTL `LeafEval.sv` weights, third instance of this trap
class in the project), now observed with a real captured margin reversal
rather than a synthetic diagnostic.

### 6. RTL-faithful leaf mirror — the design IS real under the true eval

Re-ran the offline root-action A/B with the leaf swapped from
`fast_rtl_x._leafv_ship` to `fpga/copro/leaf_r47.leaf_vrdy12` (W_VRDY=12,
matching `build_copro_d3.build_image()`'s REAL shipped override — NOT
`leaf_r47()`'s own `w_vrdy=24` default, which is the pre-retune R47 brain),
keeping imm1/eh/DISC-blend arithmetic untouched (already proven to match).
Pure python (not numba — `leaf_r47.py` is itself pure python and is the
ALREADY-VALIDATED ground truth, 100% cell-exact vs the pinned RTL corpus and
live RTL, 5036/5036; rewriting it to chase speed was rejected). Measured
2.3s/decision single-threaded — tractable when parallelized.

**Closing-the-loop check** (20 boards, mirror totals vs real firmware D_V1):
a large CONSTANT offset (base +2110.1 mean, tuck +2002.7 mean) is irrelevant
by construction (argmax and the θ margin both compare candidates WITHIN one
decision, so a candidate-independent offset cancels). What matters: the
DIFFERENTIAL residual (base-vs-tuck gap ≈107, same order as θ itself — noted
as mirror imprecision) and per-board WINNER FLIPS: **2/20** (seeds 9 and 14),
at the accepted threshold (≤2/20 → decisive enough at the A/B level, since
game-level statistics average out per-decision noise). One real bug found and
fixed along the way: `np.frombuffer` returns a READ-ONLY array, a different
numba type from a writable one, so `_expand_core` (compiled without a
read-only-array overload) threw a `TypingError` when called directly from
plain python with such an array — fixed with `.astype(np.int8)`, matching
every other working call site's convention.

**θ curve, L11 n=120, fresh off-arm, mirrored eval throughout**:

| θ | delta | 95% CI | verdict | fires/g |
|---|---|---|---|---|
| 0 | −9.49 | [−17.86, −1.11] | **REAL** | 8.43 |
| 150 | −12.94 | [−20.43, −5.48] | **REAL** | 3.17 |
| 250 | −8.50 | [−15.59, −1.58] | **REAL** | 2.19 |
| 400 | −8.04 | [−12.85, −3.39] | **REAL** | 1.02 |

**All four θ are REAL under the true eval.** The root-action design, scored
by a leaf that actually matches the RTL, transfers cleanly offline.

### 7. The power question — and its rejection

Pass-1's own firmware θ=150 CI ([−10.14, +2.51]) overlaps the mirror's
[−20.43, −5.48] on [−10.14, −5.48] — a true firmware effect around −6..−9
would be consistent with BOTH measurements, meaning pass-1's wash could have
been an underpowered detection of a real effect rather than a transfer
failure. Decisive test: extend the firmware sample.

- **Firmware θ=150, seeds 120–239 alone** (`--seed-offset 120`, same standing
  harness/image, hash-checked against pass-1's recorded hashes): WASH, +0.03
  [−6.48, +6.16], clear 99.2%→99.2%, fires/game 4.16.
- **Pooled n=240** (seeds 0–239, re-derived from merged raw per-seed
  results, not combined summary stats): **WASH**, **−1.90 [−6.45, +2.54]**
  (235/240 paired), clear 98.8%→98.8%, discordant 4 (2 tuck-only wins, 2
  tuck-only losses), fires/game 4.27.

The pooled 95% CI **excludes** the mirror's −12.94 point estimate. **The
power hypothesis is rejected.** A real mirror-vs-firmware behavioral gap
exists — the mirror (and the offline proof under it) says the design should
save ~9–13 pills/game at θ=150; the real firmware, at 2× the sample size,
shows no such effect and rules out an effect that large.

## Bug catalog (this session, stage 3)

Every one of these was found via a concrete tell (a contradictory summary
line, a sign that shouldn't be possible, a crash trace) and confirmed with a
minimal repro before being fixed — none were guessed from a traceback alone
and left unverified.

1. Pill-colour off-by-one into `S_CA`/`S_CB` (`firmware_decider.decide()`).
2. `candidate_cells()` 4-tuple unpacked as a 2-tuple (confused with
   `land_place_at.cell_offsets()`).
3. Missing `cp_live_cur` reset in `tuck_root_extension`'s per-candidate loop
   — the root cause that made every prior stage-2 gate pass while the real
   pipeline was silently scoring garbage.
4. Cave-board colour-chain confound (test board's lip shared the target
   colour, letting a base action "cheat" a win) — found twice, in two files.
5. `FirmwareDecider.__init__` hardcoded `DRCOPRO_TUCKV3="1"` unconditionally
   — made sanity-8-v3's A/B arms build the identical image.
6. Uninitialised tuck mailbox read when `EMIT_TUCK_V3=False` (exposed only
   once bug 5 was fixed and the off-arm genuinely diverged).
7. `test_firmware_decider.py` constructing `FirmwareDecider` twice in one
   process, tripping its own module-identity guard (pre-existing, unrelated
   to bugs 5/6, caught while re-verifying that diagnostic still ran clean).
8. `test_firmware_decider.py`'s stale `nb=0`, predating this session's own
   colour off-by-one fix (bug 1) — underflowed to −1 on `S_NB`.
9. `test_tuck_recognition`'s board-encoding mismatch
   (`_cave_horizontal_board()`'s raw convention doesn't round-trip through
   `nes_to_arrays`) — documented, left unfixed (non-gating diagnostic, real
   fix needs a from-scratch col/vir-native board).
10. Tuck-colour off-by-one in `firmware_components.py`'s targeted
    single-candidate score (`LA_CA`/`LA_CB` missing the same `-1` conversion
    `ca0`/`cb0`/`na0`/`nb0` correctly got) — caught from the localization's
    own summary line (imm1 matched exactly for base, systematically wrong
    for tuck).
11. `np.frombuffer`'s read-only array breaking numba type inference in
    `verify_mirror_vs_firmware.py` (unrelated to the leaf swap it was
    guessed to be) — confirmed via minimal repro before fixing.

Plus, as standing infrastructure added along the way: the image-hash
divergence assert in `ab_root_firmware.py` (turns bug 5's class into a
2-second failure forever), and `--seed-offset` (lets any run extend an
existing sample instead of restarting from seed 0).

## Dissection plan (next session's work)

The decisive open question: **where, mechanically, does the firmware's
actual played-out behavior diverge from the mirror's, given that their
per-decision component breakdowns mostly agree (imm1/eh match, leaf1 has a
bounded, roughly-symmetric residual, and only 2/20 static-board winners
flip)?** A small per-decision residual and a 2/20 static flip rate should NOT
produce "REAL −13" offline vs "WASH, CI excludes −13" on 240 real games — the
gap must be compounding somewhere across a TRAJECTORY, not visible in any
single frozen board.

Proposed method for the next session:

1. **Matched-board per-decision comparison.** Run the mirror-decider and the
   firmware-decider on IDENTICAL boards ALONG FIRMWARE TRAJECTORIES (i.e.,
   drive real games with the firmware decider, and at every decision point
   ALSO ask the mirror decider what it would have done on that exact board —
   not two independently free-running games, which only agree on the
   opening move before diverging). Log, per decision: whether the chosen
   action class matches (base-vs-base / tuck-vs-base / different-tuck), and
   for tuck decisions, whether the SAME tuck candidate was chosen or a
   different one.
2. **Characterize the firmware's fired-tuck set vs the mirror's.** Are the
   firmware's actually-fired tucks systematically lower-margin than the
   mirror's fires? Different target columns? Different board regimes
   (open/mid/end, per §6.3's regime table convention already used in
   `TUCK_V3_OFFLINE.md`)? The 107-point differential residual found in the
   closing-the-loop check is a candidate fingerprint — check whether it
   itself has structure (does it correlate with board height, virus count,
   or excavation credit?) rather than being pure noise.
3. **The first divergence class that explains the value gap names the fix.**
   If firmware tucks cluster at systematically lower true margin than the
   mirror's fires, that points at the residual itself (a scale/rounding
   detail in how the real 16-bit fixed-point arithmetic accumulates across a
   longer trajectory than any single 20-board snapshot can show). If
   firmware and mirror disagree on WHICH tuck to fire more often than the
   20-board flip rate would predict, that points at something trajectory-
   dependent in board state (e.g., an interaction between `cp_live_cur`'s
   reset and a LATER candidate's scoring within the same decision, or a
   gravity/resolve edge case that only appears on boards reachable after
   several real pill placements, never sampled by the 20-board harvest's
   theta=0 selection bias toward LARGE-margin decisions specifically).

This is deliberately scoped as design-only here — the matched-trajectory
harness itself, the specific logging fields, and the regime-correlation
analysis are the next session's implementation work, not this one's.

## Final numbers (for quick reference / memory)

- Pass-1 L11 n=120: WASH, −3.84 [−10.14, +2.51], fires/g 4.38.
- Firmware θ sweep n=40: 150 WASH −2.44, 250 WASH +0.87, 400 WASH +2.64 — all
  wash, fires/g 4.38/2.27/1.02, interpolated θ at fires/g≈2.8 is ≈225.
- 20-board localization (post colour-bug fix): base-action agreement 11/20,
  imm1/eh match (~0 mean diff), leaf1 diverges symmetrically (base −1238.4,
  tuck −1157.5 mean total diff), 1/20 sign flips.
- Mirror θ curve (RTL-faithful leaf, L11 n=120 each): 0 REAL −9.49, 150 REAL
  −12.94, 250 REAL −8.50, 400 REAL −8.04 — ALL FOUR REAL.
- Closing-the-loop (20 boards): constant offset ~+2000-2100 (irrelevant by
  construction), differential residual ≈107, winner flips 2/20.
- Firmware θ=150 pooled n=240 (seeds 0-239): WASH, **−1.90 [−6.45, +2.54]**
  — CI excludes the mirror's −12.94. Power hypothesis rejected.

**Bottom line: root-action tucks are a validated design under the true
evaluation. The current firmware implementation does not deliver that
value. Stage 3 closes here as a validated negative with a named next step,
not an unresolved question.**

## Dissection RESULTS (2026-08-04, n=40 firmware trajectories, 4876 decisions)

Harness: dissect_trajectory.py (firmware θ150 drives; mirror shadow-queried
per decision; both picks scored under the leaf_r47 mirror ruler). Analyzer:
dissect_analyze.py. Data: results/dissect/dissect_L11_n40.jsonl.

1. **ENUMERATOR-SET DIVERGENCE, CONFIRMED AT SCALE: 62.3%** (109/175) of the
   firmware's actually-fired tucks do NOT exist in the python proof's
   candidate list (RS.tuck_root_candidates, exec_only, fpr=12). The
   divergence is concentrated in HORIZONTAL tucks: 71% of out-of-set fires
   are horizontal vs 29% of in-set. tuck_scan_v3 reaches horizontal
   slide-unders the proof never enumerated. THE MIRROR PROOF AND THE
   FIRMWARE WERE NEVER TESTING THE SAME ACTION SPACE.

2. **Firmware fire quality is NOT the problem**: mean mirror-margin of
   firmware fires +507.7 (median +196) vs the mirror's own fires +514.2
   (median +245). The out-of-set fires carry NEGATIVE regret (mean −561.7):
   under the true ruler they are BETTER than the mirror's own best action on
   the same board.

3. **The two tuck channels nearly cancel**: firmware misses 109
   mirror-visible tucks (fw_base_mir_tuck, +55,150 total regret, mean +506)
   while gaining −58,421 from its out-of-set fires. Net tuck channel ≈ −3.3k
   (slightly firmware-favourable). The steady bleed is BASE-ACTION
   divergence: 376 base_diff events × 42.9 mean = +16,143 (leaf1-residual
   flips, consistent with the earlier 20-board localization).

4. **Regime flip**: firmware policy loses mirror-value in open (+9.4/dec)
   and mid (+14.1/dec) but WINS endgame (−11.7/dec). Fires: 61% mid, 22%
   end. Misses skew earlier (33% open) — the missed tucks are
   opening/mid-game, where trajectory compounding has the most room.

5. **Gate calibration**: 29.7% of firmware fires sit below θ=150 under the
   mirror ruler (firmware's own margin computation admits them).

**Reading**: the REAL-vs-WASH gap is NOT bad fires. Leads, in order:
(a) missed early-game tucks (the mirror's −12.94 plausibly lives in
opening/mid fires the firmware declines); (b) base-action divergence
compounding; (c) below-θ drag. Named next experiment: offline UNION-
enumerator A/B under the mirror ruler (candidates = union of both sets) to
measure the ceiling, then align enumerators toward whichever set the union
proves out — the horizontal-tuck reach gap is the concrete engineering item.

Status: #17 dissection phase CLOSED with mechanism named. Enumerator
alignment is future work; #47 (abandoned material) took priority per the
user's field session of 2026-08-03.

## UNION-ENUMERATOR VERDICT (2026-08-04, n=120, mirror ruler, θ=150)

union_mirror.py, same seeds/protocol as the mirror curve (RS-only arm
REPRODUCED the original −12.94 [−20.43,−5.48] exactly — rig sanity holds):

- **UNION vs off: −20.02 [−27.11,−13.19] REAL** (clear 95.8→97.5%)
- **UNION vs RS-only: −7.83 [−13.57,−2.30] REAL** — the firmware's
  out-of-proof candidates (2.12 of 5.11 fires/g; predominantly horizontal
  slide-unders) carry additive value the proof never measured.

**The proof's enumerator was the limiter.** The dissection's two cancelling
channels are now explained as one defect seen from both sides: each
enumerator holds value the other can't see. The tuck ceiling is ~−20
pills/game, 1.5x the original prize. NAMED NEXT BUILD: converge the
enumerators on the union — concretely, characterize the set difference
(which RS-visible candidates tuck_scan_v3 misses, and vice versa), then
extend tuck_scan_v3 (the validated 6502/RTL scanner) to cover the RS-only
class, and re-prove the converged set under the mirror before any firmware
build. Data: results/union_theta150.json.

## Set-difference characterization (2026-08-04, 20 games / 2,433 decisions)

characterize_setdiff.py: physically-normalized candidate sets per decision:

- shared **2,208 (28%)** — the enumerators barely overlap
- RS-only **1,527 (19%)**: 88% HORIZONTAL, concentrated DEEP (rows 10-15;
  254 at the floor row itself) — these are the missed early/mid-game tucks
  behind the dissection's +55k regret channel
- FW-only **4,219 (53%)**: all orientations (H 1242, RH 1917, V 411, RV 649),
  mass at rows 8-12 — the mid-board slide-unders whose fires beat even the
  mirror's own best actions

Scanner-extension design target: tuck_scan_v3 must additionally reach the
DEEP HORIZONTAL class (floor-adjacent resting rows with longer lateral
travel under overhangs) that RS's executability model admits and scan_v3's
reach model currently rejects. RS's own gap (everything scan_v3 sees that it
doesn't) needs no fix — the proof side simply adopts the union via
union_cands() for scoring. Sequence: (1) extend ref_tuck_scan_v3 + assert it
now covers RS-only class on this corpus; (2) port the extension to the 6502
scanner + bit-exact gate vs ref (67-board discipline); (3) re-prove the
converged set under the mirror (expect ≈ −20); (4) firmware θ recalibration
(more candidates -> more fires; θ may need raising); (5) silicon.

## Corridor-rule coverage (2026-08-04) — extension design CLOSED

corridor_coverage.py, same 20-game corpus: a generalized-approach corridor
rule (entry column-pair with open sky to trigger row r, clear corridor at r,
lateral budget |s−c| ≤ K·(rf−r+1)) covers the RS-only class at:

- horizontal: K=1 → 94.9%, **K=2 → 99.3% = the K=∞ geometric ceiling**
  (the residual 0.7% needs multi-row pathing; not worth the complexity)
- vertical: **100% at K=1**

**Design decision: scan_v4 = scan_v3 + corridor walk with K=2**, all
first_occ-table arithmetic (6502-amenable, no new primitives). Next:
implement ref_tuck_scan_v4 + corpus coverage assert (>= 99% of union),
mirror re-prove the v4-enumerated set (expect ≈ −20), then 6502 port +
bit-exact gate, θ recalibration, silicon.
