#!/usr/bin/env python3
"""Identify the carts on a mounted SD card. READ-ONLY — never writes to the card.

    python3 tools/cartid/identify_cart.py /media/<user>/<label>      # a mounted card
    python3 tools/cartid/identify_cart.py --self-test                # no card needed

Prints, per .nes found: the matched identity, or `UNIDENTIFIED` with both hashes so the unknown
can be chased. An honest unknown is a legitimate result — **a wrong identity on a cart he might
load is worse than no identity**, which is the entire reason this task exists. Nothing here
guesses a label from a filename.

⚠ MATCHING IS ON TWO HASHES, and the second one matters:
  * `file md5`    — the whole file. Changes if the iNES header changes.
  * `payload md5` — bytes[16:], i.e. PRG+CHR. Survives a header remap (mapper 100 -> 1 for Mesen),
    which alters two nibbles and therefore the file md5 while leaving the cart's actual content
    byte-identical.
A payload match with a different file md5 is reported as REMAPPED, not as a different cart.

⚠ AND: an identity here names the BYTES, not the behaviour. The core the cart is plugged into
decides whether tucks exist at all, so "this is v6e" does not by itself tell you what it will do
on a given Pocket core.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys

DRV = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
REG = os.path.join(DRV, "CART_REGISTRY.json")


def hashes(path):
    b = open(path, "rb").read()
    payload = b[16:] if b[:4] == b"NES\x1a" else b
    return hashlib.md5(b).hexdigest(), hashlib.md5(payload).hexdigest(), len(b)


def describe(e):
    bits = []
    if e.get("known_as"):
        bits.append(e["known_as"])
    if e.get("names"):
        bits.append("tags: " + ", ".join(e["names"][:3]))
    f = e.get("flags") or {}
    if f:
        on = [k.replace("DR", "") for k in
              ("DRHOLDBOARD", "DRPRESTART", "DRTUCK", "DRMMC1RST", "DRRTIVEC", "DRFCGATE",
               "DRDISTGATE", "DRRELATCH") if f.get(k) == "1"]
        bits.append("flags ON: " + (", ".join(on) if on else "(none of the notable ones)"))
        bits.append(f"DRBUILDID={f.get('DRBUILDID', '<unset:DEFAULT-ON>')}")
    if e.get("commit"):
        bits.append(f"{e.get('branch')}@{e['commit'][:8]}")
    return bits


def identify(paths, reg):
    ent = reg["entries"]
    by_payload = {}
    for h, e in ent.items():
        if e.get("payload_md5"):
            by_payload.setdefault(e["payload_md5"], []).append(h)
    n_id = n_un = 0
    for p in sorted(paths):
        fh, ph, sz = hashes(p)
        print(f"\n{os.path.basename(p)}   ({sz} B)")
        e = ent.get(fh)
        if e:
            n_id += 1
            print(f"  ✅ IDENTIFIED  file md5 {fh}")
            for b in describe(e):
                print(f"     {b}")
            continue
        cand = by_payload.get(ph, [])
        if cand:
            n_id += 1
            e = ent[cand[0]]
            print(f"  ✅ IDENTIFIED (REMAPPED HEADER)  payload md5 {ph}")
            print(f"     file md5 {fh} differs from the registry's {cand[0]}, but PRG+CHR are")
            print("     byte-identical — this is a header remap, not a different cart.")
            for b in describe(e):
                print(f"     {b}")
            continue
        n_un += 1
        print(f"  ❌ UNIDENTIFIED")
        print(f"     file md5    {fh}")
        print(f"     payload md5 {ph}")
        print("     Not guessing a label. To chase it: search manifests for either hash, or")
        print("     rebuild candidate flag sets with DRBUILDID=0 pinned and compare payload md5.")
    print(f"\n=== {n_id} identified, {n_un} UNIDENTIFIED, {len(paths)} files ===")
    return n_un


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("path", nargs="?", help="mounted card root (or any directory of .nes files)")
    ap.add_argument("--self-test", action="store_true",
                    help="exercise the no-card and known-cart paths without a card")
    a = ap.parse_args()
    if not os.path.exists(REG):
        print(f"ABORT: no registry at {REG}. Run tools/cartid/build_registry.py first.")
        return 2
    reg = json.load(open(REG))

    if a.self_test:
        print("=== SELF-TEST 1: no card / missing path (the installer's abort path) ===")
        missing = "/media/nonexistent-card-path-selftest"
        if os.path.exists(missing):
            print("  (skipped: that path unexpectedly exists)")
        else:
            rc = main_with(missing, reg)
            print(f"  -> rc={rc}  {'PASS' if rc == 2 else 'FAIL'} (expected a clean abort, not a crash)")
        print("\n=== SELF-TEST 2: known carts identify, and a remap is seen as a remap ===")
        probe = [p for p in (os.path.join(DRV, "roms", "v6e.nes"),
                             os.path.join(DRV, "tmp", "clean", "v6e_mmc1.nes")) if os.path.exists(p)]
        if not probe:
            print("  (skipped: no local probe carts)")
            return 0
        identify(probe, reg)
        return 0

    if not a.path:
        ap.print_help()
        return 2
    return main_with(a.path, reg)


def main_with(path, reg):
    if not os.path.isdir(path):
        print(f"ABORT: {path} is not a mounted directory. Insert the card and re-run.")
        print("       (Nothing was read or written.)")
        return 2
    carts = []
    for root, _d, files in os.walk(path):
        for f in files:
            if f.lower().endswith(".nes"):
                carts.append(os.path.join(root, f))
    if not carts:
        print(f"No .nes files under {path} — nothing to identify.")
        return 0
    return 1 if identify(carts, reg) else 0


if __name__ == "__main__":
    sys.exit(main())
