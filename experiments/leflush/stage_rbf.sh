#!/usr/bin/env bash
# Stage a PASSING build_rbf.sh fit (V1 + DRLEFLUSH, fw c51d2e21) into dr_mario_rl/tmp/rtl_chain/ship/antibody-dist60-v11/
# (NOT deployed). Refuses unless: verdict SHIP AS-IS (fit_verdict.sh: copro >= +0.10, pll_hdmi >= -0.062, ALMs), the
# FW-in-image bijection == the staged fw AND both controls MISMATCH (DIST60 1488e158; V1 a1ef31c8, which differs only in
# the reset stub), RTL commit 3b164c7, the 5 macros, the HSV / fallback / DRDIST logic present in the netlist, and the
# paired carts at their md5s: couch b1b57638 (fair kit D + DRABORTSTALE) and CvC 821cafdb (CvC fair + DRABORTSTALE).
#   stage_rbf.sh <seed> <fw-md5>     (several seeds can be staged side by side: proofs are named seed<N>_*)
set -u
SEED="${1:?seed}"; FWMD5="${2:?fw md5}"
SHIPD=/home/struktured/projects/dr_mario_rl/tmp/rtl_chain/ship
A=$SHIPD/antibody-dist60-v11-seed$SEED; S=$SHIPD/antibody-dist60-v11
COUCH=/home/struktured/projects/dr_mario_rl/tmp/abort_stale/carts/drmario_te_couch_fair_abort_b1b57638.nes
CVC=/home/struktured/projects/dr-mario-abortstale-wt/tmp/carts_abort/cvc_fair_abort.nes
fail() { echo "REFUSE: $*"; exit 1; }
command grep -a -q '^VERDICT: SHIP AS-IS' "$A/verdict.txt" || fail "verdict is not SHIP AS-IS"
command grep -a -A2 "${FWMD5:0:8}.hex :" "$A/FW_IN_IMAGE_PROOF.txt" | command grep -a -q 'PERFECT BIJECTION' || fail "FW bijection"
command grep -a -A2 'fw540_reachtap_dist_1488e158.hex :' "$A/FW_IN_IMAGE_PROOF.txt" | command grep -a -q 'MISMATCH' || fail "control fw 1488e158 did not mismatch"
command grep -a -A2 'tuckreach_v1_a1ef31c8.hex :' "$A/FW_IN_IMAGE_PROOF.txt" | command grep -a -q 'MISMATCH' || fail "control fw a1ef31c8 did not mismatch"
[ "$(md5sum "$A/copro_rom.hex" | cut -d' ' -f1)" = "$FWMD5" ] || fail "archived fw md5"
command grep -a -q '"rtl_commit": "3b164c7' "$A/manifest.json" || fail "rtl commit"
for m in DRHSV DRLEV_SQREG DRLEV_WRREG DRLEV_VNPF DRDIST; do command grep -a -q "VERILOG_MACRO \"$m=1\"" "$A/NES.qsf.used" || fail "qsf lacks $m"; done
N=$(cat "$A/NETLIST_CHECK.txt")
for k in 'matched60\[14\] refs=' 'vn_hit refs=' 'h_waddr refs=' 'dt_pen refs=' 'dbest refs=' 'lev_a_tgt refs='; do
  v=$(echo "$N" | command grep -a -o -E "$k[0-9]+" | command grep -a -o -E '[0-9]+$'); [ "${v:-0}" -gt 0 ] || fail "netlist: $k$v"
done
[ "$(md5sum < "$COUCH" | cut -c1-32)" = b1b576388dc2e1abffe6d1390430ebca ] || fail "couch cart md5"
[ "$(md5sum < "$CVC" | cut -c1-32)" = 821cafdbc3017129cad3c66fcc93d605 ] || fail "cvc cart md5"
mkdir -p "$S"
RBF=NES_antibody_dist60_v11_seed${SEED}_$(date +%Y%m%d).rbf
cp "$A/NES.rbf" "$S/$RBF"
for f in FW_IN_IMAGE_PROOF.txt verdict.txt NES.qsf.used NETLIST_CHECK.txt manifest.json; do cp "$A/$f" "$S/seed${SEED}_$f"; done
cp "$A/copro_rom.hex" "$S/fw540_reachtap_dist_tuckreach_leflush_${FWMD5:0:8}.hex"
cp "$COUCH" "$S/drmario_te_couch_fair_abort_b1b57638.nes"
cp "$CVC" "$S/drmario_cvc_fair_abort_821cafdb.nes"
( cd "$S" && md5sum ./*.rbf ./*.hex ./*.nes > MD5SUMS )
echo "STAGED $S/$RBF md5 $(md5sum "$S/$RBF" | cut -d' ' -f1)"; ls -la "$S"
