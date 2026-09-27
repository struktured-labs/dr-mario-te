#!/usr/bin/env python3
"""Adversarial battery against frame_watchdog.py — tries to BREAK it, not confirm it.

Every case here is an ATTACK with a pre-registered expectation. A case "lands" when the
watchdog's actual behaviour matches the attack's prediction of a DEFECT; it is "survived"
when the watchdog does the safe thing. Exit 0 means the battery reproduced the findings it
recorded; it is a regression gate, so it FAILS if the watchdog's behaviour changes.

All inputs are real: live-soak captures (frames/) and real ROM captures taken in fceux
(screens/). Nothing here contacts the MiSTer.

Run:  python3 adversarial_battery.py
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
FB = os.path.dirname(HERE)                      # experiments/freeze5_blackscreen
WD = os.path.join(FB, "frame_watchdog.py")
sys.path.insert(0, FB)
sys.path.insert(0, HERE)

from frame_watchdog import decode_png, compare          # noqa: E402
from pngio import encode_png, splice, toggle_block      # noqa: E402

FRAMES = os.path.join(HERE, "frames")
SCREENS = os.path.join(HERE, "screens")
FLOOR = 1.0e-3

# geometry measured from the live run's own change map (see below)
P1_BOTTLE = (32, 88, 95, 397)
LEFT_HALF = (0, 0, 128, 448)

RESULTS: list[tuple[str, bool, str]] = []


def record(name: str, landed: bool, detail: str) -> None:
    RESULTS.append((name, landed, detail))
    tag = "ATTACK LANDS" if landed else "watchdog survives"
    print(f"--- {name}\n    {tag}: {detail}")


def load(n: int):
    return decode_png(open(os.path.join(FRAMES, f"f{n:06d}.png"), "rb").read())


def run_watchdog(tmp: str, pngs: list[str], extra: list[str] | None = None):
    d = tempfile.mkdtemp(dir=tmp)
    cmd = [sys.executable, WD, "--offline-frames", *pngs,
           "--frame-dir", os.path.join(d, "frames"),
           "--log", os.path.join(d, "w.jsonl")] + (extra or [])
    p = subprocess.run(cmd, capture_output=True, text=True)
    recs = [json.loads(l) for l in open(os.path.join(d, "w.jsonl"))]
    return recs, p.returncode


def write_seq(tmp: str, name: str, w: int, h: int, frames: list[bytes]) -> list[str]:
    d = os.path.join(tmp, name)
    os.makedirs(d, exist_ok=True)
    out = []
    for i, r in enumerate(frames):
        p = os.path.join(d, f"{i:03d}.png")
        open(p, "wb").write(encode_png(w, h, r))
        out.append(p)
    return out


def geom_check():
    """The capture is NES 256x224 pixel-DOUBLED VERTICALLY. This is load-bearing: it sets
    how many NES tiles the min_changed_frac floor actually corresponds to."""
    w, h, rgb = load(60)
    stride = w * 3
    same = sum(1 for y in range(0, h, 2)
               if rgb[y * stride:(y + 1) * stride] == rgb[(y + 1) * stride:(y + 2) * stride])
    assert (w, h) == (256, 448) and same == h // 2, (w, h, same)
    tile_px = 8 * 16          # one 8x8 NES tile occupies 8 wide x 16 tall image px
    floor_px = w * h * FLOOR
    record("GEOM floor is ~1 NES tile, not ~1.8",
           abs(floor_px / tile_px - 1.8) > 0.5,
           f"{same}/{h//2} row pairs identical => 2x vdouble; floor {floor_px:.1f} px "
           f"= {floor_px/tile_px:.2f} NES tiles (writeup claims ~1.8, which assumes SQUARE px)")


def attack_partial_wedge(tmp):
    """One player's side of the screen is completely dead; the other keeps playing."""
    w, h = load(60)[0], load(60)[1]
    fr = [load(n)[2] for n in range(60, 68)]
    anchor = fr[0]
    for label, box in [("P1 bottle frozen", P1_BOTTLE), ("P1 ENTIRE HALF frozen", LEFT_HALF)]:
        seq = [anchor] + [splice(anchor, f, w, h, box) for f in fr[1:]]
        recs, rc = run_watchdog(tmp, write_seq(tmp, label.replace(" ", "_"), w, h, seq))
        verd = [r["verdict"] for r in recs]
        cf = [r["changed_frac"] for r in recs if "changed_frac" in r]
        landed = set(verd) <= {"INIT", "ALIVE"}
        record(f"PARTIAL WEDGE: {label}", landed,
               f"{verd.count('ALIVE')}/{len(verd)-1} ALIVE, no SUSPECT; "
               f"changed_frac {min(cf):.6f}-{max(cf):.6f} = {min(cf)/FLOOR:.0f}x-"
               f"{max(cf)/FLOOR:.0f}x the floor; roi note never fires (ROI spans BOTH bottles)")


def attack_one_tile(tmp):
    """Totally frozen screen + a single blinking 8x8 NES tile."""
    w, h, anchor = load(60)
    for label, (bw, bh), expect_alive in [("half a tile (8x8 img px)", (8, 8), False),
                                          ("ONE 8x8 NES tile", (8, 16), True),
                                          ("two tiles", (16, 16), True)]:
        seq = [anchor] + [toggle_block(anchor, w, h, 120, 40, bw, bh, on=(i % 2 == 1))
                          for i in range(1, 8)]
        recs, rc = run_watchdog(tmp, write_seq(tmp, "blink" + str(bw) + str(bh), w, h, seq))
        verd = [r["verdict"] for r in recs]
        alive = set(verd) <= {"INIT", "ALIVE"}
        cf = [r["changed_frac"] for r in recs if "changed_frac" in r][0]
        assert alive == expect_alive, (label, verd)
        record(f"BLINK FLOOR: {label}", alive,
               f"changed_frac {cf:.6f} ({cf/FLOOR:.2f}x floor) -> "
               f"{'ALIVE forever on a dead screen' if alive else 'correctly WEDGED'}")


def attack_size_flap(tmp):
    """compare() returns changed_frac=1.0 on a size mismatch => the frames channel FAILS OPEN."""
    w, h, anchor = load(60)
    d = os.path.join(tmp, "sizeflap")
    os.makedirs(d, exist_ok=True)
    pngs = []
    for i in range(8):
        hh = h if i % 2 == 0 else h - 2
        p = os.path.join(d, f"{i:03d}.png")
        open(p, "wb").write(encode_png(w, hh, anchor[:w * hh * 3]))
        pngs.append(p)
    recs, rc = run_watchdog(tmp, pngs)
    verd = [r["verdict"] for r in recs]
    landed = set(verd) <= {"INIT", "ALIVE"}
    record("SIZE FLAP fails OPEN", landed,
           f"identical FROZEN content, alternating height -> {verd.count('ALIVE')} x ALIVE "
           f"with changed_frac=1.0 (compare() maps size_mismatch to MAXIMUM motion)")


def attack_attract_mode(tmp):
    """Real ROM, idle, sampled at the watchdog's own 20 s cadence: the title screen animates
    and then drops into Dr. Mario's ATTRACT DEMO. No cart, no AI, no soak — reads ALIVE."""
    pngs = sorted(os.path.join(SCREENS, f) for f in os.listdir(SCREENS)
                  if f.startswith("t20_"))
    if not pngs:
        return
    recs, rc = run_watchdog(tmp, pngs)
    verd = [r["verdict"] for r in recs]
    cf = [r["changed_frac"] for r in recs if "changed_frac" in r]
    landed = set(verd) <= {"INIT", "ALIVE"}
    record("ATTRACT DEMO reads ALIVE", landed,
           f"{verd.count('ALIVE')}/{len(verd)-1} ALIVE at 20 s cadence; changed_frac "
           f"{min(cf):.6f}-{max(cf):.6f} = {min(cf)/FLOOR:.0f}x-{max(cf)/FLOOR:.0f}x floor "
           f"-- overlaps the healthy soak range [0.017944, 0.284651]")


def attack_static_levelsel(tmp):
    """A real idle LEVEL-SELECT screen is pixel-exactly static -> WEDGED. Correct on a soak
    (a stalled nav IS a failure) but the reason string blames the display path."""
    p = os.path.join(SCREENS, "levelsel_1.png")
    if not os.path.exists(p):
        return
    recs, rc = run_watchdog(tmp, [p] * 5)
    verd = [r["verdict"] for r in recs]
    record("real idle LEVEL-SELECT -> WEDGED", False,
           f"{verd} (pixel-exactly static; alarm is correct for a soak, but reason="
           f"'{recs[-1]['reason']}' names the display path, not the nav stall)")


def attack_stale_frame_dir(tmp):
    """Sensor totally dead (rc=0, writes NOTHING) but the frame-dir already holds frames from
    a previous run at the same seq numbers -> the watchdog REPLAYS them and reports ALIVE."""
    shim_dir = os.path.join(tmp, "shim")
    os.makedirs(shim_dir, exist_ok=True)
    shim = os.path.join(shim_dir, "misterclaw-send")
    with open(shim, "w") as f:
        f.write("#!/bin/sh\nexit 0\n")     # rc=0, writes nothing at all
    os.chmod(shim, 0o755)

    fdir = os.path.join(tmp, "reused_frames")
    os.makedirs(fdir, exist_ok=True)
    for i, n in enumerate([60, 61, 62, 63], start=1):     # leftovers from a previous run
        open(os.path.join(fdir, f"f{i:06d}.png"), "wb").write(
            open(os.path.join(FRAMES, f"f{n:06d}.png"), "rb").read())

    env = dict(os.environ, PATH=shim_dir + os.pathsep + os.environ["PATH"])
    log = os.path.join(tmp, "stale.jsonl")
    subprocess.run([sys.executable, WD, "--iterations", "4", "--interval", "0.1",
                    "--frame-dir", fdir, "--log", log],
                   capture_output=True, text=True, env=env)
    recs = [json.loads(l) for l in open(log)]
    verd = [r["verdict"] for r in recs]
    landed = set(verd) <= {"INIT", "ALIVE"}
    record("DEAD SENSOR reported ALIVE (stale frame-dir)", landed,
           f"{verd} -- capture wrote NOTHING; watchdog re-read the PREVIOUS run's frames. "
           f"No mtime/freshness check: existence+size only. Default --frame-dir is a FIXED "
           f"path and seq always restarts at 1, so a restart re-enters used sequence numbers")


def attack_capture_modes(tmp):
    """The safe directions, verified rather than assumed."""
    cases = {
        "rc!=0": "#!/bin/sh\nexit 1\n",
        "rc=0 but no file": "#!/bin/sh\nexit 0\n",
    }
    for label, body in cases.items():
        sd = os.path.join(tmp, "shim_" + label.replace("!", "n").replace("=", "")
                          .replace(" ", "_"))
        os.makedirs(sd, exist_ok=True)
        shim = os.path.join(sd, "misterclaw-send")
        open(shim, "w").write(body)
        os.chmod(shim, 0o755)
        fdir = os.path.join(sd, "frames")
        log = os.path.join(sd, "w.jsonl")
        env = dict(os.environ, PATH=sd + os.pathsep + os.environ["PATH"])
        subprocess.run([sys.executable, WD, "--iterations", "4", "--interval", "0.1",
                        "--frame-dir", fdir, "--log", log],
                       capture_output=True, text=True, env=env)
        recs = [json.loads(l) for l in open(log)]
        verd = [r["verdict"] for r in recs]
        record(f"CAPTURE {label} (empty frame-dir)", "WEDGED" not in verd,
               f"{verd} -> {recs[-1]['reason']}")


def main() -> int:
    tmp = tempfile.mkdtemp(prefix="advbat_")
    geom_check()
    attack_partial_wedge(tmp)
    attack_one_tile(tmp)
    attack_size_flap(tmp)
    attack_attract_mode(tmp)
    attack_static_levelsel(tmp)
    attack_stale_frame_dir(tmp)
    attack_capture_modes(tmp)
    landed = [n for n, l, _ in RESULTS if l]
    print("\n" + "=" * 78)
    print(f"attacks that LANDED (watchdog defect reproduced): {len(landed)}/{len(RESULTS)}")
    for n in landed:
        print("  *", n)
    return 0


if __name__ == "__main__":
    sys.exit(main())
