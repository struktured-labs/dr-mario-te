#!/usr/bin/env python3
"""DRP1WIGGLE proof on EMITTED BYTES (py65): P1's pills alternate LEFT and RIGHT.

The P1 side of a CvC cart is a dud -- it stacks at the spawn column and tops out with
every virus alive. DRP1WIGGLE gives it a watchable dummy policy: hold one direction for
the whole of each pill's descent, alternating per pill. This test drives the REAL emitted
driver bytes against a P1-side game model and asserts the landing columns actually
alternate around the spawn column.

★ THE MODEL IS THE GAME'S OWN CODE, not a convenience. Two routines matter and both are
transcribed from the disassembly (tmp/refs/dr-mario-disassembly) rather than guessed --
a looser model would "pass" for a driver that cannot move a pill on real silicon:

  getInputs / _pressedVsHeld  [prg/drmario_prg_general.asm:352]
      The 0x37CF driver hook fires at the tail of addExpansionCTRL, which getInputs calls
      TWICE, and the pad is re-latched between the two calls -- so the value the game acts
      on is (pass0 & pass1) of whatever the driver leaves in $F5. That AND is what killed
      the DRNAVDWELL nav (a 1-hook press never survives it), so it is modelled exactly.
      From that raw value the game derives BOTH bytes:  pressed($F5) = raw & ~held_prev,
      held($F7) = raw.  The driver therefore never writes $F7 itself.

  fallingPill_checkXMove      [prg/drmario_prg_game_logic.asm:290]
      pressed & (L|R) -> move NOW (horVelocity = 0); else held & (L|R) -> DAS: 16 frames
      to the first repeat, 6 per repeat after. ★ The direction itself is read from HELD,
      not from pressed -- an injection that sets only the pressed byte moves NOTHING. This
      is the whole reason the wiggle writes the raw latch every hook.

Constants are the NTSC ones (hor_accel_speed $10 / hor_max_speed $06, ver_EU=0), matching
the US Rev0 base this cart is built from.

    tests/test_p1_wiggle.py          # asserts; exit 1 on failure
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
GRAV_TH = 13            # L11 MED: frames per gravity row (same figure the other harnesses use)
HOR_ACCEL, HOR_MAX = 0x10, 0x06
B_RIGHT, B_LEFT, B_DOWN = 0x01, 0x02, 0x04
LR = B_LEFT | B_RIGHT
SPAWN_X, SPAWN_Y = 3, 15
LAST_COL = 7

_FLAGS = ("DRNOFREEZE", "DRHUMAN", "DRPOCKET", "DRRECOMMIT_NOFREEZE", "DRNAVDWELL",
          "DRPENDBOUND", "DRCOLDINIT", "DRSLAM_KOPEN", "DRP1WIGGLE")
_seq = [0]


def build(flags):
    """Fresh emitter import under EXACTLY `flags` -> (module, unit1 bytes, labels)."""
    for k in _FLAGS:
        os.environ.pop(k, None)
    os.environ.update(flags)
    _seq[0] += 1
    name = "p1wiggle_build_%d" % _seq[0]
    spec = importlib.util.spec_from_file_location(name, EMITTER)
    P = importlib.util.module_from_spec(spec)
    sys.modules[name] = P
    spec.loader.exec_module(P)
    unit1, labels = P.build_main(11, 1)
    return P, bytes(unit1), {k: BASE + v for k, v in labels.items()}


class P1Game:
    """Play-mode model of PLAYER ONE: $0305/$0306/$0325 pose, $0312 gravity counter (the
    driver pins by zeroing it), $0400 board, $F5/$F7 inputs, $5000 copro mailbox."""

    def __init__(self, P, unit1, labels, p1_done_after=25, p2_done_after=25):
        self.P, self.labels = P, labels
        self.m = MPU()
        self.m.memory[BASE:BASE + len(unit1)] = unit1
        for i in range(128):                       # both boards empty (floor = row 0)
            self.m.memory[0x0400 + i] = 0xFF
            self.m.memory[0x0500 + i] = 0xFF
        # nB = 2 for each player: the {L}_start GO write carries A = nB & $0F, so it must
        # differ from both DONE-flag values (0/1) for change-detection to see the GO.
        for a, v in ((0x0301, 1), (0x0302, 2), (0x031A, 0), (0x031B, 2),
                     (0x0381, 1), (0x0382, 2), (0x039A, 0), (0x039B, 2)):
            self.m.memory[a] = v
        self.m.memory[0x04] = 1
        self.m.memory[0x0727] = 2
        self.x, self.y, self.orient = SPAWN_X, SPAWN_Y, 0
        self.held = 0
        self.hor_vel = 0
        self.frame = 0
        self.landings = []                          # (pill index, landing column)
        self.mbox = {}
        for wb, after in ((0x5000, p1_done_after), (P.W2_BASE, p2_done_after)):
            self.mbox[wb] = dict(done=0, pub=(0xFF, 0xFF), armed=False, hooks=0,
                                 after=after, gos=[])
        self._sync()

    def _sync(self):
        for wb, s in self.mbox.items():
            self.m.memory[wb + 0x84] = s["done"]
            self.m.memory[wb + 0x85], self.m.memory[wb + 0x86] = s["pub"]

    def _hook(self):
        """One driver invocation; returns the raw byte it left in $F5."""
        m = self.m
        m.memory[0x0046] = 4
        m.memory[0x0305], m.memory[0x0306], m.memory[0x0325] = self.x, self.y, self.orient
        # P2 parked on a legal pose so its own driver path runs without tripping anything
        m.memory[0x0385], m.memory[0x0386], m.memory[0x03A5] = 3, 9, 1
        m.memory[0xF5] = 0                          # the pad re-latches between the two passes
        m.memory[0x1FE], m.memory[0x1FF] = (SENT - 1) & 0xFF, (SENT - 1) >> 8
        m.sp = 0xFD
        m.pc = self.labels["main"]
        n = 0
        while m.pc != SENT and n < 60000:
            m.step()
            n += 1
        assert m.pc == SENT, "runaway pc=%04X frame=%d" % (m.pc, self.frame)
        for wb, s in self.mbox.items():
            if m.memory[wb + 0x84] != s["done"]:    # driver wrote +$84 = GO
                s.update(done=0, pub=(0xFF, 0xFF), armed=True, hooks=0)
                s["gos"].append(self.frame)
            if s["armed"]:
                s["hooks"] += 1
                if s["hooks"] == 3:
                    s["pub"] = (5, 2)
                if s["hooks"] >= s["after"]:
                    s.update(done=1, armed=False)
        self._sync()
        return m.memory[0xF5]

    def frame_step(self, hooks=5):
        passes = []
        for h in range(hooks):
            v = self._hook()
            if h < 2:
                passes.append(v)                    # getInputs reads the pad exactly twice
        raw = passes[0] & passes[1]
        pressed, self.held = raw & ~self.held, raw

        # ---- fallingPill_checkXMove ($8DCF), transcribed ----
        move = False
        if pressed & LR:
            self.hor_vel = 0
            move = True
        elif self.held & LR:
            self.hor_vel += 1
            if self.hor_vel >= HOR_ACCEL:
                self.hor_vel = HOR_ACCEL - HOR_MAX
                move = True
        if move:
            if self.held & B_RIGHT and self.x != (self.orient & 1) + LAST_COL - 1:
                self.x += 1
            if self.held & B_LEFT and self.x > 0:
                self.x -= 1

        # ---- fallingPill_checkYMove ($8D80): fast drop needs ONLY down on the d-pad ----
        drop = (self.frame & 1) == 0 and (self.held & 0x0F) == B_DOWN
        if not drop:
            g = (self.m.memory[0x0312] + 1) & 0xFF  # driver pins by zeroing it every hook
            self.m.memory[0x0312] = g
            if g >= GRAV_TH:
                self.m.memory[0x0312] = 0
                drop = True
        if drop:
            if self.y == 0:
                self.landings.append((len(self.landings), self.x))
                self.x, self.y, self.orient = SPAWN_X, SPAWN_Y, 0
                self.hor_vel = 0
            else:
                self.y -= 1
        self.m.memory[0x43] = (self.m.memory[0x43] + 1) & 0xFF
        self.frame += 1


def boot(g, frames=10):
    """Ten mode-8 hooks so the power-on init + per-boot re-arm run before play."""
    m = g.m
    for fr in range(frames):
        m.memory[0x0046] = 8
        m.memory[0x1FE], m.memory[0x1FF] = (SENT - 1) & 0xFF, (SENT - 1) >> 8
        m.sp = 0xFD
        m.pc = g.labels["main"]
        n = 0
        while m.pc != SENT and n < 60000:
            m.step()
            n += 1
        m.memory[0x43] = (m.memory[0x43] + 1) & 0xFF


def run(flags, pills=6, max_frames=4000):
    P, u, L = build(flags)
    g = P1Game(P, u, L)
    boot(g)
    while len(g.landings) < pills and g.frame < max_frames:
        g.frame_step()
    return P, g


def main():
    FL = {"DRNOFREEZE": "1", "DRRECOMMIT_NOFREEZE": "1", "DRNAVDWELL": "0",
          "DRCOLDINIT": "1"}
    fail = []

    P, g = run(dict(FL, DRP1WIGGLE="1"))
    cols = [c for _i, c in g.landings]
    print("DRP1WIGGLE=1  landing columns (spawn=%d): %s" % (SPAWN_X, cols))
    if len(cols) < 6:
        fail.append("only %d pills landed in %d frames" % (len(cols), g.frame))
    else:
        # The headline claim: consecutive pills land on OPPOSITE sides of the spawn column.
        # Pill 1 goes RIGHT because the first spawn edge toggles WIG_DIR off its 0 seed
        # before act_p1 reads it -- arbitrary, but pinned so a silent flip is caught.
        for i, c in enumerate(cols):
            want = "right" if i % 2 == 0 else "left"
            got = "left" if c < SPAWN_X else ("right" if c > SPAWN_X else "centre")
            if got != want:
                fail.append("pill %d landed %s (col %d), expected %s" % (i, got, c, want))
        if len(set(cols)) < 2:
            fail.append("landing columns never alternate: %s" % cols)

    # the hold must last the WHOLE descent, not just the spawn frame: with a held
    # direction the capsule DASes all the way to the wall (col 0 / col 6 for a
    # horizontal pill), which a one-shot press could never reach.
    if len(cols) >= 6 and (set(cols[0::2]) != {6} or set(cols[1::2]) != {0}):
        fail.append("held direction did not carry to the wall: %s "
                    "(expected alternating 6 / 0)" % cols)

    # $F7 must stay untouched -- the game derives held from the raw latch itself, and
    # writing it would mark the button already-held and kill the pressed edge.
    P2, u2, L2 = build(dict(FL, DRP1WIGGLE="1"))
    gg = P1Game(P2, u2, L2)
    boot(gg)
    f7_dirty = 0
    for _ in range(120):
        gg.m.memory[0xF7] = 0xEE
        gg.frame_step()
        if gg.m.memory[0xF7] != 0xEE:
            f7_dirty += 1
    print("DRP1WIGGLE=1  frames in which the driver wrote $F7: %d (want 0)" % f7_dirty)
    if f7_dirty:
        fail.append("driver wrote $F7 on %d frames" % f7_dirty)

    # control: flag OFF must NOT produce the alternating spread (it is the dud we are fixing)
    _Pc, gc = run(dict(FL), pills=6)
    ccols = [c for _i, c in gc.landings]
    print("DRP1WIGGLE=0  landing columns (spawn=%d): %s" % (SPAWN_X, ccols))
    if ccols and set(ccols[0::2]) == {6} and set(ccols[1::2]) == {0}:
        fail.append("control arm also alternates 6/0 -- the test cannot tell the flag apart")

    # P2's copro must still be searching on the wiggle cart (P1 code must not starve it)
    gos2 = len(g.mbox[P.W2_BASE]["gos"])
    print("DRP1WIGGLE=1  P2 search GOs in %d frames: %d" % (g.frame, gos2))
    if gos2 < 1:
        fail.append("P2 issued no search GO on the wiggle cart")

    if fail:
        print("\nFAIL:")
        for f in fail:
            print("  " + f)
        return 1
    print("\nP1 WIGGLE: pills alternate LEFT/RIGHT for the whole descent, $F7 untouched, "
          "P2 search intact")
    return 0


if __name__ == "__main__":
    sys.exit(main())
