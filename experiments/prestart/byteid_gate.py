#!/usr/bin/env python3
"""DRPRESTART byte-identity gate: unset must reproduce the pre-feature driver EXACTLY.

The baseline is not a remembered hash and not a sibling worktree -- it is
`git show <ref>:patch_cartridge_copro.py` from this repo, written to a scratch file and
imported from there, so the gate is self-contained and cannot silently drift.

Module resolution is PINNED and `__file__` is asserted before AND after each build. That is
not ceremony: a firmware build in this project once compiled a sibling worktree's emitter and
produced a byte-identical image, and the only symptom was a hash that refused to move (see
dr-mario-copro-build-provenance). A byte-identity gate that imported the wrong file would
report PASS for exactly the wrong reason.

Section B is the positive control -- DRPRESTART=1 must DIFFER on every arm. A gate that
cannot fail is not evidence.

    experiments/prestart/byteid_gate.py [baseline-ref]     # default: main
"""
from __future__ import annotations

import hashlib
import importlib.util
import os
import shutil
import subprocess
import sys
import tempfile

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

MATRIX = [
    ("shipping default", {}),
    ("CvC stomper",      {"DRWRETRY": "1", "DRCOLDINIT": "1", "DRSTALLWD": "1", "DRBUSYESC": "1"}),
    ("human/pocket",     {"DRHUMAN": "1", "DRPOCKET": "1", "DRSTUDY": "1", "DRBUILDID": "1"}),
    ("no rotfix",        {"DRROTFIX": "0"}),
    ("nofreeze",         {"DRNOFREEZE": "1"}),
    ("tuck executor",    {"DRTUCK": "1"}),
    ("holdboard",        {"DRHOLDBOARD": "1"}),
    ("p1 wiggle",        {"DRP1WIGGLE": "1"}),
    ("p1 native",        {"DRP1NATIVE": "1"}),
    ("probe",            {"DRPROBE": "1"}),
    ("navesc+dwell",     {"DRNAVESC": "1", "DRNAVDWELL": "1"}),
    ("distgate",         {"DRDISTGATE": "1"}),
]
_n = [0]


def build(root, flags):
    for k in [k for k in os.environ if k.startswith("DR")]:
        os.environ.pop(k, None)
    os.environ.update(flags)
    _n[0] += 1
    name = "byteid_emitter_%d" % _n[0]
    path = os.path.join(root, "patch_cartridge_copro.py")
    sys.path.insert(0, root)
    try:
        spec = importlib.util.spec_from_file_location(name, path)
        M = importlib.util.module_from_spec(spec)
        sys.modules[name] = M
        spec.loader.exec_module(M)
        assert os.path.realpath(M.__file__) == os.path.realpath(path), \
            "PROVENANCE: imported %s, expected %s" % (M.__file__, path)
        unit1, labels = M.build_main(11, 1)
        assert os.path.realpath(M.__file__) == os.path.realpath(path), \
            "PROVENANCE (post-build): %s" % M.__file__
        return bytes(unit1), labels
    finally:
        sys.path.remove(root)


def stage_baseline(ref, dest):
    """Materialise `ref`'s emitter plus everything it imports at build time."""
    os.makedirs(dest, exist_ok=True)
    blob = subprocess.check_output(["git", "-C", REPO, "show",
                                    "%s:patch_cartridge_copro.py" % ref])
    with open(os.path.join(dest, "patch_cartridge_copro.py"), "wb") as f:
        f.write(blob)
    for dep in ("patch_vs_cpu.py", "expand_prg.py"):
        shutil.copy(os.path.join(REPO, dep), os.path.join(dest, dep))
    os.makedirs(os.path.join(dest, "tests"), exist_ok=True)
    return dest


def main():
    ref = sys.argv[1] if len(sys.argv) > 1 else "main"
    tmp = tempfile.mkdtemp(prefix="drprestart_byteid_")
    try:
        base = stage_baseline(ref, os.path.join(tmp, "baseline"))
        fails = 0
        print("=" * 84)
        print("A. DRPRESTART UNSET -> byte-identical to %s" % ref)
        print("=" * 84)
        print("%-18s %6s  %-34s %-34s" % ("arm", "bytes", "baseline md5", "patched md5"))
        for label, flags in MATRIX:
            b0, _ = build(base, flags)
            b1, _ = build(REPO, flags)
            ok = b0 == b1
            fails += not ok
            print("%-18s %6d  %-34s %-34s %s"
                  % (label, len(b0), hashlib.md5(b0).hexdigest(),
                     hashlib.md5(b1).hexdigest(), "OK" if ok else "*** DIFFER ***"))
            if not ok:
                n = min(len(b0), len(b1))
                first = next((i for i in range(n) if b0[i] != b1[i]), n)
                print("      first diff at offset %d; lengths %d vs %d" % (first, len(b0), len(b1)))

        print()
        print("=" * 84)
        print("B. DRPRESTART=1 -> must DIFFER on every arm (positive control)")
        print("=" * 84)
        for label, flags in MATRIX:
            f = dict(flags, DRPRESTART="1")
            b0, _ = build(base, flags)
            b1, lb = build(REPO, f)
            ok = b0 != b1 and len(b1) > len(b0) and "pre_tick" in lb and "pre_run" in lb
            fails += not ok
            print("%-18s %d -> %d  (+%d bytes)  %s"
                  % (label, len(b0), len(b1), len(b1) - len(b0), "OK" if ok else "*** NO CHANGE ***"))

        print()
        print("RESULT:", "PASS" if fails == 0 else "FAIL (%d)" % fails)
        return 1 if fails else 0
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    sys.exit(main())
