#!/usr/bin/env bash
# Block until a Quartus flow has actually produced its ARTIFACTS, then print the verdict.
#
# WHY: waiting on a log SUBSTRING kept firing early or not at all -- three misses across
# two agents. `Fitter was successful` appears while the assembler and timing analyzer are
# still running, so the summaries you then read are the PREVIOUS build's; and a condition
# with a typo (or ERE `\|`, which is not alternation) silently never matches and looks
# exactly like "still running".
#
# The artifact is the truth: wait for NES.sta.summary to be NEWER than the flow's start
# marker, which is only true once this flow's timing analysis has written it. Failure is
# covered too -- a fit that dies never updates the summary, so the explicit error scan
# below is what ends the wait in that case.
#
# Usage: wait_fit.sh <flow.log> [fork-dir] [timeout-seconds]
set -uo pipefail
LOG="${1:?usage: wait_fit.sh <flow.log> [fork-dir] [timeout-s]}"
FORK="${2:-/home/struktured/projects/NES_MiSTer-winner}"
LIMIT="${3:-5400}"
STA="$FORK/output_files/NES.sta.summary"
FIT="$FORK/output_files/NES.fit.summary"

[ -f "$LOG" ] || { echo "no such log: $LOG" >&2; exit 65; }
start=$(date -r "$LOG" +%s)          # the flow log is created when the flow starts
t0=$(date +%s)

while :; do
  # hard failures end the wait immediately -- these never produce fresh summaries
  if command grep -qa "Can't fit design\|Error (293001)\|Fitter requires" "$LOG"; then
    echo "FLOW FAILED:"
    command grep -a -E "Fitter requires|Can't fit design|Error \(293001\)" "$LOG" | head -3
    exit 2
  fi
  if [ -f "$STA" ] && [ "$(date -r "$STA" +%s)" -gt "$start" ]; then
    break
  fi
  now=$(date +%s)
  if [ $((now - t0)) -gt "$LIMIT" ]; then
    echo "TIMED OUT after ${LIMIT}s -- flow still running or stuck" >&2
    exit 3
  fi
  sleep 30
done

echo "artifacts fresh:"
echo "  $(command grep 'Fitter Status' "$FIT")"
exec "$(dirname "$0")/fit_verdict.sh" "$FORK"
