#!/usr/bin/env bash
# STEER10 mechanism check (steer10_mech.py): every (variant, game) brain-only replay + every variant's decide pass.
# Launch DETACHED under the steer10- unit prefix (the steer10-throttle PAUSE/cap switch targets python processes in
# steer10-*.service cgroups):
#   systemd-run --user --unit steer10-mech -p MemoryMax=24G -p MemorySwapMax=0 -p Nice=19 \
#       /home/struktured/projects/dr-mario-h16-wt/experiments/cvx/steer10_mech.sh [VARIANT ...]
# PAUSE: touch /home/struktured/projects/dr_mario_rl/tmp/steer10/PAUSE  (or the shared .../tmp/PAUSE_ALL)
set -uo pipefail
CVX=/home/struktured/projects/dr-mario-h16-wt/experiments/cvx
TMP=/home/struktured/projects/dr-mario-h16-wt/tmp/steer10
PY=/home/struktured/projects/dr_mario_rl/tmp/venv/bin/python
W=${STEER10_WORKERS:-8}
cd "$CVX" || exit 2
mkdir -p "$TMP" steer10/mech
LOG="$TMP/mech.log"; JB="$TMP/mech_jobs_$$.txt"
if [ $# -gt 0 ]; then VARS="$*"; else
  VARS=$("$PY" -c "import ast; t=ast.parse(open('steer10_mech.py').read()); print(' '.join(k.value for n in t.body if isinstance(n, ast.Assign) and getattr(n.targets[0], 'id', '') == 'VARIANTS' for k in n.value.keys))")
fi
GAMES="m1g2 m1g4 m2g3 m5g2 m1g1 m2g1 m2g2 m1g3 m1g5 m2g4"
echo "[$(date -u +%FT%TZ)] steer10 mech start, workers $W, git $(git rev-parse --short=8 HEAD), variants: $VARS" >> "$LOG"
{
  for v in $VARS; do
    for g in $GAMES; do echo "$v.$g steer10_mech.py replay $v $g steer10/mech/rep_${v}_${g}.jsonl"; done
    echo "$v.decide steer10_mech.py decide $v steer10/mech/dec_${v}.jsonl"
  done
} > "$JB"
run_one() {
  local tag=$1; shift
  local out=${@: -1}
  if [ -f "$out.done" ]; then echo "[$(date -u +%FT%TZ)] skip $out (done)" >> "$LOG"; return 0; fi
  NUMBA_CACHE_DIR="$TMP/nb_mech_$tag" nice -n 19 "$PY" "$@" 2>> "$TMP/mech_err_$tag.log"
  local rc=$?
  [ $rc -eq 0 ] && touch "$out.done"
  echo "[$(date -u +%FT%TZ)] done $out rc=$rc rows=$(wc -l < "$out" 2>/dev/null || echo 0)" >> "$LOG"
}
export -f run_one; export LOG TMP PY
xargs -P "$W" -L 1 bash -c 'run_one "$@"' _ < "$JB"
echo "[$(date -u +%FT%TZ)] steer10 mech DONE ($(wc -l < "$JB") jobs)" >> "$LOG"
