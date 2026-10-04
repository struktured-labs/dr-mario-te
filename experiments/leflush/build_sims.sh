#!/usr/bin/env bash
# Build the DRLEFLUSH co-sims against a SNAPSHOT of the shipped copro RTL (NES_MiSTer-drmario claude/dist-leaf 3b164c7,
# rtl/mappers, md5-checked) with the DIST60 defines (-DDRHSV -DDRLEV_SQREG -DDRLEV_WRREG -DDRLEV_VNPF -DDRDIST):
#   OUT/obj_chain/vsim_chain    experiments/abortstale/sim_pubchain.cpp (claude/abort-stale), unchanged: chained runs
#   OUT/obj_poison/vsim_poison  sim_poison.cpp + generated poison.inc, --public-flat-rw: poison / register dumps
# Firmware is read at run time from the CWD's copro_rom.hex.
#   experiments/leflush/build_sims.sh OUT_DIR [RTL_MAPPERS_DIR] [PUBCHAIN_CPP]
set -euo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
OUT="${1:?out dir}"
RTL="${2:-/home/struktured/projects/NES_MiSTer-dist/rtl/mappers}"
PUBCHAIN="${3:-/home/struktured/projects/dr-mario-abortstale-wt/experiments/abortstale/sim_pubchain.cpp}"
DPRAM="$HERE/../../fpga/copro/dpram.v"
DEFS="-DDRHSV -DDRLEV_SQREG -DDRLEV_WRREG -DDRLEV_VNPF -DDRDIST"
mkdir -p "$OUT/rtl"
for f in CoproDrMario.sv LeafEval.sv copro6502.v copro_alu.v; do cp "$RTL/$f" "$OUT/rtl/$f"; done
( cd "$OUT/rtl" && md5sum CoproDrMario.sv LeafEval.sv copro6502.v copro_alu.v ) > "$OUT/rtl/MD5SUMS"
# the 3b164c7 RTL these sims are pinned to (any other RTL is refused)
cat > "$OUT/rtl/EXPECT" <<'EOF'
ce7bf30f5c61f0a4b06acbd173ad55d2  CoproDrMario.sv
4fc42ad3a4170206f68f7f86fe1ed219  LeafEval.sv
7500e5aceb16994f24a4c369e0bd0b58  copro6502.v
54b22c5b036cd5702e6556dc149c3c43  copro_alu.v
EOF
diff "$OUT/rtl/EXPECT" "$OUT/rtl/MD5SUMS" || { echo "RTL snapshot is not 3b164c7"; exit 1; }
S="$OUT/rtl"
cd "$OUT"
cp "$PUBCHAIN" sim_pubchain.cpp
nice -n 19 verilator --cc --exe --build -j 4 -O2 -CFLAGS "-O3 -march=native" -Wno-fatal $DEFS \
  --top-module CoproDrMario --Mdir obj_chain -o vsim_chain "$S/CoproDrMario.sv" "$S/LeafEval.sv" "$S/copro6502.v" \
  "$S/copro_alu.v" "$DPRAM" "$OUT/sim_pubchain.cpp" > build_chain.log 2>&1
echo "built $OUT/obj_chain/vsim_chain"
cp "$HERE/sim_poison.cpp" "$OUT/sim_poison.cpp"
nice -n 19 verilator --cc --exe -O2 -CFLAGS "-O3 -march=native" -Wno-fatal --public-flat-rw $DEFS \
  --top-module CoproDrMario --Mdir obj_poison -o vsim_poison "$S/CoproDrMario.sv" "$S/LeafEval.sv" "$S/copro6502.v" \
  "$S/copro_alu.v" "$DPRAM" "$OUT/sim_poison.cpp" > build_poison.log 2>&1
python3 "$HERE/gen_poison.py" "$S/LeafEval.sv" "$S/CoproDrMario.sv" obj_poison/VCoproDrMario___024root.h \
  "$OUT/poison.inc" | tee gen_poison.log
nice -n 19 make -C obj_poison -j 4 -f VCoproDrMario.mk vsim_poison >> build_poison.log 2>&1
echo "built $OUT/obj_poison/vsim_poison"
