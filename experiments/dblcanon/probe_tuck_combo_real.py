#!/usr/bin/env python3
"""Combination arm (a), on the ACTUAL SHIPPED θ400 LINEAGE.

⚠ WHY THIS FILE EXISTS: `probe_tuck_combo.py` toggled `DRCOPRO_TUCKV3`, but the
shipped θ400 firmware (`f78f1e93`, inside BOTH the MiSTer core `de7dea35` and the
Pocket core `89fddd61`) is built with a DIFFERENT tuck stack:

    DRSTRAND=20 DRCHAIN=180 DRCOPRO_ARM=1 DRFIX=1
    DRCOPRO_TUCKBFS=1 DRCOPRO_TUCKBFS_TIER3=1
    DRCOPRO_TUCKV3_FIXSLOT=1 DRCOPRO_TUCKV3_THETA=400

`DRCOPRO_TUCKBFS` (the BFS enumerator + tier-3 widening) is NOT `DRCOPRO_TUCKV3`
(tuck_scan_v3).  So the earlier "the tuck path is inert in this harness" result
was measured against a tuck enumerator THAT IS NOT THE ONE THAT SHIPS — the same
class of lineage error as testing a cart flag for a core feature.  It is
re-derived here against the real recipe.

Question, unchanged: does the tuck path change ANY decision in this harness?  If
not, a combination arm measured here is vacuous and the arm stays open for a rig
that serves the tuck mailbox, or silicon.
"""

import importlib
import os
import random
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(ROOT, "fpga", "copro"))
sys.path.insert(0, os.path.join(ROOT, "tests"))

import gate_dblcanon as G  # noqa: E402

# The shipped θ400 firmware recipe, minus the tuck stack (toggled below).
BASE = {"DRSTRAND": "20", "DRCHAIN": "180", "DRCOPRO_ARM": "1", "DRFIX": "1",
        "DRCOPRO_TUCKV3_FIXSLOT": "1", "DRCOPRO_TUCKV3_THETA": "400"}
TUCK = {"DRCOPRO_TUCKBFS": "1", "DRCOPRO_TUCKBFS_TIER3": "1"}


def images(B, D3, tuck, canon):
    for k, v in BASE.items():
        os.environ[k] = v
    for k in TUCK:
        os.environ[k] = "1" if tuck else "0"
    os.environ["DRCOPRO_TUCKV3"] = "0"
    os.environ["DRDBLCANON"] = "1" if canon else "0"
    importlib.reload(B)                  # tuck flags are read at module scope
    img, clen, _ = B.build_image([0xFF] * 128, 0, 0, 0, 0)
    _c, labels = D3.build()
    return img, 0x8000 + labels["search"], clen


def main():
    B, D3 = G._load()
    FSIM = os.environ.get(
        "DRM_FAITHFUL_SIM",
        "/home/struktured/projects/dr_mario_rl/.claude/worktrees/faithful-sim")
    for p in (os.path.join(FSIM, "src"), os.path.join(FSIM, "tmp")):
        if p not in sys.path:
            sys.path.insert(0, p)
    from drmario.faithful_game import FaithfulBoard
    from xcheck_terms import faithful_to_nes
    from test_search_d3 import make_fewlegal

    arms = {}
    for tuck in (False, True):
        for canon in (False, True):
            arms[(tuck, canon)] = images(B, D3, tuck, canon)
            print(f"  tuckbfs={int(tuck)} canon={int(canon)}: "
                  f"search={arms[(tuck, canon)][2]}B")

    rng = random.Random(20260818)
    tseeds = [(t | 1) ^ 0xA4 for t in (0x10, 0x3A)]
    n = tuck_binds = canon_binds = both = 0
    for _ in range(12):
        fb = make_fewlegal(rng, FaithfulBoard)
        nes = list(faithful_to_nes(fb))
        c = rng.randint(0, 2)
        na, nb = rng.randint(0, 2), rng.randint(0, 2)
        for ts in tseeds:
            r = {}
            for k, (img, ep, _c) in arms.items():
                r[k] = G.run_fw(B, D3, img, ep, nes, c, c, na, nb, ts)
            if r[(False, False)] is None:
                continue
            n += 1
            tuck_binds += r[(True, False)] != r[(False, False)]
            canon_binds += r[(False, True)] != r[(False, False)]
            both += r[(True, True)] != r[(True, False)]

    print(f"\nSHIPPED-LINEAGE probe (theta400: TUCKBFS+TIER3+FIXSLOT+THETA=400)")
    print(f"double decisions compared: {n}")
    print(f"  DRCOPRO_TUCKBFS changed the decision : {tuck_binds}")
    print(f"  DRDBLCANON changed the decision      : {canon_binds}")
    print(f"  DRDBLCANON changed it WITH tuck on   : {both}")
    if tuck_binds == 0:
        print("\nVERDICT: the tuck path is INERT here too, on the REAL lineage.\n"
              "A combination arm measured in this harness is vacuous. Arm (a)\n"
              "stays OPEN and needs a rig that serves the tuck mailbox, or silicon.")
        return 2
    print("\nVERDICT: the tuck path BINDS on the real lineage -- the combination\n"
          "arm is meaningful HERE and must be run to completion.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
