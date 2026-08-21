#!/bin/bash
# gate_d135_adopt.sh -- adoption gate for the #131 START leak across the probe family (#135).
#
# WHAT IS GATED.  gate_d131_startleak.sh already proved the RULE at the OUTCOME level: with the
# leak the match-restart wedges, with the fix it does not.  That evidence is about the rule, and
# the rule is identical in every probe here.  What it cannot tell you is whether a given probe
# FILE actually adopted it -- a probe patched into a shape that never runs would inherit a green
# verdict it did not earn (dr-mario-tuck-mailbox-vacuous-gate).  So this gate is a MECHANISM
# gate on each patched file, run as a KILLED-MUTANT PAIR:
#
#   leak (MUTANT, D135_LEAK=1, the pre-fix behaviour) MUST report leaked > 0
#        -- if it does not, the rig never reached the 8->4 transit and a green `fix` is
#           meaningless.  This is the population control: the hazard must be REACHABLE.
#   fix  (the shipping rule)                          MUST report leaked == 0 AND blocked > 0
#        -- leaked == 0 alone would pass on a probe that simply never pressed anything, so
#           blocked > 0 is required as the non-vacuity half.
#
# A MISSING census from EITHER arm is a FAILURE, never a pass: a Mesen that died silently would
# otherwise read as "no leak observed" (dr-mario-mesen-launch-verification).
#
# REPRESENTATIVES -- one per fix SHAPE, plus every probe whose START logic differs structurally.
# The shapes are not cosmetic: three probes press START during mode 4 deliberately, and the
# uniform guard would have made them vacuous.
#   probe_framedense  shape U, cached-mode-4 family (probe2-8, soak, rotpc, startpause, fieldplay)
#   p1live            shape U, but with deliberate NON-START input during play (P1DRIVE walk)
#   stomp_pc          shape E, deliberate mode-4 START (pauses into the STUDY screen)
#
# This gate touches NO cart bytes -- defect and fix are both in the Lua harness.  The cart is
# checked for identity by run_d135probe.sh (md5 9fefaedb...) and never rebuilt.
set -u
# Worktree-relative (dispatcher-hook pattern, 2026-08-20 #140): a hardcoded worktree
# here silently gated ANOTHER worktree's carts when run from a foreign checkout.
D=$(git -C "$(dirname "${BASH_SOURCE[0]}")" rev-parse --show-toplevel) || exit 2
[ -f "$D/patch_cartridge_copro.py" ] || { echo "FAIL: resolved worktree $D lacks the emitter -- refusing to gate the wrong tree" >&2; exit 2; }
MAXF="${MAXF:-6000}"
PROBES="${PROBES:-probe_framedense.lua p1live.lua stomp_pc.lua}"

wait_for_mesen() {
  for _ in $(seq 1 480); do
    ps -eo stat,args | command grep -a 'Release/Mesen' | command grep -av grep \
      | command grep -av '^Z' >/dev/null || return 0
    sleep 15
  done
  echo "TIMED OUT waiting for a free Mesen" >&2; return 1
}

field_of() {   # field_of <probe> <arm> <blocked|leaked> -- empty if the arm produced no census
  local f="$D/tmp/d135/d135_${1%.lua}_$2_${MAXF}_s${D135_SEED:-114}/d135_census.txt"
  sed -n "s/.*$3=\([0-9]*\).*/\1/p" "$f" 2>/dev/null | tail -1
}

rc=0
printf '%-22s %-10s %-10s %s\n' PROBE LEAK_ARM FIX_ARM VERDICT
for p in $PROBES; do
  for arm in leak fix; do
    wait_for_mesen || exit 1
    "$D/tools/gate/run_d135probe.sh" "$p" "$arm" "$MAXF" </dev/null >/dev/null 2>&1
  done

  lk=$(field_of "$p" leak leaked)
  fl=$(field_of "$p" fix  leaked)
  fb=$(field_of "$p" fix  blocked)

  v=PASS
  [ -n "$lk" ] && [ -n "$fl" ] && [ -n "$fb" ] || v="FAIL(missing census)"
  [ "$v" = PASS ] && [ "${lk:-0}" -gt 0 ] || { [ "$v" = PASS ] && v="FAIL(mutant did not leak)"; }
  [ "$v" = PASS ] && [ "${fl:-1}" -eq 0 ] || { [ "$v" = PASS ] && v="FAIL(fix still leaked)"; }
  [ "$v" = PASS ] && [ "${fb:-0}" -gt 0 ] || { [ "$v" = PASS ] && v="FAIL(guard never fired)"; }

  printf '%-22s leaked=%-3s leaked=%-3s blocked=%-4s %s\n' \
    "$p" "${lk:-<none>}" "${fl:-<none>}" "${fb:-<none>}" "$v"
  [ "$v" = PASS ] || rc=1
done

[ "$rc" = 0 ] && echo "GATE PASS: mutant leaks, fix does not, guard demonstrably fired"
exit $rc
