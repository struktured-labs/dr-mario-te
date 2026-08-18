#!/usr/bin/env python3
"""Pin every module the oracle decision path imports from outside this repo.

`experiments/eval47/stage2/oracle/oracle_arm.py` puts six absolute paths under
`/home/struktured/projects/dr_mario_rl` on `sys.path` at import time.  Two of
them (`tmp/endgame`, `tmp/pillrng`) live in a gitignored tree and one
(`.claude/worktrees/faithful-sim/src`) in an unpushed agent worktree, so a clean
clone resolves none of them - and on the original box they resolve to files no
commit can reproduce.  Task #19.

Import this module and call `install()` BEFORE importing `oracle_arm`,
`run_h12` or `run_oracle`.  It loads each vendored file by explicit path,
verifies its sha256 against `experiments/vendor/VENDOR.json`, and registers it
in `sys.modules`.  A name already in `sys.modules` is never re-resolved, so
`oracle_arm`'s absolute path entries become inert whether or not they exist -
the same technique `fpga/copro/build_copro_d3.py` uses against sibling-worktree
module capture.

Deliberately additive: it does not edit any file whose sha256 is in the sealed
runtime manifest, because that would change `rolled` and decertify the champion.
"""
import hashlib
import importlib.util
import json
import os
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
VENDOR_JSON = os.path.join(REPO, "experiments", "vendor", "VENDOR.json")

# Dependency order: each module may import ones listed before it.
PLAIN = ("fast_sim_x", "fast_rtl_x", "fb", "nes_pills",
         "terms47", "root_search", "bursty_model", "p0_ab", "pressure_rig")
PACKAGE = "drmario"
PACKAGE_SUBMODULES = ("drmario.faithful_game", "drmario.faithful_env")

# Directories the pinned modules expect on sys.path for their own imports.
PATH_DIRS = ("experiments",
             "experiments/depth4/snap",
             "experiments/vendor",
             "experiments/tuck_v3",
             "experiments/eval47",
             "experiments/eval47/jointdig",
             "experiments/eval47/vocab2",
             "experiments/eval47/stage2",
             "experiments/eval47/stage2/rollout",
             "experiments/eval47/stage2/oracle")


class VendorError(RuntimeError):
    """A pinned file is missing or its content does not match VENDOR.json."""


def _sha256(path):
    with open(path, "rb") as fh:
        return hashlib.sha256(fh.read()).hexdigest()


def _check(rel, expect, why):
    path = os.path.join(REPO, rel)
    if not os.path.exists(path):
        raise VendorError(
            f"MISSING REQUIRED FILE: {rel} ({why}). Expected sha256 {expect}. "
            f"This clone cannot reproduce the sealed H12 runtime manifest.")
    got = _sha256(path)
    if got != expect:
        raise VendorError(
            f"CONTENT MISMATCH: {rel} ({why}). Expected sha256 {expect}, got {got}.")
    return path


def _load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    try:
        spec.loader.exec_module(module)
    except BaseException:
        sys.modules.pop(name, None)
        raise
    return module


def _load_package(name, init_path):
    pkg_dir = os.path.dirname(init_path)
    spec = importlib.util.spec_from_file_location(
        name, init_path, submodule_search_locations=[pkg_dir])
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    try:
        spec.loader.exec_module(module)
    except BaseException:
        sys.modules.pop(name, None)
        raise
    return module


def _all_modules(doc):
    merged = dict(doc["modules"])
    merged.update(doc["pinned_repo_modules"])
    return merged


def verify_only():
    """Check every pin without importing anything. Raises VendorError."""
    doc = json.load(open(VENDOR_JSON))
    checked = {}
    for name, rec in _all_modules(doc).items():
        checked[name] = _check(rec["path"], rec["sha256"], "pinned module")
    for name, rec in doc["data_inputs"].items():
        checked[name] = _check(rec["path"], rec["sha256"], "pinned data input")
    for rel in doc["package_support"]["files"]:
        if not os.path.exists(os.path.join(REPO, rel)):
            raise VendorError(f"MISSING REQUIRED FILE: {rel} (package support).")
    return checked


def install():
    """Verify the pins, then register the vendored modules in sys.modules."""
    doc = json.load(open(VENDOR_JSON))
    verify_only()

    vendor_dir = os.path.join(REPO, "experiments", "vendor")
    for rel in reversed(PATH_DIRS):
        extra = os.path.join(REPO, rel)
        if extra not in sys.path:
            sys.path.insert(0, extra)

    _load_package(PACKAGE, os.path.join(vendor_dir, PACKAGE, "__init__.py"))
    for name in PACKAGE_SUBMODULES:
        leaf = name.split(".", 1)[1]
        module = _load(name, os.path.join(vendor_dir, PACKAGE, leaf + ".py"))
        setattr(sys.modules[PACKAGE], leaf, module)
    modules = _all_modules(doc)
    for name in PLAIN:
        _load(name, os.path.join(REPO, modules[name]["path"]))

    return {name: sys.modules[name].__file__
            for name in PLAIN + (PACKAGE,) + PACKAGE_SUBMODULES}


if __name__ == "__main__":
    for name, path in sorted(install().items()):
        print(f"{name:<24} -> {path}")
