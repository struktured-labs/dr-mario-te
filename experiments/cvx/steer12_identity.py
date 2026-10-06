"""STEER12 identity gate: the identity arms lat0 / q00 (Knob wrapper, no shift, no miss) must reproduce FAIR's banked
rows on every non-stamp key: LULU race + owner race = the steer11 pilot couch11 rows, gate b = steer8 fD_bdepD.
Also prints the smoke rows' activity (every arm must be ACTIVE: rule 26). POSITIVE CONTROL: the lat_m6 / ex_q15 smoke
row of seed 36734 must differ from the lat0-equivalent... (smokes have no banked twin) -> control = lat0 gate rows vs the
pilot s10_A16 rows on the same seeds (a different brain): must differ."""
import json, glob, os, sys
os.chdir(os.path.dirname(os.path.abspath(__file__)))
STAMP = ("arm", "rig", "knob")


def load(pat, lab):
    d = {}
    for f in glob.glob(pat):
        for l in open(f):
            r = json.loads(l)
            if r.get("arm") == lab:
                d[r["seed"]] = r
    return d


ok = True
for a in ("lat0", "q00"):
    for cell, gp, gl, bp, bl in (("lulu", f"steer12/gate/lulu12_{a}.jsonl", f"{a}~steer", "steer11/pilot/lulu10b_c11_s10_base_*.jsonl", "s10_base~steer"),
                                 ("rc", f"steer12/gate/rc12_{a}.jsonl", f"{a}~steer", "steer11/pilot/rc10_c11_s10_base_*.jsonl", "s10_base~steer"),
                                 ("gb", f"steer12/gate/gb12_{a}.jsonl", f"{a}@owner202610", "steer8/gb10_fD_bdepD_*.jsonl", "fD_bdepD@owner202610")):
        G, B = load(gp, gl), load(bp, bl)
        both = [s for s in G if s in B]
        bad = [(s, [k for k in B[s] if k not in STAMP and G[s].get(k) != B[s].get(k)]) for s in both]
        bad = [x for x in bad if x[1]]
        good = len(both) > 0 and not bad
        ok &= good
        print(f"IDENTITY {a} {cell}: {len(both) - len(bad)}/{len(both)} identical" + (f"  DIFF {bad[:2]}" if bad else ""))
G = load("steer12/gate/lulu12_lat0.jsonl", "lat0~steer")
B = load("steer11/pilot/lulu10b_c11_s10_A16_*.jsonl", "s10_A16~steer")
both = [s for s in G if s in B]
nd = sum(1 for s in both if any(G[s].get(k) != B[s].get(k) for k in B[s] if k not in STAMP))
ctl = nd > 0
ok &= ctl
print(f"POSITIVE CONTROL lat0 vs banked A16 (must differ): {nd}/{len(both)} rows differ -> {'alive' if ctl else 'DEAD CHECKER'}")
for f in sorted(glob.glob("steer12/gate/smoke_*.jsonl")):
    for l in open(f):
        r = json.loads(l); k = r["knob"]
        act = (k["miss"] > 0) if "q" in r["rig"]["knob"] and r["rig"]["knob"].get("q", 0) > 0 else \
              (abs(k["tempo_f"]) > 0) if r["rig"]["knob"]["kind"] in ("lat", "ceil") and "lulu" in f else True
        print(f"SMOKE {os.path.basename(f)}: how {r['how']} pills {r['pills']} knob {k} -> {'active' if act else 'INACTIVE'}")
        ok &= bool(act)
print("STEER12 IDENTITY GATE", "PASS" if ok else "FAIL")
sys.exit(0 if ok else 1)
