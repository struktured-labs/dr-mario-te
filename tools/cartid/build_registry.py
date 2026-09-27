#!/usr/bin/env python3
"""Build the cart-identity registry: md5 -> (name, flags, branch, commit, base ROM).

WHY: the owner is about to re-insert an SD card carrying several carts, at least five of which
we cannot currently identify, and then play a match off it. "Which of these is which" has to be a
one-command lookup when the card mounts, not an investigation while he waits.

SOURCES, in descending order of trust:
  1. committed romgen MANIFESTS across every worktree -- each records output md5, the full flag
     snapshot, branch, commit and base ROM. That IS the identity claim.
  2. actual .nes files on disk (roms/, staging/, release/) -- hashed to recover the PAYLOAD md5,
     which manifests do not store.

⚠ THREE TRAPS, all of which have bitten this project, encoded here rather than left to be
rediscovered:
  * DRBUILDID is a DEFAULT-ON stamp that moves ~1868 bytes. An unpinned rebuild will not match a
    manifest built with it pinned off. Every rebuild this tool performs pins DRBUILDID=0, and the
    registry records each entry's DRBUILDID so a mismatch is explainable rather than mysterious.
  * A HEADER REMAP for Mesen (mapper 100 -> 1) changes the FILE md5 while leaving PRG+CHR
    byte-identical. So every entry carries BOTH file md5 and PAYLOAD md5 (bytes[16:]), and the
    identifier matches on either. The soak lane's boot image differs from the ship cart in exactly
    the two iNES mapper nibbles.
  * A cart's BEHAVIOUR is not determined by the cart alone -- the core it is plugged into decides
    whether tucks exist at all. An identity here names the BYTES, not what they will do.

    python3 tools/cartid/build_registry.py            # write CART_REGISTRY.json
    python3 tools/cartid/build_registry.py --verify   # also romgen-rebuild each manifest
"""
from __future__ import annotations

import argparse
import glob
import hashlib
import json
import os
import subprocess
import sys

DRV = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
OUT = os.path.join(DRV, "CART_REGISTRY.json")
PY = "/home/struktured/projects/dr_mario_rl/tmp/venv/bin/python"

MANIFEST_GLOBS = [
    "/home/struktured/projects/dr-mario-*-wt/roms/manifests/*.json",
    "/home/struktured/projects/dr-mario-mods/roms/manifests/*.json",
]
CART_GLOBS = [
    "/home/struktured/projects/dr-mario-*-wt/roms/*.nes",
    "/home/struktured/projects/pocket-nes-mapper100/staging/*/*.nes",
    "/home/struktured/projects/dr-mario-*-wt/release/*/*.nes",
    "/mnt/data/drmario/pocket-copro/mesen_copro_qa/**/*.nes",
]

# Carts whose identity is established in the project record but which may have no manifest here.
KNOWN = {
    "94f2fbd0d998f04a6ed6220b566bb556": "v6c (distlatch) — the FIELD-BUGGY ship cart; DRHOLDBOARD=1 soft-bricks after a match",
    "49e10ce9d40b389835f71215e38eb8ec": "v6b (boardhold fixfl) — also DRHOLDBOARD=1, same soft-brick family",
    "087ff959ac510c613bbbd2eb1ac5ecf3": "c-v8ship — SUPERSEDED: carries the DRRTIVEC A-clobber shield",
    "c0082cb34259007854120d3d4ab9fa27": "v6e — CURRENT v8 REMATCH SHIP CART (A-clobber fixed)",
    "c16271c6f093b518404d5d17e31616fb": "v8-fcgate — unhardened fallback (no MMC1RST/RTIVEC)",
    "c9364b2670a7a0e0292e56264d9f231b": "hb1-nolatch — v6e + DRHOLDBOARD=1; board-hold WORKS on this line",
    "7d307c3051ebc0f8a10e259e3c270acb": "drmario_v28cs.nes — BASE ROM, not a playable copro cart",
}


def md5(b: bytes) -> str:
    return hashlib.md5(b).hexdigest()


def hash_file(p):
    b = open(p, "rb").read()
    payload = b[16:] if b[:4] == b"NES\x1a" else b
    return md5(b), md5(payload), len(b)


def collect_manifests():
    ent = {}
    seen = set()
    for g in MANIFEST_GLOBS:
        for p in glob.glob(g):
            rp = os.path.realpath(p)
            if rp in seen:
                continue
            seen.add(rp)
            try:
                m = json.load(open(p))
            except Exception:
                continue
            o = m.get("output", {})
            h = o.get("md5")
            if not h:
                continue
            f = m.get("flag_snapshot") or m.get("flags") or {}
            e = ent.setdefault(h, {"file_md5": h, "names": [], "manifests": [], "flags": f,
                                   "branch": m.get("git", {}).get("branch"),
                                   "commit": m.get("git", {}).get("commit"),
                                   "base_md5": m.get("base_rom", {}).get("md5"),
                                   "size": o.get("size"),
                                   "drbuildid": f.get("DRBUILDID", "<unset:DEFAULT-ON>")})
            nm = m.get("tag") or o.get("name") or os.path.basename(p)
            if nm not in e["names"]:
                e["names"].append(nm)
            e["manifests"].append(os.path.relpath(p, "/home/struktured/projects"))
    return ent


def collect_files(ent):
    """Hash real .nes files to recover PAYLOAD md5 (manifests do not store it)."""
    payload_index = {}
    seen = set()
    for g in CART_GLOBS:
        for p in glob.glob(g, recursive=True):
            rp = os.path.realpath(p)
            if rp in seen or not os.path.isfile(rp):
                continue
            seen.add(rp)
            try:
                fh, ph, sz = hash_file(rp)
            except Exception:
                continue
            e = ent.get(fh)
            if e is None:
                e = ent.setdefault(fh, {"file_md5": fh, "names": [], "manifests": [], "flags": {},
                                        "branch": None, "commit": None, "base_md5": None,
                                        "size": sz, "drbuildid": None})
            e["payload_md5"] = ph
            e.setdefault("paths", [])
            rel = os.path.relpath(rp, "/home/struktured/projects")
            if rel not in e["paths"]:
                e["paths"].append(rel)
            payload_index.setdefault(ph, set()).add(fh)
    return payload_index


def verify(ent):
    """romgen-rebuild each manifest with DRBUILDID pinned, and record whether it reproduced."""
    ok = bad = skipped = 0
    for h, e in ent.items():
        mans = [m for m in e["manifests"] if m.startswith("dr-mario-v8-wt/")]
        if not mans:
            skipped += 1
            continue
        p = os.path.join("/home/struktured/projects", mans[0])
        env = dict(os.environ, DRBUILDID="0")
        r = subprocess.run([PY, os.path.join(DRV, "tools", "romgen.py"), "rebuild", p],
                           cwd=DRV, env=env, capture_output=True, text=True)
        good = "REPRODUCED byte-exact" in (r.stdout + r.stderr)
        e["rebuilt"] = bool(good)
        ok, bad = ok + bool(good), bad + (not good)
    return ok, bad, skipped


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--verify", action="store_true", help="romgen-rebuild each local manifest")
    a = ap.parse_args()
    ent = collect_manifests()
    payload_index = collect_files(ent)
    for h, note in KNOWN.items():
        ent.setdefault(h, {"file_md5": h, "names": [], "manifests": [], "flags": {},
                           "branch": None, "commit": None, "base_md5": None,
                           "size": None, "drbuildid": None})["known_as"] = note
    v = None
    if a.verify:
        v = verify(ent)
        print(f"verify: {v[0]} reproduced, {v[1]} FAILED, {v[2]} skipped (manifest not local)")
    reg = {
        "generated_by": "tools/cartid/build_registry.py",
        "entries": ent,
        "payload_to_file": {p: sorted(s) for p, s in payload_index.items() if len(s) > 1},
        "verify": {"reproduced": v[0], "failed": v[1], "skipped": v[2]} if v else None,
    }
    json.dump(reg, open(OUT, "w"), indent=1, sort_keys=True)
    npay = sum(1 for e in ent.values() if e.get("payload_md5"))
    print(f"wrote {OUT}: {len(ent)} identities, {npay} with a payload hash, "
          f"{len(reg['payload_to_file'])} payloads seen under >1 file md5 (header remaps)")


if __name__ == "__main__":
    sys.exit(main())
