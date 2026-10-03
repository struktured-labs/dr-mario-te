#!/usr/bin/env bash
# Stage a PASSING build_rbf.sh fit into dr_mario_rl/tmp/rtl_chain/ship/antibody-dist60-tuckreach/ (NOT deployed).
# Refuses unless: verdict SHIP AS-IS (fit_verdict.sh: copro >= +0.10, pll_hdmi >= -0.062, ALMs), the FW-in-image
# bijection == the staged fw AND the DIST60 fw 1488e158 MISMATCHES, the RTL commit 3b164c7, the 5 macros, the
# HSV / fallback / DRDIST logic present in the netlist, and both DIST60 carts at their md5s.
#   stage_rbf.sh <seed> <tag v1|v2> <fw-md5>      (fit dir = ship/antibody-dist60-tuckreach-seed<seed>_<tag>)
set -u
SEED="${1:?seed}"; TAG="${2:?tag}"; FWMD5="${3:?fw md5}"
SHIPD=/home/struktured/projects/dr_mario_rl/tmp/rtl_chain/ship
A=$SHIPD/antibody-dist60-tuckreach-seed${SEED}_$TAG; S=$SHIPD/antibody-dist60-tuckreach; D60=$SHIPD/antibody-dist60
fail() { echo "REFUSE: $*"; exit 1; }
command grep -a -q '^VERDICT: SHIP AS-IS' "$A/verdict.txt" || fail "verdict is not SHIP AS-IS"
command grep -a -A2 "${FWMD5:0:8}.hex :" "$A/FW_IN_IMAGE_PROOF.txt" | command grep -a -q 'PERFECT BIJECTION' || fail "FW bijection"
command grep -a -A2 'fw540_reachtap_dist_1488e158.hex :' "$A/FW_IN_IMAGE_PROOF.txt" | command grep -a -q 'MISMATCH' || fail "control fw 1488e158 did not mismatch"
[ "$(md5sum "$A/copro_rom.hex" | cut -d' ' -f1)" = "$FWMD5" ] || fail "archived fw md5"
command grep -a -q '"rtl_commit": "3b164c7' "$A/manifest.json" || fail "rtl commit"
for m in DRHSV DRLEV_SQREG DRLEV_WRREG DRLEV_VNPF DRDIST; do command grep -a -q "VERILOG_MACRO \"$m=1\"" "$A/NES.qsf.used" || fail "qsf lacks $m"; done
N=$(cat "$A/NETLIST_CHECK.txt")
for k in 'matched60\[14\] refs=' 'vn_hit refs=' 'h_waddr refs=' 'dt_pen refs=' 'dbest refs=' 'lev_a_tgt refs='; do
  v=$(echo "$N" | command grep -a -o -E "$k[0-9]+" | command grep -a -o -E '[0-9]+$'); [ "${v:-0}" -gt 0 ] || fail "netlist: $k$v"
done
C=$D60/drmario_te_couch_nmifix_reachtx_tap2_spawnedge_c960dd49.nes; V=$D60/drmario_cvc_tuckguard_08211ef4_nmifix_reachtx_tap2_spawnedge_3b8737a9.nes
[ "$(md5sum < "$C" | cut -c1-32)" = c960dd499e877f01c483af1347ed8df6 ] || fail "couch cart md5"
[ "$(md5sum < "$V" | cut -c1-32)" = 3b8737a939c19b1d592218f79bbf869c ] || fail "cvc cart md5"
mkdir -p "$S"
RBF=NES_antibody_dist60_tuckreach_${TAG}_seed${SEED}_$(date +%Y%m%d).rbf
cp "$A/NES.rbf" "$S/$RBF"
for f in FW_IN_IMAGE_PROOF.txt verdict.txt NES.qsf.used NETLIST_CHECK.txt manifest.json; do cp "$A/$f" "$S/${TAG}_$f"; done
cp "$A/copro_rom.hex" "$S/fw540_reachtap_dist_tuckreach_${TAG}_${FWMD5:0:8}.hex"
cp "$C" "$V" "$S/"
( cd "$S" && md5sum ./*.rbf ./*.hex ./*.nes > MD5SUMS )
echo "STAGED $S/$RBF md5 $(md5sum "$S/$RBF" | cut -d' ' -f1)"; ls -la "$S"
