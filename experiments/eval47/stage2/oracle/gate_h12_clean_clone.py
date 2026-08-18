#!/usr/bin/env python3
"""Clean-clone gate for the certified H12 endpoint champion (task #19).

Three assertions, all of which must hold, run inside a fresh clone:

  A. ROLLED MATCHES.  `run_h12.runtime_manifest("lulu")` recomputed here equals
     the sealed value in SEALED_H12_MANIFEST.json.  `rolled` is a hash of
     name:sha256 pairs only - no paths - so it is reproducible from content
     alone, at any checkout location.

  B. PER-FILE MATCH.  Every one of the 14 manifest entries matches the sealed
     sha256 individually, so a failure names the file rather than just the roll.

  C. SELF-CONTAINED.  Every resolved module path lies inside this clone.  Without
     C the gate is vacuous on the original box: `oracle_arm.py` hard-codes
     /home/struktured/projects/dr_mario_rl on sys.path, so a clone missing its
     vendored copies would silently pass by reading the developer's machine.
     A is a content check and cannot see that; C is what makes A mean
     "reproduces from the clone".

Exit 0 on pass, non-zero on any failure, naming the offending file.
"""
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, "..", "..", "..", ".."))
SEALED = os.path.join(HERE, "SEALED_H12_MANIFEST.json")

sys.path.insert(0, os.path.join(REPO, "tools"))


def main():
    failures = []

    import repro_bootstrap
    if os.path.abspath(os.path.dirname(repro_bootstrap.__file__)) != \
            os.path.join(REPO, "tools"):
        print(f"FAIL: repro_bootstrap resolved outside the clone: "
              f"{repro_bootstrap.__file__}")
        return 2
    try:
        resolved = repro_bootstrap.install()
    except repro_bootstrap.VendorError as exc:
        print(f"FAIL: {exc}")
        return 2

    sealed = json.load(open(SEALED))["runtime_manifest"]

    sys.path.insert(0, HERE)
    from run_h12 import runtime_manifest
    actual = runtime_manifest("lulu")

    # --- A: rolled ---------------------------------------------------------
    rolled_ok = actual["rolled"] == sealed["rolled"]
    print(f"sealed rolled = {sealed['rolled']}")
    print(f"actual rolled = {actual['rolled']}")
    if not rolled_ok:
        failures.append("rolled manifest hash differs from the sealed value")

    # --- B: per-file -------------------------------------------------------
    print("\n%-24s %-8s %s" % ("MODULE", "SHA", "RESOLVED PATH"))
    for name in sorted(sealed["files"]):
        want = sealed["files"][name]["sha256"]
        got = actual["files"].get(name)
        if got is None:
            print(f"{name:<24} {'ABSENT':<8} -")
            failures.append(f"{name}: absent from the recomputed manifest")
            continue
        ok = got["sha256"] == want
        print(f"{name:<24} {'ok' if ok else 'DIFFER':<8} "
              f"{os.path.relpath(got['path'], REPO)}")
        if not ok:
            failures.append(
                f"{name}: sha256 {got['sha256']} != sealed {want} "
                f"(resolved to {got['path']})")

    # --- C: self-contained -------------------------------------------------
    outside = sorted(
        (name, doc["path"]) for name, doc in actual["files"].items()
        if os.path.commonpath([os.path.abspath(doc["path"]), REPO]) != REPO)
    if outside:
        for name, path in outside:
            failures.append(f"{name}: resolved OUTSIDE the clone -> {path}")

    print(f"\nclone root      = {REPO}")
    print(f"modules pinned  = {len(resolved)}")
    print(f"resolved inside = {len(actual['files']) - len(outside)}"
          f"/{len(actual['files'])}")

    if failures:
        print("\nCLEAN-CLONE GATE: FAIL")
        for f in failures:
            print(f"  - {f}")
        return 1
    print("\nCLEAN-CLONE GATE: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
