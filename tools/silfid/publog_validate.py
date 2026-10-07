#!/usr/bin/env python3
"""DRPUBLOG Mesen validation: the ring decoded from periodic RAM dumps vs the probe's own truth.

Truth (tools/silfid/publog_probe.lua log): every GO's upload bytes as WRITTEN to the $5200 window (write callbacks),
the mailbox values the shim SERVED to the cart each frame (T lines: col, orient, done, k = frames since GO), and every
landing (LAND lines). The ring is decoded with tools/silfid/publog.py from the dump_*.bin files of the same run.
  RING   each decoded pill's (board, cA cB nA nB) equals exactly one GO's upload, in seq order (no gaps between the
         first and last decoded seq)
  LIVE   every live event is a value the shim served for that GO; every served value that stayed >= 2 frames (before
         DONE) is logged
  DONE   the DONE event equals the served final
  LOCK   the lock event equals the probe's LAND pose (x, y, rot)
  publog_validate.py RUN_DIR [PUBTRACE.jsonl]   (RUN_DIR holds lateflip_<tag>.log and dump_*.bin; the pubtrace the cases
  came from supplies each search's FULL timeline -- the probe stops tracing between a landing and the next injection,
  so a stale search's late publications are otherwise invisible to it)
"""
import glob, os, re, sys, collections
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import publog as PL


def main(run, pubtrace=None):
    logs = glob.glob(os.path.join(run, "lateflip_*.log")); assert len(logs) == 1, logs
    gos, inject, T, lands, W, order = [], {}, collections.defaultdict(list), {}, [], []
    for ln in open(logs[0], errors="replace"):
        if ln.startswith("GO n="):
            m = re.match(r"GO n=(\d+) f=(\d+) kind=(\w+) preempt=(\w+) prev_k=(-?\d+) up=([0-9a-f]+)", ln)
            gos.append(dict(n=int(m.group(1)), f=int(m.group(2)), kind=m.group(3), up=m.group(6), after=len(order)))
        elif ln.startswith("INJECT p"):
            m = re.match(r"INJECT p(\d+) at f=(\d+)", ln); inject[int(m.group(1))] = int(m.group(2))
            order.append(int(m.group(1)))
        elif ln.startswith("T p"):
            m = re.match(r"T p(\d+) f=(\d+) y=(\d+) x=(\d+) rot=(\d+) .*?mb=(-?\d+),(-?\d+),(-?\d+) k=(-?\d+)", ln)
            p = int(m.group(1)); T[p].append(tuple(int(x) for x in m.groups()[1:]))
        elif ln.startswith("W after=p"):
            # garbage-window trace (absolute frames): the PRESTART search's mailbox is served here, before its case is
            # injected (so it has no T lines yet)
            m = re.match(r"W after=p(\d+) f=(\d+) .*?\| mb=(-?\d+),(-?\d+),(-?\d+) k=(-?\d+)", ln)
            f, c, o, d, k = (int(x) for x in m.groups()[1:])
            W.append((f, c, o, d, k))
        elif ln.startswith("LAND p"):
            m = re.match(r"LAND p(\d+) f=(\d+) x=(\d+) y=(\d+) rot=(\d+)", ln)
            lands[int(m.group(1))] = (int(m.group(3)), int(m.group(4)), int(m.group(5)))
    by_f = {g["f"]: g for g in gos}
    # served mailbox per GO (absolute GO frame) from the T lines
    served = collections.defaultdict(list)       # go_f -> [(k, col, o, done)]
    land_of_go = {}
    for p, rows in T.items():
        sp = inject.get(p)
        if sp is None:
            continue
        gof = None
        for f, y, x, rot, c, o, d, k in rows:
            if k > 0:
                gof = sp + f - k
                served[gof].append((k, c, o, d))
            elif gof is not None and d == 1:
                served[gof].append((999, c, o, d))
        if gof is not None and p in lands:
            land_of_go[gof] = lands[p]
    gof = None
    for f, c, o, d, k in W:
        if k > 0:
            gof = f - k
            served[gof].append((k, c, o, d))
        elif gof is not None and d == 1:
            served[gof].append((999, c, o, d)); gof = None
    for g in served:
        served[g] = sorted(set(served[g]))
    timeline = {}
    if pubtrace:
        import json
        tl = {r["p"]: r for r in map(json.loads, open(pubtrace))}
        for g in gos:
            idx = g["after"] - 1 if g["kind"] == "case" else g["after"] if g["kind"] == "prefetch" else None
            if idx is not None and 0 <= idx < len(order) and order[idx] in tl:
                r = tl[order[idx]]
                timeline[g["f"]] = {(c, o) for _, c, o, _a in r["pubs"]} | {(r["final"][0], r["final"][1])}
    dumps = sorted(glob.glob(os.path.join(run, "dump_*.bin")))
    pills = PL.merge(dumps)
    key = {g["up"]: g for g in gos}
    act = collections.Counter(); bad = []
    for p in pills:
        up = p["board"] + bytes(p["upload4"]).hex()
        g = key.get(up)
        if g is None:
            act["ring_unmatched"] += 1
            if len(bad) < 3: bad.append(("ring", p["seq"], p["upload4"]))
            continue
        act["ring_ok"] += 1
        if not p["final"]:
            continue
        sv = sorted(served.get(g["f"], []))
        vals = [(c, o) for k, c, o, d in sv if k < 999 and o != 255 and d == 0]
        live = [(e["a"], e["b"]) for e in p["events"] if e["type"] == "live"]
        act["live_events"] += len(live)
        truth = timeline.get(g["f"], set(vals))          # the case's full co-sim timeline when known
        act["live_checked_vs_timeline"] += len(live) if g["f"] in timeline else 0
        for v in live:
            if v not in truth:
                act["live_not_served"] += 1
                if len(bad) < 6: bad.append(("live", p["seq"], v, sorted(set(vals))))
        runs = []
        for k, c, o, d in sv:
            if k >= 999 or o == 255 or d:
                continue
            if runs and runs[-1][0] == (c, o) and runs[-1][2] == k - 1:
                runs[-1][2] = k
            else:
                runs.append([(c, o), k, k])
        for v, k0, k1 in runs:
            if k1 - k0 + 1 >= 2:
                act["long_served"] += 1
                if v not in live:
                    act["long_served_missing"] += 1
                    if len(bad) < 9: bad.append(("missing", p["seq"], v, k0, k1, live))
        fin = [(c, o) for k, c, o, d in sv if k >= 999]
        dn = [(e["a"], e["b"]) for e in p["events"] if e["type"] == "done"]
        if fin:
            act["dones"] += 1
            if not dn or dn[0] != fin[0]:
                act["done_bad"] += 1
                if len(bad) < 12: bad.append(("done", p["seq"], dn, fin[0]))
        if g["f"] in land_of_go:
            x, y, rot = land_of_go[g["f"]]
            lk = [(e["a"], e["b"] >> 2, e["b"] & 3) for e in p["events"] if e["type"] == "lock"]
            act["locks"] += 1
            if (x, y, rot) not in lk:
                act["lock_bad"] += 1
                if len(bad) < 15: bad.append(("lock", p["seq"], lk, (x, y, rot)))
    seqs = [p["seq"] for p in pills]
    gaps = sum(1 for a, b in zip(seqs, seqs[1:]) if b != a + 1)
    act["pills"] = len(pills); act["seq_gaps"] = gaps; act["gos"] = len(gos)
    act["prestart_pills"] = sum(1 for p in pills if p["kind"] == 1)
    ok = (act["ring_unmatched"] == 0 and act["ring_ok"] > 0 and act["live_not_served"] == 0
          and act["long_served_missing"] == 0 and act["done_bad"] == 0 and act["lock_bad"] == 0 and act["dones"] > 0
          and act["locks"] > 0)
    print(dict(act))
    for b in bad:
        print("  ", b)
    print("PUBLOG MESEN VALIDATION: " + ("PASS" if ok else "FAIL"))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1], sys.argv[2] if len(sys.argv) > 2 else None))
