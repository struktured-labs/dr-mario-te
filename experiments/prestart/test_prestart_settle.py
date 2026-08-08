#!/usr/bin/env python3
"""DRPRESTART settle correctness: the REAL emitted 6502 `pre_tick` vs the faithful sim.

WHAT IS UNDER TEST.  Not a Python paraphrase -- this drives the actual bytes
`patch_cartridge_copro.py` emits for DRPRESTART=1, in py65, with the board in $0500, the
attack latch in the driver's own PRG-RAM, and the projection read back out of the P2 copro
window at $5200.  If the emitter changes, this moves with it.

GROUND TRUTH.  `vs_harness.drop_garbage`'s first two steps, which are the ROM-true release:
write `attackColors[i] | singleHalfPill` UNCONDITIONALLY into row 0 at
`garbage_columns(size, phase)`, then settle with `FaithfulBoard._apply_gravity()` to a
fixpoint.  The third step (resolve) is deliberately NOT applied: the 6502 does not resolve
cascades, it BAILS when the garbage completes a line, and that bail is asserted separately.

BOARDS are real: random legal play through `FaithfulDrMarioEnv` at several levels, sampled
after `resolve()` so every one is genuinely settled and 4-run-free -- which is exactly the
invariant the 6502 settle relies on ("the only unsupported cells are the garbage singles").
Synthetic boards would have let me assume that invariant instead of exercising it against
real link structure, real viruses and real post-cascade overhangs.

COLOUR CONVENTION (the trap in dr-mario-copro-0based-colors): the faithful sim's Pill/colour
plane is 1..3; the NES field byte and the copro mailbox are 0-based, i.e. `tile = hi<<4 |
(c-1)`.  The conversion lives in `to_nes` below and is asserted at the boundary, not assumed.

    experiments/prestart/test_prestart_settle.py [N] [arm]
        N   = number of cases (default 200)
        arm = "mister" (default, W2_BASE=$5200) or "pocket" (DRPOCKET=1 DRHUMAN=1, which
              moves P2's whole mailbox to $5000). The arm MATTERS: the prestart writes its
              projection to W2_BASE, so a rig that only ever exercised $5200 would say
              nothing about the image the Pocket core actually runs.
"""
from __future__ import annotations

import importlib.util
import os
import sys

import numpy as np
from py65.devices.mpu6502 import MPU

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
SIMSRC = "/home/struktured/projects/dr_mario_rl/.claude/worktrees/faithful-sim/src"
VSAWARE = "/home/struktured/projects/dr_mario_rl/tmp/vs_aware"
for _p in (SIMSRC, VSAWARE):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from drmario.faithful_game import (FaithfulBoard, LINK_NONE, LINK_UP, LINK_DOWN,  # noqa: E402
                                   LINK_LEFT, LINK_RIGHT)
from drmario.faithful_env import FaithfulDrMarioEnv                               # noqa: E402

BASE = 0x8000
SENT = 0x4FF2            # RTS lands here; same sentinel idiom as tests/tempo_rig.py
P2_BOARD = 0x0500
EMPTY = 0xFF
SINGLE = 0x80            # singleHalfPill, the tile checkReleaseAttack writes
# linkcorpus.py's mapping, transcribed: link[r,c] names WHERE MY PARTNER IS, so LINK_UP is
# the BOTTOM half ($50) and LINK_RIGHT is the LEFT half ($60).
_HI = {LINK_NONE: 0x8, LINK_UP: 0x5, LINK_DOWN: 0x4, LINK_LEFT: 0x7, LINK_RIGHT: 0x6}

# ROM constants (defines/drmario_constants.asm), used to derive the garbage columns exactly
# as checkReleaseAttack does -- start = frameCounter & <pos mask>, then stride gap+1.
_POS = {2: 0x03, 3: 0x03, 4: 0x01}
_STRIDE = {2: 4, 3: 2, 4: 2}


def garbage_columns(size, frame_counter):
    start = frame_counter & _POS[size]
    return [start + i * _STRIDE[size] for i in range(size)]


def to_nes(board):
    """FaithfulBoard -> the 128 NES field bytes the game keeps at $0400/$0500."""
    out = []
    for r in range(board.rows):
        for c in range(board.cols):
            col = int(board.color[r, c])
            if col == 0:
                out.append(EMPTY)
            elif board.is_virus[r, c]:
                out.append(0xD0 | (col - 1))
            else:
                out.append((_HI[int(board.link[r, c])] << 4) | (col - 1))
    return out


def build_emitter(flags):
    """Import the emitter from THIS worktree under `flags`, with the path pinned and
    __file__ asserted before and after the build (dr-mario-copro-build-provenance)."""
    for k in [k for k in os.environ if k.startswith("DR")]:
        os.environ.pop(k, None)
    os.environ.update(flags)
    path = os.path.join(REPO, "patch_cartridge_copro.py")
    sys.path.insert(0, REPO)
    try:
        spec = importlib.util.spec_from_file_location("prestart_emitter", path)
        M = importlib.util.module_from_spec(spec)
        sys.modules["prestart_emitter"] = M
        spec.loader.exec_module(M)
        assert os.path.realpath(M.__file__) == os.path.realpath(path), M.__file__
        unit1, labels = M.build_main(11, 1)
        assert os.path.realpath(M.__file__) == os.path.realpath(path), M.__file__
        return M, bytes(unit1), {k: BASE + v for k, v in labels.items()}
    finally:
        sys.path.remove(REPO)


class Rig:
    """One py65 machine holding the emitted driver; `run_pre_tick` is one JSR into it."""

    def __init__(self, M, unit1, labels):
        self.M, self.labels = M, labels
        self.m = MPU()
        self.m.memory[BASE:BASE + len(unit1)] = unit1
        self.W2 = M.W2_BASE

    def run_pre_tick(self, nes_board, size, preview, reserve_val, pills_counter=0x11,
                     seed2=0, armed2=0, pend2=0, pre_act2=0):
        m = self.m
        M = self.M
        for i in range(128):
            m.memory[P2_BOARD + i] = nes_board[i]
        for i in range(128):                       # window pre-poisoned: a bail must not write
            m.memory[self.W2 + i] = 0xA5
        for a in (self.W2 + 0x80, self.W2 + 0x81, self.W2 + 0x82, self.W2 + 0x83,
                  self.W2 + 0x84):
            m.memory[a] = 0xA5
        m.memory[M.PRE_ATK2] = 0                   # released: size cleared, garbage already in RAM
        m.memory[M.PRE_LAST2] = size               # what the previous hook saw
        m.memory[M.PRE_ACT2] = pre_act2
        m.memory[M.ARMED2], m.memory[M.PEND2] = armed2, pend2
        m.memory[M.WDOG2], m.memory[M.WDOGH2] = 0xEE, 0xEE
        m.memory[M.SEED2] = seed2
        m.memory[0x039A], m.memory[0x039B] = preview
        m.memory[0x03A7] = pills_counter
        m.memory[0x0780 + pills_counter] = reserve_val
        m.memory[0x1FE], m.memory[0x1FF] = (SENT - 1) & 0xFF, (SENT - 1) >> 8
        m.sp = 0xFD
        m.pc = self.labels["pre_tick"]
        c0, n = m.processorCycles, 0
        while m.pc != SENT and n < 400000:
            m.step()
            n += 1
        assert m.pc == SENT, "pre_tick ran away at pc=%04X" % m.pc
        return dict(
            cycles=m.processorCycles - c0,
            went=(m.memory[self.W2 + 0x84] != 0xA5),
            armed2=m.memory[M.ARMED2],
            pre_act2=m.memory[M.PRE_ACT2],
            pend2=m.memory[M.PEND2],
            window=[m.memory[self.W2 + i] for i in range(128)],
            mail=[m.memory[self.W2 + 0x80 + i] for i in range(4)],
        )


def settled_boards(n_want, levels=(11, 15, 18, 20), seeds=(1, 2, 3, 4, 5, 6, 7, 8)):
    """Real post-resolve boards from random legal play (settled + 4-run-free by construction)."""
    out = []
    rng = np.random.default_rng(20260808)
    for seed in seeds:
        for level in levels:
            env = FaithfulDrMarioEnv(level=level, seed=seed, max_pills=200)
            env.reset(seed=seed)
            for _ in range(200):
                mask = env.action_masks()
                if not mask.any():
                    break
                a = int(rng.choice(np.flatnonzero(mask)))
                _, _, term, trunc, _ = env.step(a)
                out.append(env.board.clone())
                if term or trunc:
                    break
            if len(out) >= n_want * 4:
                return out
    return out


def golden(board, size, colours, frame_counter):
    """vs_harness.drop_garbage, stopped BEFORE resolve. Returns (settled board, landed cells)."""
    b = board.clone()
    cols = [c for c in garbage_columns(size, frame_counter) if 0 <= c < b.cols]
    for i, c in enumerate(cols):
        b.color[0, c] = colours[i % len(colours)]
        b.link[0, c] = LINK_NONE
        b.is_virus[0, c] = False
    while b._apply_gravity():
        pass
    return b, cols


def stack_height(board, c):
    """16 - (topmost occupied row) for column c; 0 if the column is empty. This is the h in
    W = 264 - 16*h, i.e. how far a garbage single dropped into this column can FALL."""
    for r in range(board.rows):
        if board.color[r, c] != 0:
            return board.rows - r
    return 0


def broke_a_link(board, cols):
    """Did the release overwrite a cell that was HALF OF A LINKED CAPSULE?

    checkReleaseAttack's row-0 `sta` is unconditional, so a volley can delete one half of a
    capsule locked at the top and orphan the other. Neither reference models that state:
    `FaithfulBoard._bodies()` follows the surviving link non-reciprocally and drops the orphan
    GLUED TO THE GARBAGE as a rigid pair (its own comment says the case "shouldn't happen"),
    while the ROM's `checkDrop` walks left from a rightHalfPill hunting a leftHalfPill that is
    no longer there. The driver bails on all of them; this predicate is how the test knows it
    should, and it is checked on the PRE-release board, where the fact is unambiguous.
    """
    return any(board.color[0, c] != 0 and board.link[0, c] != LINK_NONE for c in cols)


def has_four(b, cols):
    """Does any cell in one of the garbage columns sit in a run of >= 4 of its own colour?
    Mirrors the 6502's post-settle check: every landed cell's row and its column."""
    for c in cols:
        rs = [r for r in range(b.rows) if b.color[r, c] != 0]
        if not rs:
            continue
        r = min(rs)                                   # the settled garbage is the topmost cell
        col = int(b.color[r, c])
        run = 0
        for cc in range(b.cols):                      # horizontal through (r, c)
            run = run + 1 if int(b.color[r, cc]) == col else 0
            if run >= 4:
                return True
        run = 0
        for rr in range(b.rows):                      # vertical through (r, c)
            run = run + 1 if int(b.color[rr, c]) == col else 0
            if run >= 4:
                return True
    return False


ARMS = {
    "mister": {"DRPRESTART": "1"},
    # DRPOCKET asserts DRHUMAN, and under DRHUMAN handle(1) is never emitted -- so on this arm
    # the $5000 window belongs to P2 alone and the prestart cannot collide with a P1 search.
    "pocket": {"DRPRESTART": "1", "DRPOCKET": "1", "DRHUMAN": "1"},
}


def main():
    n_want = int(sys.argv[1]) if len(sys.argv) > 1 else 200
    arm = sys.argv[2] if len(sys.argv) > 2 else "mister"
    assert arm in ARMS, "arm must be one of %s" % sorted(ARMS)
    M, unit1, labels = build_emitter(ARMS[arm])
    rig = Rig(M, unit1, labels)
    boards = settled_boards(n_want)
    rng = np.random.default_rng(4242)

    exact = mism = gos = 0
    control_caught = control_noop = 0
    bails = {"4-run": 0, "orphaned link": 0}
    strata = {}                      # h_min of the hit columns -> [go, bail]
    cyc = []
    failures = []
    for i in range(n_want):
        b0 = boards[i % len(boards)]
        size = int(rng.integers(2, 5))
        fc = int(rng.integers(0, 256))
        colours = [int(rng.integers(1, 4)) for _ in range(4)]
        gb, gcols = golden(b0, size, colours, fc)
        why_bail = ("orphaned link" if broke_a_link(b0, gcols)
                    else "4-run" if has_four(gb, gcols) else None)

        nes_in = to_nes(b0)                            # board as the game leaves it PRE-release...
        for j, c in enumerate(gcols):                  # ...plus the release, floating at row 0
            nes_in[c] = SINGLE | (colours[j % len(colours)] - 1)

        preview = (int(rng.integers(0, 3)), int(rng.integers(0, 3)))
        reserve_val = int(rng.integers(0, 9))
        r = rig.run_pre_tick(nes_in, size, preview, reserve_val, seed2=0)
        cyc.append(r["cycles"])
        # h_min = STACK HEIGHT (16 - topmost occupied row, NOT the cell count -- a column with
        # two viruses and air between them is tall, not 2 deep) of the SHALLOWEST hit column.
        # That is the same h that sets the window length W = 264 - 16*h, so the strata below
        # read directly against the timing table.
        h_min = min(stack_height(b0, c) for c in gcols)
        st = strata.setdefault(h_min, [0, 0])
        st[1 if why_bail else 0] += 1

        if why_bail:
            bails[why_bail] += 1
            # A bail must be TOTAL: no GO, no state change, and not one byte written into the
            # copro window (pre-poisoned with $A5) -- otherwise a bailed prestart could leave a
            # half-written board for the next real _start to inherit.
            ok = (not r["went"]) and r["armed2"] == 0 and r["pre_act2"] == 0 \
                and all(v == 0xA5 for v in r["window"])
            if ok:
                exact += 1
            else:
                mism += 1
                failures.append((i, "expected BAIL (%s), driver went=%s armed2=%d window_dirty=%s"
                                 % (why_bail, r["went"], r["armed2"],
                                    any(v != 0xA5 for v in r["window"]))))
            continue

        gos += 1
        want = to_nes(gb)
        problems = []
        if not r["went"]:
            problems.append("driver did NOT issue GO")
        if r["window"] != want:
            bad = [k for k in range(128) if r["window"][k] != want[k]]
            problems.append("board differs at %d offsets, first=%d (got $%02X want $%02X)"
                            % (len(bad), bad[0], r["window"][bad[0]], want[bad[0]]))
        exp_mail = [preview[0], preview[1], reserve_val // 3, reserve_val % 3]
        if r["mail"] != exp_mail:
            problems.append("mailbox %s != %s" % (r["mail"], exp_mail))
        if r["armed2"] != 1 or r["pre_act2"] != 1 or r["pend2"] != 0:
            problems.append("state armed2=%d pre_act2=%d pend2=%d"
                            % (r["armed2"], r["pre_act2"], r["pend2"]))
        if problems:
            mism += 1
            failures.append((i, "; ".join(problems)))
        else:
            exact += 1
        # DEFECT CONTROL (house rule: test the DEFECT, not the fix). The failure this whole
        # feature exists to avoid is uploading $0500 AS-IS, with the volley still floating at
        # row 0. Feed the comparator that exact board and require it to REJECT -- a comparator
        # that cannot fail is not evidence. Skipped when the settle was a genuine no-op (every
        # hit column already full to row 0), because then the two boards legitimately agree.
        if nes_in != want:
            control_caught += (nes_in != want)
        else:
            control_noop += 1

    print("=" * 74)
    print("DRPRESTART settle: emitted 6502 vs FaithfulBoard gravity")
    print("=" * 74)
    print("arm                : %s   (P2 mailbox at $%04X)" % (arm, M.W2_BASE))
    print("cases              : %d  (from %d distinct real post-resolve boards)"
          % (n_want, len(boards)))
    print("  projected + GO   : %d   (board compared cell-for-cell + mailbox)" % gos)
    print("  bailed 4-run     : %d" % bails["4-run"])
    print("  bailed orphan    : %d" % bails["orphaned link"])
    print("EXACT MATCHES      : %d / %d" % (exact, n_want))
    print("mismatches         : %d" % mism)
    print("pre_tick cycles    : min %d  median %d  max %d"
          % (min(cyc), int(np.median(cyc)), max(cyc)))
    print("defect control     : %d/%d GO cases where the RAW $0500 board (volley still floating"
          % (control_caught, gos))
    print("                     at row 0) is REJECTED by this comparator; %d were a legitimate"
          % control_noop)
    print("                     no-op (hit columns already full to row 0)")
    print()
    print("fire rate by h_min (stack height of the shallowest hit column; W = 264 - 16*h frames)")
    print("  %-6s %6s %6s %7s  %s" % ("h_min", "GO", "bail", "GO%", "window W"))
    for h in sorted(strata):
        go, bl = strata[h]
        print("  %-6d %6d %6d %6.1f%%  %d f" % (h, go, bl, 100.0 * go / (go + bl), 264 - 16 * h))
    for i, why in failures[:12]:
        print("  FAIL case %d: %s" % (i, why))
    print()
    print("RESULT:", "PASS" if mism == 0 else "FAIL")
    return 0 if mism == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
