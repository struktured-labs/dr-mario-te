#!/usr/bin/env python3
"""Reliable VS-CPU L<level> navigation + rotation validation for the cartridge AI.

Hard-resets, drives the title menu to VS-CPU mode (SELECT cycles 1P->2P->VS-CPU
via the 0x18E5 toggle hook), sets the level, starts play, then (optionally)
saves a state so future runs can skip the menu entirely.

Usage: python nav_vscpu.py [level] [--save STATE] [--load STATE] [--watch N]
"""
import sys, time
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from mesen_interface_file import MesenInterface

WORK = Path(__file__).resolve().parents[1].parent / "mesen2/bin/linux-x64/Release"


def cmd(it, c, timeout=8.0):
    try:
        return it._send_command(c, timeout=timeout)
    except Exception as e:
        return f"(timeout/err: {e})"


def tap(it, btn, hold=6, rest=14):
    it.set_input(0, [btn] if btn else [])
    it.step_frame(hold)
    it.set_input(0, [])
    it.step_frame(rest)


def r(it, a):
    return it.read_memory(a, 1)[0]


def main():
    level = 11
    save = load = None
    watch = 0
    args = sys.argv[1:]
    for i, a in enumerate(args):
        if a.isdigit():
            level = int(a)
        elif a == "--save":
            save = args[i + 1]
        elif a == "--load":
            load = args[i + 1]
        elif a == "--watch":
            watch = int(args[i + 1])

    it = MesenInterface(work_dir=WORK)
    it.connect(timeout=8)

    if load:
        # Load runs free, then re-enter step mode for deterministic watching.
        it.set_step_mode(False)
        print("LOADSTATE:", cmd(it, f"LOADSTATE {load}"))
        time.sleep(0.3)
        it.set_step_mode(True)
        it.step_frame(2)
    else:
        # Hard reset while RUNNING (powerCycle can't process in step mode).
        it.set_step_mode(False)
        print("POWERCYCLE:", cmd(it, "POWERCYCLE"))
        time.sleep(0.6)
        it.set_step_mode(True)
        it.step_frame(180)  # let the title screen settle

        print(f"boot: m46={r(it,0x46)} f04={r(it,0x04)} p727={r(it,0x0727)}")
        # SELECT x2 on the title to reach VS-CPU (1P->2P->VS). Watch p0727/f04.
        for i in range(2):
            tap(it, "select")
            print(f"  sel{i+1}: f04={r(it,0x04)} p727={r(it,0x0727)} m46={r(it,0x46)}")
        # START -> enter level select
        tap(it, "start", 8, 50)
        print(f"after start: m46={r(it,0x46)} f04={r(it,0x04)} p727={r(it,0x0727)}")
        # set level: RIGHT * level (pin moves both sliders in VS-CPU)
        for _ in range(level):
            tap(it, "right", 5, 8)
        # START -> begin play
        tap(it, "start", 8, 120)
        for _ in range(180):
            if r(it, 0x46) == 4:
                break
            it.step_frame(8)

    print(f"=== PLAY m46={r(it,0x46)} f04={r(it,0x04)} p727={r(it,0x0727)} "
          f"P2x={r(it,0x0385)} P2y={r(it,0x0386)} o3A5={r(it,0x03A5)} "
          f"Zbor={r(it,0xDA)} Ztgt={r(it,0x00)} ===")

    if save and r(it, 0x46) == 4 and r(it, 0x04) != 0:
        # Need a real savestate file; LOADSTATE reads a file the lua writes.
        # The bridge only loads; saving uses Mesen's own savestate via INPUT? -
        # fall back: dump RAM is not enough. Use emu.saveState through a cmd if present.
        print("SAVESTATE:", cmd(it, f"SAVESTATE {save}"))

    if watch:
        print("--- watching orientation/rotation over", watch, "frames ---")
        prev = None
        for f in range(watch):
            it.step_frame(1)
            snap = (r(it, 0x03A5), r(it, 0xDA), r(it, 0x0385), r(it, 0x00),
                    r(it, 0x0386), r(it, 0xF6), r(it, 0x5B))
            if snap != prev:
                print(f" f{f:3d}: o3A5={snap[0]} Zbor={snap[1]} P2x={snap[2]} "
                      f"Ztgt={snap[3]} P2y={snap[4]} F6=${snap[5]:02X} edge5B=${snap[6]:02X}")
                prev = snap


if __name__ == "__main__":
    main()
