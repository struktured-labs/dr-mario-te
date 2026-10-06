#!/usr/bin/env bash
# Build the CHAINED publish-timeline co-sim (sim_pubchain.cpp) against the shipped copro RTL with Verilator -- the same
# RTL, defines and dpram as tools/lateflip/build_pubtrace.sh on claude/late-flip (ANTIBODY_DIST: NES_MiSTer-dist
# 3b164c7 rtl/mappers, -DDRHSV -DDRLEV_SQREG -DDRLEV_WRREG -DDRLEV_VNPF -DDRDIST). Firmware is read at runtime from
# the CWD's copro_rom.hex.
#   experiments/abortstale/build_pubchain.sh OUT_DIR [RTL_MAPPERS_DIR]
set -euo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
OUT="${1:?out dir}"; RTL="${2:-/home/struktured/projects/NES_MiSTer-dist/rtl/mappers}"
DPRAM=/home/struktured/projects/dr-mario-qa-wt/fpga/copro/dpram.v
mkdir -p "$OUT"; cd "$OUT"
nice -n 19 verilator --cc --exe --build -j 4 -O2 -CFLAGS "-O3 -march=native" -Wno-fatal -DDRHSV -DDRLEV_SQREG -DDRLEV_WRREG -DDRLEV_VNPF -DDRDIST \
  --top-module CoproDrMario --Mdir obj_chain -o vsim_chain "$RTL/CoproDrMario.sv" "$RTL/LeafEval.sv" "$RTL/copro6502.v" \
  "$RTL/copro_alu.v" "$DPRAM" "$HERE/sim_pubchain.cpp" > build_pubchain.log 2>&1
echo "built $OUT/obj_chain/vsim_chain (RTL $RTL @ $(git -C "$RTL" rev-parse --short HEAD 2>/dev/null || echo '?'))"
