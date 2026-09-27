#!/usr/bin/env bash
# CHAIN540 + DRREACH + DRREACHTAP firmware (77ec742c) + DRHSV RTL (LeafEval `ifdef DRHSV, fork claude/hsv-leaf cce212a); Childproof qsf.used + VERILOG_MACRO DRHSV=1; seed 13
# (reach-wt branch reach-root). Control hex for the FW-in-image proof = the REACH fw d8014d77.
# Uses Childproof's archived NES.qsf.used verbatim; restores the shared fork (HEAD, NES.qsf, copro_rom.hex) on exit.
set -uo pipefail
FORK=/home/struktured/projects/NES_MiSTer-winner
SHIP=/home/struktured/projects/dr-mario-main-wt/experiments/rtl_chain/ship_build.sh
W=/home/struktured/projects/dr-mario-h16-wt/tmp/chain540_reach_tap_hsv
FW=$W/fw540_reachtap.hex; WANT_FW=77ec742cf0446b49a7f363b34c522864; CTRL=$W/fw540_reach_ctrl.hex
CP_QSF=$W/NES.qsf.drhsv
RTL=cce212acc94044c88a8ce9886bb6721ff793edb7; TAG=childproof-chain540-reach-tap-hsv
OUT=/home/struktured/projects/dr_mario_rl/tmp/rtl_chain/ship/$TAG-seed13
QB=/home/struktured/intelFPGA_lite/23.1std/quartus/bin
PROOF=/home/struktured/projects/dr_mario_rl/tmp/rtl_chain/ship/theta400-seed13/fw_bijection_proof.py
PY=/home/struktured/projects/dr_mario_rl/tmp/venv/bin/python
cd "$FORK" || exit 64
ORIG=$(git rev-parse HEAD)
[ "$(git rev-parse --short HEAD)" = "18cf064" ] || { echo "ABORT: fork HEAD $(git rev-parse --short HEAD) != 18cf064"; exit 64; }
[ "$(md5sum copro_rom.hex | cut -d' ' -f1)" = "f78f1e9376405dc996404f68dfa9dfb8" ] || { echo "ABORT: fork hex not baseline"; exit 64; }
[ -z "$(git status --porcelain -- rtl/)" ] || { echo "ABORT: fork rtl/ dirty"; exit 64; }
[ "$(md5sum "$FW" | cut -d' ' -f1)" = "$WANT_FW" ] || { echo "ABORT: fw540_reachtap md5"; exit 64; }
cp NES.qsf "$W/fork_NES.qsf.bak"; cp copro_rom.hex "$W/fork_copro_rom.hex.bak"
restore() {
  cd "$FORK"
  cp "$W/fork_copro_rom.hex.bak" copro_rom.hex
  git checkout -q --detach "$ORIG"
  cp "$W/fork_NES.qsf.bak" NES.qsf
  echo "RESTORED fork: HEAD $(git rev-parse --short HEAD) hex $(md5sum copro_rom.hex | cut -c1-8) qsf $(md5sum NES.qsf | cut -c1-8) (bak $(md5sum "$W/fork_NES.qsf.bak" | cut -c1-8)) rtl-clean=$([ -z "$(git status --porcelain -- rtl/)" ] && echo yes || echo NO)"
}
trap restore EXIT INT TERM
git checkout -q --detach "$RTL" || { echo "ABORT: checkout $RTL"; exit 65; }
cp "$CP_QSF" NES.qsf
cp "$FW" copro_rom.hex
echo "PRE: RTL $(git rev-parse --short HEAD) fw $(md5sum copro_rom.hex | cut -c1-8) qsf=Childproof's NES.qsf.used; compiling seed 13 $TAG  $(date -Is)"
nice -n 19 "$SHIP" 13 "$TAG"; rc=$?
echo "SHIP rc=$rc  $(date -Is)"
# firmware-in-image proof from the compiled db (fresh netlist; stale simnet removed first)
rm -rf output_files/simnet
"$QB/quartus_eda" --simulation=on --tool=modelsim --format=verilog --output_directory=output_files/simnet NES > "$OUT/eda.log" 2>&1; erc=$?
VO=$(ls output_files/simnet/*.vo 2>/dev/null | head -1)
echo "EDA rc=$erc netlist=$VO"
if [ "$erc" = 0 ] && [ -n "$VO" ]; then
  "$PY" "$PROOF" "$VO" "$FW" "$CTRL" > "$OUT/FW_IN_IMAGE_PROOF.txt" 2>&1; echo "PROOF rc=$?"; tail -6 "$OUT/FW_IN_IMAGE_PROOF.txt"
else
  echo "PROOF SKIPPED (eda failed)"
fi
# DRHSV-in-netlist check: the 15-bit HSV accumulator (bit 14) exists only with DRHSV defined (13-bit otherwise)
VO=$(ls /home/struktured/projects/NES_MiSTer-winner/output_files/simnet/*.vo 2>/dev/null | head -1)
echo "HSV netlist check: matched60[14] refs=$(command grep -a -c 'matched60\[14\]' "$VO" 2>/dev/null) matched60_p[14] refs=$(command grep -a -c 'matched60_p\[14\]' "$VO" 2>/dev/null) base_matched[14] refs=$(command grep -a -c 'base_matched\[14\]' "$VO" 2>/dev/null)" | tee "$OUT/HSV_NETLIST_CHECK.txt"
exit $rc
