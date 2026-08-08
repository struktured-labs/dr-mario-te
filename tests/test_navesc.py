#!/usr/bin/env python3
"""DRNAVESC gate: the stuck-screen escape fires on SIMULATED FREEZES, and only on them.

Task #38. Three silicon freezes (2026-08-01/02, evidence in qa-wt experiments/freeze_20260801/)
parked the game on screens awaiting a START the nav never sends. Per the house rule this gate
REPRODUCES THE DEFECT rather than asserting the guard exists: it drives the real emitted
driver bytes with the game frozen in mode 3 (the exact freeze-2 shape) and asserts the escape
presses START at ~ESC_N hooks -- then proves the three ways it must NOT fire:

  A  stuck mode 3, static tuple      -> a 4-hook START burst at ~ESC_N, re-armed bursts after
  B  mode 4 with $0386 moving        -> NEVER fires (live play is structurally excluded)
  C  mode 8 (intro), static          -> NEVER fires (hands-off rule)
  D  DRNAVESC off                    -> empty emission delta is deterministic (flag-off carts
                                        stay byte-identical; the cart-matrix sweep is the
                                        authority for class hashes)

    tests/test_navesc.py             # asserts; exit 1 on failure
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
B_START = 0x10
_FLAGS = ("DRNOFREEZE", "DRHUMAN", "DRPOCKET", "DRRECOMMIT_NOFREEZE", "DRNAVDWELL",
          "DRPENDBOUND", "DRCOLDINIT", "DRSLAM_KOPEN", "DRP1WIGGLE", "DRP1NATIVE",
          "DRNAVESC", "DRNAVESC_N")
_seq = [0]


def build(flags):
    for k in _FLAGS:
        os.environ.pop(k, None)
    os.environ.update(flags)
    _seq[0] += 1
    name = "navesc_build_%d" % _seq[0]
    spec = importlib.util.spec_from_file_location(name, EMITTER)
    P = importlib.util.module_from_spec(spec)
    sys.modules[name] = P
    spec.loader.exec_module(P)
    unit1, labels = P.build_main(11, 1)
    return P, bytes(unit1), {k: BASE + v for k, v in labels.items()}


def run_hooks(unit1, labels, n_hooks, mode, f8=0, p2row=9, move_p2=False):
    """Drive n_hooks raw driver invocations with the screen tuple controlled.
    Returns the list of hook indices whose $F5 ended with START set."""
    m = MPU()
    m.memory[BASE:BASE + len(unit1)] = unit1
    presses = []
    for h in range(n_hooks):
        m.memory[0x0046] = mode
        m.memory[0xF8] = f8
        m.memory[0x0386] = (h & 0xFF) if move_p2 else p2row
        # keep the rest of the world quiet: no viruses seen, no match active
        m.memory[0xF5] = 0
        m.memory[0x1FE], m.memory[0x1FF] = (SENT - 1) & 0xFF, (SENT - 1) >> 8
        m.sp = 0xFD
        m.pc = labels["main"]
        n = 0
        while m.pc != SENT and n < 60000:
            m.step()
            n += 1
        assert m.pc == SENT, "runaway pc=%04X hook=%d" % (m.pc, h)
        if m.memory[0xF5] & B_START:
            presses.append(h)
    return presses


def main():
    flags = {"DRNOFREEZE": "1", "DRNAVESC": "1"}
    P, unit1, labels = build(flags)
    esc_n = P.ESC_N

    # A: the defect -- stuck mode-3 screen (freeze #2's shape). Expect a 4-hook burst at
    # ~ESC_N and a SECOND burst one full period later (the re-arm).
    presses = run_hooks(unit1, labels, esc_n * 2 + 40, mode=3)
    assert presses, "escape NEVER fired on a stuck mode-3 screen"
    first = presses[0]
    assert esc_n - 10 <= first <= esc_n + 12, \
        "first escape at hook %d, expected ~%d" % (first, esc_n)
    burst1 = [p for p in presses if p < first + 8]
    assert len(burst1) >= 2, "press burst too short to survive the two-pass AND: %r" % burst1
    later = [p for p in presses if p > first + 8]
    assert later and abs(later[0] - (first + esc_n + 4)) <= 12, \
        "no re-armed second burst near %d: %r" % (first + esc_n + 4, presses[:8] + later[:4])

    # A2: freeze #3's shape -- mode 4 round-wait, $0386 static.
    presses4 = run_hooks(unit1, labels, esc_n + 40, mode=4)
    assert presses4 and esc_n - 10 <= presses4[0] <= esc_n + 12, \
        "mode-4 round-wait not escaped: %r" % presses4[:4]

    # B: live play control -- mode 4 with the P2 pill row moving every hook. MUST never fire.
    assert run_hooks(unit1, labels, esc_n * 2 + 40, mode=4, move_p2=True) == [], \
        "escape fired during simulated LIVE PLAY -- would press START mid-match"

    # C: intro (mode 8), static. MUST never fire (hands-off rule).
    assert run_hooks(unit1, labels, esc_n * 2 + 40, mode=8) == [], \
        "escape fired during the intro -- violates the mode-8 hands-off rule"

    # D: flag-off emission is deterministic and differs from flag-on (the flag is real).
    _, off1, _ = build({"DRNOFREEZE": "1"})
    _, off2, _ = build({"DRNOFREEZE": "1", "DRNAVESC": "0"})
    assert off1 == off2, "flag-off emission not deterministic"
    assert off1 != unit1, "DRNAVESC=1 changed nothing -- the escape was not emitted"

    print("NAVESC gate: A stuck-mode3 burst@%d OK, A2 mode4-wait OK, B live-play silent OK, "
          "C intro silent OK, D flag-off identity OK" % first)


if __name__ == "__main__":
    main()
