#!/usr/bin/env python3
"""ROM-LEVEL POSITIVE CONTROL for #124: min vs max over hit columns, UNEQUAL heights.

Origin: written by the garbage-window-mechanics lane, 2026-08-19, and vendored here
because it lived in a session scratchpad that gets cleaned -- the earlier garbwin rigs
were already lost that way, which killed the citation behind the published 8/8. Anything
cited as a reproduction path has to live in the repo (gate-standard rule 8).

WHY IT EXISTS. test_gw_hhit.py gates the FARM'S IMPLEMENTATION of W = 264 - 16*h_hit.
It cannot convict the FORMULA -- for that you have to ask the ROM. And the published
8/8 verification could not convict it either, because every one of those cases used a
FLAT stack, where h_min == h_max. That is the same blind spot that hid #124 for weeks:
the "ground truth" was silent on precisely the question the bug turns on.

    H_min:  W = 264 - 16*min(h over hit cols)     (claimed, and what the farm now logs)
    H_max:  W = 264 - 16*max(h over hit cols)     (the farm's pre-#124 form)

This paints columns to DIFFERENT heights, pins frameCounter so the volley lands in known
columns, and measures the real Rev 0 ROM under real 2P VS with checkReleaseAttack firing
naturally. The two hypotheses then predict widely separated frame counts, so each
measurement kills one.

MEASURED (both the originating lane and this vendored copy, identical):
    A  hit {1:h2,  5:h12}          H_min 232 | H_max  72 | ROM 232   H_max off by 160 f
    B  hit {1:h12, 5:h2}  order    H_min 232 | H_max  72 | ROM 232   H_max off by 160 f
    C  hit {1:h11, 3:h10, 5:h1, 7:h12}
                                   H_min 248 | H_max  72 | ROM 248   H_max off by 176 f
    D  hit {1:h7,  5:h7}  EQUAL    H_min 152 | H_max 152 | ROM 152   coincide: INVARIANT

⚠ D DISCRIMINATES NOTHING and is labelled that way. The original printed "H_min
CONFIRMED, H_max REFUTED" for it, because the verdict string took the `t == pred_min`
branch on a tie -- flagged by its own author before anyone quoted it. Here coincidence
is detected explicitly and D can only ever report INVARIANT HELD or a failure. It is the
control that demonstrates the blind spot, not evidence against H_max.

PROVENANCE OF THE TWO PATH DEFECTS -- corrected 2026-08-19 at the original author's
insistence, because getting this backwards in a thread about provenance would be the
same corruption in miniature:
  * THEIRS: a single hardcoded absolute path into a sibling worktree (the #118/#127
    literal hazard). Replaced here by the ordered search below.
  * MINE: the silent ROM fallback. It did NOT exist in the original -- with one literal
    and no override there was nothing to fall through TO. It arrived WITH my ordered
    search, which treated DRMARIO_ROM as merely one more candidate, so pointing it at a
    missing file silently measured a DIFFERENT ROM and printed a confident PASS. Caught
    by the skip test rather than by reading the code. Fixing one hazard class introduced
    another; that is the note worth keeping, not the credit.

Run: /home/struktured/projects/dr-mario-mods/.venv/bin/python rom_gate_uneven_minmax.py
Exit: 0 pass · 1 a case failed · 77 SKIPPED (nes_py or ROM absent -- never a silent pass)
"""
from __future__ import annotations

import hashlib
import os
import sys

FPS = 60.0988
COLS, ROWS = 8, 16

# Commercial ROM: deliberately NOT vendored. Resolved at run time, and its absence is
# reported as a SKIP that names every path tried -- an absent ROM must never read as a
# pass. Override with DRMARIO_ROM.
ROM_MD5 = "d3ec44424b5ac1a4dc77709829f721c9"      # Rev 0, the ROM these numbers came from
ROM_CANDIDATES = [
    os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "drmario.nes"),
    "/home/struktured/projects/dr-mario-canonical-wt/drmario.nes",
    "/home/struktured/projects/dr-mario-mods/drmario.nes",
]

MODE, FRAMECTR = 0x46, 0x43
P1F, P1_NEXTACT, P1_FAIL = 0x0400, 0x0317, 0x0313
P2_ATKSIZE, P2_ATKCOL = 0x0398, 0x03A9
NBPLAYERS = 0x0727
START, SELECT, DOWN, NONE = 0x08, 0x04, 0x20, 0x00
SINGLE = 0x80          # singleHalfPill; colour in the low nibble


class Skip(Exception):
    """Preconditions absent. Reported loudly with what was searched, never as a pass."""


def _check_md5(p):
    got = hashlib.md5(open(p, "rb").read()).hexdigest()
    if got != ROM_MD5 and not os.environ.get("DRMARIO_ROM_ANY"):
        raise Skip(f"ROM at {p} has md5 {got}, expected {ROM_MD5} (Rev 0). These frame "
                   "counts are ROM-specific; set DRMARIO_ROM_ANY=1 to measure anyway.")
    return p


def find_rom():
    """Locate the ROM. DRMARIO_ROM, if set, is AUTHORITATIVE -- never a hint.

    ★ An explicit override that does not exist is an ERROR, not a reason to fall back.
    The first version of this function treated it as one more candidate, so pointing it
    at a missing file silently measured a DIFFERENT ROM and printed a confident PASS.
    That is the [[dr-mario-watchdog-mgl-silent-cart-fallback]] shape exactly: the run
    reports success while the artifact under test is not the one you named."""
    env = os.environ.get("DRMARIO_ROM", "")
    if env:
        p = os.path.normpath(env)
        if not os.path.exists(p):
            raise Skip(f"DRMARIO_ROM={p} does not exist. Refusing to fall back to a "
                       "different ROM -- an explicit override is authoritative.")
        return _check_md5(p)

    tried = []
    for p in ROM_CANDIDATES:
        p = os.path.normpath(p)
        tried.append(p)
        if os.path.exists(p):
            return _check_md5(p)
    raise Skip("no Dr. Mario ROM found. Searched, in order: " + "; ".join(tried)
               + ". Set DRMARIO_ROM=<path>. The ROM is commercial and is deliberately "
                 "not vendored in this repo.")


def load_nes():
    try:
        import nes_py._rom as _rom
    except ImportError as e:
        raise Skip(
            f"nes_py not importable in {sys.executable} ({e}). Use the repo venv: "
            "/home/struktured/projects/dr-mario-mods/.venv/bin/python") from e
    # numpy-2 compat: nes_py's *_rom_stop overflow on uint8 sizes. Must precede NESEnv.
    _rom.ROM.prg_rom_stop = property(
        lambda self: int(self.prg_rom_start) + int(self.prg_rom_size) * 2 ** 10)
    _rom.ROM.chr_rom_stop = property(
        lambda self: int(self.chr_rom_start) + int(self.chr_rom_size) * 2 ** 10)
    from nes_py import NESEnv
    return NESEnv


def boot_2p(NESEnv, rom):
    env = NESEnv(rom)
    env.reset()
    ram = env.ram
    for _ in range(150):
        env.step(NONE)
    for _ in range(4):                 # SELECT at the title toggles 1P/2P
        env.step(SELECT)
    for _ in range(8):
        env.step(NONE)
    if int(ram[NBPLAYERS]) != 2:
        raise AssertionError(f"failed to reach 2P: nbPlayers={int(ram[NBPLAYERS])}")
    for i in range(1200):
        env.step(START if (i % 24) < 4 else NONE)
        if int(ram[MODE]) == 4:
            break
    else:
        raise AssertionError("never reached mode 4 (in-match)")
    for _ in range(30):
        env.step(NONE)
    return env, ram


def paint_uneven(ram, heights):
    """Fill column c to heights[c] with a (r+c)%3 colour pattern (no 4-runs)."""
    for i in range(128):
        ram[P1F + i] = 0xFF
    for c in range(COLS):
        for r in range(ROWS - heights[c], ROWS):
            ram[P1F + r * 8 + c] = SINGLE | ((r + c) % 3)


def run_case(NESEnv, rom, heights, atksize, colors, fc_pin, label):
    """Returns (ok, line) for one painted board + volley."""
    env, ram = boot_2p(NESEnv, rom)
    while int(ram[P1_NEXTACT]) != 0:
        env.step(NONE)
    paint_uneven(ram, heights)

    released = False
    for n in range(900):
        ram[P2_ATKSIZE] = atksize                      # re-arm until it fires
        for i, c in enumerate(colors[:atksize]):
            ram[P2_ATKCOL + i] = c
        if int(ram[P1_NEXTACT]) == 2:                  # about to run checkAttack
            ram[FRAMECTR] = fc_pin                     # pin the volley's columns
            env.step(NONE)
            released = True
            break
        env.step(DOWN if (n % 2) == 0 else NONE)
    if not released:
        return False, f"{label}: FAIL -- attack never released"

    hit = [c for c in range(COLS) if int(ram[P1F + c]) != 0xFF]
    if not hit:
        return False, f"{label}: FAIL -- no column was hit"
    hb = {c: heights[c] for c in hit}                  # PRE-garbage heights
    h_min, h_max = min(hb.values()), max(hb.values())
    pred_min, pred_max = 264 - 16 * h_min, 264 - 16 * h_max

    t = 1
    while t < 2000:
        if int(ram[P1_NEXTACT]) == 0 or int(ram[P1_FAIL]) != 0:
            break
        env.step(NONE)
        t += 1

    # ★ COINCIDENCE IS ITS OWN OUTCOME. When the hypotheses agree, no refutation is
    # available and claiming one is exactly the error that let a flat-stack 8/8 pose
    # as ground truth. This branch must come FIRST.
    if pred_min == pred_max:
        ok = (t == pred_min)
        verdict = ("INVARIANT HELD (both predict %d; discriminates NOTHING)" % pred_min
                   if ok else "INVARIANT BROKEN -- both hypotheses predict %d, ROM says %d"
                   % (pred_min, t))
    elif t == pred_min:
        verdict = f"H_min CONFIRMED, H_max REFUTED by {abs(pred_min - pred_max)} f"
        ok = True
    elif t == pred_max:
        verdict = f"H_max CONFIRMED, H_min REFUTED by {abs(pred_min - pred_max)} f"
        ok = False        # would overturn the #124 fix -- must fail the gate loudly
    else:
        verdict = "NEITHER hypothesis matches -- investigate"
        ok = False

    line = (f"{label}\n"
            f"   hit cols {hit}   h_before {hb}   h_min={h_min} h_max={h_max}\n"
            f"   H_min predicts {pred_min:4d} f | H_max predicts {pred_max:4d} f "
            f"| MEASURED {t:4d} f ({t / FPS:.2f} s)\n"
            f"   => {verdict}")
    return ok, line


def main():
    try:
        NESEnv = load_nes()
        rom = find_rom()
    except Skip as e:
        print(f"SKIPPED -- preconditions absent, NOT a pass.\n  {e}", file=sys.stderr)
        return 77
    print(f"ROM {rom}\n")

    base = [6] * COLS          # cols 3/4 moderate so the live pill lands harmlessly
    a = list(base); a[1], a[5] = 2, 12
    b = list(base); b[1], b[5] = 12, 2
    c = list(base); c[1], c[3], c[5], c[7] = 11, 10, 1, 12
    d = list(base); d[1], d[5] = 7, 7
    cases = [
        (a, 2, (0, 1), 0x01, "A  shallow=col1(h2)  deep=col5(h12)", True),
        (b, 2, (0, 1), 0x01, "B  deep=col1(h12)  shallow=col5(h2)   [order control]", True),
        (c, 4, (0, 1, 2, 0), 0x01, "C  4-wide {1,3,5,7}, shallowest=col5(h1)", True),
        (d, 2, (0, 1), 0x01, "D  EQUAL heights (h7) -- hypotheses coincide [CONTROL]", False),
    ]

    ok_all, n_disc = True, 0
    for heights, atk, cols, fc, label, discriminates in cases:
        ok, line = run_case(NESEnv, rom, heights, atk, cols, fc, label)
        print(line + "\n")
        ok_all &= ok
        if discriminates and ok:
            n_disc += 1

    # NOT VACUOUS: at least one case must actually separate the hypotheses, or this
    # rig has reproduced the flat-stack failure it exists to correct.
    if n_disc == 0:
        print("FAIL: no discriminating case passed -- this is the flat-stack blind "
              "spot again, not a verification.")
        ok_all = False
    else:
        print(f"{n_disc}/3 discriminating cases confirm H_min and refute H_max; "
              "D is the coincidence control and proves nothing by design.")
    print("PASS" if ok_all else "FAIL")
    return 0 if ok_all else 1


if __name__ == "__main__":
    sys.exit(main())
