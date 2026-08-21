#!/bin/bash
# Pause-hypothesis arms. Runs at the ONE configuration known to wedge (orient 3, seed 114)
# so `leak` is a positive control: if leak does not wedge the run is VOID, not a fix.
set -u
# Worktree-relative (dispatcher-hook pattern, 2026-08-20 #140): a hardcoded worktree
# here silently gated ANOTHER worktree's carts when run from a foreign checkout.
D=$(git -C "$(dirname "${BASH_SOURCE[0]}")" rev-parse --show-toplevel) || exit 2
[ -f "$D/patch_cartridge_copro.py" ] || { echo "FAIL: resolved worktree $D lacks the emitter -- refusing to gate the wrong tree" >&2; exit 2; }
while pgrep -f 'Release/Mesen .*probe_rotwedge' >/dev/null; do sleep 20; done
for arm in leak fix poke; do
  RQ_SEED=114 "$D/tools/gate/run_rotpause.sh" 3 12000 "$arm" </dev/null 2>&1 | command grep -a "^SUMMARY\|MISMATCH\|FAILED"
done
