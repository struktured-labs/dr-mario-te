#!/usr/bin/env python3
"""Is a DRDBLCANON x DRCOPRO_TUCKV3 combination arm MEANINGFUL in this rig?

nmi-fix's warning is right and this project has two precedents (DRPRESTART x
DRTUCK wedge, DRRTIVEC x DRMMC1RST mutual brick): flag interactions must be
gated as COMBINATIONS.  But there is an equally hard precedent in the other
direction -- `dr-mario-tuck-mailbox-vacuous-gate`: the stock py65 rig never
serves the tuck mailbox, so a tuck gate can be **silently inert** and report a
green combination arm that established nothing.

So before claiming any combination result, this probe asks the prior question:
**does DRCOPRO_TUCKV3 change ANY decision in this harness?**  If turning the
tuck emitter on and off leaves every published (col, orient) identical, the tuck
path never fired, and a combination arm here would be vacuous by construction --
which is a finding to report, not a gate to pass.
"""

import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(ROOT, "fpga", "copro"))
sys.path.insert(0, os.path.join(ROOT, "tests"))

import gate_dblcanon as G  # noqa: E402


def images(B, D3, tuck, canon):
    os.environ["DRCOPRO_TUCKV3"] = "1" if tuck else "0"
    os.environ["DRDBLCANON"] = "1" if canon else "0"
    import importlib
    importlib.reload(B)                     # EMIT_TUCK_V3 is read at module scope
    img, clen, _ = B.build_image([0xFF] * 128, 0, 0, 0, 0)
    _c, labels = D3.build()
    return img, 0x8000 + labels["search"], clen


def main():
    import random
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
    for k, v in arms.items():
        print(f"  tuck={int(k[0])} canon={int(k[1])}: search={v[2]}B")

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
            if r[(True, False)] != r[(False, False)]:
                tuck_binds += 1
            if r[(False, True)] != r[(False, False)]:
                canon_binds += 1
            if r[(True, True)] != r[(True, False)]:
                both += 1

    print(f"\ndouble decisions compared: {n}")
    print(f"  DRCOPRO_TUCKV3 changed the decision : {tuck_binds}")
    print(f"  DRDBLCANON changed the decision     : {canon_binds}")
    print(f"  DRDBLCANON changed it WITH tuck on  : {both}")
    if tuck_binds == 0:
        print("\nVERDICT: the tuck path is INERT in this harness (it never served a\n"
              "CANDLIST), so a DRDBLCANON x DRTUCK combination arm measured HERE would\n"
              "be VACUOUS. The combination must be gated on a rig that serves the tuck\n"
              "mailbox, or on silicon, before any cart carries both flags.")
        return 2
    print("\nVERDICT: the tuck path BINDS here -- a combination arm is meaningful and\n"
          "must be run.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
