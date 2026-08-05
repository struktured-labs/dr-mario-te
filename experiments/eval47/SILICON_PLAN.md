# #47 silicon plan: DRSTRAND root term into the copro (2026-08-04, both offline gates green)

## Validated config
`val -= 20 * g_stranded(c1)` on every ROOT candidate only (deeper plies unscored).
g_stranded = count of non-virus occupied cells with NO same-colour orthogonal
neighbour. Gates: mirror −9.85 [−16.28,−3.57] REAL; VS 54.2% vs chain180, atk
11.87v11.31. Reference deciders: eval47/ab47.py (fast), eval47/mirror47.py
(mirror), tmp/combo_term/cascade_stranded_x.py (chain+term, selfchecked).

## Architecture decision
- Chain-reward precedent: dose = runtime register ($70E6 a_chw) written by
  firmware, consumed inside LeafEval — but that term applies at EVERY eval.
  The stranded term is ROOT-ONLY → must NOT go into the per-eval leaf path.
- Root candidates ≈ 28/decision → a dedicated full-board scan is affordable
  (~128 cells ≈ hundreds of cycles ≈ ~10µs @54MHz × 28 ≈ 0.3ms/decision).
- DESIGN: new copro command ("stranded count of slot N") — a standalone scan
  FSM reusing LeafEval's board-read address path (arbitrated like existing
  states; do NOT touch the CMD-6/7 delta engine). Result in a new read
  register. Firmware root loop: after each root candidate's value, issue the
  scan on the child slot, read count, subtract DRSTRAND*count (16-bit;
  count≤~30, ws=20 → ≤600) before the root compare.
- Build knob: DRSTRAND (env, default 0). DRSTRAND=0 must emit BYTE-IDENTICAL
  firmware to shipped (the drift guard depends on this).

## Steps + validators
1. RTL: CMD dispatch in CoproDrMario.sv + scan FSM (new S_STR* states in
   LeafEval.sv or small module w/ read-port arbitration). Validator: Verilator
   co-sim unit vectors (gen corpus of boards → count vs terms47.g_stranded).
2. Firmware: root-loop integration in the LOCAL delta emitter
   (canonical tests/test_search_d3.py) + build_copro_d3 knob. Validator:
   dbg_build.py all 0 with DRSTRAND=0 → md5 c87e60a1 (byte-identical);
   run_gate.sh cell-exact PASS.
3. Co-sim behavioural gate: DRSTRAND=20 co-sim decisions vs
   cascade_stranded_x python decisions on shared boards (the bit-exact-gate
   pattern; NOTE python cascade_stranded_x uses lnkfix physics vs firmware
   ship physics — compare against a firmware-faithful python reference:
   decide_d3-based with the term, or accept decision-level spot agreement +
   the count-unit vectors as the gate).
4. Fixture check: user_flag_20260803_slot4.ss P2 board → RTL count must flag
   Exhibit A (col 5 Y/R both stranded).
5. Quartus MiSTer rbf (SPEED qsf; assert ARTIFACT md5 changed — the
   update_mif/readmemh trap). Name: NES_stomper180s20_<date>.rbf.
6. Ethernet deploy to MiSTer; silicon fingerprint rig (inject board → read
   committed placement vs decide_ship_d3+term prediction); then duel soak vs
   chain180 overnight ledger.
7. Pocket LATER (fit is tight 17,774/18,480 ALM — the scan FSM adds logic;
   check fit before promising). NO SD swap until dignity gate end-to-end.

## Traps to respect
- FIRMWARE.md: build ONLY via dbg_build.py all 0 (shadow-emitter trap);
  BASE-hex residue must not be committed; sync_to_pocket fails loud.
- ROM reproducibility: romgen + tag every shipped artifact.
- Quartus update_mif NO-OP for $readmemh — verify rbf md5 differs.
- OOM: Quartus + co-sim are heavy; do not run concurrently with big sweeps.
- Cart side: no cart/driver changes needed (term is copro-internal).
