#!/usr/bin/env python3
"""DRHOLDBOARD gate (task #48): keep both bottles visible past STAGE CLEAR / GAME OVER
until START, instead of the vanilla banner/dialog text.

Mechanism (see the DRHOLDBOARD flag comment in patch_cartridge_copro.py): the vanilla
routines that draw those screens (RB24F_CHECK_WIN/RB337_STAGE_CLEAR, L958A_TOP_7)
destroy the $0400/$0500 playfield RAM model itself, synchronously, with no START-gated
checkpoint beforehand -- so there is no point at which "defer the destructive write"
works (unlike STUDY's pause-blank deferral). Instead: continuously mirror both boards
into PRG-RAM during active pre-clear play, then restore + force a redraw every hook
once a match-end is detected, until the human's own START releases it (or, for a
non-HUMAN_P1 -- i.e. CvC/autonav -- cart, until DRHOLDBOARD_F frames elapse, so a nav
cart can never wedge).

Two-sided (same technique as test_studycounts_leak.py): drive a REAL sequence of hook
calls on one persistent MPU (memory carries across calls, matching consecutive NES
frames sharing the same RAM), simulate the game's OWN destructive write landing between
hooks exactly as timing analysis says it must (the driver hook only observes state
AFTER that frame's synchronous main-loop work), and assert the restore wins on the
hook immediately after arming -- not the arming hook itself (a real one-hook lag, not
a test artifact).

    tests/test_holdboard.py          # asserts; exit 1 on failure
"""
import os
import sys
import importlib.util

from py65.devices.mpu6502 import MPU

REPO = "/home/struktured/projects/dr-mario-finalboard-wt"
EMITTER = os.path.join(REPO, "patch_cartridge_copro.py")
sys.path.insert(0, REPO)

BASE = 0x8000
SENT = 0x4FF2
_FLAGS = ("DRNOFREEZE", "DRHUMAN", "DRPOCKET", "DRRECOMMIT_NOFREEZE", "DRNAVDWELL",
          "DRPENDBOUND", "DRCOLDINIT", "DRSTUDYCOUNTS", "DRSTUDY2P", "DRNAVESC",
          "DRSTALLWD", "DRHOLDBOARD", "DRHOLDBOARD_F")
_seq = [0]


def build(flags):
    for k in _FLAGS:
        os.environ.pop(k, None)
    os.environ.update(flags)
    _seq[0] += 1
    name = "hb_build_%d" % _seq[0]
    spec = importlib.util.spec_from_file_location(name, EMITTER)
    P = importlib.util.module_from_spec(spec)
    sys.modules[name] = P
    spec.loader.exec_module(P)
    unit1, labels = P.build_main(11, 1)
    return P, bytes(unit1), {k: BASE + v for k, v in labels.items()}


def run_hook(m, unit1, labels, mode, players=2, vs_cpu=1, vc1=5, vc2=5, start=0):
    """One hook invocation on an EXISTING mpu -- memory (and PRG-RAM state) persists."""
    m.memory[BASE:BASE + len(unit1)] = unit1
    m.memory[0x0046] = mode
    m.memory[0x0727] = players
    m.memory[0x04] = vs_cpu
    m.memory[0x0324] = vc1
    m.memory[0x03A4] = vc2
    m.memory[0x0316] = 11
    m.memory[0x0396] = 11
    m.memory[0x0306] = 15          # spawn row: no lock edge
    m.memory[0x0386] = 15
    m.memory[0x43] = (m.memory[0x43] + 1) & 0xFF     # a real per-hook clock tick
    m.memory[0xF5] = 0x10 if start else 0
    m.memory[0xF7] = 0
    m.memory[0x1FE], m.memory[0x1FF] = (SENT - 1) & 0xFF, (SENT - 1) >> 8
    m.sp = 0xFD
    m.pc = labels["main"]
    n = 0
    while m.pc != SENT and n < 60000:
        m.step()
        n += 1
    assert m.pc == SENT, "runaway pc=%04X" % m.pc
    return m


def board_pattern(seed):
    return bytes((seed + i * 7) & 0xFF for i in range(256))


def destroy_board():
    """What RB337_STAGE_CLEAR / R96D4_GAME_OVER actually do: fill with $FF then stamp text."""
    b = bytearray([0xFF] * 256)
    b[0x10:0x10 + 9] = b"GAME OVER"
    return bytes(b)


def scenario_a_stage_clear():
    """Inter-match: mode STAYS 4 throughout (RB24F_CHECK_WIN blocks internally -- confirmed
    from the disassembly, it never touches L46_TOP_STATE until AFTER its own wait-loop)."""
    human = {"DRHUMAN": "1", "DRPOCKET": "1", "DRNOFREEZE": "1", "DRHOLDBOARD": "1"}
    P, unit1, labels = build(human)
    assert P.HOLDBOARD, "HOLDBOARD not active"

    m = MPU()
    snap1, snap2 = board_pattern(0x11), board_pattern(0x81)
    m.memory[0x0400:0x0500] = snap1
    m.memory[0x0500:0x0600] = snap2
    run_hook(m, unit1, labels, mode=4, vc1=5, vc2=5)      # active play -> mirrors into HOLD_BUF*
    assert bytes(m.memory[P.HOLD_BUF1:P.HOLD_BUF1 + 256]) == snap1, "mirror (P1) not captured"
    assert bytes(m.memory[P.HOLD_BUF2:P.HOLD_BUF2 + 256]) == snap2, "mirror (P2) not captured"

    # The frame virus hits 0: the REAL RB337_STAGE_CLEAR has ALREADY run synchronously by the
    # time our hook's NMI-driven invocation observes it (confirmed from the disassembly: no
    # $F5/$F7 check precedes the destructive write) -- simulate that landing BEFORE this hook.
    garbage = destroy_board()
    m.memory[0x0400:0x0500] = garbage
    m.memory[0x0500:0x0600] = garbage
    run_hook(m, unit1, labels, mode=4, vc1=0, vc2=5)      # fc_clear ARMS here
    assert m.memory[P.HOLD_ACTIVE] == 1, "did not arm on the virus==0 hook"
    # ONE HOOK OF LAG IS EXPECTED (not a bug): the arm happens mid-hook, after the top-of-main
    # restore check already ran and found HOLD_ACTIVE==0 that same hook.
    assert bytes(m.memory[0x0400:0x0500]) == garbage, (
        "restored on the SAME hook that armed -- test's timing model (or the code) is wrong; "
        "the real destructive write always lands before our hook can react to it")

    run_hook(m, unit1, labels, mode=4, vc1=0, vc2=5)      # next hook: restore should win now
    assert bytes(m.memory[0x0400:0x0500]) == snap1, "P1 board not restored"
    assert bytes(m.memory[0x0500:0x0600]) == snap2, "P2 board not restored"
    assert m.memory[0x0300] == 0x0F and m.memory[0x0380] == 0x0F, (
        "redraw not re-triggered (L0300/L0380_UPDATE_ROW)")
    print("PASS A: STAGE CLEAR destructive write reproduced 1 hook, then restored + redraw-triggered")

    # human presses START -> release
    run_hook(m, unit1, labels, mode=4, vc1=0, vc2=5, start=1)
    assert m.memory[P.HOLD_ACTIVE] == 0, "did not release on START"
    assert m.memory[P.MATCH_ACTIVE] == 0, "MATCH_ACTIVE not cleared on release"
    print("PASS A2: human START releases the hold (HOLD_ACTIVE + MATCH_ACTIVE cleared)")


def scenario_b_game_over():
    """Set-final: a topout leaves virus counts nonzero (fc_clear never fires) -- mode instead
    transitions 4 -> 5 -> 7 (TOP_5 then its own blocking TOP_7 GAME OVER wait, confirmed from
    the disassembly). Both pages get destroyed (RB894_FILL_PAGES fills 4 AND 5, unlike the
    single-page STAGE CLEAR case)."""
    human = {"DRHUMAN": "1", "DRPOCKET": "1", "DRNOFREEZE": "1", "DRHOLDBOARD": "1"}
    P, unit1, labels = build(human)

    m = MPU()
    snap1, snap2 = board_pattern(0x22), board_pattern(0x92)
    m.memory[0x0400:0x0500] = snap1
    m.memory[0x0500:0x0600] = snap2
    run_hook(m, unit1, labels, mode=4, vc1=7, vc2=3)      # active play, virus counts still up
    assert bytes(m.memory[P.HOLD_BUF1:P.HOLD_BUF1 + 256]) == snap1

    garbage = destroy_board()
    m.memory[0x0400:0x0500] = garbage
    m.memory[0x0500:0x0600] = garbage
    run_hook(m, unit1, labels, mode=5, vc1=7, vc2=3)      # not_play ARMS here (MATCH_ACTIVE still set)
    assert m.memory[P.HOLD_ACTIVE] == 1, "did not arm on the mode!=4 hook (topout path)"

    m.memory[0x0400:0x0500] = garbage                     # TOP_7's OWN fill lands on the next hook too
    m.memory[0x0500:0x0600] = garbage
    run_hook(m, unit1, labels, mode=7, vc1=7, vc2=3)      # TOP_7 (GAME OVER) -- restore should win
    assert bytes(m.memory[0x0400:0x0500]) == snap1, "P1 board not restored under GAME OVER"
    assert bytes(m.memory[0x0500:0x0600]) == snap2, "P2 board not restored under GAME OVER"
    print("PASS B: topout/GAME OVER (mode 5->7) destructive write also gets overwritten back")

    run_hook(m, unit1, labels, mode=7, vc1=7, vc2=3, start=1)
    assert m.memory[P.HOLD_ACTIVE] == 0, "did not release on START (GAME OVER path)"
    print("PASS B2: human START releases the hold on the GAME OVER path too")


def scenario_c_cvc_autorelease():
    """Non-HUMAN_P1 (CvC/autonav) cart: the hold must self-release after DRHOLDBOARD_F frames
    even with no START ever seen, so a headless nav cart can never wedge."""
    cvc = {"DRHOLDBOARD": "1", "DRHOLDBOARD_F": "20", "DRNOFREEZE": "1"}
    P, unit1, labels = build(cvc)
    assert not P.HUMAN_P1, "this scenario requires a non-HUMAN_P1 (CvC) build"

    m = MPU()
    m.memory[0x0400:0x0500] = board_pattern(0x33)
    m.memory[0x0500:0x0600] = board_pattern(0x93)
    run_hook(m, unit1, labels, mode=4, vc1=5, vc2=5)
    run_hook(m, unit1, labels, mode=5, vc1=5, vc2=5)      # arm (no START ever injected in this test)
    assert m.memory[P.HOLD_ACTIVE] == 1

    released_at = None
    for i in range(40):
        run_hook(m, unit1, labels, mode=7, vc1=5, vc2=5, start=0)
        if m.memory[P.HOLD_ACTIVE] == 0:
            released_at = i
            break
    assert released_at is not None, "CvC hold never auto-released -- nav cart would wedge"
    assert released_at < 25, "auto-release took too long relative to DRHOLDBOARD_F=20: %d hooks" % released_at
    print("PASS C: CvC hold auto-released after %d hooks (DRHOLDBOARD_F=20, no START)" % released_at)


def scenario_d_flag_off_identity():
    human = {"DRHUMAN": "1", "DRPOCKET": "1", "DRNOFREEZE": "1", "DRSTUDYCOUNTS": "1"}
    _, off1, _ = build(dict(human, DRHOLDBOARD="0"))
    _, off2, _ = build(dict(human, DRHOLDBOARD="0"))
    assert off1 == off2, "flag-off emission not deterministic"
    _, on1, _ = build(dict(human, DRHOLDBOARD="1"))
    assert on1 != off1, "DRHOLDBOARD=1 changed nothing"
    print("PASS D: DRHOLDBOARD=0 emission deterministic (%d bytes), differs from flag-on" % len(off1))


def main():
    scenario_a_stage_clear()
    scenario_b_game_over()
    scenario_c_cvc_autorelease()
    scenario_d_flag_off_identity()
    print("\n==== ALL CHECKS PASSED (DRHOLDBOARD verified two-sided) ====")


if __name__ == "__main__":
    main()
