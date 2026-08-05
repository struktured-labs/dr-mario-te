#!/usr/bin/env python3
"""ONE-SHOT agentic release pipeline for Dr. Mario TE -> romhacking.net.

Encodes every failure mode the v9d release hit by hand, as machine checks:
  hash gate      - BPS applies to the pinned base and yields the expected RC (byte-exact)
  native shots   - captures are 256x240 (RHN rejects anything else) straight from
                   headless emulation of THE SHIPPING ROM (no stale v8 screenshots)
  claim checks   - feature claims verified against the ROM's RAM, not the docs:
                   VS CPU arming (SELECT x2) proven by watching $03A4 (P2 virus BCD)
                   decrease with zero human input; STUDY pause proven non-blanking
  stamp drift    - title version-stamp strip is hashed and compared against the
                   previous release's capture (catches "V8.00 SL on a v9 ROM")
  publish gate   - after push, polls the raw URLs until the CDN actually serves
                   them (lag is real, ~60s) and re-verifies SIZE AND DIMENSIONS
                   from the served bytes, not the local files

Usage:
  te_release_kit.py --bps release/drmario_te_v9d.bps --expect-md5 0f8f5d89... \
      [--publish] [--prev-title <png>] [--out <dir>]

Default is DRY RUN (verify + capture + emit, no git). --publish commits the
capture set + patch to the public repo (dr-mario-te main) and runs the URL gate.
Requires: uv (nes-py run), the project venv for PIL. Base ROM is pinned below.
"""
from __future__ import annotations

import argparse
import hashlib
import io
import os
import subprocess
import sys
import time
import zlib

BASE_ROM = "/home/struktured/projects/dr-mario-canonical-wt/drmario.nes"
BASE_MD5 = "d3ec44424b5ac1a4dc77709829f721c9"
PUBLIC_WT = "/home/struktured/projects/dr-mario-playerstyles-wt"
RAW_BASE = "https://raw.githubusercontent.com/struktured-labs/dr-mario-te/main"
NATIVE = (256, 240)
P2_VIRUS_BCD = 0x03A4          # per V9D_QA_EVIDENCE.md: same variable both players
SEL, START = 0x04, 0x08        # nes-py action bits, measured 2026-08-04

STAMP_BOX = (88, 208, 168, 220)  # title version-stamp strip, native coords


def sh(cmd, **kw):
    r = subprocess.run(cmd, shell=True, capture_output=True, text=True, **kw)
    if r.returncode != 0:
        raise RuntimeError(f"FAILED: {cmd}\n{r.stdout}\n{r.stderr}")
    return r.stdout


def md5(b: bytes) -> str:
    return hashlib.md5(b).hexdigest()


def apply_bps(src: bytes, patch: bytes) -> bytes:
    def rnum(b, i):
        data, shift = 0, 1
        while True:
            x = b[i]; i += 1
            data += (x & 0x7F) * shift
            if x & 0x80:
                return data, i
            shift <<= 7
            data += shift
    assert patch[:4] == b"BPS1", "bad BPS magic"
    assert zlib.crc32(patch[:-4]) == int.from_bytes(patch[-4:], "little"), "patch self-CRC"
    assert zlib.crc32(src) == int.from_bytes(patch[-12:-8], "little"), "wrong base ROM"
    i = 4
    ssize, i = rnum(patch, i); tsize, i = rnum(patch, i); msize, i = rnum(patch, i)
    i += msize
    assert ssize == len(src)
    out = bytearray(tsize)
    o = sr = tr = 0
    while i < len(patch) - 12:
        n, i = rnum(patch, i)
        cmd, ln = n & 3, (n >> 2) + 1
        if cmd == 0:
            out[o:o + ln] = src[o:o + ln]; o += ln
        elif cmd == 1:
            out[o:o + ln] = patch[i:i + ln]; i += ln; o += ln
        elif cmd == 2:
            d, i = rnum(patch, i); sr += (-1 if d & 1 else 1) * (d >> 1)
            out[o:o + ln] = src[sr:sr + ln]; sr += ln; o += ln
        else:
            d, i = rnum(patch, i); tr += (-1 if d & 1 else 1) * (d >> 1)
            for _ in range(ln):
                out[o] = out[tr]; o += 1; tr += 1
    assert o == tsize
    assert zlib.crc32(bytes(out)) == int.from_bytes(patch[-8:-4], "little"), "target CRC"
    return bytes(out)


CAPTURE_DRIVER = r'''
import json, sys
from nes_py import NESEnv
from PIL import Image
rom, out = sys.argv[1], sys.argv[2]
SEL, START = 0x04, 0x08
env = NESEnv(rom); env.reset()
def run(n, a=0):
    for _ in range(n): env.step(a)
def press(a, hold=8, settle=30):
    run(hold, a); run(settle)
def save(name):
    Image.fromarray(env.screen).save(f"{out}/{name}.png")
report = {}
run(400); save("01_title")
press(SEL); press(SEL)                    # cursor to 2P, arm CPU
press(START); run(60); save("02_level_select")
press(START); run(60)                     # into the game
v0 = int(env.ram[0x03A4])
run(900); save("03_midgame_2p")
v1 = int(env.ram[0x03A4])
report["vscpu_armed"] = bool(v1 < v0)     # P2 cleared with zero input = AI live
report["p2_virus_bcd"] = [v0, v1]
press(START, settle=45); save("04_study_2p")   # STUDY pause
import numpy as np
s = np.asarray(Image.open(f"{out}/04_study_2p.png"))
report["study_not_blanked"] = bool((s.reshape(-1,3).max(1) > 60).mean() > 0.15)
press(START)                              # resume clean
run(120); save("05_resumed")
report["screen_shape"] = list(env.screen.shape[:2])
print("CAPTURE_REPORT " + json.dumps(report))
'''


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--bps", required=True)
    ap.add_argument("--expect-md5", required=True)
    ap.add_argument("--out", default=None)
    ap.add_argument("--prev-title", default=None,
                    help="previous release's native title capture, for stamp-drift check")
    ap.add_argument("--publish", action="store_true")
    a = ap.parse_args()
    out = a.out or os.path.join(os.path.dirname(os.path.abspath(a.bps)), "kit_out")
    os.makedirs(out, exist_ok=True)
    failures = []

    # ---- stage 1: hash gate -------------------------------------------------
    src = open(BASE_ROM, "rb").read()
    assert md5(src) == BASE_MD5, "pinned base ROM changed on disk!"
    patch = open(a.bps, "rb").read()
    rom = apply_bps(src, patch)
    got = md5(rom)
    print(f"[1/5] hash gate: patched md5 {got}", "OK" if got == a.expect_md5 else "FAIL")
    if got != a.expect_md5:
        sys.exit(f"RC mismatch: expected {a.expect_md5}")
    rom_path = os.path.join(out, "rc_verified.nes")
    open(rom_path, "wb").write(rom)

    # ---- stage 2: headless capture + claim checks ---------------------------
    drv = os.path.join(out, "_capture_driver.py")
    open(drv, "w").write(CAPTURE_DRIVER)
    stdout = sh(f'cd ~/projects/dr_mario_rl && uv run --with nes-py --with "numpy<2" '
                f'python {drv} {rom_path} {out} 2>/dev/null')
    import json
    report = json.loads([l for l in stdout.splitlines()
                         if l.startswith("CAPTURE_REPORT ")][-1].split(" ", 1)[1])
    print(f"[2/5] captures: screen {report['screen_shape']}, "
          f"vscpu_armed={report['vscpu_armed']} (P2 virus {report['p2_virus_bcd']}), "
          f"study_not_blanked={report['study_not_blanked']}")
    if tuple(report["screen_shape"]) != (NATIVE[1], NATIVE[0]):
        failures.append("capture not native 256x240")
    if not report["vscpu_armed"]:
        failures.append("VS CPU arming check FAILED (SELECT x2 did not yield an active P2)")
    if not report["study_not_blanked"]:
        failures.append("STUDY pause appears blanked")

    # ---- stage 3: stamp drift ----------------------------------------------
    from PIL import Image
    title = Image.open(os.path.join(out, "01_title.png"))
    stamp = title.crop(STAMP_BOX).tobytes()
    if a.prev_title:
        prev = Image.open(a.prev_title).crop(STAMP_BOX).tobytes()
        drifted = stamp != prev
        print(f"[3/5] stamp drift vs previous release: "
              f"{'CHANGED (good - version was bumped)' if drifted else 'IDENTICAL'}")
        if not drifted:
            failures.append("title version stamp identical to previous release "
                            "(stamp not bumped - see issue #12)")
    else:
        print("[3/5] stamp drift: skipped (no --prev-title)")

    # ---- stage 4: publish + URL gate ---------------------------------------
    if a.publish:
        ver = os.path.basename(a.bps).replace(".bps", "")
        dest = f"{PUBLIC_WT}/release/screenshots/{ver}"
        os.makedirs(dest, exist_ok=True)
        names = ["01_title", "02_level_select", "03_midgame_2p", "04_study_2p"]
        for n in names:
            sh(f"cp {out}/{n}.png {dest}/{n}.png")
        sh(f'cd {PUBLIC_WT} && git add release/screenshots/{ver} && '
           f'git commit -m "release: {ver} native capture set (pipeline)" && '
           f'git push origin HEAD:main')
        print(f"[4/5] pushed release/screenshots/{ver}; waiting out the raw CDN...")
        urls = [f"{RAW_BASE}/release/screenshots/{ver}/{n}.png" for n in names]
        deadline = time.time() + 120
        for u in urls:
            while True:
                r = subprocess.run(f"curl -s -L -o {out}/_url.png -w '%{{http_code}}' {u}",
                                   shell=True, capture_output=True, text=True)
                if r.stdout.strip() == "200":
                    im = Image.open(f"{out}/_url.png")
                    if im.size != NATIVE:
                        failures.append(f"served {u} is {im.size}, not {NATIVE}")
                    break
                if time.time() > deadline:
                    failures.append(f"URL never went live: {u}")
                    break
                time.sleep(10)
        print("[4/5] URL gate done")
        url_block = "\n".join(urls)
    else:
        print("[4/5] publish: DRY RUN (pass --publish to push + URL-gate)")
        url_block = "(dry run - no URLs)"

    # ---- stage 5: emit ------------------------------------------------------
    verdict = "RELEASE-READY" if not failures else "NOT READY:\n  - " + "\n  - ".join(failures)
    open(os.path.join(out, "VERIFIED_FACTS.md"), "w").write(f"""# {os.path.basename(a.bps)} — machine-verified release facts

- base: Dr. Mario (USA) Rev 0, md5 {BASE_MD5}
- patched md5: {got} (byte-exact vs expectation)
- captures: native {NATIVE[0]}x{NATIVE[1]}, from the shipping ROM itself
- VS CPU arming (SELECT x2): {"VERIFIED — P2 virus BCD " + str(report['p2_virus_bcd']) if report['vscpu_armed'] else "FAILED"}
- STUDY pause non-blanking: {report['study_not_blanked']}
- screenshot URLs:\n{url_block}

## Verdict: {verdict}

Prose claims in RHN_ENTRY/SUBMISSION docs must not exceed these facts.
""")
    print(f"[5/5] {verdict}")
    print(f"kit_out: {out} (VERIFIED_FACTS.md + native captures + rc_verified.nes)")
    sys.exit(1 if failures else 0)


if __name__ == "__main__":
    main()
