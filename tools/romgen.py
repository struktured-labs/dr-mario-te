#!/usr/bin/env python3
"""romgen -- DETERMINISTIC, REPRODUCIBLE cart builds with a recorded recipe.

WHY THIS EXISTS (2026-07-28): `ab_slam_nav_te.nes` (md5 343b7227) is the only cart that
autonavigates on MiSTer silicon, and NOBODY CAN REBUILD IT. No build script, no recorded
flags, and it differs from every reproduction attempt by 2081 bytes starting in BASE-ROM
territory -- so it came from a different base ROM that was never written down. That blocked
a hardware A/B we needed. User's standing rule, same day:

    "make sure we can always regen a rom, deterministic, tag on github on the reg"

Every cart from now on ships with a MANIFEST recording everything needed to regenerate it:
emitter commit + emitter file hash, base ROM path + hash, every DR* env flag, and the
output hash. `rebuild` regenerates from a manifest and FAILS LOUD if the bytes differ.

    tools/romgen.py build   --out drmario_copro.nes --tag play-mister    # + manifest
    tools/romgen.py rebuild roms/manifests/play-mister.json              # verify/regen
    tools/romgen.py verify  roms/manifests/play-mister.json              # determinism only
    tools/romgen.py list                                                 # all known recipes

Flags are taken from the environment (DRSTUDY=1 DRNOFREEZE=1 ... tools/romgen.py build ...)
so this wraps rather than replaces the existing emitter.
"""
from __future__ import annotations
import argparse, hashlib, json, os, shutil, subprocess, sys, tempfile

DRV = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
EMITTER = os.path.join(DRV, "patch_cartridge_copro.py")
MANIFEST_DIR = os.path.join(DRV, "roms", "manifests")
DEFAULT_BASE = os.path.join(DRV, "drmario_v28cs.nes")


def md5(path):
    h = hashlib.md5()
    with open(path, "rb") as f:
        for b in iter(lambda: f.read(1 << 16), b""):
            h.update(b)
    return h.hexdigest()


def git(*args):
    try:
        return subprocess.run(["git", "-C", DRV, *args], capture_output=True,
                              text=True, check=True).stdout.strip()
    except Exception:
        return None


def dr_flags(env=None):
    env = env or os.environ
    return {k: v for k, v in sorted(env.items()) if k.startswith("DR")}


def do_build(out, base, flags, quiet=False):
    """Run the emitter with `flags`, return the path to the produced ROM."""
    if not os.path.exists(base):
        sys.exit(f"base ROM missing: {base}")
    env = dict(os.environ)
    for k in list(env):
        if k.startswith("DR"):
            del env[k]
    env.update(flags)
    # the emitter reads ./drmario_v28cs.nes and writes ./drmario_copro.nes
    tmpbase = None
    if os.path.abspath(base) != os.path.abspath(DEFAULT_BASE):
        tmpbase = DEFAULT_BASE + ".romgen-bak"
        if os.path.exists(DEFAULT_BASE):
            shutil.move(DEFAULT_BASE, tmpbase)
        shutil.copy(base, DEFAULT_BASE)
    try:
        r = subprocess.run([sys.executable, EMITTER], cwd=DRV, env=env,
                           capture_output=True, text=True)
        produced = os.path.join(DRV, "drmario_copro.nes")
        if not os.path.exists(produced):
            sys.exit(f"emitter produced nothing.\n{r.stdout}\n{r.stderr}")
        if out and os.path.abspath(out) != os.path.abspath(produced):
            shutil.move(produced, out); produced = out
        if not quiet:
            print(r.stdout.strip().splitlines()[-1] if r.stdout.strip() else "built")
        return produced
    finally:
        if tmpbase:
            if os.path.exists(tmpbase):
                shutil.move(tmpbase, DEFAULT_BASE)
            elif os.path.exists(DEFAULT_BASE):
                os.remove(DEFAULT_BASE)


def cmd_build(a):
    flags = dr_flags()
    # DRBUILDID_TAG source of truth: derive it from the SAME --tag this command already records
    # in the manifest, so there is exactly one place a build's identity comes from, not two that
    # could drift (the on-cart stamp and the manifest tag naming different things). An explicit
    # DRBUILDID_TAG in the environment wins (caller's deliberate override), matching the
    # env-wins-if-set pattern the rest of this file already uses for DR* flags.
    if "DRBUILDID_TAG" not in flags:
        tag_src = a.tag or os.path.basename(a.out).replace(".nes", "")
        derived = "".join(c for c in tag_src.upper() if c.isalnum())[:4] or "BILD"
        flags["DRBUILDID_TAG"] = derived
    base = a.base or DEFAULT_BASE
    out = os.path.abspath(a.out)
    do_build(out, base, flags)

    # DETERMINISM CHECK: build a second time and require identical bytes.
    second = do_build(os.path.join(tempfile.gettempdir(), "romgen_check.nes"),
                      base, flags, quiet=True)
    if md5(out) != md5(second):
        os.remove(second)
        sys.exit("NON-DETERMINISTIC BUILD -- two runs with identical inputs differ. "
                 "Do not ship this; find the nondeterminism first.")
    os.remove(second)

    man = {
        "tag": a.tag or os.path.basename(out).replace(".nes", ""),
        "output": {"name": os.path.basename(out), "md5": md5(out),
                   "size": os.path.getsize(out)},
        "base_rom": {"path": os.path.relpath(base, DRV), "md5": md5(base)},
        "emitter": {"file": "patch_cartridge_copro.py", "md5": md5(EMITTER)},
        "git": {"commit": git("rev-parse", "HEAD"),
                "branch": git("rev-parse", "--abbrev-ref", "HEAD"),
                # Exclude our OWN output (manifests) from the dirty check. A manifest records
                # /git/commit, so committing one changes the hash a rebuild would record -- the
                # check can never be self-consistently clean, and every cart built after the
                # first in a batch would false-alarm. What "reproducible" means here is that the
                # SOURCE is committed, which is exactly what this now measures.
                "dirty": bool(git("status", "--porcelain", "--",
                                  ":(exclude)roms/manifests"))},
        "flags": flags,
        "determinism": "verified: two builds byte-identical",
    }
    os.makedirs(MANIFEST_DIR, exist_ok=True)
    mp = os.path.join(MANIFEST_DIR, man["tag"] + ".json")
    json.dump(man, open(mp, "w"), indent=2, sort_keys=True)
    print(f"  md5      {man['output']['md5']}")
    print(f"  manifest {os.path.relpath(mp, DRV)}")
    if man["git"]["dirty"]:
        print("  ⚠ WORKING TREE DIRTY -- this ROM is not reproducible from a commit. "
              "Commit before shipping it.")


def cmd_rebuild(a):
    man = json.load(open(a.manifest))
    base = os.path.join(DRV, man["base_rom"]["path"])
    if md5(base) != man["base_rom"]["md5"]:
        sys.exit(f"BASE ROM CHANGED: {base}\n  want {man['base_rom']['md5']}\n"
                 f"  have {md5(base)}")
    cur = md5(EMITTER)
    if cur != man["emitter"]["md5"]:
        print(f"  ⚠ emitter differs from the manifest (want {man['emitter']['md5'][:8]}, "
              f"have {cur[:8]}). Rebuilding anyway; a byte mismatch below tells you the "
              f"emitter change is what moved it.  Recorded commit: {man['git']['commit']}")
    out = a.out or os.path.join(DRV, "tmp", man["output"]["name"])
    os.makedirs(os.path.dirname(out), exist_ok=True)
    do_build(out, base, man["flags"])
    got = md5(out)
    if got == man["output"]["md5"]:
        print(f"  ✅ REPRODUCED byte-exact: {got}")
    else:
        print(f"  ❌ MISMATCH\n     want {man['output']['md5']}\n     got  {got}")
        if cur != man["emitter"]["md5"]:
            # An emitter that has legitimately moved on is the COMMON case, and reporting it
            # as a bare MISMATCH reads as "we lost the ability to rebuild a shipped ROM" --
            # a false alarm that costs an investigation every sweep. Say what it actually
            # means and hand over the one command that settles it.
            print(f"\n     This manifest records emitter {man['emitter']['md5'][:8]} at commit "
                  f"{man['git']['commit']}, and HEAD's emitter is {cur[:8]}.\n"
                  f"     A mismatch is EXPECTED when the emitter has moved on -- it does NOT "
                  f"mean the record is bad.\n     Settle it (in a scratch tree, and restore "
                  f"afterwards):\n"
                  f"       git show {man['git']['commit']}:patch_cartridge_copro.py > "
                  f"patch_cartridge_copro.py\n"
                  f"     If it reproduces there, retire the manifest to "
                  f"roms/manifests/historical/ rather than deleting it.")
        sys.exit(1)


def _manifests(d):
    return sorted(f for f in os.listdir(d) if f.endswith(".json"))


def cmd_list(a):
    if not os.path.isdir(MANIFEST_DIR):
        print("no manifests yet"); return
    for f in _manifests(MANIFEST_DIR):
        m = json.load(open(os.path.join(MANIFEST_DIR, f)))
        fl = " ".join(f"{k}={v}" for k, v in m["flags"].items()) or "(defaults)"
        print(f"{m['tag']:<26} {m['output']['md5']}  {fl}")
    # Superseded recipes: real shipped carts whose emitter has moved on. Listed so they stay
    # visible, under their own heading so nobody mistakes them for live recipes (or for
    # breakage). See roms/manifests/historical/README.md for the reproducing commit of each.
    hist = os.path.join(MANIFEST_DIR, "historical")
    if os.path.isdir(hist) and _manifests(hist):
        print("\nhistorical/ (shipped, but rebuild from their RECORDED commit -- not HEAD):")
        for f in _manifests(hist):
            m = json.load(open(os.path.join(hist, f)))
            fl = " ".join(f"{k}={v}" for k, v in m["flags"].items()) or "(defaults)"
            print(f"  {m['tag']:<24} {m['output']['md5']}  @{(m['git']['commit'] or '?')[:8]}  {fl}")


p = argparse.ArgumentParser(description=__doc__,
                            formatter_class=argparse.RawDescriptionHelpFormatter)
s = p.add_subparsers(dest="cmd", required=True)
b = s.add_parser("build");   b.add_argument("--out", required=True); b.add_argument("--base")
b.add_argument("--tag");     b.set_defaults(fn=cmd_build)
r = s.add_parser("rebuild"); r.add_argument("manifest"); r.add_argument("--out")
r.set_defaults(fn=cmd_rebuild)
l = s.add_parser("list");    l.set_defaults(fn=cmd_list)
a = p.parse_args(); a.fn(a)
