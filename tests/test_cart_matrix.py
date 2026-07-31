#!/usr/bin/env python3
"""CART-CLASS FLAG-MATRIX ship gate (host-side, py65 on emitted bytes, no silicon).

Builds every shipping cart class from THIS repo's emitter and asserts class-correct
behavior. This is the anti-recurrence gate for the class-asymmetric defect family
found 2026-07-30: P0.2's class-blind gravity pin, P0.3's NO_FREEZE-gated cold init,
P0.4's human button theft, P0.5's class-wide RECOMMIT exclusion, and the NAVDWELL
default-on title hang (which invalidated an A/B by hanging BOTH arms at the title).

Checks per class
  build     emitter builds + every relative branch lands exactly on its label
  struct    RECOMMIT emitted iff the class expects it; handle(1) iff AI-P1;
            W2_BASE per platform
  human     human classes NEVER write $F5/$F7 in modes 0/1/4/7; AI classes DO inject
  nav       AI classes reach a REGISTERED START edge at the title under the
            two-pass AND read model ($F5 reloaded per pass) -- a press narrower
            than the window (the NAVDWELL failure shape) cannot pass this
  play      first pill gets a search GO within 10 frames of clean-boot play
  defect_*  P0.2 pin / P0.3 rematch / P2.2 relaunch with the fix flags OFF:
            expected-fail (defect present is the DOCUMENTED default-off behavior)
  fixed_*   same scenarios with DRPENDBOUND=1 / DRCOLDINIT=1: must pass

Both arms build from the SAME emitter with the flags set EXPLICITLY (never from
defaults), so flipping a flag default later cannot silently invert a row; the
current defaults are printed for visibility.

Two wrong expectations this matrix caught while being built (kept as a warning):
  - "freeze class" accidentally built as NO_FREEZE because the harness baked
    DRNOFREEZE=1 into its baseline env -- class flags must be explicit;
  - the P0.3 probe originally watched 60 frames, long enough for pill 2's
    LEGITIMATE search to mask pill 1's blind drop -- the healthy criterion is
    "a GO arrives BEFORE the first post-rematch lock", not "a GO arrives".
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
# every flag any class/arm sets: popped before each build so nothing leaks between builds
_FLAGS = ("DRNOFREEZE", "DRHUMAN", "DRPOCKET", "DRRECOMMIT_NOFREEZE", "DRNAVDWELL",
          "DRPENDBOUND", "DRCOLDINIT", "DRSLAM_KOPEN")

CLASSES = [
    ("ab_control",   {"DRNOFREEZE": "1"},
     dict(recommit=False, human=False, wb=0x5200)),
    ("mister_play",  {"DRNOFREEZE": "1", "DRRECOMMIT_NOFREEZE": "1"},
     dict(recommit=True, human=False, wb=0x5200)),
    ("mister_human", {"DRHUMAN": "1", "DRNOFREEZE": "1", "DRRECOMMIT_NOFREEZE": "1"},
     dict(recommit=True, human=True, wb=0x5200)),
    ("pocket_human", {"DRHUMAN": "1", "DRNAVDWELL": "0", "DRNOFREEZE": "1",
                      "DRPOCKET": "1", "DRRECOMMIT_NOFREEZE": "1"},
     dict(recommit=True, human=True, wb=0x5000)),
    ("freeze_legacy", {"DRNOFREEZE": "0"},
     dict(recommit=True, human=False, wb=0x5200)),
]

_seq = [0]


def build(flags, audit=False):
    """Fresh emitter import under EXACTLY `flags` -> (module, unit1, labels[, badbranches])."""
    for k in _FLAGS:
        os.environ.pop(k, None)
    os.environ.update(flags)
    import patch_vs_cpu
    cap = {}
    orig = patch_vs_cpu.Asm6502.assemble
    if audit:
        def spy(self):
            r = orig(self)
            cap.update(fix=list(self.fixups), labels=dict(self.labels), code=r)
            return r
        patch_vs_cpu.Asm6502.assemble = spy
    try:
        _seq[0] += 1
        name = "cartmatrix_build_%d" % _seq[0]
        spec = importlib.util.spec_from_file_location(name, EMITTER)
        P = importlib.util.module_from_spec(spec)
        sys.modules[name] = P
        spec.loader.exec_module(P)
        unit1, labels = P.build_main(11, 1)
    finally:
        patch_vs_cpu.Asm6502.assemble = orig
    L = {k: BASE + v for k, v in labels.items()}
    if not audit:
        return P, bytes(unit1), L
    bad = 0
    for pos, kind, target in cap["fix"]:
        if kind != "rel":
            continue
        enc = cap["code"][pos]
        enc = enc - 256 if enc >= 128 else enc
        if pos + 1 + enc != cap["labels"][target]:
            bad += 1
    return P, bytes(unit1), L, bad


class Game:
    """Minimal play-mode game model around the driver bytes: gravity counter the
    driver can pin, lock/spawn, and a harness-owned copro mailbox (GO detected by
    value change -- the GO write carries A = nB & 0x0F, so nB is set to 2, distinct
    from both DONE-flag values)."""

    def __init__(self, P, unit1, labels, done_after_hooks=10 ** 9, prgram_garbage=False):
        self.P, self.labels = P, labels
        self.m = MPU()
        self.m.memory[BASE:BASE + len(unit1)] = unit1
        if prgram_garbage:
            for a in range(0x6000, 0x6200):
                self.m.memory[a] = 0xD3
        for i in range(128):
            self.m.memory[0x0500 + i] = 0xFF
        for c in (0, 2, 5, 7):
            self.m.memory[0x0500 + 15 * 8 + c] = 0xD0 | (c % 3)
        for a, v in ((0x0381, 1), (0x0382, 2), (0x039A, 0), (0x039B, 2)):
            self.m.memory[a] = v
        self.m.memory[0x04] = 1
        self.m.memory[0x0727] = 2
        self.y, self.x, self.orient = 15, 3, 0
        self.frame = 0
        self.done_after = done_after_hooks
        self.go_hooks = []
        self.search_hooks = 0
        self.armed_live = False
        self.hook_n = 0
        self.locks = []
        self.WB = P.W2_BASE
        self.mbox_done = 0
        self.pub = (0xFF, 0xFF)
        self._sync_mbox()

    def _sync_mbox(self):
        self.m.memory[self.WB + 0x84] = self.mbox_done
        self.m.memory[self.WB + 0x85], self.m.memory[self.WB + 0x86] = self.pub

    def hook(self, mode):
        m = self.m
        m.memory[0x0046] = mode
        m.memory[0x0385], m.memory[0x0386] = self.x, self.y
        m.memory[0x03A5] = self.orient
        m.memory[0xF6] = 0
        m.memory[0x1FE], m.memory[0x1FF] = (SENT - 1) & 0xFF, (SENT - 1) >> 8
        m.sp = 0xFD
        m.pc = self.labels["main"]
        n = 0
        while m.pc != SENT and n < 60000:
            m.step()
            n += 1
        assert m.pc == SENT, "runaway pc=%04X frame=%d" % (m.pc, self.frame)
        if m.memory[self.WB + 0x84] != self.mbox_done:      # driver wrote +0x84: GO
            self.go_hooks.append(self.hook_n)
            self.armed_live = True
            self.search_hooks = 0
            self.mbox_done = 0
            self.pub = (0xFF, 0xFF)
        if self.armed_live:
            self.search_hooks += 1
            if self.search_hooks == 3:
                self.pub = (5, 2)
            if self.search_hooks >= self.done_after:
                self.mbox_done = 1
                self.armed_live = False
        self._sync_mbox()
        self.hook_n += 1
        return m.memory[0xF6]

    def frame_step(self, mode, hooks=5):
        press = 0
        for _ in range(hooks):
            press |= self.hook(mode)
        self.m.memory[0x43] = (self.m.memory[0x43] + 1) & 0xFF
        self.frame += 1
        if mode != 4:
            return press
        last = self.m.memory[0xF6]
        if last & 0x80:
            self.orient = (self.orient + 1) & 3
        if last & 0x01 and self.x < 7:
            self.x += 1
        if last & 0x02 and self.x > 0:
            self.x -= 1
        drop = False
        if last & 0x04:
            drop = True
        else:
            g = self.m.memory[0x0392] + 1
            self.m.memory[0x0392] = g
            if g >= GRAV_TH:
                self.m.memory[0x0392] = 0
                drop = True
        if drop:
            floor = 2 if self.m.memory[0x0500 + 15 * 8 + self.x] != 0xFF else 1
            if self.y - 1 <= floor:
                self.locks.append((self.frame, self.x, self.y, self.orient))
                self.y, self.x, self.orient = 15, 3, 0
            else:
                self.y -= 1
        return press


def boot(g):
    for _ in range(10):
        g.frame_step(8)


# ---------------------------------------------------------------- checks
def title_nav(P, u, L, frames=520):
    """Two-pass AND read model at the title -> (start_edges, driver $F5/$F7 writes)."""
    m = MPU()
    m.memory[BASE:BASE + len(u)] = u
    held = 0
    starts = 0
    f5w = 0
    for fr in range(frames):
        m.memory[0x43] = fr & 0xFF
        m.memory[0x0727] = 1
        m.memory[0x04] = 0
        m.memory[0x0046] = 8 if fr < 10 else 0
        passes = []
        for h in range(5):
            if h < 2:
                m.memory[0xF5] = 0
            m.memory[0xF7] = 0xEE
            m.memory[0x1FE], m.memory[0x1FF] = (SENT - 1) & 0xFF, (SENT - 1) >> 8
            m.sp = 0xFD
            m.pc = L["main"]
            n = 0
            while m.pc != SENT and n < 60000:
                m.step()
                n += 1
            assert m.pc == SENT
            if m.memory[0xF5] != 0 or m.memory[0xF7] != 0xEE:
                f5w += 1
            if h < 2:
                passes.append(m.memory[0xF5])
        raw = passes[0] & passes[1]
        if raw & 0x10 & ~held:
            starts += 1
        held = raw
    return starts, f5w


def human_play_probe(P, u, L):
    """Modes 0/1/4/7 with active play state: count driver writes to $F5/$F7."""
    m = MPU()
    m.memory[BASE:BASE + len(u)] = u
    w = 0
    for mode in (0, 1, 4, 7, 4, 1, 0, 7):
        for hk in range(40):
            m.memory[0x0046] = mode
            m.memory[0x43] = hk
            m.memory[0x04] = 1
            m.memory[0x0727] = 2
            m.memory[0x0385], m.memory[0x0386], m.memory[0x03A5] = 3, 9, 1
            m.memory[0xF5] = 0
            m.memory[0xF7] = 0
            m.memory[0x1FE], m.memory[0x1FF] = (SENT - 1) & 0xFF, (SENT - 1) >> 8
            m.sp = 0xFD
            m.pc = L["main"]
            n = 0
            while m.pc != SENT and n < 60000:
                m.step()
                n += 1
            if m.memory[0xF5] != 0 or m.memory[0xF7] != 0:
                w += 1
    return w


def play_first_go(P, u, L):
    g = Game(P, u, L, done_after_hooks=25)
    boot(g)
    for _ in range(12):
        g.frame_step(4)
        if g.go_hooks:
            return g.frame - 10
    return None


def defect_p03_rematch(P, u, L):
    """True = healthy: rematch pill 1 gets a search GO BEFORE its first lock."""
    g = Game(P, u, L, done_after_hooks=25)
    boot(g)
    for _ in range(400):
        g.frame_step(4)
    for a in (P.PEND2, P.DELAY2, P.ARMED2):     # game over by topout (see docstring)
        g.m.memory[a] = 0
    g.m.memory[P.LASTY2] = 15
    g.armed_live = False
    g.y, g.x, g.orient = 15, 3, 0
    for _ in range(30):
        g.frame_step(7)
    for _ in range(30):
        g.frame_step(1)
    gos = len(g.go_hooks)
    locks = len(g.locks)
    for _ in range(120):
        g.frame_step(4)
        if len(g.locks) > locks:
            break
    return len(g.go_hooks) > gos


def defect_p02_pin(P, u, L):
    """True = healthy: a pill queued behind a stale-ARMED search still moves."""
    g = Game(P, u, L, done_after_hooks=10 ** 9)
    boot(g)
    for _ in range(400):
        g.frame_step(4)
    y0, l0 = g.y, len(g.locks)
    for _ in range(200):
        g.frame_step(4)
    return g.y != y0 or len(g.locks) != l0


def defect_p22_relaunch(P, u, L):
    """True = healthy: first pill after a stale-ARMED2 soft relaunch searches promptly."""
    g = Game(P, u, L, done_after_hooks=10 ** 9)
    boot(g)
    for _ in range(40):
        g.frame_step(4)
    if g.m.memory[P.ARMED2] != 1:
        return True
    g.m.memory[P.WDOGH2] = 54
    prgram = bytes(g.m.memory[0x6000:0x6200])
    g2 = Game(P, u, L, done_after_hooks=25)
    g2.m.memory[0x6000:0x6200] = prgram
    g2.mbox_done = 0
    g2.pub = (0xFF, 0xFF)
    g2._sync_mbox()
    boot(g2)
    for _ in range(12):
        g2.frame_step(4)
        if g2.go_hooks:
            return True
    return False


# ---------------------------------------------------------------- matrix
def main():
    results = {}
    unexpected = []

    def record(check, cls, ok, expect_fail=False):
        if expect_fail:
            cell = "XFAIL(defect)" if not ok else "UNEXPECTED-PASS"
            bad = ok
        else:
            cell = "PASS" if ok else "FAIL"
            bad = not ok
        results[(check, cls)] = cell
        if bad:
            unexpected.append((check, cls, cell))

    OFF = {"DRPENDBOUND": "0", "DRCOLDINIT": "0"}   # explicit: immune to default flips
    ON = {"DRPENDBOUND": "1", "DRCOLDINIT": "1"}

    for cls, flags, exp in CLASSES:
        P, u, L, badbr = build(dict(flags, **OFF), audit=True)
        record("build", cls, badbr == 0)
        record("struct", cls,
               ("h2_rcdone" in L) == exp["recommit"]
               and ("h1_dz" in L) == (not exp["human"])
               and P.W2_BASE == exp["wb"])
        starts, f5w = title_nav(P, u, L)
        if exp["human"]:
            record("human", cls, human_play_probe(P, u, L) == 0 and f5w == 0)
            record("nav", cls, starts == 0)
        else:
            record("human", cls, f5w > 0)
            record("nav", cls, starts > 0)
        go = play_first_go(P, u, L)
        record("play", cls, go is not None and go <= 10)
        if cls in ("ab_control", "mister_human", "freeze_legacy"):
            record("defect_p0.3", cls, defect_p03_rematch(P, u, L), expect_fail=True)
            record("defect_p2.2", cls, defect_p22_relaunch(P, u, L), expect_fail=True)
            if cls != "freeze_legacy":      # freeze class pins-while-ARMED by CONTRACT
                record("defect_p0.2", cls, defect_p02_pin(P, u, L), expect_fail=True)
            Pf, uf, Lf = build(dict(flags, **ON))
            record("fixed_p0.3", cls, defect_p03_rematch(Pf, uf, Lf))
            record("fixed_p2.2", cls, defect_p22_relaunch(Pf, uf, Lf))
            if cls != "freeze_legacy":
                record("fixed_p0.2", cls, defect_p02_pin(Pf, uf, Lf))

    P0, _, _ = build(dict(CLASSES[0][1]))
    print("flag defaults on this emitter: DRPENDBOUND=%s DRCOLDINIT=%s"
          % (int(getattr(P0, "PENDBOUND", False)), int(getattr(P0, "COLDINIT", False))))
    checks = []
    for (c, _cls) in results:
        if c not in checks:
            checks.append(c)
    names = [c for c, _f, _e in CLASSES]
    print("%-14s" % "" + "".join("%-16s" % n for n in names))
    for ch in checks:
        print("%-14s" % ch + "".join("%-16s" % results.get((ch, n), "-") for n in names))
    if unexpected:
        print("\nUNEXPECTED results:")
        for ch, cls, cell in unexpected:
            print("  %s / %s -> %s" % (ch, cls, cell))
        return 1
    print("\nCART-CLASS MATRIX: all cells as expected "
          "(defect rows are the documented flags-OFF behavior; fixed rows prove the flags)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
