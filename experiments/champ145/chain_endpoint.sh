#!/bin/bash
# champion-145 H14 ENDPOINT chain (PREREG_H14 + AMENDMENT 1).
# Usage: chain_endpoint.sh <WORKERS> <EPS>
# Stages, each gated on the previous stage's success MARKER:
#   G1 identity  : trt(eps=0) == base on 8 consumed seeds at L20 (true label)
#   G2 not-inert : trt(eps=EPS) tie_plies must EXCEED eps=0's on the same seeds
#   E1 true arm  : N=600 registered seeds, label=true
#   E2 mutant    : same seeds, label=shuffle (dose-matched null); auto re-run
#                  with null thinning if the FULL-N flip-RATE ratio is outside
#                  [0.9,1.1] (the H12 dose-saga rule: anchor on rates)
#   A  verdict   : analyse_h14.py (self-gated) with dose anchor + mutant check
set -eo pipefail
cd "$(dirname "$(readlink -f "$0")")"
PY=${DRM_PY:-/home/struktured/projects/dr_mario_rl/tmp/venv/bin/python}
ORACLE="$PWD/../eval47/stage2/oracle"
export NUMBA_CACHE_DIR=/home/struktured/projects/dr-mario-champ145-wt/tmp/numba-cache
mkdir -p "$NUMBA_CACHE_DIR"
export PYTHONPATH="$ORACLE/bootstrap:/home/struktured/projects/dr-mario-qa-wt/experiments"

W=${1:-12}
EPS=${2:?EPS required (AMENDMENT 1 rule applied to the final screen)}
OUT="$PWD/out/endpoint"
mkdir -p "$OUT"

# registered seed material: exclusion list + startup asserts
"$PY" - <<PYEOF 2>&1 | tee "$OUT/seedlist.log"
excl = {53239, 54149, 54311, 54593, 55511, 55789, 56331, 56561, 56585, 57129,
        57245, 57431, 57773, 58007, 58253, 58403, 58427, 58957, 59115, 59937}
seeds = [s for s in range(53100, 60000) if s not in excl][:600]
assert len(seeds) == 600, len(seeds)              # startup assert: list length
assert not excl.intersection(seeds)
assert all(53100 <= s <= 59999 for s in seeds)
open("$OUT/excl.txt", "w").write("\n".join(map(str, sorted(excl))) + "\n")
print("SEEDLIST_OK", len(seeds), seeds[0], seeds[-1])
PYEOF
command grep -aq 'SEEDLIST_OK 600' "$OUT/seedlist.log"

cd "$ORACLE"

# ---- G1 identity (consumed seeds 30000-30007; NOT endpoint data)
"$PY" run_h14.py --seed-start 30000 --seed-count 8 --workers "$W" \
  --label true --future dist --fork-samples 5 --level 20 --max-pills 400 \
  --trt-trigger-eps 0.0 \
  --outdir "$OUT/g1_identity" 2>&1 | tee "$OUT/g1.log"
"$PY" - <<PYEOF 2>&1 | tee "$OUT/g1_gate.log"
import json
rows = [json.loads(l) for l in open("$OUT/g1_identity/seg_030000.jsonl")]
assert len(rows) == 8, len(rows)
bad = [r["seed"] for r in rows
       if not (r["base"]["res"] == r["trt"]["res"]
               and r["base"]["pills"] == r["trt"]["pills"]
               and r["base"]["flips"] == r["trt"]["flips"])]
assert not bad, ("G1 IDENTITY FAIL", bad)
print("G1_IDENTITY_OK")
PYEOF
command grep -aq 'G1_IDENTITY_OK' "$OUT/g1_gate.log"

# ---- G2 not-inert
"$PY" run_h14.py --seed-start 30000 --seed-count 8 --workers "$W" \
  --label true --future dist --fork-samples 5 --level 20 --max-pills 400 \
  --trt-trigger-eps "$EPS" \
  --outdir "$OUT/g2_notinert" 2>&1 | tee "$OUT/g2.log"
"$PY" - <<PYEOF 2>&1 | tee "$OUT/g2_gate.log"
import json
r0 = [json.loads(l) for l in open("$OUT/g1_identity/seg_030000.jsonl")]
r1 = [json.loads(l) for l in open("$OUT/g2_notinert/seg_030000.jsonl")]
t0 = sum(x["trt"].get("tie_plies", 0) for x in r0)
t1 = sum(x["trt"].get("tie_plies", 0) for x in r1)
assert t1 > t0, ("G2 NOT-INERT FAIL", t0, t1)
print("G2_NOTINERT_OK", t0, "->", t1)
PYEOF
command grep -aq 'G2_NOTINERT_OK' "$OUT/g2_gate.log"

# ---- E1 true arm (THE ENDPOINT)
"$PY" run_h14.py --seed-start 53100 --seed-count 6900 --workers "$W" \
  --exclude-file "$OUT/excl.txt" --limit-eligible 600 \
  --label true --future dist --fork-samples 5 --level 20 --max-pills 400 \
  --trt-trigger-eps "$EPS" \
  --outdir "$OUT/e1_true" 2>&1 | tee "$OUT/e1.log"
command grep -aq 'DONE' "$OUT/e1.log"

# ---- E2 mutant, unthinned first
"$PY" run_h14.py --seed-start 53100 --seed-count 6900 --workers "$W" \
  --exclude-file "$OUT/excl.txt" --limit-eligible 600 \
  --label shuffle --future dist --fork-samples 5 --level 20 --max-pills 400 \
  --trt-trigger-eps "$EPS" \
  --outdir "$OUT/e2_mutant" 2>&1 | tee "$OUT/e2.log"
command grep -aq 'DONE' "$OUT/e2.log"

# ---- dose anchor on FULL-N rates; auto-thin + re-run if out of band
"$PY" - <<PYEOF 2>&1 | tee "$OUT/dose.log"
import json, os, glob
def rate(d):
    fl = pl = 0
    for fn in glob.glob(os.path.join(d, "seg_*.jsonl")):
        for ln in open(fn):
            r = json.loads(ln)
            fl += r["trt"]["flips"]; pl += r["trt"]["plies_scored"]
    return fl / max(1, pl)
rt, rm = rate("$OUT/e1_true"), rate("$OUT/e2_mutant")
ratio = rm / rt if rt else 0.0
print(f"true_rate={rt:.5f} mutant_rate={rm:.5f} ratio={ratio:.4f}")
if 0.9 <= ratio <= 1.1:
    print("DOSE_IN_BAND")
else:
    keep = rt / rm if rm else 0.0
    num = max(1, round(keep * 1000))
    print(f"DOSE_OUT_OF_BAND keep={keep:.4f} num={num} den=1000")
PYEOF
if command grep -aq 'DOSE_OUT_OF_BAND' "$OUT/dose.log"; then
  NUM=$(command grep -a 'DOSE_OUT_OF_BAND' "$OUT/dose.log" | sed 's/.*num=\([0-9]*\).*/\1/')
  "$PY" run_h14.py --seed-start 53100 --seed-count 6900 --workers "$W" \
    --exclude-file "$OUT/excl.txt" --limit-eligible 600 \
    --label shuffle --future dist --fork-samples 5 --level 20 --max-pills 400 \
    --trt-trigger-eps "$EPS" --null-keep-num "$NUM" --null-keep-den 1000 \
    --outdir "$OUT/e2b_mutant" 2>&1 | tee "$OUT/e2b.log"
  command grep -aq 'DONE' "$OUT/e2b.log"
  MUT="$OUT/e2b_mutant"
else
  MUT="$OUT/e2_mutant"
fi

# ---- A verdict
"$PY" analyse_h14.py --true-dir "$OUT/e1_true" --mutant-dir "$MUT" \
  2>&1 | tee "$OUT/verdict.log"
command grep -aq 'ANALYSE_H14_OK' "$OUT/verdict.log"

echo ENDPOINT_CHAIN_OK
