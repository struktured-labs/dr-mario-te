#!/usr/bin/env python3
"""Co-sim verdicts: RTL (vsim_pub2) final vs the py65 firmware decision vs the mirror(+sim DANGER), per board, and
the paired OFF->ON copro cost (DONE and first-publish clocks; 48 sim clocks per NES CPU cycle, 29780.5 cycles/frame).
Usage: analyze_cosim.py GDIR CDIR"""
import json, sys, statistics as st
G, C = sys.argv[1], sys.argv[2]
FR = 29780.5 * 48
ld = lambda p: [json.loads(l) for l in open(p)]
gj = lambda t: json.load(open(f"{G}/{t}.json"))["res"]
cs = {t: ld(f"{C}/{t}.jsonl") for t in ("OFF", "D4", "D1")}
ok = True
for t in ("OFF", "D4", "D1"):
    g, c = gj(t), cs[t]
    assert len(g) == len(c) == 210
    fw = sum(tuple(x["final"]) == tuple(r["d1"]) for x, r in zip(c, g))
    mi = sum(tuple(x["final"]) == tuple(r["e1"]) for x, r in zip(c, g))
    mv = sum(tuple(x["final"]) != tuple(o["final"]) for x, o in zip(c, cs["OFF"]))
    print(f"{t:3s}: RTL final == py65 fw {fw}/210; == mirror(+sim DANGER) {mi}/210; RTL final differs from OFF on {mv}")
    ok &= fw == 210 and mi == 210
for t in ("D4", "D1"):
    dd = [(x["done_clk"] - o["done_clk"]) / 48 for x, o in zip(cs[t], cs["OFF"])]
    df = [(x["first_clk"] - o["first_clk"]) / 48 for x, o in zip(cs[t], cs["OFF"]) if x["first_clk"] and o["first_clk"]]
    rel = [(x["done_clk"] / o["done_clk"] - 1) * 100 for x, o in zip(cs[t], cs["OFF"])]
    q = lambda v, p: sorted(v)[int(p * (len(v) - 1))]
    print(f"{t} cost vs OFF (NES CPU cycles): DONE median {st.median(dd):+.0f} p90 {q(dd,.9):+.0f} max {max(dd):+.0f} "
          f"({st.median(rel):+.2f}% median, max {max(rel):+.2f}%, = {max(dd)*48/FR:+.3f} f max); "
          f"first publish median {st.median(df):+.0f} max {max(df):+.0f}; OFF DONE median {st.median([o['done_clk']/FR for o in cs['OFF']]):.2f} f")
d4 = cs["D4"][60:120]
for m in ("after_rootord", "no_clear", "lut_off1", "inert", "row_off1"):
    c = ld(f"{C}/mut_{m}.jsonl"); g = gj(f"mut_{m}")
    diff = sum(tuple(x["final"]) != tuple(y["final"]) for x, y in zip(c, d4))
    agree = sum(tuple(x["final"]) == tuple(r["d1"]) for x, r in zip(c, g))
    print(f"mutant {m:13s}: RTL final != D4 RTL on {diff}/60 -> {'KILLED' if diff else 'survived'}; "
          f"RTL == its own py65 build {agree}/60")
print("COSIM_DRDANGER", "PASS" if ok else "FAIL")
