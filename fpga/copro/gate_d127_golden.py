#!/usr/bin/env python3
"""#127 gate: the firmware must be validated against THIS tree's nes_d3_golden.

THE DEFECT. tests/test_vrdy.py and tests/test_readiness_ext.py open with a hardcoded
`sys.path.insert(0, "/home/struktured/projects/dr-mario-mods")`. From that moment a sibling
worktree -- on whatever branch it is parked -- outranks this tree for every top-level name it
can supply. build_copro_d3.py defended ONE name (test_search_d3); MEASURED, fifteen more were
escaping, including `nes_d3_golden`, the golden the shipped-firmware py65 gate compares
against. The gate was therefore scoring this tree's firmware against another branch's
reference, and this tree's own golden never ran.

THE CHECKS
  C1  RESOLUTION. After importing build_copro_d3, nes_d3_golden -- and every other module
      this tree owns a copy of -- must resolve INSIDE this tree.
  C2  DECOY. Plant a same-named `nes_d3_golden.py` on a directory injected at sys.path[0]
      exactly the way test_vrdy does it. The fixed resolution must NOT pick it up. The decoy
      carries a sentinel, so "did not pick it up" is checked positively rather than inferred.
  C3  THE ASSERTION MUST BITE. Deliberately escape (COPRO_BOOTSTRAP_OFF=1, which disables
      ONLY the new shield -- the original single-name guard stays, so this isolates exactly
      the coverage #127 adds) and require build_copro_d3 to RAISE. An assertion that cannot
      fail is decoration; this proves C1's green is earned.

⚠ The decoy is written to a private temp dir and put on sys.path the way the offending files
do. It is NEVER written into dr-mario-mods: planting a file in another lane's checkout to
test your own gate is how you corrupt someone else's run.

Exit: 0 all pass · 1 a check failed
"""
from __future__ import annotations

import os
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
PY = sys.executable
SENTINEL = "D127_DECOY_SENTINEL"

C1 = r"""
import sys; sys.argv = ["gate"]
sys.path.insert(0, {here!r})
import build_copro_d3            # noqa: F401  -- installs the shield, runs the assertion
import copro_bootstrap as CB
import nes_d3_golden as G
print("GOLDEN=" + (G.__file__ or "?"))
print("SENTINEL=" + str(getattr(G, {sent!r}, None)))
print("OFFENDERS=" + repr(CB.offenders({root!r})))
"""

DECOY = f'''"""Decoy planted by gate_d127_golden.py. If this module is ever imported as
nes_d3_golden the shield has failed and the firmware is being graded against the wrong file."""
{SENTINEL} = True
def decide_d3(*a, **k):
    raise AssertionError("the DECOY nes_d3_golden was executed -- #127 has regressed")
'''


def run(src, env=None, cwd=HERE):
    return subprocess.run([PY, "-c", src], capture_output=True, text=True,
                          env=env or os.environ.copy(), cwd=cwd)


def main():
    ok = True

    # ---- C1: resolution ----------------------------------------------------------
    p = run(C1.format(here=HERE, root=ROOT, sent=SENTINEL))
    if p.returncode != 0:
        print(f"C1 FAIL: build_copro_d3 did not import (rc={p.returncode})")
        print("   " + p.stderr.strip()[-500:])
        return 1
    out = dict(l.split("=", 1) for l in p.stdout.strip().splitlines() if "=" in l)
    golden = out.get("GOLDEN", "")
    inside = os.path.abspath(golden).startswith(ROOT + os.sep)
    print(f"C1 resolution   nes_d3_golden -> {golden}")
    print(f"   {'OK  ' if inside else 'FAIL'} inside this tree ({ROOT})")
    offs = out.get("OFFENDERS", "[]")
    clean = offs.strip() == "[]"
    print(f"   {'OK  ' if clean else 'FAIL'} modules resolved outside the tree: {offs}")
    ok &= inside and clean

    # ---- C2: decoy on an injected sys.path[0] ------------------------------------
    with tempfile.TemporaryDirectory(prefix="d127_decoy_") as td:
        with open(os.path.join(td, "nes_d3_golden.py"), "w") as fh:
            fh.write(DECOY)
        src = (f"import sys\nsys.path.insert(0, {td!r})\n"
               + C1.format(here=HERE, root=ROOT, sent=SENTINEL))
        p2 = run(src)
        if p2.returncode != 0:
            print(f"C2 FAIL: import raised with the decoy present (rc={p2.returncode})")
            print("   " + p2.stderr.strip()[-400:])
            ok = False
        else:
            o2 = dict(l.split("=", 1) for l in p2.stdout.strip().splitlines() if "=" in l)
            took_decoy = o2.get("SENTINEL") != "None" or td in o2.get("GOLDEN", "")
            print(f"C2 decoy        planted at sys.path[0]: {td}")
            print(f"   resolved -> {o2.get('GOLDEN','?')}   sentinel={o2.get('SENTINEL')}")
            print(f"   {'FAIL -- decoy WON' if took_decoy else 'OK   decoy ignored'}")
            ok &= not took_decoy

    # ---- C3: the assertion must bite ---------------------------------------------
    env = dict(os.environ, COPRO_BOOTSTRAP_OFF="1")
    p3 = run(C1.format(here=HERE, root=ROOT, sent=SENTINEL), env=env)
    bit = p3.returncode != 0 and "resolved OUTSIDE this worktree" in p3.stderr
    print(f"C3 mutant       COPRO_BOOTSTRAP_OFF=1 -> rc={p3.returncode}")
    if bit:
        n = p3.stderr.count("  ->  ")
        print(f"   OK   KILLED: assert_self_contained raised and named {n} escaped module(s)")
    else:
        print("   FAIL SURVIVED: escaping the shield did not raise the self-containment "
              "error -- C1's green is unearned")
        print("   " + (p3.stderr.strip()[-400:] or "<no stderr>"))
    ok &= bit

    print("\nPASS" if ok else "\nFAIL")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
