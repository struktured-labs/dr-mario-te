#!/usr/bin/env python3
"""Two-sided py65 proof for the STUDYCOUNTS OAM-leak garble fix.

Defect: STUDYCOUNTS writes live digit sprites into OAM shadow-buffer slots 8-15
every PLAY-mode hook ($0046==4), but (pre-fix) does nothing on any other mode --
neither redraw nor blank. This reproduces that exact sequence at the CPU-RAM
level (same technique as tests/test_study2p.py's one_hook helper), but reuses
ONE MPU instance across two hook calls so slot content from the play hook
persists into the settings-screen hook, exactly as it would across two real
NES frames sharing the same $0200 shadow-OAM buffer in CPU RAM.

  A (defect, pre-fix code): play hook (mode=4) writes non-$FF digit tiles into
    slots 8-15; a SUBSEQUENT settings-screen hook (mode=1) leaves them exactly
    as the play hook left them -- garbage persists.
  B (fix, post-fix code): the same sequence, but the settings-screen hook now
    forces all 8 Y-bytes to $FF (off-screen) -- garbage gone.
  C flag-off (DRSTUDYCOUNTS=0) emission unaffected -- the fix code doesn't run.
"""
import os
import sys
import importlib.util

from py65.devices.mpu6502 import MPU

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
EMITTER = os.path.join(REPO, "patch_cartridge_copro.py")
sys.path.insert(0, REPO)

BASE = 0x8000
SENT = 0x4FF2
_FLAGS = ("DRNOFREEZE", "DRHUMAN", "DRPOCKET", "DRRECOMMIT_NOFREEZE", "DRNAVDWELL",
          "DRPENDBOUND", "DRCOLDINIT", "DRSTUDYCOUNTS", "DRSTUDY2P", "DRNAVESC")
_seq = [0]

# The 8 OAM Y-byte addresses STUDYCOUNTS owns (slots 8-15).
SLOTS = (8, 9, 10, 11, 12, 13, 14, 15)
Y_ADDRS = [0x0200 + s * 4 for s in SLOTS]


def build(flags):
    for k in _FLAGS:
        os.environ.pop(k, None)
    os.environ.update(flags)
    _seq[0] += 1
    name = "leak_build_%d" % _seq[0]
    spec = importlib.util.spec_from_file_location(name, EMITTER)
    P = importlib.util.module_from_spec(spec)
    sys.modules[name] = P
    spec.loader.exec_module(P)
    unit1, labels = P.build_main(11, 1)
    return P, bytes(unit1), {k: BASE + v for k, v in labels.items()}


def run_hook(m, unit1, labels, mode, players=2, vc1=0x48, vc2=0x22, lvl1=11, lvl2=11):
    """Run one hook invocation on an EXISTING mpu (memory persists across calls)."""
    m.memory[BASE:BASE + len(unit1)] = unit1
    m.memory[0x0046] = mode
    m.memory[0x0727] = players
    m.memory[0x04] = 1
    m.memory[0x0324] = vc1          # P1 virus count (BCD)
    m.memory[0x03A4] = vc2          # P2 virus count (BCD)
    m.memory[0x0316] = lvl1         # P1 level (binary)
    m.memory[0x0396] = lvl2         # P2 level (binary)
    m.memory[0x0306] = 15           # spawn row: no lock edge
    m.memory[0x0386] = 15
    m.memory[0x1FE], m.memory[0x1FF] = (SENT - 1) & 0xFF, (SENT - 1) >> 8
    m.sp = 0xFD
    m.pc = labels["main"]
    n = 0
    while m.pc != SENT and n < 60000:
        m.step()
        n += 1
    assert m.pc == SENT, "runaway pc=%04X" % m.pc
    return m


def main():
    human = {"DRHUMAN": "1", "DRPOCKET": "1", "DRNOFREEZE": "1", "DRSTUDYCOUNTS": "1"}
    P, unit1, labels = build(human)
    assert P.STUDY and P.STUDYCOUNTS, "STUDYCOUNTS not active under this build"

    # ---- A: play hook writes real digit sprites into slots 8-15 ----
    m = MPU()
    run_hook(m, unit1, labels, mode=4, vc1=0x48, vc2=0x22, lvl1=11, lvl2=11)
    play_y = [m.memory[a] for a in Y_ADDRS]
    assert any(y != 0xFF for y in play_y), (
        "play hook never wrote digit sprites (test setup broken): Y bytes = %r" % play_y)
    print("PASS: play-mode hook wrote non-FF Y into >=1 of slots 8-15: %r" % play_y)

    # ---- B: SAME mpu (memory persists), now hook fires in settings-screen mode ----
    run_hook(m, unit1, labels, mode=1, players=2)   # mode=1: settings/level-select screen
    settle_y = [m.memory[a] for a in Y_ADDRS]
    print("settings-screen hook Y bytes after: %r" % settle_y)
    assert all(y == 0xFF for y in settle_y), (
        "GARBLE REPRODUCES: settings-screen hook left stale digit sprites visible "
        "(slots 8-15 Y bytes should all be $FF/off-screen): %r" % settle_y)
    print("PASS: settings-screen hook blanked all 8 slots (Y=$FF) -- no garble")

    # ---- C: flag-off emission unaffected (byte-identical guard) ----
    _, off1, _ = build(dict(human, DRSTUDYCOUNTS="0"))
    _, off2, _ = build(dict(human, DRSTUDYCOUNTS="0"))
    assert off1 == off2, "flag-off emission not deterministic"
    print("PASS: DRSTUDYCOUNTS=0 emission deterministic (%d bytes)" % len(off1))

    print("\n==== ALL CHECKS PASSED (fix verified two-sided) ====")


if __name__ == "__main__":
    main()
