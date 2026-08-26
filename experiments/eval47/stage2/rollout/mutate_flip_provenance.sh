#!/bin/bash
# KILLED-MUTANT EVIDENCE for test_flip_provenance.py.
#
# The gate is only worth anything if it goes RED on a broken logger.  This
# script mutates arm_lut.py one defect at a time, runs the gate, and records
# whether it failed.  Every mutant MUST fail; the clean tree MUST pass.
# arm_lut.py is restored from git after each mutant.
set -u
cd "$(dirname "$0")"
PY=/home/struktured/projects/dr_mario_rl/tmp/venv/bin/python
SRC=arm_lut.py
OUT=../../../../tmp/mutants
mkdir -p "$OUT"

# Snapshot the CURRENT working file, not git HEAD: the provenance work may be
# uncommitted, and `git checkout --` would silently delete it (it did once).
SNAP="$OUT/arm_lut.snapshot.py"
cp "$SRC" "$SNAP"
restore() { cp "$SNAP" "$SRC"; }
trap restore EXIT

run_case() {   # name  expect(pass|fail)
  local name=$1 expect=$2
  "$PY" test_flip_provenance.py > "$OUT/$name.log" 2>&1
  local rc=$?
  local got; [ $rc -eq 0 ] && got=pass || got=fail
  local which; [ "$got" = "$expect" ] && which=OK || which="WRONG"
  echo "$name: expected=$expect got=$got  [$which]  (rc=$rc)"
  [ "$got" = "$expect" ]
}

mutate() {     # python-expression-free sed replacement
  restore
  "$PY" - "$1" "$2" <<'EOF'
import sys, io
old, new = sys.argv[1], sys.argv[2]
s = io.open("arm_lut.py", encoding="utf-8").read()
assert s.count(old) == 1, f"anchor not unique ({s.count(old)}): {old!r}"
io.open("arm_lut.py", "w", encoding="utf-8").write(s.replace(old, new))
EOF
}

fails=0
echo "=== CLEAN TREE (control: the gate must PASS, or nothing below means anything)"
restore
run_case clean pass || fails=$((fails+1))

echo
echo "=== MUTANTS (each must turn the gate RED)"

mutate '        if a != base_a:
            self.stats["flips"] += 1
            if self.provenance:' \
       '        if a != base_a:
            self.stats["flips"] += 1
        if True:
            if self.provenance:'
run_case M1_log_every_ply fail || fails=$((fails+1))

mutate '"ply": int(self.stats["plies"]) - 1,' '"ply": int(self.stats["plies"]),'
run_case M2_ply_off_by_one fail || fails=$((fails+1))

mutate '"base_action": int(base_a),
                "trt_action": int(a),' \
       '"base_action": int(a),
                "trt_action": int(base_a),'
run_case M3_swap_base_trt fail || fails=$((fails+1))

mutate '"maxh": int(H.max()),' '"maxh": int(H.min()),'
run_case M4_maxh_wrong_stat fail || fails=$((fails+1))

# d_spawn_h is the spawn-lane sensor. Cols 3/4 are the spawn columns; 0/1
# are not. This mutant proves that the independent board scan catches drift.
mutate '"d_spawn_h": max(int(H[3]), int(H[4])),' \
       '"d_spawn_h": max(int(H[0]), int(H[1])),'
run_case M8_d_spawn_h_wrong_cols fail || fails=$((fails+1))

mutate '"viruses": int(np.count_nonzero(vir)),' '"viruses": int(np.count_nonzero(col)),'
run_case M5_viruses_wrong_plane fail || fails=$((fails+1))

mutate '        r["t_to_end"] = n_plies - 1 - r["ply"]' \
       '        r["t_to_end"] = r["ply"]'
run_case M6_t_to_end_not_remaining fail || fails=$((fails+1))

mutate '"champ_rank_chosen": rank,' '"champ_rank_chosen": 0,'
run_case M7_rank_constant fail || fails=$((fails+1))

restore
echo
echo "=== FINAL: re-run the clean tree to prove the restore worked"
run_case clean_after pass || fails=$((fails+1))

echo
if [ $fails -eq 0 ]; then echo "MUTATION GATE: ALL OK"; else echo "MUTATION GATE: $fails WRONG"; fi
exit $fails
