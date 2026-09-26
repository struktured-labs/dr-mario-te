#!/usr/bin/env bash
# Runs the FALLBACK fit (seed 13, fork 391afb8ffeafcd9b532127b879c814eb1f9f7fcd = DRHSV + DRLEV_SQREG/WRREG/VNPF) ONLY IF the plain-HSV
# sweep ends with "NO SEED PASSED" (coordinator: "fit it only if the seed sweep fails"). Waits for the sweep to exit first
# (one shared fork tree => strictly sequential).
set -u
H=/home/struktured/projects/dr-mario-h16-wt/experiments/cvx; W=/home/struktured/projects/dr-mario-h16-wt/tmp/chain540_reach_tap_hsv
QB=/home/struktured/intelFPGA_lite/23.1std/quartus/bin; FORK=/home/struktured/projects/NES_MiSTer-winner
SUM=$W/SWEEP_SUMMARY.txt; RTL=391afb8ffeafcd9b532127b879c814eb1f9f7fcd; SEED=13
while pgrep -f chain540_reach_tap_hsv_sweep.sh > /dev/null; do sleep 30; done
if ! tail -3 "$SUM" | grep -a -q 'NO SEED PASSED'; then echo "sweep did not end in NO SEED PASSED -- fallback fit NOT run" | tee -a "$SUM"; exit 0; fi
OUT=/home/struktured/projects/dr_mario_rl/tmp/rtl_chain/ship/childproof-chain540-reach-tap-hsv-pipe-seed$SEED
echo "=== fallback fit start $(date -Is) seed $SEED rtl ${RTL:0:7} ===" >> "$SUM"
"$H/chain540_reach_tap_hsv_pipe_build.sh" "$SEED" "$RTL" > "$W/build_pipe_seed$SEED.log" 2>&1
sed -e "s#worst_paths.txt#worst_paths_pipe_seed$SEED.txt#; s#worst_path_full.txt#worst_path_full_pipe_seed$SEED.txt#" "$H/chain540_reach_tap_hsv_paths.tcl" > "$W/paths_pipe_seed$SEED.tcl"
(cd "$FORK" && timeout 900 "$QB/quartus_sta" -t "$W/paths_pipe_seed$SEED.tcl" > "$W/sta_pipe_seed$SEED.log" 2>&1)
cp "$W/worst_paths_pipe_seed$SEED.txt" "$OUT/" 2>/dev/null
CS=$(grep -a 'copro slack' "$OUT/verdict.txt" | grep -a -o -E '[-]?[0-9]+\.[0-9]+' | head -1)
PH=$(grep -a 'pll_hdmi' "$OUT/verdict.txt" | grep -a -o -E '[-]?[0-9]+\.[0-9]+' | head -1)
AL=$(grep -a 'ALMs' "$OUT/verdict.txt" | grep -a -o -E '[0-9]+ / [0-9]+' | head -1)
NL=$(cat "$OUT/HSV_NETLIST_CHECK.txt" 2>/dev/null)
echo "FALLBACK seed $SEED: copro $CS pll_hdmi $PH ALMs $AL | $NL $(date -Is)" | tee -a "$SUM"
if awk -v c="$CS" -v p="$PH" 'BEGIN{exit !(c+0 >= 0.10 && p+0 >= 0)}'; then echo "FALLBACK PASS at seed $SEED" | tee -a "$SUM"; else echo "FALLBACK FAIL at seed $SEED" | tee -a "$SUM"; fi
