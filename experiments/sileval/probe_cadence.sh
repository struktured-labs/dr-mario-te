#!/bin/bash
# probe_cadence.sh -- how often does the sampler actually CATCH a match ending?
#
# Not a prereg row and never written to rows/: this measures the INSTRUMENT.
# Population A caught a side at 0 viruses in 18 of 4,589 samples (0.4%) at the
# registered 20 s cadence, which is why the match-1 winner (E1) is not
# adjudicable from the banked artifacts. This runs the identical code path at a
# faster cadence and reports the achieved rate.
set -u
HERE="$(cd "$(dirname "$0")" && pwd)"
SILEVAL_LIB_ONLY=1 . "$HERE/sileval_ab.sh"
for seed in 27875 62371 23031; do
  note "probe seed=$seed cadence=${SAMPLE_SECS}s cycle=${CYCLE_SECS}s"
  run_arm "$seed" ship
done
