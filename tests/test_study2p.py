#!/usr/bin/env python3
"""DRSTUDY2P gate: the driver-side 2P pause-preview tail writes the exact layout the
evac'd base-ROM tail was supposed to draw (task #39; probe-proven defect signature:
P1 preview frozen at 1P position Y=$45 X=$BE/$C6, P2 slots never written, STUDY unlifted).

Asserts on the REAL emitted bytes via py65:
  A  2P/VS hook -> slots 37-40 carry the 2P layout (Y=$33, P1 X=$38/$40, P2 X=$B8/$C0,
     tiles $60|color / $70|color from the LIVE preview bytes) + STUDY letters at Y=$08
  B  1P hook ($0727=1) -> none of those slots written (branch not taken)
  C  flag-off emission deterministic and != flag-on (the flag is real)

    tests/test_study2p.py            # asserts; exit 1 on failure
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


def build(flags):
    for k in _FLAGS:
        os.environ.pop(k, None)
    os.environ.update(flags)
    _seq[0] += 1
    name = "study2p_build_%d" % _seq[0]
    spec = importlib.util.spec_from_file_location(name, EMITTER)
    P = importlib.util.module_from_spec(spec)
    sys.modules[name] = P
    spec.loader.exec_module(P)
    unit1, labels = P.build_main(11, 1)
    return P, bytes(unit1), {k: BASE + v for k, v in labels.items()}


def one_hook(unit1, labels, players, pv1=(1, 2), pv2=(0, 2)):
    m = MPU()
    m.memory[BASE:BASE + len(unit1)] = unit1
    m.memory[0x0046] = 4                      # play mode (pause keeps it 4)
    m.memory[0x0727] = players
    m.memory[0x04] = 1
    m.memory[0x031A], m.memory[0x031B] = pv1  # P1 next-pill colors
    m.memory[0x039A], m.memory[0x039B] = pv2  # P2 next-pill colors
    m.memory[0x0306] = 15                     # spawn row: no lock edge
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
    P, unit1, labels = build(dict(human, DRSTUDY2P="1"))
    assert P.STUDY2P, "STUDY2P not active under a human/study build"

    # A: 2P layout written by one hook
    m = one_hook(unit1, labels, players=2, pv1=(1, 2), pv2=(0, 2))
    oam = m.memory
    expect = {
        0x0294: 0x33, 0x0295: 0x60 | 1, 0x0296: 0x02, 0x0297: 0x38,   # slot 37: P1 L
        0x0298: 0x33, 0x0299: 0x70 | 2, 0x029A: 0x02, 0x029B: 0x40,   # slot 38: P1 R
        0x029C: 0x33, 0x029D: 0x60 | 0, 0x029E: 0x02, 0x029F: 0xB8,   # slot 39: P2 L
        0x02A0: 0x33, 0x02A1: 0x70 | 2, 0x02A2: 0x02, 0x02A3: 0xC0,   # slot 40: P2 R
        0x0280: P.STUDY_2P_Y, 0x0284: P.STUDY_2P_Y, 0x0288: P.STUDY_2P_Y,
        0x028C: P.STUDY_2P_Y, 0x0290: P.STUDY_2P_Y,                    # STUDY lift
    }
    bad = {hex(a): (hex(oam[a]), hex(v)) for a, v in expect.items() if oam[a] != v}
    assert not bad, "2P layout wrong (addr: got/want): %r" % bad

    # B: 1P writes the 1P layout to slots 37-38 (the driver owns previews in BOTH modes now
    # that part1 is letters-only) and leaves P2 slots + the STUDY lift untouched.
    m1 = one_hook(unit1, labels, players=1, pv1=(1, 2))
    expect_1p = {
        0x0294: 0x45, 0x0295: 0x60 | 1, 0x0296: 0x02, 0x0297: 0xBE,   # slot 37: P1 L, 1P pos
        0x0298: 0x45, 0x0299: 0x70 | 2, 0x029A: 0x02, 0x029B: 0xC6,   # slot 38: P1 R, 1P pos
    }
    bad1 = {hex(a): (hex(m1.memory[a]), hex(v)) for a, v in expect_1p.items() if m1.memory[a] != v}
    assert not bad1, "1P layout wrong: %r" % bad1
    untouched = [0x029C, 0x029D, 0x02A0, 0x02A1, 0x0280, 0x0290]
    leaked = {hex(a): hex(m1.memory[a]) for a in untouched if m1.memory[a] != 0}
    assert not leaked, "1P hook wrote P2/lift slots: %r" % leaked
    # B2: the EVAC part1 blob is letters-only (no preview writes left to stomp the driver)
    assert P.STUDY_BLOB_EVAC[:8] == bytes.fromhex("A980854220F68860"), \
        "EVAC part1 is not the letters-only v2 form"
    assert len(P.STUDY_BLOB_EVAC) == 52, "EVAC blob must fill the audited 52B run"

    # C: flag-off identity
    _, off1, _ = build(dict(human, DRSTUDY2P="0"))
    _, off2, _ = build(dict(human, DRSTUDY2P="0"))
    assert off1 == off2, "flag-off emission not deterministic"
    assert off1 != unit1, "DRSTUDY2P=1 changed nothing"

    print("STUDY2P gate: A 2P layout OK, B 1P untouched OK, C flag-off identity OK")


if __name__ == "__main__":
    main()
