#!/bin/bash
# gate_d131_startleak.sh -- regression gate for the #131 match-restart wedge.
#
# THE DEFECT (harness-side): the probe family delivers START on a fixed frame
# cadence in every non-level-select mode, including mode 8 (intro).  Mode 8 is
# the only predecessor of mode 4, and the 8->4 transition happens in the main
# loop AFTER that frame's NMI input poll -- so the START is still sitting in the
# P1 newly-pressed latch $F5 when the stock pause routine $978E runs, already in
# mode 4.  $97A7 LDA $F5 / AND #$10 accepts it and the match pauses at spawn.
# On a P1-native cart the pause is then PERMANENT (see task #133): the driver's
# P1 executor rewrites $F5 every hook from a command vocabulary that has no
# START, so $97D6 LDA $F5 / CMP #$10 can never be satisfied by any controller.
#
# THE GATE IS A KILLED-MUTANT PAIR, not a single assertion:
#   leak (MUTANT, the pre-fix behaviour) MUST wedge   -- if it does not, the rig
#        is not reproducing and a green `fix` would be meaningless
#   fix  (the shipping rule)             MUST NOT wedge
# Both directions are required.  A gate that only checked `fix` would pass on a
# rig that had silently stopped reaching the second match at all.
#
# This gate touches NO cart bytes -- the defect and the fix are both in the Lua
# harness, so there is no romgen/byte-identity step to run.  The cart is checked
# for identity by run_d131gate.sh (md5 9fefaedb...) and never rebuilt.
set -u
D=/home/struktured/projects/dr-mario-dispatch131-wt
MAXF="${MAXF:-4000}"

wait_for_mesen() {
  for _ in $(seq 1 480); do
    ps -eo stat,args | command grep -a 'Release/Mesen' | command grep -av grep \
      | command grep -av '^Z' >/dev/null || return 0
    sleep 15
  done
  echo "TIMED OUT waiting for a free Mesen" >&2; return 1
}

verdict_of() {   # verdict_of <arm> -- echo the verdict word, empty if the arm produced none
  local log="$D/tmp/d131gate/dg_o3_${MAXF}_s114_$1/d131gate.log"
  command grep -a "^SUMMARY" "$log" 2>/dev/null | sed -n 's/.*verdict=\([A-Z_]*\).*/\1/p' | tail -1
}

rc=0
for arm in leak fix; do
  wait_for_mesen || exit 1
  D1_SEED=114 D1_ARM="$arm" "$D/tools/gate/run_d131gate.sh" 3 "$MAXF" </dev/null >/dev/null 2>&1
done

vleak=$(verdict_of leak)
vfix=$(verdict_of fix)
echo "leak(mutant)=${vleak:-<none>}  fix=${vfix:-<none>}"

# A missing verdict is a FAILURE, never a pass: an arm whose Mesen died silently
# would otherwise read as "did not wedge" (dr-mario-mesen-launch-verification).
[ "$vleak" = "STILL_WEDGED" ] || { echo "FAIL: mutant arm did not reproduce the wedge (got '${vleak:-<none>}')"; rc=1; }
[ "$vfix"  = "NO_WEDGE" ]     || { echo "FAIL: fixed arm did not stay clean (got '${vfix:-<none>}')"; rc=1; }

[ "$rc" = 0 ] && echo "GATE PASS: mutant wedges, fix does not"
exit $rc
