# Tuck v3 — firmware design (phase 3, DESIGN DOC ONLY, no implementation)

Task #17, phase 3. This document proposes how to port the offline-proven
generalised-root-action design (`TUCK_V3_OFFLINE.md`, θ*=150, L11 −10.03 REAL,
L20 clear 99.2% p=0.039, sizing verdict GO from `decisions_L{11,20}.json`) into
the actual copro firmware + driver. **Nothing here is implemented.** Every
recommendation is written so the lead can approve, redirect, or reject each
piece independently before any RTL/6502 edit lands.

Repos referenced (read-only for this phase):
- `CANON` = `/home/struktured/projects/dr-mario-canonical-wt` (copro firmware + RTL)
- `DRIVER` = `/home/struktured/projects/dr-mario-mods-wt/driver-nav` (NES cart driver, `patch_cartridge_copro.py`)
- `QA` = `/home/struktured/projects/dr-mario-qa-wt` (validation harnesses)

---

## 1. Root enumeration source

### What exists today

`CANON/fpga/copro/tuck_scan.py` (`emit_tuck_scan`) is a **self-contained 6502
routine**, not RTL — it never touches the NODE/LeafEval hardware interface at
all. It is `JSR`'d **after** the search completes (`build_copro_d3.py:93-94`,
`stub.jsr(search_ep); stub.jsr(TUCK_ROM)`), reads the settled board directly
from `$0500`, and publishes exactly ONE descriptor
(`TUCK_COL`/`TUCK_ROW` = `$6139`/`$613A`) via a "deepest rest row wins, first
found breaks ties" global scan (`tuck_scan.py:173-184`, the `ts_take` label).

Its motion model already matches the offline proof's legality gate exactly —
its own docstring (`tuck_scan.py:9-19`) states "switch to target column `c` at
ANY row `r` the capsule passes through," the identical adjacent-column,
any-row predicate `root_search._exec_reach_cells` implements. Good continuity:
whatever enumeration design we land on, the underlying LEGALITY MODEL does not
need to change.

**Its limitation**: it has **no orientation concept at all** — implicitly
vertical-only (one target column, one approach column, no capsule-width
handling). The tuck-validation-195 README (`QA/fpga/copro/tuck_validation/README.md`)
already flagged this for the OLD v1/v2 design: "26.5% of published tucks are
for a HORIZONTAL capsule... and the enumerator is single-cell." My phase-2
offline data (n=25 games, L11, θ=150, orientation-tagged) makes this sharper
for the ROOT-ACTION design specifically: **candidates are ~50/50 horizontal
vs vertical (as expected — the BFS enumerator has no orientation bias), but
FIRED (winning) tucks are 73% horizontal (H+RH: 116/159) vs 27% vertical
(V+RV: 43/159).** A vertical-only firmware enumerator would structurally be
unable to propose the majority of what the offline proof measured as valuable.

### Two directions

| | **(a) reuse tuck_scan as-is, vertical-only** | **(b) extend to multi-candidate, both orientations** |
|---|---|---|
| Code change | Small: replace "keep only the global-best" (`ts_take`) with "append to a candidate list," called once/decision instead of once/game | Moderate: (a)'s list-append PLUS a second sweep direction for horizontal capsules (scan by row-adjacent column PAIRS instead of column-adjacent single cells) |
| ROM cost | ~same as today, ~200B | Roughly 2x today's routine (~400-500B) for the second sweep; see §7 |
| Scan cost | 8 cols × 2 sides × ≤16 rows ≈ 256 inner iterations, ~15-20 cycles each ≈ 4-5K cycles ≈ negligible vs. NODE cost | ~2x scan cost, still negligible (see §7 — the enumeration pass is NOT the bottleneck at any candidate count considered) |
| Value captured | ~27% of the offline-measured fired-tuck value (vertical share only) | ~100% of the offline-measured value (matches what `root_search.py` actually scored) |

**Recommendation: (b).** The enumeration SCAN cost is negligible either way —
the real budget question (§7) is the NUMBER OF NODE-SCORED CANDIDATES, not the
cost of finding them. Given that, there is no cost argument for shipping the
cheaper-but-27%-value option. The scan should run ONCE per decision (not once
per candidate, not once per game as today), populating a bounded candidate
list that the ply-1 root loop then iterates for scoring — this is what makes
motion legality a **search-action constraint** (enforced once, at generation
time) rather than a late publish-time filter, per the phase-1/phase-2 design
principle already established and re-affirmed by the team lead's framing.

---

## 2. Search integration

### The existing NODE machinery

The 32 base root actions are scored via a hardware BoardEngine command
protocol, mailbox-mapped at `$70E0-$70F8` (`CoproDrMario.sv:60`, `a_lev`
decode; `LeafEval.sv:49-50` for the CMD table):

```
CMD 1 = LEAF on CUR (pure eval, no land/resolve)
CMD 2/3 = slot <-> CUR copies
CMD 4 = NODE: land (from o4,col via a first-occ walk) + place + resolve + leaf   [ALL IN RTL]
CMD 5 = LAND_RESOLVE (no leaf)
CMD 6/7 = incremental DELTA-leaf engine (base latch / delta child) — a separate optimisation, unrelated to tucks
```

`test_search_d3.py:_e_node` (lines 161-168) is the 6502-side call site: write
`o4`→`LEV_A_O4`, `col`→`LEV_A_COL`, colours, `CMD=4`, poll `LEV_GO`. The RTL's
own landing walk (`LeafEval.sv:445-481`, `S_FO1`/`S_PLACE`/`S_PLACE_B`) derives
the two rest cells from `(o4, col)` — this is the RTL-side equivalent of
`_resting()`, and it is **not** capable of landing at an arbitrary row a tuck
needs.

**The gap**: there is no existing CMD that accepts explicit rest cells. CMD 1
(leaf-only) assumes a board is already correctly resolved and placed; nothing
in the current table can put a board into that state except CMD 4/5/7's
`(o4,col)`-driven walk.

### Two integration options

**Option A — extend the RTL (recommended).** Add a new CMD (e.g. **CMD 8 =
"NODE_AT"**) that skips the `S_FO1`/`S_PLACE`/`S_PLACE_B` landing-walk
computation (`LeafEval.sv:439-481`, ~40 lines) and instead takes the two rest
offsets **directly** as new argument registers (need 7 bits each, 0-127,
versus today's 2-bit `o4` + 3-bit `col`), reusing the *identical* cell-write
logic already at `LeafEval.sv:155-157` (`bl_we`/`bl_wa`/`bl_wd` for
`S_PLACE`/`S_PLACE_B`) and falling straight into the **existing, unmodified**
`S_APPLY` resolve/gravity/leaf pipeline that CMD 4/5/7 already share. This is
surgical: skip ~40 lines, add ~2 new mailbox registers, reuse essentially all
of the RTL-verified resolve/leaf machinery. Tuck children cost exactly what
base NODE children cost — matches the phase-1 budget note's "~0.6 frames per
child" estimate and the lead's own sizing verdict from `decisions_L{11,20}.json`.

**Option B — software land+resolve, zero RTL change.** Reuse the ALREADY-PROVEN
`eh_terms` pattern (`test_search_d3.py:204-322`, `_emit_eh_terms`), which
re-derives a board in 6502 RAM (`CUR=$0700`) via SOFT `land_place` +
`resolve_capped` primitives (already exist), because "the engine keeps the
resolved ply-1 board... only in an RTL slot with no read-back path"
(`_emit_eh_terms` docstring). For tucks: write a new soft
`land_place_at(r0,c0,r1,c1)` (small, mirrors what `tuck_scan` already
computes), run the existing `resolve_capped`, then bulk-copy the resolved
board into an RTL slot via the memory-mapped write window
(`CoproDrMario.sv:64`, "`$7000-$707F` W: board bytes into slot `wslot`") and
score with CMD 1. **Cost**: zero Quartus resynthesis, but a 128-byte
RAM→mapped-window copy (~640+ cycles) plus a software resolve pass per
candidate — plausibly an order of magnitude slower per candidate than Option
A's RTL-pipelined path. At the phase-2 measured worst case (12-14
candidates/decision), Option B's overhead could materially exceed the "~0.6
frames/child" budget the sizing call assumed.

**Recommendation: Option A**, given the worst-case candidate counts observed.
Option B is a viable fallback ONLY if a Quartus resynthesis is infeasible this
cycle — in that case, recommend pairing it with a TIGHTER per-decision
candidate cap than θ=150 alone provides, to keep the worst case affordable.

### Where θ=150 lives

The same 6502 code that runs the strictly-greater, keep-first argmax across
the 32 base actions today (`test_search_d3.py`, the ply-1 select loop around
lines 384-522, culminating in `D_BC`/`D_BO` "running best" updates at line
522). After each tuck child's NODE result returns (same `LEV_SCO`/`LEV_IMM`
result registers a base child uses), compute `val = imm + leaf` exactly as for
a base child, then require `val >= best_base_val + 150` before it may replace
the running best — mirroring `root_search._root_value`'s gate exactly, in the
**same integer eval units**: `fast_rtl_x.weights_rtl_r47()` /
`variant("winner")` (imm/virus=180, imm/cell=10, the 5 tunable coefficients
{vrdy8/buried48/rdyext8/setup32/matched48}) IS the python mirror of these RTL
coefficients per the coef-opt lineage that produced them — the offline θ=150
is stated in the RTL's own arithmetic scale by construction, not a rescaled
approximation. **Residual verification** (§5): a hex/RTL parameter diff check
confirming the DEPLOYED `LeafEval.sv` synthesis constants still equal these
values before trusting θ=150 unchanged.

**Depth caveat.** The offline proof scored each tuck candidate with a FULL
depth-3 subtree (ply-2 + expectimax third + DISC_SHIFT blend) — that is the
entire point of the root-action design (leaf-only scoring was the REFUTED v2).
Giving each firmware tuck child its own ply-2 subtree costs the same ~1/32 of
full search per child as a base action. At the phase-2 mean candidate rate
(~1.2-2.0/pill) this is cheap; at the observed worst case (12-14/decision) it
costs ~12-14/32 ≈ 38-44% extra search time on that single decision — see §7
for how this reconciles with the lead's own sizing verdict.

### Orientation

**Recommend both, not vertical-only** — see §1's 73%-horizontal finding.
Vertical-only forfeits the majority of the measured win.

---

## 3. Executor fixes (D1 / D2)

Both are driver-side (`DRIVER/patch_cartridge_copro.py`), independent of the
root-action redesign, and are **prerequisite for any DRTUCK cart regardless**
(confirmed still open on v1 firmware, `tuck_regression.py`, re-run 2026-08-02
read-only in phase 1 — see `TUCK_V3_OFFLINE.md` §4).

**D1 — publish `15 − r` coordinates.** `patch_cartridge_copro.py:1327`:
```python
a.ins16("LDA_abs", W_TROW); a.ins16("STA_abs", TUCK_R2)
```
copies the copro's published row directly. The executor compares this against
`$0386`, which the game stores as `15 − row` (confirmed vs meatfighter
`DrMarioAI.java:69`). Fix: insert a subtraction before the store —
`LDA #15; SEC; SBC W_TROW; STA TUCK_R2` (computes `15 - W_TROW` via the
standard 6502 idiom, since `SBC` computes `A - M - !C`).

**D2 — invalidate on new-pill edge only.** `patch_cartridge_copro.py:1369-1373`
currently invalidates (`STA TUCK_C2, 0xFF`) at the TOP of the `{L}_start`
label — reached whenever `armed==0`, i.e. every frame for the whole descent
after a pill lands and before the next search launches, not just once per new
pill. **A ready-to-apply patch already exists**:
`QA/fpga/copro/tuck_validation/d2_invalidation_fix.patch` moves the three
invalidation instructions from before the `pend`/`delay` early-out gates
(lines 1374-1375) to just after them, immediately before the board-copy loop
begins (`{L}_cp`, line 1381) — this is the genuine "a new search is about to
start" edge. Recommend applying this patch as-is (it matches independently the
fix I derived from first principles reading the same code) rather than
re-deriving it.

**tuck_regression.py section-1 re-bless plan.** The file's own docstring
already anticipates this: *"Section-1 goldens... will fail when v2's two-cell
enumerator lands — that is a deliberate RE-BLESS, not a regression. Update the
expected tuples, note two-cell semantics in the commit."* Under root-action
with a multi-candidate, both-orientation enumerator (§1), the 9 ENUMERATOR
GOLDENS (`tuck_regression.py:191-204`, single `(approach, trigger)` tuples
per board) need updating to a LIST-shaped expectation. More significantly,
**Section 2's D3 check** (`tuck_regression.py:230-243`, `enum_full`'s
"deepest-wins across all columns" reference model) tests an architecture
root-action retires entirely — under root-action there is no independent
"enumerator's opinion of the best column" to disagree with the search's
`best_col`, by construction (§4). Recommend **retiring** the D3 check (with a
note explaining why, not silently deleting it) and replacing it with a new
regression: "the published descriptor's column equals the winning tuck
candidate's actual landing column" — trivially true by construction, but
worth pinning against a few real boards so a future refactor can't
reintroduce the old decoupling.

---

## 4. Publish contract

Requirement: publish the tuck descriptor **only** when a tuck candidate IS the
ply-1 argmax; publish `0xFF` (no tuck) otherwise; no stale descriptor may
steer the next pill.

Today, two HALVES of this exist but don't compose correctly:
- **START-time default**: `build_copro_d3.py:90-91` writes `0xFF` to both
  `TUCK_COL`/`TUCK_ROW` before every search — this half is fine and should be
  kept.
- **PUBLISH-time write**: currently `tuck_scan.py` writes unconditionally
  whenever IT finds a candidate (`ts_take`, `tuck_scan.py:181-184`),
  regardless of what the SEARCH decided — this is exactly D3 (§1, §3), and is
  retired under root-action.

**New design**: the ply-1 select loop (`test_search_d3.py` ~384-522) already
tracks a "running best" (`D_BC`/`D_BO`) and updates it on every strictly-better
candidate. Add a new flag byte, e.g. `D_BKIND` (is-tuck), updated in lockstep:
set when a TUCK candidate becomes the new best, **cleared** when a BASE
candidate becomes the new best (a later base win in the same decision must
overwrite an earlier tuck win's flag). At the END of the ply-1 loop, once
`D_BC`/`D_BO` are finalised: if `D_BKIND` is set, publish the winning tuck's
`(approach, trigger)` in `15−r` units (D1-corrected) to `TUCK_COL`/`TUCK_ROW`;
else leave them at the START-time `0xFF` default. This is the direct firmware
analogue of `choose_root_with_tucks`'s `best["kind"]` tag in the offline
proof.

---

## 5. Gate plan

| gate | location | what it checks | when it applies here |
|---|---|---|---|
| **flag-off byte-identity** | bit-exactness gate, `QA/experiments/bitexact_gate/` (`gate.py`, `tb_leafeval_gate.cpp`) | with the new CMD/enumerator/publish-contract code emitted but the tuck flag OFF (`DRCOPRO_TUCK=0`/`DRTUCK=0`), the build must be byte-for-byte identical to today's shipped image | FIRST gate any change here must pass — standing rule for every opt-in feature in this codebase |
| **py65 firmware gate** | `CANON/fpga/copro/run_gate.sh` | cell-exact corpus comparison, baseline vs delta firmware moves; rebuilds `mister_vsim` from source every run (its own header explains why — a prior stale-binary bug tested the wrong eval for ~2h) | any RTL change (Option A's new CMD 8) must pass this before being trusted |
| **tuck-validation-195 co-sim** | `QA/fpga/copro/tuck_validation/` (`sim_tuck.cpp`, `sim_tuck_cap.cpp`, `gate_fire_rate.py`, `real_ab.py`, `latency.py`) | the existing 195-real-board + 22-adversarial-board corpus and testbench infrastructure that verified D1/D2/D3 and latency for v1/v2 | natural home for re-validating D1/D2's fix and the new multi-candidate/both-orientation enumerator goldens (§3) |
| **tuck_regression.py** | `QA/experiments/tuck_regression.py` | pinned regression case, 2s no-hardware | re-bless section 1, retire+replace the D3 check (§3) before promoting `DRTUCK_V2`-style hard-fail mode |
| **decide_ship_d3 proxy** | `fast_rtl_x.decide_ship_d3` / `decide_ship_d3_wdict` | predicted the chip's committed placement 3/3 in prior use (memory: `dr-mario-decide-ship-d3-proxy`) | cheap pre-silicon sanity check of a firmware build's committed placements against the python model on a handful of real boards |
| **offline A/B rerun with the FIRMWARE model** | new — wraps the real 6502 image (py65 or Verilator co-sim) in place of `root_search.choose_root_with_tucks` | re-runs the EXACT statistical harness already built (`root_search.py`/`ab_root.py`/`sweep_theta.py` — paired seeds, bootstrap CI, sign test, real NES stream) against the real firmware's search instead of the python scratch model | **the final pre-Quartus/pre-cart gate.** The θ=150 result must not be assumed to transfer from python to firmware — it must be re-measured. Only the decision-making call needs swapping (a firmware-driving wrapper analogous to how `build_copro_d3.py:main()` already validates `search_ep` calls against `decide_d3`); the statistics code is directly reusable |

---

## 6. Passengers

**#33's `$5089` xlate fix** rides the same Quartus resynthesis. Today, `$5089`
(and any other unmapped cart offset) falls through to
`default: xlate = 12'h8FE`, a single shared scratch cell — the SAME aliasing
class of bug that already broke the tuck executor once (`W_TCOL`/`W_TROW`
both landing on `$68FE` before being wired to `$6139`/`$613A`, per the
tuck-executor-gap memory). Option A's new CMD 8 mailbox registers (off_a/off_b
args) need their OWN `xlate()` cases too — this is the identical class of edit
to the identical file, at the identical resynthesis. Batch #33's personality
byte in with whatever `xlate()` cases tuck v3 needs; do not resynthesise for
either alone.

---

## 7. Budget table

**ROM (copro's own internal image, `build_copro_d3.py`, distinct from the NES
cart PRG-ROM `patch_cartridge_copro.py` patches)**: search code occupies
`$8000`–~`$88E1` (~2.2KB), `tuck_scan` today sits at `$A800` (~200B), SQ
tables start `$B000`. Free headroom: ~`$88E1`–`$A800` (~6.4KB unused) plus
~1.8KB between today's `tuck_scan` and `$B000`. A both-orientation,
multi-candidate enumerator (roughly 2x today's routine, §1) is comfortably
under 1KB — fits with wide margin. Option A's RTL CMD-8 extension is a gate
count / Verilog change, not a byte count — it needs its own timing-closure
pass (memory: `dr-mario-single-copro-fit`, "fits timing-clean, 87% ALM, MUST
use SPEED qsf" — the margin should be re-checked after adding new
registers/states, not assumed to still hold).

**Scratch RAM**: `tuck_scan` today uses 10 bytes (`$61A1`-`$61AA`) inside a
documented-free 32-byte block (`$61A1`-`$61C0`). A candidate LIST (capacity
16, matching phase-2's measured max=14 with margin) storing
`(approach, trigger, rest, orient)` = 4 bytes/candidate × 16 = **64 bytes —
exceeds the documented-free 32-byte window.** This needs a NEW scratch
allocation. Copro RAM is only `$0000`-`$0FFF` + `$6100`-`$61FF`
(`test_search_d3.py`'s own HW-CONSTRAINT comment), `$0800`-`$08FF` aliases
`$6100`-`$61FF`, and `WORK2` already lives at `$0B00` ("TK/TK1/pills end at
`$0A7F`"). There is likely headroom beyond `WORK2`'s own footprint, but the
exact free-byte accounting needs the lead's own map — **flagged as an open
item**, not computed blind here.

**Search-time cost** (the number the lead already priced GO from
`decisions_L{11,20}.json`, restated here for the doc's completeness, not
re-derived): mean 1.2-2.0 extra candidates/decision × ~1/32 of full-search
cost each ≈ 4-6% mean tempo increase; worst observed 12-14
candidates/decision × ~1/32 ≈ 38-44% on that single decision, which the lead
converted to **+8.4 frames @85.9MHz / ~13 frames at the ÷2-class clock,
against a ~195-frame fall budget — GO.**

**Caveat carried from the phase-2 report**: this offline harness logs
per-decision candidate COUNT (`n`) but not per-candidate SCORING cost
directly — the 1/32-of-full-search-per-child conversion is an estimate from
the phase-1 budget note, not a firmware-measured cycle count. The
firmware-model re-run (§5, final gate) is also the first point at which an
actual cycle count for a tuck-heavy decision becomes available; recommend
treating today's budget table as sizing-grade but not silicon-timing-grade
until that gate runs.

---

## Summary of open decisions for the lead

1. Option A (RTL CMD-8 extension) vs Option B (software land + slot-copy,
   zero RTL change) for search integration (§2) — recommend A.
2. Both orientations vs vertical-only for the enumerator (§1) — recommend
   both, given the 73%-horizontal fired-tuck finding.
3. Scratch RAM allocation for a 16-candidate list (§7) — needs the lead's own
   free-space map; not resolved here.
4. Whether to apply the existing `d2_invalidation_fix.patch` as-is (§3) —
   recommend yes.
5. Retire (not just re-bless) `tuck_regression.py`'s D3 check (§3) — recommend
   yes, with a replacement contract check.

Implementation waits for review of all five.
