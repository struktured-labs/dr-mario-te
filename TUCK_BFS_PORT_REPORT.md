# Tuck BFS 6502 port (task #17, stage 4) — status report

Branch: `tuck-bfs-6502` (worktree `dr-mario-canonical-wt`, not pushed, main/copro-canonical
untouched, no `.hex`/`.rbf`/cart file touched).

Ship config this ports (decided in prior sessions, see
`dr-mario-qa-wt/experiments/tuck_v3/TUCK_V3_FIRMWARE_SAGA.md`): **TE-free BFS enumerator**,
scored downstream at **θ=250** (offline value −18.05 REAL, statistically indistinguishable
from the union enumerator's −20.02, on the exact motion-truth set the executor can actually
perform — "TE free ≡ gravity-timed, ZERO diff on 1,094 boards / 5,474 tucks"). This report
covers the **enumerator only**; θ-gating and scoring are the existing depth-3 search's job,
unchanged.

## Status: DONE, bit-exact including colours, capacity=64 wired and tested, memory map
sign-off complete

| # | Deliverable | Result |
|---|---|---|
| 1 | Standalone 6502 BFS | `tests/tuck_bfs_6502.py`, 815 bytes code + 384 bytes data |
| 2 | py65 harness + 200-board corpus | `tests/test_tuck_bfs_6502.py`, `tests/gen_tuck_bfs_corpus.py`, `tests/tuck_bfs_corpus_200.json` |
| 3 | Bit-exact gate vs `tuck_enum` mode="free", cells+orient+**colours** | **200/200** |
| 4 | Budget report + capacity policy | §4-5, capacity=64 **implemented in the 6502 routine**, not just proposed |
| 5 | Capacity-64 depth-descending overflow test | synthetic 110-candidate board, exact-selection-match, §5 |
| 6 | Memory-map sign-off vs the real firmware image | §3 — one real conflict found (tuck_v3.py ZP) and **resolved by relocation**, not just documented |

No blockers hit at any stage. This is the second pass on this branch: the first pass
(bit-exact cells+orient only, capacity=128 test-only, memory map self-checked but not
validated against the real firmware tree) is preserved in the branch's earlier commit; this
pass closes every item the team lead's follow-up asked for.

## 1. Algorithm — NOT a literal BFS-queue port, and why that's still correct

The reference (`dr-mario-qa-wt/experiments/tuck_enum.py`, `mode="free"`, meatfighter's
model) is a FIFO breadth-first search over states `(x, y, orient)`, 512 states total. A
literal port needs a work-queue that can hold up to 512 entries — but the 6502's X/Y index
registers are 8-bit, so a single `LDA table,X` can't address past offset 255. The usual
6502 fix (a 16-bit zero-page pointer walked with `(ptr),Y` and incremented across page
boundaries) works but is exactly the kind of bookkeeping most likely to hide an off-by-one.

Instead the port exploits a structural fact about the move set that the reference's own
docstring states but doesn't exploit: **Left/Right/Rotate never change row `y`, and Down is
the only move that changes it — and Down only ever increases `y`.** There is no Up. That
makes the reachable-state graph row-monotonic: once row `y`'s Left/Right/Rotate closure is
a fixed point, nothing discovered in row `y+1` (or below) can ever feed back into row `y`.
So the reachable set can be computed **row-major**: close row `y` (only 8 cols × 4 orients =
32 states — an 8-bit index) to a local fixed point, push Down into row `y+1`, repeat. No
queue, no >255 index, ever.

This was proved equivalent to the reference **before writing a line of 6502**:
`tests/proto_rowbfs.py` implements the row-wise algorithm in plain Python and diffs it
against `tuck_enum.enumerate(..., mode="free", union_straight_drops=False)` on 500 random
boards (0 mismatches) plus the module's own cave-board regression (the 3 known-by-hand
tuck cells under an overhang, all found). That file's docstring carries the full argument.

**Canonical comparison target.** `tuck_enum.enumerate()`'s default (`union_straight_drops=
True`) adds back physically-unreachable straight-drop placements the BFS itself never
finds, tagged `reachable=False` — a pure geometry BFS structurally cannot produce those, so
comparing against the *default* output would be a guaranteed, uninteresting mismatch. The
gate instead compares against `union_straight_drops=False`, i.e. the BFS's own target set —
this is the only well-posed comparison for a "port the BFS" task, and it's stated explicitly
in `tuck_bfs_6502.py`'s docstring and `test_tuck_bfs_6502.py`'s `reference_set()`.

**Canonical order.** Because reachability is order-independent (any traversal order finds
the same set — see the docstring argument), the port doesn't try to replicate the
reference's FIFO discovery order. Both sides are compared as **sets** of `(cells, orient)`;
the 6502 side additionally emits in a fixed ascending `(y, x, orient)` order for
determinism, but the gate does not depend on that order matching the reference's.

## 2. Bit-exact result

- **8,000/8,000** `is_legal(x,y,o)` checks vs a direct port of `tuck_enum._legal_table`
  (400 random boards × 20 random states each).
- **500/500** random synthetic boards, full routine vs `tuck_enum` reachable set.
- **1/1** cave-board regression (the documented "3 cells under a lip, unreachable by
  straight drop" case) — full-set match, not just the 3 marked cells.
- **200/200** real L11 boards (`tuck_bfs_corpus_200.json`), now comparing **cells + orient +
  colours** — the number that matters, since it's what the θ=250 ship config was proven on.
- **Capacity-64 overflow test** (new this pass): a synthetic board with 110 reachable
  candidates (`tests/overflow_board.json`, found by sparse-random search — dense/staircase/
  checkerboard patterns all plateaued near 30-52; independently-scattered sparse occupancy
  (3-35% fill, rows 4-15 only) found boards past 100 within a few thousand trials) confirms:
  `BFS_OUTN` caps at exactly 64; the emitted set matches, entry-for-entry, a python
  simulation of the port's OWN depth-descending priority policy applied to the full
  110-candidate reference set (`expected_after_capacity()` in the test harness — sorts by
  `(-row, col*4+orient)`, same order the 6502 emit phase walks, and truncates at 64); and
  the row boundary is respected exactly (`min_kept_row == max_dropped_row == 8` — the
  truncation happened mid-row-8, keeping every row-8-and-deeper candidate the 6502 found and
  dropping every row-7-and-shallower one, with no row order violations).

Colours were threaded through by adding two more output arrays (`OUT_CA`/`OUT_CB`) and a
small unrolled `orient in {1,2} -> flip` branch in the emit phase, matching
`tuck_enum._FLIP` exactly (verified this is **not** the same partition as `is_h(orient)` --
flip groups {V, RH} together, not {H, RH}). PILL_A/PILL_B ($92/$93 after the ZP move, §3)
went from "documented but unread" to real inputs the emit phase now reads; the harness sets
them before every call via a new `call_bfs()` helper.

No reference changes were made to reach any of this; every mismatch found during
development (all in early drafts, before the row-wise design was locked in, and one
branch-range assembler error introduced by the colour-emission code growing a loop body
past 127 bytes -- fixed with the same invert+JMP idiom already used elsewhere in the file)
was fixed in the port.

## 3. MEMORY-MAP VALIDATION — SIGNED OFF, one conflict found and resolved

Validated against the real firmware image, not just the d3 search's own declared map:
`build_copro_d3.py`'s `build_image()` (every ROM/RAM region it lays down), every
runtime-written address in `test_search_d3.py`'s emitter, `primitives.py`, `test_depth2.py`,
**and `tuck_v3.py`** — the existing `DRCOPRO_TUCKV3`-gated firmware (the prior-generation
root-action tuck implementation this port is downstream of per the SAGA's "THE CONVERGENCE
ANSWER") — plus a direct read of `CoproDrMario.sv`'s address decode for the RAM claim, since
the copro's WRAM is a single flat 4 KB block and python-side "nothing claims this address"
isn't itself proof against a hardware alias.

**RAM $0E00-$0F7F (384 B): CONFIRMED FREE, unconditionally.**

| Region checked | Address | Verdict |
|---|---|---|
| LIVE/BOARD | $0500-$057F | outside claimed range |
| WORK1 | $0600 | outside claimed range |
| CUR / MARK (EH_PLY1 build) | $0700 / $0780-$078F | outside claimed range |
| TK\_\* (incl. PILLA/PILLB) | $0900-$09FF | outside claimed range |
| TK1\_\* | $0A00-$0A7F | outside claimed range |
| WORK2 | $0B00 | outside claimed range |
| DBG_RING / DBG_RING2 | $0C00-$0DFF | outside claimed range |
| LEV\_\* (engine I/O) | $70xx | different address space entirely — not WRAM (`a_ram_lo` requires `AB[15:12]==0`; $70xx fails that test, confirmed in `CoproDrMario.sv`) |
| tuck_v3.py: CANDLIST, TS_CNT/TS_DROP, TS_\* | $61A1-$61AC, $61F6-$61F7 | mailbox window ($61xx, aliases wram[$8xx] only) — nowhere near $0Exx |
| tuck_scan.py (v1, EMIT_TUCK) | — | no RAM/ZP claims found at all beyond the `EMPTY` constant |
| CoproDrMario.sv hardware alias | $0800-$08FF ↔ $6100-$61FF | the ONLY WRAM alias that exists; $0E00-$0FFF is untouched by it — `dpram` is a flat 4 KB block, $0000-$0FFF passes straight through except that one documented alias |

Nothing claims $0E00-$0FFF anywhere in the checked tree or the RTL. This routine takes 384
of those 512 bytes (VIS 64 B + 5×64 B output arrays, resized down from the first pass's 448
B when capacity dropped from a 128-slot test buffer to the real 64-slot mailbox cap).

**ZP: moved from $73-$88 to $81-$96 (22 B) after finding a real collision — now CONFIRMED
FREE, unconditionally.**

The first pass claimed $73-$88, right after the d3 search's own map (`D_STR`/`D_P1L`/
`D_P1H` = $70-$72). That missed `tuck_v3.py`, which was never checked in the first pass.
`tuck_v3.py`'s SCORING/GATING scratch (`TP_BASE` through `TK2_TMPH`) occupies **$73-$80** —
a direct, byte-for-byte overlap with 14 of this routine's first-pass 22 claimed bytes.

That overlap is *not* automatically fatal: `tuck_v3.py`'s own docstring documents the same
"time-disjoint phases reuse the same bytes" convention `primitives.py`'s ZP pool already
uses for $CA-$D5, and applies it to $70-$72 on purpose (`TI1L`/`TP_IDX` deliberately reuse
`D_STR`/`D_P1L`/`D_P1H`, since the #47 stranded-half dose and tuck scoring never run at the
same instant). Checking which of `tuck_v3.py`'s TWO phases actually uses $73-$80: its
enumerator (`tuck_scan_v3`) keeps its own scratch (`TS_C`/`TS_FC`/... ) entirely in the
$61xx mailbox window — none of it is zero page. Only the **scoring** functions
(`tuck_cell_prep`, `tuck_imm1`, `tuck_ply2_score`, `tuck_root_extension`) use $70-$80. Since
this port replaces the *enumerator* half and feeds the *same downstream scoring*, the
natural call order is enumerate-then-score — meaning this routine's ZP state is provably
dead by the time scoring's reuse of the same bytes begins. That would have been a legitimate
"confirmed free, conditional on call order" sign-off.

Rather than ship a conditional, the routine was moved instead: $81-$96, immediately after
`tuck_v3.py`'s own `TK2_TMPH`=$80. A fresh sweep of every `.py` file in the build chain
(`test_search_d3.py`, `primitives.py`, `patch_vs_cpu.py`, `test_depth2.py`,
`test_leaf_d3.py`, `test_pollution.py`, `test_readiness_ext.py`, `test_vrdy.py`,
`tuck_v3.py`, `tuck_scan.py`, `build_copro_d3.py`, `build_firmware.py`) for any hex literal
in $81-$96 found nothing. This removes the conditional entirely — no call-order requirement,
no risk from a future re-entrancy or ordering bug silently corrupting either routine's
state. `patch_vs_cpu.py`'s v18/v19 AI zero page ($00-$01, $6B-$6F, $CA-$E1) is confirmed a
non-issue per the session lead's resolution addendum below (different CPU's address space).

The relocation is a pure address relabel (same 22 named bytes, same logic) — re-ran the full
4-stage test suite after the move and got byte-identical results (200/200, 500/500, cave
board, overflow test all still pass, same 815-byte code size).

```
BFS_VIS    = $0E00 (64 B)  512-bit visited plane, row y owns bytes [y*4 .. y*4+3]
BFS_OUT_X  = $0E40 (64 B)  candidate x
BFS_OUT_Y  = $0E80 (64 B)  candidate y
BFS_OUT_O  = $0EC0 (64 B)  candidate orient (0=H,1=V,2=RH,3=RV)
BFS_OUT_CA = $0F00 (64 B)  candidate colour at cells[0]
BFS_OUT_CB = $0F40 (64 B)  candidate colour at cells[1]

ZP $81-$96 (22 B), immediately after tuck_v3.py's TK2_TMPH=$80.
Full byte-by-byte map in tuck_bfs_6502.py's module docstring.
```

Board input is read-only from `LIVE_BOARD` ($0500) — the routine never writes there, so it
can't corrupt the live settled board while the game renders it, matching the convention
`first_occ`/`kernel_wc` already use. `PILL_A`/`PILL_B` ($92/$93) must now be set before
calling (§2) — legality itself still doesn't depend on them, only the emit phase's colour
output does.

## 4. Budget

**Clock domain: RESOLVED (session lead, see addendum at the end of this file) — this runs
on the copro's own 6502 core at 54.669 MHz, the same core the d3 search it extends already
runs on.** At that clock, one 60 Hz frame is ≈911,150 cycles; the numbers below (updated for
the colour+capacity-64 changes, code grew from 775 to 815 bytes) still fit comfortably
inside a single frame at every percentile measured. No amortization/chunking needed — the
routine ships as a single monolithic per-pill call. The NES 1.79 MHz / NMI-only math further
down is kept as reference for a hypothetical future native-cart port, where it WOULD bind.

Measured via py65 instruction-cycle counting, 200-board real-L11 corpus:

| | cycles/board | candidates/board |
|---|---|---|
| min | 590,781 | 30 |
| p50 | 909,335 | 36 |
| p90 | 1,035,925 | 46 |
| p95 | 1,046,553 | 50 |
| p99 | 1,143,398 | 56 |
| max | 1,198,327 | 56 |

Code: 815 bytes (was 775 before colour output + the descending-emit-loop invert/JMP fix).
Data: 384 bytes (VIS + 5 output arrays, capacity-64 sized — down from 448 bytes at the
first pass's 128-slot test-only sizing). Candidate count showed negligible correlation with
board occupancy (Pearson r ≈ 0.08 on the first-pass data, unchanged in character) — cost is
dominated by the row fixed-point's own structure (each row costs a handful of 32-state
passes regardless of fill), not raw cell count.

**Frame-budget verdict (copro core, 54.669 MHz — see the addendum below for how this was
resolved): one 60 Hz frame is ≈911,150 copro cycles.** The median board (909,335 cycles)
fits in **under one frame** (~16.6 ms); the worst observed board (1,198,327 cycles) takes
~1.32 frames (~21.9 ms). Against the stated L11 gravity budget (13 frames/row ⇒ even the
*tightest* possible placement, a 1-row fall, allows ~217 ms), a **monolithic root-call-
per-pill is comfortably feasible**, ~10x headroom even in the worst case observed. No
amortization or resumability work is needed for this routine. (The NES 1.79 MHz / ~2,273
cycles-per-NMI-slice math — ≈399-526 NMI slices, i.e. seconds, which would NOT fit inside a
single pill's fall — is retained only as reference for a hypothetical future native-cart
port, where `test_resumable.py`'s chunking pattern would be the template.)

## 5. Capacity policy — IMPLEMENTED in the routine, not just proposed (for the real
firmware mailbox; the first pass's 128-slot buffers were test-only sizing for gate
correctness, not RAM economy)

Observed over 200 real L11 boards: min 30, p50 36, p90 46, p95 50, p99 56, max 56
candidates/board (raw reachable placements, *before* θ-gating — this is the population the
depth-3 scorer sees, not the ~2-8 fires/game the SAGA's θ=250 curve reports after scoring
picks a winner most decisions don't take).

**Implemented: `OUT_CAP=64`** (power-of-2, clean indexing, covers the full 200-board sample
with 8 slots of headroom over the observed max of 56). This is calibrated on a 200-board
sample, not a proof — a real board that needs >64 hasn't been observed but hasn't been
ruled out either.

**Truncation priority: descending row depth, implemented in the 6502 emit phase itself
(§3's `tb_emit_phase`), not left as a downstream policy note.** The set-difference
characterization done earlier this session (`characterize_setdiff.py`, cited in the SAGA)
found the enumerator's *novel* value concentrated at rows 8-15 (RS-only: 88% horizontal,
"concentrated DEEP... 254 at the floor row itself"; FW-only: "mass at rows 8-12"). Shallow
(small-`y`) candidates are the ones most likely to already be covered by the existing
straight-drop enumerator — the whole reason this BFS exists is the deep, tucked-under-
overhang placements. The emit phase now scans the visited plane in **descending row order**
(y=15 down to 0; construction/phase-1 is unaffected and still runs ascending, which is
load-bearing for correctness — see §1) so that if `BFS_OUTN` ever reaches `OUT_CAP`, the
candidates dropped are exactly the shallowest ones, not an arbitrary discovery-order subset.

**Validated, not just implemented:** a synthetic board with 110 reachable candidates
(`tests/overflow_board.json`) confirms the 6502 output — 64 candidates, correctly capped —
matches EXACTLY a python simulation of the same priority policy applied to the full
110-candidate reference set (sort by `(-row, col*4+orient)`, take the first 64; see §2). The
boundary row (8, in this synthetic board) was split between kept and dropped candidates
exactly as expected, and the row-priority invariant (`min_kept_row >= max_dropped_row`)
holds. This is the strongest evidence available short of a real board that overflows.

## 6. Open risks (updated — most of the first pass's list is now closed)

1. ~~Memory map is unconfirmed~~ **CLOSED (§3)** — validated against the real firmware
   image including `tuck_v3.py`; the one real conflict found was resolved by relocation,
   not merely documented.
2. ~~Clock-domain question is unresolved~~ **CLOSED** — resolved by the session lead
   (addendum below): copro core, comfortably inside budget, no amortization needed.
3. ~~Colours are not threaded through the output~~ **CLOSED (§2, §5)**.
4. ~~Capacity policy is a proposal, not implemented~~ **CLOSED (§5)**.
5. **200-board corpus, not exhaustive** — real L11 games from 15 deterministic seeds
   (`gen_tuck_bfs_corpus.py`, `--every 7` placements, spanning opening through near-clear:
   virus count 1-48, occupancy 11-54 cells observed). Bit-exact here is strong evidence,
   not a proof for all 2^128-ish board states; the algorithm-level proof (row-monotonicity,
   §1) is what actually carries the generality claim and does not depend on the corpus at
   all. The capacity-64 overflow test (§5) used a SEPARATE synthetic board specifically
   because the 200-board corpus's own max (56) couldn't exercise truncation.
6. **`ROW_PASS_CAP=40`** is a hard safety net, not load-bearing — measured max real
   convergence was 4 passes/row (300 synthetic boards, `tests/proto_rowbfs.py`'s pass-count
   variant). If a future board ever needed more than 40, the row would silently stop early
   (some legal states left unmarked) rather than hang; this has never fired in testing but
   is worth a counter/assert if this becomes safety-critical.
7. **Memory-map validation was done by grepping `.py` sources for hex literals in the
   claimed ranges**, not by static analysis of the assembled bytecode or a formal address
   allocator — a hex constant assigned to a variable but never actually used, or an address
   computed at runtime (e.g. via an indexed table rather than a literal), would not show up
   in that sweep. Nothing in the checked files does this, but the sweep's soundness rests
   on that observation holding, not on a structural guarantee.

## 7. What the next session should do

1. Wire `tuck_bfs` into the real firmware emitter (a new emit function alongside
   `test_search_d3.py`'s existing ones, following the DRSTRAND-style opt-in-flag pattern
   for a byte-identical-by-default build) as the candidate source for the existing
   `tuck_root_candidates`/`tuck_scan_v3` call site, replacing/supplementing them per the
   SAGA's "THE CONVERGENCE ANSWER" decision. The memory map (§3) and colour output (§2)
   are both ready for this; nothing further should block starting it.
2. Decide the exact call-site contract with `tuck_v3.py`'s scoring functions
   (`tuck_cell_prep`/`tuck_ply2_score`/`tuck_root_extension`) — they currently walk
   `CANDLIST` at $61AC (5 bytes/candidate: target, approach, trigger, rest, orient) in the
   mailbox window; this port's output shape (5 parallel 64-byte arrays in $0E00-$0F7F) is
   different and will need either a translation step or a rework of the scoring loop's own
   indexing to read the new layout directly.
3. Firmware A/B at θ=250 against the current shipped enumerator, then `run_gate.sh` co-sim,
   then silicon, per the SAGA's stated sequence.

## Files on this branch

- `tests/tuck_bfs_6502.py` — the emitter (self-contained, doesn't touch
  `test_search_d3.py`)
- `tests/test_tuck_bfs_6502.py` — 4-stage validation harness (is_legal, random boards +
  cave board, 200-board bit-exact gate incl. colours + capacity check, capacity-64
  overflow/priority test)
- `tests/gen_tuck_bfs_corpus.py` — 200-board real-L11 corpus generator
- `tests/tuck_bfs_corpus_200.json` — the corpus itself (deterministic, regenerable)
- `tests/overflow_board.json` — synthetic 110-candidate board for the capacity-64 test
  (found by sparse-random search, ~3-35% fill in rows 4-15 only; provenance in §2)
- `tests/tuck_bfs_budget_raw.json` — raw per-board cycles/candidates, backing §4-5's numbers
- `tests/proto_rowbfs.py` — the pre-6502 Python algorithm proof (§1), kept for provenance
- `tests/translate_ref.py` — Python reference for the CANDLIST translation (§8.1-8.2),
  validated against `tuck_scan_v3_ref.py` before any 6502 was written
- `tests/tuck_bfs_translate_6502.py` — the translation emitter (§8.3)
- `tests/test_tuck_bfs_translate_6502.py` — full-chain py65 validation harness (§8.4)
- `tests/validate_tuckbfs_wiring.py` / `tests/validate_tuckbfs_wiring_corpus.py` —
  end-to-end firmware wiring validation (§8.5); the corpus variant has a known
  in-process-loop anomaly documented in its own docstring, use per-board subprocess
  isolation (as both scripts' own single-board path does) for anything that matters
- `fpga/copro/build_copro_d3.py` — modified (not new): added the `DRCOPRO_TUCKBFS` knob
  (§8.5), byte-identical when unset
- `TUCK_BFS_PORT_REPORT.md` — this file

## RESOLUTION ADDENDUM (session lead, 2026-08-05 early)

Section 4's open question — which CPU executes this — is resolved by the
project's own architecture: task #17 targets the COPRO firmware
(test_search_d3.py emits copro-side code; the d3 search this extends runs on
the copro's 6502 core at 54.669 MHz, per the copro-clock-tap work). At that
clock, the median 907k-cycle board completes in ~16.6 ms ≈ one 60 Hz frame,
p99 ~21 ms — comfortably inside a pill's fall window (13 frames/row at L11).
NO amortization/chunking needed. The NES-side 1.79 MHz math in section 4
stays as reference for any future native-cart (v28cs-lineage) port, where
chunking WOULD be required.

Corollary: the zero-page placeholder ($73-$86) needs checking only against
COPRO firmware ZP usage (test_search_d3.py/primitives.py — already done);
patch_vs_cpu.py's NES-side AI zero page is a different CPU's address space
and is NOT a collision surface for this integration.

Remaining before silicon: mailbox format + colour threading, capacity=64
wiring with depth-descending priority, memory-map sign-off, firmware A/B at
θ250 via the mirror rig, then run_gate.sh co-sim.

## FOLLOW-UP (this session, after the addendum above): the ZP sign-off moved

The addendum's corollary said checking the ZP placeholder against
`test_search_d3.py`/`primitives.py` was "already done" and sufficient. Doing
the full memory-map validation this pass asked for (§3) turned up one file
that check hadn't covered: `tuck_v3.py`, the existing `DRCOPRO_TUCKV3`-gated
firmware — its scoring/gating scratch (`TP_BASE`..`TK2_TMPH`) occupies
$73-$80, a real byte-for-byte overlap with this routine's original $73-$88
claim. Analysis showed it would have been safe under a time-disjoint-phase
argument (tuck_v3.py's ZP use there belongs to its scoring phase, not its
enumerator, and this routine's own ZP is dead by the time scoring runs) — but
rather than ship a conditional sign-off, the routine's ZP was moved to
$81-$96 (right after tuck_v3.py's own last byte), which is unconditionally
free against every file checked including tuck_v3.py. Pure address relabel;
re-ran all 4 test stages after the move, byte-identical pass. See §3 for the
full table.

## 8. CANDLIST TRANSLATION + FIRMWARE WIRING (third increment, this session)

The team lead's next ask: implement the translation from tuck_bfs's output arrays into
tuck_v3.py's `CANDLIST` format, wire it behind a new `DRCOPRO_TUCKBFS` knob following the
`DRSTRAND` opt-in pattern, and validate the full chain against `tuck_scan_v3`. All three are
done. New files: `tests/translate_ref.py` (Python reference, validated first), `tests/
tuck_bfs_translate_6502.py` (the 6502 port), `tests/test_tuck_bfs_translate_6502.py` (py65
validation), `tests/validate_tuckbfs_wiring.py` + `tests/validate_tuckbfs_wiring_corpus.py`
(end-to-end firmware validation).

### 8.1 The translation contract — narrower than it might look, and why

`CANDLIST` ($61AC, 14 slots × 5 B: target/approach/trigger/rest/orient) is NOT a simple
reshaping of tuck_bfs's `(x, y, orient)` triples. Tracing every read of `approach`/`trigger`
through tuck_v3.py's scoring functions settled the question of whether they're real:
`tuck_cell_prep` reads `target`/`rest`/`orient` only (to place cells via `land_place_at`) —
but `tuck_root_extension` reads `approach`/`trigger` for the WINNING candidate specifically,
publishing them to `TUCK_COL`/`TUCK_ROW` ($6139/$613A) — the driver's physical steering
target for the real falling pill. So `approach`/`trigger` are a real execution contract
(single-adjacent-column, single-row entry point, in tuck_scan_v3's own restricted motion
vocabulary), not passthrough metadata this port can invent values for.

tuck_bfs's `(target, rest, orient)` already IS tuck_scan_v3's geometric candidate identity
(`_cells_of(x,y,o)` and `candidate_cells(target,rest,orient)` are the same function). What's
missing is deriving a valid `(approach, trigger)` for each one — and NOT every tuck_bfs
candidate has one, precisely because tuck_bfs's reachability model is a proper superset of
tuck_scan_v3's restricted one (that superset is the entire reason this port exists).
Measured on the 200-board real-L11 corpus (uncapped, to see the true population before the
14-slot cap): **median 36 raw BFS candidates/board, but only median 2 (mean 3.34, max 12)
survive translation** — the other ~89% require genuinely multi-step paths (multiple lateral
moves and/or rotations) that a single adjacent-column slide-in can't express. The 14-slot
capacity never bound in this sample (max translated was 12). This is consistent with —
not a contradiction of — the team lead's framing that surfacing the REST of tuck_bfs's value
needs a wider execution contract, tracked separately (task #60) and deliberately not
pre-empted here.

### 8.2 Derivation rule + a real bug found in the existing firmware's own model

For each tuck_bfs candidate, the translation tries `side = target-1` then `side = target+1`
(tuck_scan_v3's own documented tie-break order), scanning trigger rows ascending and
simulating the fall — literally re-running tuck_scan_v3's own geometric rule restricted to
one `(target, rest)` query. Validated bit-exact in Python first (`translate_ref.py` vs
`tuck_scan_v3_ref.py`'s own uncapped output): **0/732 mismatches over 400 random boards.**

That validation surfaced a genuine, pre-existing over-approximation in tuck_scan_v3's own
model (not introduced by this port): its rule bounds valid trigger rows by
`first_occ(approach)` alone — it checks the approach column is *empty* that deep, but never
that a pill could actually *get there* at a shallow row. Found a concrete board where this
matters: tuck_scan_v3 claims `target=7, approach=6, trigger=5` is valid, but column 6 is
only enterable by first sliding through column 5, and column 5's wall doesn't open until row
8 — with no Up move in the whole model, a pill reaching column 6 at all is already past row
5. Traced this by hand (`column 5 all 16 rows: [3,1,2,1,2,3,2,2,0,1,2,2,2,3,0,2]` — occupied
every row through 7, first empty at row 8) before accepting it as a real finding, not a
translation bug: confirmed the target/rest key itself is correctly ABSENT from tuck_bfs's
own reachable set on that board (tuck_bfs's row-monotonic BFS proves it unreachable, full
stop), so this class of error cannot leak into the translation through the target side.

**Defensive refinement added anyway, not just relied on the argument above:** every found
`(approach, trigger)` is additionally checked against tuck_bfs's own VISITED bitplane
(`BFS_VIS` is still populated after `tuck_bfs` returns; the check reuses `tb_vis_test`
verbatim — zero new computation) before being accepted. A candidate whose descriptor doesn't
verify is dropped, not silently accepted. This is a second line of defense against the SAME
failure class showing up on the approach side of a target that IS legitimately reachable via
some other path.

### 8.3 6502 port — one real bug, found and fixed before shipping

Assembled clean on the first pass (1427 bytes combined with tuck_bfs, 92 labels) but failed
its first correctness test: a 5-board smoke run found entries missing specifically from
HORIZONTAL geometry (`orient` 0/2) whenever the second `first_occ` lookup ran. Root cause:
the horizontal min-computation (`fc = min(first_occ(target), first_occ(target+1))`) stashed
the first result in `TR_TMP` intending to compare it after the second `tr_first_occ` call —
but `tr_first_occ` uses `TR_TMP` as its OWN internal offset-walking scratch, so the second
nested call clobbered the first result before the comparison ran (measured: computed
`FC=11` instead of the correct `6` on a real corpus board). Fixed by giving the "remember
across a nested call" role its own register (`TR_TMP2`), which is a broader lesson worth
stating plainly: **a helper subroutine's own internal scratch is not safe as a caller-side
temporary across a second call to that same helper** — same trap class as the ZP allocation
discipline elsewhere in this file, just at the subroutine-composition level instead of the
whole-program level. Re-ran the 5-board smoke test after the fix: 5/5 clean, then scaled up.

Also hit and fixed one more branch-range assembler error (the visited-check block growing
the emit-phase loop body past 127 bytes) — same invert-and-JMP idiom already established in
`tuck_bfs_6502.py`, not a new pattern.

New ZP: `$97-$A8` (18 B), immediately after `tuck_bfs_6502.py`'s own `$81-$96` claim.
Confirmed free by the same sweep methodology as §3 (every `.py` file in the build chain,
including `tuck_v3.py`) — no hits beyond the `TXS` opcode literal (`0x9A`) in
`build_copro_d3.py`/`build_firmware.py`, which is an instruction encoding, not an address.

### 8.4 Validation: 50-board full chain, bit-exact + scan_v3 cross-checked

Full chain (`tuck_bfs` → `tr_translate` → `CANDLIST`) run under py65 on **50 real L11 corpus
boards**:

- **50/50 boards match `translate_ref.py`'s prediction exactly** (same CANDLIST contents,
  entry for entry).
- **0 scan_v3 cross-check surprises** across 198 total CANDLIST entries: every single one
  matches what `tuck_scan_v3_ref.py`'s own uncapped rule would compute for that exact
  geometric candidate, confirming the port never emits a candidate scan_v3's own model
  wouldn't also endorse (the §8.2 over-approximation case is excluded by construction, as
  argued, and this 50-board sweep found zero counterexamples to that argument).
- Aggregate: 198 CANDLIST entries / 1,648 drops across 50 boards (mean 3.96/32.96),
  consistent with §8.1's 200-board figures.

### 8.5 Firmware wiring: `DRCOPRO_TUCKBFS`, byte-identity confirmed

Added to `build_copro_d3.py` following the `DRSTRAND`/`EMIT_TUCK_V3` opt-in-flag pattern
exactly: `EMIT_TUCK_BFS = os.environ.get("DRCOPRO_TUCKBFS", "0") == "1"`, asserted mutually
exclusive with both `EMIT_TUCK` and `EMIT_TUCK_V3` (alternative enumerators feeding the SAME
unmodified tuck_v3.py scoring functions — `tuck_cell_prep`/`tuck_ply2_score`/
`tuck_root_extension`/`land_place_at` are called completely unchanged, just emitted onto a
new image built from `tuck_bfs` + `tr_translate` instead of `tuck_scan_v3`). Shares
`TUCK_V3_ROM`'s address as `TUCK_BFS_ROM` (never co-resident, so no collision) rather than
claiming a 4th ROM region. **Zero changes to `test_search_d3.py`** — every address the new
block needs (`resolve_capped`, `expectimax`, `eh_terms_scan`, `cp_live_cur`) was already
exposed for `EMIT_TUCK_V3`'s identical use of them.

**Byte-identity, verified not asserted:** built `build_image()` with the flag unset before
and after the full edit (using a git-stash round-trip to get a true pre-edit baseline) —
`md5(image) = 753bfb2397d10b5de078a1c9068433d2` in both cases. Re-confirmed once more after
the translation code and the ZP-collision fix landed. Every new code path is additive
(new `if EMIT_TUCK_BFS:` blocks, new stub conditionals appended after the existing ones) —
nothing existing was reordered or modified.

**A pre-existing, unrelated bug was found and NOT fixed (out of scope, and not mine):**
calling `build_image()` fresh in a plain Python process throws `KeyError: 'eh_terms_scan'`
— reproduced identically on `EMIT_TUCK_V3=1` against the git-stashed ORIGINAL
`build_copro_d3.py`, before any of this session's edits, so this is not a regression this
port introduced. Root cause (traced, not fixed): importing `test_vrdy` AND
`test_readiness_ext` together, before `test_search_d3`, leaves `test_search_d3.build()`'s
output missing that label — `dbg_build.py`'s own header comment obliquely acknowledges the
fragility class this belongs to (it force-preloads `test_search_d3` via `importlib` before
anything else can import it). All validation in this section used that same
force-preload pattern, matching the project's own established workaround rather than
inventing a new one.

**End-to-end validation** (`validate_tuckbfs_wiring.py`, `validate_tuckbfs_wiring_corpus.py`,
using the force-preload pattern, real L11 corpus boards, full stub reset→DONE flow through
py65's RTL-engine emulation):

- `S_BEST_C`/`S_BEST_O` (the base search's own decision) matches `decide_d3`'s reference
  EXACTLY on every board tried — the base search is provably unaffected by any of this.
- `BFS_OUTN`, and `TS_CNT + TS_DROP`, correctly account for every candidate across every
  board sampled this way (e.g. board id 20: `4 + 34 = 38`; id 60: `4 + 30 = 34`; id 80:
  `2 + 42 = 44` — checked on 6+ boards, always exact).
- Board id=0's specific result (`TS_CNT=0, TS_DROP=30` — every one of 30 raw candidates
  lacked a verified descriptor) was cross-checked against `translate_ref.py`'s independent
  prediction for that exact board and matched exactly.
- No tuck fired (`TUCK_COL != 0xFF`) in a 20-board sample — expected, not a red flag: the
  SAGA's own θ=250 measurement puts the base rate at ~4.84 fires per WHOLE GAME (tens of
  decisions), so the chance of a single sampled decision-point firing is low, and these 20
  boards are independent snapshots, not one continuous trajectory.
- A convenience script (`validate_tuckbfs_wiring_corpus.py`) that loops over multiple boards
  IN ONE PROCESS shows every board finishing suspiciously fast with everything reading 0 —
  not reproduced when each board is isolated in its own subprocess (which is how every
  number above was actually obtained). Not root-caused; flagged prominently in that file's
  own docstring and here rather than left as a silent trap for whoever runs it next.

### 8.6 What's still open after this increment

1. The pre-existing `eh_terms_scan` KeyError (§8.5) should get root-caused by whoever owns
   the `test_vrdy`/`test_readiness_ext`/`test_search_d3` import interaction — it currently
   blocks calling `build_image()` directly outside the `dbg_build.py`-style force-preload
   workaround, for EMIT_TUCK_V3 as much as for EMIT_TUCK_BFS.
2. The `validate_tuckbfs_wiring_corpus.py` in-process multi-board anomaly (§8.5) is
   unexplained. Suspect `attach_engine_emu`'s `ObservableMemory`/closure state isn't
   properly scoped per `Cpu` instance across repeated in-process calls, but this wasn't
   confirmed.
3. No tuck has been observed to actually WIN the θ gate in this session's testing (small,
   independent-snapshot sample). A real firmware A/B (per the SAGA's stated sequence, θ=250
   via the mirror rig) is the next real test of whether this enumerator's value shows up in
   play, not a substitute for it.
4. Colours are still not part of `CANDLIST` (§2's colour work applies to `tuck_bfs`'s own
   output arrays only) — confirmed genuinely unnecessary for this path specifically, since
   `tuck_cell_prep` re-derives colour from `S_CA`/`S_CB` directly, independent of anything
   `tuck_bfs` emits.
