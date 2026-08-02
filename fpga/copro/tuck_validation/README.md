# Tuck pre-silicon validation (Verilator co-sim, 2026-08-01)

Validation of the tuck firmware (`DRCOPRO_TUCK=1`, `751b6ce9`) and the `DRTUCK=1` driver
executor against the REAL RTL, before any of it reaches silicon.

**Verdict: the RTL and the enumerator are correct. Three defects on the consuming side block
any `DRTUCK=1` cart. Latency is a non-issue.** `DRTUCK` defaults OFF and no cart recipe sets
it, so shipped carts are unaffected.

Everything here runs from this directory with no scratch state. The recipe lives next to the
programs on purpose: a proof whose program sits in a scratchpad has an expiry date
(cf. `gate_and_probe.py`).

---

## The three defects

| | defect | evidence |
|---|---|---|
| **D1** | `tuck_scan` publishes a BOARD ROW (0 = top); the executor compares it against `$0386`, which the game stores as **15 − row** | meatfighter `DrMarioAI.java:69` — `y = 15 - readCPU(CURRENT_Y)` |
| **D2** | the driver's invalidation sits at the TOP of `h2_start`, before the pend/delay early-outs, so it runs on every descent frame | real driver bytes in py65: `TUCK_C2` non-`0xFF` for **1 frame of 40** |
| **D3** | the enumerator maximises depth over ALL 8 columns and publishes only (approach, trigger); the executor's final column is `TGT_C2` = the search's `best_col` | those disagree on **140/160 = 87.5%** of real L11 boards |

### ★ Partial fixes are ANTI-fixes

Real driver bytes, L11 physics, `best_col` taken from the RTL's own answer, n = 160 real L11
boards that publish a tuck:

| arm | landed OFF the scored column | landed deeper than no-tuck |
|---|---|---|
| no tuck (today's carts) | 0 / 160 (0.0%) | 0 / 160 |
| as built, D2 fixed | 18 / 160 (11.2%) | 9 / 160 (5.6%) |
| **D2 + D1 (row 15−r), no D3** | **73 / 160 (45.6%)** | 43 / 160 (26.9%) |
| D2 + D1 + best_col-only | **0 / 160 (0.0%)** | 44 / 160 (27.5%) |

Fixing D1 and D2 without D3 makes it **worse**: the un-converted row reads as a near-top
switch so the tuck barely fires, and converting it makes the tuck actually execute — to a
column the search never scored. The last row's 44 is the same 44 boards where a `best_col`
tuck exists, so **44/44 converted, zero mis-lands** — restricted is not safe-because-inert.

Open beyond the three: **26.5%** of published tucks are for a HORIZONTAL capsule (`o4 >= 2`,
two columns wide) and the enumerator is single-cell. And "deepest wins" executes a rest
position the eval never scored — a v2 should eval-gate the tuck against the straight
placement into `best_col`.

## Latency — settled, do not re-measure

Paired co-sim, same boards, same RTL, only the firmware differs (`c87e60a1` vs `751b6ce9`):

* real corpus (195 boards): min 5,472 / median 11,040 / **max 14,688** added clocks = **0.010 frames** @85.9 MHz
* worst case: **48,864** clocks = **0.034 frames** @85.9 MHz, **0.068** at the ÷2 clock, 0.32% of that board's DONE
* search answer unchanged **195/195** — `tuck_scan` does not perturb the search

The worst board (`data/worstboard.txt`) is single blockers at row 1 on alternating columns
with the neighbours empty to the floor — 940 loop bodies. It was **found by hill-climbing the
board space over 400 random restarts** against the exact loop bodies the 6502 executes, not
picked by hand, so it is a searched bound.

## RTL non-regression

Rebuilding the co-sim from the winner RTL with exactly the two `xlate` arms deleted and
running baseline firmware through both gives **22/22 identical** in `best_col`, `best_orient`
AND clock count. The mailbox wiring cannot regress the shipped path.

---

## Reproducing

Requires an interpreter with `py65` (and `numba` for the wider rigs):
`/home/struktured/projects/dr_mario_rl/tmp/venv/bin/python`.

### 1. Build the firmware pair

```sh
cd <canonical>/fpga/copro
python dbg_build.py all 0                    # -> copro_rom.hex  c87e60a1  (shipped baseline)
DRCOPRO_TUCK=1 python dbg_build.py all 0     # -> copro_rom.hex  751b6ce9  (tuck)
```

`dbg_build.py` writes `copro_rom.hex` IN PLACE — copy each result out and restore the
original under a `trap`, or you clobber the canonical base (cf. the base-ROM collision).

### 2. Build the co-sim

`sim_tuck.cpp` streams a board, polls DONE, then reads the descriptor back over the NES bus at
cart `$5087/$5088` — through `xlate()`, not out of copro RAM. `sim_tuck_cap.cpp` is identical
with a 400 M-clock cap for adversarial boards that may not converge.

```sh
verilator --cc --exe --build -j 4 -O2 -Wno-fatal --top-module CoproDrMario \
  --Mdir obj_tuck -o VCoproTuck \
  $R/mappers/CoproDrMario.sv $R/mappers/LeafEval.sv \
  $R/mappers/copro6502.v $R/mappers/copro_alu.v sim_tuck.cpp
# R=/home/struktured/projects/NES_MiSTer-winner/rtl
```

`copro_alu.v` / `copro6502.v` must be named explicitly — rival `ALU.v` / `cpu.v` sit in the
same directory. `dpram.v` is not required.

### 3. Run it

The RTL loads `copro_rom.hex` **relative to the working directory**, so run each arm from a
directory holding the firmware you mean to test:

```sh
mkdir -p run_tuck && cp copro_rom.tuck.hex     run_tuck/copro_rom.hex
mkdir -p run_base && cp copro_rom.baseline.hex run_base/copro_rom.hex
(cd run_tuck && .../VCoproTuck .../data/real_sub.txt > .../results/out_tuck_real.csv)
(cd run_base && .../VCoproTuck .../data/real_sub.txt > .../results/out_base_real.csv)
```

~11–17 s per board; the 195-board corpus takes ~1 h per arm. Both arms are independent — run
them concurrently, detached (`nohup … & disown`), not under a harness task.

### 4. Analyse

```sh
python latency.py real      # paired added-clock stats (also: adv)
python real_ab.py           # the four-arm table; runs the real driver bytes per board
```

---

## Files

| path | what |
|---|---|
| `sim_tuck.cpp`, `sim_tuck_cap.cpp` | Verilator testbench; reads `$5085`–`$5088` + clocks over the NES bus |
| `gen_adv.py` | 22 adversarial boards + the Python reference expectation for each |
| `tuck_lib.py` | shared board primitives and the full enumerator (incl. the target column, which the firmware never publishes) |
| `exec_tuck_sim.py` | runs the driver EXACTLY as emitted — all arms tie, because D2 |
| `exec_tuck_sim_fixed.py` | same, with D2 repaired **in memory** so the executor is observable |
| `real_ab.py` | the four-arm table over the real corpus |
| `latency.py` | paired added-clock statistics |
| `d2_invalidation_fix.patch` | the D2 fix as a unified diff — for reading; the runnable form is the in-memory transform |
| `data/` | board corpora: `real_sub.txt` (195 real L11), `adv.txt` (22 adversarial), `worstboard.txt`, `approach_only_blocked.txt` |
| `results/` | raw co-sim CSVs: tuck / baseline × real / adversarial, plus the no-arms RTL control |

`exec_tuck_sim_fixed.py` patches driver-nav's emitter source in memory rather than keeping a
copy of a 3000-line file here. If the emitter moves past the anchor it **asserts** rather than
silently measuring the unfixed driver.

## The ship gate

`../../../experiments/tuck_regression.py` — 9 enumerator goldens (always hard) plus the
D1/D2/D3 contract, which `xfail`s on v1 and becomes a hard failure under `DRTUCK_V2=1`.
Run that, not this directory, as the v2 gate.
