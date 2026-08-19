#!/bin/bash
# Killed-mutant driver for analyze_shadowlat.py's h_hit == -1 handling (#124 fallout).
#
# The gate standard: a check is only a check if it FAILS on wrong code. Each mutant
# below is a plausible wrong implementation (M1/M2 are the ACTUAL pre-fix code); the
# driver requires test_lat_conversion.py to exit non-zero on every one, and zero on
# the parent.
#
# Self-contained: paths derive from this file's own location (repro-19 rule), and the
# interpreter is $PY or whatever python3 is on PATH.
set -u
CF=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
PY=${PY:-python3}
WORKROOT=${TMPDIR:-$CF/../../tmp}          # repo tmp/ (gitignored) unless TMPDIR is set
mkdir -p "$WORKROOT" || exit 1
WORK=$(mktemp -d "$WORKROOT/shadowlat_mut.XXXXXX")
SRC=$CF/analyze_shadowlat.py
fails=0

run_case () { # name want_rc file
  local name=$1 want=$2 f=$3
  LAT_MODULE="$f" $PY "$CF/test_lat_conversion.py" >"$WORK/$name.log" 2>&1
  local rc=$?
  if [ "$want" = "nonzero" ] && [ $rc -ne 0 ]; then
    echo "  KILLED  $name (rc=$rc)"
  elif [ "$want" = "zero" ] && [ $rc -eq 0 ]; then
    echo "  ok      $name (rc=0)"
  else
    echo "  SURVIVED/BROKEN  $name (rc=$rc, wanted $want) -- see $WORK/$name.log"
    fails=$((fails + 1))
  fi
}

mut () { # name  python-mutation-applied-to-$WORK/$name.py
  local name=$1; shift
  cp "$SRC" "$WORK/$name.py"
  $PY - "$WORK/$name.py" "$@" <<'EOF'
import sys
path, old, new = sys.argv[1], sys.argv[2], sys.argv[3]
s = open(path).read()
assert s.count(old) == 1, f"mutation anchor not unique/found: {old!r}"
open(path, "w").write(s.replace(old, new))
EOF
  [ $? -ne 0 ] && { echo "  MUTATION FAILED TO APPLY: $name"; fails=$((fails + 1)); return; }
  run_case "$name" nonzero "$WORK/$name.py"
}

echo "parent (must pass):"
run_case parent zero "$SRC"

echo "mutants (must all be killed):"
# M1: the shipped defect -- no guard, so -1 silently becomes 264+16 = 280 f.
mut M1_no_guard \
  '    if h_hit < 0:
        raise ValueError(' \
  '    if False:
        raise ValueError('
# M2: the full pre-fix behaviour -- unscorable releases scored against the bogus window.
cp "$SRC" "$WORK/M2_prefix.py"
$PY - "$WORK/M2_prefix.py" <<'EOF'
import sys
p = sys.argv[1]; s = open(p).read()
s = s.replace("    if h_hit < 0:\n        raise ValueError(",
              "    if False:\n        raise ValueError(", 1)
s = s.replace("                if h_hit < 0:\n", "                if False:\n", 1)
open(p, "w").write(s)
EOF
run_case M2_prefix nonzero "$WORK/M2_prefix.py"
# M3: unscorable releases dropped from the release denominator (silently absent).
mut M3_drop_from_denominator \
  '            if post_garbage:' \
  '            if post_garbage and h_hit >= 0:'
# M4: the counter exists but is never incremented (invisible skips).
mut M4_dead_counter \
  '                    out["n_window_unscorable"] += 1' \
  '                    out["n_window_unscorable"] += 0'
# M5: per-band counter dead (aggregate right, bands wrong).
mut M5_dead_band_counter \
  '                    b["n_window_unscorable"] += 1' \
  '                    b["n_window_unscorable"] += 0'
# M6: window base bumped to the bogus 280 the old -1 path produced.
mut M6_base_280 \
  'GARBAGE_WINDOW_BASE = 264' \
  'GARBAGE_WINDOW_BASE = 280'
# --- by_h_hit table (#136) -------------------------------------------------------
# M7: THE #124 CONFLATION ITSELF -- key the per-h table on max_h, the variable the
# BANDS use, instead of h_hit, the variable the window is set by. This is the exact
# substitution that produced the stale pilot, so the gate has to be able to see it.
mut M7_key_on_max_h \
  '                    e = by_h.setdefault(
                        h_hit,' \
  '                    e = by_h.setdefault(
                        max_h,'
# M8: late counted against the fall budget instead of the window inside the table
# (aggregate late_vs_window stays correct, so only the new table can catch it).
mut M8_wrong_budget_in_table \
  '                    for d in per_domain:
                        if fr[d] > win:
                            e["late"][d] += 1' \
  '                    for d in per_domain:
                        if fr[d] > fall_budget_frames(entry_row):
                            e["late"][d] += 1'
# M9: silicon frames written into the table for BOTH domains -- a sim-domain claim
# would then silently quote silicon lateness (the domain trap, table-local).
mut M9_domain_collapse \
  '                    for d in per_domain:
                        if fr[d] > win:
                            e["late"][d] += 1' \
  '                    for d in per_domain:
                        if fr["silicon"] > win:
                            e["late"][d] += 1'
# M10: median replaced by the mean. This was EQUIVALENT on the first two fixture cells
# ({10,80} -> 45 either way; {50,60,70} -> 60 either way), so a skewed cell
# ({10,20,300}: median 20, mean 110) was added to the fixture to make it killable
# rather than dropping it -- an unkillable mutant is a fact about the fixtures.
mut M10_mean_not_median \
  '    return s[m] if n % 2 else 0.5 * (s[m - 1] + s[m])' \
  '    return sum(s) / n'

echo
if [ $fails -ne 0 ]; then
  echo "GATE FAILED: $fails case(s) wrong. work=$WORK"
  exit 1
fi
echo "GATE PASSED: parent green, all mutants killed. work=$WORK"
exit 0
