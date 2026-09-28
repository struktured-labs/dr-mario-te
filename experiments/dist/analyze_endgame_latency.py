#!/usr/bin/env python3
"""Endgame DECISION LATENCY of the DRDIST firmware vs ANTIBODY's, both on the DRDIST RTL (real copro6502 co-sim with
engine-command counters, tmp/fwcosim_end): 437 endgame boards (1..4 viruses; the 154 real gate-(b) game boards + the
283 couch endgame boards incl. the STEER6 regression games). The RTL term adds 0 engine cycles per command (gate:
CYCLES identical, DT_LATE 0; co-sim: DIST RTL + fw 77ec742c == ANTIBODY RTL + fw 77ec742c on 69/69 boards, moves AND
clocks). What remains is VALUE-DEPENDENT SEARCH EFFORT: the term changes leaf values, the search's value-driven parts
(tuck extension, top-k selection) do different amounts of work. Reported: GO->DONE clock delta per board (and in NES
frames at 85.9 MHz / 60 Hz -> 1 frame = 1.43 M clocks), engine command deltas, moves changed.
Usage: analyze_endgame_latency.py [DIR]"""
import json, os, re, sys

PAT = re.compile(r"^case (\d+): copro=\((\d+),(\d+)\) oracle=\(\d+,\d+\) clocks=(\d+)")
CMD = re.compile(r"^\s+cmds k=(\d+) c1=(\d+) c2=(\d+) c3=(\d+) c4=(\d+) c6=(\d+) c7=(\d+) c8=(\d+) busy=(\d+)")
FRAME = 85.9e6 / 60.0988


def load(d, fw):
    out = {}
    for s in sorted(x for x in os.listdir(d) if x.startswith(fw + "_s")):
        idx = [int(x) for x in open(os.path.join(d, s, "idx.txt")).read().split()]
        cur = None
        for l in open(os.path.join(d, s, "run.log")):
            m = PAT.match(l)
            if m:
                k, c, o, clk = map(int, m.groups()); cur = idx[k]; out[cur] = dict(mv=(c, o), clk=clk)
                continue
            m = CMD.match(l)
            if m and cur is not None:
                v = list(map(int, m.groups()))
                out[cur].update(cmds=sum(v[1:8]), c7=v[6], c4=v[4], busy=v[8])
    return out


def main(d):
    kinds = json.load(open(os.path.join(d, "kinds.json")))
    a, b = load(d, "c77"), load(d, "cD")
    ks = sorted(set(a) & set(b))
    dl = sorted((b[k]["clk"] - a[k]["clk"]) / FRAME for k in ks)
    n = len(dl)
    q = lambda p: dl[min(n - 1, int(p * n))]
    moved = sum(a[k]["mv"] != b[k]["mv"] for k in ks)
    more = sum(b[k]["cmds"] > a[k]["cmds"] for k in ks); less = sum(b[k]["cmds"] < a[k]["cmds"] for k in ks)
    print(f"endgame boards {n}/{len(kinds)} ({sum(1 for k in ks if kinds[k] == 'game')} game, "
          f"{sum(1 for k in ks if kinds[k] != 'game')} couch)")
    print(f"moves changed by the term: {moved}")
    print(f"engine commands: more on {more}, fewer on {less}, equal on {n - more - less}")
    print(f"GO->DONE delta (frames): mean {sum(dl) / n:+.3f}  median {q(0.5):+.3f}  p90 {q(0.9):+.3f}  p95 {q(0.95):+.3f}"
          f"  max {dl[-1]:+.3f}  min {dl[0]:+.3f}")
    base = sorted(a[k]["clk"] / FRAME for k in ks)
    print(f"ANTIBODY endgame decision time (frames): median {base[n // 2]:.2f}  p95 {base[int(0.95 * n)]:.2f}")
    for thr in (0.5, 1.0, 2.0):
        print(f"  boards slower by > {thr} frame: {sum(1 for x in dl if x > thr)}   faster by > {thr}: "
              f"{sum(1 for x in dl if x < -thr)}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1] if len(sys.argv) > 1 else "tmp/fwcosim_end"))
