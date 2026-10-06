#!/usr/bin/env bash
# Build the publish-timeline co-sim (tools/lateflip/sim_pubtrace.cpp) against a copro RTL tree with Verilator.
#   tools/lateflip/build_pubtrace.sh [RTL_MAPPERS_DIR] [OUT_DIR] [extra verilator -D flags...]
# Defaults: the ANTIBODY_DIST RTL (NES_MiSTer-dist 3b164c7, rtl/mappers) with its shipped defines
# (DRHSV DRLEV_SQREG DRLEV_WRREG DRLEV_VNPF DRDIST), output tmp/pubtrace/obj_pub2/vsim_pub2.
# The firmware is NOT baked in: CoproDrMario.sv $readmemh("copro_rom.hex") at runtime from the process CWD, so one
# binary serves every firmware hex (run it in a directory holding the hex you want).
set -euo pipefail
R="$(cd "$(dirname "$0")/../.." && pwd)"
RTL="${1:-/home/struktured/projects/NES_MiSTer-dist/rtl/mappers}"
OUT="${2:-$R/tmp/pubtrace}"; shift $(( $# > 2 ? 2 : $# )) || true
DEFS=("$@"); [ ${#DEFS[@]} -eq 0 ] && DEFS=(-DDRHSV -DDRLEV_SQREG -DDRLEV_WRREG -DDRLEV_VNPF -DDRDIST)
DPRAM=/home/struktured/projects/dr-mario-qa-wt/fpga/copro/dpram.v
mkdir -p "$OUT"; cd "$OUT"
nice -n 19 verilator --cc --exe --build -j 2 -O2 -Wno-fatal "${DEFS[@]}" --top-module CoproDrMario --Mdir obj_pub2 \
  -o vsim_pub2 "$RTL/CoproDrMario.sv" "$RTL/LeafEval.sv" "$RTL/copro6502.v" "$RTL/copro_alu.v" "$DPRAM" \
  "$R/tools/lateflip/sim_pubtrace.cpp" > build_pubtrace.log 2>&1
echo "built $OUT/obj_pub2/vsim_pub2  (RTL $RTL @ $(git -C "$RTL" rev-parse --short HEAD 2>/dev/null || echo '?'), ${DEFS[*]})"
