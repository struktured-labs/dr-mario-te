#!/usr/bin/env python3
"""frame_watchdog_mutants.py — KILLED-MUTANT battery for frame_watchdog.py.

The old wedge discriminator shipped broken because its only control (9h19m idle at the
menu, no core loaded) was STRUCTURALLY INCAPABLE of failing in the direction that mattered
(busy-and-healthy). This battery exists so that failure cannot repeat: every mutant below
is a feed the watchdog MUST classify a specific way, and each one attacks a specific way
this watchdog could be wrong. A mutant that was not RUN is not a mutant.

Each mutant is executed through the real CLI (subprocess), not by calling internals, so
what is tested is the shipped entry point.

Run:  python3 experiments/freeze5_blackscreen/frame_watchdog_mutants.py
Exit: 0 = every mutant killed as expected; 1 = at least one survived.
"""
from __future__ import annotations

import json
import os
import struct
import subprocess
import sys
import zlib

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
WD = os.path.join(HERE, "frame_watchdog.py")
OUT = os.path.join(ROOT, "tmp", "framewd", "mutants")

sys.path.insert(0, HERE)
from frame_watchdog import decode_png, pixhash  # noqa: E402

REAL_A = os.path.join(HERE, "soak_20260809_214501.png")   # VIRUS 47/26, 21:45:01 EDT
REAL_B = os.path.join(HERE, "soak2_214552.png")           # VIRUS 45/32, 21:45:52 EDT
# Live burst off the same soak, 22:06:19 / 22:06:23 EDT (~4 s apart), VIRUS 46/43.
# Committed alongside the two 21:45 frames so this battery reproduces from a clean
# checkout — tmp/ is gitignored and must never be a test dependency.
LIVE_C = os.path.join(HERE, "soak3_burst_a.png")
LIVE_D = os.path.join(HERE, "soak4_burst_b.png")


# ----------------------------------------------------------------------------------
# Synthetic frame construction (stdlib PNG writer).
# ----------------------------------------------------------------------------------
def write_png(path: str, rgb: bytes, w: int, h: int, filt: int = 0, level: int = 9) -> None:
    """Write packed RGB as an 8-bit truecolour PNG. `filt` selects the per-row filter byte;
    varying it re-encodes identical pixels into different FILE bytes (mutant E)."""
    raw = bytearray()
    stride = w * 3
    prev = bytes(stride)
    for y in range(h):
        line = rgb[y * stride:(y + 1) * stride]
        raw.append(filt)
        if filt == 0:
            raw += line
        elif filt == 2:  # Up
            raw += bytes((line[i] - prev[i]) & 0xFF for i in range(stride))
        else:
            raise ValueError("only filter 0/2 implemented")
        prev = line

    def chunk(t: bytes, d: bytes) -> bytes:
        c = t + d
        return struct.pack(">I", len(d)) + c + struct.pack(">I", zlib.crc32(c))

    hdr = struct.pack(">IIBBBBB", w, h, 8, 2, 0, 0, 0)
    with open(path, "wb") as f:
        f.write(b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", hdr)
                + chunk(b"IDAT", zlib.compress(bytes(raw), level))
                + chunk(b"IEND", b""))


def build_synthetics() -> dict:
    os.makedirs(OUT, exist_ok=True)
    w, h, a = decode_png(open(REAL_A, "rb").read())
    paths = {}

    # freeze-5 end state: display dead, framebuffer all black.
    black = bytes(w * h * 3)
    paths["black"] = os.path.join(OUT, "syn_black.png")
    write_png(paths["black"], black, w, h)

    # Same PIXELS as REAL_A, different FILE bytes (filter 2 + compression level 1).
    paths["reencoded"] = os.path.join(OUT, "syn_reencoded_A.png")
    write_png(paths["reencoded"], a, w, h, filt=2, level=1)
    # And a byte-identical-pixel copy written our way with filter 0, so the pair
    # {reencoded, plain} differ in file bytes but not in a single pixel.
    paths["plain"] = os.path.join(OUT, "syn_plain_A.png")
    write_png(paths["plain"], a, w, h, filt=0, level=9)

    # "Blinking cursor" on an otherwise frozen screen: one 8x8 tile (64 px) toggled white.
    def blink(npx: int, name: str) -> str:
        mut = bytearray(a)
        done = 0
        y = 200
        x = 100
        while done < npx:
            i = ((y * w) + x) * 3
            mut[i:i + 3] = b"\xff\xff\xff"
            done += 1
            x += 1
            if x >= 108:
                x = 100
                y += 1
        p = os.path.join(OUT, name)
        write_png(p, bytes(mut), w, h)
        return p

    paths["blink64"] = blink(64, "syn_blink64.png")     # below the floor -> must stay WEDGED
    paths["blink256"] = blink(256, "syn_blink256.png")  # above the floor -> documented limit
    return paths


# ----------------------------------------------------------------------------------
# Mutant runner.
# ----------------------------------------------------------------------------------
def run_mutant(name: str, frames: list[str], extra: list[str] | None = None) -> dict:
    d = os.path.join(OUT, name)
    os.makedirs(d, exist_ok=True)
    log = os.path.join(d, "log.jsonl")
    if os.path.exists(log):
        os.remove(log)
    cmd = [sys.executable, WD, "--offline-frames", *frames,
           "--frame-dir", os.path.join(d, "frames"), "--log", log]
    if extra:
        cmd += extra
    p = subprocess.run(cmd, capture_output=True, text=True, cwd=ROOT)
    recs = [json.loads(l) for l in open(log)] if os.path.exists(log) else []
    return {"name": name, "rc": p.returncode, "stderr": p.stderr.rstrip("\n"), "recs": recs}


def verdicts(r: dict) -> list[str]:
    return [x["verdict"] for x in r["recs"]]


def reasons(r: dict) -> list[str]:
    return [x["reason"] for x in r["recs"]]


def main() -> int:
    syn = build_synthetics()
    results = []
    failures = []

    def check(res: dict, want_final: str, want_reason: str | None,
              forbid: set[str] | None = None) -> None:
        vs, rs = verdicts(res), reasons(res)
        ok = bool(vs) and vs[-1] == want_final
        if want_reason and (not rs or rs[-1] != want_reason):
            ok = False
        if forbid and set(vs) & forbid:
            ok = False
        res["expected"] = f"final={want_final}" + (f" reason={want_reason}" if want_reason else "")
        res["killed"] = ok
        results.append(res)
        if not ok:
            failures.append(res["name"])

    # (a) MANDATORY — genuinely static screen: the same frame four times.
    check(run_mutant("A_static_same_frame", [REAL_A] * 4),
          "WEDGED", "frames_static")

    # (b) MANDATORY — the two real screenshots from tonight's live game (VIRUS 47/26 ->
    #     45/32). MUST be ALIVE and must never emit WEDGED.
    check(run_mutant("B_live_real_pair", [REAL_A, REAL_B]),
          "ALIVE", "frames_differ", forbid={"WEDGED"})

    # (b2) the same, extended with the two live-burst captures ~3 s apart.
    check(run_mutant("B2_live_four_real", [REAL_A, REAL_B, LIVE_C, LIVE_D]),
          "ALIVE", "frames_differ", forbid={"WEDGED"})

    # (b3) alternating real frames: a live screen that oscillates must stay ALIVE.
    check(run_mutant("B3_live_alternating", [REAL_A, REAL_B] * 3),
          "ALIVE", "frames_differ", forbid={"WEDGED"})

    # (c) MANDATORY — synthesised freeze-5 end state: black framebuffer.
    check(run_mutant("C_black_frozen", [syn["black"]] * 4),
          "WEDGED", "frames_static_black")

    # (c2) the truer freeze-5 signature per the standing METHOD RULE: the screenshot
    #      service stops answering at all.
    check(run_mutant("C2_capture_dead", ["MISSING"] * 3),
          "WEDGED", "capture_dead")

    # (d) COMPARISON-METHOD mutant: identical PIXELS, different PNG FILE bytes. A raw
    #     byte/file-hash compare would call this ALIVE. It must be WEDGED.
    check(run_mutant("D_reencoded_same_pixels",
                     [syn["plain"], syn["reencoded"]] * 2),
          "WEDGED", "frames_static")

    # (e) ANTI-BLINKING-CURSOR mutant: frozen screen with a 64 px (one 8x8 tile) blink.
    #     "Some pixels moved" must NOT certify life.
    check(run_mutant("E_blink64_below_floor", [REAL_A, syn["blink64"]] * 2),
          "WEDGED", "frames_static")

    # (f) HONEST LIMIT mutant: a 256 px blink is ABOVE the floor and is expected to read
    #     ALIVE. This is not a pass/fail of the design, it is the documented boundary of
    #     the anti-blink defence — recorded so nobody discovers it in the field.
    lim = run_mutant("F_blink256_above_floor", [REAL_A, syn["blink256"]] * 2)
    lim["expected"] = "final=ALIVE (documented limit, not a defect)"
    lim["killed"] = verdicts(lim)[-1] == "ALIVE"
    results.append(lim)
    if not lim["killed"]:
        failures.append(lim["name"])

    # (g) SINGLE static interval must be SUSPECT, never WEDGED (K is doing its job).
    check(run_mutant("G_one_static_interval_only", [REAL_A, REAL_A, REAL_B]),
          "ALIVE", "frames_differ", forbid={"WEDGED"})

    # (h) A single dropped capture must be SUSPECT, not WEDGED, and must NOT launder a
    #     frozen picture: static, drop, static -> the static streak survives the gap.
    check(run_mutant("H_dropped_capture_no_launder",
                     [REAL_A, REAL_A, "MISSING", REAL_A, REAL_A]),
          "WEDGED", "frames_static")

    # (i) human profile: the frames channel is disabled, so a static screen must NOT be
    #     called wedged (a paused human game is legitimate).
    check(run_mutant("I_human_profile_static_ok", [REAL_A] * 6, ["--profile", "human"]),
          "SUSPECT", "frames_static", forbid={"WEDGED"})

    # ------------------------------------------------------------------
    # Report
    # ------------------------------------------------------------------
    print("=" * 78)
    print("KILLED-MUTANT BATTERY — frame_watchdog.py")
    print("=" * 78)
    for r in results:
        status = "KILLED" if r["killed"] else "*** SURVIVED ***"
        print(f"\n--- {r['name']}  [{status}]   expected: {r['expected']}")
        print(f"    exit={r['rc']}  verdicts={verdicts(r)}")
        print(f"    reasons ={reasons(r)}")
        for line in r["stderr"].splitlines():
            print(f"    | {line}")

    # Comparison-method evidence: the re-encode pair really is byte-different.
    print("\n" + "-" * 78)
    print("COMPARISON-METHOD EVIDENCE (mutant D)")
    import hashlib
    for k in ("plain", "reencoded"):
        raw = open(syn[k], "rb").read()
        w, h, rgb = decode_png(raw)
        print(f"    {os.path.basename(syn[k]):24s} file_md5={hashlib.md5(raw).hexdigest()} "
              f"bytes={len(raw):6d}  pixhash={pixhash(rgb)}")
    print("    => different FILE bytes, identical PIXEL hash: a byte-compare would have")
    print("       reported this frozen screen as ALIVE.")

    print("\n" + "=" * 78)
    if failures:
        print(f"RESULT: {len(failures)} MUTANT(S) SURVIVED: {failures}")
        return 1
    print(f"RESULT: ALL {len(results)} MUTANTS KILLED")
    return 0


if __name__ == "__main__":
    sys.exit(main())
