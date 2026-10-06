"""Print the game:p,p,... spec of every pill of a game NOT already co-simulated at a given seed in seedcls.jsonl."""
import json, sys, load
g, seed = sys.argv[1], int(sys.argv[2])
have = set()
for fn in sys.argv[3:]:
    for l in open(fn):
        r = json.loads(l)
        if r["game"] == g and r["seed"] == seed: have.add(r["p"])
ps = [p for p in sorted(load.pubtrace(g)) if p not in have]
print(f"{g}:{','.join(map(str, ps))}")
