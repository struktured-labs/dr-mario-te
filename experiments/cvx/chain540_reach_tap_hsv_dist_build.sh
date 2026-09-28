#!/usr/bin/env bash
# ANTIBODY + DRDIST (STEER6b dist_target60): firmware 1488e158 (CHAIN540 + DRREACH + DRREACHTAP + DRDIST target routine),
# RTL fork claude/dist-target (LeafEval/CoproDrMario `DRDIST` on top of ANTIBODY's DRHSV + DRLEV_SQREG/WRREG/VNPF);
# Childproof qsf.used + VERILOG_MACRO DRHSV DRLEV_SQREG DRLEV_WRREG DRLEV_VNPF DRDIST. Seed 3 first (the SOTA seed).
# (reach-wt branch reach-root). Control hex for the FW-in-image proof = the REACH fw d8014d77.
# Uses Childproof's archived NES.qsf.used verbatim; restores the shared fork (HEAD, NES.qsf, copro_rom.hex) on exit.
set -uo pipefail
SEED="${1:-3}"; RTL="${2:?usage: chain540_reach_tap_hsv_dist_build.sh <seed> <rtl-commit>}"
FORK=/home/struktured/projects/NES_MiSTer-winner
SHIP=/home/struktured/projects/dr-mario-main-wt/experiments/rtl_chain/ship_build.sh
W=/home/struktured/projects/dr-mario-h16-wt/tmp/chain540_reach_tap_hsv_dist
FW=$W/fw540_reachtap_dist_1488e158.hex; WANT_FW=1488e1583ab7ad8b2011d4c136926faf; CTRL=$W/fw540_reachtap_77ec742c.hex
CP_QSF=$W/NES.qsf.drhsv_dist; WANT_QSF=a7a0ce8bcefe679e4967b1e178b1765c
TAG=childproof-antibody-dist
OUT=/home/struktured/projects/dr_mario_rl/tmp/rtl_chain/ship/$TAG-seed$SEED
QB=/home/struktured/intelFPGA_lite/23.1std/quartus/bin
PROOF=/home/struktured/projects/dr_mario_rl/tmp/rtl_chain/ship/theta400-seed13/fw_bijection_proof.py
PY=/home/struktured/projects/dr_mario_rl/tmp/venv/bin/python
cd "$FORK" || exit 64
ORIG=$(git rev-parse HEAD)
[ "$(git rev-parse --short HEAD)" = "18cf064" ] || { echo "ABORT: fork HEAD $(git rev-parse --short HEAD) != 18cf064"; exit 64; }
[ "$(md5sum copro_rom.hex | cut -d' ' -f1)" = "f78f1e9376405dc996404f68dfa9dfb8" ] || { echo "ABORT: fork hex not baseline"; exit 64; }
[ -z "$(git status --porcelain -- rtl/)" ] || { echo "ABORT: fork rtl/ dirty"; exit 64; }
[ "$(md5sum "$FW" | cut -d' ' -f1)" = "$WANT_FW" ] || { echo "ABORT: fw540_reachtap_dist md5"; exit 64; }
[ "$(md5sum "$CP_QSF" | cut -d' ' -f1)" = "$WANT_QSF" ] || { echo "ABORT: qsf md5"; exit 64; }
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
echo "PRE: RTL $(git rev-parse --short HEAD) fw $(md5sum copro_rom.hex | cut -c1-8) qsf=Childproof's NES.qsf.used+DRHSV+DRLEV_SQREG+DRLEV_WRREG+DRLEV_VNPF+DRDIST; compiling seed $SEED $TAG  $(date -Is)"
nice -n 10 "$SHIP" "$SEED" "$TAG"; rc=$?
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
echo "HSV netlist check: matched60[14] refs=$(command grep -a -c 'matched60\[14\]' "$VO" 2>/dev/null) matched60_p[14] refs=$(command grep -a -c 'matched60_p\[14\]' "$VO" 2>/dev/null) base_matched[14] refs=$(command grep -a -c 'base_matched\[14\]' "$VO" 2>/dev/null) sq_h_in refs=$(command grep -a -c 'sq_h_in' "$VO" 2>/dev/null) sq_v_in refs=$(command grep -a -c 'sq_v_in' "$VO" 2>/dev/null) h_waddr refs=$(command grep -a -c 'h_waddr' "$VO" 2>/dev/null) vn_hit refs=$(command grep -a -c 'vn_hit' "$VO" 2>/dev/null) dt_pen refs=$(command grep -a -c 'dt_pen' "$VO" 2>/dev/null) dbest refs=$(command grep -a -c 'dbest' "$VO" 2>/dev/null) lev_a_tgt refs=$(command grep -a -c 'lev_a_tgt' "$VO" 2>/dev/null)" | tee "$OUT/NETLIST_CHECK.txt"
exit $rc
