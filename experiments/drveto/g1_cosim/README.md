# G1 (minimal) -- delta-path co-sim gate for DRVETO / Fix A

py65 structurally cannot execute CMD-6/7 (attach_engine_emu has no delta path),
so every py65 gate ran USE_DELTA=False while the SHIP hex is the delta build.
This gate closes that disclosed gap on the REAL RTL (Verilator, the recovered
REBUILD_VSIM invocation + `--public-flat-rw` for the observer; sources =
fpga/copro/{CoproDrMario.sv,LeafEval.sv,copro6502.v,copro_alu.v}, md5-identical
to the NES_MiSTer-winner fork at 08f2343: CoproDrMario da3e5e80, LeafEval
5f062096).

Battery: `gen_g1_cases.py` (11 cases: 5 vetog1 fatal-board reconstructions,
3 note-A goldens + 1 veto-silent golden, RV_clear_c3, PC4cap0) ->
`build_g1.sh` + `build_g1_hexes.py` -> 4 hexes through `sim_g1_veto.cpp` ->
`run_g1.py` verdict.  Result: G1_RESULT.txt -- **PASS**, 2026-08-30.

Per-iteration assertions on the shipped-config delta path (MEASURED):
- the zp $B4 D_VETO write executes for every s_loop candidate (count == py65
  reference on all 11 cases);
- at every $B4 write the last completed LeafEval command is CMD-4 and live
  lev_rvc/lev_win equal that CMD-4's latched values (the C1 freshness
  invariant);
- delta final == base final on all 11 cases (and == the py65 full-stub
  reference on all 11 -- no RTL-vs-emu leaf divergence on this corpus);
- no vetoed candidate is bus-visible in the mailbox during the search phase
  while unvetoed candidates exist (the G2 invariant at RTL level; search/tuck
  phase split by the first fetch into [$9000,$A800) -- zp $B4 is stale after).

Killed mutants / positive controls:
- **M2 under delta** (0b2f9998, flag moved to o_cand): cmd4viol fires 208 times
  across all 11 cases -> KILLED by the freshness invariant -- the exact trap
  class py65 could not see.
- **veto1** (47edb895, the pre-Fix-A shipped hex): passes every final/freshness
  check (the delta-path emission audit confirmed in-rig) but publishes the
  VETOED (3,0) mid-search on PC4cap0 (`3:0:1:s`) -- the anytime hole
  demonstrated on the real RTL; fixa_delta (a2b2e4ac) on the same board never
  stores it.

Hexes: fixa_delta = tmp/drveto/veto2_fixa.hex a2b2e4ac (ship candidate) ·
fixa_base b85e8945 · m2_delta 0b2f9998 · veto1 47edb895.
Runtime: ~25-42M copro clocks/case, ~4 min/arm wall on blackmage.

⚠ Builder provenance trap (found live in build_g1_hexes.py, now pinned): a
second `import build_copro_d3` in one process can bind a SIBLING worktree's
builder (the emitter's module-level sys.path inserts put dr-mario-mods first) --
it silently produced the th400 BASELINE f78f1e93 while claiming to build the M2
mutant.  Pin build_copro_d3 by path, like build_dbgpub pins the emitter.
