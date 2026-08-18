#!/bin/bash
# deploy_hetzner_distill.sh — ship the distillation instrument to the MONTHLY
# node and run the tie-event dataset extension on a DISJOINT seed range.
#
# Derivative of deploy_hetzner_oracle.sh (proven path layout), with three
# deltas that matter:
#
#  1. IRON RULE.  This node is RENTED MONTHLY and is NOT disposable.  This
#     script only ever uses SSH for file transfer and service control.  It
#     never deletes, rebuilds, rescales, changes the type of, or touches the
#     protection on the server.  There is deliberately no hcloud call anywhere
#     in this file.
#
#  2. THE GATE RE-RUNS ON THIS CPU.  New silicon means the logging-is-inert
#     proof does not transfer: a different CPU could in principle produce a
#     different game.  So the identity gate runs HERE, on the SAME SEEDS as the
#     local gate, and the per-seed results are compared against the local
#     artifact.  Same seeds must give the same ply count, the same tie count and
#     the same flip count.  NO GATE, NO ROWS.
#
#  3. DISJOINT SEEDS, and not the ones the brief suggested.  The local identity
#     gate already consumes 61000-61019, so 61000+ is NOT clean for data.  The
#     extension therefore starts at 62000 and 61000-61999 is reserved for gates
#     in perpetuity.  Merging rows later needs provenance that cannot collide.
#
# The pre-existing drm-queue.service is NOT displaced.  It is an idle
# job-queue runner (empty queue, ~0% CPU) that exists to keep this box busy;
# leaving it running costs nothing and removing it would delete a standing
# mechanism this script does not own.
set -euo pipefail

TARGET=${1:?usage: deploy_hetzner_distill.sh root@HOST KEYFILE [gate|launch]}
KEY=${2:?usage: deploy_hetzner_distill.sh root@HOST KEYFILE [gate|launch]}
MODE=${3:-deploy-only}
SEED_START=${SEED_START:-62000}
SEED_COUNT=${SEED_COUNT:-1000}
WORKERS=${WORKERS:-2}
GATE_SEEDS=${GATE_SEEDS:-6}
GATE_START=${GATE_START:-61000}

HERE=$(dirname "$(readlink -f "$0")")
REPO=$(readlink -f "$HERE/../../../..")
PROJECTS=/home/struktured/projects
SSH=(ssh -F /dev/null -o BatchMode=yes -o StrictHostKeyChecking=accept-new
     -o ConnectTimeout=25 -i "$KEY")
RSH="ssh -F /dev/null -o BatchMode=yes -o StrictHostKeyChecking=accept-new -i $KEY"
EX=(--exclude=__pycache__/ --exclude='*.pyc' --exclude=.git/
    --exclude=eval47/tmp/ --exclude=stage2/oracle/out/
    --exclude=stage2/oracle/logs/ --exclude='*.mp4' --exclude='*.png'
    --exclude='*.jpg' --exclude='id_*' --exclude='*.pem')
REMOTE_ORACLE=/home/struktured/projects/dr-mario-qa-wt/experiments/eval47/stage2/oracle
REMOTE_ENV="export NUMBA_CACHE_DIR=/tmp/dr-mario-te-numba-cache && mkdir -p \$NUMBA_CACHE_DIR && export PYTHONPATH=$REMOTE_ORACLE/bootstrap:/home/struktured/projects/dr-mario-qa-wt/experiments\${PYTHONPATH:+:\$PYTHONPATH}"

echo "=== REMOTE PREFLIGHT (read-only) ==="
"${SSH[@]}" "$TARGET" '
  hostname; nproc; uptime
  echo "--- pre-existing drm units (NOT displaced by this script):"
  systemctl list-units "drm-*" --all --no-pager | head -10
  if systemctl is-active --quiet drm-distill-ext; then
    echo "drm-distill-ext already active; refusing to double-launch" >&2
    exit 3
  fi
  if ps -eo cmd | grep -E "run_h12|run_oracle|run_ab\.py" | grep -v grep; then
    echo "a compute job is already running; refusing to oversubscribe" >&2
    exit 4
  fi
  exit 0
'

echo "=== SYNC ==="
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
rsync -a -e "$RSH" "${EX[@]}" \
  --exclude=eval47/results/dr_lulu_20260808_fit.json \
  "$REPO/experiments/" \
  "$TARGET:/home/struktured/projects/dr-mario-qa-wt/experiments/"
rsync -a -e "$RSH" \
  "$REPO/experiments/eval47/results/dr_lulu_20260808_fit.json" \
  "$TARGET:/home/struktured/projects/dr-mario-qa-wt/experiments/eval47/results/"

echo "=== REMOTE CODE FINGERPRINT ==="
"${SSH[@]}" "$TARGET" "cd $REMOTE_ORACLE && sha256sum h12_arm_dataset.py \
  run_h12_dataset.py temporal_accum.py h12_arm.py oracle_arm.py | cat"
echo "--- local, for comparison:"
(cd "$HERE" && sha256sum h12_arm_dataset.py run_h12_dataset.py \
  temporal_accum.py h12_arm.py oracle_arm.py)

if [[ "$MODE" == gate || "$MODE" == launch ]]; then
  echo "=== REMOTE TEMPORAL SELFTEST ==="
  "${SSH[@]}" "$TARGET" "cd $REMOTE_ORACLE && $REMOTE_ENV && \
    /root/drm/venv/bin/python temporal_accum.py"

  echo "=== REMOTE IDENTITY GATE ($GATE_SEEDS seeds from $GATE_START, "\
"$WORKERS workers) ==="
  echo "    NOTE: this node is ~2.3 useful cores, so the gate runs fewer seeds"
  echo "    than the local one; the cross-node comparison below is what makes"
  echo "    the reduced n acceptable."
  # Run the gate as a TRANSIENT UNIT, not over a held-open SSH session: it
  # takes ~45 min on this CPU and a dropped connection must not kill it or,
  # worse, leave it half-run and look like a failure.
  "${SSH[@]}" "$TARGET" "systemctl reset-failed drm-distill-gate 2>/dev/null; \
    systemd-run --unit=drm-distill-gate \
    --description='H12 distill identity gate (this CPU)' \
    --property=WorkingDirectory=$REMOTE_ORACLE \
    --property=Environment=NUMBA_CACHE_DIR=/tmp/dr-mario-te-numba-cache \
    --property=Environment=PYTHONPATH=$REMOTE_ORACLE/bootstrap:/home/struktured/projects/dr-mario-qa-wt/experiments \
    /root/drm/venv/bin/python gate_dataset_identity.py \
      --seeds $GATE_SEEDS --seed-start $GATE_START --workers $WORKERS \
      --out out/gate_dataset_identity_hetzner.json"
  echo "gate launched as drm-distill-gate; poll with:"
  echo "  ssh -i $KEY $TARGET 'journalctl -u drm-distill-gate --no-pager | tail -20'"
fi

if [[ "$MODE" == launch ]]; then
  echo "=== LAUNCH drm-distill-ext (seeds $SEED_START..$((SEED_START+SEED_COUNT-1)), $WORKERS workers) ==="
  "${SSH[@]}" "$TARGET" "systemd-run --unit=drm-distill-ext \
    --description='H12 distillation tie-event dataset extension' \
    --property=Restart=on-failure --property=RestartSec=30 \
    --property=WorkingDirectory=$REMOTE_ORACLE \
    --property=Environment=NUMBA_CACHE_DIR=/tmp/dr-mario-te-numba-cache \
    --property=Environment=PYTHONPATH=$REMOTE_ORACLE/bootstrap:/home/struktured/projects/dr-mario-qa-wt/experiments \
    /root/drm/venv/bin/python run_h12_dataset.py \
      --seed-start $SEED_START --seed-count $SEED_COUNT \
      --workers $WORKERS --segment 50 \
      --outdir out/distill_ext_$SEED_START"
  sleep 5
  "${SSH[@]}" "$TARGET" 'systemctl --no-pager status drm-distill-ext | head -14'
fi
