#!/bin/bash
# Clean-clone reproducibility gate for the certified H12 endpoint champion (#19).
#
# Clones this repository into tmp/, builds a venv from tools/requirements-oracle.txt,
# and verifies the sealed H12 runtime manifest reproduces EXACTLY inside the clone,
# with every module resolved from the clone rather than from a sibling worktree.
#
#   tools/gate_clean_clone.sh              # the gate
#   tools/gate_clean_clone.sh --mutants    # the gate, then 4 mutants that MUST fail
#
# Nothing outside tmp/ is written, and no sealed out/ tree is touched.
set -uo pipefail

REPO=$(cd "$(dirname "$(readlink -f "$0")")/.." && pwd)
BRANCH=${DRM_GATE_BRANCH:-$(git -C "$REPO" rev-parse --abbrev-ref HEAD)}
WORK=$REPO/tmp/clean-clone-gate
CLONE=$WORK/clone
VENV=$WORK/venv
GATE=experiments/eval47/stage2/oracle/gate_h12_clean_clone.py
MUTANTS=0
[[ "${1:-}" == "--mutants" ]] && MUTANTS=1

rm -rf "$WORK"
mkdir -p "$WORK"

echo "=== clone $BRANCH -> $CLONE"
git clone --quiet --branch "$BRANCH" --single-branch "$REPO" "$CLONE" || exit 3
echo "clone HEAD: $(git -C "$CLONE" rev-parse --short HEAD)"

echo "=== venv from tools/requirements-oracle.txt"
uv venv --quiet --python 3.12 "$VENV" || exit 3
VIRTUAL_ENV=$VENV uv pip install --quiet -r "$CLONE/tools/requirements-oracle.txt" || exit 3
PY=$VENV/bin/python

# A stale PYTHONPATH (run_gates.sh exports one) would defeat the whole point.
unset PYTHONPATH
export NUMBA_CACHE_DIR=$WORK/numba-cache
mkdir -p "$NUMBA_CACHE_DIR"

echo
echo "=== GATE (expect PASS, exit 0)"
out=$(cd "$CLONE" && "$PY" "$GATE" 2>&1); rc=$?
echo "$out"
echo "exit=$rc"
if [[ $rc -ne 0 ]]; then
  echo
  echo "CLEAN-CLONE GATE: FAIL (the clone cannot reproduce the sealed H12 manifest)"
  exit 1
fi

[[ $MUTANTS -eq 0 ]] && { echo; echo "CLEAN-CLONE GATE: PASS"; exit 0; }

# ---- killed-mutant standard: the gate must go RED on wrong inputs ----------
# Each mutant names the file it damaged; the gate must exit non-zero AND say so.
fails=0
mutant() {  # mutant <name> <path-that-must-be-named> <shell-damage>
  local name=$1 needle=$2 damage=$3
  git -C "$CLONE" checkout --quiet -- . && git -C "$CLONE" clean --quiet -fd
  ( cd "$CLONE" && eval "$damage" )
  local o r
  o=$(cd "$CLONE" && "$PY" "$GATE" 2>&1); r=$?
  local named=no; grep -qF -- "$needle" <<<"$o" && named=yes
  echo "--- mutant $name: exit=$r names_file=$named"
  grep -E "FAIL|MISSING|MISMATCH|CLEAN-CLONE" <<<"$o" | head -4
  if [[ $r -eq 0 || $named != yes ]]; then
    echo "    *** MUTANT SURVIVED - the gate is vacuous for this fault ***"
    fails=$((fails + 1))
  fi
}

echo
echo "=== MUTANTS (each MUST fail, naming the damaged file)"

# M1: the exact task-#19 defect - the dr. lulu fit missing from the clone.
mutant M1_delete_dr_lulu_fit "experiments/eval47/results/dr_lulu_20260808_fit.json" \
  "rm -f experiments/eval47/results/dr_lulu_20260808_fit.json"

# M2: a vendored module missing - the unpushed faithful_game.py case.
mutant M2_delete_faithful_game "experiments/vendor/drmario/faithful_game.py" \
  "rm -f experiments/vendor/drmario/faithful_game.py"

# M3: present but altered. Proves the gate checks CONTENT, not existence.
mutant M3_corrupt_vendored_fb "experiments/vendor/fb.py" \
  "printf '\n# corrupted by the mutant\n' >> experiments/vendor/fb.py"

# M4: the realistic import race. experiments/nes_pills.py is a DIFFERENT module
# with the same name; the sealed run used the tmp/pillrng one now vendored here.
# Swapping them is exactly the fault a name-based sys.path resolution makes, and
# it is the mutant an existence check cannot kill.
mutant M4_swap_nes_pills "nes_pills" \
  "cp experiments/nes_pills.py experiments/vendor/nes_pills.py"

git -C "$CLONE" checkout --quiet -- . && git -C "$CLONE" clean --quiet -fd

echo
if [[ $fails -eq 0 ]]; then
  echo "CLEAN-CLONE GATE: PASS (4/4 mutants killed)"
  exit 0
fi
echo "CLEAN-CLONE GATE: UNSOUND ($fails mutant(s) survived)"
exit 2
