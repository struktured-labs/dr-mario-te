"""VS pairing worker. Pins the import graph, then plays cnt games.

Env:
  VS_SEND_RULE=cells|lines   (default cells)
  VS_WS=0                    (default 0 = cart DRSTRAND; loop gens 0-2 used 20)
"""
import sys, json, os
sys.path.insert(0, "/home/struktured/projects/dr-mario-h16-wt/experiments/cvx")
import import_pin
loaded = import_pin.pin()
import pressure_rig as PR
import vs_sim, population as POP
WS = int(os.environ.get("VS_WS", "0"))
SEND = os.environ.get("VS_SEND_RULE", "cells")
assert SEND in ("cells", "lines")
PR._init(11, 0, WS)
ma, mb, lo, cnt, step, out = (
    json.loads(sys.argv[1]), json.loads(sys.argv[2]),
    int(sys.argv[3]), int(sys.argv[4]), int(sys.argv[5]), sys.argv[6],
)
with open(out, "w") as fh:
    for i in range(cnt):
        s = lo + i * step
        wA, fA = POP.make_policy(ma)
        wB, fB = POP.make_policy(mb)
        r = vs_sim.play_vs(s, 11, wA, fA, wB, fB, wt=0, ws=WS, send_rule=SEND)
        fh.write(json.dumps({
            "seed": s, "A": POP.name(ma), "B": POP.name(mb),
            "winner": r["winner"], "how": r["how"], "sent": r["sent"],
            "ws": WS, "send_rule": SEND,
        }) + "\n")
        fh.flush()
