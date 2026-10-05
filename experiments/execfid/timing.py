"""Execution-fidelity lane (2026-10-04): per-pill frame timelines, SILICON (couch recording, hidden-spawn tracker traj)
vs MESEN (lateflip_probe / execfid probe logs of the real cart fed the co-sim publish timeline), for the same pills.

Events, all in frames since the pill's spawn (silicon: tracker t_spawn; Mesen: the frame $0386 became $0F):
  drop1   first frame the capsule's BOTTOM cell is below the spawn row (first gravity tick or first soft-drop step)
  lat1    first frame the column differs from the spawn column 3
  slam    first row step of the final fast-drop run (row steps <= 3 f apart, ending at the arrival)
  arrive  first frame at the final pose (orientation, bottom row, column)
  lock    Mesen only: the frame $0397 (nextAction) became non-zero
  last    silicon only: the last tracked frame before the next spawn
Silicon rows: tracker row of an H capsule = its row; of a V capsule = its TOP cell, so bottom = row + 1 (checked against
the Mesen LAND y on the M4 G2 V landings). Mesen bottom row = 15 - y.

Usage: timing.py --cases CASES.jsonl --log MESEN.log [--log ...] [--rawh RAWH.jsonl ...] [--pubtrace PUB.jsonl]
       [--game G3] [--label L] [--out rows.jsonl]   -> gap summary by predicted state (+ per-pill rows)
"""
from __future__ import annotations

import json
import re
import statistics as st
import sys

T = re.compile(r"^T p(\d+) f=(\d+) y=(\d+) x=(\d+) rot=(\d+) na=(\d+) grav=(\d+) \| tgt=(\d+),(\d+) rd2=(\d+) arm=(\d+) "
               r"pend=(\d+) dly=(\d+) eff=(\d+) bud=(\d+) fall=(\d+) proph=(\w+) lg=(\d+),(\d+) \| pad=(\w+) held=(\w+) \| "
               r"mb=(-?\d+),(-?\d+),(\d+) k=(-?\d+)(?: sa=(\d+) st=(\d+))?")
LAND = re.compile(r"^LAND p(\d+) f=(\d+) x=(\d+) y=(\d+) rot=(\d+) action=(\d+)")
INJ = re.compile(r"^INJECT p(\d+) at f=(\d+)")


def runs_slam(steps, arrive):
    """steps = [(frame, bottom_row)] at each row change. The fast-drop run that ends at the arrival frame."""
    idx = [i for i, (f, r) in enumerate(steps) if f <= arrive]
    if not idx:
        return None
    i = idx[-1]
    j = i
    while j > 0 and steps[j][0] - steps[j - 1][0] <= 3:
        j -= 1
    if i - j < 2:          # fewer than 3 consecutive fast steps: not a slam
        return None
    return steps[j][0]


def sil_events(q):
    ts = q["t_spawn"]
    tr = []
    for t, o, r, c, cl in q["traj"]:
        f = round((t - ts) * 60)
        tr.append((f, o, r + (1 if o == "V" else 0), c))
    if not tr:
        return None
    fin = tr[-1][1:]
    arrive = next(f for f, *pose in tr if tuple(pose) == fin)
    drop1 = next((f for f, o, b, c in tr if b > 0), None)
    lat1 = next((f for f, o, b, c in tr if c != 3), None)
    steps, prev = [], None
    for f, o, b, c in tr:
        if prev is not None and b != prev:
            steps.append((f, b))
        prev = b
    return dict(drop1=drop1, lat1=lat1, slam=runs_slam(steps, arrive), arrive=arrive, last=tr[-1][0], fin=fin)


def mesen_cases(path):
    C = {}
    inj = {}
    for line in open(path, errors="replace"):
        m = INJ.match(line)
        if m:
            inj[int(m.group(1))] = int(m.group(2)); continue
        m = T.match(line)
        if m:
            g = m.groups(); p = int(g[0])
            c = C.setdefault(p, {"fr": [], "land": None})
            if c["land"] is None:
                c["fr"].append(dict(f=int(g[1]), y=int(g[2]), x=int(g[3]), rot=int(g[4]), na=int(g[5]), grav=int(g[6]),
                                    rd2=int(g[9]), arm=int(g[10]), pad=int(g[19], 16), held=int(g[20], 16),
                                    done=int(g[23]), sa=None if g[25] is None else int(g[25]),
                                    stab=None if g[26] is None else int(g[26])))
            continue
        m = LAND.match(line)
        if m:
            p = int(m.group(1)); c = C.setdefault(p, {"fr": [], "land": None})
            if c["land"] is None:
                c["land"] = dict(f=int(m.group(2)), x=int(m.group(3)), y=int(m.group(4)), rot=int(m.group(5)),
                                 act=int(m.group(6)))
    for p, c in C.items():
        c["inject_f"] = inj.get(p)
    return C


def mesen_events(c):
    fr = [x for x in c["fr"] if x["na"] == 0]
    if not fr or c["land"] is None:
        return None
    ld = c["land"]
    fin = (ld["x"], 15 - ld["y"], ld["rot"])
    pose = lambda x: (x["x"], 15 - x["y"], x["rot"])
    arrive = next(x["f"] for x in fr if pose(x) == fin)
    drop1 = next((x["f"] for x in fr if x["y"] < 15), None)
    lat1 = next((x["f"] for x in fr if x["x"] != 3), None)
    steps, prev = [], None
    for x in fr:
        b = 15 - x["y"]
        if prev is not None and b != prev:
            steps.append((x["f"], b))
        prev = b
    down1 = next((x["f"] for x in fr if x["pad"] & 0x04), None)
    sa0 = fr[0]["sa"]
    first0 = next((i for i, x in enumerate(c["fr"]) if x["done"] == 0), None)     # the GO clears the served DONE
    done_f = None if first0 is None else next((x["f"] for x in c["fr"][first0:] if x["done"] == 1), None)
    return dict(drop1=drop1, lat1=lat1, slam=runs_slam(steps, arrive), arrive=arrive, lock=ld["f"], down1=down1,
                sa0=sa0, done=done_f, act=ld["act"])


def med(xs):
    xs = [x for x in xs if x is not None]
    return (st.median(xs), len(xs)) if xs else (None, 0)


def pct(xs, q):
    xs = sorted(x for x in xs if x is not None)
    if not xs:
        return None
    return xs[min(len(xs) - 1, int(q * (len(xs) - 1) + 0.5))]


def attach_traj(Q, rawh_paths):
    """10/03 cases carry no traj: join each case to its hidden-spawn tracker record by t_spawn."""
    R = {}
    for path in rawh_paths:
        for l in open(path):
            r = json.loads(l)
            R[round(r["t_spawn"], 3)] = r
    for q in Q:
        if "traj" not in q:
            r = R.get(round(q["t_spawn"], 3))
            q["traj"] = r["traj"] if r else []
    return Q


def compare(Q, log, pubtrace=None, go_f=1):
    """Per pill: silicon vs Mesen events, plus the PREDICTED silicon slam/prestart state from the silicon spawn times and
    the co-sim DONE (pubtrace done_f, frames since GO; GO = spawn + go_f):
      FIRST  first pill of the game (SLAM_ARM starts 0)
      STALE  the previous pill's search was still ARMED at this pill's spawn edge (GO+done_f > next spawn) -> the
             cart's lock-while-armed / abort_stale disarm: SLAM_ARM = 0, so this pill holds for DONE before slamming
      GARB   the previous pill received garbage (a DRPRESTART garbage-window search may own this spawn)"""
    L = mesen_cases(log)
    P = {t["p"]: t for t in map(json.loads, open(pubtrace))} if pubtrace else {}
    qi = {q["p"]: q for q in Q}
    rows = []
    for q in Q:
        s = sil_events(q)
        c = L.get(q["p"])
        m = mesen_events(c) if c else None
        if s is None or m is None:
            continue
        prev = qi.get(q["p"] - 1)
        if prev is None:
            state = "FIRST"
        elif (q["p"] - 1) in P:
            edge = round((q["t_spawn"] - prev["t_spawn"]) * 60)
            state = "STALE" if go_f + P[q["p"] - 1]["done_f"] > edge else "armed"
        else:
            state = "?"
        garb = bool(prev and (prev.get("garbage_recv") or 0))
        o, col, _cl, row = q["actual"]                     # the tracker's own last pose must BE the landing; a landing
        trk_ok = s["fin"] == (o, row + (1 if o == "V" else 0), col)   # re-derived by the clear-pop repair is excluded
        nq = qi.get(q["p"] + 1)
        rows.append(dict(p=q["p"], same=m["act"] == q["actual_action"] and trk_ok, trk_ok=trk_ok, state=state, garb=garb,
                         d_arrive=s["arrive"] - m["arrive"], d_last_lock=s["last"] - m["lock"],
                         d_drop1=None if None in (s["drop1"], m["drop1"]) else s["drop1"] - m["drop1"],
                         sil=s, mes=m, sil_next=round((nq["t_spawn"] - q["t_spawn"]) * 60) if nq else None))
    return rows


def summarize(rows, label=""):
    S = [r for r in rows if r["same"]]
    a = [r["d_arrive"] for r in S]; ll = [r["d_last_lock"] for r in S]; d1 = [r["d_drop1"] for r in S]
    print(f"{label} same-landing n={len(S)}/{len(rows)} | OLD METRIC silicon last-tracked - Mesen lock: median "
          f"{med(ll)[0]} p10 {pct(ll, .1)} p90 {pct(ll, .9)} | ARRIVAL at the final pose: median {med(a)[0]} p10 "
          f"{pct(a, .1)} p90 {pct(a, .9)}, |d|<=2 on {sum(abs(x) <= 2 for x in a)} | first drop median {med(d1)[0]}")
    from collections import defaultdict
    agg = defaultdict(list)
    for r in S:
        agg[r["state"] + ("+GARB" if r["garb"] else "")].append(r)
    for k in sorted(agg):
        v = agg[k]; ds = [r["d_arrive"] for r in v]
        print(f"   {k:11s} n={len(v):3d} arrival gap median {med(ds)[0]:+} |d|<=2 {sum(abs(d) <= 2 for d in ds):3d}  "
              f">+2 {sum(d > 2 for d in ds):3d}  <-2 {sum(d < -2 for d in ds):3d}   outliers: "
              + " ".join(f"p{r['p']}:{r['d_arrive']:+d}" for r in v if abs(r["d_arrive"]) > 2))


def main():
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--cases", required=True)
    ap.add_argument("--log", required=True, action="append")
    ap.add_argument("--rawh", action="append", default=[])
    ap.add_argument("--pubtrace")
    ap.add_argument("--game")
    ap.add_argument("--label", default="")
    ap.add_argument("--out")
    a = ap.parse_args()
    Q = [json.loads(l) for l in open(a.cases)]
    if a.game:
        Q = [q for q in Q if q.get("game") == a.game]
    if a.rawh:
        attach_traj(Q, a.rawh)
    for log in a.log:
        rows = compare(Q, log, a.pubtrace)
        summarize(rows, f"{a.label} {log.split('/')[-1]}")
        if a.out:
            with open(a.out, "w") as fh:
                for r in rows:
                    fh.write(json.dumps(r) + "\n")


if __name__ == "__main__":
    main()
