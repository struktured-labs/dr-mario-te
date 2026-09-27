# DRCHAIN=540 linknode co-sim

The chain-weight loop lives on this branch in `experiments/bitexact_gate/gate.py`
(it was the fixed set `0, 45, 90`). The same loop is `experiments/hsv/gate/gate.py:653`
on `origin/hsv-leaf`. This run used the gate on this branch.

`a_chw` is the byte firmware stores. `DRCHAIN = a_chw * 4`, so 135 is DRCHAIN 540
(0x87) and 255 is the 8-bit register maximum (DRCHAIN 1020).

Simulator: Verilator 5.020 (Debian 5.020-1), via `gate.py linknode` and
`tb_linknode_gate.cpp`. The testbench is Verilator-specific.

## Shipping RTL — PASS

`fpga/copro/LeafEval.sv` is byte-identical to `NES_MiSTer-drmario` `08f2343`
`rtl/mappers/LeafEval.sv` (git blob `bf9710da4445ba9053e4043949946f3a45253c4c`,
md5 `5f06209642d1547e99cea077523662dc`). That is the Childproof / chain-540 RTL
named in `experiments/cvx/CHAIN540_BUILD.md`.

```
cd experiments/bitexact_gate
python3 gate.py linknode \
  --rtl /workspace/fpga/copro/LeafEval.sv \
  --chain-weights 0,45,90,135,255
```

Exit 0. `GATE PASS` at every weight, including 135 and 255. Mutant selfcheck
killed 9/9.

| a_chw | DRCHAIN | result | placements | imm / chain mismatches |
|---:|---:|---|---:|---:|
| 0 | 0 | PASS | 7282/7282 | 0 / 0 |
| 45 | 180 | PASS | 7282/7282 | 0 / 0 |
| 90 | 360 | PASS | 7282/7282 | 0 / 0 |
| 135 | 540 | PASS | 7282/7282 | 0 / 0 |
| 255 | 1020 | PASS | 7282/7282 | 0 / 0 |

Each of the 7282 records is one placement (parent board, orientation, column,
cap-1 or fixpoint). 7089 were legal and were compared on cells, viruses, chain
depth, immediate score, leaf score, win, colour plane, and link plane. The other
193 were illegal and were compared on legality. Chain depth in the corpus is
0×3000, 1×4149, 2×130, 3×3. The bonus is live only when chain > 1, and that
happened on 133 placements, so the non-zero doses were not vacuous. A plain
clear (chain == 1) kept the dose-0 immediate score.

No mismatch on this RTL. There is no failing case to replay.

## Overflow and the chain-15 stop

The corpus never builds a chain deeper than 3, so the co-sim does not execute
the chain-15 stop. The RTL behavior, checked against the widths in
`LeafEval.sv`, is:

- `chain` is 4 bits and stops at 15 (`if (chain != 4'd15)`). It does not wrap.
- Each round after the first adds `{6'd0, a_chw, 2'b00}` into `chain_bonus`,
  which is `a_chw * 4`. At the stop that is 14 additions.
- `chain_bonus` is an unsigned 16-bit add. It wraps if the sum exceeds 65535.
  It does not saturate on its own. The chain counter stopping is what caps it.
- `imm` is unsigned 16-bit: `180 * rv_vir + 10 * rv_cells + chain_bonus`.

At the chain-15 stop the bonus is `14 * a_chw * 4`:

| a_chw | DRCHAIN | bonus at chain 15 | worst imm (rv_vir=63, rv_cells=127, plus that bonus) |
|---:|---:|---:|---:|
| 135 | 540 | 7560 | 20170 |
| 255 | 1020 | 14280 | 26890 |

Both fit in 16 bits (65535). 7560 is the figure in the chain-540 build record.
`rv_vir` is 6 bits and `rv_cells` is 7 bits, so 63 and 127 are the largest
values those counters can hold before they themselves wrap. Even that corner,
plus a saturated chain at weight 255, stays under 65536 (26890).

On the corpus the deepest immediate score the testbench asked the RTL to match
was 1750 at weight 135 and 2710 at weight 255. The passing comparison is
full-width on the reference side and 16-bit on the RTL side, so a wrap would
have been a mismatch. None occurred. Weight 255 is inside the same 16-bit range
as 135; it does not stress a saturating adder, because the design does not have
one for this term.

## HSV / reach / tap RTL

REACH and TAP are firmware (`DRREACH`, `DRREACHTAP` on the chain-540 ROM). They
are not a second `LeafEval`. The RTL variant is `NES_MiSTer-drmario`
`claude/hsv-leaf`. Two snapshots were fetched and gated. `dpram.v` was the copy
next to `fpga/copro/LeafEval.sv`.

Build-record snapshot `cce212a` (`LeafEval.sv` md5 `05a5db35000254a7e5b8935bc8eb5eef`):

```
python3 gate.py linknode --rtl /tmp/rtl-hsv-cce/LeafEval.sv --chain-weights 0,135,255
python3 gate.py linknode --rtl /tmp/rtl-hsv-cce/LeafEval.sv --define DRHSV --chain-weights 135
python3 gate.py linknode --rtl /tmp/rtl-hsv-cce/LeafEval.sv --define DRHSV --chain-weights 255
```

Branch tip `391afb8` (md5 `25f6b499efef446717b44bc82a96348e`), which adds further
`DRLEV_*` timing ifdefs on top of `cce212a`:

```
python3 gate.py linknode --rtl /tmp/rtl-hsv/LeafEval.sv --chain-weights 0,45,90,135,255
python3 gate.py linknode --rtl /tmp/rtl-hsv/LeafEval.sv --define DRHSV --chain-weights 135
python3 gate.py linknode --rtl /tmp/rtl-hsv/LeafEval.sv --define DRHSV --chain-weights 255
```

With `DRHSV` left undefined, both files PASS 7282/7282 at every weight above,
including 135 and 255, with 0 immediate-score and 0 chain mismatches, and 9/9
mutants killed. The default compile of those files matches the shipping chain path.

With `-DDRHSV`, the gate FAILs, and the failure is only the leaf score. Same
counts on both snapshots, at both 135 and 255:

- 5421/7282 records match
- 1861 leaf-score (`sco`) mismatches
- 0 mismatches on legal, cells, viruses, chain depth, immediate score, win,
  colour plane, or link plane
- the 133 chain>1 placements are still in the run

Minimal repro (testbench line, `cce212a` and the branch tip agree). Placement
case 20, fixpoint, orientation 2, column 2, chain 2, 8 cells, 2 viruses:

- DRCHAIN 540 (`a_chw` 135): immediate score 980/980, leaf score 4370 vs corpus 4882
- DRCHAIN 1020 (`a_chw` 255): immediate score 1460/1460, leaf score 4370 vs corpus 4882

The immediate-score step from 980 to 1460 is `(255 - 135) * 4 * (2 - 1) = 480`.
The chain bonus scaled and did not wrap. The leaf score moved by the same amount
at both weights, which is the HSV term (−512 per high spawn-column virus, folded
into `matched60`), not the chain adder. The pinned corpus was built with the
winner leaf, so those 1861 score deltas are the HSV leaf doing what it was built
to do. They are not a chain-weight defect.
