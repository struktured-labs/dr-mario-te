import sys, json
sys.path.insert(0, "/home/struktured/projects/dr-mario-h16-wt/experiments/cvx")
import import_pin
import_pin.pin()
import pressure_rig as PR
from vs_choose import VsPolicy, KNOBS
from clock_play import play_hartford
PR._init(11, 0, 0)
d = json.loads(sys.argv[1])
lo, cnt, step, out = int(sys.argv[2]), int(sys.argv[3]), int(sys.argv[4]), sys.argv[5]
pol = VsPolicy(**{k: d.get(k, 0.0) for k in KNOBS})
with open(out, "w") as fh:
    for i in range(cnt):
        s = lo + i * step
        r = play_hartford(s, pol)
        r["A"] = pol.name()
        fh.write(json.dumps(r) + "\n")
        fh.flush()
