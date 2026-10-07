"""STEER13 identity gate: A_fair_q00 and B_orc6_q00 == FAIR's banked rows (lulu: steer11 pilot couch11 s10_base; gb:
steer8 fD_bdepD) on every non-stamp key except the stuck probe (part B runs without it). Positive control: the lulu
gate rows vs the banked A16 pilot rows must differ. Smokes: every arm active (misses / non-final commits / tempo)."""
import json, glob, os, sys
os.chdir(os.path.dirname(os.path.abspath(__file__)))
SKIP = ("arm", "rig", "knob", "stuck")


def load(pat, lab):
    d = {}
    for f in glob.glob(pat):
        for l in open(f):
            r = json.loads(l)
            if r.get("arm") == lab:
                d[r["seed"]] = r
    return d


ok = True
for a in ("A_fair_q00", "B_orc6_q00_fairref"):
    for cell, gp, gl, bp, bl in (("lulu", f"steer13/gate/lulu_{a}.jsonl", f"{a}~steer", "steer11/pilot/lulu10b_c11_s10_base_*.jsonl", "s10_base~steer"),
                                 ("gb", f"steer13/gate/gb_{a}.jsonl", f"{a}@owner202610", "steer8/gb10_fD_bdepD_*.jsonl", "fD_bdepD@owner202610")):
        G, B = load(gp, gl), load(bp, bl)
        both = [s for s in G if s in B]
        bad = [(s, [k for k in B[s] if k not in SKIP and G[s].get(k) != B[s].get(k)]) for s in both]
        bad = [x for x in bad if x[1]]
        if a.startswith("A"):                       # part A keeps the stuck probe: it must match too
            bad += [(s, ["stuck"]) for s in both if G[s].get("stuck") != B[s].get("stuck")]
        good = len(both) > 0 and not bad
        ok &= good
        print(f"IDENTITY {a} {cell}: {len(both) - len(bad)}/{len(both)} identical" + (f"  DIFF {bad[:2]}" if bad else ""))
G = load("steer13/gate/lulu_B_orc6_q00_fairref.jsonl", "B_orc6_q00_fairref~steer")
B = load("steer11/pilot/lulu10b_c11_s10_A16_*.jsonl", "s10_A16~steer")
both = [s for s in G if s in B]
nd = sum(1 for s in both if any(G[s].get(k) != B[s].get(k) for k in B[s] if k not in SKIP))
ok &= nd > 0
print(f"POSITIVE CONTROL B_orc6_q00_fairref vs banked A16 (must differ): {nd}/{len(both)} rows differ")
for f in sorted(glob.glob("steer13/gate/smoke_*.jsonl")):
    for l in open(f):
        r = json.loads(l); k = r["knob"]; spec = r["rig"]["knob"]
        if spec["part"] == "A":
            act = k["miss"] > 0
        elif spec["fw"] == "orc":
            act = abs(k["tempo_f"]) > 0
        else:
            act = k["nonfinal_commit"] > 0 or k["late"] > 0
        if spec["part"] == "B" and spec["fw"] == "1488" and spec["mt"] == 6:      # it IS the reference: tempo 0
            cons = k["tempo_f"] == 0
            ok &= cons
            print(f"CONSISTENCY {os.path.basename(f)} seed {r['seed']}: tempo charged {k['tempo_f']} (must be 0) -> "
                  f"{'ok' if cons else 'FAIL'}")
        ok &= bool(act)
        print(f"SMOKE {os.path.basename(f)} seed {r['seed']}: how {r['how']} pills {r['pills']} t_end {r.get('t_end', r.get('elapsed_s'))} "
              f"knob {k} -> {'active' if act else 'INACTIVE'}")
print("STEER13 IDENTITY GATE", "PASS" if ok else "FAIL")
sys.exit(0 if ok else 1)
