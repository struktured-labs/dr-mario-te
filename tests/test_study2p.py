#!/usr/bin/env python3
"""DRSTUDY2P gate: the driver-side 2P pause-preview tail writes the exact layout the
evac'd base-ROM tail was supposed to draw (task #39; probe-proven defect signature:
P1 preview frozen at 1P position Y=$45 X=$BE/$C6, P2 slots never written, STUDY unlifted).

PAUSE GATE (2026-08-08 field-defect fix): the block draws ONLY when the S2P_TTL
play-frame heartbeat has drained (= a mode-4 blocking wait, i.e. the pause loop) with
MATCH_ACTIVE set and no board hold; on live play frames (TTL>0) it BLANKS slots 32-40
(Y=$FF) and decrements the TTL. The old unconditional draw is the OAM leak the owner
saw on the Pocket ("flickers + STUDY on top as if start pressed").

Asserts on the REAL emitted bytes via py65:
  A  paused 2P/VS hook (TTL=0, MATCH_ACTIVE=1) -> slots 37-40 carry the 2P layout
     (Y=$33, P1 X=$38/$40, P2 X=$B8/$C0, tiles from the LIVE preview bytes) + STUDY Y=$08
  B  paused 1P hook ($0727=1) -> 1P layout, P2 slots untouched
  C  flag-off emission deterministic and != flag-on (the flag is real)
  D  DEFECT SHAPE, live play hook (TTL topped up as the $D2CC heartbeat leaves it):
     NO letter tiles written, slots parked at Y=$FF, TTL decremented -- the exact
     hook state that used to leak now provably blanks
  E  board-hold hook (DRHOLDBOARD=1, HOLD_ACTIVE=1, TTL drained) -> blanked, no STUDY
     over the held board
  F  first play hook of a match (MATCH_ACTIVE=0, TTL=0) -> blanked (heartbeat not started)

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
          "DRPENDBOUND", "DRCOLDINIT", "DRSTUDYCOUNTS", "DRSTUDY2P", "DRNAVESC",
          "DRHOLDBOARD")
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


def one_hook(unit1, labels, players, pv1=(1, 2), pv2=(0, 2),
             ttl=0, match_active=1, hold_active=0):
    m = MPU()
    m.memory[BASE:BASE + len(unit1)] = unit1
    m.memory[0x0046] = 4                      # play mode (pause keeps it 4)
    m.memory[0x0727] = players
    m.memory[0x04] = 1
    m.memory[0x6149] = 0xA5                   # NAV_MAGIC: steady-state (power-on init done),
                                              # else the init clears MATCH_ACTIVE this hook
    m.memory[0x61B0] = ttl                    # S2P_TTL: 0 = heartbeat drained (paused)
    m.memory[0x6164] = match_active           # MATCH_ACTIVE
    m.memory[0x6195] = hold_active            # HOLD_ACTIVE (DRHOLDBOARD builds)
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
        0x0281: 0x0D, 0x0285: 0xA0, 0x0289: 0x0C, 0x028D: 0xA1, 0x0291: 0xA2,  # letter tiles
        0x0283: 0x70, 0x0287: 0x78, 0x028B: 0x80, 0x028F: 0x88, 0x0293: 0x90,  # letter X
    }
    bad = {hex(a): (hex(oam[a]), hex(v)) for a, v in expect.items() if oam[a] != v}
    assert not bad, "2P layout wrong (addr: got/want): %r" % bad

    # B: 1P writes the 1P layout to slots 37-38 (the driver owns previews in BOTH modes now
    # that part1 is letters-only) and leaves P2 slots + the STUDY lift untouched.
    m1 = one_hook(unit1, labels, players=1, pv1=(1, 2))
    expect_1p = {
        0x0294: 0x45, 0x0295: 0x60 | 1, 0x0296: 0x02, 0x0297: 0xBE,   # slot 37: P1 L, 1P pos
        0x0298: 0x45, 0x0299: 0x70 | 2, 0x029A: 0x02, 0x029B: 0xC6,   # slot 38: P1 R, 1P pos
        0x0280: 0x0F, 0x0284: 0x0F, 0x0288: 0x0F, 0x028C: 0x0F, 0x0290: 0x0F,  # letters, 1P Y
        0x0281: 0x0D, 0x0291: 0xA2, 0x0283: 0x70, 0x0293: 0x90,                # letter tiles/X (ends)
    }
    bad1 = {hex(a): (hex(m1.memory[a]), hex(v)) for a, v in expect_1p.items() if m1.memory[a] != v}
    assert not bad1, "1P layout wrong: %r" % bad1
    untouched = [0x029C, 0x029D, 0x02A0, 0x02A1]                       # P2 slots only
    leaked = {hex(a): hex(m1.memory[a]) for a in untouched if m1.memory[a] != 0}
    assert not leaked, "1P hook wrote P2 slots: %r" % leaked
    # B2: the EVAC part1 blob is the v4 HEARTBEAT (LDA #N; STA S2P_TTL; RTS)
    want = bytes([0xA9, P.S2P_TTL_N, 0x8D, P.S2P_TTL & 0xFF, P.S2P_TTL >> 8, 0x60])
    assert P.STUDY_BLOB_EVAC[:6] == want and set(P.STUDY_BLOB_EVAC[6:]) == {0xFF}, \
        "EVAC part1 is not the v4 heartbeat form"
    assert len(P.STUDY_BLOB_EVAC) == 52, "EVAC blob must fill the audited 52B run"

    # C: flag-off identity
    _, off1, _ = build(dict(human, DRSTUDY2P="0"))
    _, off2, _ = build(dict(human, DRSTUDY2P="0"))
    assert off1 == off2, "flag-off emission not deterministic"
    assert off1 != unit1, "DRSTUDY2P=1 changed nothing"

    # D: DEFECT SHAPE -- a live play hook (heartbeat topped up, exactly what $D2CC leaves
    # behind every unpaused frame). The pre-fix block drew STUDY here (the field leak);
    # the fix must blank instead. Slots parked offscreen, letter tiles untouched, TTL DEC'd.
    md = one_hook(unit1, labels, players=2, ttl=P.S2P_TTL_N, match_active=1)
    ys = [0x0200 + s_ * 4 for s_ in range(32, 41)]
    off = {hex(a): hex(md.memory[a]) for a in ys if md.memory[a] != 0xFF}
    assert not off, "live-play hook left slots visible (the leak): %r" % off
    tiles_untouched = [0x0281, 0x0285, 0x0289, 0x028D, 0x0291, 0x0295, 0x0299, 0x029D, 0x02A1]
    drawn = {hex(a): hex(md.memory[a]) for a in tiles_untouched if md.memory[a] != 0}
    assert not drawn, "live-play hook wrote STUDY/preview tiles (the leak): %r" % drawn
    assert md.memory[0x61B0] == P.S2P_TTL_N - 1, "live-play hook must DEC the TTL"

    # E: board-hold (STAGE CLEAR / GAME OVER wait, mode still 4, heartbeat drained):
    # STUDY must NOT be drawn over the held board.
    Ph, unit1h, labelsh = build(dict(human, DRSTUDY2P="1", DRHOLDBOARD="1"))
    mh = one_hook(unit1h, labelsh, players=2, ttl=0, match_active=1, hold_active=1)
    offh = {hex(a): hex(mh.memory[a]) for a in ys if mh.memory[a] != 0xFF}
    assert not offh, "hold hook left slots visible: %r" % offh
    assert mh.memory[0x0281] == 0, "hold hook drew STUDY over the held board"
    # E2: same build, genuine pause during a live match -> still draws
    mh2 = one_hook(unit1h, labelsh, players=2, ttl=0, match_active=1, hold_active=0)
    assert mh2.memory[0x0281] == 0x0D and mh2.memory[0x0280] == Ph.STUDY_2P_Y, \
        "DRHOLDBOARD build lost the pause draw"

    # F: first play hook of a match (MATCH_ACTIVE still 0, TTL boot-cleared): blank,
    # not a one-hook STUDY flash at round start.
    mf = one_hook(unit1, labels, players=2, ttl=0, match_active=0)
    offf = {hex(a): hex(mf.memory[a]) for a in ys if mf.memory[a] != 0xFF}
    assert not offf, "match-start hook left slots visible: %r" % offf

    print("STUDY2P pause gate: A 2P pause draw OK, B 1P OK, C flag-off identity OK, "
          "D live-play blanks (defect shape) OK, E hold blanks OK, F match-start blanks OK")


if __name__ == "__main__":
    main()
