#!/usr/bin/env bash
# ANTIBODY + DRDIST (DIST60) RTL + the V11 firmware (V1 a1ef31c8 = 1488e158 + DRTUCKREACH + DRTUCKLIVE + DRROOTORD, + DRLEFLUSH).
# Copy of experiments/tuckreach/build_rbf.sh (itself h16-wt chain540_reach_tap_hsv_dist_build.sh) with the firmware swapped: same shared fork tree
# (NES_MiSTer-winner, detached at the DIST RTL fork claude/dist-leaf 3b164c7 for the compile, restored on exit), the
# same archived Childproof qsf + DRHSV DRLEV_SQREG DRLEV_WRREG DRLEV_VNPF DRDIST (a7a0ce8b), ship_build.sh (clean db:
# copro_rom.hex is $readmemh'd at SYNTHESIS, so a firmware swap needs a full compile -- update_mif is a no-op).
# FW-in-image proof controls = 1488e158 (the DIST60 firmware) and a1ef31c8 (V1, differs ONLY in the reset stub), which
# must both MISMATCH (V1 only on the high-half slices the 64 stub bytes touch).
#   build_rbf.sh <seed> <fw.hex> <fw-md5>      (run at nice 19; only when load < 10 and >= 30 GB available)
set -uo pipefail
SEED="${1:?seed}"; FW="${2:?fw hex}"; WANT_FW="${3:?fw md5}"; RTL=3b164c7
FORK=/home/struktured/projects/NES_MiSTer-winner
SHIP=/home/struktured/projects/dr-mario-main-wt/experiments/rtl_chain/ship_build.sh
W=/home/struktured/projects/dr_mario_rl/tmp/v11/rbf; mkdir -p "$W"
CTRL=/home/struktured/projects/dr_mario_rl/tmp/rtl_chain/ship/antibody-dist60/fw540_reachtap_dist_1488e158.hex
CTRL2=/home/struktured/projects/dr_mario_rl/tmp/rtl_chain/ship/antibody-dist60-tuckreach/fw540_reachtap_dist_tuckreach_v1_a1ef31c8.hex
CP_QSF=/home/struktured/projects/dr-mario-h16-wt/tmp/chain540_reach_tap_hsv_dist/NES.qsf.drhsv_dist; WANT_QSF=a7a0ce8bcefe679e4967b1e178b1765c
TAG=antibody-dist60-v11
OUT=/home/struktured/projects/dr_mario_rl/tmp/rtl_chain/ship/$TAG-seed$SEED
QB=/home/struktured/intelFPGA_lite/23.1std/quartus/bin
PROOF=/home/struktured/projects/dr_mario_rl/tmp/rtl_chain/ship/theta400-seed13/fw_bijection_proof.py
PY=/home/struktured/projects/dr_mario_rl/tmp/venv/bin/python
pgrep -x quartus_map >/dev/null || pgrep -x quartus_fit >/dev/null || pgrep -x quartus_sh >/dev/null && { echo "ABORT: another Quartus is running"; exit 63; }
cd "$FORK" || exit 64
ORIG=$(git rev-parse HEAD)
[ "$(git rev-parse --short HEAD)" = "18cf064" ] || { echo "ABORT: fork HEAD $(git rev-parse --short HEAD) != 18cf064"; exit 64; }
[ "$(md5sum copro_rom.hex | cut -d' ' -f1)" = "f78f1e9376405dc996404f68dfa9dfb8" ] || { echo "ABORT: fork hex not baseline"; exit 64; }
[ -z "$(git status --porcelain -- rtl/)" ] || { echo "ABORT: fork rtl/ dirty"; exit 64; }
[ "$(md5sum "$FW" | cut -d' ' -f1)" = "$WANT_FW" ] || { echo "ABORT: fw md5"; exit 64; }
FWC="$W/fw540_reachtap_dist_tuckreach_leflush_${WANT_FW:0:8}.hex"; cp "$FW" "$FWC"; FW="$FWC"   # proof output names the md5
[ "$(md5sum "$CTRL" | cut -d' ' -f1)" = 1488e1583ab7ad8b2011d4c136926faf ] || { echo "ABORT: control fw md5"; exit 64; }
[ "$(md5sum "$CTRL2" | cut -d' ' -f1)" = a1ef31c896ce3c8080c2eb9cd5cb182d ] || { echo "ABORT: control2 fw md5"; exit 64; }
[ "$(md5sum "$CP_QSF" | cut -d' ' -f1)" = "$WANT_QSF" ] || { echo "ABORT: qsf md5"; exit 64; }
cp NES.qsf "$W/fork_NES.qsf.bak"; cp copro_rom.hex "$W/fork_copro_rom.hex.bak"
restore() {
  cd "$FORK"
  cp "$W/fork_copro_rom.hex.bak" copro_rom.hex
  git checkout -q --detach "$ORIG"
  cp "$W/fork_NES.qsf.bak" NES.qsf
  echo "RESTORED fork: HEAD $(git rev-parse --short HEAD) hex $(md5sum copro_rom.hex | cut -c1-8) qsf $(md5sum NES.qsf | cut -c1-8) rtl-clean=$([ -z "$(git status --porcelain -- rtl/)" ] && echo yes || echo NO)"
}
trap restore EXIT INT TERM
git checkout -q --detach "$RTL" || { echo "ABORT: checkout $RTL"; exit 65; }
cp "$CP_QSF" NES.qsf
cp "$FW" copro_rom.hex
echo "PRE: RTL $(git rev-parse --short HEAD) fw $(md5sum copro_rom.hex | cut -c1-8) qsf=DIST60 (a7a0ce8b); compiling seed $SEED $TAG  $(date -Is)"
nice -n 19 "$SHIP" "$SEED" "$TAG"; rc=$?
echo "SHIP rc=$rc  $(date -Is)"
rm -rf output_files/simnet
nice -n 19 "$QB/quartus_eda" --simulation=on --tool=modelsim --format=verilog --output_directory=output_files/simnet NES > "$OUT/eda.log" 2>&1; erc=$?
VO=$(ls output_files/simnet/*.vo 2>/dev/null | head -1)
echo "EDA rc=$erc netlist=$VO"
if [ "$erc" = 0 ] && [ -n "$VO" ]; then
  "$PY" "$PROOF" "$VO" "$FW" "$CTRL" "$CTRL2" > "$OUT/FW_IN_IMAGE_PROOF.txt" 2>&1; echo "PROOF rc=$?"; tail -6 "$OUT/FW_IN_IMAGE_PROOF.txt"
else
  echo "PROOF SKIPPED (eda failed)"
fi
echo "netlist check: matched60[14] refs=$(command grep -a -c 'matched60\[14\]' "$VO" 2>/dev/null) vn_hit refs=$(command grep -a -c 'vn_hit' "$VO" 2>/dev/null) h_waddr refs=$(command grep -a -c 'h_waddr' "$VO" 2>/dev/null) dt_pen refs=$(command grep -a -c 'dt_pen' "$VO" 2>/dev/null) dbest refs=$(command grep -a -c 'dbest' "$VO" 2>/dev/null) lev_a_tgt refs=$(command grep -a -c 'lev_a_tgt' "$VO" 2>/dev/null)" | tee "$OUT/NETLIST_CHECK.txt"
exit $rc
