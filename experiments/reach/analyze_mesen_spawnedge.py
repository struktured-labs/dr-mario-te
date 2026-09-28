#!/usr/bin/env python3
"""Analyse mesen_spawnedge_probe.lua logs (fix off vs on). Per LIVE pill (p2_nextAction == 0 interval), the new-pill
edges attributed to it are those fired after the previous pill locked and up to this pill's lock. Expected: exactly
1 for every pill on the fixed cart, including every round's first pill; the fix-off cart differs ONLY for pills that
follow a Y=$0F lock.
  analyze_mesen_spawnedge.py tmp/mesen/spawnedge_cvc_se0.log tmp/mesen/spawnedge_cvc_se1.log
"""
import collections, sys


def parse(fn):
    E, S, F, inits = [], [], [], []
    summary = None
    for line in open(fn):
        t = line.split()
        if not t:
            continue
        if t[0] == "E":
            E.append(int(t[1]))
        elif t[0] == "S":
            S.append(tuple(int(x) for x in t[1:8]))          # frame mode y pc na x rot
        elif t[0].startswith("F") and t[0] != "FATAL":
            F.append(line.strip())
        elif t[0] == "INIT":
            inits.append(int(t[3]))
        elif t[0] == "SUMMARY":
            summary = line.strip()
    return E, S, F, inits, summary


def pills(S):
    """live intervals: (start_frame, end_frame, y_at_lock, pc, mode_at_start)."""
    out, cur, prev = [], None, None
    for fr, mode, y, pc, na, x, rot in S:
        if prev is not None:
            if na == 0 and prev[4] != 0:
                cur = [fr, None, None, pc, mode]
            elif na != 0 and prev[4] == 0 and cur is not None:
                cur[1] = fr; cur[2] = prev[2]; out.append(tuple(cur)); cur = None
        prev = (fr, mode, y, pc, na, x, rot)
    return out


def analyse(fn):
    E, S, F, inits, summary = parse(fn)
    P = pills(S)
    modes = [s[1] for s in S]
    # match restarts: the autonav passes through the menu modes 0/1/2 again after the first match
    menu_visits = 0; inmenu = True
    for s in S:
        if s[1] in (0, 1, 2) and not inmenu:
            menu_visits += 1; inmenu = True
        elif s[1] == 4:
            inmenu = False
    rows = []
    prev_end = 0
    round_first = set()
    for fi in inits:
        nxt = [i for i, p in enumerate(P) if p[0] > fi]
        if nxt:
            round_first.add(nxt[0])
    for i, (st, en, ylock, pc, mode) in enumerate(P):
        n = sum(1 for e in E if prev_end < e <= en)
        pre = [e - st for e in E if prev_end < e <= en]
        rows.append(dict(i=i, start=st, end=en, ylock=ylock, edges=n, rel=pre, round_first=i in round_first,
                         after_y15=(i > 0 and P[i - 1][2] == 15)))
        prev_end = en
    return dict(fn=fn, summary=summary, F=F, inits=len(inits), menu_restarts=menu_visits, pills=rows)


def main(fns):
    res = [analyse(f) for f in fns]
    for r in res:
        rows = r["pills"]
        hist = collections.Counter(x["edges"] for x in rows)
        rf = [x for x in rows if x["round_first"]]
        rf_hist = collections.Counter(x["edges"] for x in rf)
        rf_rel = collections.Counter(tuple(x["rel"]) for x in rf)
        a15 = [x for x in rows if x["after_y15"]]
        print(f"== {r['fn']}")
        print(f"   {r['summary']}")
        print(f"   level inits (round starts) {r['inits']}, match restarts via the menu {r['menu_restarts']}, live pills {len(rows)}")
        print(f"   edges per pill: {dict(sorted(hist.items()))}")
        print(f"   ROUND-START pills: {len(rf)}, edges per pill {dict(sorted(rf_hist.items()))}, "
              f"edge frame relative to the pill going live: {dict(rf_rel)}")
        print(f"   pills following a Y=$0F lock: {len(a15)}, their edges: {[x['edges'] for x in a15]}")
        for f in r["F"]:
            print("   " + f)
        bad = [x for x in rows if x["edges"] != 1 and not x["after_y15"]]
        print(f"   pills with != 1 edge that do NOT follow a Y=$0F lock: {len(bad)} {[(x['i'], x['edges'], x['start']) for x in bad[:8]]}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
