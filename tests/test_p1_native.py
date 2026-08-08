#!/usr/bin/env python3
"""DRP1NATIVE proof on EMITTED BYTES (py65): P1 actually plays, slowly, and survives the AND.

Drives the real emitted driver + the P1-mirrored v28cs depth-1 AI against a P1-side game
model with a LIVE board (locked pills are written back, so the AI's target genuinely moves
as the bottle fills). Four claims, in descending order of how badly a regression would hurt:

 1. ★ TWO-PASS AND IDENTITY. getInputs calls the driver twice per frame and ANDs the two
    $F5 values. If the two passes ever disagree, the AND silently eats the input and P1
    "randomly ignores its own moves" -- the DRNAVDWELL failure shape, and miserable to
    diagnose after the fact. v28cs's per-pill cache is what guarantees agreement (hook 1
    searches and stores the key, hook 2 matches the key and reuses the result), so this test
    asserts the two passes are byte-identical on EVERY frame, and separately asserts the
    search really does run once per pill rather than once per hook.
 2. The AI plays: it places pills in several distinct columns, and NOT the single column a
    broken/garbage target produces. The specific regression this guards is the live one --
    an undecoded copro window publishes column 80, which drives every pill into one wall.
 3. The soft drop is stripped: $F5 never carries DOWN ($04), so P1 falls at natural gravity.
 4. handle(1) is gone and P2's copro search is untouched.

Board convention, from the emitted code (not assumed): land_col walks $0400 by +8 per row,
so offset row 0 is the TOP; the game's pill Y counts UP from the floor. Hence
offset = (15 - pillY) * 8 + pillX.

    tests/test_p1_native.py          # asserts; exit 1 on failure
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
GRAV_TH = 13
HOR_ACCEL, HOR_MAX = 0x10, 0x06
B_RIGHT, B_LEFT, B_DOWN, B_A = 0x01, 0x02, 0x04, 0x80
LR = B_LEFT | B_RIGHT
SPAWN_X, SPAWN_Y = 3, 15
LAST_COL = 7

_FLAGS = ("DRNOFREEZE", "DRHUMAN", "DRPOCKET", "DRRECOMMIT_NOFREEZE", "DRNAVDWELL",
          "DRPENDBOUND", "DRCOLDINIT", "DRSLAM_KOPEN", "DRP1WIGGLE", "DRP1NATIVE")
_seq = [0]


def build(flags):
    """Fresh emitter import under EXACTLY `flags` -> (module, unit1, labels, blobs)."""
    for k in _FLAGS:
        os.environ.pop(k, None)
    os.environ.update(flags)
    _seq[0] += 1
    name = "p1native_build_%d" % _seq[0]
    spec = importlib.util.spec_from_file_location(name, EMITTER)
    P = importlib.util.module_from_spec(spec)
    sys.modules[name] = P
    spec.loader.exec_module(P)
    unit1, labels = P.build_main(11, 1)
    blobs = P.build_p1_native() if P.P1NATIVE else None
    return P, bytes(unit1), {k: BASE + v for k, v in labels.items()}, blobs


class P1Game:
    """P1-side model with a LIVE board: locked pills are written back to $0400, so the AI is
    searching a bottle that actually fills up."""

    def __init__(self, P, unit1, labels, blobs):
        self.P, self.labels = P, labels
        self.m = MPU()
        self.m.memory[BASE:BASE + len(unit1)] = unit1
        if blobs:
            ai, lab, sw = blobs
            self.m.memory[P.P1AI_CPU:P.P1AI_CPU + len(ai)] = ai
            self.m.memory[P.P1SWAP_CPU:P.P1SWAP_CPU + len(sw)] = sw
            self.ai_lo, self.ai_hi = P.P1AI_CPU, P.P1AI_CPU + len(ai)
        else:
            self.ai_lo = self.ai_hi = -1
        for i in range(128):
            self.m.memory[0x0400 + i] = 0xFF     # P1 board: empty
            self.m.memory[0x0500 + i] = 0xFF     # P2 board
        for c in range(8):                        # a few viruses on the bottom two rows
            if c % 3 != 2:
                self.m.memory[0x0400 + 15 * 8 + c] = 0xD0 | (c % 3)
            if c % 3 == 0:
                self.m.memory[0x0400 + 14 * 8 + c] = 0xD0 | ((c + 1) % 3)
        for a, v in ((0x0301, 1), (0x0302, 2), (0x031A, 0), (0x031B, 2),
                     (0x0381, 1), (0x0382, 2), (0x039A, 0), (0x039B, 2)):
            self.m.memory[a] = v
        self.m.memory[0x04] = 1
        self.m.memory[0x0727] = 2
        self.x, self.y, self.orient = SPAWN_X, SPAWN_Y, 0
        self.held = 0
        self.hor_vel = 0
        self.frame = 0
        self.landings = []
        self.pass_mismatch = []      # frames where the two hooks disagreed  (claim 1)
        self.searches = []           # frames on which the AI actually ran   (claim 1)
        self.down_frames = []        # frames where DOWN was pressed         (claim 3)
        self.p2_gos = []
        self.p2_done, self.p2_pub = 0, (0xFF, 0xFF)
        self.p2_armed, self.p2_hooks = False, 0
        self._sync()

    def _sync(self):
        wb = self.P.W2_BASE
        self.m.memory[wb + 0x84] = self.p2_done
        self.m.memory[wb + 0x85], self.m.memory[wb + 0x86] = self.p2_pub

    def cell(self, x, y):
        return self.m.memory[0x0400 + (15 - y) * 8 + x]

    def _hook(self):
        m = self.m
        m.memory[0x0046] = 4
        m.memory[0x0305], m.memory[0x0306], m.memory[0x0325] = self.x, self.y, self.orient
        m.memory[0x0385], m.memory[0x0386], m.memory[0x03A5] = 3, 9, 1
        m.memory[0xF5] = 0
        m.memory[0x1FE], m.memory[0x1FF] = (SENT - 1) & 0xFF, (SENT - 1) >> 8
        m.sp = 0xFD
        m.pc = self.labels["main"]
        n, ran_ai = 0, False
        while m.pc != SENT and n < 400000:
            if self.ai_lo <= m.pc < self.ai_hi:
                ran_ai = True
            m.step()
            n += 1
        assert m.pc == SENT, "runaway pc=%04X frame=%d" % (m.pc, self.frame)
        if ran_ai:
            self.searches.append(self.frame)
        wb = self.P.W2_BASE
        if m.memory[wb + 0x84] != self.p2_done:
            self.p2_gos.append(self.frame)
            self.p2_done, self.p2_pub = 0, (0xFF, 0xFF)
            self.p2_armed, self.p2_hooks = True, 0
        if self.p2_armed:
            self.p2_hooks += 1
            if self.p2_hooks == 3:
                self.p2_pub = (5, 2)
            if self.p2_hooks >= 25:
                self.p2_done, self.p2_armed = 1, False
        self._sync()
        return m.memory[0xF5]

    def frame_step(self, hooks=2):
        passes = [self._hook() for _ in range(hooks)]
        if passes[0] != passes[1]:                       # ★ claim 1
            self.pass_mismatch.append((self.frame, passes[0], passes[1]))
        raw = passes[0] & passes[1]
        pressed, self.held = raw & ~self.held, raw
        if raw & B_DOWN:                                 # claim 3
            self.down_frames.append(self.frame)

        if pressed & B_A:                                # rotation
            self.orient = (self.orient + 1) & 3

        move = False                                     # fallingPill_checkXMove ($8DCF)
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

        drop = (self.frame & 1) == 0 and (self.held & 0x0F) == B_DOWN
        if not drop:
            g = (self.m.memory[0x0312] + 1) & 0xFF
            self.m.memory[0x0312] = g
            if g >= GRAV_TH:
                self.m.memory[0x0312] = 0
                drop = True
        if drop:
            wide = 0 if (self.orient & 1) else 1          # horizontal occupies x and x+1
            blocked = self.y == 0 or any(
                self.cell(self.x + dx, self.y - 1) != 0xFF for dx in range(wide + 1))
            if blocked:
                for dx in range(wide + 1):                # cement it: the board is LIVE
                    self.m.memory[0x0400 + (15 - self.y) * 8 + self.x + dx] = 0x4C | (dx % 3)
                self.landings.append((len(self.landings), self.x, self.y))
                self.x, self.y, self.orient = SPAWN_X, SPAWN_Y, 0
                self.hor_vel = self.held = 0
            else:
                self.y -= 1
        self.m.memory[0x43] = (self.m.memory[0x43] + 1) & 0xFF
        self.frame += 1


def boot(g, frames=10):
    m = g.m
    for _ in range(frames):
        m.memory[0x0046] = 8
        m.memory[0x1FE], m.memory[0x1FF] = (SENT - 1) & 0xFF, (SENT - 1) >> 8
        m.sp = 0xFD
        m.pc = g.labels["main"]
        n = 0
        while m.pc != SENT and n < 400000:
            m.step()
            n += 1
        m.memory[0x43] = (m.memory[0x43] + 1) & 0xFF


def run(flags, pills=8, max_frames=4000):
    P, u, L, blobs = build(flags)
    g = P1Game(P, u, L, blobs)
    boot(g)
    while len(g.landings) < pills and g.frame < max_frames:
        g.frame_step()
    return P, g


def main():
    FL = {"DRNOFREEZE": "1", "DRRECOMMIT_NOFREEZE": "1", "DRNAVDWELL": "0", "DRCOLDINIT": "1"}
    fail = []

    P, g = run(dict(FL, DRP1NATIVE="1"))
    cols = [c for _i, c, _y in g.landings]
    print("DRP1NATIVE=1  landing columns: %s" % cols)
    print("DRP1NATIVE=1  frames simulated: %d, pills: %d" % (g.frame, len(g.landings)))

    # ---- claim 1: the two hooks of a frame must emit an IDENTICAL byte ----
    print("DRP1NATIVE=1  frames where hook1 != hook2: %d (want 0)" % len(g.pass_mismatch))
    if g.pass_mismatch:
        fail.append("two-pass AND broken on %d frame(s), e.g. %s"
                    % (len(g.pass_mismatch), g.pass_mismatch[:3]))
    print("DRP1NATIVE=1  frames on which the AI ran: %d  (pills=%d -> want ~1 per pill)"
          % (len(g.searches), len(g.landings)))
    if not g.searches:
        fail.append("the P1 AI never executed -- the JSR target or blob placement is wrong")
    elif len(g.searches) > len(g.landings) + 2:
        fail.append("AI ran %d times for %d pills: the per-pill cache is not holding, which "
                    "is exactly what breaks the two-pass AND" % (len(g.searches), len(g.landings)))

    # ---- claim 2: it plays -- several distinct columns, not one wall ----
    if len(cols) < 6:
        fail.append("only %d pills landed in %d frames" % (len(cols), g.frame))
    elif len(set(cols)) < 2:
        fail.append("every pill landed in column %d -- that is the garbage-target signature "
                    "(open-bus col 80 drives one direction forever), not a working search"
                    % cols[0])

    # ---- claim 3: the soft drop is stripped ----
    print("DRP1NATIVE=1  frames with DOWN pressed: %d (want 0 -- the down-strip)"
          % len(g.down_frames))
    if g.down_frames:
        fail.append("DOWN pressed on %d frame(s): the soft-drop strip did not take"
                    % len(g.down_frames))

    # ---- claim 4: handle(1) dropped, P2 untouched ----
    _P2, _u2, L2, _b2 = build(dict(FL, DRP1NATIVE="1"))
    print("DRP1NATIVE=1  handle(1) emitted: %s (want False) | handle(2) emitted: %s (want True)"
          % ("h1_dz" in L2, "h2_dz" in L2))
    if "h1_dz" in L2:
        fail.append("handle(1) is still emitted under DRP1NATIVE")
    if "h2_dz" not in L2:
        fail.append("handle(2) is missing -- P2's copro search was removed by mistake")
    print("DRP1NATIVE=1  P2 search GOs: %d (want >=1)" % len(g.p2_gos))
    if not g.p2_gos:
        fail.append("P2 issued no search GO on the native cart")

    # ---- control: flag OFF must not produce this behaviour ----
    _Pc, gc = run(dict(FL), pills=8)
    ccols = [c for _i, c, _y in gc.landings]
    print("DRP1NATIVE=0  landing columns: %s (control)" % ccols)
    if ccols and cols and ccols == cols:
        fail.append("control arm lands identically -- the test cannot tell the flag apart")

    if fail:
        print("\nFAIL:")
        for f in fail:
            print("  " + f)
        return 1
    print("\nP1 NATIVE: searches once per pill, both hook passes agree, no soft drop, "
          "handle(1) dropped, P2 search intact")
    return 0


if __name__ == "__main__":
    sys.exit(main())
