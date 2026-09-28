#!/usr/bin/env bash
# Seed sweep of ANTIBODY + DRDIST (fork claude/dist-leaf 3b164c7, fw 1488e158). PRE-APPROVED by the coordinator
# (<= 4 seeds). Seed 3 gave copro +0.591 but pll_hdmi -0.596 (framework ascal paths = seed placement noise).
# Sequential (one shared fork tree), nice -n 10 via the build script; stop at the first seed with copro >= +0.10 AND
# pll_hdmi >= baseline-0.05 (the fit_verdict.sh bar: verdict rc 0).   usage: chain540_reach_tap_hsv_pipe_sweep.sh 3 9 ...
set -u
H=/home/struktured/projects/dr-mario-h16-wt/experiments/cvx; W=/home/struktured/projects/dr-mario-h16-wt/tmp/chain540_reach_tap_hsv_dist
QB=/home/struktured/intelFPGA_lite/23.1std/quartus/bin; FORK=/home/struktured/projects/NES_MiSTer-winner
RTL=$(git -C /home/struktured/projects/NES_MiSTer-dist rev-parse 3b164c7); SUM=$W/SWEEP_SUMMARY.txt
echo "=== DIST sweep start $(date -Is) seeds: $* rtl ${RTL:0:7} ===" >> "$SUM"
for SEED in "$@"; do
  OUT=/home/struktured/projects/dr_mario_rl/tmp/rtl_chain/ship/childproof-antibody-dist-seed$SEED
  "$H/chain540_reach_tap_hsv_dist_build.sh" "$SEED" "$RTL" > "$W/build_seed$SEED.log" 2>&1; brc=$?
  sed -e "s#/home/struktured/projects/dr-mario-h16-wt/tmp/chain540_reach_tap_hsv/#$W/#g; s#worst_paths.txt#worst_paths_seed$SEED.txt#; s#worst_path_full.txt#worst_path_full_seed$SEED.txt#" "$H/chain540_reach_tap_hsv_paths.tcl" > "$W/paths_seed$SEED.tcl"
  (cd "$FORK" && timeout 900 "$QB/quartus_sta" -t "$W/paths_seed$SEED.tcl" > "$W/sta_seed$SEED.log" 2>&1)
  cp "$W"/worst_paths_seed$SEED.txt* "$OUT/" 2>/dev/null
  CS=$(grep -a 'copro slack' "$OUT/verdict.txt" | grep -a -o -E '[-]?[0-9]+\.[0-9]+' | head -1)
  PH=$(grep -a 'pll_hdmi' "$OUT/verdict.txt" | grep -a -o -E '[-]?[0-9]+\.[0-9]+' | head -1)
  AL=$(grep -a 'ALMs' "$OUT/verdict.txt" | grep -a -o -E '[0-9]+ / [0-9]+' | head -1)
  echo "DIST seed $SEED: copro $CS pll_hdmi $PH ALMs $AL verdict_rc $brc | $(cat "$OUT/NETLIST_CHECK.txt" 2>/dev/null) $(date -Is)" | tee -a "$SUM"
  if [ "$brc" = 0 ]; then echo "DIST PASS at seed $SEED" | tee -a "$SUM"; exit 0; fi
done
echo "DIST: NO SEED PASSED" | tee -a "$SUM"; exit 1
