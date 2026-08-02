#!/usr/bin/env python3
"""DRSTALLWD gate: the play-mode P2 stall watchdog (task #40 follow-up).

Freeze #4 (2026-08-02, experiments/freeze_20260801/FREEZE4_ROOTCAUSE.md) showed the P0.2
"lock-while-armed" pin -- P2's search doesn't DONE before its pill locks, so the NEXT capsule's
spawn edge finds ARMED2 still set, handle(2) never reaches `_start`, and `freeze_pending` pins
GRAV_P2 for as long as the stale search remains in flight. NAVESC (task #38) cannot cure this:
its START injection only toggles pause during mode 4, which does not change $0046, so the
underlying wedge (and NAVESC's own watchdog!) keeps ticking right through the pause.

DRSTALLWD watches P2's OWN game-owned pose ($0385/$0386/$03A5), not the driver's own
PEND2/ARMED2/DELAY2 scratch, and fires a SCOPED reset (ARMED2/WDOG2/WDOGH2=0, PEND2=1, DELAY2=0)
that re-arms handle(2)'s `_start` gate without discarding ROT_DONE2/STABLE_CT2/TGT_C2/TGT_O2.

Per the house rule this gate REPRODUCES THE DEFECT rather than only asserting the guard exists:

  A  isolated trigger: a WEDGED quintet (ARMED2=1, stale WDOG2/WDOGH2) + static pose in mode 4
     with viruses present -> fires at ~STALLWD_N hooks, and ROT_DONE2/STABLE_CT2/TGT_C2/TGT_O2
     are BYTE-IDENTICAL before and after (the reset is scoped, not a full pill-lock replay)
  B  no viruses (VCOUNT_P2==0)      -> NEVER fires
  C  outside mode 4                 -> NEVER fires
  D  pose genuinely moving          -> NEVER fires (the counter re-arms on every real step)
  E  flag-off identity              -> DRSTALLWD=0 == unset (byte-exact default); =1 changes bytes
  F  END-TO-END DEFECT REPRO: a mock copro that NEVER asserts DONE for P2, driven through >=2
     STALLWD periods. WITHOUT the watchdog the pill sticks at its post-lock-while-armed pose
     forever (0 further landings). WITH it, ARMED2 visibly re-arms (0->1, proving `_start` fired)
     and landings resume periodically -- the fix actually clears the reproduced defect, not just
     "looks plausible" on paper.

    tests/test_stallwd.py             # asserts; exit 1 on failure
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

# PRG-RAM addresses (see patch_cartridge_copro.py's module-level constants)
PEND2, ARMED2, WDOG2, WDOGH2, DELAY2 = 0x614F, 0x6161, 0x6162, 0x6166, 0x615F
ROT_DONE2, STABLE_CT2, TGT_C2, TGT_O2 = 0x616E, 0x6171, 0x6152, 0x6153
SWD_S0, SWD_S1, SWD_S2, SWD_CTL, SWD_CTH = 0x618D, 0x618E, 0x618F, 0x6190, 0x6191
VCOUNT_P2 = 0x03A4
PX2, PY2, ORI2 = 0x0385, 0x0386, 0x03A5
NAV_MAGIC = 0x6149   # power-on lazy-init magic; pre-set so a fresh MPU skips the once-ever
                      # power-on init block (which also clears ROT_DONE2 among others) and
                      # isolated tests start from OUR seed, not the power-on defaults.

_FLAGS = ("DRNOFREEZE", "DRHUMAN", "DRPOCKET", "DRRECOMMIT_NOFREEZE", "DRNAVDWELL",
          "DRPENDBOUND", "DRCOLDINIT", "DRSLAM_KOPEN", "DRP1WIGGLE", "DRP1NATIVE",
          "DRNAVESC", "DRNAVESC_N", "DRWRETRY", "DRSTALLWD", "DRSTALLWD_N")
_seq = [0]


def build(flags):
    for k in _FLAGS:
        os.environ.pop(k, None)
    os.environ.update(flags)
    _seq[0] += 1
    name = "stallwd_build_%d" % _seq[0]
    spec = importlib.util.spec_from_file_location(name, EMITTER)
    P = importlib.util.module_from_spec(spec)
    sys.modules[name] = P
    spec.loader.exec_module(P)
    unit1, labels = P.build_main(11, 1)
    return P, bytes(unit1), {k: BASE + v for k, v in labels.items()}


# ---------------------------------------------------------------------------
# A-D: isolated trigger tests. $04 is left 0 so mode-4 play dispatch (handle()/act/
# stagnate()) never runs on these hooks -- STALLWD sits BEFORE that gate in `main`,
# so this exercises its trigger/no-fire logic on its own, independent of whether the
# rest of the driver is behaving.
# ---------------------------------------------------------------------------

def run_hooks(unit1, labels, n_hooks, mode=4, vcount_p2=0x30, pose=(3, 9, 1),
              move_at=None, seed=None):
    m = MPU()
    m.memory[BASE:BASE + len(unit1)] = unit1
    m.memory[NAV_MAGIC] = 0xA5             # skip the once-ever power-on init (see NAV_MAGIC note)
    if seed:
        for addr, val in seed.items():
            m.memory[addr] = val
    x, y, o = pose
    snaps = []
    for h in range(n_hooks):
        if move_at is not None and h in move_at:
            y = (y - 1) & 0xFF
        m.memory[0x0046] = mode
        m.memory[VCOUNT_P2] = vcount_p2
        m.memory[PX2], m.memory[PY2], m.memory[ORI2] = x, y, o
        m.memory[0x04] = 0                     # skip handle()/act -- isolate the trigger
        m.memory[0x1FE], m.memory[0x1FF] = (SENT - 1) & 0xFF, (SENT - 1) >> 8
        m.sp = 0xFD
        m.pc = labels["main"]
        n = 0
        while m.pc != SENT and n < 60000:
            m.step()
            n += 1
        assert m.pc == SENT, "runaway pc=%04X hook=%d" % (m.pc, h)
        snaps.append(dict(pend2=m.memory[PEND2], armed2=m.memory[ARMED2], wdog2=m.memory[WDOG2],
                           wdogh2=m.memory[WDOGH2], delay2=m.memory[DELAY2],
                           rot_done2=m.memory[ROT_DONE2], stable_ct2=m.memory[STABLE_CT2],
                           tgt_c2=m.memory[TGT_C2], tgt_o2=m.memory[TGT_O2],
                           swd_ctl=m.memory[SWD_CTL], swd_cth=m.memory[SWD_CTH]))
    return snaps


WEDGED_SEED = {ARMED2: 1, WDOG2: 123, WDOGH2: 2, PEND2: 0, DELAY2: 0,
               ROT_DONE2: 1, STABLE_CT2: 42, TGT_C2: 5, TGT_O2: 2}


def test_a_fires_and_scoped(P, unit1, labels):
    n = P.STALLWD_N
    snaps = run_hooks(unit1, labels, n + 20, mode=4, vcount_p2=0x30,
                       pose=(3, 9, 1), seed=WEDGED_SEED)
    fired_idx = next((i for i, s in enumerate(snaps) if s["armed2"] == 0 and s["pend2"] == 1), None)
    assert fired_idx is not None, "watchdog never fired on a wedged, static P2 pose"
    assert n - 4 <= fired_idx <= n + 4, "fired at hook %d, expected ~%d" % (fired_idx, n)
    fired = snaps[fired_idx]
    assert fired["wdog2"] == 0 and fired["wdogh2"] == 0 and fired["delay2"] == 0, \
        "scoped reset didn't clear WDOG2/WDOGH2/DELAY2: %r" % fired
    # scoped: ROT_DONE2 / STABLE_CT2 / TGT_C2 / TGT_O2 must be BYTE-IDENTICAL to the seed --
    # the whole point of the scoped reset is not discarding a still-good commit/argmax.
    for key, addr_name in (("rot_done2", "ROT_DONE2"), ("stable_ct2", "STABLE_CT2"),
                            ("tgt_c2", "TGT_C2"), ("tgt_o2", "TGT_O2")):
        want = WEDGED_SEED[{"rot_done2": ROT_DONE2, "stable_ct2": STABLE_CT2,
                             "tgt_c2": TGT_C2, "tgt_o2": TGT_O2}[key]]
        assert fired[key] == want, "%s changed across the reset: %d != seed %d" % (
            addr_name, fired[key], want)
    print("  A  fires at hook %d (~%d), ROT_DONE2/STABLE_CT2/TGT_C2/TGT_O2 preserved: OK" %
          (fired_idx, n))


def test_b_no_virus_no_fire(P, unit1, labels):
    n = P.STALLWD_N
    snaps = run_hooks(unit1, labels, n + 40, mode=4, vcount_p2=0x00,
                       pose=(3, 9, 1), seed=WEDGED_SEED)
    assert all(s["armed2"] == 1 for s in snaps), \
        "watchdog fired with VCOUNT_P2==0 (P2 has no viruses -- should never fire)"
    print("  B  VCOUNT_P2==0 never fires (%d hooks checked): OK" % len(snaps))


def test_c_not_mode4_no_fire(P, unit1, labels):
    n = P.STALLWD_N
    for mode in (0, 1, 2, 3, 7, 8):
        snaps = run_hooks(unit1, labels, n + 40, mode=mode, vcount_p2=0x30,
                           pose=(3, 9, 1), seed=WEDGED_SEED)
        assert all(s["armed2"] == 1 for s in snaps), \
            "watchdog fired outside mode 4 (mode=%d)" % mode
    print("  C  never fires outside mode 4 (modes 0,1,2,3,7,8 checked): OK")


def test_d_moving_pose_no_fire(P, unit1, labels):
    n = P.STALLWD_N
    # nudge Y down every (n // 2) hooks -- well under the threshold each time, so the
    # counter never accumulates to N even though total elapsed hooks vastly exceeds N.
    move_at = set(range(n // 2, 6 * n, n // 2))
    snaps = run_hooks(unit1, labels, 6 * n, mode=4, vcount_p2=0x30,
                       pose=(3, 15, 1), move_at=move_at, seed=WEDGED_SEED)
    assert all(s["armed2"] == 1 for s in snaps), \
        "watchdog fired while the pose was genuinely progressing (legitimately slow, not wedged)"
    print("  D  genuinely-progressing pose never fires (%d hooks, %d moves): OK" %
          (len(snaps), len(move_at)))


def test_e_flag_off_identity():
    _, off1, _ = build({"DRNOFREEZE": "1"})
    _, off2, _ = build({"DRNOFREEZE": "1", "DRSTALLWD": "0"})
    _, on, _ = build({"DRNOFREEZE": "1", "DRSTALLWD": "1"})
    assert off1 == off2, "flag-off emission not deterministic"
    assert off1 != on, "DRSTALLWD=1 changed nothing -- the watchdog was not emitted"
    print("  E  flag-off byte-identical to unset, flag-on changes emission: OK")


# ---------------------------------------------------------------------------
# F: end-to-end defect reproduction + fix validation. A P2 game model with a
# per-mailbox "never asserts DONE" mock copro (same idea as freeze4_repro.py's
# scratch harness), driven through several STALLWD periods.
# ---------------------------------------------------------------------------

SPAWN_X, SPAWN_Y = 3, 15
GRAV_TH = 13


class Game:
    """Minimal CvC play model: P1 parked on a legal, never-moving pose (its own driver
    path still runs so nothing about P1 wedges the hook budget); P2 gets real gravity
    physics via a transcribed fallingPill_checkYMove, same constants as test_p1_wiggle.py."""

    def __init__(self, P, unit1, labels, p2_done_after=25, p2_never_done=False):
        self.P, self.labels = P, labels
        self.m = MPU()
        self.m.memory[BASE:BASE + len(unit1)] = unit1
        for i in range(128):
            self.m.memory[0x0400 + i] = 0xFF
            self.m.memory[0x0500 + i] = 0xFF
        for a, v in ((0x0301, 1), (0x0302, 2), (0x031A, 0), (0x031B, 2),
                     (0x0381, 1), (0x0382, 2), (0x039A, 0), (0x039B, 2)):
            self.m.memory[a] = v
        self.m.memory[0x04] = 1
        self.m.memory[0x0727] = 2
        self.m.memory[VCOUNT_P2] = 0x30                    # P2 still has viruses
        self.m.memory[0x0305], self.m.memory[0x0306], self.m.memory[0x0325] = 3, 9, 1
        self.x, self.y, self.orient = SPAWN_X, SPAWN_Y, 0
        self.frame = 0
        self.landings = []
        self.mbox = {}
        for wb, after, never in ((0x5000, 20, False), (P.W2_BASE, p2_done_after, p2_never_done)):
            self.mbox[wb] = dict(done=0, pub=(0xFF, 0xFF), armed=False, hooks=0,
                                  after=after, never_done=never)
        self._sync()

    def _sync(self):
        for wb, s in self.mbox.items():
            self.m.memory[wb + 0x84] = s["done"]
            self.m.memory[wb + 0x85], self.m.memory[wb + 0x86] = s["pub"]

    def _hook(self):
        m = self.m
        m.memory[0x0046] = 4
        m.memory[PX2], m.memory[PY2], m.memory[ORI2] = self.x, self.y, self.orient
        m.memory[0xF5] = 0
        m.memory[0x1FE], m.memory[0x1FF] = (SENT - 1) & 0xFF, (SENT - 1) >> 8
        m.sp = 0xFD
        m.pc = self.labels["main"]
        n = 0
        while m.pc != SENT and n < 60000:
            m.step()
            n += 1
        assert m.pc == SENT, "runaway pc=%04X frame=%d" % (m.pc, self.frame)
        for wb, s in self.mbox.items():
            if m.memory[wb + 0x84] != s["done"]:            # driver wrote +$84 = GO
                s.update(done=0, pub=(0xFF, 0xFF), armed=True, hooks=0)
            if s["armed"] and not s["never_done"]:
                s["hooks"] += 1
                if s["hooks"] == 3:
                    s["pub"] = (5, 2)
                if s["hooks"] >= s["after"]:
                    s.update(done=1, armed=False)
        self._sync()

    def frame_step(self):
        for _ in range(2):                                 # 2 hooks/frame, both inside the NMI
            self._hook()
        g = (self.m.memory[0x0392] + 1) & 0xFF
        self.m.memory[0x0392] = g
        if g >= GRAV_TH:
            self.m.memory[0x0392] = 0
            if self.y == 0:
                self.landings.append((len(self.landings), self.x, self.frame))
                self.x, self.y, self.orient = SPAWN_X, SPAWN_Y, 0
            else:
                self.y -= 1
        self.m.memory[0x43] = (self.m.memory[0x43] + 1) & 0xFF
        self.frame += 1


def boot(g):
    m = g.m
    for _ in range(10):
        m.memory[0x0046] = 8
        m.memory[0x1FE], m.memory[0x1FF] = (SENT - 1) & 0xFF, (SENT - 1) >> 8
        m.sp = 0xFD
        m.pc = g.labels["main"]
        n = 0
        while m.pc != SENT and n < 60000:
            m.step()
            n += 1
        m.memory[0x43] = (m.memory[0x43] + 1) & 0xFF


def test_f_end_to_end(stallwd_n=200, frames=4000):
    base_flags = dict(DRCOLDINIT="1", DRNOFREEZE="1", DRRECOMMIT_NOFREEZE="1")

    # WITHOUT the watchdog: the documented, unfixed P0.2 lock-while-armed pin should
    # stick the pill at its post-first-lock spawn pose and NEVER release it.
    P0, u0, L0 = build(base_flags)
    g0 = Game(P0, u0, L0, p2_never_done=True)
    boot(g0)
    for _ in range(frames):
        g0.frame_step()
    assert len(g0.landings) <= 1, (
        "control (DRSTALLWD off) recovered on its own (%d landings) -- the lock-while-armed "
        "defect isn't reproduced, so this is not a valid test of the fix" % len(g0.landings))
    stuck_pose = (g0.x, g0.y)
    print("  F0 control (DRSTALLWD=0): %d landing(s), final pose stuck at %r" %
          (len(g0.landings), stuck_pose))

    # WITH the watchdog: same defect (P2's search still never DONEs), but STALLWD should
    # repeatedly detect the static pose, force a scoped reset, and hand control back to
    # handle(2)'s own `_start` gate. The reset (ARMED2/WDOG2/WDOGH2->0, PEND2->1, DELAY2->0)
    # and `_start`'s re-arm (PEND2->0, ARMED2->1) can both land inside the SAME frame's two
    # hooks -- getInputs calls the driver hook twice per frame -- so end-of-frame sampling can
    # miss the transient ARMED2==0. Sample at HOOK granularity via a thin wrapper instead.
    P1_, u1, L1 = build(dict(base_flags, DRSTALLWD="1", DRSTALLWD_N=str(stallwd_n)))
    g1 = Game(P1_, u1, L1, p2_never_done=True)
    boot(g1)
    fire_events = [0]
    orig_hook = g1._hook

    def counting_hook():
        orig_hook()
        if g1.m.memory[ARMED2] == 0:      # never_done mock: ARMED2==0 post-launch is only ever
            fire_events[0] += 1           # reachable via a STALLWD scoped reset (see test A/F0)
    g1._hook = counting_hook

    for _ in range(frames):
        g1.frame_step()
    # de-duplicate consecutive same-hook observations into discrete fire events isn't needed --
    # ARMED2==0 is instantaneous (handle()'s own `_start` re-arms it the very next hook once
    # DELAY2==0, which STALLWD's reset already guarantees), so each fire shows up as exactly one
    # hook of ARMED2==0. Sanity: the count must be well below the hook budget.
    assert 0 < fire_events[0] < frames * 2, "implausible fire count %d" % fire_events[0]
    print("  F1 fix (DRSTALLWD=1): %d landing(s), %d watchdog fire(s) over %d frames (%d hooks)" %
          (len(g1.landings), fire_events[0], frames, frames * 2))
    assert fire_events[0] >= 2, (
        "expected >= 2 watchdog fires (>= 2 STALLWD periods) in %d frames, saw %d" %
        (frames, fire_events[0]))
    assert len(g1.landings) >= 2, (
        "expected the watchdog to unstick P2 repeatedly (>= 2 landings beyond the first "
        "natural fall), saw %d" % len(g1.landings))


def main():
    base = dict(DRNOFREEZE="1", DRRECOMMIT_NOFREEZE="1", DRCOLDINIT="1")
    P, unit1, labels = build(dict(base, DRSTALLWD="1", DRSTALLWD_N="200"))
    print("DRSTALLWD_N=%d" % P.STALLWD_N)

    test_a_fires_and_scoped(P, unit1, labels)
    test_b_no_virus_no_fire(P, unit1, labels)
    test_c_not_mode4_no_fire(P, unit1, labels)
    test_d_moving_pose_no_fire(P, unit1, labels)
    test_e_flag_off_identity()
    test_f_end_to_end(stallwd_n=P.STALLWD_N)

    print("\nSTALLWD gate: A fire+scoped OK, B no-virus OK, C mode-gate OK, D no-false-fire OK, "
          "E flag-off identity OK, F end-to-end defect repro + fix OK")


if __name__ == "__main__":
    main()
