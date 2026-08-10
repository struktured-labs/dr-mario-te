#!/bin/bash
# STAGE-2 CORPUS `s2lulu`, POPULATION SCALE: per-decision extraction of ALL
# 12,000 lulu-census games (1,686 topout + 738 stall + 9,576 clear), EVERY
# decision of every game.
#
# Pre-registered in experiments/eval47/stage2/PREREG_STAGE2.md @ b9725fc.
# Queued strictly BEHIND 060-pressured-census-4.sh; pending queue was verified
# EMPTY before this file was added, so nothing was displaced.
#
# REMOTE-NODE DISCIPLINE (memory: remote-node-code-skew):
#  * The CODE is hashed and PINNED below. A skewed tree aborts the job instead
#    of silently producing numbers from different code.
#  * The census input is hash-pinned too.
#  * The fidelity gate is RE-RUN ON THIS NODE after the sync -- a gate that only
#    ran on the dev box does not certify this box.
#  * `ps`, never `pgrep -c` (pgrep self-matches).
#  * Outputs are per-run .npz files written whole; the only appended file is the
#    queue runner's own log, which it already holds under flock.
set -eu

S2=/home/struktured/projects/dr-mario-qa-wt/experiments/eval47/stage2
EV=/home/struktured/projects/dr-mario-qa-wt/experiments/eval47
PY=/root/drm/venv/bin/python
CODE_HASH_EXPECT=7b42d55b4ba5a13661a56a59753b8a5fefb8d4cab9a9234f9503f4bc28d94b5e
CENSUS=$EV/jointdig/results_hetzner/lulu_census.jsonl
CENSUS_SHA_EXPECT=886be1fc2e30c4856f583840d34ba4a5372ae4c420a30fdfa38fafe2f525c277

cd "$S2"
echo "S2-CORPUS START $(date -Is)"
echo "host: $(hostname)  cores: $(nproc)  load: $(cut -d' ' -f1-3 /proc/loadavg)"
echo "python procs already running (ps, not pgrep): $(ps -e -o comm= | grep -c '^python' || true)"

# ---- GUARD 1: code skew ----------------------------------------------------
CH=$($PY - <<'EOF'
import hashlib, os
EV = '/home/struktured/projects/dr-mario-qa-wt/experiments/eval47'
h = hashlib.sha256()
for p in (EV + '/stage2/build_s2_corpus.py', EV + '/pressure_rig.py',
          EV + '/bursty_model.py', EV + '/jointdig/p0_ab.py',
          EV + '/results/dr_lulu_20260808_fit.json'):
    h.update(hashlib.sha256(open(p, 'rb').read()).digest())
print(h.hexdigest())
EOF
)
echo "code sha256: $CH"
if [ "$CH" != "$CODE_HASH_EXPECT" ]; then
  echo "ABORT: CODE SKEW -- expected $CODE_HASH_EXPECT"; exit 3
fi

# ---- GUARD 2: census input ------------------------------------------------
CS=$(sha256sum "$CENSUS" | cut -d' ' -f1)
echo "census sha256: $CS  rows: $(wc -l < "$CENSUS")"
if [ "$CS" != "$CENSUS_SHA_EXPECT" ]; then
  echo "ABORT: census input changed -- expected $CENSUS_SHA_EXPECT"; exit 4
fi

# ---- GUARD 3: re-earn the fidelity gate ON THIS NODE ------------------------
# 24 seeds must reproduce the census row AND the real rig's trace-derived
# fields, and all three mutants (ws=0 / garbage-rng+1 / tie-break flip) must
# BREAK it. build_s2_corpus.py exits non-zero if any of that fails, and `set -e`
# turns that into a FAILED job rather than a corpus nobody checked.
$PY build_s2_corpus.py --gate-only --workers 4 --tag hetzner

# ---- the corpus ------------------------------------------------------------
# --ctrl-sample 0 = ALL 9,576 cleared games (the local half sampled 1,700).
# ~12,000 games at ~0.58 g/s = ~5.7 h.
$PY build_s2_corpus.py --run --workers 4 --ctrl-sample 0 --tag hetzner

echo "S2-CORPUS DONE $(date -Is)"
ls -la "$S2/results"
