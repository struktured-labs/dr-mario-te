#!/usr/bin/env bash
# Cell-exact gate: baseline-firmware moves vs all-delta-firmware moves on the same corpus.
#
# Builds mister_vsim from source every run (Verilator --build is incremental: a no-op when nothing
# changed, a correct rebuild when LeafEval.sv/CoproDrMario.sv/etc changed). This fixes three defects
# that cost ~2h on 2026-07-26 (see FIRMWARE.md "Running the gate / long jobs"):
#   1. No committed binary. The old committed obj_mister/mister_vsim was ~50x slower than a fresh build
#      (unoptimised; the recorded verilate command was byte-identical, so the slow flags were not even
#      captured -- a committed binary nobody can attribute is a provenance hazard). obj_mister/ is now
#      gitignored and rebuilt here.
#   2. Re-verilate before gating. The gate used to run a PRE-BUILT binary; editing LeafEval.sv and gating
#      without re-verilating tested the STALE eval constants and passed green on the old eval.
#   3. Line-buffered output that keeps clocks=. The old pipe was block-buffered (0-byte log hid all
#      progress) and sed stripped clocks= (the GO->DONE search-cost counter, the most diagnostic field).
set -e
cd "$(dirname "$0")"
PY=~/projects/dr-mario-mods/.venv/bin/python
N="${1:-12}"

# --- build the co-sim from source. Explicit file list; NEVER glob: ALU.v/cpu.v are the old Arlet core
#     and collide with copro_alu.v/copro6502.v as duplicate module defs. Only sim_mister.cpp links in. ---
echo "== verilate + build mister_vsim (incremental) =="
verilator --cc --build --exe -Wno-fatal --top-module CoproDrMario \
  CoproDrMario.sv LeafEval.sv copro6502.v copro_alu.v dpram.v sim_mister.cpp \
  -o mister_vsim --Mdir obj_mister
VSIM=./obj_mister/mister_vsim
[ -x "$VSIM" ] || { echo "BUILD FAILED: $VSIM missing"; exit 3; }

$PY gen_corpus.py "$N" >/dev/null

# run_one <full-log>: stream full per-case lines (WITH clocks=) live to stdout AND to <full-log>,
# line-buffered so progress is visible as it runs.
run_one() { stdbuf -oL "$VSIM" 2>&1 | stdbuf -oL grep -E "^case" | stdbuf -oL tee "$1"; }

echo "== baseline build + run =="
$PY dbg_build.py baseline 0 >/dev/null 2>&1
run_one /tmp/gate_base_full.txt
echo "== all-delta build + run =="
$PY dbg_build.py all 0 >/dev/null 2>&1
run_one /tmp/gate_all_full.txt

# Cell-exact diff on a move-only projection (oracle + clocks stripped): clocks legitimately differs
# base vs delta and must NOT be in the compared text. The full logs above retain it for diagnosis.
sed -E 's/ oracle.*//' /tmp/gate_base_full.txt > /tmp/gate_base.txt
sed -E 's/ oracle.*//' /tmp/gate_all_full.txt  > /tmp/gate_all.txt
if diff -q /tmp/gate_base.txt /tmp/gate_all.txt >/dev/null; then
  echo "GATE PASS: CELL-EXACT across $N boards (baseline moves == all-delta moves)"
else
  echo "GATE FAIL: divergence"; diff /tmp/gate_base.txt /tmp/gate_all.txt
fi
# restore the SHIPPED hex = the DELTA build (this is what vendors to silicon; see FIRMWARE.md).
$PY dbg_build.py all 0 >/dev/null 2>&1
md5sum copro_rom.hex   # expect c87e60a1736224cfc3fa29cfed7c6f16 (shipped delta)
