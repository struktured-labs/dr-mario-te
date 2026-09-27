#!/bin/bash
# G3 tempo sim build -- same recovered REBUILD_VSIM invocation as g1_cosim/build_g1.sh
set -e
HERE="$(cd "$(dirname "$0")" && pwd)"
R="$HERE/../../../fpga/copro"
cd "$HERE"
verilator --cc --exe --build -j 4 -O2 -Wno-fatal --top-module CoproDrMario \
  --public-flat-rw -y "$R" --Mdir obj_g3 -o sim_g3_tempo \
  "$R/CoproDrMario.sv" "$R/LeafEval.sv" \
  "$R/copro6502.v" "$R/copro_alu.v" \
  "$HERE/sim_g3_tempo.cpp"
echo "built: $HERE/obj_g3/sim_g3_tempo"
