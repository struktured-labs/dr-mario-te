#!/bin/bash
# soak_only.sh -- phase 3 alone: the seed-segmented soak, given gates that already passed.
#
# WHY THIS EXISTS SEPARATELY. drive_soak2.sh runs gates then soak in one process. The gates are
# cheap (~60 s an arm) and their results are already on disk; the soak is hours. Re-running the
# gates to restart the soak would burn the budget the soak needs. This runs phase 3 only, taking
# the gate outcomes as inputs, so the long run can be restarted, resized or re-tuned without
# discarding validated evidence.
#
# It does NOT decide anything the gates decided: ACHK_USABLE is passed IN. If the A-check was not
# proven usable, it is passed as 0 and the soak's ACHK line must be read as VOID, not as evidence.
#
# Env: BOOT SEEDS FPS ACHK_USABLE DEADLINE_EPOCH [PS_ACHK_EVERY] [EXTRA_ENV...]
set -u
# Worktree-relative (dispatcher-hook pattern, 2026-08-20 #140): a hardcoded worktree
# here silently gated ANOTHER worktree's carts when run from a foreign checkout.
D=$(git -C "$(dirname "${BASH_SOURCE[0]}")" rev-parse --show-toplevel) || exit 2
[ -f "$D/patch_cartridge_copro.py" ] || { echo "FAIL: resolved worktree $D lacks the emitter -- refusing to gate the wrong tree" >&2; exit 2; }
R=$D/tools/gate
BOOT=${BOOT:-$D/tmp/soak/v6e_mmc1.nes}
SEEDS=${SEEDS:-"114 4271 21013 30011"}
FPS=${FPS:-60}
ACHK_USABLE=${ACHK_USABLE:-0}
LOG=$D/tmp/soak/drive.log
DEADLINE=${DEADLINE_EPOCH:?DEADLINE_EPOCH required}

say() { echo "[$(date +%H:%M:%S)] $*" | tee -a "$LOG"; }
left() { echo $(( DEADLINE - $(date +%s) )); }

# ⚠ REFUSE TO BE THE SECOND DRIVER. Twice today two soak drivers ran for one deliverable. The
# damage is not a crash -- Mesen is single-instance so they politely serialise -- it is that they
# share TAGS. Both write tmp/soak/s-soak-s<seed>/probe_soak.log, so the second silently OVERWRITES
# the first's segment, and both append to drive.log so the narrative interleaves and stops
# attributing. Worst case a seed is counted twice in the pooled denominator, which INFLATES the
# bound: the run would claim more evidence than it has, in the single number this rig exists to
# produce. Detection is BY UNIT, never `pgrep -f`, which has twice today reported a dead driver as
# alive by matching a sibling's command line -- and reapers are excluded because a reaper is not a
# driver: it owns no tag and writes no segment.
SELF_UNIT="${SOAK_UNIT:-}"
OTHERS=$(systemctl --user list-units --state=active --no-legend 'drmario-soak-*' 2>/dev/null \
         | command awk '{print $1}' | command grep -v 'reap' | command grep -v "^${SELF_UNIT}$" || true)
if [ -n "${OTHERS//[[:space:]]/}" ]; then
  say "REFUSING TO START: another soak DRIVER unit is already active:"
  for u in $OTHERS; do say "    $u"; done
  say "  Stop it by unit (systemctl --user stop <unit>), or pass SOAK_UNIT=<own unit name>."
  exit 2
fi

ARM_RC=0
arm() {
  local tag="$1" cart="$2" fr="$3" tmo="$4"
  while :; do
    SEAT_WAIT_POLLS=180 bash "$R/run_soak.sh" "$tag" "$cart" "$fr" "$tmo" 2>&1 | tee -a "$LOG"
    ARM_RC=${PIPESTATUS[0]}
    [ "$ARM_RC" != 4 ] && return 0
    if [ "$(left)" -lt 600 ]; then say "$tag: seat never freed, budget gone -- UNRUN"; return 0; fi
    say "$tag: seat held by another lane; $(left)s left, waiting again"
  done
}

NSEED=$(echo $SEEDS | wc -w)
REM=$(left); BUDGET=$(( REM - 480 ))       # reserve 8 min for teardown + the pooled bound
if [ "$BUDGET" -lt 600 ]; then say "FATAL: no budget for the soak ($BUDGET s)"; exit 1; fi
PERSEG=$(( BUDGET / NSEED ))
say "=== soak_only: $NSEED segments, ${PERSEG}s each, fps=$FPS, ACHK_USABLE=$ACHK_USABLE, every=${PS_ACHK_EVERY:-1} ==="

for sd in $SEEDS; do
  RL=$(left)
  if [ "$RL" -lt 600 ]; then say "seed $sd SKIPPED: only ${RL}s left"; continue; fi
  SEGB=$(( RL - 480 )); [ "$SEGB" -gt "$PERSEG" ] && SEGB=$PERSEG
  SEGF=$(python3 -c "print(int($SEGB * $FPS * 0.92))")
  say "--- segment seed=$sd : $SEGF frames, ${SEGB}s budget ---"
  t0=$(date +%s)
  PS_SEED=$sd PS_ACHK=$ACHK_USABLE PS_INJECT=0 PS_CKPT=30000 \
    arm "s-soak-s$sd" "$BOOT" "$SEGF" $(( SEGB + 240 ))
  say "segment seed=$sd rc=$ARM_RC wall=$(( $(date +%s) - t0 ))s"
done

say "--- pooled bound ---"
python3 "$R/soak_bound.py" $D/tmp/soak/s-soak-s*/probe_soak.log 2>&1 | tee -a "$LOG"
say "=== soak_only done ==="
