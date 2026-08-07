#!/usr/bin/env bash
# Post-2x2 queue, ordered by what the headline depends on.
#
# 1. THE CONTROL ARM (A'). Arms B and D take their base candidates from
#    reach_root's REACHABILITY-FILTERED pool (choose_reach_tier's base branch),
#    while arm A is pure base32 -- the shipped firmware's own search is not
#    reachability-filtered. So D - A confounds "the tuck program" with "the
#    reach32 fix". Running the tier-3 decision path with theta so large no tuck
#    can ever pass the gate isolates it: that arm IS reach-filtered base32 with
#    no tucks. D - A' is then the tuck program alone, and A' - A prices the
#    reachability filter on its own.
# 2. Divergence horizon (explicitly requested).
# 3. Theta sensitivity (robustness check, last).
set -u
cd "$(dirname "$0")"
PY=/home/struktured/projects/dr_mario_rl/tmp/venv/bin/python
N=${N:-400}
W=${W:-6}

while pgrep -x -f "bash run_all.sh" > /dev/null; do sleep 30; done
echo "=== run_all.sh clear, starting queue2 $(date -Is) ==="

echo "=== START ctrl_bursty $(date -Is) ==="
"$PY" run_2x2.py --seeds "$N" --workers "$W" --pressure bursty --theta 1e18 \
    --arms t3_drop --out results/ctrl_bursty_notuck 2>&1
echo "=== END ctrl_bursty rc=$? $(date -Is) ==="

echo "=== START ctrl_clean $(date -Is) ==="
"$PY" run_2x2.py --seeds "$N" --workers "$W" --pressure clean --theta 1e18 \
    --arms t3_drop --out results/ctrl_clean_notuck 2>&1
echo "=== END ctrl_clean rc=$? $(date -Is) ==="

echo "=== START divergence_clean $(date -Is) ==="
"$PY" divergence.py --seeds 300 --workers "$W" --pressure clean \
    --out results/divergence_clean 2>&1
echo "=== END divergence_clean rc=$? $(date -Is) ==="

echo "=== START divergence_bursty $(date -Is) ==="
"$PY" divergence.py --seeds 300 --workers "$W" --pressure bursty \
    --out results/divergence_bursty 2>&1
echo "=== END divergence_bursty rc=$? $(date -Is) ==="

echo "=== START theta0 $(date -Is) ==="
"$PY" run_2x2.py --seeds "$N" --workers "$W" --pressure bursty --theta 0 \
    --arms t3_drop,t3_tuck --out results/bursty_theta0 2>&1
echo "=== END theta0 rc=$? $(date -Is) ==="

echo "=== START theta250 $(date -Is) ==="
"$PY" run_2x2.py --seeds "$N" --workers "$W" --pressure bursty --theta 250 \
    --arms t3_drop,t3_tuck --out results/bursty_theta250 2>&1
echo "=== END theta250 rc=$? $(date -Is) ==="

echo "QUEUE2 COMPLETE $(date -Is)"
