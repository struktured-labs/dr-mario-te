#!/usr/bin/env python3
"""#137 self-containment + skip gate for hmin_neardeath.py.

Reproducing the published medians proves the rig still MEASURES the same thing. It does NOT
prove the rig is reachable from git -- a run on this box would reproduce them just as happily
by importing the gitignored `dr_mario_rl/tmp/vs_aware` tree the vendoring exists to escape.
So this gate checks the two things the numbers cannot:

  A1 THE #137 BLOCKER (gating). No module may resolve inside a GITIGNORED tmp/ tree or a
     session scratchpad. That is what vendoring this rig was for: the published table used to
     rest on `dr_mario_rl/tmp/vs_aware`, which no clone can reach and which a scratchpad clean
     would delete. This check FAILS the gate.
  A2 FULL CLEAN-CLONE REACHABILITY (reported, KNOWN GAP -- see below). No module may resolve
     outside the repo AT ALL. Same shape as gate_clean_clone.sh's check C (repro-19).

⚠ A2 CURRENTLY FAILS, and it is reported rather than fixed here -- deliberately, with reasons.
The escape is NOT in this rig: `transfer_check.py` (a sibling this whole directory imports)
pulls `drmario.faithful_game` from `dr_mario_rl/.claude/worktrees/faithful-sim/src`, an
UNPUSHED agent worktree. So it is a property of cosim_farm, not of hmin_neardeath, and it
predates the vendoring. It is NOT folded into A1 because the two have different owners and
different risks, and collapsing them would either hide the blocker being fixed or manufacture
a red gate for work this task does not own (task #118).

The tempting fix -- copy faithful_game.py in here and pin it -- is the WRONG one. repro-19
already vendored that exact module under a SEALED sha256 manifest in its own repo, and #19's
audit found origin already carrying a DIFFERENT faithful_game.py. Adding a third copy from a
fourth location is how that divergence happened in the first place. Whoever closes #118 should
reuse repro-19's sealed vendor, not fork another.
  B  AUTHORITATIVE OVERRIDE. DRMARIO_HOSTDATA pointing at a missing file must SKIP (77), not
     silently fall through to /mnt/data and print a confident PASS against a corpus nobody
     asked for. That defect was introduced into the sibling ROM gate by exactly this kind of
     fix (d513562) and was caught only by a skip test -- so here is the skip test.

KILLED MUTANTS -- an assertion that cannot fail is not a check:
  m_escape   import the gitignored vs_harness BEFORE measuring. Check A must CATCH it.
             Without this, A would pass on a broken checker that inspects nothing.
  m_absent   point the override at a missing path. Check B must yield 77, never 0.

Exit: 0 all checks pass · 1 a check failed
"""
from __future__ import annotations

import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(HERE))
PY = sys.executable

# A1: the #137 blocker -- gitignored trees and session scratchpads. GATING.
BLOCKER = ("/dr_mario_rl/tmp/", "/scratchpad/", "/tmp/claude-")
# A2: everything else outside the repo. REPORTED (see the docstring: task #118).
OUTSIDE_EXTRA = ("/.claude/worktrees/",)

AUDIT = r"""
import os, sys, json
sys.path.insert(0, {here!r})
{preload}
import hmin_neardeath as H
try:
    H.measure()
except H.Skip as e:
    print("SKIP:" + str(e)); raise SystemExit(77)
seen = []
for name, mod in list(sys.modules.items()):
    f = getattr(mod, "__file__", None)
    if f:
        seen.append((name, os.path.abspath(f)))
print(json.dumps(seen))
"""


def resolved_modules(preload=""):
    src = AUDIT.format(here=HERE, preload=preload)
    p = subprocess.run([PY, "-c", src], capture_output=True, text=True, cwd=HERE)
    if p.returncode == 77:
        return None, p.stdout.strip()
    if p.returncode != 0:
        return None, f"audit failed rc={p.returncode}: {p.stderr.strip()[-400:]}"
    import json
    return json.loads(p.stdout.strip().splitlines()[-1]), ""


def offenders(mods, pats):
    return [(n, f) for n, f in mods if any(p in f for p in pats)]


def main():
    ok = True

    # ---- A1: no gitignored / scratchpad module (GATING) ---------------------------
    mods, err = resolved_modules()
    if mods is None:
        print(f"FAIL check A1: {err}")
        return 1
    bad = offenders(mods, BLOCKER)
    print(f"check A1 gitignored/scratchpad imports: {len(mods)} modules resolved, "
          f"{len(bad)} in a tree no clone can reach")
    for name, f in bad:
        print(f"   ESCAPED  {name}  ->  {f}")
    ok &= not bad

    # ---- m_escape: the checker must be able to FAIL -------------------------------
    preload = ("sys.path.insert(0, '/home/struktured/projects/dr_mario_rl/tmp/vs_aware')\n"
               "import rom_attack_rule\n")
    mods_m, err_m = resolved_modules(preload)
    if mods_m is None:
        print(f"  m_escape  INCONCLUSIVE ({err_m}) -- the gitignored tree is already gone "
              "on this box, so the mutant cannot be planted. A1 is UNPROVEN here, which is "
              "a failure, not a pass.")
        ok = False
    else:
        caught = offenders(mods_m, BLOCKER)
        print(f"  m_escape  {'KILLED' if caught else 'SURVIVED'}: planted a gitignored "
              f"import, checker flagged {len(caught)}")
        ok &= bool(caught)

    # ---- A2: full clean-clone reachability (REPORTED, known gap #118) -------------
    out = offenders(mods, BLOCKER + OUTSIDE_EXTRA)
    print(f"\ncheck A2 full clean-clone reachability: {len(out)} modules outside the repo "
          "[KNOWN GAP -- reported, does not gate]")
    for name, f in out:
        print(f"   OUTSIDE  {name}  ->  {f}")
    if out:
        print("   ^ transfer_check.py's dependency, shared by all of cosim_farm and older than"
              "\n     this vendoring. Owner: task #118. Reuse repro-19's SEALED faithful_game"
              "\n     vendor -- do NOT add a third copy (#19 already found two that differed).")

    # ---- B: the override is authoritative ----------------------------------------
    env = dict(os.environ, DRMARIO_HOSTDATA="/nonexistent/death_hostdata.txt")
    p = subprocess.run([PY, os.path.join(HERE, "hmin_neardeath.py")],
                       capture_output=True, text=True, env=env, cwd=HERE)
    good = p.returncode == 77 and "Refusing to fall back" in (p.stderr + p.stdout)
    print(f"check B  m_absent override: rc={p.returncode} "
          f"{'KILLED (skipped, no fallback)' if good else 'SURVIVED -- FELL BACK'}")
    if not good:
        print("   " + (p.stdout + p.stderr).strip()[:300])
    ok &= good

    print("\nPASS" if ok else "\nFAIL")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
