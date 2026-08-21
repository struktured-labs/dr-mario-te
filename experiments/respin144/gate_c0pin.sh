#!/usr/bin/env bash
# respin-144 post-build gate sheet. Run AFTER build_mister_dblcanon_c0pin.sh exits 0.
# Every check is a CONTENT proof (build_id.v date stamp means rbf md5 proves nothing).
set -uo pipefail
FORK=/home/struktured/projects/NES_MiSTer-winner
OUT=/home/struktured/projects/dr_mario_rl/tmp/rtl_chain/ship/theta400dblcanon-c0pin-seed13
QEDA=/home/struktured/intelFPGA_lite/23.1std/quartus/bin/quartus_eda
FITRPT=$OUT/NES.fit.rpt
STARPT=$OUT/NES.sta.rpt
EXPECTED=/home/struktured/projects/dr_mario_rl/tmp/rtl_chain/ship/theta400dblcanon-seed13/copro_rom.hex   # b03a586e
CTRL_BASE=/home/struktured/projects/dr_mario_rl/tmp/rtl_chain/ship/theta400-seed13/copro_rom.hex          # f78f1e93, 1356B away
CTRL_TH150=/mnt/data/drmario_cosim/fw/theta_sweep/th150/copro_rom.hex                                     # 2B away from th400 base
fails=0
say() { printf '%-14s %s\n' "$1" "$2"; }
chk() { local n=$1 ok=$2 d=$3; if [ "$ok" = 1 ]; then say "PASS" "$n: $d"; else say "FAIL" "$n: $d"; fails=$((fails+1)); fi }

# G1: fitter verdict (3 criteria: ALM floor, copro slack, pll_hdmi slack)
/home/struktured/projects/dr-mario-main-wt/experiments/rtl_chain/fit_verdict.sh "$FORK" | tee "$OUT/verdict_gate.txt"
command grep -q 'VERDICT: SHIP AS-IS' "$OUT/verdict_gate.txt"; chk G1-fitverdict $([ $? -eq 0 ] && echo 1 || echo 0) "fit_verdict SHIP AS-IS"

# G2: C0 pin honored -- Output Clock Location is N0
loc=$(command grep -A3 'counter\[0\].output_counter' "$FITRPT" | command grep -o 'PLLOUTPUTCOUNTER_X0_Y[0-9]*_N[0-9]*' | head -1)
chk G2-c0loc $([ "$loc" = "PLLOUTPUTCOUNTER_X0_Y5_N1" ] && echo 1 || echo 0) "pll_hdmi output counter at ${loc:-NOT-FOUND}"

# G3: divclk[0] resource placement agrees
dloc=$(command grep 'pll_hdmi.*divclk\[0\]' "$FITRPT" | command grep -o 'PLLOUTPUTCOUNTER_X0_Y[0-9]*_N[0-9]*' | sort -u | tr '\n' ' ')
chk G3-divclk $([ "$dloc" = "PLLOUTPUTCOUNTER_X0_Y5_N1 " ] && echo 1 || echo 0) "divclk[0] placed at: ${dloc:-NOT-FOUND}"

# G4: the location assignment was not IGNORED
ign=$(command grep -i -c 'ignored.*PLLOUTPUTCOUNTER\|PLLOUTPUTCOUNTER.*ignored' "$FITRPT" || true)
chk G4-notignored $([ "${ign:-0}" = 0 ] && echo 1 || echo 0) "ignored-assignment mentions of the pin: $ign"

# G5: VIDEO clock domain read+quoted (pll_hdmi slack from sta rpt)
echo "--- VIDEO domain (sta rpt) ---"; command grep -n 'pll_hdmi' "$STARPT" | head -8 | tee "$OUT/quote_video_domain.txt"
[ -s "$OUT/quote_video_domain.txt" ]; chk G5-videodomain $([ $? -eq 0 ] && echo 1 || echo 0) "video domain lines quoted"

# G6: USER_IO/SPI clock domain read+quoted
echo "--- USER_IO/SPI domain (sta rpt) ---"; command grep -n 'spi_sck' "$STARPT" | head -8 | tee "$OUT/quote_userio_domain.txt"
[ -s "$OUT/quote_userio_domain.txt" ]; chk G6-userio $([ $? -eq 0 ] && echo 1 || echo 0) "spi_sck domain lines quoted"

# G7: firmware-in-netlist content proof with killed-mutant controls
( cd "$FORK" && "$QEDA" --simulation --tool=modelsim --format=verilog --output_directory=output_files/simnet NES ) > "$OUT/eda.log" 2>&1
python3 "$FORK/tools_verify_fw_in_image.py" "$FORK/output_files/simnet/NES.vo" "$EXPECTED" "$CTRL_BASE" "$CTRL_TH150" \
  | tee "$OUT/FW_IN_IMAGE_PROOF.txt"; rcp=${PIPESTATUS[0]}
chk G7-fwproof $([ "$rcp" = 0 ] && echo 1 || echo 0) "16384/16384 expected match + controls killed (exit $rcp)"

# G7b: THE semantic content proof -- the built netlist's counter atom is physical index 5,
# the index pll_cfg_hdmi.v's hardcoded DPRIO write targets.
oci=$(command grep -o 'pll_hdmi|pll_hdmi_inst|altera_pll_i|cyclonev_pll|counter\[0\].output_counter .output_counter_index = [0-9]*' "$FORK/output_files/simnet/NES.vo" | command grep -o '[0-9]*$' | head -1)
chk G7b-index5 $([ "$oci" = 5 ] && echo 1 || echo 0) "netlist output_counter_index = ${oci:-NOT-FOUND} (want 5 = reconfig write target)"

# G8: distinctness -- new rbf differs from every prior artifact
new=$(md5sum "$OUT/NES.rbf" | cut -d' ' -f1)
dup=0; for r in 974de3ed0464edf666b45768007e7be6 de7dea35a9fa03a622cccc8068bd935e; do [ "$new" = "$r" ] && dup=1; done
chk G8-distinct $([ "$dup" = 0 ] && echo 1 || echo 0) "new rbf $new != dblcanon-974de3ed, theta400-de7dea35"

echo; [ "$fails" = 0 ] && echo "GATE SHEET: ALL LOCAL GATES PASS ($new)" || echo "GATE SHEET: $fails FAILURE(S)"
exit "$fails"
