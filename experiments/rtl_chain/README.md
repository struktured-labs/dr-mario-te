# rtl_chain — validating the link-aware / **Combo Stomper** copro engine

Instruments behind `CoproDrMario.sv` + `LeafEval.sv` gaining a link plane, body gravity,
fixpoint resolve and the DRCHAIN chain reward (NES_MiSTer-winner, branch
`claude/winner-single-copro`).

Two brains, one bitstream, picked by two firmware bytes:

| | `$70E5` a_fix | `$70E6` DRCHAIN/4 | |
|---|---|---|---|
| **lnk1** | 0 | 0 | link-faithful physics baseline: body gravity, one clear round |
| **Combo Stomper** | 1 | >0 | resolve to fixpoint and pay for chain depth |

`DRCHAIN=0` reproduces lnk1 exactly (the reward term vanishes), so both arms ship in one
`.rbf` and the hardware A/B is a two-byte hex patch — verified: the lnk1 and
Combo Stomper (dose 360) firmware images differ at exactly two offsets.

⚠ **Pointer note.** Build the co-sim against the **winner fork**
(`NES_MiSTer-winner/rtl/mappers/`) or `dr-mario-canonical-wt`. The copy under
`dr-mario-qa-wt/fpga/copro/LeafEval.sv` is STALE — 18 KB, no delta engine — and
verilating it "verifies" hardware that isn't the shipped engine. Identify these files by
hash, never by directory name.

## What each file answers

**`gravity_order_test.py`** — *does the RTL need a 128-entry stable sort?*

The reference kernel (`cascade_link_x._link_gravity`) enumerates bodies row-major and
stable-sorts them lowest-first before dropping each one row. That sort is expensive in
silicon. Body gravity is confluent — bodies only ever move DOWN — so any drop order should
reach the same settled board. This compares a deliberately cheap RTL-shaped sweep (bottom-up
rows, canonical representative cell, **no sort**) against the sorted reference on the FULL
result: colour plane, virus plane, LINK plane, cells, viruses and chain depth.

    VERDICT (measured): CONFLUENT. 96,540 real placements (L11 6 games + L17 8 games,
    cap-1 and fixpoint), 0 mismatches, max chain 3.

Comparing only cells/viruses would have passed while the link plane rotted, and the link
plane is what drives the *next* placement's gravity.

**`gen_chain_cases.py`** — builds CMD-4 (NODE) co-sim cases from REAL self-play boards.
Ground truth is `cascade_chain_x._expand_chain` + `fast_rtl_x._leafv_ship`. Synthetic fills
flatter link physics: they rarely contain the tall stacks of intact pairs where body and
compact gravity actually disagree.

**`tb_chain.cpp`** — the Verilator testbench. Checks colour, virus AND link planes, cells,
viruses, chain depth, imm, sco, win, and reports DONE latency per arm. Takes an optional
DRCHAIN dose; **refuses a dose run over a corpus containing no cascades**, because the
reward term is only live when `chain > 1` and would otherwise pass whether the RTL
implemented it or not.

**`size_leafeval.sh`** — standalone ALM sizing for one LeafEval variant on the production
device with the production optimization settings (SPEED, never AGGRESSIVE AREA). Not a fit
verdict for the whole core; a *delta* instrument, and ~10 minutes a run.

    base                                    5,864 ALMs
    link plane, first cut                   8,674     (+2,810)  -> did NOT fit the core
      + one shared read port                8,034     (-640)
      + two funnelled write ports           7,627     (-407)

### The ladder

Every row is a clean full-core fit. Both columns moved the whole way, which is the point:
the area work and the timing work were the same work.

| build | copro slack | ALMs (of 41,910) |
|---|---|---|
| pre-link baseline | +0.118 | 36,465 |
| link plane, first cut | **−3.241** | 42,130 — *did not fit* |
| + read/write split (timing) | −0.312 | 39,055 |
| + third apply stage | −0.113 | 38,390 |
| + gravity fall split | +0.001 | 38,173 |
| + link plane into RAM | +0.026 | 37,364 |
| + DRCHAIN as an accumulator | +0.096 | 37,132 |
| ship build (seed 2) | **+0.181** | **37,249** |

⚠ **Every row above the ship build is SEED 5**, not a default seed — `NES.qsf` line 55
already carried `set_global_assignment -name SEED 5` before this work began. The ladder is
therefore still like-for-like (one seed throughout, only the RTL moving), but that was true
by accident rather than by construction, and it is worth knowing before citing the table as
a controlled experiment. Scripts here now strip existing SEED lines and write exactly one,
asserting the count, so the ambiguity cannot recur.

Ship bar is **+0.10**, not "positive" — see `fit_verdict.sh`. The baseline shipped at
+0.118 and cliffed to −3.241 on the first real change; a picosecond-order hair is a seed
lottery ticket, and tucks or a VS term would cash it negative immediately.

Four path promotions, each structurally different, which is why the rule is **re-run
`report_timing` after every fix and re-aim before building** — a remedy chosen against a
stale path list is ritual, not engineering:

    apply-sweep partner lookup  ->  gravity fall decision  ->  per-virus run/span walk
                                ->  the DRCHAIN multiplier itself

The third of those was BASELINE logic failing on pure congestion, which is what re-aimed
the RAM conversion from "delete a mux" to "shed area". The fourth was the feature's own
multiplier, dissolved by making the reward an accumulator.

⚠ **`clk85` is NOT a copro-only clock.** It feeds the SDRAM controller and the EEPROM
dpram, and `rtl/sdram.sv` pins its constants to that rate (`tRCD=20ns -> 2 cycles@85MHz`).
Retuning it is a memory-timing change, never a timing-closure knob. If a clock lever is
ever genuinely needed it is a DEDICATED `outclk_3` for the copro (VCO 429.545 / 6 =
71.59 MHz), leaving clk85 alone — and then: fresh `report_timing` to confirm the relief
lands on the copro domain, an end-to-end DONE re-measure rather than a percentage
estimate, and a check that SDRAM and EEPROM are still on 85.909.

### Where a 128-entry register file's area actually goes

Worth reading before optimizing anything here, because two of the three results are
against intuition.

- **The write decoders are NOT the cost.** Merging the link into a 6-bit `bcell`, which
  shares the 128-way write decoders and the address path (the "widen the cell encoding"
  shape), recovers **exactly 0 ALMs** — 8,674 either way, behaviourally perfect and
  cycle-identical. Don't redo this experiment.
- **The read muxes are.** Four independent `blink[<expr>]` reads meant four independent
  128:1 mux trees, plus speed-driven register duplication on top (`blink[30][1]~DUPLICATE`
  in the timing report is the tell). One address register and one mux: −640.
- **Funnelling the writes still helps, for a different reason.** Ten write statements give
  all 128 registers a ten-way enable and a ten-way data mux; two explicit ports leave each
  a 2-way enable and a 2:1 mux: −407.
- **Area here is NON-MONOTONIC.** Folding the two gravity `bcell` reads onto the same
  shared address register measured **+418** and was reverted. Measure each step; do not
  reason your way to a "surely this helps" change.

The same register file also blew TIMING before it blew area — see the `bcell`/`bl_ra`
comments in LeafEval.sv for the read/write split that fixed it.

## The gate

The routine check lives next door as a new level:

    cd ../bitexact_gate && python gate.py linknode

It runs the pinned `linknode_cases.txt` at DRCHAIN doses 0 / 180 / 360 and then kills 9
mutants. It has its own corpus because the older pinned one carries **no link information**
— measured, its parent high-nibble histogram is exactly `{4, 13, 15}` — so it cannot tell
body gravity from compact gravity. `node_cases.txt` was left untouched on purpose: other
lanes' blessings are tied to its md5.

## Reading a `gate.py rtl` failure on this engine

`gate.py rtl` PHASE2 NODE uses a COMPACT-gravity oracle. A link-aware engine fails it on
clearing placements **by design** — that divergence is the lnk1 payload. What matters is
that PHASE1 LEAF and PHASE3 DELTA stay at 948/948 and 4494/4494, which is what proves the
eval and the delta fast path were not disturbed.

## Shipping: the fit verdict, then the same-placement A/B

**`fit_verdict.sh`** prints the three numbers that decide whether the engine ships as-is,
each with its own PASS/FAIL, and exits non-zero if any fails — the call is arithmetic, not
judgement:

| | criterion | why it is the one that matters |
|---|---|---|
| (a) | copro-domain setup slack **> 0** | the pre-link baseline had only **+0.118 ns** here |
| (b) | `pll_hdmi` no worse than the **−0.012** baseline | pre-existing and not ours, but placement pressure can move it, and then it is ours to explain |
| (c) | **≥ 1,500 ALMs free** | headroom floor for tucks and the VS lane behind this work |

**`swap_arm.sh <lnk1\|stomp180\|stomp360>`** — the intended A/B METHODOLOGY, not just a
convenience.

The arm-select bytes live in the copro firmware, so on a **cart** they really are a
two-byte patch of a file. On **MiSTer** they are not: `CoproDrMario.sv` pulls the firmware
in with `initial $readmemh("copro_rom.hex", rom)`, which bakes it into the bitstream.
Swapping arms therefore needs a new `.rbf` — but **not** a new fit:

    quartus_cdb NES -c NES --update_mif      # re-read the hex into the fitted database
    quartus_asm NES -c NES                   # re-emit the bitstream   (~2 min, not ~40)

That is better than merely faster. Both arms come out of the **same placement and the same
routing**, so nothing but the ROM contents differs between them. Any behavioural difference
observed on hardware is the brain, and cannot be a fitter artifact — which is exactly the
confound that two independently-fitted builds would leave open. Pair it with a fixed boot
seed (same capsule stream) and the only free variable left is the brain.

Deploy with a **device-side md5**: copy, then verify the hash on the MiSTer itself, never
on the host.

## Environment

`/home/struktured/projects/dr_mario_rl/tmp/venv/bin/python` (numba + py65). The kernels are
imported from `dr_mario_rl/tmp/combo_term`.

## DONE latency: what the pipelining actually cost

Measured end-to-end through the real mapper (`donelat/run_arms.sh`), tucks on both sides so
it is like-for-like against what is deployed.

⚠ **The first version of this table was measured on 6 boards and UNDERSTATED the tail by
22%.** Six boards cannot see a p95. Re-measured on the 69-board corpus, Combo Stomper 180
(`f4b6dfbf`):

| statistic | clocks | frames @85.909 MHz |
|---|---|---|
| min | 26.1M | 18.2 |
| median | 48.3M | 33.7 |
| p90 | 59.2M | 41.3 |
| p95 | 63.4M | 44.3 |
| **max** | **81.9M** | **57.2** |

The superseded worst-of-6 was 67.13M = **46.9 frames**; it is left visible here rather than
overwritten, because the correction is the point. Against a ~80-frame budget the true worst
case uses **72%**, not 59%.

Roughly 1.8x the deployed `751b6ce9` arm — far more than the +25% measured before timing
closure. Three timing splits and the RAM's read-latency bubbles all land on the clearing
path, and they add up: per-NODE worst went 4,353 → 11,507 cycles across the campaign.
Timing margin was bought with latency, and the budget is where it was spent.

⚠ The rig prints `@85.9MHz eff/2`. The `eff/2` is a STALE LABEL from when the copro sat on
outclk_1 (42.95 MHz). It runs on `clk85` now — `CoproDrMario.clk_cpu` is wired to outclk_0
with `RDY` tied high and no clock enable — so the seconds it prints are correct and the
frame counts above are at the true rate. Worth knowing before someone halves them in their
head: at 42.95 MHz the worst case would be ~94 frames and OVER budget.

## Truncation: what a shorter budget actually costs (`sim_agree.cpp` + `analyse_agree.py`)

The Pocket runs the same search on a slower clock against the same pill budget, so the
question is not "is it slower" (it is) but **"does a truncated search commit a different
move?"** Latency only matters through that.

It is directly observable, because the firmware is genuinely anytime: `test_search_d3.py`
publishes the running best into the result mailbox on every strict improvement, after
writing `orient=0xFF` at search start as a "no candidate yet" sentinel. So the rig records
every publish transition with its clock offset in ONE pass, and agreement at any truncation
point K is then computed analytically instead of re-running per K.

**Two gates, because a convergence curve is easy to fake accidentally.**

| gate | what it would have caught | result |
|---|---|---|
| non-perturbation | sampling that slows the thing it measures | max \|T_peek − T_bus\| = **48 clocks** of ~50M vs `dist69.log` |
| address | wrong wram index producing a plausible curve from unrelated bytes | peeked final move == bus-read move, **69/69** |

Sampling reads the dpram array directly rather than issuing host bus cycles (`dpram_agree.v`
adds `public_flat_rd` — sim-only file, read-only). The 48-clock residue is the old rig's
48-clock poll quantisation, and it has the expected sign.

**Result (69 boards, shipped `stomp180` arm):**

| commit at f of the search | agree | differ |
|---|---|---|
| 0.05 | 65.2% | 24 |
| 0.20 | 82.6% | 12 |
| 0.50 | 95.7% | 3 |
| 0.70 | 98.6% | 1 |
| **0.80 and beyond** | **100%** | **0** |

At the Pocket's 72.9M-clock budget, **68 of 69 boards finish outright**; the one that does
not (board 58, 81.9M) gets **89.0%** of its search done and commits **the same move**. Force
*every* board to 89% and agreement is still 69/69. So: **label = chain180, zero measured
quality cost from truncation.**

Two things keep that from being a vacuous result. First, agreement at f=0.05 is only 65%, so
the search really does refine late on a third of boards — 100%-at-80% is earned, not
automatic. Second, the early convergence has a **mechanism**, which is why it extrapolates to
tail boards that were never sampled: phase 0 scores every legal root move at depth 1 into
`TK1_K*`, and the deep loop's `mx1_loop` is an argmax-and-poison pass that walks that
shortlist in DESCENDING shallow score. Depth 3 is best-first over a depth-1 ranking, so it
commits the shallow favourite immediately and spends the rest confirming. A board twice as
slow as anything observed would sit at 44% completion, which the curve prices directly.

⚠ **What this does NOT measure.** Agreement is move identity, so 100% means zero cost — but a
disagreement would not imply a *large* cost, since two moves can be near-equal in eval. And
it models "the answer changed", not "the driver could still physically steer there"; late
retargeting is separately constrained by the orient lock and RECOMMIT. If a future budget
pushes boards below ~80% completion, the paired h2h should run on the diverging boards only
(`analyse_agree.py` names them) and report eval delta alongside win rate.

Incidental finding: the firmware stores col and orient as two consecutive instructions, so
for ~7 clocks the mailbox reads (new col, PREVIOUS orient) — a pair that looks valid and
never was a candidate. Total exposure across the corpus is 182 clocks in 3.44G
(0.0000053%); the 0xFF sentinel does not mask this case. Real, not worth hardware.

## Pocket sizing (`size_leafeval_pocket.sh`)

Same delta instrument as `size_leafeval.sh` but on the Pocket part (5CEBA4F23C8) with the
Pocket's own optimisation policy — its vendored `nes_pocket.qsf` ships **AGGRESSIVE AREA +
OPTIMIZATION_TECHNIQUE AREA**, not the MiSTer's SPEED. AREA-mode synthesis makes different
sharing decisions, so a delta measured under SPEED is not automatically the Pocket's delta.

| variant | ALMs (of 18,480) | RAM blocks |
|---|---|---|
| `pbase` (pre-chain, `94f84404`) | 5,906 | 1 |
| `pchain` (shipped chain engine, `80135f04`) | 6,696 | 2 |
| **delta** | **+790** | +1 |

The +790 lands within 6 ALMs of the +784 measured on the MiSTer part, so in this case the
optimisation policy did not move the cost — worth knowing, but it had to be measured rather
than assumed.

Against the Pocket core's current fit (17,380 / 18,480 = **1,100 free**) that leaves ~310
ALMs. But seed variance across the archived Pocket fits spans 17,380–18,008 — **±628 ALMs,
larger than the margin itself.** So the standalone delta says "arithmetically fits on a good
seed", not "fits"; only a whole-core trial fit decides it, and the standalone delta is not
guaranteed to survive in-core sharing either.

⚠ The Pocket's vendored `LeafEval.sv` is **code-identical** to the MiSTer pre-chain base
(comment-stripped md5 `1cecf2fc` on both) — but its header comment still advertises the OLD
eval constants (`60*setup`, `30*buried`, `12*rdy_ext`, `12*vrdy`) while the RTL underneath
carries the coef-opt winner (`32/48/8/8`). Reading that comment suggests the Pocket is
running a stale brain; it is not. Fix belongs in the canonical source + `sync_to_pocket.sh`,
never by hand in the vendored tree.
