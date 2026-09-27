#!/usr/bin/env bash
# FW-in-image proof for the chain540-reach build: re-export the netlist from the compiled db (quartus_eda needs
# --format=verilog with --tool), with the fork in the build's exact state, then restore the fork baseline.
set -uo pipefail
FORK=/home/struktured/projects/NES_MiSTer-winner; W=/home/struktured/projects/dr-mario-h16-wt/tmp/chain540_reach
OUT=/home/struktured/projects/dr_mario_rl/tmp/rtl_chain/ship/childproof-chain540-reach-seed13
QB=/home/struktured/intelFPGA_lite/23.1std/quartus/bin; PY=/home/struktured/projects/dr_mario_rl/tmp/venv/bin/python
PROOF=/home/struktured/projects/dr_mario_rl/tmp/rtl_chain/ship/theta400-seed13/fw_bijection_proof.py
RTL=08f23434cac449db7ee5f641958fcc00c616c29d
cd "$FORK" || exit 64
[ "$(git rev-parse --short HEAD)" = "18cf064" ] || { echo "ABORT: fork HEAD"; exit 64; }
[ "$(md5sum copro_rom.hex | cut -d' ' -f1)" = "f78f1e9376405dc996404f68dfa9dfb8" ] || { echo "ABORT: fork hex"; exit 64; }
ORIG=$(git rev-parse HEAD); cp NES.qsf "$W/eda_NES.qsf.bak"; cp copro_rom.hex "$W/eda_copro_rom.hex.bak"
restore() { cd "$FORK"; cp "$W/eda_copro_rom.hex.bak" copro_rom.hex; git checkout -q --detach "$ORIG"; cp "$W/eda_NES.qsf.bak" NES.qsf
  echo "RESTORED fork: HEAD $(git rev-parse --short HEAD) hex $(md5sum copro_rom.hex | cut -c1-8) qsf $(md5sum NES.qsf | cut -c1-8) rtl-clean=$([ -z "$(git status --porcelain -- rtl/)" ] && echo yes || echo NO)"; }
trap restore EXIT INT TERM
git checkout -q --detach "$RTL"; cp "$OUT/NES.qsf.used" NES.qsf; cp "$W/fw540_reach.hex" copro_rom.hex
rm -rf output_files/simnet
"$QB/quartus_eda" --simulation=on --tool=modelsim --format=verilog --output_directory=output_files/simnet NES > "$OUT/eda.log" 2>&1; erc=$?
VO=$(ls output_files/simnet/*.vo 2>/dev/null | head -1)
echo "EDA rc=$erc netlist=$VO"
[ "$erc" = 0 ] && [ -n "$VO" ] || exit 3
"$PY" "$PROOF" "$VO" "$W/fw540_reach.hex" "$W/fw540_ctrl.hex" > "$OUT/FW_IN_IMAGE_PROOF.txt" 2>&1; echo "PROOF rc=$?"; tail -8 "$OUT/FW_IN_IMAGE_PROOF.txt"
