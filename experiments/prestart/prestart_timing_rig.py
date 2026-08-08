#!/usr/bin/env python3
"""DRPRESTART timing: how much of the garbage window does the prestart actually reclaim?

Drives the REAL emitted driver through `main` -- the whole play dispatch, not just the new
routine -- for a modelled VS garbage window, and measures three things per stack height:

    release -> GO      how fast the driver reacts to the volley
    GO -> spawn        the prestart's LEAD: search time bought before the capsule exists
    DONE vs spawn      does the answer land BEFORE the capsule starts falling?

TIMELINE MODEL (all four numbers ROM-derived, none invented here):
  * W = 264 - 16*h frames from release to spawn (h = stack height of the shallowest hit
    column). Emulator-verified 8/8 on the real Rev0 ROM: h=0 -> 264 f, 6 -> 168, 13 -> 56,
    15 -> 24.
  * post-garbage gravity is 16 FRAMES PER ROW (checkDrop is gated on the nametable row-render
    cursor), so the rig animates the volley down one row every 16 frames rather than settling
    $0500 instantly. That is not cosmetic: it is what makes "did the driver read a floating
    board?" a question this rig can answer instead of assume.
  * the driver runs exactly 2 hooks per frame, both inside the NMI.
  * checkReleaseAttack runs in the MAIN LOOP, so the earliest hook that can observe it is the
    NMI of the following frame -- the rig releases between frames for exactly that reason.

SEARCH LATENCY is a parameter, not a guess baked into the answer: T_s defaults to 300 hooks
(= 150 frames), the project's measured warm depth-3 figure, and is swept so the DONE-before-
spawn claim is reported as a boundary rather than a single yes/no.

BASELINE ARM is the same emitter with DRPRESTART unset, run through the same timeline, so
every number below is a paired A/B on one code path -- not this build against a remembered one.

    experiments/prestart/prestart_timing_rig.py
"""
from __future__ import annotations

import importlib.util
import os
import sys

from py65.devices.mpu6502 import MPU

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
BASE = 0x8000
SENT = 0x4FF2
SPAWN_Y = 15                 # $0386 counts UP from the floor: spawn = 15, landing = 0
EMPTY = 0xFF
SINGLE = 0x80
T_S_DEFAULT = 300            # warm depth-3 search, in HOOKS (= 150 frames at 2 hooks/frame)

_FLAGS_BASE = {"DRCOLDINIT": "1", "DRWRETRY": "1"}
_seq = [0]


def build(flags):
    for k in [k for k in os.environ if k.startswith("DR")]:
        os.environ.pop(k, None)
    os.environ.update(flags)
    _seq[0] += 1
    name = "timing_emitter_%d" % _seq[0]
    path = os.path.join(REPO, "patch_cartridge_copro.py")
    sys.path.insert(0, REPO)
    try:
        spec = importlib.util.spec_from_file_location(name, path)
        M = importlib.util.module_from_spec(spec)
        sys.modules[name] = M
        spec.loader.exec_module(M)
        assert os.path.realpath(M.__file__) == os.path.realpath(path), M.__file__
        unit1, labels = M.build_main(11, 1)
        return M, bytes(unit1), {k: BASE + v for k, v in labels.items()}
    finally:
        sys.path.remove(REPO)


def flat_board(h):
    """16x8 field with every column stacked h high. Colours cycle on (row+col) mod 3 so no
    4-run exists anywhere -- the garbage must be what creates one, if anything does."""
    b = [EMPTY] * 128
    for r in range(16 - h, 16):
        for c in range(8):
            b[r * 8 + c] = SINGLE | ((r + c) % 3)
    return b


class Sim:
    """One driver instance on a modelled VS timeline."""

    def __init__(self, M, unit1, labels, t_s=T_S_DEFAULT):
        self.M, self.labels = M, labels
        self.t_s = t_s
        self.m = MPU()
        self.m.memory[BASE:BASE + len(unit1)] = unit1
        self.W2 = M.W2_BASE
        self.frame = 0
        self.y = SPAWN_Y
        self.events = []
        self.hook_cycles = []
        for i in range(128):
            self.m.memory[0x0400 + i] = EMPTY
            self.m.memory[0x0500 + i] = EMPTY
        for a, v in ((0x0301, 1), (0x0302, 2), (0x031A, 0), (0x031B, 2),
                     (0x0381, 1), (0x0382, 2), (0x039A, 0), (0x039B, 2)):
            self.m.memory[a] = v
        self.m.memory[0x04] = 1
        self.m.memory[0x0727] = 2
        self.m.memory[0x03A4] = 0x20                 # VCOUNT_P2, non-endgame
        self.m.memory[0x03A7] = 0x11
        self.m.memory[0x0780 + 0x11] = 4
        self.m.memory[0x0305], self.m.memory[0x0306], self.m.memory[0x0325] = 3, 9, 1
        self.copro = dict(armed=False, hooks=0, done=0, go_frame=None, done_frame=None,
                          gos=[])
        self._sync()

    def _sync(self):
        self.m.memory[self.W2 + 0x84] = self.copro["done"]

    def _hook(self, mode=4):
        m = self.m
        m.memory[0x0046] = mode
        m.memory[0x0385], m.memory[0x0386], m.memory[0x03A5] = 3, self.y, 0
        m.memory[0xF6] = 0
        m.memory[0xF8] = 0
        m.memory[0x1FE], m.memory[0x1FF] = (SENT - 1) & 0xFF, (SENT - 1) >> 8
        m.sp = 0xFD
        m.pc = self.labels["main"]
        n = 0
        c0 = m.processorCycles
        while m.pc != SENT and n < 500000:
            m.step()
            n += 1
        assert m.pc == SENT, "runaway pc=%04X frame=%d" % (m.pc, self.frame)
        self.hook_cycles.append(m.processorCycles - c0)
        s = self.copro
        if m.memory[self.W2 + 0x84] != s["done"]:            # driver wrote +$84 = GO
            s.update(armed=True, hooks=0, done=0)
            s["gos"].append(self.frame)
            s["go_frame"] = self.frame
            s["done_frame"] = None
        if s["armed"]:
            s["hooks"] += 1
            if s["hooks"] >= self.t_s:
                s.update(armed=False, done=1)
                s["done_frame"] = self.frame
                # publish a legal answer so handle() adopts it instead of hitting its guard
                m.memory[self.W2 + 0x85], m.memory[self.W2 + 0x86] = 3, 1
        self._sync()

    def frame_step(self, mode=4):
        for _ in range(2):
            self._hook(mode)
        self.m.memory[0x43] = (self.m.memory[0x43] + 1) & 0xFF
        self.frame += 1

    def boot(self):
        for _ in range(10):
            self._hook(mode=8)


def run(flags, h, size=3, t_s=T_S_DEFAULT, garbage=True, settle_anim=True):
    """One inter-capsule timeline, with or without a volley. Returns the measured frames.

    `garbage=False` is the NO-REGRESSION arm: the identical timeline minus the release, so a
    DRPRESTART build must reproduce the baseline's spawn-edge flow exactly (one GO, at +7 f).
    """
    M, unit1, labels = build(flags)
    sim = Sim(M, unit1, labels, t_s=t_s)
    sim.boot()

    board = flat_board(h)
    for i, v in enumerate(board):
        sim.m.memory[0x0500 + i] = v
    sim.y = 0                                     # previous capsule has locked
    sim.m.memory[0x0318] = 0
    for _ in range(6):                            # let the driver observe the locked pose
        sim.frame_step()

    W = 264 - 16 * h
    cols = []
    if garbage:
        # the attacker banks a volley: attackSize goes nonzero and sits there
        sim.m.memory[0x0318] = size
        for _ in range(3):
            sim.frame_step()
        # checkReleaseAttack: garbage into row 0, THEN attackSize cleared -- that ORDER is what
        # makes the edge safe to observe. Both happen in the main loop, between NMIs.
        cols = [(sim.m.memory[0x43] & (0x01 if size == 4 else 0x03))
                + i * (4 if size == 2 else 2) for i in range(size)]
        cols = [c for c in cols if c < 8]
        for j, c in enumerate(cols):
            sim.m.memory[0x0500 + c] = SINGLE | (j % 3)
        sim.m.memory[0x0318] = 0
    release_frame = sim.frame
    gos_before = len(sim.copro["gos"])

    # ---- the window: the game animates the volley down one row per 16 frames
    land_row = 15 - h
    for f in range(W):
        if garbage and settle_anim:
            step = f // 16
            for j, c in enumerate(cols):
                cur = min(step, land_row)
                prev = cur - 1
                if 0 <= prev < 16:
                    sim.m.memory[0x0500 + prev * 8 + c] = EMPTY
                sim.m.memory[0x0500 + cur * 8 + c] = SINGLE | (j % 3)
        sim.frame_step()

    # ---- action_sendPill: the capsule spawns; $0386 jumps to 15 = the driver's only trigger
    sim.y = SPAWN_Y
    spawn_frame = sim.frame
    for _ in range(400):
        sim.frame_step()
        if sim.copro["done_frame"] is not None and not sim.copro["armed"] \
                and sim.copro["done_frame"] >= release_frame:
            break

    s = sim.copro
    gos = s["gos"][gos_before:]                   # only the searches for THIS capsule
    hc = sim.hook_cycles
    return dict(W=W, release=release_frame, spawn=spawn_frame, cols=cols,
                gos=gos, go=s["go_frame"], done=s["done_frame"],
                n_gos_total=len(gos),
                n_gos_in_window=sum(1 for g in gos if release_frame <= g < spawn_frame),
                hook_max=max(hc), hook_typ=sorted(hc)[len(hc) // 2])


def run_second_volley(flags, h, t_s=T_S_DEFAULT):
    """P1 attacks AGAIN before the receiver's next spawn. The projection the prestart searched
    is now stale, so the driver must INVALIDATE (tear down the in-flight search) and hand the
    capsule back to the ordinary spawn-edge path -- i.e. end up with baseline timing, not a
    second GO fired at a still-running copro."""
    M, unit1, labels = build(flags)
    sim = Sim(M, unit1, labels, t_s=t_s)
    sim.boot()
    for i, v in enumerate(flat_board(h)):
        sim.m.memory[0x0500 + i] = v
    sim.y = 0
    sim.m.memory[0x0318] = 0
    for _ in range(6):
        sim.frame_step()

    def release(tag):
        sim.m.memory[0x0318] = 3
        for _ in range(2):
            sim.frame_step()
        base = sim.m.memory[0x43] & 0x03
        for j in range(3):
            c = base + j * 2
            if c < 8:
                sim.m.memory[0x0500 + c] = SINGLE | (j % 3)
        sim.m.memory[0x0318] = 0
        return sim.frame

    r1 = release("first")
    gos_at_r1 = len(sim.copro["gos"])
    for _ in range(40):                            # part-way through the animation...
        sim.frame_step()
    r2 = release("second")                         # ...a second volley lands
    for _ in range(max(1, 264 - 16 * h - 40)):
        sim.frame_step()
    sim.y = SPAWN_Y
    spawn = sim.frame
    for _ in range(400):
        sim.frame_step()
        # must be a DONE for a search started AFTER the spawn -- the first prestart's own DONE
        # lands mid-window and would otherwise exit the loop before the fallback search runs
        if sim.copro["done_frame"] is not None and not sim.copro["armed"] \
                and sim.copro["done_frame"] > spawn:
            break
    gos = sim.copro["gos"][gos_at_r1:]
    return dict(r1=r1, r2=r2, spawn=spawn, gos=gos,
                go_after_spawn=[g for g in gos if g >= spawn],
                done=sim.copro["done_frame"])


def main():
    t_s = int(sys.argv[1]) if len(sys.argv) > 1 else T_S_DEFAULT
    on = dict(_FLAGS_BASE, DRPRESTART="1")
    off = dict(_FLAGS_BASE)

    print("=" * 96)
    print("DRPRESTART timing -- real emitted driver, modelled VS garbage window")
    print("search latency T_s = %d hooks = %.1f frames (warm depth-3)" % (t_s, t_s / 2.0))
    print("=" * 96)
    print("%-5s %-8s | %-11s %-10s %-13s | %-11s %-13s | %s"
          % ("h", "W (f)", "rel->GO", "GO->spawn", "DONE-spawn", "base GO", "base DONE",
             "gain (f)"))
    print("-" * 96)
    rows = []
    for h in (0, 6, 13, 15):
        a = run(on, h, t_s=t_s)
        b = run(off, h, t_s=t_s)
        rel_go = a["go"] - a["release"]
        lead = a["spawn"] - a["go"]
        margin = a["spawn"] - a["done"] if a["done"] is not None else None
        b_go = b["go"] - b["spawn"]
        b_done = b["done"] - b["spawn"] if b["done"] is not None else None
        gain = (b_done - margin * -1) if margin is not None and b_done is not None else None
        gain = (b_done + margin) if (margin is not None and b_done is not None) else None
        rows.append((h, a, b, rel_go, lead, margin, b_go, b_done, gain))
        print("%-5d %-8d | %-11d %-10d %-13s | +%-10d %-13s | %s"
              % (h, a["W"], rel_go, lead,
                 ("DONE %d f BEFORE spawn" % margin) if margin and margin > 0
                 else ("%d f AFTER spawn" % -margin) if margin is not None else "never",
                 b_go, ("+%d" % b_done) if b_done is not None else "never",
                 ("%d" % gain) if gain is not None else "-"))
    print()
    print("rel->GO    : frames from the volley landing in RAM to the copro being started. 0 means")
    print("             the very next NMI -- checkReleaseAttack runs in the MAIN LOOP, so the")
    print("             first hook that can see it is already the earliest possible reaction.")
    print("GO->spawn  : the LEAD -- search time bought before the capsule exists")
    print("DONE-spawn : positive = the answer is already published when the capsule spawns")
    print("base GO    : baseline arm, frames AFTER spawn before its search starts (the 15-hook")
    print("             settle); base DONE = frames after spawn before its answer arrives")
    print("gain       : how many frames EARLIER the answer is available, prestart vs baseline")
    print()

    ok = True
    print("-" * 96)
    print("GO discipline (the GO-storm freeze family is why this is a gate, not a note)")
    print("-" * 96)
    for h, a, b, rel_go, lead, margin, b_go, b_done, gain in rows:
        line = ("h=%-3d prestart: %d GO(s) in window, %d total for the capsule | "
                "baseline: %d GO(s) in window, %d total"
                % (h, a["n_gos_in_window"], a["n_gos_total"],
                   b["n_gos_in_window"], b["n_gos_total"]))
        bad = []
        if a["n_gos_in_window"] != 1:
            bad.append("prestart did not GO exactly once in the window")
        if a["n_gos_total"] != 1:
            bad.append("prestart DOUBLE-SEARCHED the capsule (%d GOs)" % a["n_gos_total"])
        if b["n_gos_in_window"] != 0:
            bad.append("baseline searched inside the window -- the rig models it wrongly")
        if b["n_gos_total"] != 1:
            bad.append("baseline GO count is %d, expected 1" % b["n_gos_total"])
        print("  " + line + ("   OK" if not bad else "   *** " + "; ".join(bad)))
        ok = ok and not bad

    print()
    print("-" * 96)
    print("NO-REGRESSION: identical timeline with NO volley -- the prestart build must reproduce")
    print("the baseline spawn-edge flow exactly (this is the path 100%% of clean pills take)")
    print("-" * 96)
    for h in (0, 6, 13, 15):
        a = run(on, h, t_s=t_s, garbage=False)
        b = run(off, h, t_s=t_s, garbage=False)
        same = (a["n_gos_total"] == b["n_gos_total"]
                and (a["go"] - a["spawn"]) == (b["go"] - b["spawn"])
                and (a["done"] - a["spawn"]) == (b["done"] - b["spawn"]))
        print("  h=%-3d prestart GO +%d f / DONE +%d f (%d GO) | baseline GO +%d f / DONE +%d f "
              "(%d GO)   %s"
              % (h, a["go"] - a["spawn"], a["done"] - a["spawn"], a["n_gos_total"],
                 b["go"] - b["spawn"], b["done"] - b["spawn"], b["n_gos_total"],
                 "IDENTICAL" if same else "*** DIVERGED"))
        ok = ok and same

    print()
    print("-" * 96)
    print("SECOND VOLLEY: P1 attacks again mid-animation -- the projection is stale, so the")
    print("driver must invalidate and fall back to a normal spawn-edge search")
    print("-" * 96)
    for h in (0, 6):
        v = run_second_volley(on, h, t_s=t_s)
        after = v["go_after_spawn"]
        good = (len(after) == 1 and after[0] - v["spawn"] == 7)
        print("  h=%-3d GOs at frames %s; spawn %d -> %s"
              % (h, [g - v["r1"] for g in v["gos"]], v["spawn"] - v["r1"],
                 "one search at spawn+%d f (baseline flow) OK" % (after[0] - v["spawn"])
                 if good else "*** %d search(es) after spawn: %s"
                 % (len(after), [g - v["spawn"] for g in after])))
        ok = ok and good

    print()
    print("-" * 96)
    print("HOOK COST (the driver runs inside the NMI; the frame is 29780 cycles and only")
    print("overrunning a WHOLE frame is dangerous -- that is the DRREENTRY/BUSY guard's case)")
    print("-" * 96)
    for h in (0, 15):
        a = run(on, h, t_s=t_s)
        b = run(off, h, t_s=t_s)
        print("  h=%-3d prestart: typical hook %d cyc, PEAK %d cyc (%.0f%% of a frame) | "
              "baseline: typical %d, peak %d"
              % (h, a["hook_typ"], a["hook_max"], 100.0 * a["hook_max"] / 29780,
                 b["hook_typ"], b["hook_max"]))

    print()
    print("RESULT:", "PASS" if ok else "FAIL")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
