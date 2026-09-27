# PREREG #136 — re-capture the DRPRESTART latency pilot on the current generation

**Registered:** 2026-08-19, before any verdict data exists (proof of timing in the
commit message: the verdict JSONL does not exist and the calibration file is empty).
**Lane:** garbage-prestart-lane. **Branch:** `prestart-latency-136`
(= `fixes-130-124` @ d513562, plus the four `cosim-farm` shadowlat-analysis commits
cherry-picked, plus this lane's additions). **Cost:** local only, $0.

---

## 1. The question, and why the old answer cannot simply be re-read

#92 published: the copro's post-garbage answer lands inside the window for **89.4% of
releases (all 186 decisions at h ≤ 12, zero overruns)**, degrading to 25/80/100/100%
late at h = 13/14/15/16 — hence "DRPRESTART is a MID-BOARD instrument, not a
near-death one".

Two things have changed since, and **neither is fixable by re-analysing the old file**:

1. **The window variable was wrong three ways** (#124): `h_hit` was the MAX over
   BOARD-INFERRED hit columns of POST-SETTLE heights; the window is set by the MIN,
   over the VOLLEY'S OWN columns, of PRE-garbage heights. A `lat` row is exactly five
   fields and carries neither the column draw nor the pre-garbage heights, so the
   correct value is not recoverable from `prestart_pilot.jsonl` by any means.
2. **The firmware generation moved.** The pilot ran `s20b` (`e970e9ab`). The shipped
   MiSTer rbf `974de3ed` / Pocket bundle now carry `b03a586e` (θ400 tier-3 tuck +
   `DRDBLCANON`, #123). DRDBLCANON removes duplicate double-capsule candidates, which
   changes SEARCH COST — the exact quantity this measurement is about.

⇒ #136 is a fresh capture, not a re-analysis. Its purpose is to establish whether the
**latency benefit** #115 explicitly left un-re-established still holds on the cart
generation the owner intends to turn DRPRESTART back on for.

## 2. Rig, and why this one (gate standard rule 10)

**Verilator co-sim farm** (`experiments/cosim_farm`), `pressure=bursty` (v1.1),
`exec_mode=drop`, level 11, `max_pills=300`.

| rig | executes | usable here? |
|---|---|---|
| Mesen | cart DRIVER only; its copro mailbox is a Lua reimplementation | **No** — it never runs `copro_rom.hex`, so both firmware arms would trace identically and the comparison would be vacuous by construction (the core-stage trap) |
| py65 | firmware, no RTL timing; agrees with real RTL on 13.3% of L11 moves | **No** — it cannot produce a per-decision clock count at all |
| **Verilator co-sim** | the real RTL executing the real `copro_rom.hex`, reporting per-decision clocks | **Yes** — the only rig that emits the measured quantity |

**What this rig CANNOT do, stated up front:** the farm is TURN-BASED. The board freezes
during `decide()`, so **no decision here is ever actually late**. This is a shadow
projection of measured RTL clocks onto the ROM-derived budget, exactly as #92 was. It
cannot show a panic vertical, only a budget exceeded. It also does not execute the
DRPRESTART DRIVER code at all — see §7.

**Clock domain: SILICON** (`clocks / 909,650`), per #92's own finding that the two
domains disagree 1.57x and can give opposite verdicts on the same decision. Any cart
claim is a silicon-domain claim. The sim-lockstep number is reported alongside and is
never the basis of a verdict.

## 3. Arms (paired, same seeds)

| arm | copro_rom.hex | what it isolates |
|---|---|---|
| `p136_cur` | `b03a586e` — θ400 + DRDBLCANON, the SHIPPED firmware | the answer to the actual question |
| `p136_leg` | `e970e9ab` — s20b, the firmware #92 measured | the h-definition change alone, at fixed firmware |

Two things moved since #92; one arm can only report their SUM. `p136_leg` under the
corrected window separates them: `leg` vs #92 is the h fix, `cur` vs `leg` is the
generation.

**Seed block: 63000-63999, claimed by this lane** (free per the 2026-08-18 registry
note, which lists 63000-65535 unclaimed; blocks are registered below 65536 so
seed == stream key). Verdict seeds run in ascending order from 63000.
**Seeds 63900-63907 are CALIBRATION** (throughput only, run before this prereg, on the
pre-`h_legacy` `game.py`) and are excluded from every verdict number. They are in a
separate file and a separate arm label and must never be pooled.

## 4. The reading rule (registered before the data)

**R1 — PRIMARY: spawn-ready share.** On `p136_cur`, silicon domain,
p = (post-garbage decisions finishing within W = 264 − 16·h_min) / n_window_scored.

| outcome | criterion |
|---|---|
| **SURVIVES** | lower bound of the 95% interval for p **≥ 0.894** |
| **DEGRADED** | upper bound **< 0.894** |
| **INDETERMINATE** | the interval straddles 0.894 |

0.894 is #92's published point estimate. #124 proved every pre-fix window figure is a
LOWER bound (the corrected windows are LONGER), so if the mechanism is unchanged the
new number can only rise; requiring the new interval's lower bound to clear the old
point estimate is the honest "at least as good as advertised" bar.

**Interval:** releases are clustered within games, so the decision uses a **game-level
cluster bootstrap** (10,000 resamples of games with replacement, percentile interval).
The Wilson interval is reported too, and is the more optimistic of the two by
construction; it is NOT the decision instrument.

**Registered size: seeds 63000-63079, 80 per arm.** Sized from one calibration game
(seed 63900, `b03a586e`): 768 s wall, 115 decisions, **14 post-garbage releases**. So
80 games ≈ 1,100 releases per arm, ~5x #92's 208, at ~1.5 h/arm on 12 workers.

**Minimum sample:** `n_window_scored ≥ 300` on `p136_cur` (vs #92's 208). Below that
the verdict is **INDETERMINATE-BY-SAMPLE** and is reported as such — the routing is
NOT to extend the run until a bar is cleared.

**R2 — SECONDARY: is it still a MID-BOARD instrument?** From the `by_h_hit` table,
let h\* = the largest h whose window W exceeds the median silicon decision cost.
The "mid-board, not near-death" claim is RE-AFFIRMED iff late share is **< 5% at
h ≤ h\*−1** and **> 50% at h ≥ h\*+1**. #92's h\* was ~13.6 with a flat-in-h cost
(~44-48 f); both the flatness and h\* are re-reported, not assumed.

**R3 — DESCRIPTIVE: generation delta.** Median silicon frames per decision,
`cur` vs `leg`, paired by seed; mean paired difference with a 95% interval. No
threshold, no verdict attached.

**R4 — DESCRIPTIVE: how big was the #124 correction?** Every release now logs BOTH
window variables (`h_legacy` = the pre-#124 expression transcribed verbatim from
main's `game.py:314-317`, beside the corrected `h_hit`). Report the paired
distribution of `h_legacy − h_corrected` and of the frame difference in W. This
replaces the un-poolable cross-file comparison #124 correctly forbade.

## 5. Gate sheet — all of it must pass BEFORE the verdict is read

| # | gate | what it proves |
|---|---|---|
| G1 | `test_lat_conversion.py` green on the parent | the analysis arithmetic, incl. the new `by_h_hit` table |
| G2 | `gate_shadowlat_mutants.sh` — every mutant killed | the analysis is not vacuous. Includes **M7** (key the per-h table on `max_h` — the #124 conflation itself) and **M8** (score the table against the FALL budget instead of the window). M10 (mean-for-median) was equivalent under the original fixtures and a skewed cell was added to make it killable rather than dropping it. |
| G3 | `test_gw_hhit.py` green, incl. the new legacy-formula cases | `h_legacy` really is the pre-fix quantity |
| G4 | **POPULATION (rule 7)**: on the live run, (a) `n_window_unscorable == 0`; (b) **median(h_legacy − h_corrected) ≥ 1** | (b) is the non-vacuity check: on a flat stack the two definitions coincide, so an all-zero difference would mean the corpus never exercised the defect and the recapture measured nothing. That outcome is a FINDING, to be reported, not a silent pass. |
| G5 | **PROVENANCE (rule 11)**: `fw_md5` asserted per row (`b03a586e` / `e970e9ab`); `manifest` rolled hash constant within each arm | a firmware/harness drift cannot hide in the result |
| G6 | determinism: 2 seeds re-run into a second file, `lat` rows byte-identical | the capture is reproducible |

⚠ **Known provenance limit, registered not hidden:** `b03a586e` was COPIED from
`tmp/rtl_chain/ship/theta400dblcanon-seed13/copro_rom.hex`, not rebuilt. A byte-exact
rebuild from `build_copro_d3.py` with `DRDBLCANON=1` at the θ400 flags is attempted and
reported; a failure to rebuild does not invalidate the clocks (the hex that ran is
hashed into every row) but is reported as an open provenance item.

## 6. Rule 12 — the phase-dial screen

DRPRESTART is a tempo-shifting flag, and #115 showed its entire observable cart effect
is a ±2-frame shift that can masquerade as anything. Screen, applied here:

- **There is no DRPRESTART arm in this measurement.** Neither arm builds or runs the
  flag; the farm executes no cart driver at all.
- Both arms are turn-based and therefore **phase-free by construction** — there are no
  frames, no `f%30`, and no restart transit to land on.
- The `cur` vs `leg` difference (R3) is a difference in CLOCKS SPENT SEARCHING, which
  is not a phase quantity.

⇒ No arm difference reported here can be phase-mediated. Recorded explicitly so that R3
is never read as a cart A/B of the flag.

## 7. Scope limits, registered in advance

- **Shadow, not observation.** Turn-based farm ⇒ a projection onto budgets, not a
  measurement of a late decision. No claim about what an overrun COSTS is made.
- **This does not test the DRPRESTART driver code.** It measures the budget the driver
  would be spending. Whether the 6502 side detects the release, projects the settled
  board and issues GO correctly is a DRIVER question and belongs on a rig that runs the
  driver. #115 exonerated the flag of the wedge; this establishes the budget; neither
  is a silicon A/B of the feature.
- **Every window figure remains a LOWER bound.** `bursty_model.sample` draws random
  distinct columns while the ROM releases maximally SPREAD sets ({c,c+4}, …). Spread
  sets find a shallow column more often ⇒ real h_min is lower and real windows longer.
  Filed, not folded in.
- One pressure model (bursty v1.1), one level (11), `exec_mode=drop`.
- The 264 − 16·h formula assumes the volley triggers no clear; a clear only LENGTHENS
  the window, so the budget is conservative.
