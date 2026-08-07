#!/usr/bin/env python3
"""code_manifest.py -- hash the code that produced a result, so a result can be
tied back to it after the fact.

THE HAZARD, stated once. A long job runs against a tree that other agents are
editing. Nothing warns you. This already happened here: `adversary_harness.py`
gained a field 12 minutes after a remote node was synced, the two nodes ran
different code, and the ONLY symptom was one hash in one field of one rare seed
-- `result`, `pills`, `viruses_left` and `n_moves` all matched. The offending
edit was correct, additive and backward-compatible. **The hazard is structural,
not anyone's mistake, which is exactly why it needs a mechanical detector rather
than discipline.**

It is also NOT remote-only. Two local agents that imported a module at different
times, or a 20-hour job and the tree it started from, have the same exposure.

TWO WAYS TO BUILD A MANIFEST, and the second is stronger:

  from_paths(paths)      -- hash a declared file list. Simple, but it hashes
                            what you MEANT to load.
  from_imports(names)    -- hash the files actually resolved in sys.modules.
                            This catches the case a path list cannot: a module
                            imported from a DIFFERENT WORKTREE than you assumed
                            (`dr-mario-main-wt` vs `dr-mario-qa-wt` both provide
                            `reach_root`, `root_search`, `terms47`). Call it
                            AFTER the imports you care about.

USE IT LIKE THIS in any long-running job:

    import code_manifest
    code_manifest.stamp(os.path.join(out_dir, "manifest.json"))

then compare `rolled` across nodes, or against the value stored beside an older
result. A mismatch INVALIDATES everything produced since the last match.

CLI:
    code_manifest.py                 # default decide-path files, JSON to stdout
    code_manifest.py --rolled        # just the rolled hash
    code_manifest.py FILE [FILE...]  # hash an explicit list
"""
from __future__ import annotations

import os
import sys
import json
import time
import hashlib
import argparse

_P = "/home/struktured/projects"

# The files that decide a game. Anything that changes a move belongs here.
DECIDE_PATH_FILES = [
    f"{_P}/dr-mario-qa-wt/experiments/adversary/adversary_harness.py",
    f"{_P}/dr-mario-qa-wt/experiments/eval47/reach_root.py",
    f"{_P}/dr-mario-qa-wt/experiments/eval47/terms47.py",
    f"{_P}/dr-mario-qa-wt/experiments/tuck_v3/root_search.py",
    f"{_P}/dr_mario_rl/tmp/combo_term/fast_rtl_x.py",
    f"{_P}/dr_mario_rl/tmp/combo_term/fast_sim_x.py",
    f"{_P}/dr_mario_rl/tmp/endgame/fb.py",
    f"{_P}/dr-mario-qa-wt/experiments/nes_pills.py",
    f"{_P}/dr_mario_rl/.claude/worktrees/faithful-sim/src/drmario/faithful_env.py",
    f"{_P}/dr_mario_rl/.claude/worktrees/faithful-sim/src/drmario/faithful_game.py",
]

# Module names whose RESOLVED file matters. Used by from_imports().
DECIDE_PATH_MODULES = [
    "adversary_harness", "reach_root", "terms47", "root_search",
    "fast_rtl_x", "fast_sim_x", "fb", "nes_pills",
    "drmario.faithful_env", "drmario.faithful_game",
    "pressure_rig", "bursty_model", "fit_ensemble_source",
]


def _sha(path):
    try:
        with open(path, "rb") as f:
            return hashlib.sha256(f.read()).hexdigest()
    except OSError:
        return "MISSING"


def _roll(per):
    return hashlib.sha256(
        "".join(f"{k}:{v}" for k, v in sorted(per.items())).encode()).hexdigest()


def from_paths(paths=None):
    """Manifest over a declared file list. Keys are basenames."""
    paths = DECIDE_PATH_FILES if paths is None else list(paths)
    per = {os.path.basename(p): _sha(p) for p in paths}
    return {"kind": "paths", "files": per, "rolled": _roll(per)}


def from_imports(names=None):
    """Manifest over modules ACTUALLY resolved in sys.modules.

    Stronger than from_paths: it records the file that really got imported, so a
    module served from an unexpected worktree shows up as a different hash AND a
    different path. Modules not imported are simply absent -- call this after the
    imports you care about, not at the top of the file.
    """
    names = DECIDE_PATH_MODULES if names is None else list(names)
    per, where = {}, {}
    for n in names:
        m = sys.modules.get(n)
        f = getattr(m, "__file__", None) if m is not None else None
        if not f:
            continue
        per[n] = _sha(f)
        where[n] = f
    return {"kind": "imports", "files": per, "paths": where, "rolled": _roll(per)}


def combined():
    """Both views plus enough environment to explain a numeric difference."""
    env = {"python": sys.version.split()[0], "argv0": sys.argv[0],
           "host": os.uname().nodename, "time": time.time()}
    try:
        import numpy, numba, llvmlite
        env.update(numpy=numpy.__version__, numba=numba.__version__,
                   llvmlite=llvmlite.__version__)
    except ImportError:
        pass
    return {"paths": from_paths(), "imports": from_imports(), "env": env}


def stamp(out_path, extra=None):
    """Write a manifest beside a job's output. Call at job START.

    Returns the rolled path-hash so a caller can also log it inline.
    """
    doc = combined()
    if extra:
        doc["extra"] = extra
    os.makedirs(os.path.dirname(os.path.abspath(out_path)), exist_ok=True)
    with open(out_path, "w") as f:
        json.dump(doc, f, indent=2)
    return doc["paths"]["rolled"]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("paths", nargs="*")
    ap.add_argument("--rolled", action="store_true", help="print only the rolled hash")
    a = ap.parse_args()
    doc = from_paths(a.paths) if a.paths else from_paths()
    if a.rolled:
        print(doc["rolled"])
    else:
        print(json.dumps(doc, indent=2))
        missing = [k for k, v in doc["files"].items() if v == "MISSING"]
        if missing:
            print(f"\n⚠ MISSING: {missing}", file=sys.stderr)
            sys.exit(1)


if __name__ == "__main__":
    main()
