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

CAPACITY=18480
FLOOR=200          # Pocket ships at 94-97% full; a floor of 1500 is not meaningful here.
                   # This is "did it land at all with a little room", not the MiSTer bar.

# ---- wait for the flow to END, then let the freshness gate judge ---------------------
#
# ⚠ The first version waited for $STA to become "newer than the flow log start", taking the
# start as `stat -c %Y $LOG`. That is not the flow's start -- the log is appended for the
# whole run, so its mtime is NOW. Launch the waiter late and the deadline is already in the
# future of the artifact, so the condition can never become true; it fell through to the
# no-process branch and reported "flow died without a verdict" on a build that had just
# SUCCEEDED (17,774 ALMs, Fitter Successful).
#
# Waiting and judging are separate jobs and I had conflated them. Waiting only needs to know
# the flow is over; whether the artifacts describe THIS build is the freshness gate's job,
# and it decides that from the design inputs, which is a fact about content rather than a
# race against the clock. So: wait for Quartus to be gone (we run flows serially), then scan
# for failure, then hand off.
if [ -n "$LOG" ] && [ -f "$LOG" ]; then
  echo "waiting for the flow to finish..."
  while pgrep -f '[q]uartus' >/dev/null; do
    if command grep -qaE "Can't fit|Fitter requires|Error \(29300[0-9]\)" "$LOG"; then
      echo "FLOW FAILED -- fitter could not place the design:" >&2
      command grep -aE "Can't fit|Fitter requires|Error \(" "$LOG" | head -8 >&2
      exit 70
    fi
    sleep 30
  done
  sleep 3          # let the last write land
  if command grep -qaE "Can't fit|Fitter requires|Error \(29300[0-9]\)" "$LOG"; then
    echo "FLOW FAILED -- fitter could not place the design:" >&2
    command grep -aE "Can't fit|Fitter requires|Error \(" "$LOG" | head -8 >&2
    exit 70
  fi
fi

for f in "$FIT" "$STA"; do
  [ -f "$f" ] || { echo "missing $f" >&2; exit 65; }
done

# ---- FRESHNESS: reports must post-date the newest DESIGN INPUT, plus flow ordering -----
#
# ⚠ The first version of this block compared the reports against the .sof and was WRONG BY
# CONSTRUCTION -- the flow order is
#     Analysis & Synthesis -> Fitter (writes fit.*) -> Assembler (writes .sof) -> STA
# so fit.summary is ALWAYS older than the .sof in a perfectly honest compile. I shipped that
# version and it would have fired UNKNOWN on the very build it was written to judge.
# Spectator hit and fixed the identical bug in fit_verdict.sh (160ecaf); this is their rule,
# adopted. A gate that rejects only CORRECT builds teaches you to ignore it -- worse than
# no gate at all.
#
# The mechanism the original incident actually had: a design input changed and the stage
# that consumes it did not re-run, so its report PREDATES that input. Assert exactly that,
# plus ordering between the reports. Both hold for an honest run at any speed.
COPRO="$PROJ/../target/pocket/vendor/copro"
NEWEST_IN=$(ls -t "$COPRO/copro_rom.hex" "$COPRO/CoproDrMario.sv" "$COPRO/LeafEval.sv" \
            2>/dev/null | head -1)
if [ -n "$NEWEST_IN" ]; then
  for f in "$FIT" "$STA"; do
    if [ "$f" -ot "$NEWEST_IN" ]; then
      echo "VERDICT: UNKNOWN -- $(basename "$f") PREDATES $(basename "$NEWEST_IN")." >&2
      echo "  The stage consuming that input did not re-run; the report describes a" >&2
      echo "  different compile. Refusing to quote slack or utilisation." >&2
      exit 66
    fi
  done
fi
if [ "$STA" -ot "$FIT" ]; then
  echo "VERDICT: UNKNOWN -- the timing report predates the fitter report; flow order broken." >&2
  exit 66
fi

used=$(command grep -E "Logic utilization" "$FIT" | command grep -oE "[0-9,]+ / " | head -1 | tr -d ' ,/')
status=$(command grep -E "Fitter Status" "$FIT" | cut -d: -f2- | sed 's/^ *//')
free=$((CAPACITY - used))
# Pocket copro rides outclk_4 (54.669 MHz, its own async group per core_constraints.sdc).
# ⚠ The clock is named `general[4].gpll`, NOT `counter[4]` -- that is the MiSTer core's
# naming, and copying the MiSTer pattern here matched nothing. The first run printed
# "copro slack : <not found>" and still stamped LANDED, because the timing criterion was
# only applied when it parsed. A criterion that silently does not apply is not a criterion,
# so an unparsed slack is now a hard failure rather than a pass.
copro=$(awk '/Model Setup/ && /general\[4\]\.gpll/ {f=1;next} f&&/^Slack/{print $3;exit}' "$STA")
# the summary lists domains in ascending slack order, so the first block is the worst
worst=$(awk '/Model Setup/ {f=1;next} f&&/^Slack/{print $3;exit}' "$STA")

echo "Fitter status : $status"
printf "ALMs          : %s / %s  (%s free)\n" "$used" "$CAPACITY" "$free"
printf "copro slack   : %s ns (outclk_4)\n" "${copro:-<not found>}"
printf "worst setup   : %s ns (any domain)\n" "${worst:-<not found>}"
echo
pass=1
[ -n "$used" ] && [ "$free" -ge "$FLOOR" ] || { echo "FAIL: only $free ALMs free (floor $FLOOR)"; pass=0; }
if [ -z "${copro:-}" ]; then
  echo "FAIL: could not parse the copro (outclk_4 / general[4].gpll) slack from $STA."
  echo "  Not applying a criterion is not the same as passing it."
  pass=0
else
  [ "$(awk -v s="$copro" 'BEGIN{print (s>0)?1:0}')" = 1 ] || { echo "FAIL: copro slack $copro <= 0"; pass=0; }
fi
if [ -z "${worst:-}" ]; then
  echo "FAIL: could not parse any setup slack from $STA."; pass=0
else
  [ "$(awk -v s="$worst" 'BEGIN{print (s>0)?1:0}')" = 1 ] || { echo "FAIL: worst setup $worst <= 0"; pass=0; }
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
