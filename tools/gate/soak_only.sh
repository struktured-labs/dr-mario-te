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
D=/home/struktured/projects/dr-mario-v8-wt
R=$D/tools/gate
BOOT=${BOOT:-$D/tmp/soak/v6e_mmc1.nes}
SEEDS=${SEEDS:-"114 4271 21013 30011"}
FPS=${FPS:-60}
ACHK_USABLE=${ACHK_USABLE:-0}
LOG=$D/tmp/soak/drive.log
DEADLINE=${DEADLINE_EPOCH:?DEADLINE_EPOCH required}

say() { echo "[$(date +%H:%M:%S)] $*" | tee -a "$LOG"; }
left() { echo $(( DEADLINE - $(date +%s) )); }

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
