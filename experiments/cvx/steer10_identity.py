"""STEER10 identity gate check: steer10/gate s10_base rows vs the banked steer8 fD_bdepD rows (every non-stamp key)."""
import json, glob
def load(pat, lab):
    d = {}
    for f in glob.glob(pat):
        for l in open(f):
            r = json.loads(l)
            if r.get("arm") == lab:
                d[r["seed"]] = r
    return d
for cell, glab, blab in (("gb10", "s10_base@owner202610", "fD_bdepD@owner202610"), ("rc10", "s10_base~steer", "fD_bdepD~steer"),
                         ("lulu10", "s10_base~steer", "fD_bdepD~steer")):
    G = load(f"steer10/gate/{cell}_s10_base.jsonl", glab); B = load(f"steer8/{cell}_fD_bdepD_*.jsonl", blab)
    both = [s for s in G if s in B]
    same = 0
    for s in both:
        bad = [k for k in B[s] if k not in ("arm", "rig") and G[s].get(k) != B[s].get(k)]
        same += not bad
        if bad:
            print(cell, s, "DIFF keys", bad)
    print(f"IDENTITY {cell}: {same}/{len(both)} rows identical on every non-stamp key")
S = [json.loads(l) for l in open("steer10/gate/smoke_lulu10b_s10_base.jsonl")]
for r in S:
    print("smoke lulu10b", r["seed"], r["how"], r["t_end"], "pills", r["pills"], "recv", r["tiles_recv"], "sizes", r["sizes"],
          "lam", r["lam"], "rule", r["rule"])
