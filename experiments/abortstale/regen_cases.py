#!/usr/bin/env python3
"""Rebuild a lateflip_probe case file from a CHAINED co-sim run (chain_cosim.py run), so the Mesen replay serves the
timelines the copro actually produces in the chained pipeline instead of the idle-copro (fresh) ones.

  regen_cases.py BANKED.jsonl CHAIN.jsonl OUT.jsonl OUT.lua
Per pill: board / upload / colours / silicon & python actions / vc stay the banked record's; pubs / done_f / final /
tuck come from the chained run. A pill whose search the chain ABORTED keeps its chained publishes before the abort and
the banked remainder after it (never served at a fixed point: the next GO preempts it at the same frame), and the
banked done_f / final / tuck. Case order and chain flags = the fair_v1_replay chained files (first pill unchained).
"""
import json
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
GEN = "/home/struktured/projects/dr_mario_rl/tmp/fair_v1_replay/tools/lateflip/gen_cases_lua.py"
FRAME = 29780.5 * 48


def main():
    banked, chain, out_jsonl, out_lua = sys.argv[1:5]
    B = [json.loads(l) for l in open(banked)]
    C = {json.loads(l)["p"]: json.loads(l) for l in open(chain)}
    with open(out_jsonl, "w") as f:
        for b in B:
            r = dict(b)
            c = C.get(b["p"])
            if c is not None:
                if c["end"] == "DONE":
                    r.update(pubs=c["pubs"], done_f=c["done_f"], final=c["final"], tuck=c["tuck"])
                else:
                    lim = round(c["end_clk"] / FRAME, 2)
                    r["pubs"] = [x for x in c["pubs"] if x[0] < lim] + [list(x) for x in b["pubs"] if x[0] >= lim]
            f.write(json.dumps(r) + "\n")
    ps = [str(b["p"]) if i == 0 else f"{b['p']}c" for i, b in enumerate(B)]
    subprocess.run([sys.executable, GEN, out_jsonl, out_lua] + ps, check=True)


if __name__ == "__main__":
    main()
