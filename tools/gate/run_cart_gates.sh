#!/usr/bin/env bash
# Run the three NMI/MMC1 hazard gates -- the safety-critical ones that guard the shipped
# cart's interrupt discipline. Whole suite costs ~1.2 s, so this is cheap enough to run on
# every push.
#
# WHY THIS EXISTS: test_rtivec.py sat RED from v6e (2026-08-10) to 2026-08-18 because its
# RTI assertion was pinned to the pre-v6e shield layout. Nobody noticed: the repo has 62
# test files, no CI, no git hooks, no runner script, and 20 of those 62 need a pytest that
# is not installed on the default python. A gate nothing executes is not a gate.
#
# ABSENCE IS NOT PASS. A missing suite, a missing interpreter or a missing ROM is a FAILURE
# here, never a silent skip -- the batch-void rule from the Mesen launch traps applies just
# as much to a cheap local runner as to an 18k-frame arm.
#
#   tools/gate/run_cart_gates.sh              # uses DRGATE_PY or finds a py65 python
#   DRGATE_PY=/path/to/python tools/gate/...  # pin the interpreter explicitly
#
# Opt in as a pre-push hook (not installed automatically -- shared repo):
#   ln -s ../../tools/gate/run_cart_gates.sh .git/hooks/pre-push
set -u
cd "$(dirname "$0")/../.." || exit 2
REPO=$PWD

# ---- interpreter: py65 is required; there is no fallback that could pass vacuously -------
PY=${DRGATE_PY:-}
if [ -n "$PY" ]; then
  # A PINNED interpreter is validated too. Skipping this check let a py65-less DRGATE_PY
  # through to fail later as three ModuleNotFoundErrors -- still a failure, but it reads as
  # "the gates are broken" instead of "your interpreter is wrong". Found by testing this
  # runner's own failure modes.
  "$PY" -c 'import py65' >/dev/null 2>&1 || {
    echo "FAIL: DRGATE_PY=$PY has no py65 module." >&2
    exit 2; }
fi
if [ -z "$PY" ]; then
  for c in "$REPO/.venv/bin/python" \
           /home/struktured/projects/dr-mario-mods/.venv/bin/python \
           python3; do
    if command -v "$c" >/dev/null 2>&1 && "$c" -c 'import py65' >/dev/null 2>&1; then
      PY=$c; break
    fi
  done
fi
if [ -z "$PY" ]; then
  echo "FAIL: no python with py65 found. Set DRGATE_PY=/path/to/python." >&2
  echo "      (Refusing to run: a gate that cannot execute must not report success.)" >&2
  exit 2
fi

# ---- the base ROM the emitter patches; untracked, so check it explicitly -----------------
BASE=$REPO/drmario_v28cs.nes
BASE_MD5=7d307c3051ebc0f8a10e259e3c270acb
if [ ! -f "$BASE" ]; then
  echo "FAIL: $BASE missing (untracked). Copy it in; the emitter cannot build without it." >&2
  exit 2
fi
got=$(md5sum "$BASE" | cut -d' ' -f1)
if [ "$got" != "$BASE_MD5" ]; then
  echo "FAIL: base ROM hash moved: got $got want $BASE_MD5" >&2
  echo "      Every recorded manifest is relative to that base -- stop, do not gate." >&2
  exit 2
fi

# ---- the reference carts the A-clobber mutant needs, by CONTENT not by name --------------
SHIP=$REPO/roms/c-v8ship.nes     # must be the CLOBBERED cart -- the mutant side
V6E=$REPO/roms/v6e.nes           # must be the FIXED cart -- the pass side
for f in "$SHIP" "$V6E"; do
  [ -f "$f" ] || { echo "FAIL: $f missing -- test_rtivec_aclobber needs both arms." >&2; exit 2; }
done
[ "$(md5sum "$SHIP" | cut -d' ' -f1)" = 087ff959ac510c613bbbd2eb1ac5ecf3 ] || {
  echo "FAIL: roms/c-v8ship.nes is not 087ff959 -- the mutant arm must be the clobbered cart." >&2
  exit 2; }
[ "$(md5sum "$V6E" | cut -d' ' -f1)" = c0082cb34259007854120d3d4ab9fa27 ] || {
  echo "FAIL: roms/v6e.nes is not c0082cb3 -- the pass arm must be the fixed cart." >&2
  exit 2; }

echo "cart hazard gates  py=$PY  base=$BASE_MD5"
echo "----------------------------------------------------------------------"

rc=0
run() {
  local name=$1; shift
  local f=$REPO/tests/$name.py
  if [ ! -f "$f" ]; then
    printf '%-24s MISSING (counts as FAILURE, not skip)\n' "$name"; rc=1; return
  fi
  local out; out=$("$PY" "$f" "$@" 2>&1); local r=$?
  if [ $r -eq 0 ]; then
    printf '%-24s PASS   %s\n' "$name" "$(printf '%s' "$out" | tail -1)"
  else
    printf '%-24s FAIL (rc=%d)\n' "$name" "$r"
    printf '%s\n' "$out" | tail -20 | sed 's/^/    /'
    rc=1
  fi
}

run test_rtivec
run test_mmc1rst
run test_rtivec_aclobber "$SHIP" "$V6E"
# PRG-RAM map gate (2026-08-20, collision-140): killed mutants for the deriver, incl. the
# two-symbols-one-address check that would have caught FC_STAB/SL_PH sharing $61BB. 0.1 s.
run test_prg_ram_map

echo "----------------------------------------------------------------------"
if [ $rc -eq 0 ]; then echo "cart hazard gates: ALL PASS"; else echo "cart hazard gates: FAILURES ABOVE"; fi
exit $rc
