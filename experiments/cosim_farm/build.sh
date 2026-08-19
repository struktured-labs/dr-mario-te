#!/usr/bin/env bash
# Verilate BOTH co-sim binaries from the SAME RTL sources:
#   farm_vsim   -- this lane's persistent stdin/stdout decision server (sim_farm.cpp)
#   mister_vsim -- the project's STOCK one-shot binary (fpga/copro/sim_mister.cpp),
#                  rebuilt here from source so the agreement gate compares against a
#                  binary of known provenance rather than a committed artifact nobody
#                  can attribute (the exact defect run_gate.sh's header documents).
#
# Explicit file list, NEVER a glob: ALU.v/cpu.v are the old Arlet core and collide with
# copro_alu.v/copro6502.v as duplicate module definitions.
#
# -CFLAGS -O2 raises only the C++ compiler's optimisation level (Verilator's default is
# -Os). It cannot change simulation semantics -- and the agreement gate proves it did not,
# since farm_vsim is built WITH it and mister_vsim WITHOUT it, and they must still agree
# bit-for-bit. Verilator flags that DO change semantics (--x-assign/--x-initial) are
# deliberately not used.
set -e
cd "$(dirname "$0")"
HERE="$(pwd)"
COPRO="$(cd ../../fpga/copro && pwd)"
BUILD="${COSIM_FARM_BUILD:-$HERE/build}"
mkdir -p "$BUILD"

SRCS="$COPRO/CoproDrMario.sv $COPRO/LeafEval.sv $COPRO/copro6502.v $COPRO/copro_alu.v $COPRO/dpram.v"

echo "== verilate farm_vsim (persistent server) =="
verilator --cc --build --exe -Wno-fatal --top-module CoproDrMario \
  $SRCS "$HERE/sim_farm.cpp" \
  -CFLAGS -O2 \
  -o farm_vsim --Mdir "$BUILD/obj_farm"

echo "== verilate mister_vsim (stock one-shot, agreement reference) =="
verilator --cc --build --exe -Wno-fatal --top-module CoproDrMario \
  $SRCS "$COPRO/sim_mister.cpp" \
  -o mister_vsim --Mdir "$BUILD/obj_mister"

for b in "$BUILD/obj_farm/farm_vsim" "$BUILD/obj_mister/mister_vsim"; do
  [ -x "$b" ] || { echo "BUILD FAILED: $b missing"; exit 3; }
  echo "built $b  md5=$(md5sum "$b" | cut -d' ' -f1)"
done
