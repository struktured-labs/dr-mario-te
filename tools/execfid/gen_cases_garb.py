#!/usr/bin/env python3
"""gen_cases_lua.py + garbage: CHAINED cases (every p), and for each case whose silicon pill RECEIVED garbage before the
next spawn (cases jsonl garbage_recv > 0), a `garb={size, c0, c1, ...}` field: execfid_probe.lua writes P2's incoming
volley (ROM p1_attackSize $0318 / p1_attackColors $0329) at f2 of that case, so the ROM releases it after the lock and
the cart's DRPRESTART garbage-window path runs; the prestart GO is served the NEXT case's co-sim timeline.
Usage: gen_cases_garb.py PUBTRACE.jsonl CASES.jsonl OUT.lua [--only p,p,...] [--nogarb]"""
import json, subprocess, sys, os
pub, cases, out = sys.argv[1:4]
only = None; nogarb = "--nogarb" in sys.argv
if "--only" in sys.argv:
    only = {int(x) for x in sys.argv[sys.argv.index("--only") + 1].split(",")}
here = os.path.dirname(os.path.abspath(__file__))
ps = [json.loads(l)["p"] for l in open(pub)]
subprocess.run([sys.executable, os.path.join(here, "..", "lateflip", "gen_cases_lua.py"), pub, out] + [f"{p}c" for p in ps], check=True)
G = {}
for l in open(cases):
    q = json.loads(l)
    n = q.get("garbage_recv") or 0
    if n >= 2 and not nogarb and (only is None or q["p"] in only):
        G[q["p"]] = min(4, n)
lines = open(out).read().split("\n")
for i, ln in enumerate(lines):
    if ln.startswith("  {p="):
        p = int(ln[5:ln.index(",")])
        if p in G:
            cols = ",".join(str(k % 3) for k in range(G[p]))
            lines[i] = ln.replace(", chain=", f", garb={{{G[p]},{cols}}}, chain=", 1)
open(out, "w").write("\n".join(lines))
print(f"garbage on {len(G)} cases: {sorted(G.items())}")
