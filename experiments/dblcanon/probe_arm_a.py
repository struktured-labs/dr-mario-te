#!/usr/bin/env python3
"""Combination arm (a), SUBPROCESS-ISOLATED — supersedes both earlier probes.

⚠⚠ WHY THE EARLIER PROBES WERE INVALID, and it is worth stating plainly because
both of their headline numbers went into a report and a teammate was asked to
preserve one of them:

`probe_tuck_combo.py` and `probe_tuck_combo_real.py` switched build flags with
`importlib.reload(build_copro_d3)` inside ONE process.  The reload re-executes
that module's import-order guard, and the interaction leaves the flag state
inconsistent — MEASURED: with `DRCOPRO_TUCKBFS=1` and `DRDBLCANON=1` in the
environment, the reload path built an image with `D3.DBLCANON == 0` and ZERO
canonicalisation bytes, while a FRESH PROCESS with identical environment built
`clen=2483` containing `AND #$FE` exactly once.  The reload silently zeroed the
very flags the probes were toggling.

So the earlier readings — "DRCOPRO_TUCKV3/TUCKBFS changed the decision: 0/24,
therefore the tuck path is inert" and the "0-vs-12" contrast offered as an
internal positive control — measured the reload bug, not the firmware.  Both are
WITHDRAWN.  This file answers the question with each arm in its own process, so
no flag state can leak or reset between arms.
"""

import json
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
PY = sys.executable

BASE = {"DRSTRAND": "20", "DRCHAIN": "180", "DRCOPRO_ARM": "1", "DRFIX": "1",
        "DRCOPRO_TUCKV3_FIXSLOT": "1", "DRCOPRO_TUCKV3_THETA": "400"}

WORKER = r'''
import json, os, sys
ROOT = os.environ["DRM_ROOT"]
sys.path.insert(0, os.path.join(ROOT, "fpga", "copro"))
sys.path.insert(0, os.path.join(ROOT, "tests"))
sys.path.insert(0, os.path.join(ROOT, "experiments", "dblcanon"))
import gate_dblcanon as G
B, D3 = G._load()
FSIM = os.environ.get("DRM_FAITHFUL_SIM",
    "/home/struktured/projects/dr_mario_rl/.claude/worktrees/faithful-sim")
for p in (os.path.join(FSIM, "src"), os.path.join(FSIM, "tmp")):
    if p not in sys.path:
        sys.path.insert(0, p)
from drmario.faithful_game import FaithfulBoard
from xcheck_terms import faithful_to_nes
from test_search_d3 import make_fewlegal
import random

img, clen, _ = B.build_image([0xFF] * 128, 0, 0, 0, 0)
_c, labels = D3.build()
ep = 0x8000 + labels["search"]
rom = bytes(img[0x8000:0xC000])
canon_bytes = sum(1 for i in range(len(rom) - 1)
                  if rom[i] == 0x29 and rom[i + 1] == 0xFE)

rng = random.Random(20260818)
tseeds = [(t | 1) ^ 0xA4 for t in (0x10, 0x3A)]
out = []
for _ in range(12):
    fb = make_fewlegal(rng, FaithfulBoard)
    nes = list(faithful_to_nes(fb))
    c = rng.randint(0, 2)
    na, nb = rng.randint(0, 2), rng.randint(0, 2)
    for ts in tseeds:
        out.append(G.run_fw(B, D3, img, ep, nes, c, c, na, nb, ts))
print("RESULT" + json.dumps({
    "clen": clen, "canon_bytes": canon_bytes,
    "dblcanon": int(D3.DBLCANON), "tuckbfs": bool(B.EMIT_TUCK_BFS),
    "decisions": out}))
'''


def arm(tuck, canon):
    env = dict(os.environ)
    env.update(BASE)
    env["DRM_ROOT"] = ROOT
    env["DRCOPRO_TUCKBFS"] = "1" if tuck else "0"
    env["DRCOPRO_TUCKBFS_TIER3"] = "1" if tuck else "0"
    env["DRCOPRO_TUCKV3"] = "0"
    env["DRDBLCANON"] = "1" if canon else "0"
    p = subprocess.run([PY, "-c", WORKER], env=env, capture_output=True,
                       text=True, timeout=3600)
    line = [l for l in p.stdout.splitlines() if l.startswith("RESULT")]
    if not line:
        print(p.stdout[-2000:], p.stderr[-2000:])
        raise RuntimeError(f"arm tuck={tuck} canon={canon} produced no result")
    return json.loads(line[0][6:])


def main():
    r = {}
    for tuck in (False, True):
        for canon in (False, True):
            r[(tuck, canon)] = a = arm(tuck, canon)
            print(f"  tuckbfs={int(tuck)} canon={int(canon)}: clen={a['clen']} "
                  f"AND#$FE={a['canon_bytes']} DBLCANON={a['dblcanon']} "
                  f"EMIT_TUCK_BFS={a['tuckbfs']}")

    # PLUMBING CONTROL: every arm must have built what it claims to have built.
    bad = [k for k, a in r.items()
           if a["dblcanon"] != int(k[1]) or a["tuckbfs"] != k[0]
           or a["canon_bytes"] != int(k[1])]
    if bad:
        print(f"\n⚠ PLUMBING FAILURE in arms {bad} — flags did not reach the "
              f"build. Any decision numbers below are meaningless.")
        return 3

    def diff(a, b):
        da, db = r[a]["decisions"], r[b]["decisions"]
        return sum(1 for x, y in zip(da, db) if x != y and x is not None)

    n = sum(1 for x in r[(False, False)]["decisions"] if x is not None)
    print(f"\nARM (a), subprocess-isolated, shipped θ400 lineage")
    print(f"double decisions compared: {n}")
    print(f"  DRCOPRO_TUCKBFS changed the decision : "
          f"{diff((False, False), (True, False))}")
    print(f"  DRDBLCANON changed the decision      : "
          f"{diff((False, False), (False, True))}")
    print(f"  DRDBLCANON changed it WITH tuck on   : "
          f"{diff((True, False), (True, True))}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
