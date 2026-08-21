#!/bin/bash
set -u
# Worktree-relative (dispatcher-hook pattern, 2026-08-20 #140): a hardcoded worktree
# here silently gated ANOTHER worktree's carts when run from a foreign checkout.
D=$(git -C "$(dirname "${BASH_SOURCE[0]}")" rev-parse --show-toplevel) || exit 2
[ -f "$D/patch_cartridge_copro.py" ] || { echo "FAIL: resolved worktree $D lacks the emitter -- refusing to gate the wrong tree" >&2; exit 2; }
while pgrep -x Mesen >/dev/null; do sleep 15; done
RP_SEED=114 RP_PCFRAMES=20 "$D/tools/gate/run_rotpc.sh" 3 4000  </dev/null 2>&1 | command grep -a "^SUMMARY\|FAILED"
RP_SEED=114 RP_PCFRAMES=20 RP_CTLFRAME=1471 "$D/tools/gate/run_rotpc.sh" 0 4000 </dev/null 2>&1 | command grep -a "^SUMMARY\|FAILED"
