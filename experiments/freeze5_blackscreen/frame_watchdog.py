#!/usr/bin/env python3
"""frame_watchdog.py — PC-side frame-progress watchdog for MiSTer Dr. Mario soaks.

WHY THIS EXISTS
---------------
The previous discriminator (`wedge_probe.sh`, device-side) classified a wedge from
/proc forensics: wchan=0 + empty /proc/<pid>/stack + State=R + nonvoluntary >> voluntary
context switches, plus busy_frac=100% for consec>=6 polls. On 2026-08-09 21:45 EDT that
entire signature was measured firing continuously on a game that was demonstrably playing
(paired screenshots 51 s apart: VIRUS 47/26 -> 45/32). Its validating control had been
9h19m *idle at the menu with no core loaded* — at the menu the framework genuinely blocks,
so the signature is absent BY CONSTRUCTION. An idle control cannot fail in the direction
that matters (busy-and-healthy). See WEDGE_PROBE.md, section "FRAME-PROGRESS WATCHDOG".

This watchdog replaces the *discriminator*, not the logging. It observes the only thing
anyone actually cares about: does the picture change? It is immune to the busy-vs-blocked
confound because it never looks at the framework process at all.

TWO CHANNELS, KEPT SEPARATE ON PURPOSE
--------------------------------------
  capture channel : did the screenshot service answer at all?
      The standing METHOD RULE in WEDGE_PROBE.md (established on the arm-1 and vanilla
      verdicts, and re-affirmed after a screenshot MISREAD nearly inverted a verdict) is:
      "a returned screenshot means the display path is ALIVE. A wedge is proven by the
      screenshot service TIMING OUT, never by frame content."  So K consecutive capture
      failures => reason=capture_dead. That is the freeze-5 signature proper.
  frames channel  : did the returned picture change?
      K consecutive identical frames while the service still answers => frames_static
      (or frames_static_black when the frame is also ~all black). A frozen picture is a
      soak failure too, but it is NOT the same diagnosis — it can be a driver/nav stall
      with a perfectly healthy display path. The log names the channel so the two are
      never conflated the way busy_frac conflated busy with wedged.

HOW "LEGITIMATELY STATIC" IS SEPARATED FROM "WEDGED"  (the load-bearing argument)
---------------------------------------------------------------------------------
By DURATION, not by content. Scope: an UNATTENDED CvC/autonav soak (--profile cvc-soak,
the default). On such a cart every legitimate static screen is BOUNDED:

  * final-board hold (DRHOLDBOARD): on a non-HUMAN_P1 (CvC) cart a $43-clock-edge 16-bit
    counter FORCE-releases after DRHOLDBOARD_F frames, default 600 = 9.98 s NTSC.
    Source: FINAL_BOARD_HOLD_REPORT.md "Restore/release", scenario C ("the nav cart
    cannot wedge"). This is the longest legitimate static screen on the rig.
  * vanilla STAGE CLEAR / GAME OVER blocking waits: released by autonav's START.
  * title / level-select / between-match: autonav walks through them in seconds.

N is therefore chosen GREATER than the longest bounded static screen, so two consecutive
captures can never BOTH land inside one (20 s > 9.98 s), and K then demands three further
independent intervals of proven zero change. Anything that holds one identical frame for
K*N = 60 s on an autonav soak is a failure by definition — the remaining question is only
WHICH failure, which the channel + screen_class fields answer.

  ==> Consequence, stated plainly: on a HUMAN cart this argument does NOT hold. Pause and
      hold-until-START are unbounded there. Run --profile human for a human session: it
      keeps the capture channel (real freeze-5 detection) and DISABLES the frames channel.

screen_class (black / in_match / other) is DIAGNOSTIC ONLY. It refines the reason string
and is logged for later analysis; it can never suppress a WEDGED verdict, so a
misclassification cannot hide a wedge. See classify_screen().

SAFETY — non-negotiable, enforced by construction
-------------------------------------------------
  * Runs entirely PC-side. It writes NOTHING to the device filesystem.
  * It sends NO input, loads NO core, and CANNOT reboot: there is no reboot/reload/ssh/
    input code path anywhere in this file. Audit with:
        command grep -n 'reboot\\|reload\\|ssh\\|input\\|--host.*launch' frame_watchdog.py
  * Its only device interaction is `misterclaw-send ... screenshot`, the read-only capture
    path explicitly EXONERATED as a wedge trigger by the 2026-08-05 controlled experiment
    (the wedge recurred with all PC-side IPC stopped).
  * Alarming is LOG + stderr + exit code 2. Nothing is killed or restarted, ever.

USAGE
-----
  live:    ./frame_watchdog.py --host MiSTer --log tmp/framewd/watch.jsonl
  bounded: ./frame_watchdog.py --iterations 6            (live, 6 polls, then exits)
  mutant:  ./frame_watchdog.py --offline-frames a.png a.png a.png a.png   (no device at all)
           `--offline-frames MISSING` injects a capture failure at that position.

EXIT CODES: 0 = ran, no wedge seen.  2 = a WEDGED verdict was emitted.  1 = usage/IO error.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import statistics
import subprocess
import sys
import time
import zlib
from dataclasses import dataclass, field
from datetime import datetime, timezone

SCHEMA = "framewd/1"

# ----------------------------------------------------------------------------------
# Defaults. Every one is justified from measurement in WEDGE_PROBE.md
# ("FRAME-PROGRESS WATCHDOG") — do not retune without redoing the timing argument there.
# ----------------------------------------------------------------------------------
DEFAULT_INTERVAL_S = 20.0      # > 9.98 s max legitimate static screen (DRHOLDBOARD cap)
DEFAULT_K = 3                  # 3 static intervals = 4 captures spanning 60 s
DEFAULT_K_CAPFAIL = 3          # 3 consecutive dead captures before calling it
DEFAULT_TOLERANCE = 8          # per-channel abs delta a pixel must exceed to count changed
DEFAULT_MIN_CHANGED_FRAC = 1.0e-3   # 114.7 px of 114688 must change to certify ALIVE
DEFAULT_CAPTURE_TIMEOUT_S = 12.0
BLACK_LEVEL = 16               # all channels <= this => pixel counts as black
BLACK_FRAC_MIN = 0.98          # >= this fraction black => screen_class "black"

# Playfield ROI (both bottle interiors + counters), taken from the MEASURED change
# bounding box of the two real 2026-08-09 soak frames (x 32..222, y 88..397) plus a
# 4 px margin — not guessed. Secondary signal only; does NOT drive the verdict.
DEFAULT_ROI = (28, 84, 227, 402)     # x0, y0, x1, y1  (half-open)

# in_match fingerprint tuning (diagnostic only)
CHROME_BLOCK_W, CHROME_BLOCK_H = 32, 16
CHROME_MIN_SD = 40.0           # a chrome block must have real structure, not flat colour
CHROME_BLOCK_MAD_MAX = 6.0     # per-block mean-abs-diff at or below this => block matches
CHROME_MATCH_MIN_FRAC = 0.90   # >= this fraction of chrome blocks matching => in_match


# ==================================================================================
# PNG decode — stdlib only.
# ==================================================================================
class DecodeError(Exception):
    pass


def decode_png(data: bytes) -> tuple[int, int, bytes]:
    """Decode a PNG to (width, height, packed_rgb). Raise DecodeError on anything odd.

    Deliberately strict: an unexpected PNG variant must FAIL LOUDLY (and be logged as a
    capture failure) rather than be silently mis-measured into a wrong verdict.
    """
    if data[:8] != b"\x89PNG\r\n\x1a\n":
        raise DecodeError("not a PNG")
    pos = 8
    ihdr = None
    palette = b""
    idat = bytearray()
    while pos + 8 <= len(data):
        ln = int.from_bytes(data[pos:pos + 4], "big")
        typ = data[pos + 4:pos + 8]
        body = data[pos + 8:pos + 8 + ln]
        pos += 12 + ln
        if typ == b"IHDR":
            ihdr = body
        elif typ == b"PLTE":
            palette = body
        elif typ == b"IDAT":
            idat += body
        elif typ == b"IEND":
            break
    if ihdr is None:
        raise DecodeError("no IHDR")
    w = int.from_bytes(ihdr[0:4], "big")
    h = int.from_bytes(ihdr[4:8], "big")
    depth, ctype, interlace = ihdr[8], ihdr[9], ihdr[12]
    if depth != 8:
        raise DecodeError(f"unsupported bit depth {depth}")
    if interlace != 0:
        raise DecodeError("interlaced PNG unsupported")
    channels = {0: 1, 2: 3, 3: 1, 4: 2, 6: 4}.get(ctype)
    if channels is None:
        raise DecodeError(f"unsupported colour type {ctype}")
    if ctype == 3 and not palette:
        raise DecodeError("palette image with no PLTE")

    raw = zlib.decompress(bytes(idat))
    stride = w * channels
    if len(raw) != (stride + 1) * h:
        raise DecodeError(f"raw length {len(raw)} != expected {(stride + 1) * h}")

    out = bytearray(stride * h)
    prev = bytearray(stride)
    bpp = channels
    ip = 0
    for y in range(h):
        ft = raw[ip]
        ip += 1
        line = bytearray(raw[ip:ip + stride])
        ip += stride
        if ft == 0:
            pass
        elif ft == 1:
            for i in range(bpp, stride):
                line[i] = (line[i] + line[i - bpp]) & 0xFF
        elif ft == 2:
            for i in range(stride):
                line[i] = (line[i] + prev[i]) & 0xFF
        elif ft == 3:
            for i in range(stride):
                a = line[i - bpp] if i >= bpp else 0
                line[i] = (line[i] + ((a + prev[i]) >> 1)) & 0xFF
        elif ft == 4:
            for i in range(stride):
                a = line[i - bpp] if i >= bpp else 0
                c = prev[i - bpp] if i >= bpp else 0
                b = prev[i]
                p = a + b - c
                pa, pb, pc = abs(p - a), abs(p - b), abs(p - c)
                pr = a if (pa <= pb and pa <= pc) else (b if pb <= pc else c)
                line[i] = (line[i] + pr) & 0xFF
        else:
            raise DecodeError(f"bad filter type {ft} on row {y}")
        out[y * stride:(y + 1) * stride] = line
        prev = line

    # Normalise every supported variant to packed RGB so all downstream maths is uniform.
    if ctype == 2:
        rgb = bytes(out)
    elif ctype == 6:
        rgb = bytes(b for i in range(0, len(out), 4) for b in out[i:i + 3])
    elif ctype == 0:
        rgb = bytes(v for v in out for _ in range(3))
    elif ctype == 4:
        rgb = bytes(out[i] for i in range(0, len(out), 2) for _ in range(3))
    else:  # ctype == 3
        rgb = bytes(b for idx in out for b in palette[idx * 3:idx * 3 + 3])
    if len(rgb) != w * h * 3:
        raise DecodeError("normalised buffer size mismatch")
    return w, h, rgb


# ==================================================================================
# Frame comparison.
# ==================================================================================
def crop(rgb: bytes, w: int, h: int, roi: tuple[int, int, int, int]) -> bytes:
    x0, y0, x1, y1 = roi
    x0, y0 = max(0, x0), max(0, y0)
    x1, y1 = min(w, x1), min(h, y1)
    if x1 <= x0 or y1 <= y0:
        return b""
    out = bytearray()
    for y in range(y0, y1):
        base = (y * w + x0) * 3
        out += rgb[base:base + (x1 - x0) * 3]
    return bytes(out)


def black_frac(rgb: bytes) -> float:
    if not rgb:
        return 0.0
    r, g, b = rgb[0::3], rgb[1::3], rgb[2::3]
    dark = sum(1 for m in map(max, r, g, b) if m <= BLACK_LEVEL)
    return dark / len(r)


def compare(a: bytes, b: bytes, tol: int) -> dict:
    """Compare two packed-RGB buffers of DECODED PIXELS.

    Returns changed_frac (fraction of PIXELS whose max per-channel |delta| exceeds tol),
    mad (mean absolute per-BYTE delta) and max_abs.

    WHY DECODED PIXELS AND NOT PNG BYTES — both failure directions:
      * falsely ALIVE: two encodings of ONE frozen framebuffer can differ in filter
        choice, zlib block boundaries or ancillary chunks. A byte- or file-hash compare
        would read a dead screen as moving. That is the exact failure class this watchdog
        exists to remove, so byte-compare is disqualified. (Mutant E proves this.)
      * falsely WEDGED: an analog/dither/scaler path that jitters pixels would make a live
        screen compare equal-ish. Measured on this rig: tol=0 and tol=8 return the SAME
        changed_frac on both real pairs, i.e. the capture is pixel-exact and carries zero
        noise. tol is kept as a guard for a future noisy capture path, not because this one
        needs it.
    """
    if len(a) != len(b):
        return {"changed_frac": 1.0, "mad": 255.0, "max_abs": 255, "size_mismatch": True}
    if a == b:  # C-level memcmp fast path; the overwhelmingly common wedged case
        return {"changed_frac": 0.0, "mad": 0.0, "max_abs": 0, "size_mismatch": False}
    d = bytes(map(lambda x, y: x - y if x > y else y - x, a, b))
    npx = len(d) // 3
    changed = sum(1 for m in map(max, d[0::3], d[1::3], d[2::3]) if m > tol)
    return {
        "changed_frac": changed / npx if npx else 0.0,
        "mad": sum(d) / len(d),
        "max_abs": max(d),
        "size_mismatch": False,
    }


def pixhash(rgb: bytes) -> str:
    """Hash of DECODED PIXELS (not of the PNG file). Two different encodings of the same
    framebuffer hash identically here — which is the point."""
    return hashlib.blake2b(rgb, digest_size=8).hexdigest()


# ==================================================================================
# Screen classification (DIAGNOSTIC ONLY — never suppresses a verdict).
# ==================================================================================
@dataclass
class ChromeRef:
    """'Is this a Dr. Mario VS play screen?' fingerprint.

    Built from TWO committed real in-match frames: the chrome blocks are the 32x16 blocks
    that are pixel-IDENTICAL across both (so they are match furniture, not game content)
    AND have per-block stdev >= CHROME_MIN_SD (so they carry structure, not flat
    background). A candidate frame is in_match when >= CHROME_MATCH_MIN_FRAC of those
    blocks match reference A with block mean-abs-diff <= CHROME_BLOCK_MAD_MAX.

    VALIDATION HONESTY: the positive side is validated on 4 real in-match frames from two
    different match states; the negative side only on synthetic non-match frames (black,
    inverted, shuffled). It has NOT been validated against a real title/level-select
    capture, because taking one would require disturbing a live soak. That is exactly why
    this label is diagnostic and never gates an alarm.
    """
    w: int
    h: int
    ref: bytes
    blocks: list[tuple[int, int]] = field(default_factory=list)

    @classmethod
    def build(cls, path_a: str, path_b: str) -> "ChromeRef":
        wa, ha, a = decode_png(open(path_a, "rb").read())
        wb, hb, b = decode_png(open(path_b, "rb").read())
        if (wa, ha) != (wb, hb):
            raise DecodeError("chrome reference frames differ in size")
        blocks = []
        for by in range(0, ha - CHROME_BLOCK_H + 1, CHROME_BLOCK_H):
            for bx in range(0, wa - CHROME_BLOCK_W + 1, CHROME_BLOCK_W):
                ba = block_bytes(a, wa, bx, by)
                bb = block_bytes(b, wa, bx, by)
                if ba == bb and statistics.pstdev(ba) >= CHROME_MIN_SD:
                    blocks.append((bx, by))
        return cls(wa, ha, a, blocks)

    def match_frac(self, rgb: bytes, w: int, h: int) -> float:
        if (w, h) != (self.w, self.h) or not self.blocks:
            return 0.0
        ok = 0
        for bx, by in self.blocks:
            ba = block_bytes(self.ref, self.w, bx, by)
            bb = block_bytes(rgb, w, bx, by)
            mad = sum(map(lambda p, q: p - q if p > q else q - p, ba, bb)) / len(ba)
            if mad <= CHROME_BLOCK_MAD_MAX:
                ok += 1
        return ok / len(self.blocks)


def block_bytes(rgb: bytes, w: int, bx: int, by: int) -> bytes:
    out = bytearray()
    for y in range(by, by + CHROME_BLOCK_H):
        base = (y * w + bx) * 3
        out += rgb[base:base + CHROME_BLOCK_W * 3]
    return bytes(out)


def classify_screen(rgb: bytes, w: int, h: int, bfrac: float,
                    chrome: ChromeRef | None) -> tuple[str, float | None]:
    if bfrac >= BLACK_FRAC_MIN:
        return "black", None
    if chrome is None:
        return "unknown", None
    mf = chrome.match_frac(rgb, w, h)
    return ("in_match" if mf >= CHROME_MATCH_MIN_FRAC else "other"), mf


# ==================================================================================
# Capture.
# ==================================================================================
_DISCOVERED = re.compile(r"Auto-discovered\s+MisterClaw\s+at\s+([0-9.]+)")


@dataclass
class Capturer:
    """Wraps `misterclaw-send screenshot`. Read-only; this is the whole device interface.

    Caches the auto-discovered IP after the first call: resolving by name costs an extra
    LAN scan per call, and scanning the LAN every 20 s is not "gentle". On any failure the
    cache is dropped and the ORIGINAL host string is retried once, so a moved IP self-heals
    instead of becoming a permanent false WEDGED.
    """
    host: str
    timeout_s: float = DEFAULT_CAPTURE_TIMEOUT_S
    binary: str = "misterclaw-send"
    _ip: str | None = field(default=None, repr=False)

    def _run(self, host: str, out_path: str) -> tuple[bool, str, float]:
        t0 = time.monotonic()
        try:
            p = subprocess.run(
                [self.binary, "-H", host, "--timeout", str(int(self.timeout_s)),
                 "screenshot", "--output", out_path],
                capture_output=True, text=True, timeout=self.timeout_s + 8.0,
            )
        except subprocess.TimeoutExpired:
            return False, "subprocess_timeout", time.monotonic() - t0
        except FileNotFoundError:
            return False, "misterclaw-send_not_found", time.monotonic() - t0
        dt = time.monotonic() - t0
        blob = (p.stdout or "") + (p.stderr or "")
        m = _DISCOVERED.search(blob)
        if m:
            self._ip = m.group(1)
        if p.returncode != 0:
            return False, f"rc={p.returncode} {blob.strip()[:160]}", dt
        if not os.path.exists(out_path) or os.path.getsize(out_path) == 0:
            return False, "empty_or_missing_file", dt
        return True, "", dt

    def capture(self, out_path: str) -> tuple[bool, str, float]:
        hosts = [self._ip, self.host] if self._ip else [self.host]
        err, total = "", 0.0
        for hh in hosts:
            ok, err, dt = self._run(hh, out_path)
            total += dt
            if ok:
                return True, "", total
            self._ip = None  # drop the cache; next attempt re-discovers
        return False, err, total


@dataclass
class OfflineCapturer:
    """Mutant harness: replays a fixed list of PNG paths. The literal token MISSING (or any
    path that does not exist) injects a capture failure at that position. Exhausting the
    list ends the run. No device is contacted."""
    frames: list[str]
    _i: int = 0

    def capture(self, out_path: str) -> tuple[bool, str, float]:
        if self._i >= len(self.frames):
            raise StopIteration
        src = self.frames[self._i]
        self._i += 1
        if src == "MISSING" or not os.path.exists(src):
            return False, f"offline_injected_failure:{src}", 0.0
        shutil.copyfile(src, out_path)
        return True, "", 0.0


# ==================================================================================
# Classifier.
# ==================================================================================
ALIVE, SUSPECT, WEDGED, INIT = "ALIVE", "SUSPECT", "WEDGED", "INIT"


@dataclass
class Classifier:
    """Three-state frame-progress classifier.

        ALIVE   : the frame changed since the previous SUCCESSFUL capture, by at least
                  min_changed_frac of the pixels.
        SUSPECT : one interval with no qualifying change, or one failed capture.
        WEDGED  : k consecutive static intervals (frames_static / frames_static_black),
                  or k_capfail consecutive failed captures (capture_dead).

    min_changed_frac is the ANTI-BLINKING-CURSOR floor: "some pixels moved" is not accepted
    as proof of life. Calibration (measured, see WEDGE_PROBE.md): live play 3 s apart
    changes 1204 px = 1.05e-2; the floor is 1.0e-3 = 114.7 px = ~1.8 NES tiles, i.e. 10.5x
    below the smallest real motion observed and above any 1-tile blink.

    Counter discipline (both directions):
      * a FAILED capture does NOT reset consec_static, and the next successful frame is
        compared against the last SUCCESSFUL frame (gap_s records the true span) — so an
        intermittently-failing capture path cannot launder a frozen picture into ALIVE;
      * a successful, changed frame DOES reset consec_capfail — a recovered service is
        recovered.
      * k_static = 0 disables the frames channel entirely (--profile human).
    """
    k: int = DEFAULT_K
    k_capfail: int = DEFAULT_K_CAPFAIL
    min_changed_frac: float = DEFAULT_MIN_CHANGED_FRAC
    consec_static: int = 0
    consec_capfail: int = 0

    def step(self, capture_ok: bool, changed_frac: float | None,
             screen_class: str = "unknown") -> tuple[str, str]:
        if not capture_ok:
            self.consec_capfail += 1
            if self.consec_capfail >= self.k_capfail:
                return WEDGED, "capture_dead"
            return SUSPECT, "capture_fail"
        self.consec_capfail = 0
        if changed_frac is None:
            return INIT, "first_frame"
        if changed_frac >= self.min_changed_frac:
            self.consec_static = 0
            return ALIVE, "frames_differ"
        self.consec_static += 1
        reason = "frames_static_black" if screen_class == "black" else "frames_static"
        if self.k > 0 and self.consec_static >= self.k:
            return WEDGED, reason
        return SUSPECT, reason


PROFILES = {
    # unattended CvC/autonav soak: every legitimate static screen is bounded (<=9.98 s)
    "cvc-soak": {"k": DEFAULT_K},
    # human session: pause / hold-until-START are UNBOUNDED, so the frames channel cannot
    # discriminate. Keep the capture channel (real freeze-5) and disable frames.
    "human": {"k": 0},
}


# ==================================================================================
# Runner.
# ==================================================================================
def now_iso() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def run(args) -> int:
    os.makedirs(args.frame_dir, exist_ok=True)
    os.makedirs(os.path.join(args.frame_dir, "alerts"), exist_ok=True)
    os.makedirs(os.path.dirname(os.path.abspath(args.log)) or ".", exist_ok=True)

    chrome = None
    if args.chrome_ref_a and args.chrome_ref_b:
        try:
            chrome = ChromeRef.build(args.chrome_ref_a, args.chrome_ref_b)
        except Exception as e:
            print(f"WARN chrome reference unavailable ({e}); screen_class=unknown",
                  file=sys.stderr)

    cap = (OfflineCapturer(args.offline_frames) if args.offline_frames is not None
           else Capturer(args.host, args.capture_timeout))
    clf = Classifier(k=args.k, k_capfail=args.k_capfail,
                     min_changed_frac=args.min_changed_frac)

    logf = open(args.log, "a", buffering=1)
    prev = None            # (rgb, w, h, path, wallclock)
    seq = 0
    t_start = time.monotonic()
    last_verdict = None
    roi_static_streak = 0
    ring: list[str] = []
    exit_code = 0

    while True:
        if args.iterations and seq >= args.iterations:
            break
        if args.max_runtime and (time.monotonic() - t_start) > args.max_runtime:
            break
        t_poll = time.monotonic()
        seq += 1
        path = os.path.join(args.frame_dir, f"f{seq:06d}.png")
        try:
            ok, err, cap_s = cap.capture(path)
        except StopIteration:
            seq -= 1
            break

        rec = {
            "schema": SCHEMA, "ts": now_iso(), "seq": seq, "capture_ok": ok,
            "capture_ms": round(cap_s * 1000, 1), "interval_s": args.interval,
            "k": args.k, "k_capfail": args.k_capfail, "profile": args.profile,
            "min_changed_frac": args.min_changed_frac, "tolerance": args.tolerance,
        }
        cur = None
        if ok:
            try:
                blob = open(path, "rb").read()
                w, h, rgb = decode_png(blob)
                cur = (rgb, w, h, path, time.time())
                bfrac = black_frac(rgb)
                sclass, mfrac = classify_screen(rgb, w, h, bfrac, chrome)
                rec.update({"png_bytes": len(blob), "w": w, "h": h,
                            "pixhash": pixhash(rgb), "black_frac": round(bfrac, 5),
                            "screen_class": sclass})
                if mfrac is not None:
                    rec["chrome_match_frac"] = round(mfrac, 4)
            except Exception as e:  # decode failure is a capture failure, loudly
                ok = False
                err = f"decode_error:{e}"
                rec["png_bytes"] = os.path.getsize(path) if os.path.exists(path) else 0
        if not ok:
            rec["error"] = err
            rec["screen_class"] = "none"

        changed_frac = None
        if ok and prev is not None:
            st = compare(prev[0], cur[0], args.tolerance)
            changed_frac = st["changed_frac"]
            rec.update({"changed_frac": round(st["changed_frac"], 6),
                        "mad": round(st["mad"], 4), "max_abs": st["max_abs"],
                        "gap_s": round(cur[4] - prev[4], 2)})
            if st.get("size_mismatch"):
                rec["size_mismatch"] = True
            if args.roi:
                a = crop(prev[0], prev[1], prev[2], args.roi)
                b = crop(cur[0], cur[1], cur[2], args.roi)
                if a and b and len(a) == len(b):
                    rst = compare(a, b, args.tolerance)
                    rec["roi_changed_frac"] = round(rst["changed_frac"], 6)
                    rec["roi_mad"] = round(rst["mad"], 4)
                    # A frozen PLAYFIELD under a still-animating UI is a driver/nav stall,
                    # not a display wedge. Surfaced as an annotation; deliberately does NOT
                    # drive the verdict (whole-frame does), so it can never false-alarm.
                    roi_static_streak = (roi_static_streak + 1
                                         if rst["changed_frac"] < args.min_changed_frac
                                         else 0)
                    rec["roi_static_streak"] = roi_static_streak
                    if roi_static_streak >= args.k and changed_frac >= args.min_changed_frac:
                        rec["note"] = "playfield_static_while_screen_moves"

        verdict, reason = clf.step(ok, changed_frac, rec.get("screen_class", "unknown"))
        rec.update({"verdict": verdict, "reason": reason,
                    "consec_static": clf.consec_static,
                    "consec_capfail": clf.consec_capfail})
        logf.write(json.dumps(rec, sort_keys=True) + "\n")

        flag = "  <== ALERT" if verdict == WEDGED else ""
        print(f"[{rec['ts']}] seq={seq} {verdict:7s} {reason:19s} "
              f"class={rec.get('screen_class', '-'):8s} "
              f"changed={rec.get('changed_frac', 'n/a')} "
              f"static={clf.consec_static} capfail={clf.consec_capfail}{flag}",
              file=sys.stderr, flush=True)

        if verdict == WEDGED and last_verdict != WEDGED:
            adir = os.path.join(args.frame_dir, "alerts", f"wedge_{seq:06d}_{reason}")
            os.makedirs(adir, exist_ok=True)
            for src in [p for p in (prev[3] if prev else None, path) if p and os.path.exists(p)]:
                shutil.copyfile(src, os.path.join(adir, os.path.basename(src)))
            print(f"ALERT wedge_confirmed reason={reason} evidence={adir} "
                  f"(NOTHING has been rebooted, reloaded, or killed)",
                  file=sys.stderr, flush=True)
            exit_code = 2
        last_verdict = verdict

        if ok:
            prev = cur
        ring.append(path)
        while len(ring) > args.keep_frames:
            old = ring.pop(0)
            if prev and old == prev[3]:
                ring.insert(0, old)
                break
            if os.path.exists(old):
                os.remove(old)

        if args.iterations and seq >= args.iterations:
            break
        if args.offline_frames is not None:
            continue
        sleep_s = args.interval - (time.monotonic() - t_poll)
        if sleep_s > 0:
            time.sleep(sleep_s)

    logf.close()
    return exit_code


def main() -> int:
    here = os.path.dirname(os.path.abspath(__file__))
    ap = argparse.ArgumentParser(description="PC-side frame-progress watchdog (never reboots)")
    ap.add_argument("--host", default="MiSTer")
    ap.add_argument("--profile", choices=sorted(PROFILES), default="cvc-soak")
    ap.add_argument("--interval", type=float, default=DEFAULT_INTERVAL_S)
    ap.add_argument("--k", type=int, default=None, help="override the profile's static K")
    ap.add_argument("--k-capfail", type=int, default=DEFAULT_K_CAPFAIL)
    ap.add_argument("--tolerance", type=int, default=DEFAULT_TOLERANCE)
    ap.add_argument("--min-changed-frac", type=float, default=DEFAULT_MIN_CHANGED_FRAC)
    ap.add_argument("--capture-timeout", type=float, default=DEFAULT_CAPTURE_TIMEOUT_S)
    ap.add_argument("--frame-dir", default="tmp/framewd/frames")
    ap.add_argument("--log", default="tmp/framewd/frame_watchdog.jsonl")
    ap.add_argument("--keep-frames", type=int, default=60)
    ap.add_argument("--iterations", type=int, default=0, help="0 = run forever")
    ap.add_argument("--max-runtime", type=float, default=0, help="seconds; 0 = unbounded")
    ap.add_argument("--offline-frames", nargs="*", default=None,
                    help="mutant mode: replay these PNGs; MISSING injects a capture failure")
    ap.add_argument("--roi", default=",".join(str(v) for v in DEFAULT_ROI),
                    help="x0,y0,x1,y1 secondary playfield ROI; 'none' to disable")
    ap.add_argument("--chrome-ref-a", default=os.path.join(here, "soak_20260809_214501.png"))
    ap.add_argument("--chrome-ref-b", default=os.path.join(here, "soak2_214552.png"))
    a = ap.parse_args()
    a.roi = None if a.roi.lower() == "none" else tuple(int(v) for v in a.roi.split(","))
    if a.k is None:
        a.k = PROFILES[a.profile]["k"]
    return run(a)


if __name__ == "__main__":
    sys.exit(main())
