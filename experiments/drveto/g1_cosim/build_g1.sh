#!/bin/bash
# Build the G1 co-sim testbench against THIS worktree's RTL (byte-identical to the
# NES_MiSTer-winner fork's mappers -- verified by md5 in the G1 report).  Based on
# fpga/copro/REBUILD_VSIM.sh (the recovered canonical invocation) plus
# --public-flat-rw for the internal-signal observer.  copro_alu.v / copro6502.v
# named explicitly (rival ALU.v / cpu.v live in the same directory).
set -e
HERE="$(cd "$(dirname "$0")" && pwd)"
R="$HERE/../../../fpga/copro"
cd "$HERE"
verilator --cc --exe --build -j 4 -O2 -Wno-fatal --top-module CoproDrMario \
  --public-flat-rw -y "$R" --Mdir obj_g1 -o sim_g1_veto \
  "$R/CoproDrMario.sv" "$R/LeafEval.sv" \
  "$R/copro6502.v" "$R/copro_alu.v" \
  "$HERE/sim_g1_veto.cpp"
echo "built: $HERE/obj_g1/sim_g1_veto"
