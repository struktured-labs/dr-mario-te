#!/bin/bash
# score_d115.sh -- score the #115 re-run: does DRPRESTART x DRTUCK still look like a wedge pair
# once the harness's own START press can no longer land on the 8->4 transit?
#
# The original conviction was:
#     PRESTART=1 TUCK=0 -> 83 pills, 5 clean ends
#     PRESTART=0 TUCK=1 -> 171 pills, 10 clean ends
#     PRESTART=1 TUCK=1 -> 9 pills, 1 clean end   WEDGE
# and the #135 retrospective showed every PRESTART=1 cell's last 8->4 landed on f%30==1 -- the
# START-leak signature -- including the "faults alone" control, which wedged at f=8581.
#
# READING THIS TABLE
#   wedges=0 in EVERY cell           => the wedge was the harness. The pair is not convicted.
#   the `both` cell alone still dies  => a real interaction survives the fix; #115 stands.
#   blocked>0                         => the guard actually fired, so a clean run is EARNED and
#                                        not just a run that never pressed anything. A cell with
#                                        blocked=0 is NOT evidence of health -- report it as
#                                        unexercised (dr-mario-tuck-mailbox-vacuous-gate).
#   f%30 of the last 8->4             => kept in the table so a surviving death can be checked
#                                        against the discriminator rather than assumed clean.
# THREE SEEDS per cell, because match-1 length sets the restart phase: a single seed is one
# lottery draw, and drawing it three times is what stops a phase artifact from masquerading
# as a flag effect (or vice versa).
set -u
# Worktree-relative (dispatcher-hook pattern, 2026-08-20 #140): a hardcoded worktree
# here silently gated ANOTHER worktree's carts when run from a foreign checkout.
D=$(git -C "$(dirname "${BASH_SOURCE[0]}")" rev-parse --show-toplevel) || exit 2
[ -f "$D/patch_cartridge_copro.py" ] || { echo "FAIL: resolved worktree $D lacks the emitter -- refusing to gate the wrong tree" >&2; exit 2; }
D="$D/tmp/d115"
printf '%-14s %6s %8s %5s %7s %8s %8s %9s %s\n' \
  CELL SEED LAST_8to4 'f%30' PILLS GOES 'st/end' BLOCKED VERDICT
rc=0
for cell in both prestartonly tuckonly neither; do
  for seed in 114 4271 21013; do
    log="$D/${cell}_s${seed}/probe6.log"
    cen="$D/${cell}_s${seed}/d135_census.txt"
    if [ ! -f "$log" ]; then
      printf '%-14s %6s %8s %5s %7s %8s %8s %9s %s\n' "$cell" "$seed" - - - - - - "NO LOG (fail)"
      rc=1; continue
    fi
    f=$(command grep -a 'MODE f=' "$log" | command grep -a '8->4' | tail -1 \
          | sed -n 's/.*MODE f=\([0-9]*\).*/\1/p')
    m=$([ -n "$f" ] && echo $((f % 30)) || echo -)
    S=$(command grep -a '^SUMMARY' "$log" | tail -1)
    pills=$(echo "$S" | command grep -ao 'pills=[0-9]*' | head -1 | cut -d= -f2)
    goes=$(echo "$S" | command grep -ao 'goes=[0-9]*' | head -1 | cut -d= -f2)
    st=$(echo "$S" | command grep -ao 'matches_started=[0-9]*' | head -1 | cut -d= -f2)
    en=$(echo "$S" | command grep -ao 'matches_ended=[0-9]*' | head -1 | cut -d= -f2)
    blk=$(sed -n 's/.*blocked=\([0-9]*\).*/\1/p' "$cen" 2>/dev/null | tail -1)
    lk=$(sed -n 's/.*leaked=\([0-9]*\).*/\1/p' "$cen" 2>/dev/null | tail -1)

    v=OK
    [ -z "$S" ] && { v="NO SUMMARY (fail)"; rc=1; }
    [ "$v" = OK ] && [ "${lk:-1}" != 0 ] && { v="LEAKED (guard failed)"; rc=1; }
    [ "$v" = OK ] && [ "${blk:-0}" -eq 0 ] 2>/dev/null && v="unexercised (blocked=0)"
    # a cell that stopped advancing: started > ended by more than the one in-flight match
    [ "$v" = OK ] && [ -n "${st:-}" ] && [ -n "${en:-}" ] && \
      [ $((st - en)) -gt 1 ] && v="STILL DIES"

    printf '%-14s %6s %8s %5s %7s %8s %8s %9s %s\n' \
      "$cell" "$seed" "${f:-none}" "$m" "${pills:--}" "${goes:--}" \
      "${st:--}/${en:--}" "${blk:--}" "$v"
  done
done
echo
echo "reminder: blocked=0 means the guard never fired in that cell -- report it as UNEXERCISED,"
echo "not as evidence the cart is healthy. leaked>0 means the patched probe did not hold."
exit $rc
