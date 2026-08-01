#!/usr/bin/env bash
# Wait for a POCKET flow to really finish, then score it mechanically.
#
# ⚠ WHY THIS EXISTS AS A SCRIPT AND NOT AS A GREP I RETYPE. On 2026-08-01 I waited on
# `Quartus Prime Shell was successful` in the flow log and got a completion notification
# ~2 minutes into a ~45-minute compile. That banner is printed by EVERY stage of
# `--flow compile` (Analysis & Synthesis, Fitter, Assembler, Timing Analyzer each run their
# own quartus_sh), so the first match means "synthesis finished", not "the build finished".
# This is the same defect the MiSTer `wait_fit.sh` was written for, and knowing the rule did
# not stop me from re-implementing the bug by hand. So the rule lives in a file now.
#
# WAIT ON THE ARTIFACT: block until nes_pocket.sta.summary is NEWER than the flow-log start,
# with an explicit failure scan so a dead flow ends the wait instead of hanging forever.
#
# The MiSTer fit_verdict.sh cannot be reused: it hardcodes 41,910 ALMs and greps the
# `emu|pll ... counter[0]` clock. The Pocket is a different part (18,480 ALMs) and its copro
# rides outclk_4. Reusing it would have produced a confident number about the wrong silicon.
#
#   pocket_fit_verdict.sh <project-dir> [flow.log]
set -uo pipefail
PROJ=${1:?usage: pocket_fit_verdict.sh <project-dir> [flow.log]}
LOG=${2:-}
OUT="$PROJ/output_files"
FIT="$OUT/nes_pocket.fit.summary"
STA="$OUT/nes_pocket.sta.summary"
SOF="$OUT/nes_pocket.sof"

CAPACITY=18480
FLOOR=200          # Pocket ships at 94-97% full; a floor of 1500 is not meaningful here.
                   # This is "did it land at all with a little room", not the MiSTer bar.

# ---- wait on the artifact, not on a log substring -----------------------------------
if [ -n "$LOG" ] && [ -f "$LOG" ]; then
  START=$(stat -c %Y "$LOG")
  echo "waiting for $STA to be newer than the flow log start ($(date -d @"$START" '+%H:%M:%S'))"
  while :; do
    if [ -f "$STA" ] && [ "$(stat -c %Y "$STA")" -gt "$START" ]; then break; fi
    if command grep -qaE "Can't fit|Fitter requires|Error \(29300[0-9]\)|Error: Quartus" "$LOG"; then
      echo "FLOW FAILED -- fitter could not place the design:" >&2
      command grep -aE "Can't fit|Fitter requires|Error \(" "$LOG" | head -8 >&2
      exit 70
    fi
    if ! pgrep -f '[q]uartus' >/dev/null; then
      sleep 5   # let a final write land
      if [ -f "$STA" ] && [ "$(stat -c %Y "$STA")" -gt "$START" ]; then break; fi
      echo "no Quartus process and no fresh $STA -- flow died without a verdict" >&2
      exit 71
    fi
    sleep 30
  done
fi

for f in "$FIT" "$STA"; do
  [ -f "$f" ] || { echo "missing $f" >&2; exit 65; }
done

# ---- STA freshness: a slack from a report older than the artifact is not a number -----
if [ -f "$SOF" ]; then
  for f in "$FIT" "$STA"; do
    if [ "$f" -ot "$SOF" ]; then
      echo "VERDICT: UNKNOWN -- $(basename "$f") is OLDER than the .sof." >&2
      echo "  That report describes a different compile. Refusing to quote numbers." >&2
      exit 66
    fi
  done
fi

used=$(command grep -E "Logic utilization" "$FIT" | command grep -oE "[0-9,]+ / " | head -1 | tr -d ' ,/')
status=$(command grep -E "Fitter Status" "$FIT" | cut -d: -f2- | sed 's/^ *//')
free=$((CAPACITY - used))
# Pocket copro rides outclk_4 (54.669 MHz, its own async group per core_constraints.sdc)
copro=$(awk '/Type  : Setup/ && /counter\[4\]/ {f=1;next} f&&/Slack/{print $3;exit}' "$STA")
worst=$(awk '/Type  : Setup/ {f=1;next} f&&/Slack/{print $3;exit}' "$STA")

echo "Fitter status : $status"
printf "ALMs          : %s / %s  (%s free)\n" "$used" "$CAPACITY" "$free"
printf "copro slack   : %s ns (outclk_4)\n" "${copro:-<not found>}"
printf "worst setup   : %s ns (any domain)\n" "${worst:-<not found>}"
echo
pass=1
[ -n "$used" ] && [ "$free" -ge "$FLOOR" ] || { echo "FAIL: only $free ALMs free (floor $FLOOR)"; pass=0; }
if [ -n "${copro:-}" ]; then
  [ "$(awk -v s="$copro" 'BEGIN{print (s>0)?1:0}')" = 1 ] || { echo "FAIL: copro slack $copro <= 0"; pass=0; }
fi
case "$status" in *Successful*) ;; *) echo "FAIL: fitter status is '$status'"; pass=0;; esac

if [ "$pass" = 1 ]; then
  echo "POCKET TRIAL FIT: LANDED -- the chain engine fits this part on this seed."
  echo "  NOT a ship verdict: seed variance across archived Pocket fits spans ~628 ALMs,"
  echo "  so confirm on the shipping seed before anyone stages an .rbf."
else
  echo "POCKET TRIAL FIT: NO -- see the failing criterion above."
fi
exit $((1 - pass))
