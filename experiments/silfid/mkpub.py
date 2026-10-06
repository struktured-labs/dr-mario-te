"""Build a per-game pubtrace JSONL for a replay variant.
  mkpub.py OUT game seedcls <seed> [cosim.jsonl...]  : banked timelines, with pills found in the cosim files at that seed replaced
  mkpub.py OUT game shift <frames>                   : every publish time and done_f shifted (min 0.01)"""
import json, sys, os
CF = "/home/struktured/projects/dr-mario-h16-wt/experiments/couch_forensics"
out, game, mode, arg = sys.argv[1:5]
recs = [json.loads(l) for l in open(os.path.join(CF, f"pubtrace_{game}_lulu_20261005.jsonl"))]
n = 0
if mode == "seedcls":
    seed = int(arg); sub = {}
    for fn in sys.argv[5:]:
        for l in open(fn):
            r = json.loads(l)
            if r["game"] == game and r["seed"] == seed and r.get("spu_off", 0) == int(os.environ.get("SPU_OFF", "0")):
                sub[r["p"]] = r
    for r in recs:
        s = sub.get(r["p"])
        if s:
            r["pubs"] = s["pubs"]; r["done_f"] = s["done_f"]; r["final"] = s["final"]; r["tuck"] = s["tuck"]
            if os.environ.get("KEEP_UPLOAD", "1") != "1": r["upload"] = s["upload"]
            n += 1
elif mode == "spu":
    # Mesen-side gravity only: re-encode the upload's speedUps nibbles as (p + off)//10 (the copro timeline is unchanged)
    off = int(arg)
    for r in recs:
        t = r["upload"].split(); cA, cB, nA, nB = (int(v) for v in t[:4])
        spu = min(49, (r["p"] + off) // 10)
        nA = (nA & 0x0F) | ((spu & 0x0F) << 4)
        nB = (nB & 0x0F) | (((((spu >> 4) & 3) | (nB >> 4 & 0x0C))) << 4)
        r["upload"] = " ".join([str(cA), str(cB), str(nA), str(nB)] + t[4:]); n += 1
elif mode == "shift":
    d = float(arg)
    for r in recs:
        r["pubs"] = [[max(0.01, round(t + d, 2)), c, o, a] for t, c, o, a in r["pubs"]]
        r["done_f"] = max(0.02, round(r["done_f"] + d, 2)); n += 1
with open(out, "w") as f:
    for r in recs: f.write(json.dumps(r) + "\n")
print(f"{out}: {len(recs)} records, {n} modified")
