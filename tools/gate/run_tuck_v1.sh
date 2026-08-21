#!/bin/bash
# run_tuck_v1.sh -- price the descriptor stream the POCKET core actually publishes.
#
# probe7 mode 4 emulates tuck v1 (fpga/copro/tuck_scan.py), which is what the rematch
# platform's core carries: Cores/agg23.NES/nes.rev a0d5190f = strand180_20, firmware e970e9ab,
# built DRSTRAND=20 DRCOPRO_TUCK=1 ... -- v1, no tuck_v3, therefore NO theta at any dose.
# v1 has no value gate: it takes the deepest executor-reachable rest under best_col.
# The number that matters is MISLAND -- pills where a descriptor was live and the capsule did
# NOT rest on the column the search scored, i.e. the documented "strictly worse than no tuck".
set -u
# Worktree-relative (dispatcher-hook pattern, 2026-08-20 #140): a hardcoded worktree
# here silently gated ANOTHER worktree's carts when run from a foreign checkout.
D=$(git -C "$(dirname "${BASH_SOURCE[0]}")" rev-parse --show-toplevel) || exit 2
[ -f "$D/patch_cartridge_copro.py" ] || { echo "FAIL: resolved worktree $D lacks the emitter -- refusing to gate the wrong tree" >&2; exit 2; }
R="$D/tools/gate/run_one7.sh"
LOG="$D/tmp/clean/tuckv1.log"
mkdir -p "$D/tmp/clean"; : >"$LOG"
say() { echo "[$(date +%H:%M:%S)] $*" | tee -a "$LOG"; }
say "=== v1-FUNC: v8+tuck ship flags, 18000f, tuck-v1 descriptors (the Pocket stream) ==="
bash "$R" w-v1-func "$D/roms/v8tuck.nes"  18000 4 2>&1 | tee -a "$LOG"
say "=== v1-CTL: v8 plain DRTUCK=0, 9000f, SAME v1 descriptors (must execute ZERO) ==="
bash "$R" w-v1-ctl  "$D/roms/v8repro.nes"  9000 4 2>&1 | tee -a "$LOG"
say "=== DONE ==="
for t in w-v1-func w-v1-ctl; do
  s=$(command grep -a "SUMMARY tag=$t" "$D/tmp/clean/$t/probe7.log" 2>/dev/null | head -1)
  echo "${t}: ${s:-NO LOG}" | tee -a "$LOG"
done
