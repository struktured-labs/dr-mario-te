#!/usr/bin/env python3
"""Summarise a lateflip_probe log: per injected case, the Mesen landing vs silicon / python brain / copro final, the
target changes the driver adopted AFTER committing (late retargets), and whether DRLATEGUARD froze the pill.

Usage: parse_lateflip.py LOG [LOG2]   (two logs -> side-by-side, e.g. flag off vs on)
"""
import re
import sys

T = re.compile(r"^T p(\d+) f=(\d+) y=(\d+) x=(\d+) rot=(\d+) na=(\d+) grav=(\d+) \| tgt=(\d+),(\d+) rd2=(\d+) arm=(\d+) "
               r"pend=(\d+) dly=(\d+) eff=(\d+) bud=(\d+) fall=(\d+) proph=(\w+) lg=(\d+),(\d+) \| pad=(\w+) held=(\w+) \| "
               r"mb=(-?\d+),(-?\d+),(\d+) k=(-?\d+)")
LAND = re.compile(r"^LAND p(\d+) f=(\d+) x=(\d+) y=(\d+) rot=(\d+) action=(\d+) \| sil=(-?\w+) sim=(\d+) cosim_final=(\d+)")
UP = re.compile(r"^UPLOAD p(\d+) (\w+)")
O2V = {0: 0, 2: 1, 3: 2, 1: 3}


def load(path):
    cases = {}
    for line in open(path, errors="replace"):
        m = T.match(line)
        if m:
            g = list(m.groups()); p = int(g[0])
            c = cases.setdefault(p, {"frames": [], "land": None, "upload": None})
            if c["land"] is None:
                c["frames"].append(dict(f=int(g[1]), y=int(g[2]), x=int(g[3]), rot=int(g[4]), na=int(g[5]),
                                        tc=int(g[7]), to=int(g[8]), rd2=int(g[9]), arm=int(g[10]), pend=int(g[11]),
                                        cmt=int(g[17]), lock=int(g[18]), pad=int(g[19], 16)))
            continue
        m = LAND.match(line)
        if m:
            p = int(m.group(1)); c = cases.setdefault(p, {"frames": [], "land": None, "upload": None})
            if c["land"] is None:
                c["land"] = dict(f=int(m.group(2)), act=int(m.group(6)), sil=m.group(7), sim=int(m.group(8)),
                                 fin=int(m.group(9)))
            continue
        m = UP.match(line)
        if m:
            cases.setdefault(int(m.group(1)), {"frames": [], "land": None, "upload": None})["upload"] = m.group(2)
    for p, c in cases.items():
        fr = c["frames"]
        tg = [(x["tc"], x["to"]) for x in fr]
        first_rd2 = next((i for i, x in enumerate(fr) if x["rd2"] == 1 and x["pend"] == 0), None)
        late = 0
        if first_rd2 is not None:
            for i in range(first_rd2 + 1, len(fr)):
                if tg[i] != tg[i - 1]:
                    late += 1
        c["late_retargets"] = late
        c["frozen"] = any(x["lock"] == 1 for x in fr)
        c["commit_f"] = fr[first_rd2]["f"] if first_rd2 is not None else None
    return cases


def act(o4col):
    return o4col


def main():
    logs = [load(p) for p in sys.argv[1:]]
    ps = sorted(set().union(*[set(L) for L in logs]))
    hdr = "p     sil  sim  fin | " + " | ".join(f"land late frz up" for _ in logs)
    print(hdr)
    agg = [dict(sil=0, sim=0, fin=0, n=0, hyb=0) for _ in logs]
    for p in ps:
        row = []
        base = None
        for k, L in enumerate(logs):
            c = L.get(p)
            if not c or not c["land"]:
                row.append("   -   -   -  -"); continue
            ld = c["land"]; base = ld
            a = agg[k]; a["n"] += 1
            a["sil"] += str(ld["act"]) == ld["sil"]; a["sim"] += ld["act"] == ld["sim"]; a["fin"] += ld["act"] == ld["fin"]
            row.append(f"{ld['act']:4d} {c['late_retargets']:4d} {'F' if c['frozen'] else '.':>3s} {('ok' if c['upload'] == 'MATCH' else (c['upload'] or '?'))[:2]:>2s}")
        if base:
            print(f"p{p:3d} {base['sil']:>4s} {base['sim']:4d} {base['fin']:4d} | " + " | ".join(row))
    for k, a in enumerate(agg):
        print(f"log{k}: n={a['n']} land==silicon {a['sil']} land==python-brain {a['sim']} land==copro-final {a['fin']}")


if __name__ == "__main__":
    main()
