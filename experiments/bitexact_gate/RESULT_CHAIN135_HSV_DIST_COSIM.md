# DRCHAIN=540 (a_chw 135) and 255 linknode co-sim on the RTL that shipped: ANTIBODY and ANTIBODY_DIST

Run 2026-10-02, 19:30–19:42 ET, on the shared bot box (not blackmage, not a MiSTer).
Verilator 5.032 (Debian 5.032-1+b2), Python 3 + numpy.

## Verdict

Both shipped LeafEval builds **PASS** the link-aware NODE co-sim at a_chw **0, 45, 90, 135 and 255**
(DRCHAIN 0 / 180 / 360 / 540 / 1020), with the HSV term (and, for DIST, the D term) in the reference.
Zero mismatches on any field at any weight. Mutant selfcheck kills everything, including new term-off
controls that prove the HSV and D terms are live in the RTL.

| build | RTL (md5) | defines | a_chw | result | placements | legal checked | chain>1 | imm / chain / leaf mismatches | mutants |
|---|---|---|---|---|---:|---:|---:|---|---|
| ANTIBODY | `391afb8` (`25f6b499`) | DRHSV DRLEV_SQREG DRLEV_WRREG DRLEV_VNPF | 0 | PASS | 7282/7282 | 7089 | 133 | 0 / 0 / 0 | 10/10 |
| | | | 45 | PASS | 7282/7282 | 7089 | 133 | 0 / 0 / 0 | |
| | | | 90 | PASS | 7282/7282 | 7089 | 133 | 0 / 0 / 0 | |
| | | | **135** | **PASS** | 7282/7282 | 7089 | 133 | 0 / 0 / 0 | |
| | | | 255 | PASS | 7282/7282 | 7089 | 133 | 0 / 0 / 0 | |
| ANTIBODY_DIST | `3b164c7` (`4fc42ad3`) | DRHSV DRLEV_SQREG DRLEV_WRREG DRLEV_VNPF DRDIST | 0 | PASS | 7282/7282 | 7089 | 133 | 0 / 0 / 0 | 11/11 |
| | | | 45 | PASS | 7282/7282 | 7089 | 133 | 0 / 0 / 0 | |
| | | | 90 | PASS | 7282/7282 | 7089 | 133 | 0 / 0 / 0 | |
| | | | **135** | **PASS** | 7282/7282 | 7089 | 133 | 0 / 0 / 0 | |
| | | | 255 | PASS | 7282/7282 | 7089 | 133 | 0 / 0 / 0 | |
| control: DIST RTL, DRDIST **off** | `3b164c7` (`4fc42ad3`) | DRHSV + the 3 fallback defines | 0..255 (all 5) | PASS | 7282/7282 | 7089 | 133 | 0 / 0 / 0 | 10/10 |

Every run also matched cells, viruses, win, colour plane and link plane (all 0 mismatches), and the
link-RAM bypass invariant held (`0 latched by a consumer`).

## What changed in the gates (tooling only)

`experiments/hsv/gate/gate.py` and `experiments/dist/gate/gate.py`, `linknode` level only, mirroring PR #22:

- The chain-weight loop was hardcoded to `0, 45, 90`. Default is now `0, 45, 90, 135`; `--chain-weights`
  takes any comma list of 0..255 (e.g. add 255, the 8-bit register max).
- `--define` now reaches the linknode Verilator build (it was accepted but ignored at this level, so the
  linknode runs recorded for ANTIBODY in `experiments/hsv/GATE_FALLBACK.txt` were **fallback-only, without
  DRHSV**). With `--define DRHSV` the expected leaf score of each legal, non-winning record becomes
  `s16(sco − 512·hsv(child))`; with `--define DRDIST` (dist gate only, requires DRHSV) it also adds
  `−60·D(child, target)` and appends a per-record target (`pick_target` on the parent, the same rule
  `experiments/dist/linknode_dist.py` uses) that the testbench drives into `a_tgt` (`-DHAS_TGT`).
  Immediate score and chain depth are never adjusted — the terms only touch the leaf.
- **Term-off controls** (new selfcheck mutants): the same RTL is run against expected scores with a term
  left out; it must fail on *exactly* the records where that term is non-zero, with 0 imm and 0 chain
  mismatches. That proves the term is live in the RTL and the adjustment is what makes the run pass.
- Pinned corpora fall back to the committed `experiments/bitexact_gate/` copies (these gates' own copies
  are gitignored); `dpram.v` falls back to `fpga/copro/dpram.v`.
- The combo_term numba kernels are now only required by the modes that execute them; `linknode` runs
  without that external tree.
- Per-weight machine lines `LINKNODE_RESULT …` and a term census `LINKNODE_TERMS …`; a JSON record per
  run in `results/linknode_run_<rtl-md5>_<defines>.json`.
- Tests: `tests/test_linknode_gate_weights.py` (weight parsing, label, spec-term adjustment, target
  token, tb summary parser; no Verilator needed).

No RTL, firmware, coefficients, carts or rbf were changed.

## RTL identity (which source was co-simulated)

Fetched from `struktured-labs/NES_MiSTer-drmario` (read-only):

| build | commit | `rtl/mappers/LeafEval.sv` git blob | md5 |
|---|---|---|---|
| ANTIBODY (rbf `6b73907c`) | `claude/hsv-leaf` `391afb8ffeafcd9b532127b879c814eb1f9f7fcd` | `b2d2fe5200ff9aef5ec97728e8c9079804085e7d` | `25f6b499efef446717b44bc82a96348e` |
| ANTIBODY_DIST (rbf `318607aa`) | `claude/dist-leaf` `3b164c7b1c09c61b065359365d5bb687ab8e20d5` | `9fc12c3e13d13145e99a5824ad830646896f4db6` | `4fc42ad3a4170206f68f7f86fe1ed219` |
| (same file) | `claude/dist-target` `14eb0d4a0d3ff9129eee9077b07079ae14650abd` | `9fc12c3e…` (byte-identical to 3b164c7) | `4fc42ad3…` |

The ANTIBODY md5 `25f6b499` is the one `experiments/hsv/GATE_FALLBACK.txt` records for the clean 391afb8 tree,
and the defines are the ones `experiments/cvx/CHAIN540_REACH_TAP_HSV_BUILD.md` §3/§4 lists for the seed-3 fit.
The DIST defines are ANTIBODY's plus `DRDIST` (`experiments/cvx/ANTIBODY_DIST_BUILD.md`; the RTL refuses
DRDIST without DRHSV). That the rbfs were built from exactly these files is taken from those build records
(netlist checks there); this run cannot inspect an rbf. `3b164c7..391afb8` touches only `LeafEval.sv` and
`CoproDrMario.sv`. The DRCHAIN dose is not a define: firmware writes `a_chw` to `$70E6`, which the testbench
drives directly. The firmware (`1488e158`, target to `$70F5`) is outside this NODE co-sim; its target rule
is the gate's `pick_target` mode 1 (proved == firmware in the DIST build record).

Corpus: `experiments/bitexact_gate/linknode_cases.txt`, md5 `efe8e4a4cd0b5b14c514ccf41af93651`, 7282 placement
records (parent board, orientation, column, colours, cap-1 or fixpoint) from real self-play.

## Are the terms and the chain bonus actually exercised?

| | ANTIBODY | ANTIBODY_DIST |
|---|---:|---:|
| legal placements compared field by field | 7089 | 7089 |
| illegal (compared on legality) | 193 | 193 |
| leaf score compared (legal, not a win) | 7070 | 7070 |
| chain depth 0 / 1 / 2 / 3 (legal) | 2807 / 4149 / 130 / 3 | same |
| cascading (chain > 1, the bonus is paid) | 133 | 133 |
| records with HSV ≠ 0 (largest −4608) | 1861 | 1861 |
| records with a valid target | — | 6371 |
| records with D ≠ 0 (largest −960 = D 16 cap) | — | 5001 |
| …of those, firmware-rule targets with D ≠ 0 | — | 714 of 887 |
| expected leaf scores changed by the terms | 1861 | 5582 |
| cascading records that also carry a term | 30 | 93 |
| term-off control | HSV: 1861/1861 → KILLED | D: 5001/5001, HSV+D: 5582/5582 → KILLED |

Largest immediate score the RTL had to match: 1750 at a_chw 135, 2710 at 255. The RTL side is 16-bit, the
reference side full-width, so a wrap would have shown as an imm mismatch; none did.

## 16-bit headroom (chain counter stops at 15, plus HSV and DIST)

From the RTL (391afb8 lines 670/673/787; 3b164c7 lines 793/796/910 — same logic):

- `chain` is 4 bits and stops at 15; each round after the first adds `a_chw·4` into the unsigned 16-bit
  `chain_bonus`: at most 14 additions. `imm = 180·rv_vir + 10·rv_cells + chain_bonus` (unsigned 16-bit).
- HSV and D do **not** touch `imm`. They ride the leaf's signed 15-bit `matched60` path, which `sco`
  sign-extends into its (by-design) signed-16 combine. The RTL never adds `imm` and `sco` together.

| a_chw | DRCHAIN | chain bonus at the stop | worst imm (rv_vir 63, rv_cells 127) | fits u16 (65535)? |
|---:|---:|---:|---:|---|
| 135 | 540 | 7560 | 20170 | yes |
| 255 | 1020 | 14280 | 26890 | yes |

Leaf path: HSV worst −512·27 = −13,824, D worst −960, together −14,784; matched cover worst +2,304. Range
−14,784..+2,304 sits inside signed 15-bit (−16,384..+16,383) at any chain weight, because the chain bonus is
not on this path. On the corpus the adjusted leaf scores spanned −362..5824 (DIST) and 598..6118 (ANTIBODY).

Not covered here (firmware, not RTL): `fpga/copro/tuck_v3.py` adds `imm` to the child value in 16 bits and
the search compares from a `$8000` floor, i.e. signed. One ply of the theoretical worst-case imm plus the
largest real leaf noted in `experiments/hsv/README.md` (+7,234) is 27,404 at 135 (fits under +32,767) but
34,124 at 255 (would wrap). That corner needs chain 15 with 63 viruses and 127 cells cleared at once, far
beyond anything observed (corpus max chain 3, imm 2710), and 255 is not a shipped dose.

## Commands

```
# RTL (read-only fetch)
git clone --filter=blob:none --no-checkout https://github.com/struktured-labs/NES_MiSTer-drmario /tmp/nesdrm
cd /tmp/nesdrm && git fetch origin claude/hsv-leaf claude/dist-leaf claude/dist-target
mkdir -p /tmp/rtl/ab /tmp/rtl/dist
git show 391afb8:rtl/mappers/LeafEval.sv > /tmp/rtl/ab/LeafEval.sv
git show 3b164c7:rtl/mappers/LeafEval.sv > /tmp/rtl/dist/LeafEval.sv

FB="--define DRLEV_SQREG --define DRLEV_WRREG --define DRLEV_VNPF"

# ANTIBODY (HSV gate)
cd experiments/hsv/gate
python3 gate.py linknode --rtl /tmp/rtl/ab/LeafEval.sv --define DRHSV $FB --chain-weights 0,45,90,135,255

# ANTIBODY_DIST (DIST gate)
cd experiments/dist/gate
python3 gate.py linknode --rtl /tmp/rtl/dist/LeafEval.sv --define DRHSV $FB --define DRDIST --chain-weights 0,45,90,135,255

# control: DIST RTL with DRDIST off == ANTIBODY behaviour
cd experiments/hsv/gate
python3 gate.py linknode --rtl /tmp/rtl/dist/LeafEval.sv --define DRHSV $FB --chain-weights 0,45,90,135,255

# tests
python3 -m pytest -q tests/test_linknode_gate_weights.py
```

Each gate run took 2–3 minutes. Verdict lines: `GATE PASS linknode: LeafEval.sv (md5 25f6b499) == reference on
7282 cases at a_chw 0,45,90,135,255 with DRHSV DRLEV_SQREG DRLEV_WRREG DRLEV_VNPF, 10/10 mutants killed` and
`… (md5 4fc42ad3) … with DRHSV DRLEV_SQREG DRLEV_WRREG DRLEV_VNPF DRDIST, 11/11 mutants killed`.

## Limits

- The linknode corpus never builds a chain deeper than 3, so the chain-15 stop is argued from the RTL above,
  not executed.
- This is the LeafEval NODE path (CMD 4), the one that resolves clears and cascades. The `gate.py rtl`
  LEAF / NODE / DELTA phases (CMD 1/4/6/7, compact-gravity oracle) were not re-run at other doses here.
- No hardware or rbf was examined; build-to-source identity is from the build records.
