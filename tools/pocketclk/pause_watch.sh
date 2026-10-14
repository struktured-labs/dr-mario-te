#!/usr/bin/env bash
# SIGSTOP / SIGCONT the lane's farm units while dr_mario_rl/tmp/PAUSE_ALL exists; exits when no farm unit is left.
P=/home/struktured/projects/dr_mario_rl/tmp/PAUSE_ALL; U="grok-pocketclk-sim grok-pocketclk-sim2"; s=0
alive() { for u in $U; do systemctl --user is-active -q $u && return 0; done; return 1; }
while alive; do
  if [ -e $P ] && [ $s = 0 ]; then for u in $U; do systemctl --user kill -s STOP $u 2>/dev/null; done; s=1
  elif [ ! -e $P ] && [ $s = 1 ]; then for u in $U; do systemctl --user kill -s CONT $u 2>/dev/null; done; s=0; fi
  sleep 5; done
