#!/usr/bin/env python3
"""Provenance manifests for FIRMWARE and CORE artifacts -- the romgen guarantee, extended.

WHY THIS EXISTS. `romgen` made every CART reproducible: it records the emitter commit and
hash, the base ROM and hash, every DR* flag, and builds twice to prove determinism. Firmware
(`copro_rom.hex`) and FPGA cores had no equivalent, so the deployed `copro_rom.hex`
(c87e60a1) became an ORPHAN: it is vendored into four trees, no local script reproduces it,
and all five `dbg_build.py` modes miss it (baseline edff4304 / all 908fc80d / p0 f4cece87 /
p2 bf8109bf / p3 bf57dd4c). The emitter moved after it was built and nothing recorded which
state produced it.

THE DESIGN POINT: remembering to record provenance is not a process, it is a hope. The rule
has to be enforced where the artifact is CREATED and again where it is DEPLOYED, so an
undocumented artifact cannot reach hardware even if everyone forgets.

    stamp(...)   call it from a builder -- writes <artifact>.manifest.json next to the
                 artifact, recording builder+argv, every input file with its hash, the
                 output hash, and (optionally) a second build to prove determinism.
    verify(...)  re-reads the manifest and confirms the artifact and all inputs still hash
                 as recorded. Returns (ok, reasons).
    require()    hard gate for a deploy path: raises unless the artifact verifies.

Deliberately dependency-free and importable from any tree.
"""
import hashlib
import json
import os
import subprocess
import sys

MANIFEST_SUFFIX = ".manifest.json"


def _md5(path):
    h = hashlib.md5()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def _git(repo, *args):
    try:
        return subprocess.run(["git", "-C", repo, *args],
                              capture_output=True, text=True, timeout=30).stdout.strip()
    except Exception:
        return ""


def manifest_path(artifact):
    return artifact + MANIFEST_SUFFIX


def stamp(artifact, builder, inputs, argv=None, env_keys=(), rebuild=None, extra=None):
    """Record how `artifact` was built. Returns the manifest dict.

    artifact : path to the produced file
    builder  : path to the script that produced it
    inputs   : iterable of paths whose content determines the output
    argv     : the exact argv used (defaults to sys.argv)
    env_keys : environment variable names that affect the build; values are recorded
    rebuild  : optional zero-arg callable that rebuilds the artifact in place. If given,
               it is invoked once and the artifact re-hashed to PROVE determinism -- the
               same two-build check romgen does.
    """
    repo = os.path.dirname(os.path.abspath(builder))
    man = {
        "artifact": {"name": os.path.basename(artifact), "md5": _md5(artifact),
                     "size": os.path.getsize(artifact)},
        "builder": {"file": os.path.relpath(os.path.abspath(builder), repo),
                    "md5": _md5(builder),
                    "argv": list(argv if argv is not None else sys.argv)},
        "inputs": [{"path": p, "md5": _md5(p)} for p in inputs if os.path.exists(p)],
        "env": {k: os.environ.get(k) for k in env_keys},
        "git": {"commit": _git(repo, "rev-parse", "HEAD"),
                "branch": _git(repo, "rev-parse", "--abbrev-ref", "HEAD"),
                # exclude manifests: they record the commit, so committing one moves the
                # hash a rebuild would record and the check could never be self-consistent.
                "dirty": bool(_git(repo, "status", "--porcelain", "--",
                                   ":(exclude)*" + MANIFEST_SUFFIX))},
    }
    if extra:
        man["notes"] = extra

    if rebuild is not None:
        first = man["artifact"]["md5"]
        rebuild()
        second = _md5(artifact)
        man["determinism"] = ("verified: two builds byte-identical" if first == second
                              else f"FAILED: {first} != {second}")
    else:
        man["determinism"] = "not checked (no rebuild callable supplied)"

    with open(manifest_path(artifact), "w") as fh:
        json.dump(man, fh, indent=2, sort_keys=True)
    return man


def verify(artifact):
    """(ok, reasons). Confirms the artifact and its recorded inputs still match."""
    mp = manifest_path(artifact)
    if not os.path.exists(mp):
        return False, [f"NO MANIFEST at {mp} -- this artifact has no recorded recipe. "
                       f"That is exactly how copro_rom.hex c87e60a1 became unreproducible."]
    man = json.load(open(mp))
    bad = []
    if not os.path.exists(artifact):
        return False, [f"artifact missing: {artifact}"]
    cur = _md5(artifact)
    if cur != man["artifact"]["md5"]:
        bad.append(f"artifact hash changed: {cur} != recorded {man['artifact']['md5']}")
    for inp in man.get("inputs", []):
        if not os.path.exists(inp["path"]):
            bad.append(f"input vanished: {inp['path']}")
        elif _md5(inp["path"]) != inp["md5"]:
            bad.append(f"input changed since the build: {inp['path']}")
    if man.get("determinism", "").startswith("FAILED"):
        bad.append(man["determinism"])
    if man.get("git", {}).get("dirty"):
        bad.append("built from a DIRTY tree -- not reproducible from a commit")
    return (not bad), bad


def require(artifact):
    """Hard gate. Call this before any deploy (scp/cp to SD, core packaging)."""
    ok, why = verify(artifact)
    if not ok:
        raise SystemExit("REFUSING TO DEPLOY " + artifact + "\n  " + "\n  ".join(why))
    return True


def _cli():
    import argparse
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("cmd", choices=["verify", "require", "show"])
    ap.add_argument("artifact")
    a = ap.parse_args()
    if a.cmd == "show":
        print(json.dumps(json.load(open(manifest_path(a.artifact))), indent=2))
        return 0
    ok, why = verify(a.artifact)
    print(("OK   " if ok else "FAIL ") + a.artifact)
    for w in why:
        print("  - " + w)
    if a.cmd == "require" and not ok:
        return 1
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(_cli())
