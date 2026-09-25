"""Steering-faithful execution layer: WHERE a pill actually lands on the couch cart, not where the brain aimed.

The offline sims (gate_b, vs_race, cosim farm) place every pill at the brain's straight-drop target instantly.
On silicon the P2 cart driver steers the capsule frame by frame under live ROM gravity, and it sometimes
lands elsewhere (couch forensics, experiments/couch_forensics/RESULT_COUCH_PREVALENCE.md). This module
simulates that execution at frame level:

ROM (Dr. Mario disassembly, NTSC), per controlled frame, in action_pillFalling order:
  checkYMove  : odd frameCounter + ONLY-DOWN held -> lower 1 row; else speedCounter++ and lower when
                speedCounter > speedCounterTable[base(speed) + speedUps] (speedUps += 1 every 10 pills,
                max 49). A lower into an occupied / off-floor cell = LOCK (the pill lands there).
  checkXMove  : L/R PRESS edge -> horVelocity v := 0 and move 1 now; HELD -> v++, move when v >= 16 then
                v := 10 (6 f/col). A move into the wall is skipped; into a blocked cell: undone, v := 15.
                v is NOT reset between pills (silicon-verified 2026-09-25, experiments/das_carry/).
  checkRotate : A press -> rot-1, B press -> rot+1 (mod 4); an illegal H result tries a left wall-kick;
                an illegal result is undone.
Couch cart P2 driver (tempo-wt patch_cartridge_copro.py; couch flags DRROTFIX DRROTDIR DRDISTGATE
DRPROPH DRSLAM, 2 hooks/frame, both hooks write identical inputs):
  - control starts F0 frames after the new pill appears (the video's frame 0 = preview change); the
    driver pins the gravity counter during its 15-hook settle (freeze_pending, DRPENDBOUND), so gravity
    starts counting at G0 = 7|8 (fitted: silicon first natural drop - threshold = 7|8, n=246);
  - no answer yet (f < t_act): DRPROPH pulse if the spawn is on a throat ledge (min(fo3, fo4) <= 2):
    the deeper-fo side (ties LEFT) if its gate cells (rows 0-1 of col 2 / col 5) are free, else the
    other side, else none; 1 frame on / 1 off keyed to frame parity, held forced 0 so every on-frame is
    a fresh press edge (1 col / 2 f). Otherwise no button.
  - answer known (f >= t_act): rotate first (A or B per the shortest direction, held forced 0, one per
    frame), then steer the column: DISTGATE clamps the target to DIST_TABLE[free rows below the capsule
    across the [x..target] span] columns (surface-relative; y=0 -> 0), held continuously (DAS), and once
    aligned soft-drop (slam). t_act (answer latency) is SAMPLED from the empirical silicon distribution.
Game orientation <-> sim action variant: rot 0 = var 0 (H a,b), rot 2 = var 1 (H b,a), rot 3 = var 2
(V a top), rot 1 = var 3 (V b top) (bitexact-gate map a_o4 = var ^ 2, then the driver's {0:3,1:1,2:0,3:2}).

Policies (experiment arms): proph = "throat" (couch) | "brain" (pulse toward the brain's target side) |
None; prehold (carry the charge toward the target side through the lock when v >= 10); pulse (all column
moves by alternate-frame press edges, DISTGATE sized for it); distgate on/off.
"""
from __future__ import annotations

import os
import json
import random

ROWS, COLS = 16, 8
SPEED_TABLE = [0x45, 0x43, 0x41, 0x3F, 0x3D, 0x3B, 0x39, 0x37, 0x35, 0x33, 0x31, 0x2F, 0x2D, 0x2B, 0x29, 0x27,
               0x25, 0x23, 0x21, 0x1F, 0x1D, 0x1B, 0x19, 0x17, 0x15, 0x13, 0x12, 0x11, 0x10, 0x0F, 0x0E, 0x0D,
               0x0C, 0x0B, 0x0A, 0x09, 0x09, 0x08, 0x08, 0x07, 0x07, 0x06, 0x06, 0x05, 0x05, 0x05, 0x05, 0x05,
               0x05, 0x05, 0x05, 0x05, 0x05, 0x05, 0x05, 0x04, 0x04, 0x04, 0x04, 0x04, 0x03, 0x03, 0x03, 0x03,
               0x03, 0x02, 0x02, 0x02, 0x02, 0x02, 0x01, 0x01, 0x01, 0x01, 0x01, 0x01, 0x01, 0x01, 0x01, 0x01,
               0x00]
SPEED_BASE = {0: 0x0F, 1: 0x19, 2: 0x1F}          # LOW, MED, HI (baseSpeedSettingValue)
HOR_ACCEL, HOR_MAX = 16, 6                         # NTSC hor_accel_speed / hor_max_speed
RIGHT, LEFT, DOWN, BTN_B, BTN_A = 0x01, 0x02, 0x04, 0x40, 0x80
ROT_OF_VAR = {0: 0, 1: 2, 2: 3, 3: 1}
VAR_OF_ROT = {v: k for k, v in ROT_OF_VAR.items()}
F0 = 3                                             # first frame the ROM processes lateral input (DRPROPH moves at f3-4)
G0_CHOICES = (7, 8)                                # driver's settle pin (freeze_pending: 15 hooks, GRAV_P2 := 0)
                                                   # ends here; FITTED on silicon: first natural drop - thr = 7|8
                                                   # (mode, every speed band k=0..119, 7 couch games)


def table_threshold(pills_placed, speed=1):
    return SPEED_TABLE[SPEED_BASE[speed] + min(49, pills_placed // 10)]


def dist_table(dasedge=12, gravrow=30):
    t = [0 if y == 0 else max(1, min(7, (y * gravrow) // dasedge)) for y in range(16)]
    return t, max(1, next(i for i in range(16) if t[i] == max(t)))


def cells(x, row, rot):
    if rot % 2 == 0:
        return ((row, x), (row, x + 1))
    return ((row - 1, x), (row, x))               # vertical: (top, bottom); ROM Y = bottom


def valid(color, x, row, rot):
    for r, c in cells(x, row, rot):
        if c < 0 or c >= COLS or r >= ROWS:
            return False
        if r >= 0 and color[r][c] != 0:
            return False
    return True


def fo(color, c):
    for r in range(ROWS):
        if color[r][c] != 0:
            return r
    return ROWS


def proph_throat(color):
    """DRPROPH trigger (proph_trigger): None if no ledge, else 'L'/'R'/'-' (armed but both gates blocked)."""
    f3, f4 = fo(color, 3), fo(color, 4)
    if f3 > 2 and f4 > 2:
        return None
    gate_l = color[0][2] == 0 and color[1][2] == 0
    gate_r = color[0][5] == 0 and color[1][5] == 0
    if f4 > f3:                                    # right throat deeper
        return "R" if gate_r else ("L" if gate_l else "-")
    return "L" if gate_l else ("R" if gate_r else "-")


def target_side(var, col):
    """Which way the capsule must travel from spawn x=3 to reach the target column."""
    return "R" if col > 3 else ("L" if col < 3 else None)


# ---- empirical answer latency (frames from preview change to the driver's first action), silicon
_LAT = None
_LAT_ROT = None
NROT = {0: 0, 1: 2, 2: 1, 3: 1}                      # presses from spawn rot 0 to each target var (DRROTDIR)


def latency_by_rot(path=None):
    """POST-HOC SENSITIVITY (STEER1): first-lateral-move frame conditioned on how many rotation presses the
    silicon landing needed (medians 15 / 22 / 15 for 0 / 1 / 2). The pooled sampler (the pre-registered
    default) ignores that and rotates AFTER the sample, which is too slow for H and too fast for V targets."""
    global _LAT_ROT
    if _LAT_ROT is None:
        path = path or os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "couch_forensics",
                                    "cases_all_games.jsonl")
        out = {0: [], 1: [], 2: []}
        for l in open(path):
            q = json.loads(l)
            f = (q.get("video") or {}).get("first_lateral_f")
            if f is None or q.get("proph_dir") is not None or not q.get("verified", True):
                continue
            o, cols, a, b = q["actual"][0], tuple(q["actual"][2]), q["cur"][0], q["cur"][1]
            var = (0 if cols == (a, b) else 1) if o == "H" else (2 if cols == (a, b) else 3)
            out[NROT[var]].append(int(f))
        _LAT_ROT = {k: sorted(v) for k, v in out.items()}
    return _LAT_ROT


def latency_samples(path=None):
    global _LAT
    if _LAT is None:
        path = path or os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "couch_forensics",
                                    "cases_all_games.jsonl")
        xs = []
        for l in open(path):
            q = json.loads(l)
            f = (q.get("video") or {}).get("first_lateral_f")
            if f is not None and q.get("proph_dir") is None and q.get("verified", True):
                xs.append(int(f))
        _LAT = sorted(xs)
    return _LAT


class Steer:
    """Stateful per game (the ROM's horVelocity carries across pills)."""

    def __init__(self, proph="throat", prehold=False, pulse=False, distgate=True, speed=1, seed=0, tap_period=None,
                 lat=None, trace=False, lat_mode="pooled"):
        self.proph, self.prehold, self.pulse, self.distgate = proph, prehold, pulse, distgate
        self.lat_mode = lat_mode                     # "pooled" (pre-registered) | "byrot" (post-hoc sensitivity)
        self.hint_side = None                        # "plan" mode: side of the PREVIOUS search's ply-2 plan
        self.use_hint = False
        self.speed = speed
        # tap_period (STEER3): None = STEER1's alternate-frame pulse (parity-keyed); P = one fresh press every P
        # frames from the first steering frame. DISTGATE is sized to the tap rate (2 hooks/frame -> 2P hooks/col).
        self.tap_period = tap_period
        self.dtable, self.scancap = dist_table(dasedge=(2 * (tap_period or 2)) if pulse else 12)
        self.lat = lat if lat is not None else latency_samples()
        self.seed = seed
        self.trace = trace
        self.reset(seed)

    def reset(self, seed):
        self.seed = seed
        self.v = 0                                   # ROM horVelocity, carried across pills
        self.v_at_lock = 0
        self.stats = {"pills": 0, "exact": 0, "proph_fired": 0, "clamp_short": 0, "moved_off_target": 0,
                      "not_straight": 0, "frames": 0}

    # -------------------------------------------------------------------------------------------
    def _t_act(self, k, t_act=None, nrot=0):
        if t_act is not None:
            return int(t_act)
        rng = random.Random(self.seed * 1000003 + k * 7919 + 17)
        if self.lat_mode == "byrot":
            xs = latency_by_rot()[nrot]
            return xs[rng.randrange(len(xs))]
        return self.lat[rng.randrange(len(self.lat))]

    def _eff(self, color, x, row, tcol):
        if not self.distgate or tcol == x:
            return tcol
        Y = min(ROWS - 1 - row, 15)
        n = min(Y, self.scancap)
        lo, hi = min(x, tcol), max(x, tcol)
        fall = 0
        r = row + 1
        for i in range(n):
            if all(color[r + i][c] == 0 for c in range(lo, hi + 1)):
                fall += 1
            else:
                break
        b = self.dtable[fall]
        if tcol < x:
            return max(tcol, max(0, x - b))
        return min(tcol, min(7, x + b))

    def execute(self, color, target_action, k, t_act=None, phase=None):
        """Simulate one pill. color: 16x8 nested list/array of the settled board (0 = empty).
        target_action: the brain's action (var*8 + col). k: pills already placed this game (speed).
        Returns dict(var, col, row_cells, info). row_cells = ((r0,c0),(r1,c1)) in sim convention
        (H: left,right; V: top,bottom)."""
        tvar, tcol = target_action // 8, target_action % 8
        trot = ROT_OF_VAR[tvar]
        thr = table_threshold(k, self.speed)
        nrot = NROT[tvar]
        ta = self._t_act(k, t_act, nrot)
        # byrot: ta is the FIRST LATERAL frame (as measured); the answer (rotation start) is nrot frames earlier.
        # pooled (pre-registered): ta is the answer; rotation follows it, then lateral.
        t_ans = max(F0, ta - nrot) if self.lat_mode == "byrot" else ta
        rng = random.Random(self.seed * 1000003 + k * 7919 + 29)
        ph = rng.randrange(2) if phase is None else phase
        g0 = G0_CHOICES[rng.randrange(2)] if phase is None else G0_CHOICES[phase]
        # PROPH arming (at the new-pill edge, on the settled board)
        pd = None
        armed = proph_throat(color)
        if armed is not None and self.proph is not None:
            if self.proph == "throat":
                pd = armed if armed in ("L", "R") else None
            elif self.proph in ("brain", "plan"):
                side = self.hint_side if self.proph == "plan" else target_side(tvar, tcol)
                if side == "L" and color[0][2] == 0 and color[1][2] == 0:
                    pd = "L"
                elif side == "R" and color[0][5] == 0 and color[1][5] == 0:
                    pd = "R"
        # pre-hold (carry the charge toward the target side through the lock); only when it pays
        pre = None
        if self.prehold and pd is None and self.v_at_lock >= 10:
            pre = self.hint_side if self.use_hint else target_side(tvar, tcol)
        x, row, rot = 3, 0, 0
        v = self.v
        spd = 0
        prev_held = (RIGHT if pre == "R" else LEFT) if pre else 0   # held since the lock: no edge at spawn
        clamped_ever = False
        lock_f = None
        last_tap = None
        tr = [] if self.trace else None
        for f in range(F0, F0 + 4000):
            # ---------------- driver decision (from last frame's state) ----------------
            raw, clear = 0, False
            if f < t_ans:
                if pd is not None:
                    clear = True
                    if (f + ph) % 2 == 0:
                        raw = RIGHT if pd == "R" else LEFT
                elif pre is not None and ((pre == "R" and x < 7) or (pre == "L" and x > 0)) and \
                        (self.use_hint or x != tcol):
                    raw = RIGHT if pre == "R" else LEFT  # plan mode: the driver doesn't know tcol yet
            elif rot != trot:
                clear = True
                delta = (trot - rot) & 3
                raw = BTN_B if delta == 1 else BTN_A
            elif f < ta:
                raw = 0                                    # byrot: rotated early, lateral waits for the gate
            else:
                eff = self._eff(color, x, row, tcol)
                if eff != tcol:
                    clamped_ever = True
                if x == eff:
                    raw = DOWN
                else:
                    d = RIGHT if x < eff else LEFT
                    if self.pulse and self.tap_period is not None:
                        clear = True
                        if last_tap is None or f - last_tap >= self.tap_period:
                            raw = d; last_tap = f
                        else:
                            raw = 0
                    elif self.pulse:
                        clear = True
                        raw = d if (f + ph) % 2 == 0 else 0
                    else:
                        raw = d
            held_prev = 0 if clear else prev_held
            pressed = raw & ~held_prev
            held = raw
            prev_held = held
            # ---------------- ROM: checkYMove ----------------
            lower = False
            if (f + ph) % 2 == 1 and (held & 0x0F) == DOWN:
                lower = True
            elif f >= g0:
                spd += 1
                if spd > thr:
                    lower = True
            if lower:
                spd = 0
                if valid(color, x, row + 1, rot):
                    row += 1
                else:
                    lock_f = f
                    break
            # ---------------- ROM: checkXMove ----------------
            if pressed & (LEFT | RIGHT) or held & (LEFT | RIGHT):
                go = True
                if not (pressed & (LEFT | RIGHT)):
                    v += 1
                    if v < HOR_ACCEL:
                        go = False
                    else:
                        v = HOR_ACCEL - HOR_MAX
                else:
                    v = 0
                if go:
                    if held & RIGHT:
                        if x != (COLS - 2 + (rot & 1)):
                            if valid(color, x + 1, row, rot):
                                x += 1
                            else:
                                v = HOR_ACCEL - 1
                    if held & LEFT:
                        if x != 0:
                            if valid(color, x - 1, row, rot):
                                x -= 1
                            else:
                                v = HOR_ACCEL - 1
            # ---------------- ROM: checkRotate ----------------
            for btn, dr in ((BTN_A, -1), (BTN_B, 1)):
                if pressed & btn:
                    r0, x0 = rot, x
                    rot = (rot + dr) & 3
                    if rot % 2 == 0:
                        if not valid(color, x, row, rot):
                            x -= 1
                            if not valid(color, x, row, rot):
                                rot, x = r0, x0
                        elif held & LEFT and valid(color, x - 1, row, rot):
                            x -= 1
                    elif not valid(color, x, row, rot):
                        rot, x = r0, x0
            if tr is not None:
                tr.append((f, x, row, rot, v, raw))
        self.v = v
        self.v_at_lock = v
        var = VAR_OF_ROT[rot]
        cs = cells(x, row, rot)
        st = self.stats
        st["pills"] += 1
        st["frames"] += (lock_f or 0)
        exact = (var == tvar and x == tcol)
        st["exact"] += int(exact)
        st["proph_fired"] += int(pd is not None)
        if not exact:
            st["moved_off_target"] += 1
            if clamped_ever and pd is None:
                st["clamp_short"] += 1
        return {"var": var, "col": x, "cells": cs, "lock_f": lock_f, "t_act": ta, "proph": pd, "armed": armed,
                "clamped": clamped_ever, "exact": exact, "trace": tr}


def straight_cells(color, var, col):
    """Sim resting cells for (var, col) as FaithfulBoard.resting_position would return, or None."""
    top = lambda c: next((r for r in range(ROWS) if color[r][c] != 0), ROWS)
    if var in (0, 1):
        if col < 0 or col + 1 >= COLS:
            return None
        r = min(top(col), top(col + 1)) - 1
        return None if r < 0 else ((r, col), (r, col + 1))
    if col < 0 or col >= COLS:
        return None
    b = top(col) - 1
    return None if b - 1 < 0 else ((b - 1, col), (b, col))


class forced_landing:
    """Context manager: every resting_position() call on boards of env.board's class returns `cs` (the executed
    landing cells) for the duration. Used so probe_placement's clone AND env.step both see a non-straight
    landing. A vertical capsule with its top half above the field (row -1) is not representable: None."""

    def __init__(self, board, cs):
        self.cls, self.cs = type(board), cs

    def __enter__(self):
        self.orig = self.cls.resting_position
        cs = self.cs
        self.cls.resting_position = lambda self_, pill, o, c: (cs if cs[0][0] >= 0 else None)
        return self

    def __exit__(self, *exc):
        self.cls.resting_position = self.orig
        return False


def is_straight(color, res):
    sc = straight_cells(color, res["var"], res["col"])
    return sc is not None and tuple(map(tuple, sc)) == tuple(map(tuple, res["cells"]))


def place_executed(env, res):
    """Apply an executed landing through env.step so all env bookkeeping (resolve, counters, top-out,
    pill advance) stays identical. If the landing is the straight drop of (var, col) this is exactly
    env.step(var*8+col); otherwise the landing cells are injected for this one step."""
    var, col, cs = res["var"], res["col"], res["cells"]
    b = env.board
    color = b.color
    sc = straight_cells(color, var, col)
    a = var * 8 + col
    if sc is not None and tuple(map(tuple, sc)) == tuple(map(tuple, cs)):
        return env.step(a), True
    # non-straight landing (under an overhang / locked high): inject the exact cells for this step.
    # A vertical capsule locked with its top half above the field (row -1) is not representable in the
    # sim board: resting_position -> None -> env.step treats it as illegal = top-out (conservative, rare).
    b.resting_position = lambda pill, o, c, _cs=cs: (_cs if _cs[0][0] >= 0 else None)
    try:
        out = env.step(a)
    finally:
        del b.resting_position
    return out, False
