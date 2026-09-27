#!/usr/bin/env bash
# Seed sweep of the HSV + register-stage FALLBACK build (fork 391afb8: DRHSV + DRLEV_SQREG/WRREG/VNPF).
# NEEDS A COORDINATOR GO-AHEAD before running (standing rule: no seed hunt without asking). Seed 13 gave copro +0.760
# but pll_hdmi -0.176 (framework ascal paths = seed placement noise); this looks for a seed passing BOTH.
# Sequential (one shared fork tree), nice -n 10 via the build script; stop at the first seed with copro >= +0.10 AND
# pll_hdmi >= baseline-0.05 (the fit_verdict.sh bar: verdict rc 0).   usage: chain540_reach_tap_hsv_pipe_sweep.sh 3 9 ...
set -u
H=/home/struktured/projects/dr-mario-h16-wt/experiments/cvx; W=/home/struktured/projects/dr-mario-h16-wt/tmp/chain540_reach_tap_hsv
QB=/home/struktured/intelFPGA_lite/23.1std/quartus/bin; FORK=/home/struktured/projects/NES_MiSTer-winner
RTL=391afb8ffeafcd9b532127b879c814eb1f9f7fcd; SUM=$W/SWEEP_SUMMARY.txt
echo "=== fallback sweep start $(date -Is) seeds: $* rtl ${RTL:0:7} ===" >> "$SUM"
for SEED in "$@"; do
  OUT=/home/struktured/projects/dr_mario_rl/tmp/rtl_chain/ship/childproof-chain540-reach-tap-hsv-pipe-seed$SEED
  "$H/chain540_reach_tap_hsv_pipe_build.sh" "$SEED" "$RTL" > "$W/build_pipe_seed$SEED.log" 2>&1; brc=$?
  sed -e "s#worst_paths.txt#worst_paths_pipe_seed$SEED.txt#; s#worst_path_full.txt#worst_path_full_pipe_seed$SEED.txt#" "$H/chain540_reach_tap_hsv_paths.tcl" > "$W/paths_pipe_seed$SEED.tcl"
  (cd "$FORK" && timeout 900 "$QB/quartus_sta" -t "$W/paths_pipe_seed$SEED.tcl" > "$W/sta_pipe_seed$SEED.log" 2>&1)
  cp "$W"/worst_paths_pipe_seed$SEED.txt* "$OUT/" 2>/dev/null
  CS=$(grep -a 'copro slack' "$OUT/verdict.txt" | grep -a -o -E '[-]?[0-9]+\.[0-9]+' | head -1)
  PH=$(grep -a 'pll_hdmi' "$OUT/verdict.txt" | grep -a -o -E '[-]?[0-9]+\.[0-9]+' | head -1)
  AL=$(grep -a 'ALMs' "$OUT/verdict.txt" | grep -a -o -E '[0-9]+ / [0-9]+' | head -1)
  echo "FALLBACK seed $SEED: copro $CS pll_hdmi $PH ALMs $AL verdict_rc $brc | $(cat "$OUT/HSV_NETLIST_CHECK.txt" 2>/dev/null) $(date -Is)" | tee -a "$SUM"
  if [ "$brc" = 0 ]; then echo "FALLBACK PASS at seed $SEED" | tee -a "$SUM"; exit 0; fi
done
echo "FALLBACK: NO SEED PASSED" | tee -a "$SUM"; exit 1
