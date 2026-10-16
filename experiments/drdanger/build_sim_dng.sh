#!/usr/bin/env bash
# Build the DRDANGER bus-observer co-sim against the shipped A16 RTL (NES_MiSTer-dist 3b164c7 mappers, the shipped
# defines -- the same invocation as tools/lateflip/build_pubtrace.sh) + --public-flat-rw. Output: tmp/drdanger/obj_dng/vsim_dng
set -euo pipefail
R="$(cd "$(dirname "$0")/../.." && pwd)"
RTL="${1:-/home/struktured/projects/NES_MiSTer-dist/rtl/mappers}"
DPRAM=/home/struktured/projects/dr-mario-qa-wt/fpga/copro/dpram.v
OUT="$R/tmp/drdanger"; mkdir -p "$OUT"; cd "$OUT"
nice -n 19 verilator --cc --exe --build -j 4 -O2 -Wno-fatal -DDRHSV -DDRLEV_SQREG -DDRLEV_WRREG -DDRLEV_VNPF -DDRDIST \
  --public-flat-rw --top-module CoproDrMario --Mdir obj_dng -o vsim_dng \
  "$RTL/CoproDrMario.sv" "$RTL/LeafEval.sv" "$RTL/copro6502.v" "$RTL/copro_alu.v" "$DPRAM" \
  "$R/experiments/drdanger/sim_dng.cpp" > build_sim_dng.log 2>&1
echo "built $OUT/obj_dng/vsim_dng (RTL $(git -C "$RTL" rev-parse --short HEAD))"
