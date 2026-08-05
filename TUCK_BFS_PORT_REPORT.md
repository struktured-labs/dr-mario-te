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

## Status: DONE, bit-exact, all four deliverables complete

| # | Deliverable | Result |
|---|---|---|
| 1 | Standalone 6502 BFS | `tests/tuck_bfs_6502.py`, 775 bytes code + 448 bytes data |
| 2 | py65 harness + 200-board corpus | `tests/test_tuck_bfs_6502.py`, `tests/gen_tuck_bfs_corpus.py`, `tests/tuck_bfs_corpus_200.json` |
| 3 | Bit-exact gate vs `tuck_enum` mode="free" | **200/200** |
| 4 | Budget report + capacity policy | below |

No blockers hit. Nothing was shipped partial — every stage that could be made bit-exact was
made bit-exact before moving to the next.

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
- **200/200** real L11 boards (`tuck_bfs_corpus_200.json`) — the number that matters, since
  it's what the θ=250 ship config was proven on.

No reference changes were made to reach this; every mismatch found during development (all
in early drafts, before the row-wise design was locked in) was fixed in the port.

## 3. Memory map — PLACEHOLDER, needs owner sign-off before integration

Checked against every address `test_search_d3.py` + `primitives.py` declare in this tree as
of 2026-08-04 (LIVE=$0500-$057F, WORK1=$0600, CUR/MARK=$0700/$0780, TK=$0900-$09FF,
TK1=$0A00-$0A7F, WORK2=$0B00, DBG_RING=$0C00, DBG_RING2=$0D00, LEV_*=$70xx copro RTL I/O).
**Not** cross-checked against `patch_vs_cpu.py`'s v18/v19 AI zero-page usage — those aren't
believed to run in the same build as the d3 search, but that belief needs an explicit
owner check before this ships.

```
BFS_VIS   = $0E00  (64 B)   512-bit visited plane, row y owns bytes [y*4 .. y*4+3]
BFS_OUT_X = $0E40  (128 B)  candidate columns
BFS_OUT_Y = $0EC0  (128 B)  candidate rows
BFS_OUT_O = $0F40  (128 B)  candidate orientations (0=H,1=V,2=RH,3=RV)
                            -- 448 of 512 bytes in the undocumented $0E00-$0FFF block

ZP $73-$86 (20 of a reserved 29-byte $73-$8F block), starting immediately after the d3
search's own D_STR/D_P1L/D_P1H = $70-$72. Full byte-by-byte map in tuck_bfs_6502.py's
module docstring.
```

Board input is read-only from `LIVE_BOARD` ($0500) — the routine never writes there, so it
can't corrupt the live settled board while the game renders it, matching the convention
`first_occ`/`kernel_wc` already use. `PILL_A`/`PILL_B` ($84/$85) are accepted as documented
mailbox-shaped inputs for interface parity but are **not read** by the BFS — legality
depends only on occupancy, colours never gate a placement (proven trivially: `is_legal`
never reads a colour, only the `EMPTY`/non-`EMPTY` sentinel).

The 128-entry-per-array output sizing (384 B) is generous **for the standalone gate** — see
§5 for the separate, smaller number recommended for the real firmware mailbox.

## 4. Budget

Measured via py65 instruction-cycle counting, 200-board real-L11 corpus:

| | cycles/board | candidates/board |
|---|---|---|
| min | 588,756 | 30 |
| p50 | 907,070 | 36 |
| p90 | 1,033,790 | 46 |
| p95 | 1,044,232 | 50 |
| p99 | 1,141,021 | 56 |
| max | 1,195,878 | 56 |

Code: 775 bytes. Data: 448 bytes (VIS + 3 output arrays). Candidate count showed
negligible correlation with board occupancy (Pearson r ≈ 0.08) — cost is dominated by the
row fixed-point's own structure (each row costs a handful of 32-state passes regardless of
fill), not raw cell count.

**Frame-budget comparison — this is the one open question that matters most for
integration**, because the two plausible execution contexts give opposite verdicts:

- **If this runs on the copro's own 6502 core** (clocked ~54.669 MHz per
  `dr-mario-copro-clock-tap.md`, and everything about `test_search_d3.py`'s board/ZP
  layout — the $6100-$61FF/$0800-$08FF WRAM alias, the copro-resident TK/TK1/DBG_RING
  arrays — says the *existing* depth-3 search already runs there, not on the NES's own
  CPU): one 60 Hz frame is ≈911,150 copro cycles. The median board (907,070 cycles) fits in
  **under one frame** (~16.6 ms); the worst observed board (1,195,878 cycles) takes ~1.31
  frames (~21.9 ms). Against the stated L11 gravity budget (13 frames/row ⇒ even the
  *tightest* possible placement, a 1-row fall, allows ~217 ms), a **monolithic root-call-
  per-pill is trivially feasible**, ~10x headroom even in the worst case. No amortization
  needed.
- **If this instead has to run on the NES's own 1.79 MHz CPU inside NMI-only slices**
  (`py65_harness.py`'s own docstring cites ~2,273 usable cycles/frame for that context):
  the median board needs ≈399 NMI slices (≈6.65 s), the worst ≈526 (≈8.8 s) — far beyond
  even a full-height 15-row fall (≈195 frames ≈ 3.25 s). Under this hypothesis a monolithic
  call does **not** fit and the routine would need chunking/resumability (the codebase
  already has a pattern for this — `test_resumable.py`/`test_resumable_incr.py` — the row
  fixed-point structure ports naturally to a resumable state machine: suspend/resume at
  row boundaries, or even mid-row between passes, since all live state is already in named
  zero-page/RAM rather than the call stack).

**This needs to be resolved by whoever integrates it**, ideally by checking which core
`CoproDrMario.sv` dispatches this class of routine to — the strong prior, given everything
else in `test_search_d3.py`'s memory map, is the copro core, in which case §4 says this
ships as-is with no further engineering. Flagging it explicitly rather than guessing.

## 5. Capacity policy proposal (for the real firmware mailbox — separate from the
standalone port's 128-slot test buffers, which were sized for gate correctness, not RAM
economy)

Observed over 200 real L11 boards: min 30, p50 36, p90 46, p95 50, p99 56, max 56
candidates/board (raw reachable placements, *before* θ-gating — this is the population the
depth-3 scorer sees, not the ~2-8 fires/game the SAGA's θ=250 curve reports after scoring
picks a winner most decisions don't take).

**Recommendation: mailbox capacity = 64** (power-of-2, clean indexing, covers the full
200-board sample with 8 slots of headroom over the observed max). This is a proposal on a
200-board sample, not a proof — a board that needs >64 has not been observed but hasn't
been ruled out either; the port's own capacity guard (§3, `OUT_CAP`) never silently
corrupts memory on overflow regardless of the cap chosen, it just stops appending.

**If truncation is ever needed, don't truncate by discovery order — prioritize by row
depth.** The set-difference characterization done earlier this session (`characterize_
setdiff.py`, cited in the SAGA) found the enumerator's *novel* value concentrated at rows
8-15 (RS-only: 88% horizontal, "concentrated DEEP... 254 at the floor row itself"; FW-only:
"mass at rows 8-12"). Shallow (small-`y`) candidates are the ones most likely to already be
covered by the existing straight-drop enumerator — the whole reason this BFS exists is the
deep, tucked-under-overhang placements. So a truncation policy should sort candidates by
**descending row `y`** and keep the top 64, not keep-first-found — this drops the
low-value, already-covered end of the set first if it must drop anything at all.

## 6. Open risks

1. **Memory map is unconfirmed** (§3) — needs an explicit check against every other build
   config in this tree (not just the d3 search's own documented map) before real
   integration.
2. **Clock-domain question is unresolved** (§4) — determines whether any further
   engineering (resumability) is needed at all, or whether this ships as a single
   monolithic call.
3. **200-board corpus, not exhaustive** — real L11 games from 15 deterministic seeds
   (`gen_tuck_bfs_corpus.py`, `--every 7` placements, spanning opening through near-clear:
   virus count 1-48, occupancy 11-54 cells observed). Bit-exact here is strong evidence,
   not a proof for all 2^128-ish board states; the algorithm-level proof (row-monotonicity,
   §1) is what actually carries the generality claim, and that proof does not depend on the
   corpus at all.
4. **Colours are not threaded through the output.** The BFS only emits `(x, y, orient)`;
   attaching `(colour0, colour1)` per candidate (via `tuck_enum._FLIP`, a pure function of
   `orient`) is a few-instruction addition the next session should make once the mailbox
   format is fixed, since the scorer will need it.
5. **`ROW_PASS_CAP=40`** is a hard safety net, not load-bearing — measured max real
   convergence was 4 passes/row (300 synthetic boards, `tmp/proto_rowbfs.py`'s pass-count
   variant). If a future board ever needed more than 40, the row would silently stop
   early (some legal states left unmarked) rather than hang; this has never fired in
   testing but is worth a counter/assert if this becomes safety-critical.

## 7. What the next session should do

1. Resolve the clock-domain question (§4) with whoever owns `CoproDrMario.sv` / the
   driver's dispatch logic — this single fact decides whether any further work is needed
   before integration, or whether the port ships as-is.
2. Cross-check the placeholder memory map (§3) against every build config that might
   coexist with the d3 search (not just the ones checked here).
3. Add colour output (§6.4) once the mailbox format is settled.
4. Wire `tuck_bfs` into the real firmware emitter (a new emit function alongside
   `test_search_d3.py`'s existing ones, following the DRSTRAND-style opt-in-flag pattern
   for a byte-identical-by-default build) as the candidate source for the existing
   `tuck_root_candidates`/`tuck_scan_v3` call site, replacing/supplementing them per the
   SAGA's "THE CONVERGENCE ANSWER" decision.
5. Firmware A/B at θ=250 against the current shipped enumerator, then silicon, per the
   SAGA's stated sequence.

## Files on this branch

- `tests/tuck_bfs_6502.py` — the emitter (603 lines, self-contained, doesn't touch
  `test_search_d3.py`)
- `tests/test_tuck_bfs_6502.py` — 3-stage validation harness (231 lines)
- `tests/gen_tuck_bfs_corpus.py` — 200-board real-L11 corpus generator (85 lines)
- `tests/tuck_bfs_corpus_200.json` — the corpus itself (deterministic, regenerable)
- `tests/tuck_bfs_budget_raw.json` — raw per-board cycles/candidates/occupancy/virus,
  backing §4-5's numbers
- `tests/proto_rowbfs.py` — the pre-6502 Python algorithm proof (§1), kept for provenance
- `TUCK_BFS_PORT_REPORT.md` — this file
