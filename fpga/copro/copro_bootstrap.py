#!/usr/bin/env python3
"""Make THIS tree authoritative for top-level module names (task #127).

THE DEFECT.  `tests/test_vrdy.py` and `tests/test_readiness_ext.py` each open with an
UNCONDITIONAL, HARDCODED

    HERE = "/home/struktured/projects/dr-mario-mods"
    sys.path.insert(0, HERE + "/tests"); sys.path.insert(0, HERE)

Position 0.  So from the moment either is imported, a SIBLING WORKTREE -- on whatever branch
it happens to be parked -- outranks this tree for every top-level name it can supply.  Python
resolves a module by path only on its FIRST import, so whichever entry is first at that
instant wins SILENTLY, with no error and no warning.

build_copro_d3.py already defended ONE name (`test_search_d3`, root-caused 2026-08-05) by
force-registering this tree's copy into sys.modules.  MEASURED 2026-08-19, that defence was
covering 1 of 16: with the old guard in place, FIFTEEN modules still resolved into
dr-mario-mods, including

    nes_d3_golden      <- the GOLDEN the shipped firmware is validated against
    primitives, py65_harness, patch_vs_cpu, test_depth2, nes_d2_golden, ...

which means the py65 firmware gate has been checking this tree's firmware against ANOTHER
BRANCH'S reference implementation, and this tree's own nes_d3_golden was never executed.
(#127 filed that for nes_d3_golden alone; the name-by-name count is worse.)

THE FIX -- and why it is not more of the same.  Registering each name individually does not
scale and cannot cover a name nobody has thought of yet: it also EXECUTES every module you
pre-register, whether the run needed it or not.  Instead `install()` puts a finder at the
FRONT of `sys.meta_path`.  meta_path is consulted BEFORE any sys.path finder, so this tree
wins regardless of what anyone inserts at position 0, afterwards or before, for names that
have not yet been imported -- the whole class, not an enumerated list.

Names ALREADY bound when install() runs cannot be fixed by any finder (a caller holding
`import nes_d3_golden as G` has its own reference), so install() additionally re-registers
any cached entry that resolves outside this tree, exactly as the old single-name guard did.
That is the same limit the old guard documented, and it is inherent to the import cache.

`assert_self_contained()` is the check that this actually worked -- absence of an error is
not evidence, so the gate calls it explicitly and it names every offender.
"""
from __future__ import annotations

import importlib.util
import os
import sys

__all__ = ["install", "assert_self_contained", "SelfContainmentError"]


class SelfContainmentError(RuntimeError):
    """A module resolved outside this worktree. The run is measuring another branch."""


class _RootFirstFinder:
    """Resolve TOP-LEVEL module names from this tree's own directories, first.

    Deliberately narrow: it claims a name only if this tree actually has a file for it, and
    only for top-level imports (`path is None`).  Submodules, packages and site-packages are
    left entirely alone -- this is a shield against one specific hijack, not a global import
    override, and a finder that answered for names it does not own would be a worse bug than
    the one it fixes."""

    def __init__(self, dirs):
        self.dirs = [d for d in dirs if os.path.isdir(d)]

    def find_spec(self, name, path=None, target=None):
        if path is not None or "." in name:
            return None
        for d in self.dirs:
            p = os.path.join(d, name + ".py")
            if os.path.isfile(p):
                return importlib.util.spec_from_file_location(name, p)
        return None


def _tree_dirs(root):
    return [os.path.join(root, "tests"), root]


def install(root, verbose=False):
    """Make `root` authoritative. Returns the list of already-cached names it had to reclaim.

    Set COPRO_BOOTSTRAP_OFF=1 to disable -- that is the KILLED MUTANT for the gate, not a
    supported mode.  With it set, the sibling worktree wins again and the gate must FAIL;
    a fix whose absence changes nothing was never doing anything."""
    if os.environ.get("COPRO_BOOTSTRAP_OFF") == "1":
        return []

    root = os.path.abspath(root)
    dirs = _tree_dirs(root)
    if not any(isinstance(f, _RootFirstFinder) for f in sys.meta_path):
        sys.meta_path.insert(0, _RootFirstFinder(dirs))

    # Reclaim names already bound to a copy outside this tree. A finder cannot help here:
    # sys.modules is consulted before meta_path.
    reclaimed = []
    for name in list(sys.modules):
        if "." in name:
            continue
        mod = sys.modules[name]
        f = getattr(mod, "__file__", None)
        if not f or _inside(f, root):
            continue
        for d in dirs:
            p = os.path.join(d, name + ".py")
            if os.path.isfile(p):
                spec = importlib.util.spec_from_file_location(name, p)
                new = importlib.util.module_from_spec(spec)
                sys.modules[name] = new
                spec.loader.exec_module(new)
                reclaimed.append(name)
                if verbose:
                    print(f"  reclaimed {name}: {f} -> {p}")
                break
    return reclaimed


def _inside(path, root):
    return os.path.abspath(path).startswith(os.path.abspath(root) + os.sep)


def offenders(root):
    """Top-level modules this tree OWNS a copy of, but which resolved somewhere else."""
    root = os.path.abspath(root)
    dirs = _tree_dirs(root)
    out = []
    for name, mod in sorted(sys.modules.items()):
        if "." in name:
            continue
        f = getattr(mod, "__file__", None)
        if not f or _inside(f, root):
            continue
        # Only names this tree could have supplied. A stdlib or site-packages module living
        # outside the tree is correct, not an escape -- flagging those would make the check
        # noise, and a check people learn to ignore is not a check.
        if any(os.path.isfile(os.path.join(d, name + ".py")) for d in dirs):
            out.append((name, os.path.abspath(f)))
    return out


def assert_self_contained(root, where=""):
    bad = offenders(root)
    if bad:
        lines = "\n".join(f"    {n}  ->  {f}" for n, f in bad)
        raise SelfContainmentError(
            f"{len(bad)} module(s) resolved OUTSIDE this worktree{' in ' + where if where else ''}"
            f"; this run is validating against another branch:\n{lines}\n"
            f"  tree = {os.path.abspath(root)}")
    return True
