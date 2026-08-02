#!/usr/bin/env bash
# Standalone ALM sizing for one LeafEval variant.
#
# Synthesizes LeafEval ALONE (virtual pins, no surrounding NES core) on the production
# device with the production optimization settings, so the ALM number is comparable
# between variants.  This is NOT the fit verdict for the whole core -- it is the DELTA
# instrument: (chain - base) is what gets added to the 36,465/41,910 the full core uses.
#
# Usage: size_leafeval.sh <path-to-LeafEval.sv> <tag>
set -euo pipefail
SRC="$1"; TAG="$2"
QROOT=/home/struktured/intelFPGA_lite/23.1std/quartus
QSH="$QROOT/bin/quartus_sh"
WORK=/home/struktured/projects/dr_mario_rl/tmp/rtl_chain/sizing/$TAG
DPRAM=/home/struktured/projects/NES_MiSTer-winner/rtl/dpram.vhd

rm -rf "$WORK"; mkdir -p "$WORK"
cp "$SRC" "$WORK/LeafEval.sv"
cp "$DPRAM" "$WORK/dpram.vhd"

cat > "$WORK/sz.qpf" <<'EOF'
PROJECT_REVISION = "sz"
EOF

cat > "$WORK/sz.qsf" <<'EOF'
set_global_assignment -name FAMILY "Cyclone V"
set_global_assignment -name DEVICE 5CSEBA6U23I7
set_global_assignment -name TOP_LEVEL_ENTITY LeafEval
set_global_assignment -name OPTIMIZATION_MODE "HIGH PERFORMANCE EFFORT"
set_global_assignment -name OPTIMIZATION_TECHNIQUE SPEED
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

echo "=== $TAG ==="
command grep -E "Logic utilization|Total registers|Total block memory bits|Total RAM Blocks|Total DSP" \
  sz.fit.summary || true
