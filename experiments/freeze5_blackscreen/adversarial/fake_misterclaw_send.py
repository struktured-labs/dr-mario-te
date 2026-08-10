#!/usr/bin/env python3
"""Fake misterclaw-send. Behaviour selected by $SHIM_MODE. Contacts NO device.

Modes:
  ok_nowrite     rc=0, prints the auto-discovery banner, WRITES NOTHING
  ok_cached      rc=0, always copies the SAME png (a stale cache)
  ok_truncated   rc=0, writes a truncated/corrupt PNG
  hang           sleeps forever (after printing the discovery banner on call #1)
  rcfail         rc=1 with an error message
  ok_real        rc=0, copies the next png from $SHIM_FRAMES (colon-separated)
"""
import os
import shutil
import sys
import time

mode = os.environ.get("SHIM_MODE", "ok_nowrite")
state = os.environ.get("SHIM_STATE", "/tmp/shimstate")
out = None
argv = sys.argv[1:]
for i, a in enumerate(argv):
    if a == "--output" and i + 1 < len(argv):
        out = argv[i + 1]

n = 0
if os.path.exists(state):
    n = int(open(state).read().strip() or 0)
n += 1
open(state, "w").write(str(n))

# The real binary prints this whenever the host name is not directly reachable.
if os.environ.get("SHIM_DISCOVER", "1") == "1":
    print("Host \"MiSTer\" not reachable, scanning local network...", file=sys.stderr)
    print("Auto-discovered MisterClaw at 10.42.0.226", file=sys.stderr)

if mode == "hang":
    time.sleep(9999)
    sys.exit(0)

if mode == "ok_then_hang":
    # call #1 succeeds (this is what seeds the watchdog's IP cache in production),
    # every later call hangs.
    if n == 1:
        shutil.copyfile(os.environ["SHIM_CACHE"], out)
        sys.exit(0)
    time.sleep(9999)

if mode == "rcfail":
    print("connection refused", file=sys.stderr)
    sys.exit(1)

if mode == "ok_nowrite":
    sys.exit(0)

if mode == "ok_cached":
    shutil.copyfile(os.environ["SHIM_CACHE"], out)
    sys.exit(0)

if mode == "ok_truncated":
    blob = open(os.environ["SHIM_CACHE"], "rb").read()
    open(out, "wb").write(blob[:len(blob) // 2])
    sys.exit(0)

if mode == "ok_real":
    fr = os.environ["SHIM_FRAMES"].split(":")
    shutil.copyfile(fr[(n - 1) % len(fr)], out)
    sys.exit(0)

sys.exit(3)
