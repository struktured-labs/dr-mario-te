# DRDANGER -- throat-danger root penalty in the copro search (firmware flag)

Source: grok/tapout-study (PR #45) `RESULT_TAPOUT.md` + `tapout/FIRMWARE_SKETCH_DANGER.md`; guards confirmed D4
(2ac27a43), D1 the fallback. This branch implements both arms in the 6502 search emitter, **off by default**.

## What it does
Per root candidate (ply-1 move) that runs `eh_terms` (every non-WIN root): `CUR` ($0700) holds the root's soft b1
(placed + targeted cap-1 clear + one compact gravity -- the sim's `_soft_b1`). The scan finds Hs = max column height of
cols 2..5, n = max(0, Hs - h0), stores n in `D_DNG` ($0287). At `o_cand`, right after DRVETO and before the DRROOTORD
pre-pass store and the jitter: `val1 -= LUT[n]`, 16-bit signed, saturating at -32767 (DRVETO's form).

| arm | LUT | flag |
|---|---|---|
| D4 (default) | 40 * n^2, h0 10 (n 0..6) | `DRDANGER=1` (`DRDANGER_ARM=D4`) |
| D1 | 60 * n, h0 11 (n 0..5) | `DRDANGER=1 DRDANGER_ARM=D1` |

WIN roots skip `eh_terms` and pay nothing (D_DNG is cleared per root before the replay). The sim penalises them too;
WIN = 30000 dwarfs the LUT max (1440), so the decision cannot differ -- confirmed on 40 WIN boards (below).
`D_DNG` is abs $0287 (zp $B6 from the sketch is used by reach_6502); the RO block is $0200-$0286.

## Byte cost / identity
| build (`build_fw.py 540 OUT 1 1 1 1 1 1 19 8 1 VK`) | md5 | search |
|---|---|---|
| VK16, DRDANGER unset / =0 / =0 + ARM=D1 | **b545d740** (= shipped A16) | 3125 B |
| VK4, DRDANGER=0 | **c51d2e21** (= shipped V11) | 3125 B |
| VK16, DRDANGER=1 D4 | 70dad713 | 3207 B (+82) |
| VK16, DRDANGER=1 D1 | cdb1b119 | 3205 B (+80) |

## Gates (all logs in `logs/`)
Reference = the STEER14/tapout **sim's own** rule: per-root n from the sim's `_soft_b1` + cols 2..5 height (the
exact code `tapout_run._danger_pen` uses; golden o4 -> sim variant via cosim `VAR_OF_O4`), fed into the verbatim
golden whole-search mirror (`gate_drveto.decide_mirror` + the DANGER line after DRVETO, before the jitter).
Corpus: 60 real gate-(b) game boards (L11/L15) + 150 synthetic tall-throat boards (cols 2..5 at 3..14) + 40 WIN boards.

| # | gate | result |
|---|---|---|
| 1 | byte identity, flag off (unset, =0, =0+ARM=D1; VK16 and VK4) | **PASS** b545d740 / c51d2e21 |
| 2 | mirror == sim: firmware per-root n (py65, every D_DNG write keyed by zp D_C1/D_O1) == sim n | **PASS** D4 3541/3541 live roots, D1 2822/2822, WIN set 687/687 (D4) 644/644 (D1); 0 wrong |
| 3a | py65 whole search, firmware decision == mirror(+sim DANGER), flag OFF control | **PASS** 250/250 (incl. WIN); **0 writes to $0287** by the shipped firmware |
| 3a | same, D4 | **PASS** 210/210; the term moved 13 decisions (non-vacuous); WIN set 40/40 (WIN chosen, moved 0 -- as designed) |
| 3a | same, D1 | **PASS** 210/210; moved 8; WIN set 40/40 |
| 3b | RTL (Verilator, NES_MiSTer-dist 3b164c7 + shipped defines, DELTA path) bus observer `vsim_dng`: every copro write to $0287 == sim n | **PASS** D4 210 boards 7082/7082; D1 107 boards 2488/2488; 0 wrong n; 0 scan-without-clear; observer passive (final+DONE == plain vsim_pub2 run) 210/210, 107/107; OFF 0 writes |
| 3b | RTL publish co-sim, decision effect (vsim_pub2) | D4 changes the RTL final on 32/210 boards vs OFF, D1 on 6/210 |

Mutants (D4, 60 tall boards; WIN set for no_clear):

| mutant | py65 decision gate | RTL | verdict |
|---|---|---|---|
| after_rootord (penalty after the pre-pass store) | 5/60 wrong | RTL final == D4 on 60/60 | KILLED (py65) |
| no_clear (D_DNG not cleared per root) | 60/60 + WIN 40/40 (decision-equivalent: WIN >> LUT max) | **762/762 scan writes without the per-root clear** | KILLED (RTL bus invariant); decision-equivalent by construction |
| lut_off1 | 2/60 wrong | RTL final != D4 on 8/60 | KILLED |
| inert (apply not emitted) | 5/60 wrong | RTL final != D4 on 16/60 | KILLED |
| row_off1 (scan one row low) | 5/60 boards wrong per-root n | 4 wrong n on the bus (20 boards) | KILLED |

Note: the `logs/py65_*win.txt` files print FAIL only from the non-vacuity rule (moved > 0), which a WIN-only set cannot meet by
design; every check in them passes.

Disclosed: the RTL final is NOT compared 1:1 with py65 (the OFF control agrees on only 114/210, the same as before the
change: py65 runs the search entry only, without the DELTA path / tuck / anytime-deadline the RTL runs and with the
emulator leaf). So the RTL gate is the per-root bus check (exact) + observer passivity, not decision equality.
The py65 harness binds the golden module the emitter was built against (#127 module split; the OFF control proves the
aliased mirror == the firmware) and its image is the py65 (non-DELTA) build; the ship hexes above are the `build_fw.py`
builds the RTL ran.

## Cycle cost
- py65 whole search (no deadline, paired by board, ON - OFF): D4 median **+5,065** copro cycles (p90 +6,494, max
  +6,722) = **+0.09%** (max +0.12%); D1 median +4,845 (max +5,840) = +0.09%. Static: scan <= 6 (D4) / 5 (D1) rows x
  ~30 cycles + apply ~30, per root visit.
- RTL (real copro, anytime deadline): DONE time ON - OFF median +272 NES CPU cycles (max +408 = **0.014 frame**);
  first publish median +136 (max +3,196 D4 / +2,312 D1). OFF DONE median 36.1 f.
- Cart NES-CPU frame budget: unchanged (the penalty runs on the copro's 6502; no cart change).

## Not done here (Carmelo)
No Quartus, no rbf, no hardware, no cart replays (not cheap: the cart path needs the rbf). Steps:
1. `DRDANGER=1 python experiments/reach/build_fw.py 540 fw540_..._drdanger_d4_70dad713.hex 1 1 1 1 1 1 19 8 1 16`
   -> md5 must be 70dad713106f41c44153d519f1d7c9d6 (D1 fallback: `DRDANGER_ARM=D1` -> cdb1b119).
2. Full Quartus compile exactly like `experiments/a16mt/build_rbf.sh` (same fork tree NES_MiSTer-winner at RTL 3b164c7,
   qsf a7a0ce8b, the 5 macros, clean db -- copro_rom.hex is $readmemh'd at synthesis, update_mif is a no-op), with
   fw = the D4 hex and the proof controls swapped: **A16 b545d740 must MISMATCH** (the new must-differ control) and V11
   c51d2e21 must mismatch. Copy build_rbf.sh/stage_rbf.sh with TAG `antibody-dist60-v11-a16-drdanger`.
3. Pass bar (same as A16): fit successful, ALMs fit (A16 was 37,711/41,910), copro slack >= +0.10 ns, pll_hdmi >= -0.062,
   FW-in-image bijection == 70dad713, rbf md5 != A16 rbf e00a764e.
4. Soak on bluemage: the A16 cart (FAIR2PLUS 5a1695da + u8 slam 1ebd386e) unchanged, new rbf; stall/timeout counters
   and DONE latency vs A16, then the couch test vs dr. lulu (kill/tap-out rate is the endpoint: sim D4 kill 3.27% vs
   6.98%).

## Reproduce
```
python experiments/reach/build_fw.py 540 out.hex 1 1 1 1 1 1 19 8 1 16              # flag off -> b545d740
DRDANGER=1 python experiments/reach/build_fw.py 540 d4.hex 1 1 1 1 1 1 19 8 1 16   # 70dad713
DRDANGER=1 DRDANGER_ARM=D1 python experiments/reach/build_fw.py 540 d1.hex 1 1 1 1 1 1 19 8 1 16  # cdb1b119
python experiments/drdanger/gate_drdanger.py --arm OFF|D4|D1 [--mut M] [--win 40] --out X.json   # py65 gate
experiments/drdanger/build_sim_dng.sh && experiments/drdanger/run_dng.sh TAG HEX LINES A B         # RTL observer
python experiments/drdanger/cosim_drdanger.py OUT.jsonl HEX                                        # RTL publish co-sim
python experiments/drdanger/analyze_cosim.py GDIR CDIR; python experiments/drdanger/analyze_dng.py VD CDIR LINES
```
(the gates read the sim from the tapout worktree, env `TAPOUT_CVX`; mutant hexes via `build_mut_hex.py`, test-only.)
