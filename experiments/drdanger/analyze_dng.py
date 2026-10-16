#!/usr/bin/env python3
"""RTL per-root gate: every copro-bus write to D_DNG ($0287) in the vsim_dng co-sim (real RTL, DELTA path) checked
against the SIM's n for that root (gate_drdanger.sim_n = tapout's _soft_b1 + cols 2..5 height), plus the clear-before-
scan invariant (every scan write is immediately preceded by a 0 write for the same root key) and observer passivity
(final/DONE == the vsim_pub2 run of the same hex). Usage: analyze_dng.py VD CDIR LINES"""
import json, os, sys
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
VD, C, LINES = sys.argv[1:4]
L = open(LINES).read().splitlines()
import gate_drdanger as G


def arm_setup(arm):
    G.ARM = arm
    import importlib
    D3 = sys.modules.get("test_search_d3")
    G.GS._ST["D3"] = D3


def load(tag):
    out = {}
    d = os.path.join(VD, tag, "out")
    for f in os.listdir(d):
        t = open(os.path.join(d, f)).read().split()
        i = t.index("DONE"); k = t.index("DNG")
        w = list(map(int, t[k + 2:])); n = int(t[k + 1]); assert len(w) == 3 * n
        out[int(f[:-4])] = dict(done=int(t[i + 1]), final=(int(t[i + 2]), int(t[i + 3])),
                                w=[tuple(w[3 * j:3 * j + 3]) for j in range(n)])
    return out


def check(tag, arm, ref_tag):
    import gate_drdanger  # noqa
    h0 = dict(D4=10, D1=11)[arm]
    R = load(tag)
    off = 61 if tag.startswith("mut_") else 1   # mutant co-sim jsonl i 0..59 = lines 61..120
    ref = {json.loads(l)["i"] + off: json.loads(l) for l in open(os.path.join(C, ref_tag + ".jsonl"))}
    bad_n = bad_clear = live = live_ok = passive = 0
    for idx, r in R.items():
        f = L[idx - 1].split(); cA, cB = int(f[0]) & 0x0F, int(f[1]) & 0x0F
        nes = [int(x, 16) for x in f[4:]]
        cache = {}
        for j, (c, o, v) in enumerate(r["w"]):
            if (c, o) not in cache:
                cache[(c, o)] = sim_n(nes, o, c, cA, cB, h0)
            want = cache[(c, o)]
            if v != 0:
                live += 1; live_ok += v == want
                bad_n += v != want
                if j == 0 or r["w"][j - 1] != (c, o, 0):
                    bad_clear += 1
        passive += idx in ref and ref[idx]["final"] == list(r["final"]) and ref[idx]["done_clk"] == r["done"]
    print(f"{tag:16s} boards {len(R)}: live root writes == sim n {live_ok}/{live}; wrong n {bad_n}; "
          f"scan without preceding clear {bad_clear}; observer passive (final+DONE == vsim_pub2) {passive}/{len(R)}")
    return bad_n, bad_clear, passive == len(R), live


def sim_n(nes, o4, col, pA, pB, h0):
    import numpy as np
    pcol = np.zeros(128, dtype=np.int8); pvir = np.zeros(128, dtype=np.int8)
    for i, x in enumerate(nes):
        if x != 0xFF:
            pcol[i] = (x & 0x0F) + 1; pvir[i] = 1 if (x & 0xF0) == 0xD0 else 0
    bc = np.empty(128, dtype=np.int8); bv = np.empty(128, dtype=np.int8)
    if G._soft_b1(pcol, pvir, G.VAR_OF_O4[o4], col, pA + 1, pB + 1, bc, bv) == 0:
        return -1
    h = 0
    for c in range(2, 6):
        for r in range(16):
            if bc[r * 8 + c] != 0:
                h = max(h, 16 - r); break
    return h - h0 if h > h0 else 0


if __name__ == "__main__":
    res = {}
    for tag, arm, ref in (("D4", "D4", "D4"), ("D1", "D1", "D1"), ("mut_no_clear", "D4", "mut_no_clear"),
                          ("mut_row_off1", "D4", "mut_row_off1")):
        if os.path.isdir(os.path.join(VD, tag, "out")):
            if tag.startswith("mut_"):   # mutant co-sim jsonl is indexed 0..59 for lines 61..120
                pass
            res[tag] = check(tag, arm, ref)
    off = load("OFF") if os.path.isdir(os.path.join(VD, "OFF", "out")) else {}
    print(f"OFF              boards {len(off)}: D_DNG writes {sum(len(r['w']) for r in off.values())}")
    ok = (res["D4"][:2] == (0, 0) and res["D4"][2] and res["D1"][:2] == (0, 0) and res["D1"][2]
          and res["mut_no_clear"][1] > 0 and res["mut_row_off1"][0] > 0 and off and
          sum(len(r["w"]) for r in off.values()) == 0)
    print("RTL_DNG_GATE", "PASS" if ok else "FAIL")
