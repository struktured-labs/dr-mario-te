#!/usr/bin/env bash
# Stage a PASSING ANTIBODY + DRDIST build (fork claude/dist-leaf 3b164c7, fw 1488e158) into
# dr_mario_rl/tmp/rtl_chain/ship/antibody-dist60/ with the DRSPAWNEDGE carts. Refuses unless every check holds:
# verdict SHIP AS-IS (fit_verdict.sh: copro >= +0.10, pll_hdmi >= -0.012-0.05), FW bijection == 1488e158 (and the
# ANTIBODY fw 77ec742c MISMATCHES), the RTL commit, the 5 macros, HSV + fallback + DRDIST logic present in the netlist.
set -u
SEED="${1:?usage: antibody_dist_stage.sh <seed>}"
SHIPD=/home/struktured/projects/dr_mario_rl/tmp/rtl_chain/ship
A=$SHIPD/childproof-antibody-dist-seed$SEED; S=$SHIPD/antibody-dist60
CARTS=/home/struktured/projects/dr-mario-reach-wt/tmp/carts
fail() { echo "REFUSE: $*"; exit 1; }
grep -a -q '^VERDICT: SHIP AS-IS' "$A/verdict.txt" || fail "verdict is not SHIP AS-IS"
grep -a -A2 'fw540_reachtap_dist_1488e158.hex :' "$A/FW_IN_IMAGE_PROOF.txt" | grep -a -q 'PERFECT BIJECTION' || fail "FW bijection"
grep -a -A2 'fw540_reachtap_77ec742c.hex :' "$A/FW_IN_IMAGE_PROOF.txt" | grep -a -q 'MISMATCH' || fail "control fw did not mismatch"
[ "$(md5sum "$A/copro_rom.hex" | cut -d' ' -f1)" = 1488e1583ab7ad8b2011d4c136926faf ] || fail "archived fw md5"
grep -a -q '"rtl_commit": "3b164c7' "$A/manifest.json" || fail "rtl commit"
for m in DRHSV DRLEV_SQREG DRLEV_WRREG DRLEV_VNPF DRDIST; do grep -a -q "VERILOG_MACRO \"$m=1\"" "$A/NES.qsf.used" || fail "qsf lacks $m"; done
N=$(cat "$A/NETLIST_CHECK.txt")
for k in 'matched60\[14\] refs=' 'vn_hit refs=' 'h_waddr refs=' 'dt_pen refs=' 'dbest refs=' 'lev_a_tgt refs='; do
  v=$(echo "$N" | grep -a -o -E "$k[0-9]+" | grep -a -o -E '[0-9]+$'); [ "${v:-0}" -gt 0 ] || fail "netlist: $k$v"
done
[ "$(md5sum < $CARTS/couch_tap2_se1.nes | cut -c1-32)" = c960dd499e877f01c483af1347ed8df6 ] || fail "couch cart md5"
[ "$(md5sum < $CARTS/cvc_tap2_se1.nes | cut -c1-32)" = 3b8737a939c19b1d592218f79bbf869c ] || fail "cvc cart md5"
mkdir -p "$S"
RBF=NES_antibody_dist60_seed${SEED}_$(date +%Y%m%d).rbf
cp "$A/NES.rbf" "$S/$RBF"
cp "$A/FW_IN_IMAGE_PROOF.txt" "$A/verdict.txt" "$A/NES.qsf.used" "$A/NETLIST_CHECK.txt" "$S/"
cp "$A/copro_rom.hex" "$S/fw540_reachtap_dist_1488e158.hex"
cp "$CARTS/couch_tap2_se1.nes" "$S/drmario_te_couch_nmifix_reachtx_tap2_spawnedge_c960dd49.nes"
cp "$CARTS/cvc_tap2_se1.nes" "$S/drmario_cvc_tuckguard_08211ef4_nmifix_reachtx_tap2_spawnedge_3b8737a9.nes"
RM=$(md5sum "$S/$RBF" | cut -d' ' -f1)
CS=$(grep -a 'copro slack' "$A/verdict.txt" | grep -a -o -E '[-]?[0-9]+\.[0-9]+' | head -1)
PH=$(grep -a 'pll_hdmi' "$A/verdict.txt" | grep -a -o -E '[-]?[0-9]+\.[0-9]+' | head -1)
AL=$(grep -a 'ALMs' "$A/verdict.txt" | grep -a -o -E '[0-9]+ / [0-9]+' | head -1)
cat > "$S/BUILD.md" <<MD
# antibody-dist60 — staged (NOT deployed). Build record: h16-wt experiments/cvx/ANTIBODY_DIST_BUILD.md
ANTIBODY (CHAIN540 + REACH + TAP + HSV) + **DRDIST** (STEER6b dist_target60) + **DRSPAWNEDGE** carts.
- **rbf** \`$RBF\`, md5 $RM.
  - RTL: NES_MiSTer-drmario \`claude/dist-leaf\` 3b164c7 (on ANTIBODY's 391afb8; only LeafEval.sv + CoproDrMario.sv
    change).
  - Defines: DRHSV + DRLEV_SQREG + DRLEV_WRREG + DRLEV_VNPF + DRDIST (Childproof qsf.used + macros), SEED $SEED.
- **Firmware** \`fw540_reachtap_dist_1488e158.hex\` = ANTIBODY's 77ec742c recipe + DRDIST=1 (dr-mario-te \`dist-target\`).
- **Timing:** copro $CS ns (bar +0.10) · pll_hdmi $PH ns (bar ≥ −0.062, fit_verdict.sh l.24/87) · ALMs $AL.
- **Proofs:**
  - \`FW_IN_IMAGE_PROOF.txt\`: 16/16 == 1488e158; ANTIBODY 77ec742c 0/16.
  - \`NETLIST_CHECK.txt\`: HSV (matched60[14]), the fallback registers, and the DRDIST engine (dt_pen, dbest,
    lev_a_tgt).
- **Carts (the DRSPAWNEDGE fix, reach-root cd8a3b4; everything else == ANTIBODY):**
  - couch: \`drmario_te_couch_nmifix_reachtx_tap2_spawnedge_c960dd49.nes\`, md5 c960dd499e877f01c483af1347ed8df6;
  - CvC: \`drmario_cvc_tuckguard_08211ef4_nmifix_reachtx_tap2_spawnedge_3b8737a9.nes\`, md5
    3b8737a939c19b1d592218f79bbf869c.
- **PAIRING:** this rbf + these carts.
  - The DRDIST firmware is inside the rbf. The carts carry no DRDIST change: DRSPAWNEDGE is cart-only.
  - An ANTIBODY cart on this rbf is DRDIST without the edge fix.
  - These carts on the ANTIBODY rbf are ANTIBODY plus the edge fix.
MD
echo "STAGED $S/$RBF md5 $RM"; ls -la "$S"
