#!/usr/bin/env bash
# Sequential driver for the independent 2x2. Runs are SEQUENTIAL on purpose:
# the box is shared with a co-sim farm, a self-play rig and adversarial lanes,
# so the 6-worker cap is a cap on the whole lane, not per job.
set -u
cd "$(dirname "$0")"
PY=/home/struktured/projects/dr_mario_rl/tmp/venv/bin/python
N=${N:-400}
W=${W:-6}

run() {           # run <logname> <args...>
  local name=$1; shift
  echo "=== START $name $(date -Is) ==="
  "$PY" run_2x2.py --seeds "$N" --workers "$W" "$@" 2>&1
  echo "=== END $name rc=$? $(date -Is) ==="
}

# 1. PRIMARY: survival under bursty v1.1 pressure, firmware theta
run bursty_t150 --pressure bursty --theta 150 --out results/bursty_theta150

# 2. speed axis: clean stream
run clean_t150 --pressure clean --theta 150 --out results/clean_theta150

# 3. v1 hazard bracket: unperformable descriptor lands in the approach column
#    instead of degrading to a plain drop. v1_drop is re-run (it is identical
#    either way) so the pairing is self-contained.
run bursty_v1haz --pressure bursty --theta 150 --on-blocked approach \
    --arms v1_drop,v1_tuck --out results/bursty_v1_hazard

# 4. theta sensitivity on the headline pair only
run bursty_t0   --pressure bursty --theta 0   --arms t3_drop,t3_tuck \
    --out results/bursty_theta0
run bursty_t250 --pressure bursty --theta 250 --arms t3_drop,t3_tuck \
    --out results/bursty_theta250

echo "ALL RUNS COMPLETE $(date -Is)"
