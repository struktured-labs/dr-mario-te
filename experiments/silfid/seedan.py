"""Seed-class co-sim analysis: per pill / class, does the timeline change vs seed 0, and does silicon's landing appear?"""
import json, collections, sys
import load
FI = load.fidelity(); MI = load.misses()
def canon(a, cur):
    if a is None or a < 0: return None
    return (a // 16) * 16 + a % 8 if cur[0] == cur[1] else a
base = {}
for g in load.GAMES:
    for p, r in load.pubtrace(g).items(): base[(g, p)] = r
R = collections.defaultdict(dict)
for fn in sys.argv[1:] or ["/home/struktured/projects/dr_mario_rl/tmp/silfid/cosim/seedcls.jsonl"]:
    for l in open(fn):
        r = json.loads(l); R[(r["game"], r["p"])][r["seed"]] = r
seeds = sorted({s for v in R.values() for s in v})
tab = collections.Counter(); per_game = collections.defaultdict(lambda: collections.Counter())
for (g, p), bys in sorted(R.items()):
    f = FI[(g, p)]; cur = f["cur"]; sil = canon(f["silicon"], cur)
    b = base[(g, p)]
    bset = {canon(x[3], cur) for x in b["pubs"]} | {canon(b["final"][2], cur)}
    so = (MI.get((g, p)) or {}).get("silicon_only")
    row = []
    for s in seeds:
        r = bys.get(s)
        if r is None: row.append("  ?"); continue
        same = [x[3] for x in r["pubs"]] == [x[3] for x in b["pubs"]] and r["final"][2] == b["final"][2]
        cset = {canon(x[3], cur) for x in r["pubs"]} | {canon(r["final"][2], cur)}
        newsil = (sil in cset) and (sil not in bset)
        row.append(" = " if same else (" S!" if newsil else " ~ "))
        per_game[g][(s, "same" if same else ("newsil" if newsil else "diff"))] += 1
    print(f"{g} p{p:3d} {'SO' if so else '  '} sil a{sil} base_has_sil={sil in bset!s:5s} |" + "".join(row))
print("seeds", seeds)
for g, c in per_game.items():
    print(g, " ".join(f"s{s}:{c[(s,'same')]}/{c[(s,'diff')]}/{c[(s,'newsil')]}" for s in seeds))
