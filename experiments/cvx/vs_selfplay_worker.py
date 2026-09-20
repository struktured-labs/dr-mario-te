import sys, json, os
sys.path.insert(0, "/home/struktured/projects/dr-mario-h16-wt/experiments/cvx")
import import_pin
import_pin.pin()
import pressure_rig as PR
import vs_sim
from vs_choose import VsPolicy
PR._init(11, 0, 0)
from vs_choose import KNOBS
ma, mb, lo, cnt, step, out = (
    json.loads(sys.argv[1]), json.loads(sys.argv[2]),
    int(sys.argv[3]), int(sys.argv[4]), int(sys.argv[5]), sys.argv[6],
)
def _pol(d):
    return VsPolicy(**{k: d.get(k, 0.0) for k in KNOBS})
# each seed played BOTH seats (CRN). cnt is number of seeds, 2 rows each.
with open(out, "w") as fh:
    for i in range(cnt):
        s = lo + i * step
        for A, B, seat in ((ma, mb, 0), (mb, ma, 1)):
            pA, pB = _pol(A), _pol(B)
            r = vs_sim.play_vs(s, 11, pA, None, pB, None, wt=0, ws=0, send_rule="cells")
            # winner 0/1 is seat in this play; report as A-of-this-row
            fh.write(json.dumps({
                "seed": s, "seat": seat,
                "A": pA.name(), "B": pB.name(),
                "winner": r["winner"], "how": r["how"], "sent": r["sent"],
            }) + "\n")
            fh.flush()
