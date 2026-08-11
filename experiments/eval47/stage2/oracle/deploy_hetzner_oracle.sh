#!/bin/bash
# Sync the sealed oracle tree to the disposable Hetzner node and optionally
# launch Tier A as a persistent systemd unit. `launch` keeps an otherwise-idle
# node busy through true+null; `launch-true` supports the faster two-box split.
set -euo pipefail

TARGET=${1:?usage: deploy_hetzner_oracle.sh root@HOST KEYFILE [launch|launch-true]}
KEY=${2:?usage: deploy_hetzner_oracle.sh root@HOST KEYFILE [launch|launch-true]}
MODE=${3:-deploy-only}
HERE=$(dirname "$(readlink -f "$0")")
REPO=$(readlink -f "$HERE/../../../..")
PROJECTS=/home/struktured/projects
SSH=(ssh -F /dev/null -o BatchMode=yes -o StrictHostKeyChecking=accept-new
     -i "$KEY")
RSH="ssh -F /dev/null -o BatchMode=yes -o StrictHostKeyChecking=accept-new -i $KEY"
EX=(--exclude=__pycache__/ --exclude='*.pyc' --exclude=.git/
    --exclude=eval47/tmp/ --exclude=stage2/oracle/out/
    --exclude=stage2/oracle/logs/ --exclude='*.mp4' --exclude='*.png'
    --exclude='*.jpg' --exclude='id_*' --exclude='*.pem')

echo "=== REMOTE PREFLIGHT ==="
"${SSH[@]}" "$TARGET" '
  hostname
  nproc
  free -h
  uptime
  if systemctl is-active --quiet drm-oracle-clair-a; then
    echo "drm-oracle-clair-a is already active" >&2
    exit 3
  fi
  if ps -eo pid,etime,pcpu,pmem,cmd | grep -E "run_oracle|run_ab.py" | grep -v grep; then
    echo "remote compute job already active; refusing to oversubscribe" >&2
    exit 4
  fi
'

"${SSH[@]}" "$TARGET" \
  'mkdir -p /home/struktured/projects/dr_mario_rl/tmp \
            /home/struktured/projects/dr_mario_rl/.claude/worktrees/faithful-sim \
            /home/struktured/projects/dr-mario-qa-wt/experiments'

for d in combo_term endgame tuck pillrng; do
  rsync -a -e "$RSH" "${EX[@]}" \
    "$PROJECTS/dr_mario_rl/tmp/$d/" \
    "$TARGET:/home/struktured/projects/dr_mario_rl/tmp/$d/"
done
rsync -a -e "$RSH" "${EX[@]}" \
  "$PROJECTS/dr_mario_rl/.claude/worktrees/faithful-sim/src/" \
  "$TARGET:/home/struktured/projects/dr_mario_rl/.claude/worktrees/faithful-sim/src/"
rsync -a -e "$RSH" "${EX[@]}" --exclude=eval47/results/dr_lulu_20260808_fit.json \
  "$REPO/experiments/" \
  "$TARGET:/home/struktured/projects/dr-mario-qa-wt/experiments/"
rsync -a -e "$RSH" \
  "$PROJECTS/dr-mario-qa-wt/experiments/eval47/results/dr_lulu_20260808_fit.json" \
  "$TARGET:/home/struktured/projects/dr-mario-qa-wt/experiments/eval47/results/"

REMOTE_ORACLE=/home/struktured/projects/dr-mario-qa-wt/experiments/eval47/stage2/oracle
echo "=== REMOTE FAST GATES ==="
"${SSH[@]}" "$TARGET" "cd $REMOTE_ORACLE && \
  export NUMBA_CACHE_DIR=/tmp/dr-mario-te-numba-cache && mkdir -p \"\$NUMBA_CACHE_DIR\" && \
  /root/drm/venv/bin/python gate_dist.py && \
  /root/drm/venv/bin/python gate_null_thinning.py && \
  /root/drm/venv/bin/python test_oracle_verdict.py && \
  /root/drm/venv/bin/python test_runner_banking.py"

if [[ "$MODE" == launch || "$MODE" == launch-true ]]; then
  if [[ "$MODE" == launch ]]; then
    RUNNER="$REMOTE_ORACLE/run_full.sh A 4"
    DESCRIPTION="Tier-A ORACLE-CLAIR true+null N=9000"
  else
    RUNNER="$REMOTE_ORACLE/run_label.sh true 4"
    DESCRIPTION="Tier-A ORACLE-CLAIR true label N=9000"
  fi
  echo "=== LAUNCH REMOTE: $DESCRIPTION ==="
  "${SSH[@]}" "$TARGET" "systemd-run --unit=drm-oracle-clair-a \
    --description='$DESCRIPTION' \
    --property=Restart=on-failure --property=RestartSec=20 \
    /bin/bash $RUNNER"
  "${SSH[@]}" "$TARGET" 'systemctl --no-pager status drm-oracle-clair-a || true'
else
  echo "deploy-only complete; use 'launch' for true+null or 'launch-true'"
  echo "when the heavier null will run locally in parallel"
fi
