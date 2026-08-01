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
