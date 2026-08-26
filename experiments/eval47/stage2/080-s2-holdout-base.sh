#!/bin/bash
# STAGE-2 PRIMARY-ENDPOINT BASELINE: the champion (base arm, ws=20) under the
# dr. lulu fitted pressure on the 3,000 ROLLOUT seeds 20000..22999.
#
# WHY THIS IS QUEUED NOW, BEFORE ANY MODEL EXISTS (house law "queue the next job
# STRUCTURALLY"): PREREG_STAGE2.md sec 6.3 fixes the primary endpoint as a
# PAIRED rollout, base vs treatment, on N=3,000 seeds drawn from a range
# DISJOINT from every corpus seed (corpus seeds are 2..12001). The base half of
# that pair does not depend on the model at all, so computing it now costs
# nothing that would otherwise be spent and removes ~1.4 h from the critical
# path once a candidate term exists. If no candidate ever clears the offline
# gates, this is simply an extra 3,000-game lulu census on fresh seeds -- still
# a useful artifact, never a wasted one.
#
# It also serves as the rollout IDENTITY GATE reference: the treatment run's
# base arm must reproduce these rows exactly, or the rollout is void.
#
# Queued strictly BEHIND 060-pressured-census-4.sh and 070-s2-corpus.sh.
set -eu

J=/home/struktured/projects/dr-mario-qa-wt/experiments/eval47/jointdig
PY=/root/drm/venv/bin/python
OUT=results_hetzner/s2_holdout_base.jsonl

cd "$J"
echo "S2-HOLDOUT-BASE START $(date -Is)"
echo "host: $(hostname)  cores: $(nproc)  load: $(cut -d' ' -f1-3 /proc/loadavg)"
echo "python procs (ps, not pgrep): $(ps -e -o comm= | grep -c '^python' || true)"

# OFF-identity gate: p0_ab's own selftest proves the harness still reproduces
# pressure_rig.play() on both models, incl. a killed mutant. If it drifted, this
# exits non-zero and `set -e` fails the job rather than banking bad rows.
$PY p0_ab.py --selftest

# p0_ab.py appends and resumes on (arm, model, seed), so a restart cannot
# duplicate rows; the append is the only shared file and it is line-buffered
# with an explicit flush per row.
$PY p0_ab.py --arm base --model lulu --seed-start 20000 --seed-count 3000 \
    --workers 4 --out "$OUT"

echo "rows: $(wc -l < "$OUT")"
$PY - <<'EOF'
import json, collections
p = "results_hetzner/s2_holdout_base.jsonl"
rows = [json.loads(l) for l in open(p)]
c = collections.Counter(r["res"] for r in rows)
da = sum(r["dies_ahead"] for r in rows)
n = len(rows)
print(f"n={n} {dict(c)} clear_rate={c['clear']/n:.4%} dies_ahead={da} ({da/n:.4%})")
print("seed range:", min(r['seed'] for r in rows), "..", max(r['seed'] for r in rows))
assert len(set(r['seed'] for r in rows)) == n, "DUPLICATE SEEDS"
EOF
echo "S2-HOLDOUT-BASE DONE $(date -Is)"
