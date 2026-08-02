#!/usr/bin/env bash
# Standalone ALM sizing for one LeafEval variant ON THE POCKET DEVICE.
#
# WHY A SECOND SCRIPT INSTEAD OF A FLAG. size_leafeval.sh sizes on the MiSTer part
# (5CSEBA6U23I7, 41,910 ALMs) with the MiSTer production settings -- HIGH PERFORMANCE
# EFFORT / SPEED. The Pocket is a different part (5CEBA4F23C8, 18,480 ALMs) AND ships a
# different optimisation policy: its vendored nes_pocket.qsf sets AGGRESSIVE AREA +
# OPTIMIZATION_TECHNIQUE AREA, because area is the binding constraint there, not Fmax.
#
# Those two settings do not merely shift the numbers by a constant -- AREA-mode synthesis
# makes different sharing decisions, so a delta measured under SPEED does not predict the
# delta under AREA. Sizing the Pocket question with the MiSTer script would produce a
# confident number for the wrong silicon. Hence: same instrument, Pocket policy.
#
# Still a DELTA instrument, not a fit verdict: LeafEval alone with virtual pins says what
# the chain engine ADDS, and the trial fit of the whole core says whether it lands.
#
#   size_leafeval_pocket.sh <path-to-LeafEval.sv> <tag>
set -euo pipefail
SRC="$1"; TAG="$2"
QROOT=/home/struktured/intelFPGA_lite/23.1std/quartus
QSH="$QROOT/bin/quartus_sh"
WORK=/home/struktured/projects/dr_mario_rl/tmp/rtl_chain/sizing_pocket/$TAG
DPRAM=/home/struktured/projects/pocket-nes-mapper100/rtl/upstream/dpram.vhd

[ -f "$SRC" ]   || { echo "no such LeafEval: $SRC" >&2; exit 65; }
[ -f "$DPRAM" ] || { echo "no Pocket dpram at $DPRAM" >&2; exit 65; }

rm -rf "$WORK"; mkdir -p "$WORK"
cp "$SRC" "$WORK/LeafEval.sv"
cp "$DPRAM" "$WORK/dpram.vhd"
md5sum "$SRC" > "$WORK/INPUT.md5"      # identify the variant by hash, never by tag

cat > "$WORK/sz.qpf" <<'EOF'
PROJECT_REVISION = "sz"
EOF

# Device + optimisation policy mirror projects/nes_pocket.qsf (the vendored Pocket build).
cat > "$WORK/sz.qsf" <<'EOF'
set_global_assignment -name FAMILY "Cyclone V"
set_global_assignment -name DEVICE 5CEBA4F23C8
set_global_assignment -name TOP_LEVEL_ENTITY LeafEval
set_global_assignment -name OPTIMIZATION_MODE "AGGRESSIVE AREA"
set_global_assignment -name OPTIMIZATION_TECHNIQUE AREA
set_global_assignment -name NUM_PARALLEL_PROCESSORS 4
set_global_assignment -name VERILOG_INPUT_VERSION SYSTEMVERILOG_2005
set_global_assignment -name SYSTEMVERILOG_FILE LeafEval.sv
set_global_assignment -name VHDL_FILE dpram.vhd
set_global_assignment -name AUTO_RESOURCE_SHARING ON
set_instance_assignment -name VIRTUAL_PIN ON -to *
set_instance_assignment -name VIRTUAL_PIN OFF -to clk
EOF

cd "$WORK"
"$QSH" --flow compile sz > compile.log 2>&1 || {
  echo "[$TAG] COMPILE FAILED -- tail:"; tail -40 compile.log; exit 1; }

echo "=== $TAG (Pocket 5CEBA4F23C8, AGGRESSIVE AREA) ==="
cat INPUT.md5
command grep -E "Logic utilization|Total registers|Total block memory bits|Total RAM Blocks|Total DSP" \
  sz.fit.summary || true
