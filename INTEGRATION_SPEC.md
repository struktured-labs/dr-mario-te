# Cartridge search-integration spec (ultracode workflow wf_acbf841e, 2026-06-28)

Verdicts: zp-coloring=SOUND, stack-safety=SOUND, slicing=FLAWED (FATAL gravity-lock; fix below).

## zp_map

CANONICAL DECISION (resolves design1 vs design2/3): persistent driver state goes to RAM ($0190+, absolute addressing — the driver is OUR code and doesn't need zp modes), leaving the scarce zp window exclusively for the primitives/kernel that HARD-REQUIRE zp addressing. This is design2/3's approach; design1's all-zp packing works but is needlessly tight. Window $CA-$E1 = 24 bytes split: 12 shared-temp POOL + 9 DEDICATED + 3 WRAPPER-OWNED.

== WRAPPER-OWNED, RESERVED (verified against patch_vs_cpu.py _build_rotation_wrapper) ==
  $DA  Z_BORIENT  (orientation, full 0-3; wrapper reads `CMP $DA` vs $03A5) — publish target
  $DD  target column (wrapper reads `LDA $0385; CMP $DD`) — publish target
  $DF  last-seen P2y (wrapper-managed new-pill edge; line 1117 `STA $DF` every frame) — DO NOT TOUCH
  >>> CORRECTION to all three input designs: they reserved {$DA,$DD,$DE}. The ACTUAL wrapper code
      uses $DD (not $DE) for the column and uses $DF for last-y. $DE is FREE; $DF is sacred.
      Designs 1&3 put Z_OFFB at $DF and design2 put last-y logic implicitly — either clobbers the
      wrapper's only new-pill detector. Fixed here.

== 9 DEDICATED (one address each; never pooled) ==
  $D6 SH_MAXH      live: shape -> score
  $D7 SH_HOLES     live: shape -> score
  $D8 SH_TOPRISK   live: shape -> score
  $D9 Z_TILEA      pill tile A (set ONCE per pill at arm; read by kernel place; persists across slices)
  $DB Z_TILEB      pill tile B (set ONCE per pill at arm)            [skip $DA reserved]
  $DC Z_OFFA       placed cell A offset (read by kernel place + find_clears_targeted)
  $DE Z_OFFB       placed cell B offset  [moved off $DF onto the now-free $DE]
  $E0 RV_CELLS     resolve grand total (kept at original addr; live resolve->score)
  $E1 RV_VIR       resolve grand total (kept at original addr; live resolve->score)

== 12-byte SHARED POOL P0..P11 = $CA..$D5 ==
  P0 $CA  P1 $CB  P2 $CC  P3 $CD  P4 $CE  P5 $CF  P6 $D0  P7 $D1  P8 $D2  P9 $D3  P10 $D4  P11 $D5

Per-phase occupancy (phases are TIME-DISJOINT within one placement-eval; a slice boundary is a
placement boundary where the ENTIRE pool is dead and recomputed next placement):
  PhaseA driver-landing (first_occ + offset calc, before kernel):
     P0=first_occ working offset (was $F8) ; P1=SE_FOL ; P2=SE_T(fo*8 temp)
  PhaseB resolve/find_clears (PEAK, 12 of 12):  full-board pass during fc_flush is the binding clique:
     P0=_ROW/_COL  P1=_OFF  P2=_STEP  P3=_CNT  P4=_RUN  P5=_MCOL  P6=_RSTART  P7=_FLCNT
     P8=_BP1(bitpack walk offset, fc_flush)  P9=_BP2(bitpack mask, fc_flush+fc_apply)
     P10=PASS_CELLS  P11=PASS_VIR        (Z_OFFA/B dedicated $DC/$DE also live; RV_* dedicated live)
  PhaseB gravity (between fc passes; fc temps dead):
     P0=_GCOL  P1=_GREAD  P2=_GDEST  P3=_GTILE
  PhaseC shape (resolve fully returned):
     P0=_SHCOL  P1=_SHOFF  P2=_SHSEEN  P3=_SHTMP   (SH_* dedicated being written; RV_* live)
  PhaseD score (kernel returned):
     P0=SE_SLO  P1=SE_SHI  P2=SE_T  P3=T_LO  P4=T_HI  (reads RV_* + SH_* dedicated; writes best to RAM)

SHARING PROOF (no two simultaneously-live vars share a byte):
 1. _ROW and _COL share P0: full find_clears completes ALL rows (fc_hrow loop on _ROW) BEFORE any
    column (fc_vcol loop on _COL) — strictly sequential, never co-live (primitives.py 73-84).
 2. find_clears and gravity never overlap: resolve calls find_clears (RTS, P0-P9 dead) THEN gravity
    (RTS) THEN loops — so _G* safely reuse P0-P3.
 3. PEAK is the FULL-board cascade pass (12 live), NOT the targeted first pass (11 live, no _ROW/_COL
    but +Z_OFFA/B which are DEDICATED $DC/$DE, off-pool). Both fit: full=12<=12, targeted=11+2ded.
 4. _FLCNT kept as its OWN pool byte (P7) — NOT aliased to _RUN. (The _RUN/_FLCNT alias is valid but I
    decline it: keeping them separate costs the last pool byte yet needs no lifetime argument from the
    implementer. The alias is the documented spare-byte recovery if a future capped-buried term needs
    one — see DEPTH2 _build_marginal_burial Z_BURIED.)
 5. Bitpack scratch _BP1/_BP2 (NEW vars) get P8/P9. They must be distinct from P0-P7 because fc_flush
    runs INSIDE fc_scan (whose loop counter is Y) — so fc_flush must NOT clobber Y and instead walks the
    cell offset in _BP1 (zp) and holds the mask in _BP2, freeing X for the table index. SH_MAXH ($D6) is
    NOT borrowed for this (design3 did) — keeping bitpack scratch in-pool avoids any cross-region aliasing.
 6. PhaseD score temps (P0-P4) reuse the pool after the kernel returns; they read only DEDICATED
    operands ($D6-$D8 SH_*, $E0-$E1 RV_*) and the persistent best in RAM — zero collision with P0-P4.
 7. SE_FOL (P1) survives the 2nd first_occ in h_loop because first_occ touches only P0 (its working
    offset) — verified against test_search.py h_loop (103-106).

PERSISTENT (cross-slice / cross-pill): Z_TILEA $D9, Z_TILEB $DB (set once/pill at arm, never in pool
range $CA-$D5). All driver cursor/best/colors/state are in RAM (see ram_layout), NOT zp.

RENAME TABLE (primitives.py lines 22-28 constants, plus hardcoded literals):
  _ROW $E2->$CA  _COL $E3->$CA  _OFF $E4->$CB  _STEP $E8->$CC  _CNT $E9->$CD  _RUN $E5->$CE
  _MCOL $E6->$CF  _RSTART $E7->$D0  _FLCNT $EA->$D1  (+NEW _BP1=$D2 _BP2=$D3)
  PASS_CELLS $EB->$D4  PASS_VIR $EC->$D5
  _GCOL $ED->$CA  _GREAD $EE->$CB  _GDEST $EF->$CC  _GTILE $F0->$CD
  _SHCOL $F4->$CA  _SHOFF $F5->$CB  _SHSEEN $F6->$CC  _SHTMP $F7->$CD
  SH_MAXH $F1->$D6  SH_HOLES $F2->$D7  SH_TOPRISK $F3->$D8
  RV_CELLS $E0 KEEP  RV_VIR $E1 KEEP
  first_occ $F8->$CA (lines 246,249,251)
  find_clears_targeted $6D->$DC, $6E->$DE (lines 113,117,121,125)
  kernel place $6D->$DC, $6E->$DE, $D2->$D9, $D3->$DB (lines 232,233)
TEST (test_search.py 24-32): Z_OFFA $6D->$DC, Z_OFFB $6E->$DE, Z_TILEA $D2->$D9, Z_TILEB $D3->$DB;
  score temps onto the pool to validate the sharing: SE_SLO $66->$CA, SE_SHI $67->$CB, SE_T $6A->$CC,
  T_LO $5E->$CD, T_HI $5D->$CE, SE_FOL $5F->$CB. PERSISTENT test bookkeeping (SE_ORIENT/SE_COL/
  SE_BCOL/SE_BORIENT/SE_BESTLO/SE_BESTHI/SE_PCA/SE_PCB) STAYS in low zp $5D-$65/$68-$69 (no conflict
  with $CA-$E1) — lowest-risk path to 400/400; their address is immaterial to the coloring proof since
  none of them share. (Full RAM relocation of these is optional extra fidelity; not required for the gate.)

## ram_layout

Region $0100-$01BF (page-1 low stack; probe-confirmed free $0100-$01EE). All live data <= $019F; a
32-byte guard band $01A0-$01BF separates it from the stack-descent zone.

| range        | size | use |
|--------------|------|-----|
| $0100-$017F  | 128B | WORK — the MUTABLE working board the sim operates on (relocated from SCRATCH=$0600) |
| $0180-$018F  | 16B  | MARK — bit-packed find_clears mark buffer (relocated from MARK=$0300) |
| $0190        | 1B   | ST_MODE   0=IDLE, 1=SEARCHING, 2=DONE  (also serves as the publish "valid" flag) |
| $0191        | 1B   | SE_COL    cursor column 0..7 |
| $0192        | 1B   | SE_ORIENT cursor orient 0=vert / 1=horiz |
| $0193        | 1B   | SE_BCOL   best column |
| $0194        | 1B   | SE_BORIENT best orient (0/1, pre-encoding) |
| $0195        | 1B   | SE_BESTLO best score lo (16-bit) |
| $0196        | 1B   | SE_BESTHI best score hi |
| $0197        | 1B   | SE_PCA    current pill color A (snapshot at arm) |
| $0198        | 1B   | SE_PCB    current pill color B |
| $0199        | 1B   | ST_BUSY   re-entrancy guard (0 free / 1 slice in flight) |
| $019A-$019F  | 6B   | reserved |
| $01A0-$01BF  | 32B  | GUARD BAND (unused margin) |
| $01C0-$01EE  | --   | stack-descent risk zone DURING search — DO NOT USE |

BOARD MODEL (canonical = WORKING-COPY; resolves design1's NMI-glitch risk #2):
The settled board $0500-$057F (stable during a pill's fall, constraint 4) is treated as PRISTINE and is
NEVER written by the search. Each placement, the kernel COPIES $0500->WORK($0100) and runs
place/resolve_targeted/shape on WORK. There is NO restore loop (next placement re-copies). Because $0500
is never mutated, an NMI render mid-slice (the search runs in the main loop, an NMI can still fire on
hw vblank) always reads the true settled board -> ZERO playfield glitch, even on a multi-frame cascade
eval. This is strictly safer than the backup/restore model (which flickers for the few frames a >30k-cyc
cascade placement spans). first_occ (landing calc, driver) reads PRISTINE $0500 (== WORK at copy time).
  primitives.py edits: BOARD(line 17) used by resolve/find_clears/gravity/shape/place -> WORK=$0100;
  add PRISTINE=$0500 used ONLY by first_occ and the kernel copy source; remove SCRATCH(line 221); kernel
  (228-239) becomes: copy PRISTINE->WORK (LDA $0500,X / STA $0100,X, X=0..127), place 2 cells into WORK,
  resolve_targeted, shape, RTS (delete the k_rs restore loop). test_kernel "restored" check trivially
  holds ($0500 untouched); outputs unchanged -> 4500/4500 stands after re-run.

STACK-COLLISION MARGIN (worst case = NMI nested inside a main-loop slice):
 - Gameplay SP top ~ $01EE (game uses ~17 stack bytes).
 - Slice call chain in the main-loop spin: trampoline->slice->kernel->resolve_targeted->find_clears->
   fc_scan->fc_flush ~7 JSR levels ~14 bytes -> SP ~ $01E0 mid-slice.
 - An NMI fires on hw vblank mid-slice: pushes PC+P (3) plus the game's NMI-handler depth (~17) ->
   worst SP ~ $01CC.
 - Highest live RAM byte = $019F. Margin to $01CC = 45 bytes; the $01A0-$01BF guard band absorbs any
   deeper-than-modeled descent down to $01C0. WORK ($0100-$017F) is lowest/safest.
 - MUST MEASURE on Mesen: log min SP across a slice WITH an NMI nested (Lua). If SP dips below $01C0,
   shrink the chain (inline fc_flush) or drop MARK/driver-state lower. Note bit-packing already removed
   the stack PHA/PLA that design1's mark-set would have added, keeping the chain shallow.

py65 test impact: primitives.py SCRATCH->WORK=$0100, MARK->$0180; per the working-copy split above.
RAM driver state ($0190+) is exercised only by the ROM driver (re-tested separately); the existing
test_search keeps its bookkeeping in low zp (zp_map), so 400/400 validates the zp coloring + bitpack +
working-copy without a RAM/abs rewrite of the test harness.

## mark_scheme

Bit-pack the 128-cell mark buffer to 16 bytes at MARK_BASE=$0180 (constraint 6; no 2nd clean 128-block
exists — WORK takes $0100-$017F). cell offset c(0..127) -> byte MARK_BASE+(c>>3), bit (c&7). Add an
8-byte ROM table in the unit-1 bank: BITS: .byte $01,$02,$04,$08,$10,$20,$40,$80.

Three edits in primitives.py emit_find_clears. KEY constraint: fc_flush is JSR'd from INSIDE fc_scan
whose loop counter is Y (132-153) -> fc_flush MUST preserve Y. fc_apply is the tail-call (NOT inside the
Y loop, 94-105) -> may clobber Y. The packing is chosen so fc_flush never touches Y (no stack push
needed), keeping the call chain shallow for the stack-margin argument.

1) fc_clearmark (88-91): zero 16 bytes instead of 128 (also ~210 cyc faster):
   LDA #0 / LDX #15
   .clr STA $0180,X / DEX / BPL .clr
   STA PASS_CELLS / STA PASS_VIR / RTS

2) fc_flush SET (155-162): walk the cell offset in _BP1($D2) so X is free; hold the mask in _BP2($D3);
   Y untouched:
   fc_flush:
     LDA _RUN / CMP #4 / BCC fc_fldone
     LDA _RSTART / STA _BP1
     LDA _RUN / STA _FLCNT
   fc_flmark:
     LDA _BP1 / AND #7 / TAX / LDA BITS,X / STA _BP2     ; _BP2 = bit mask (X used transiently)
     LDA _BP1 / LSR / LSR / LSR / TAX                     ; X = byte index
     LDA _BP2 / ORA $0180,X / STA $0180,X                 ; set the bit (absolute,X into page 1)
     LDA _BP1 / CLC / ADC _STEP / STA _BP1                 ; advance offset by _STEP
     DEC _FLCNT / BNE fc_flmark
   fc_fldone: RTS
   (Y preserved throughout; only X/A/_BP1/_BP2 used.)

3) fc_apply TEST+CLEAR (94-105): keep cell offset in X (it indexes WORK); use Y + _BP2 for the bit math:
   fc_apply:
     LDX #127
   fc_ap:
     TXA / AND #7 / TAY / LDA BITS,Y / STA _BP2          ; mask
     TXA / LSR / LSR / LSR / TAY / LDA $0180,Y           ; load mark byte
     AND _BP2 / BEQ fc_apnext                             ; test the cell's bit
     LDA WORK,X / AND #$F0 / CMP #$D0 / BNE fc_apnv / INC PASS_VIR
   fc_apnv:
     INC PASS_CELLS / LDA #$FF / STA WORK,X               ; WORK = $0100, abs,X
   fc_apnext:
     DEX / BPL fc_ap / RTS

Correctness: marks ACCUMULATE across all row+col scans before any clear, so a cell in both a horizontal
and a vertical >=4 run is cleared exactly once — identical to the validated 128-byte version (the pack is
a faithful re-encoding of the same set/test/clear set). Cost: fc_flush/fc_apply add ~8-9 cyc/cell of
shift+lookup (fc_apply ~+1.6k worst pass); per-placement stays ~17-20k. Re-validate via py65 BEFORE ROM:
test_clear_detect 800/800, test_resolve 500/500, test_kernel 4500/4500, test_search 400/400; re-measure
avg/max placement cyc with py65_harness to confirm 1 placement/frame keeps margin under ~25k.

## slicing

RESUMABLE STATE MACHINE driven by the MAIN-LOOP spin patch ($B660-$B664 wait_for_vblank, DEPTH2 §7),
NOT the NMI. This is the explicit resolution of constraint 3's failure mode: one placement eval (~17k,
up to ~114k on a cascade) is 7x-50x the ~2273-cyc NMI window, so an in-NMI search overruns -> next NMI
re-enters -> stack corruption -> mode=255 hang. The spin runs in the main loop (~25k usable cyc/frame);
a slice that overruns merely delays that frame's main work, and the NMI fires, renders pristine $0500,
and returns normally — no corruption.

PERSISTED BETWEEN SLICES: RAM $0190-$0199 (ST_MODE, SE_COL, SE_ORIENT, SE_BCOL, SE_BORIENT, SE_BESTLO,
SE_BESTHI, SE_PCA, SE_PCB, ST_BUSY) + zp Z_TILEA $D9 / Z_TILEB $DB. NOTHING in the 12-byte pool survives
a boundary — a boundary is always a PLACEMENT boundary (never inside a kernel call), where the pool is
fully dead and rebuilt next placement. The board is NOT snapshotted by the slicer: each placement re-
copies pristine $0500->WORK (stable during the fall, constraint 4), so all slices see an identical run-
free settled board (the precondition resolve_targeted requires).

SPIN-HOOK SLICE (once per frame, via $D2CC trampoline into unit-1 bank):
  if ST_BUSY != 0: RTS                      ; re-entrancy guard (defense-in-depth)
  if ST_MODE != SEARCHING: RTS              ; idle/done -> nothing to do
  INC ST_BUSY
  ; --- advance to the next LEGAL cursor, doing exactly ONE eval ---
  step:
    compute landing for (SE_ORIENT,SE_COL) via first_occ on $0500
      (vert: fo>=2 ; horiz: min(foL,foR)>=1)  ; mirrors test_search v_loop/h_loop
    if ILLEGAL: advance_cursor ; if exhausted -> goto finish ; else goto step   ; skips are cheap
    set Z_OFFA $DC / Z_OFFB $DE ; JSR kernel (copy$0500->WORK, place, resolve_targeted, shape) ;
      compute 16-bit score (eval_and_score epilogue) ; if score > SE_BEST(strict, keep-first): update
      SE_BESTLO/HI, SE_BCOL, SE_BORIENT
    advance_cursor
  finish_or_yield:
    if cursor exhausted: JSR publish ; ST_MODE = DONE
  DEC ST_BUSY ; RTS
  advance_cursor: orient0 col 0..7, then orient1 col 0..6 (exactly test_search order, for argmax tie
    fidelity), exhausted after orient1/col6.

PLACEMENTS PER SLICE = 1 (one EVAL; illegal cursors are skipped within the same slice at ~hundreds of
cyc each). Bound: one targeted eval ~17k cyc < ~25k spin budget with margin; 2 evals (~34k) would
overrun. At most 15 cursor steps (8 vert + 7 horiz) -> <=15 slices -> <=15 frames (~0.25 s), well inside
an L11 pill's multi-tens-of-frames fall. The rare cascade eval (up to ~114k ~ 4 frames) is atomic
(kernel not internally resumable); it overruns but, running in the main loop, is non-fatal (next NMI
fires-and-returns). Optional hardening if measured common: cap resolve cascades at 4 passes in rt_loop
(~60k ~ 2 frames, bounded golden divergence) — only if py65 cycle histogram shows it necessary.

PUBLISH / DONE: when the cursor exhausts, `publish` writes the target the $FF54 wrapper reads (see
output_wiring): if SE_BCOL==$FF (topped out, no legal placement) write a safe fallback (col 3, orient 0)
so the wrapper never acts on garbage; else write column->$DD and the encoded orientation->$DA, then set
ST_MODE=DONE LAST. Store order is load-bearing: $DD and $DA first, ST_MODE=DONE (the valid flag) last,
so the wrapper (which can run between our stores in a later frame) never sees a torn (col,orient) pair.
ST_MODE==DONE latches; subsequent spin calls RTS immediately until the next pill re-arms.

PER-PILL RE-TRIGGER (new-pill detection): REUSE the wrapper's existing edge — it already re-plans once
per pill when P2y ($0386) INCREASES vs $DF (patch_vs_cpu.py 1106-1110). No separate signature byte is
spent. At that edge the wrapper calls our ARM (replacing its `JSR search_entry; LDA $00; STA $DD`):
  arm: ST_MODE=SEARCHING ; SE_COL=0 ; SE_ORIENT=0 ; SE_BESTLO=SE_BESTHI=0 ; SE_BCOL=SE_BORIENT=$FF ;
       read the active P2 pill's two colors -> SE_PCA/SE_PCB ; (ORA #$40) -> Z_TILEA $D9 / Z_TILEB $DB
       (set ONCE here, not per eval) ; RTS.
The wrapper keeps managing $DF every frame (line 1117) — we do not touch it. While ST_MODE!=DONE the
wrapper holds the pill (gate below), giving the spin its ~15 frames to finish before lock.

## output_wiring

GROUNDED in the real wrapper (patch_vs_cpu.py _build_rotation_wrapper 1094-1139). The memory-note
"$DD/$DE col, $DA orient" was partly stale; the CODE contract is:
  - TARGET COLUMN -> $DD   (move block: `LDA $0385 (P2 capsule X); CMP $DD`; nudge R/L/Down via $F6)
  - TARGET ORIENT -> $DA = Z_BORIENT, FULL 0-3 state (orient block: `LDA $03A5; CMP $DA`; rotate CCW
    via $F8=0,$F6=$80 until $03A5==$DA). NOT a 0/1 H/V flag — it is the exact $03A5 rotation state, and
    its parity also encodes COLOR ORDER (comment 1118-1122: 0/2 = horizontal two color orders, 1/3 =
    vertical two color orders).
  - $DF = wrapper's last-seen P2y (new-pill edge) — RESERVED, never written by the search.
  - $DE is FREE (the docstring's "$DE" is superseded by the $DD code) -> reused for Z_OFFB.

PUBLISH (our slice, on completion): write $DD = SE_BCOL ; write $DA = encode(SE_BORIENT, color order) ;
then ST_MODE=DONE last. ORIENT ENCODING: our SE_BORIENT 0=vertical (PCA@offa=upper), 1=horizontal
(PCA@offa=left). Map to $03A5: vertical -> {1 or 3}, horizontal -> {0 or 2}, choosing the value whose
color order matches PCA-at-offa. The current search (test_search) does NOT enumerate color-swapped
variants (always PCA@offa, PCB@offb), so only 2 of the 4 states are ever published; build a verified
2-entry map (placeholder: vertical->1, horizontal->0, matching the wrapper's Z_BORIENT=0=horizontal
default at line 720). REUSE v28cs's own color-order convention here — it already produces a correct 0-3
Z_BORIENT for the same $03A5 actuator, so copy its encoding rather than deriving fresh.

WRAPPER EDITS (3 small changes to _build_rotation_wrapper):
  (a) Replace the per-pill `JSR search_entry; LDA $00; STA $DD` (1110-1113) with `JSR arm` — arm only
      starts our resumable search (sets ST_MODE=SEARCHING, snapshots colors); it does NOT set $DD/$DA.
  (b) GATE the orient block (1123-1129) and the move block (1131-1138): prefix each frame with
      `LDA ST_MODE($0190); CMP #2(DONE); BNE w_hold` where w_hold = RTS (no rotate, no move, no drop
      this frame). While SEARCHING the pill hovers; once publish sets DONE, the existing rotate-to-$DA
      and move-to-$DD logic drives P2 unchanged. This also gates the Down/drop so the pill cannot lock
      before the search commits.
  (c) Keep line 1117 (`STA $DF`) — the wrapper's new-pill edge stays intact and owns $DF.

BYPASS of v28cs's own search: v28cs previously computed its shallow target inside `search_entry` (sets
Z_TARGET=$00, Z_BORIENT=$DA) and the wrapper snapshotted $00->$DD. We replace that synchronous decision
entirely: arm starts OUR async search; publish is the sole writer of $DD/$DA thereafter. The $FF54
rotate+move ACTUATOR is untouched and unverified-logic-free (it is the validated v28cs mover) — we only
change WHO fills its target cache and WHEN.

CALL CHAIN per frame: NMI/game per-frame logic -> $FF54 wrapper (arm on edge; else gated rotate/move) ;
separately, wait_for_vblank spin ($B660 patch) -> JSR $D2CC trampoline -> unit-1 bank slice entry ->
one placement on zp/WORK/MARK (shared, not banked) -> on completion publish $DD/$DA + ST_MODE=DONE ->
trampoline restores prior MMC1 bank on EVERY exit path (including ST_BUSY bail and DONE). Gate ST_BUSY
in the FIXED bank before the trampoline so a bail never needlessly bank-switches.

ADDRESSES to confirm on disasm/Mesen before flashing: $DD col, $DA orient(0-3 + color parity), $DF
reserved, $03A5 orient state, $0385 P2 capsule X, $0386 P2y, $F6/$F8 move/rotate triggers, $D2CC
trampoline, $B660 spin; ACTIVE P2 pill colors source for SE_PCA/SE_PCB (the current falling pill, NOT
the $031A/$031B next-pill preview — candidate $0381/$0382, confirm P1 vs P2 bank).

## risks

1. ORIENT/COLOR ENCODING is the top correctness surface. $DA must be the full $03A5 0-3 state AND its
   parity encodes which color is top/left. Our search fixes PCA@offa, so it can only publish 2 of 4
   states; a wrong map yields legal-looking but mis-colored placements that silently tank clear-rate.
   VALIDATE on Mesen against a hand-checked board (place a known 2-color pill, confirm $03A5 ends where
   expected and colors land correctly). Reuse v28cs's existing color-order encoding rather than deriving
   fresh. If the search later adds color-swap variants, it doubles placements (~30 frames) but uses all
   4 states — measure fall-window headroom first.

2. $DF clobber (already fixed here, but the implementer must not regress it). Two of the three input
   designs put a search var on $DF; the real wrapper uses $DF as last-seen P2y for new-pill detection.
   Z_OFFB is on $DE (free), not $DF. Grep the assembled search for any write to $DA/$DD/$DF other than
   publish; there must be NONE except publish ($DD,$DA) and the wrapper ($DF).

3. Stack collision with NMI nested inside a main-loop slice. Worst SP modeled ~$01CC (7-deep slice
   ~$01E0, + NMI push 3 + game NMI handler ~17). Highest live RAM = $019F; guard band to $01BF. MEASURE
   min SP on Mesen (Lua) during a slice WITH an NMI firing mid-eval; if it dips below $01C0, inline
   fc_flush (removes a JSR level) or move MARK/driver-state lower (WORK must stay $0100-$017F).

4. py65 RE-VALIDATION GATE (do FIRST, before any ROM work). After the zp remap + MARK bit-pack +
   working-copy board: test_search 400/400, test_kernel 4500/4500 match + 4500/4500 restore (now
   trivial since $0500 untouched), test_resolve 500/500, test_clear_detect 800/800, test_gravity
   800/800, test_shape_eval 600/600. The bit-packed set/test/clear and the WORK relocation are the only
   logic changes to validated routines — they must pass cell-for-cell. Run the slicer to completion in
   one call and confirm it reproduces 400/400 (same enumeration order + strict-> keep-first).

5. Execution context: confirm the slice runs in the wait_for_vblank spin ($B662), fires exactly once per
   frame (not per spin iteration), and that an NMI firing mid-slice returns cleanly (ST_BUSY blocks
   accidental re-entry). An accidental in-NMI placement is the constraint-3 hang.

6. Pill-lock vs search latency. The wrapper gate (ST_MODE!=DONE -> hold, incl. Down) must actually
   prevent lock during the ~15 search frames. Confirm the held pill does not auto-lock from gravity
   alone before DONE; if L11 gravity is fast enough to matter, also gate the game's gravity/lock for P2
   on ST_MODE==DONE, or arm during the spawn animation. Confirm $0500 EXCLUDES the falling pill (only
   the settled board), else the targeted-resolve precondition and landings break.

7. Cascade overrun frequency. If deep (~114k) cascade evals are common at L11, dropped frames could make
   P2 sluggish. Histogram per-eval cyc on py65 over the 400 boards; if the 95th-pct slice exceeds ~25k,
   cap resolve at 4 passes (bounded golden divergence) and re-validate.

8. Bank-switch hygiene: the $D2CC trampoline must restore the exact prior MMC1 PRG bank on every slice
   exit (ST_BUSY bail, mid-search yield, DONE). Code size: search+primitives+state machine (~1.2KB) in
   the unit-1 bank with BITS table; spin shim + arm + gate edits in fixed-bank free ROM (~392B
   fragmented) — confirm the assembled layout fits before flashing. v28cs stays the demo ship until the
   ROM is validated on Mesen.

Files to edit: /home/struktured/projects/dr-mario-mods/tests/primitives.py (zp 22-28, find_clears 70-162
incl. bitpack rewrite of fc_clearmark/fc_flush/fc_apply, gravity 165-189, shape 192-218, kernel/
working-copy 221-239, first_occ 242-254); /home/struktured/projects/dr-mario-mods/tests/test_search.py
(zp 24-32); /home/struktured/projects/dr-mario-mods/tests/test_kernel.py (22-46);
/home/struktured/projects/dr-mario-mods/patch_vs_cpu.py (_build_rotation_wrapper 1094-1139: arm + gate +
publish wiring).

## Adversarial verdicts

### Verdict 0: sound

Traced every claimed live range against the actual emitted instructions in primitives.py (emit_find_clears 70-162, emit_gravity 165-189, emit_shape 192-218, emit_kernel 224-239, emit_first_occ 242-254) and test_search.py (v_loop 89-98, h_loop 102-114, eval_and_score 118-157). No zp conflict found.

1. PhaseB peak is genuinely 12 distinct bytes: in fc_flush-within-fc_scan the co-live set is _ROW/_COL(P0 $CA), _OFF(P1 $CB), _STEP(P2 $CC), _CNT(P3 $CD), _RUN(P4 $CE), _MCOL(P5 $CF), _RSTART(P6 $D0), _FLCNT(P7 $D1), _BP1(P8 $D2), _BP2(P9 $D3), PASS_CELLS(P10 $D4), PASS_VIR(P11 $D5) = exactly $CA-$D5, no dup. Z_OFFA/B($DC/$DE) and RV_*($E0/$E1) are off-pool dedicated, so the spec's loose "Z_OFFA/B also live" note during the FULL pass is harmless (they are actually dead there).

2. _ROW/_COL sharing $CA is safe: fc_hrow (74-78) completes all rows before fc_vcol (79-84) starts, and line 79 re-inits _COL=0, so no stale value; fc_scan/fc_flush never write $CA so _ROW survives the scan. fc_scan does mutate _OFF($CB) but fc_hrow recomputes _OFF from _ROW each iteration (line 75).

3. The Z_TILEA/Z_TILEB relocation off $D2/$D3 is correct and load-bearing: test_kernel.py:23 and primitives.py:232-233 confirm the live contract Z_TILEA=$D2,Z_TILEB=$D3; the spec moves them to $D9/$DB and reuses $D2/$D3 for _BP1/_BP2. Since _BP1/_BP2 are live in fc_flush, NOT moving the tiles would clobber the per-pill-persistent tile bytes. $D9/$DB are touched by no phase, so the tiles persist across every placement eval.

4. SE_FOL(P1) vs SE_SHI(P1) not co-live: SE_FOL last read h_loop line 106 before eval_and_score; SE_SHI first written line 124; the intervening second first_occ (104) touches only $F8->$CA=P0, confirming proof #7 against real code.

5. Score temps (P0-P4) safe: kernel RTS's at line 121 before the 123-150 accumulation, so no primitive co-runs; max co-live is 4 vars (SE_SLO,SE_SHI,T_LO,T_HI during the holes term 137-142); operands RV_*/SH_* are dedicated $E0/$E1/$D6-$D8, disjoint from $CA-$CE.

6. Gravity _G*(P0-P3) and shape _SH*(P0-P3) reuse the pool only after find_clears RTS's and after PASS_* are consumed into RV_* (resolve 56-57); neither touches RV_*($E0/$E1) which must survive to score. Confirmed in code.

7. $DF (wrapper last-y) carries no search var; Z_OFFB is on the free $DE, correctly fixing the design1/3 $DF clobber. Persistent SE_* bookkeeping stays in low zp $5D-$69 (test) / RAM $0193+ (ROM), disjoint from $CA-$E1, so no scoped temp reaches it.

8. Window bound holds: every byte is in $CA-$E1 (pool $CA-$D5; ded $D6-$D9,$DB,$DC,$DE,$E0,$E1; wrapper $DA,$DD,$DF). No $E2+ use, none below $CA. RV_CELLS/RV_VIR kept at $E0/$E1.

**Fix:** None needed for the zp-coloring lens. Two implementer cautions (not conflicts, already specified but must not regress): (a) apply the Z_TILEA $D2->$D9 and Z_TILEB $D3->$DB moves atomically with introducing _BP1=$D2/_BP2=$D3, or fc_flush will clobber the tiles; (b) tighten the spec's PhaseB prose to say Z_OFFA/B are DEAD in the full-board pass (live only in the targeted first pass), since the current "also live" wording overstates occupancy though it is off-pool and harmless.

### Verdict 1: sound

STACK MARGIN IS SAFE BY A WIDE MARGIN; the <8-byte flag is NOT triggered.

CALL-CHAIN VERIFICATION (primitives.py, read in full): Deepest path during a slice = spin -> JSR $D2CC(trampoline) -> JSR slice -> JSR kernel(line 228) -> JSR resolve_targeted(line 234->50) -> JSR find_clears(line 60->71) -> JSR fc_scan(line 77->131) -> JSR fc_flush(line 143/153->155, leaf). That is exactly 7 JSRs = 14 bytes of return addresses, matching the spec. All other branches are strictly shallower: gravity (line 58/66) is a leaf at depth 5; shape (line 235) is a leaf at depth 4; first_occ runs at slice depth (before the kernel, stack unwound) and is a leaf. CRITICAL POSITIVE: I scanned the entire chain for PHA/PHP/PHX/PHY and found NONE in resolve/resolve_targeted/find_clears/fc_scan/fc_flush/gravity/shape/kernel/first_occ -> the search consumes ONLY return-address bytes, so the 14-byte figure is exact for the sim primitives (consistent with the spec's "bit-packing removed the PHA/PLA": new fc_flush/fc_apply use only A/X/Y + zp _BP1/_BP2, no pushes).

WORST-CASE SP (two models, both safe):
- TIGHT bound from the measured "17 bytes / stays above $01EF": since (mainloop_depth + NMI_full_depth) <= 17 in normal play (NMI nests on main loop) and our slice adds 14 bytes to mainloop_depth before an NMI can fire, worst used = 17 + 14 = 31 bytes -> SP = $01FF-31 = $01E0. Margin to highest live RAM ($019F) = 65 bytes.
- CONSERVATIVE (spec's model, which double-counts mainloop=17 AND a fresh NMI=3+17): 51 bytes -> SP $01CC. Margin to $019F = 45 bytes; margin to top of live data even after the 32-byte guard band ($01BF) = 13 bytes.
Either way margin >> 8. The guard band $01A0-$01BF (32 bytes unused) absorbs deeper-than-modeled descent; live-data ceiling is correctly pinned at $019F and WORK is at the lowest/safest $0100-$017F.

NO NMI COMPOUNDING: A cascade eval is atomic (~114k cyc ~ 4 frames) so 4 NMIs fire during it, but each NMI handler (~2273 cyc) completes and pops before the next vblank -> NMIs never nest on each other; only ONE NMI's frames sit atop the slice at any instant. So stack growth is bounded by the single worst case above. The ONLY route to unbounded compounding is the constraint-3 failure (slice running INSIDE the NMI and overrunning a frame), which the design explicitly forbids by running the slice in the wait_for_vblank main-loop spin and guarding with ST_BUSY. That is a code-discipline hazard, not a numeric-margin one; the numeric margin for the intended (main-loop) design is safe.

RESIDUAL CAVEATS (none fatal via this lens):
1. The whole bound rests on the UNVERIFIED "game uses ~17 bytes, stays above $01EF" probe (spec already flags MUST-MEASURE). To breach live data at $019F the game would need ~96 bytes of mainloop+NMI depth (a ~5x underestimate) -- implausible for a 17-byte baseline, but the probe should specifically capture worst-case audio nesting (level-clear fanfare + multiple SFX channels), when NES sound-engine NMI depth peaks.
2. The $D2CC trampoline's OWN stack use (likely a PHA to save A and/or a nested JSR to restore the prior MMC1 bank on exit) is uncounted -- estimate +2 to +6 bytes. Absorbed by the guard band but should be folded into the count.

**Fix:** No structural fix needed; the buffers at $0100-$019F cannot be clobbered under the modeled or even ~5x-pessimized stack depth. Minor hardening to make the argument airtight:
(a) Count the trampoline conservatively as 2 extra levels (treat the chain as 8 JSR = 16 bytes, plus a 2-byte trampoline PHA = 18 bytes): tight SP becomes $01FF-(17+18)=$01DC, conservative $01CA -- still 61/43-byte margins. Bake this 18-byte figure into the spec instead of 14.
(b) Make the Mesen Lua SP probe (already MUST-MEASURE in risk 3) log min SP under TWO adversarial conditions: a deep cascade-eval slice with an NMI nested mid-eval, AND a level-clear/multi-SFX audio frame -- assert min SP > $01C0 (>=33-byte margin above $019F) and fail the gate if it dips below.
(c) Keep the live-data ceiling hard-pinned at $019F (already done) and add an assembler assert that no search/driver store targets $01A0-$01EE, so the guard band can never be silently consumed by a future addition.
(d) Enforce (not just document) that the slice never runs in the NMI: ST_BUSY guard plus a check that the slice entry is only reachable from the $B660 wait_for_vblank spin -- this is what actually prevents the unbounded-compounding failure that would dwarf any numeric margin.

### Verdict 2: flawed

Three slicing-consistency holes, two fatal, all centered on the assumption that "hold the pill + re-copy $0500 each slice" keeps every slice consistent.

FINDING A (FATAL — mid-search lock mutates $0500): The gate (`output_wiring` edit (b): `LDA ST_MODE($0190); CMP #2; BNE w_hold`, `w_hold:RTS`) only SUPPRESSES P2 INPUT (it stops writing the $F6 Right/Left/Down trigger). It does NOT stop the game's intrinsic gravity, which descends and eventually LOCKS the active pill on its own timer regardless of input. The original design never hit this because `JSR search_entry` was SYNCHRONOUS — the decision existed before the pill moved. The async hold runs ~15 slices/frames (`slicing`: "<=15 frames ~0.25s"). At L11 — the explicit target (memory: l11-target-truth) — gravity is fast; 0.25s is many gravity ticks, so the held pill auto-locks DURING the search. Consequences, all corrupt: (1) the locked pill becomes settled cells in $0500, so slices after the lock copy a DIFFERENT board than slices before it (the per-slice `copy $0500->WORK` in `ram_layout` BOARD MODEL guarantees the argmax is taken over inconsistent boards — placement A scored on board-before-lock vs placement B scored on board-after-lock, comparison is meaningless, keep-first can latch a transient winner); (2) the lock triggers clear+cascade and a NEXT-pill spawn, so $0386 jumps up and the wrapper re-fires arm while ST_MODE is still SEARCHING; (3) publish eventually writes $DD/$DA for a pill that is already locked, and the wrapper drives the now-current (different) pill to a stale target. Constraint 4 ("settled cells stable until lock/cascade") is true — but THIS DESIGN CAUSES the lock mid-search, so the precondition it relies on is the very thing it breaks. Risk 6 hand-waves "if gravity is fast enough... also gate gravity" — at L11 it is not "if," it is the common case, and the spec ships input-gating as the primary mechanism.

FINDING B (FATAL — arm vs slice cross-context race, not covered by ST_BUSY): ST_BUSY ($0199) is documented as guarding only SPIN re-entry ("if ST_BUSY!=0: RTS" at the top of the spin-hook). But `arm` runs in a DIFFERENT context — it is called from the $FF54 wrapper, which executes in the controller-hook/NMI path, while the slice executes in the main-loop spin ($B660). arm rewrites the PERSISTENT shared state: ST_MODE=SEARCHING, SE_COL($0191)=0, SE_ORIENT=0, SE_BCOL($0193)=$FF, SE_BESTLO/HI=0, and Z_TILEA($D9)/Z_TILEB($DB) to the NEW pill's colors. Nothing makes arm check ST_BUSY. So if a new-pill edge ($0386>$DF) fires while a main-loop slice is mid-eval (made reachable by Finding A's premature lock+respawn, or any spurious y-increase), arm stomps SE_COL/SE_BCOL/Z_TILEA mid-flight; the slice resumes its current `kernel`+score using OLD geometry (SE_COL) with NEW tiles (Z_TILEA/B) and writes the result into a just-zeroed SE_BEST — a half-old/half-new corrupt argmax. The spec's "ST_MODE=DONE stored last prevents tearing" argument only protects the PUBLISH direction (wrapper reading torn $DD/$DA); it gives no protection for arm WRITING state into a live slice.

FINDING C (board-stability regime gap — $0500 may include the hovering pill): Risk 6 flags "confirm $0500 EXCLUDES the falling pill" as unverified, but understates how load-bearing it is for slicing. Constraint 4's evidence is "stable during a FALL." The async hold creates a NOVEL regime constraint 4 never covered: a pill HOVERING at the spawn row for ~15 frames. If $0500 includes the active pill (common in NES Dr. Mario playfield arrays), its 2 spawn cells sit in $0500 at the top and (a) corrupt `first_occ` (it returns row 0/1 for center columns, marking vertical placements illegal and landing horizontals on the pill itself), and (b) may be present or absent in a given slice depending on whether the game's per-frame pill re-blit ran before or after that slice's `copy $0500->WORK` — i.e., the top two cells flicker in/out across slices, again making the argmax inconsistent. The per-slice re-copy (chosen in `ram_layout` for render-glitch safety) is itself the consistency hazard: it re-samples a board that can change for ANY reason between frames.

Secondary timing note (reinforces A): even before a lock, the held pill DESCENDS each gravity tick ($0386 decreasing). So the usable "stable settled board" window before lock at L11 is only a few frames, but the search budget is up to 15 slices — the slicer is too slow for the level it targets, so DONE routinely arrives after the pill has already left the top (or locked).

**Fix:** A: Do not rely on input-gating to hold the pill. While ST_MODE!=DONE, actively freeze P2's gravity/lock — zero or reload the game's P2 gravity/drop counter every frame in the wrapper's hold branch (find the P2 fall-timer RAM, sibling to $0385/$0386/$03A5, and pin it), OR arm during the spawn animation and HARD-CAP the search to finish within the guaranteed pre-first-gravity-tick window at L11 (measure that window on Mesen; if <15 frames, cut placements/slice budget or coarsen the eval). Verify on Mesen that a held pill does not lock for at least the worst-case search duration.

B: Make arm ST_BUSY-aware and slice-atomic. If ST_BUSY!=0 when a new-pill edge fires, do NOT mutate state inline — set a one-byte ST_PENDING_ARM flag (e.g. $019A in the reserved block) and have the spin, at a clean placement boundary (pool dead), notice the pending flag and perform the reset there. Equivalently, wrap the slice's non-atomic state region with SEI/CLI so an NMI-context arm cannot interleave. Also have arm refuse to re-arm while ST_MODE==SEARCHING for the SAME pill (compare a per-pill signature, or only honor the edge once ST_MODE has returned to DONE/IDLE).

C: Snapshot ONCE, not per slice. At arm, copy $0500 into a dedicated stable PRISTINE buffer in free RAM (a second 128B block, or reuse WORK and forbid re-copy), and have EVERY slice copy WORK from that frozen snapshot — never re-read live $0500 mid-search. This guarantees all slices see one identical board, making the argmax self-consistent regardless of what the live board does. Before snapshotting, explicitly confirm (Mesen Lua) that $0500 at the arm instant excludes the active pill AND that the prior pill's cascade has fully settled; if the active pill is present in $0500, mask out its two known spawn cells in the snapshot. (Snapshot-once trades the spec's render-glitch safety back in — but render glitch is cosmetic; an inconsistent decision is not. Keep the never-write-$0500 working-copy model for glitch safety on the WORK side; just freeze the SOURCE.)

Re-validation: none of A/B/C changes the py65 golden path (tests drive search synchronously with a static board), so 400/400 still gates the zp/bitpack/working-copy rewrite — but the slicer, gravity-freeze, and arm/ST_BUSY interlock MUST be validated live on Mesen with a Lua probe that (i) logs min SP with an NMI nested in a slice, (ii) confirms the held pill never locks before DONE at L11, and (iii) confirms $0500 is byte-identical across all slices of one search.

