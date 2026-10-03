#!/usr/bin/env python3
"""Turn publish-timeline records (pubtrace JSONL, one per case) into the Lua data file lateflip_probe.lua loads.

Each JSONL record needs: p, upload ("cA cB nA nB <128 hex>", the exact bytes the couch cart uploads), pubs
([[t_frames_since_GO, col, o4, action], ...] -- valid publishes only, after the firmware's $FF store), done_f,
final ([col, o4, action]), tuck ([tcol, trow], optional -> no tuck), actual_action (silicon), sim_action (python
brain), virus count vc. Optional: chain (true -> inject at the very next spawn even if the previous search still runs).

Usage: gen_cases_lua.py IN.jsonl OUT.lua [p ...]   (p list = which cases, in order; default all)
"""
import json
import sys


def lua_list(xs):
    return "{" + ",".join(str(int(x)) for x in xs) + "}"


def main():
    src, out = sys.argv[1], sys.argv[2]
    recs = {}
    order = []
    for line in open(src):
        r = json.loads(line)
        recs[r["p"]] = r
        order.append(r["p"])
    want = [int(x.rstrip("c")) for x in sys.argv[3:]] or order
    chain = {int(x.rstrip("c")) for x in sys.argv[3:] if x.endswith("c")}
    parts = ["return {"]
    for p in want:
        r = recs[p]
        t = r["upload"].split()
        cA, cB, nA, nB = (int(v) for v in t[:4])
        board = [int(v, 16) for v in t[4:]]
        assert len(board) == 128
        upload = board + [cA, cB, nA, nB]
        pubs = ",".join("{%.4f,%d,%d}" % (pt[0], pt[1], pt[2]) for pt in r["pubs"])
        tuck = r.get("tuck") or [255, 0]
        spu = ((nA >> 4) & 0x0F) | ((nB >> 4) & 0x03) << 4
        parts.append(
            "  {p=%d, chain=%s, board=%s, upload=%s, cur={%d,%d}, nxt={%d,%d}, spu=%d, vc=%d, actual=%d, sim=%d, fin=%d,"
            " sched={pubs={%s}, done_f=%.4f, final={%d,%d}, tuck={%d,%d}}},"
            % (p, "true" if p in chain else "false", lua_list(board), lua_list(upload), cA & 3, cB & 3, nA & 3, nB & 3,
               spu, r["vc"], -1 if r["actual_action"] is None else r["actual_action"],
               -1 if r["sim_action"] is None else r["sim_action"], r["final"][2], pubs, r["done_f"], r["final"][0],
               r["final"][1], tuck[0], tuck[1]))
    parts.append("}")
    open(out, "w").write("\n".join(parts) + "\n")
    print(f"wrote {len(want)} cases -> {out}")


if __name__ == "__main__":
    main()
