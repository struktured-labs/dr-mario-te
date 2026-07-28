#!/bin/bash
# RECOVERED 2026-07-28 — the MiSTer copro Verilator co-sim build. This command was in NO
# tracked script (see memory dr-mario-mister-vsim-build); reconstructed from
# obj_mister/VCoproDrMario__verFiles.dat. dpram.v is NOT required (6 modules from 4 sources).
# ★ copro_alu.v / copro6502.v MUST be named explicitly — rival ALU.v / cpu.v live in the same
#   directory and a glob picks the wrong ones.
set -e
R=${R:-/home/struktured/projects/NES_MiSTer-winner/rtl}
TB=${1:-sim_mister.cpp}
OUT=${2:-VCoproDrMario}
verilator --cc --exe --build -j 4 -O2 -Wno-fatal --top-module CoproDrMario \
  --Mdir obj_mister -o "$OUT" \
  "$R/mappers/CoproDrMario.sv" "$R/mappers/LeafEval.sv" \
  "$R/mappers/copro6502.v" "$R/mappers/copro_alu.v" \
  "$TB"
echo "built: obj_mister/$OUT"
