#!/bin/bash
# prepush_privacy_sweep.sh — MANDATORY before pushing to dr-mario-te (PUBLIC).
# Scans only what the push would ADD, against the private-name list and the
# usual credential shapes. Exits 1 on any hit.
#   usage: bash tools/prepush_privacy_sweep.sh [<remote-ref>]
set -uo pipefail
REF="${1:-origin/distill-m1}"
if [ "${1:-}" = "--self-test" ]; then
  # POSITIVE CONTROL. A sweep that has only ever printed CLEAN is not a sweep.
  t=$(mktemp); trap 'rm -f "$t"' EXIT
  printf '+ghp_AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA\n+played by lulu tonight\n+harmless line\n' > "$t"
  P='ghp_|github_pat_|AKIA|BEGIN [A-Z ]*PRIVATE KEY|xox[baprs]-|@gmail\.com|@strukturedlabs\.com|setenv\.sh'
  c=$(grep -icE "$P" "$t"); l=$(grep -icE '(^|[^r])\blulu\b' "$t")
  n=$(printf '+drlulu cleared this\n+nothing to see\n' | grep -icE "$P|(^|[^r])\blulu\b")
  echo "[self-test] planted credential caught: $c (must be >=1)"
  echo "[self-test] planted bare-lulu caught:  $l (must be >=1)"
  echo "[self-test] clean text stays silent:   $n (must be 0)"
  { [ "$c" -ge 1 ] && [ "$l" -ge 1 ] && [ "$n" -eq 0 ]; } \
    && { echo "[self-test] PASS — the sweep can fire AND can stay quiet"; exit 0; } \
    || { echo "[self-test] *** FAIL ***"; exit 1; }
fi
cd "$(git rev-parse --show-toplevel)"
DIFF=$(git diff "$REF"...HEAD 2>/dev/null | grep '^+' || true)
[ -z "$DIFF" ] && { echo "privacy sweep: nothing to add vs $REF"; exit 0; }
# ⚠ family names are internal-only (privacy-family-names); drlulu is the ONLY
# public name. Credential shapes included because a public push is forever.
PATTERNS='ghp_|github_pat_|AKIA|BEGIN [A-Z ]*PRIVATE KEY|xox[baprs]-|@gmail\.com|@strukturedlabs\.com|setenv\.sh'
hits=$(printf '%s\n' "$DIFF" | grep -inE "$PATTERNS" || true)
# bare 'lulu' not preceded by 'dr' — the modern-edits naming policy
lulu=$(printf '%s\n' "$DIFF" | grep -inE '(^|[^r])\blulu\b' | grep -v 'init_rig' || true)
rc=0
if [ -n "$hits" ]; then echo "⛔ CREDENTIAL/PII PATTERN IN ADDED LINES:"; echo "$hits" | head -20; rc=1; fi
if [ -n "$lulu" ]; then echo "⚠ bare 'lulu' in added PROSE (rig keys excluded) — policy is drlulu:"; echo "$lulu" | head -20; rc=1; fi
[ $rc -eq 0 ] && echo "privacy sweep vs $REF: CLEAN ($(printf '%s\n' "$DIFF" | wc -l) added lines scanned)"
exit $rc
