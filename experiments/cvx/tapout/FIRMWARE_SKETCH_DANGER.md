# Firmware sketch: DRDANGER (the D4 / D1 throat penalty) in the copro 6502 search firmware

This is a sketch only. Nothing here was built: no firmware hex, no rbf, no Quartus run, no hardware. The references
are to the production firmware emitter on `claude/u8-slam` / `claude/a16-mt2`, `tests/test_search_d3.py`. The
`h16-rollout-gated` branch carries an older copy without DRVETO.

## What the sim does (`tapout_run._danger_pen`)
For each allowed root a:
- Hs is the max height of columns 2..5 on the root's soft b1.
- n = max(0, Hs − h0); D4 squares it.
- The root value drops by P·n, after DRVETO, with DRVETO's 16-bit saturation.

The penalty is seen by the anytime publish timeline as well as by the final answer.

## Where it hooks in
1. **Height scan at the root-replay site, right after `a.jsr("eh_terms")`** (test_search_d3.py ~l.756, `if EH_PLY1:`).
   - `eh_terms` re-derives this root's soft b1 into CUR = $0700, which is exactly the board the sim's `_soft_b1`
     builds.
   - Store the LUT index n in a free zero-page byte. `$B6` is suggested; `$B4-$C9` is documented as unclaimed and
     DRVETO uses `$B4`/`$B5`. Re-check the claim map before using it.
   - Clear it to 0 at the top of the root loop, so a root that skips `eh_terms` gets no penalty.
2. **Penalty at `o_cand`, immediately after the DRVETO penalty block** (~l.887-898) and BEFORE the `if DRROOTORD:`
   pre-pass store.
   - The pre-pass d2 (pass B) and the deep pass (C) therefore both see the penalised val1.
   - The anytime mailbox (`S_BEST_C/O`) then publishes penalised running bests. That is the timeline the sim's
     penalised META assumes, and `meta_pen_mismatch` was 0 in every arm.
3. **Build flag** `DRDANGER` (env, default 0 = emits nothing = byte-identical firmware), with D4 = (P 40, h0 10,
   quadratic) and D1 = (P 60, h0 11, linear) baked into the LUT.
   - It would be plumbed like `DRVETO` in `build_copro_d3.py` (`D3.DRVETO = int(os.environ.get(...))`).
   - It needs a Python mirror (`danger_val`, like `veto_val`) for the gates.

## 6502 (D4; D1 differs only in the LUT and the first-row constant)
Only rows 0..5 can give n > 0, since Hs > 10 means an occupied cell in rows 0-5 of cols 2-5. Empty cells are $FF,
so the AND of 4 cells is $FF iff all four are empty.
```
; --- root-replay, after JSR eh_terms ------------------------------------  bytes  cycles (worst)
        LDX #2            ; CUR index of (row 0, col 2)                         2      2
        LDY #6            ; n if the first occupied row is row 0 (16-0-10)      2      2
dg_l:   LDA CUR,X         ; cols 2..5 of this row                              3      4
        AND CUR+1,X                                                            3      4
        AND CUR+2,X                                                            3      4
        AND CUR+3,X                                                            3      4
        CMP #$FF                                                               2      2
        BNE dg_hit                                                             2      2
        TXA / CLC / ADC #8 / TAX   ; next row                                  5      8
        DEY                                                                    1      2
        BNE dg_l          ; 6 rows                                             2      3
dg_hit: STY D_DNG         ; n (0 = no penalty)                                 2      3
; --- o_cand, after the DRVETO block ---------------------------------------
        LDY D_DNG                                                              2      3
        BEQ dg_np                                                              2      2
        SEC                                                                    1      2
        LDA D_V1L / SBC LUTL,Y / STA D_V1L                                     7     10
        LDA D_V1H / SBC LUTH,Y                                                 5      7
        BVC dg_st                                                              2      3
        LDA #$01 / STA D_V1L / LDA #$80   ; saturate at -32767 (as DRVETO)     6      7
dg_st:  STA D_V1H                                                              2      3
dg_np:
; root-loop entry: LDA #0 / STA D_DNG                                          4      5
; LUTL/LUTH, n = 0..6: P*n^2 = 0, 40, 160, 360, 640, 1000, 1440                14      -
```
- **Size:** about 30 B (scan) + 29 B (apply) + 4 B (clear) + 14 B (LUT) = **about 77 bytes of ROM, 1 zp byte**.
  - D1 is the same size: LUT P·n = 0, 60, ..., 300 for h0 11 (n = 0..5), with `LDY #5`.
  - That is about 0.1 KB, smaller than STEER10's ereach estimate (0.2-0.5 KB). It sits inside the existing search
    loop, so no new module is needed.
- **Copro cycles:** the scan worst case (no occupied cell, 6 rows) is about 6 × 33 + 7 ≈ 205 cycles; the apply is
  ≤ 40 and the clear 5.
  - That gives about 250 cycles per root visit, × 32 roots × 2 passes (DRROOTORD B + C) ≈ **16k cycles per decision**.
  - At 85.9 MHz (MiSTer) that is 0.19 ms (**≈ 0.011 f**); at 54.7 MHz (Pocket), 0.29 ms (≈ 0.018 f).
  - The search itself is about 26 f (≈ 26k leaves × 1,849 clk), so this adds < 0.1 % to search time.
  - The STEER7 slope of 1.1-2.7 pp tap-out per frame puts that cost at < 0.05 pp, which is noise. Part of it overlaps
    the LeafEval ply-2 commands, as the eh terms do.
- **Cart NMI budget (28,001 / 29,780 worst frame): unchanged, + 0 cycles.**
  - That census is the NES CPU's NMI frame in the cart.
  - DRDANGER runs on the copro's own 6502 inside the FPGA core and changes only which answer the copro publishes. The
    cart, its mailbox protocol and its driver are untouched, so no cart rebuild is needed for the penalty itself.
  - If the change ships with u8, that is the existing u8 cart (1ebd386e, NMI census unchanged).
- **RTL: none.** LeafEval, the DIST FSM and the mailbox are unchanged.

## Gates before any hardware (the existing DRVETO pattern)
1. Byte identity: DRDANGER=0 rebuilds today's hex exactly.
2. Python mirror ≡ sim: `danger_val` against `tapout_run._danger_pen` on the stage-0 trace boards (all 32 roots).
3. Verilator co-sim of the copro (`fpga/copro` sim) vs the sim's choices on fixed boards. That covers the final and
   the anytime publishes, plus the killed mutants:
   - penalty after the ROOTORD store, so pass B misses it;
   - no clear on roots that skip eh_terms;
   - LUT off by one.
4. Cycle measurement in co-sim (copro busy frames ± a DRDANGER delta).
5. Owner-gated: a full Quartus fit (a firmware change is not an update_mif no-op), a bluemage soak, then a couch test.
