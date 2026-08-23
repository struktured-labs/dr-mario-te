#!/bin/sh
# inputd_ctl.sh -- start/stop/status for sileval_inputd, ON the box.
#
# Why a script on the box and not an ssh one-liner: a one-liner that greps for
# "inputd.py" MATCHES ITS OWN COMMAND LINE, so the kill loop kills the ssh
# session running it (observed: ssh exit 255). Living in a file keeps the
# pattern out of the caller's cmdline; $$ exclusion covers this script itself.
#
# status is LIVENESS, not file existence: a dead daemon leaves its FIFO behind,
# and the old `test -p` check reported "ready" forever while every keystroke
# went into a fifo with no reader. Existence of the fifo proves nothing.
DAEMON=/media/fat/linux/sileval_inputd.py
FIFO=/tmp/sileval_input.fifo
LOG=/tmp/sileval_inputd.log

pids() {
  for d in /proc/[0-9]*; do
    p=${d#/proc/}
    [ "$p" = "$$" ] && continue
    c=$(tr "\0" " " < "$d/cmdline" 2>/dev/null)
    case "$c" in
      *sileval_inputd.py*) case "$c" in *inputd_ctl*) ;; *) echo "$p";; esac ;;
    esac
  done
}

case "$1" in
  status)
    n=$(pids | wc -l)
    echo "daemons=$n"
    [ -p "$FIFO" ] && echo "fifo=yes" || echo "fifo=no"
    # ALIVE only if exactly one daemon AND a real fifo
    [ "$n" -eq 1 ] && [ -p "$FIFO" ] && { echo "state=ALIVE"; exit 0; }
    echo "state=DEAD"; exit 1 ;;
  stop)
    for p in $(pids); do kill "$p" 2>/dev/null; done
    sleep 1
    for p in $(pids); do kill -9 "$p" 2>/dev/null; done
    rm -f "$FIFO"; echo stopped ;;
  start)
    "$0" stop >/dev/null 2>&1
    rm -f "$LOG"
    setsid nohup python3 "$DAEMON" </dev/null >"$LOG" 2>&1 &
    i=0
    while [ $i -lt 25 ]; do
      "$0" status >/dev/null 2>&1 && { echo "started"; exit 0; }
      sleep 1; i=$((i+1))
    done
    echo "FAILED to start; log:"; cat "$LOG" 2>/dev/null; exit 1 ;;
  *) echo "usage: $0 {start|stop|status}"; exit 2 ;;
esac
