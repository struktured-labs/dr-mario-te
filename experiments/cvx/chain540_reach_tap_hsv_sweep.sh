#!/usr/bin/env bash
# LIMITED seed sweep of the CHAIN540+REACH+TAP+HSV build (coordinator go-ahead 2026-09-26): seeds run SEQUENTIALLY
# (one shared fork tree), under nice -n 10; stop at the first seed with copro slack >= +0.10 AND pll_hdmi >= 0.
# Per seed: slack/ALMs from the ship verdict + the 30 worst copro setup paths (quartus_sta on the compiled db).
set -u
H=/home/struktured/projects/dr-mario-h16-wt/experiments/cvx; W=/home/struktured/projects/dr-mario-h16-wt/tmp/chain540_reach_tap_hsv
QB=/home/struktured/intelFPGA_lite/23.1std/quartus/bin; FORK=/home/struktured/projects/NES_MiSTer-winner
SUM=$W/SWEEP_SUMMARY.txt; echo "=== sweep start $(date -Is) seeds: $* ===" >> $SUM
for SEED in "$@"; do
  OUT=/home/struktured/projects/dr_mario_rl/tmp/rtl_chain/ship/childproof-chain540-reach-tap-hsv-seed$SEED
  "$H/chain540_reach_tap_hsv_seed_build.sh" "$SEED" > "$W/build_seed$SEED.log" 2>&1
  sed -e "s#worst_paths.txt#worst_paths_seed$SEED.txt#; s#worst_path_full.txt#worst_path_full_seed$SEED.txt#" "$H/chain540_reach_tap_hsv_paths.tcl" > "$W/paths_seed$SEED.tcl"
  (cd "$FORK" && timeout 900 "$QB/quartus_sta" -t "$W/paths_seed$SEED.tcl" > "$W/sta_seed$SEED.log" 2>&1)
  cp "$W/worst_paths_seed$SEED.txt" "$OUT/" 2>/dev/null
  CS=$(grep -a 'copro slack' "$OUT/verdict.txt" | grep -a -o -E '[-]?[0-9]+\.[0-9]+' | head -1)
  PH=$(grep -a 'pll_hdmi' "$OUT/verdict.txt" | grep -a -o -E '[-]?[0-9]+\.[0-9]+' | head -1)
  AL=$(grep -a 'ALMs' "$OUT/verdict.txt" | grep -a -o -E '[0-9]+ / [0-9]+' | head -1)
  HSVN=$(grep -a -o 'matched60\[14\] refs=[0-9]*' "$OUT/HSV_NETLIST_CHECK.txt" 2>/dev/null)
  TOP=$(grep -a -E '^; -?[0-9]' "$W/worst_paths_seed$SEED.txt" 2>/dev/null | head -3 | awk -F';' '{gsub(/.*\|/,"",$3); gsub(/.*\|/,"",$4); gsub(/ /,"",$2); printf "%s %s->%s; ", $2, $3, $4}')
  echo "seed $SEED: copro $CS pll_hdmi $PH ALMs $AL $HSVN | worst: $TOP $(date -Is)" | tee -a $SUM
  if awk -v c="$CS" -v p="$PH" 'BEGIN{exit !(c+0 >= 0.10 && p+0 >= 0)}'; then echo "PASS at seed $SEED" | tee -a $SUM; exit 0; fi
done
echo "NO SEED PASSED" | tee -a $SUM; exit 1
