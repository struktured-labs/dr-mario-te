#!/usr/bin/env python3
"""Pipeline stats from a lateflip_probe log: per case pill, was the PREVIOUS search still ARMED at the spawn edge,
the GO frame (frames after the injection/spawn), and the wait vs the nominal GO.

  pipe_stats.py LOG [nominal_go_f=1]
GO frame = f - k on the first trace line of the case with pend == 0 and k >= 0 (k = frames since the shim saw GO).
"""
import re
import sys

T = re.compile(r"^T p(\d+) f=(\d+) .*? arm=(\d+) pend=(\d+) .*? k=(-?\d+)")


def load(path):
    out = {}
    for line in open(path, errors="replace"):
        m = T.match(line)
        if not m:
            continue
        p, f, arm, pend, k = (int(x) for x in m.groups())
        c = out.setdefault(p, {"rows": []})
        c["rows"].append((f, arm, pend, k))
    res = {}
    for p, c in out.items():
        rows = c["rows"]
        first = rows[0]
        # the PREVIOUS search had not finished at the edge: the shim still serves it (k >= 0 = frames since its GO).
        # (D carts: also ARMED2 = 1 + PEND2 = 1 at f=1; DRABORTSTALE carts clear ARMED2 in the edge hook itself.)
        stale = first[3] >= 0
        go = None
        for f, arm, pend, k in rows:
            if pend == 0 and k >= 0:
                go = f - k
                break
        res[p] = dict(stale=stale, go=go, k0=first[3])
    return res


def summary(res, nominal=1):
    gos = [r["go"] for r in res.values() if r["go"] is not None]
    waits = {p: r["go"] - nominal for p, r in res.items() if r["go"] is not None and r["go"] > nominal}
    stale = [p for p, r in res.items() if r["stale"]]
    return dict(n=len(res), stale=len(stale), waits=len(waits), wait_max=max(waits.values(), default=0),
                wait_sum=sum(waits.values()), go_none=sum(r["go"] is None for r in res.values()), waitlist=waits)


if __name__ == "__main__":
    nominal = int(sys.argv[2]) if len(sys.argv) > 2 else 1
    r = load(sys.argv[1]); s = summary(r, nominal)
    print({k: v for k, v in s.items() if k != "waitlist"})
    print(" ".join(f"p{p}:{w}" for p, w in sorted(s["waitlist"].items())))
