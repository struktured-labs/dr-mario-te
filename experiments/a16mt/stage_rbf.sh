#!/usr/bin/env bash
# Stage a PASSING experiments/a16mt/build_rbf.sh fit (V11 + A16, fw b545d740) into
# dr_mario_rl/tmp/rtl_chain/ship/antibody-dist60-v11-a16/ (NOT deployed). Refuses unless: verdict SHIP AS-IS
# (fit_verdict.sh: copro >= +0.10, pll_hdmi >= -0.062, ALMs), the FW-in-image bijection == the staged fw AND both controls
# MISMATCH (V11 c51d2e21, one byte away; DIST60 1488e158), RTL commit 3b164c7, the 5 macros, the HSV / fallback / DRDIST
# logic present in the netlist, the rbf md5 differs from every V11 / DIST60 rbf (a hex-only change must change the
# bitstream: the update_mif / smart-recompilation trap), and the paired couch carts at their md5s: FAIR2PLUS 5a1695da and
# FAIR2PLUS + MIN_THINK 4 hooks 170f179d.
#   stage_rbf.sh <seed> <fw-md5> <carts-dir>     (carts-dir holds ctl_fair2plus.nes + fair2plus_mt2.nes from
#                                                  tools/a16mt/build_carts.sh)
set -u
SEED="${1:?seed}"; FWMD5="${2:?fw md5}"; CARTS="${3:?carts dir}"
SHIPD=/home/struktured/projects/dr_mario_rl/tmp/rtl_chain/ship
A=$SHIPD/antibody-dist60-v11-a16-seed$SEED; S=$SHIPD/antibody-dist60-v11-a16
F2P=$CARTS/ctl_fair2plus.nes; MT2=$CARTS/fair2plus_mt2.nes
fail() { echo "REFUSE: $*"; exit 1; }
command grep -a -q '^VERDICT: SHIP AS-IS' "$A/verdict.txt" || fail "verdict is not SHIP AS-IS"
command grep -a -A2 "${FWMD5:0:8}.hex :" "$A/FW_IN_IMAGE_PROOF.txt" | command grep -a -q 'PERFECT BIJECTION' || fail "FW bijection"
command grep -a -A2 'leflush_c51d2e21.hex :' "$A/FW_IN_IMAGE_PROOF.txt" | command grep -a -q 'MISMATCH' || fail "control fw c51d2e21 did not mismatch"
command grep -a -A2 'fw540_reachtap_dist_1488e158.hex :' "$A/FW_IN_IMAGE_PROOF.txt" | command grep -a -q 'MISMATCH' || fail "control fw 1488e158 did not mismatch"
[ "$(md5sum "$A/copro_rom.hex" | cut -d' ' -f1)" = "$FWMD5" ] || fail "archived fw md5"
command grep -a -q '"rtl_commit": "3b164c7' "$A/manifest.json" || fail "rtl commit"
for m in DRHSV DRLEV_SQREG DRLEV_WRREG DRLEV_VNPF DRDIST; do command grep -a -q "VERILOG_MACRO \"$m=1\"" "$A/NES.qsf.used" || fail "qsf lacks $m"; done
N=$(cat "$A/NETLIST_CHECK.txt")
for k in 'matched60\[14\] refs=' 'vn_hit refs=' 'h_waddr refs=' 'dt_pen refs=' 'dbest refs=' 'lev_a_tgt refs='; do
  v=$(echo "$N" | command grep -a -o -E "$k[0-9]+" | command grep -a -o -E '[0-9]+$'); [ "${v:-0}" -gt 0 ] || fail "netlist: $k$v"
done
R=$(md5sum < "$A/NES.rbf" | cut -c1-32)
for old in 43aa62d5712c7a28e9ce42c56387fdaf b64d8ea99b94aaac26dd64a3f12a52bd 527e8dd6b990f38e575d23a96024e65e 318607aabb0520ec941f578984dd8b9b; do
  [ "$R" != "$old" ] || fail "rbf md5 $R equals a known non-A16 build ($old): the firmware did not reach the bitstream"
done
[ "$(md5sum < "$F2P" | cut -c1-32)" = 5a1695da51a850b38eaf983bbae49206 ] || fail "FAIR2PLUS cart md5"
[ "$(md5sum < "$MT2" | cut -c1-32)" = 170f179db8d63c24a0b1bcd747c9df7e ] || fail "FAIR2PLUS+MT2 cart md5"
mkdir -p "$S"
RBF=NES_antibody_dist60_v11_a16_seed${SEED}_$(date +%Y%m%d).rbf
cp "$A/NES.rbf" "$S/$RBF"
for f in FW_IN_IMAGE_PROOF.txt verdict.txt NES.qsf.used NETLIST_CHECK.txt manifest.json; do cp "$A/$f" "$S/seed${SEED}_$f"; done
cp "$A/copro_rom.hex" "$S/fw540_reachtap_dist_tuckreach_leflush_vk16_${FWMD5:0:8}.hex"
cp "$F2P" "$S/drmario_te_couch_fair2plus_5a1695da.nes"
cp "$MT2" "$S/drmario_te_couch_fair2plus_mt2_170f179d.nes"
( cd "$S" && md5sum ./*.rbf ./*.hex ./*.nes > MD5SUMS )
echo "STAGED $S/$RBF md5 $R"; ls -la "$S"
