#!/usr/bin/env bash
# The three numbers that decide whether the link engine ships as-is, printed together
# with their pass/fail so the call is mechanical rather than a judgement.
#
#   (a) copro-domain setup slack >= +0.10 ns -- emu|pll|...counter[0] is the copro clock.
#       NOT merely "positive". The pre-link baseline shipped at +0.118 and cliffed to
#       -3.241 on the first real change; a picosecond-order hair is a seed lottery ticket,
#       not margin, and tucks (#17) or any VS term would cash it negative immediately.
#       The bar exists to refuse exactly that number, so it lives HERE -- a stale bar in
#       the script that enforces the rule is the false-stamp class of bug.
#   (b) pll_hdmi no worse than the baseline's -0.012 by more than noise. PRE-EXISTING and
#                                              not ours, but placement pressure can move
#                                              it, and then it becomes ours to explain.
#   (c) >= 1500 ALMs FREE                   -- headroom floor for tucks (#17) and the VS
#                                              lane behind this one.
#
# Any one failing => the BRAM conversion (task #27) becomes the plan again.
set -uo pipefail
FORK=${1:-/home/struktured/projects/NES_MiSTer-winner}
FIT=$FORK/output_files/NES.fit.summary
STA=$FORK/output_files/NES.sta.summary
CAPACITY=41910
FLOOR=1500
BASE_HDMI=-0.012
SLACK_BAR=0.10       # ship bar, NOT zero -- see the note above

for f in "$FIT" "$STA"; do
  [ -f "$f" ] || { echo "missing $f -- has the flow finished?" >&2; exit 65; }
done

# ★ FRESHNESS. A slack read from a report that describes a DIFFERENT compile is not a number
# about this bitstream. Added 2026-08-01 after a build quoted "+0.094" from an NES.sta.rpt
# half an hour older than its own rbf: Quartus SMART RECOMPILATION had skipped the Timing
# Analyzer (along with synthesis and the fitter). The verdict looked precise and was
# meaningless. Report UNKNOWN rather than a stale figure.
#
# ⚠ CORRECTED 2026-08-01, same day: the first version of this block compared the reports
# against NES.rbf, which is WRONG BY CONSTRUCTION. The flow order is
#     Analysis & Synthesis -> Fitter (writes fit.*) -> Assembler (writes .sof/.rbf) -> STA
# so NES.fit.summary is ALWAYS older than the rbf in a perfectly honest compile. The rule
# fired UNKNOWN on the first clean build it ever saw (racer, 4/4 stages run, 0 skipped)
# -- a gate that rejects only correct builds teaches you to ignore it.
#
# The mechanism the incident actually had is: a design input changed, and the stage that
# consumes it did not re-run, so its report PREDATES that input. So that is what we assert
# -- every report must post-date the newest design input -- plus flow ORDERING between the
# reports themselves. Both hold for an honest run at any speed.
NEWEST_IN=$(ls -t "$FORK/copro_rom.hex" "$FORK"/rtl/mappers/CoproDrMario.sv \
                  "$FORK"/rtl/mappers/LeafEval.sv 2>/dev/null | head -1)
if [ -n "$NEWEST_IN" ]; then
  for f in "$FIT" "$STA"; do
    if [ "$f" -ot "$NEWEST_IN" ]; then
      echo "VERDICT: UNKNOWN -- $(basename "$f") PREDATES $(basename "$NEWEST_IN")." >&2
      echo "  The stage that consumes that input did not re-run for this build; the report" >&2
      echo "  describes a different compile. Refusing to quote slack or utilisation." >&2
      exit 66
    fi
  done
fi
if [ "$STA" -ot "$FIT" ]; then
  echo "VERDICT: UNKNOWN -- NES.sta.summary predates NES.fit.summary (flow order violated)." >&2
  exit 66
fi

used=$(command grep -E "Logic utilization" "$FIT" | command grep -oE "[0-9,]+ /" | head -1 | tr -d ' ,/')
status=$(command grep -E "Fitter Status" "$FIT" | cut -d: -f2- | sed 's/^ *//')
free=$((CAPACITY - used))
# slack lines follow their "Type : Setup '<clock>'" line
copro=$(awk "/Type  : Setup .*counter\[0\].output_counter/ && /emu\|pll/ {f=1;next} f&&/Slack/{print \$3;exit}" "$STA")
hdmi=$(awk "/Type  : Setup .*pll_hdmi/ {f=1;next} f&&/Slack/{print \$3;exit}" "$STA")

pass=1
chk() { if [ "$1" = 1 ]; then echo "PASS"; else echo "FAIL"; pass=0; fi; }

echo "Fitter status : $status"
printf "ALMs          : %s / %s  (%s free)   " "$used" "$CAPACITY" "$free"
chk "$(awk -v f="$free" -v m="$FLOOR" 'BEGIN{print (f>=m)?1:0}')"
printf "copro slack   : %s ns (bar +%s)   " "${copro:-<none>}" "$SLACK_BAR"
chk "$(awk -v s="${copro:-0}" -v b="$SLACK_BAR" 'BEGIN{print (s>=b)?1:0}')"
# closing timing at all is real progress and worth saying, but it is NOT the bar
if [ -n "${copro:-}" ] \
   && [ "$(awk -v s="$copro" 'BEGIN{print (s>0)?1:0}')" = 1 ] \
   && [ "$(awk -v s="$copro" -v b="$SLACK_BAR" 'BEGIN{print (s<b)?1:0}')" = 1 ]; then
  echo "                (timing CLOSES at $copro ns, but that is a hair, not margin)"
fi
printf "pll_hdmi      : %s ns (baseline %s)   " "${hdmi:-<none>}" "$BASE_HDMI"
chk "$(awk -v s="${hdmi:-0}" -v b="$BASE_HDMI" 'BEGIN{print (s>=b-0.05)?1:0}')"
echo
if [ "$pass" = 1 ]; then
  echo "VERDICT: SHIP AS-IS -- all three criteria met; BRAM conversion (#27) not needed."
else
  echo "VERDICT: BRAM CONVERSION (#27) BECOMES THE PLAN -- a criterion failed above."
fi
exit $((1 - pass))
