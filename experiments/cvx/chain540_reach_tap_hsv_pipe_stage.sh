#!/usr/bin/env bash
# Stage a PASSING fallback-HSV build (fork 391afb8: DRHSV + DRLEV_SQREG/WRREG/VNPF, fw 77ec742c) into
# dr_mario_rl/tmp/rtl_chain/ship/chain540-reach-tap-hsv/  -- rbf + BUILD.md + proofs. Refuses unless every check holds:
#   verdict rc 0 (fit_verdict.sh: copro >= +0.10, pll_hdmi >= -0.012-0.05), FW bijection == 77ec742c,
#   HSV in the netlist (matched60[14]), fallback registers present (vn_hit, h_waddr in the netlist; sq_h_in/sq_v_in
#   PACKED into the LeafEval Mult DSPs and run_h/run_v NOT -- the fit report's register-packing table).
# The TAP carts are NOT copied: HSV is RTL-only, the carts in ../chain540-reach-tap/ pair unchanged.
set -u
SEED="${1:?usage: chain540_reach_tap_hsv_pipe_stage.sh <seed>}"
SHIPD=/home/struktured/projects/dr_mario_rl/tmp/rtl_chain/ship
A=$SHIPD/childproof-chain540-reach-tap-hsv-pipe-seed$SEED; S=$SHIPD/chain540-reach-tap-hsv; TAP=$SHIPD/chain540-reach-tap
fail() { echo "REFUSE: $*"; exit 1; }
grep -a -q '^VERDICT: SHIP AS-IS' "$A/verdict.txt" || fail "verdict is not SHIP AS-IS"
grep -a -A2 'fw540_reachtap.hex :' "$A/FW_IN_IMAGE_PROOF.txt" | grep -a -q 'PERFECT BIJECTION' || fail "FW bijection"
[ "$(md5sum "$A/copro_rom.hex" | cut -d' ' -f1)" = 77ec742cf0446b49a7f363b34c522864 ] || fail "archived fw md5"
grep -a -q '"rtl_commit": "391afb8ffeafcd9b532127b879c814eb1f9f7fcd"' "$A/manifest.json" || fail "rtl commit"
N=$(cat "$A/HSV_NETLIST_CHECK.txt")
for k in 'matched60\[14\] refs=' 'vn_hit refs=' 'h_waddr refs='; do
  v=$(echo "$N" | grep -a -o -E "$k[0-9]+" | grep -a -o -E '[0-9]+$'); [ "${v:-0}" -gt 0 ] || fail "netlist: $k$v"
done
for m in DRHSV DRLEV_SQREG DRLEV_WRREG DRLEV_VNPF; do grep -a -q "VERILOG_MACRO \"$m=1\"" "$A/NES.qsf.used" || fail "qsf lacks $m"; done
SQP=$(grep -a -c -E 'LeafEval:leafeval\|sq_[hv]_in\[[0-9]\].*Packed Register.*LeafEval:leafeval\|Mult[0-9]+' "$A/NES.fit.rpt")
RUNP=$(grep -a -c -E 'LeafEval:leafeval\|run_[hv]\[[0-9]\][^;]*;[^;]*Packed Register.*LeafEval:leafeval\|Mult[0-9]+' "$A/NES.fit.rpt")
[ "$SQP" -gt 0 ] && [ "$RUNP" = 0 ] || fail "DSP packing: sq_*_in packed=$SQP run_* packed=$RUNP"
{ echo "fallback-register check (seed $SEED, fit report register-packing + netlist):"
  echo "  sq_h_in/sq_v_in bits PACKED into LeafEval Mult DSPs: $SQP rows (DRLEV_SQREG present; the DSP inputs are the enable-free copies)"
  echo "  run_h/run_v bits packed into a Mult DSP: $RUNP rows (was the seed-13 HSV-only root cause: run_h -> Mult5~8)"
  echo "  $N"; } > "$A/FALLBACK_REG_CHECK.txt"
DATE=$(date +%Y%m%d); RBF=NES_childproof_chain540_reach_tap_hsv_fb_seed${SEED}_$DATE.rbf
[ -f "$S/BUILD_FAILED.md" ] && mv "$S/BUILD_FAILED.md" "$A/BUILD_FAILED_prior_staging_note.md"
cp "$A/NES.rbf" "$S/$RBF"; cp "$A/FW_IN_IMAGE_PROOF.txt" "$A/verdict.txt" "$A/NES.qsf.used" "$A/HSV_NETLIST_CHECK.txt" "$A/FALLBACK_REG_CHECK.txt" "$S/"
cp "$TAP/fw540_reachtap_77ec742c.hex" "$S/"
RM=$(md5sum "$S/$RBF" | cut -d' ' -f1); [ "$RM" = "$(md5sum "$A/NES.rbf" | cut -d' ' -f1)" ] || fail "rbf copy md5"
CS=$(grep -a 'copro slack' "$A/verdict.txt" | grep -a -o -E '[-]?[0-9]+\.[0-9]+' | head -1)
PH=$(grep -a 'pll_hdmi' "$A/verdict.txt" | grep -a -o -E '[-]?[0-9]+\.[0-9]+' | head -1)
AL=$(grep -a 'ALMs' "$A/verdict.txt" | grep -a -o -E '[0-9]+ / [0-9]+' | head -1)
COUCH=$(ls "$TAP"/drmario_te_couch_*tap2_*.nes); CVC=$(ls "$TAP"/drmario_cvc_*tap2_*.nes)
cat > "$S/BUILD.md" <<EOF
# chain540-reach-tap-hsv — staged (NOT deployed). Build record: h16-wt experiments/cvx/CHAIN540_REACH_TAP_HSV_BUILD.md
- **rbf** \`$RBF\`, md5 $RM.
  - RTL: NES_MiSTer-drmario \`claude/hsv-leaf\` 391afb8 (LeafEval.sv md5 25f6b499; the ONLY file differing from shipping 08f2343).
  - Defines: DRHSV + DRLEV_SQREG + DRLEV_WRREG + DRLEV_VNPF (Childproof qsf.used + VERILOG_MACROs), SEED $SEED.
  - fw 77ec742c (CHAIN540 + DRREACH + DRREACHTAP), unchanged from chain540-reach-tap.
- **Timing:** copro $CS ns (bar +0.10) · pll_hdmi $PH ns (bar ≥ −0.062) · ALMs $AL.
  - The bars are defined in \`dr-mario-main-wt/experiments/rtl_chain/fit_verdict.sh\` (main @ 160ecaf):
    SLACK_BAR=0.10 (l.25); BASE_HDMI=−0.012 with pass iff hdmi ≥ BASE_HDMI−0.05 (l.24, l.87).
- **Proofs:**
  - \`FW_IN_IMAGE_PROOF.txt\`: bijection 16/16 == 77ec742c.
  - \`HSV_NETLIST_CHECK.txt\`: matched60[14] present, i.e. the HSV fold into matched60 at S_COLWALK (S_DONE2 untouched).
  - \`FALLBACK_REG_CHECK.txt\`: vn_hit / h_waddr are in the netlist; sq_h_in / sq_v_in are packed into the Mult DSPs,
    and run_h / run_v are NOT.
- **Gates:** dr-mario-te \`hsv-leaf\` 3756966, \`experiments/hsv/GATE_FALLBACK.txt\`.
  - Bitexact + linknode + 15 mutants.
  - 0 added engine cycles.
  - The firmware co-sim matches HSV-only on moves AND clocks, 69/69.

**PAIRING — the TAP carts are UNCHANGED** (HSV is RTL-only; fw and CoproDrMario.sv are identical to chain540-reach-tap). Use them from \`../chain540-reach-tap/\`:
- couch TE: \`$(basename "$COUCH")\` md5 $(md5sum "$COUCH" | cut -d' ' -f1)
- CvC soak: \`$(basename "$CVC")\` md5 $(md5sum "$CVC" | cut -d' ' -f1)
- \`fw540_reachtap_77ec742c.hex\` (copied here) md5 $(md5sum "$S/fw540_reachtap_77ec742c.hex" | cut -d' ' -f1)

The pairing rules of chain540-reach-tap/BUILD.md apply unchanged: P=0 DAS, P≥2 tap, and an old cart means no filter.
EOF
echo "STAGED $S/$RBF md5 $RM"; ls -la "$S"
