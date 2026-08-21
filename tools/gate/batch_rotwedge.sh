#!/bin/bash
# Replication matrix for #132: does the match-start wedge track the published orient?
set -u
# Worktree-relative (dispatcher-hook pattern, 2026-08-20 #140): a hardcoded worktree
# here silently gated ANOTHER worktree's carts when run from a foreign checkout.
D=$(git -C "$(dirname "${BASH_SOURCE[0]}")" rev-parse --show-toplevel) || exit 2
[ -f "$D/patch_cartridge_copro.py" ] || { echo "FAIL: resolved worktree $D lacks the emitter -- refusing to gate the wrong tree" >&2; exit 2; }
for s in 114 271 999; do
  for o in 0 1 2 3; do
    RW_SEED=$s "$D/tools/gate/run_rotwedge.sh" "$o" 12000 </dev/null 2>&1 | command grep -a "^SUMMARY\|MISMATCH\|FAILED"
  done
done
