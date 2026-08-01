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
