# rtl_chain — validating the link-aware / chain-capable copro engine

Instruments behind `CoproDrMario.sv` + `LeafEval.sv` gaining a link plane, body gravity,
fixpoint resolve and the DRCHAIN reward (NES_MiSTer-winner, branch
`claude/winner-single-copro`).

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
verdict for the whole core; a *delta* instrument.

    base  5,864 ALMs / 1,225 regs / 1 RAM / 7 DSP
    chain 8,676 ALMs / 1,636 regs / 1 RAM / 7 DSP     -> +2,812 ALMs, RAM and DSP unchanged

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

## Environment

`/home/struktured/projects/dr_mario_rl/tmp/venv/bin/python` (numba + py65). The kernels are
imported from `dr_mario_rl/tmp/combo_term`.
