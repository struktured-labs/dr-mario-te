#!/usr/bin/env python3
"""Owner's TWO-PILL JOINT DIG tactic (task #96) — detector.

    "a common tactic to clear crappy columns is you look at what you have now and what
     pill is next, if they clear the next cell from that bad column together and you can
     manage to fit them in time you go for it."

The search already SEES the preview, so this line is inside its tree. The hypothesis under
test is that the EVAL declines the setup half: a pill parked on a dangerous column to enable
next turn's clear scores badly on the current vocabulary.

WHAT COUNTS AS A DIG -- and why the primary signal is viruses.
  Gravity in Dr. Mario is vertical only, so a cell never leaves its column except by being
  cleared. VIRUSES additionally never move at all. Therefore
      viruses_in_D(before) - viruses_in_D(after)
  is an EXACT count of viruses cleared out of column D, with no gravity ambiguity anywhere.
  That is the primary signal (`vdig`).
  The secondary signal (`odig`) is "occupancy of D strictly decreased". It is deliberately
  CONSERVATIVE: placing the capsule into D can add up to 2 cells, so a strict decrease
  implies pre-existing material was cleared, while the converse does not hold. It never
  false-positives; it can under-count. Both are reported; neither is inferred from the other.

WHAT COUNTS AS *JOINT*. A pair (p1, p2) is a joint dig iff
      dig(p1 alone) == 0   AND   dig(p1 then p2) > 0
i.e. the first placement pays nothing on the danger column and the second cashes it. That is
precisely the owner's "together". A line where p1 already digs is a SINGLE dig and is counted
separately -- conflating the two is the easiest way to manufacture a fake availability rate.

DANGER COLUMN, three definitions from the task, all computed (no arbitrary pick):
  "tall"    the tallest column, if its height >= H_MIN (default 6)
  "buried"  a column holding a virus with >=1 non-virus cell above it (junk over virus)
  "hit"     caller-supplied (the column a garbage volley landed in); pass explicitly

Placement enumeration is variant 0..3 x column 0..7; `_expand_chain` returns ok=0 for
illegal ones. variant<2 = horizontal (cells at c, c+1), variant>=2 = vertical (both at c).
Colours are 1-BASED here, matching the `col` plane (0 = empty) -- NOT the copro mailbox's
0-based convention.
"""
from __future__ import annotations

import sys

import numpy as np

for _p in ("/home/struktured/projects/dr_mario_rl/tmp/combo_term",
           "/home/struktured/projects/dr_mario_rl/tmp/endgame",
           "/home/struktured/projects/dr_mario_rl/.claude/worktrees/faithful-sim/src"):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import cascade_chain_x as C          # noqa: E402
from fast_sim_x import NCELL, COLS   # noqa: E402

ROWS = NCELL // COLS
H_MIN_DEFAULT = 6
VARIANTS = (0, 1, 2, 3)


def warmup():
    C.warmup_chain()


def _col_cells(col, c):
    return [r for r in range(ROWS) if col[r * COLS + c] != 0]


def col_height(col, c):
    """ROWS - topmost occupied row; 0 if empty."""
    for r in range(ROWS):
        if col[r * COLS + c] != 0:
            return ROWS - r
    return 0


def col_occupancy(col, c):
    return sum(1 for r in range(ROWS) if col[r * COLS + c] != 0)


def col_viruses(col, vir, c):
    return sum(1 for r in range(ROWS) if col[r * COLS + c] != 0 and vir[r * COLS + c])


def danger_columns(col, vir, h_min=H_MIN_DEFAULT):
    """-> dict(mode -> [columns]). See the module docstring for the definitions."""
    heights = [col_height(col, c) for c in range(COLS)]
    tall = []
    hmax = max(heights)
    if hmax >= h_min:
        tall = [c for c in range(COLS) if heights[c] == hmax]
    buried = []
    for c in range(COLS):
        cells = _col_cells(col, c)
        for r in cells:
            if vir[r * COLS + c]:
                if any(rr < r and col[rr * COLS + c] != 0 and not vir[rr * COLS + c]
                       for rr in range(ROWS)):
                    buried.append(c)
                    break
    return {"tall": tall, "buried": buried}


def _added_in(variant, column, d):
    if variant < 2:
        return (1 if column == d else 0) + (1 if column + 1 == d else 0)
    return 2 if column == d else 0


class Scanner:
    """Reusable scratch so a corpus pass does not reallocate 128-byte planes per candidate."""

    def __init__(self):
        self.b1 = tuple(np.empty(NCELL, np.int8) for _ in range(3))
        self.b2 = tuple(np.empty(NCELL, np.int8) for _ in range(3))
        # b3 is RESERVED for callers evaluating a specific placement of their own. scan()
        # reuses b1/b2 on every candidate, so a caller that stashed a result in b1 before
        # calling scan() would read back the scanner's last candidate instead. That bug was
        # live in the first corpus pass and silently produced a 0% take-rate.
        self.b3 = tuple(np.empty(NCELL, np.int8) for _ in range(3))
        self.mk = np.empty(NCELL, np.int8)

    def place(self, col, vir, lnk, variant, column, pa, pb, out):
        ok, nv, cells, ch = C._expand_chain(col, vir, lnk, variant, column, pa, pb,
                                            out[0], out[1], out[2], self.mk, 0)
        return ok, nv, cells, ch

    def legal(self, col, vir, lnk, pa, pb):
        out = []
        for v in VARIANTS:
            for c in range(COLS):
                ok, _, _, _ = self.place(col, vir, lnk, v, c, pa, pb, self.b1)
                if ok:
                    out.append((v, c))
        return out

    def scan(self, col, vir, lnk, cur, nxt, d):
        """One decision, one danger column d. Returns a dict of availability facts.

        `cur`/`nxt` are (a, b) 1-based colour pairs.
        """
        v0 = col_viruses(col, vir, d)
        o0 = col_occupancy(col, d)
        single_v = single_o = 0
        joint_v = joint_o = 0
        wit_v = wit_o = None
        setups_v = set()          # p1 that are the setup half of SOME virus-joint line
        setups_o = set()
        for v1 in VARIANTS:
            for c1 in range(COLS):
                ok, _, _, _ = self.place(col, vir, lnk, v1, c1, cur[0], cur[1], self.b1)
                if not ok:
                    continue
                a1, b1c, l1 = self.b1
                v1c = v0 - col_viruses(a1, b1c, d)
                o1c = (o0 + _added_in(v1, c1, d)) - col_occupancy(a1, d)
                if v1c > 0:
                    single_v += 1
                    if wit_v is None:
                        wit_v = ("single", (v1, c1), None)
                if o1c > 0:
                    single_o += 1
                    if wit_o is None:
                        wit_o = ("single", (v1, c1), None)
                # JOINT requires the first half to pay NOTHING on d
                if v1c > 0 and o1c > 0:
                    continue
                vA = col_viruses(a1, b1c, d)
                oA = col_occupancy(a1, d)
                for v2 in VARIANTS:
                    for c2 in range(COLS):
                        ok2, _, _, _ = self.place(a1, b1c, l1, v2, c2, nxt[0], nxt[1], self.b2)
                        if not ok2:
                            continue
                        a2, b2c, _ = self.b2
                        v2c = vA - col_viruses(a2, b2c, d)
                        o2c = (oA + _added_in(v2, c2, d)) - col_occupancy(a2, d)
                        if v1c == 0 and v2c > 0:
                            joint_v += 1
                            setups_v.add((v1, c1))
                            if wit_v is None or wit_v[0] == "single":
                                if wit_v is None:
                                    wit_v = ("joint", (v1, c1), (v2, c2))
                        if o1c == 0 and o2c > 0:
                            joint_o += 1
                            setups_o.add((v1, c1))
                            if wit_o is None:
                                wit_o = ("joint", (v1, c1), (v2, c2))
        return dict(
            d=d, v0=v0, o0=o0,
            single_vdig=single_v, joint_vdig=joint_v,
            single_odig=single_o, joint_odig=joint_o,
            vdig_avail=(single_v > 0 or joint_v > 0),
            joint_v_only=(joint_v > 0 and single_v == 0),
            joint_o_only=(joint_o > 0 and single_o == 0),
            setups_v=setups_v, setups_o=setups_o,
            witness_v=wit_v, witness_o=wit_o,
        )


# ---------------------------------------------------------------------------------------
# P0 -- the owner's canonical instance of the joint dig (task #96, second refinement):
#   "my most common use of it is a monocolor + dual color of which one is same as mono.
#    that guarantees a clear if you can vert the mono."
#
# cur = (X,X) mono; nxt contains X; the danger column's EXPOSED TOP cell is colour X and
# the column has >= 2 free rows. Vert the mono onto it -> 3 X stacked in that column; the
# KNOWN next pill delivers the 4th -> a deterministic vertical clear that removes the bad
# column's top cell, with a one-pill risk window and the off-colour half disposed of by the
# clear itself.
#
# ★ It is decidable at the ROOT: no search, just a pattern match on (cur, nxt, board). That
# is what makes a systematic decline diagnostic rather than merely suboptimal.
# ★ It is nonetheless VERIFIED by simulation here, never asserted from the pattern alone --
# the pattern is the cheap filter, `_expand_chain` is the judge. A pattern that "should"
# clear but does not (an interfering horizontal match, a cascade, a colour I mis-read) is
# counted as not-P0.
# ⚠ ASSUMPTION: nav-reachability is NOT modelled. The fast sim lets any column be reached,
# exactly as the champion's own action space does, so P0 availability here is an upper
# bound on what a nav-constrained cart could execute.
# ---------------------------------------------------------------------------------------

def top_row(col, c):
    """Row index of the topmost occupied cell in column c, or None if empty."""
    for r in range(ROWS):
        if col[r * COLS + c] != 0:
            return r
    return None


def p0_precondition(col, cur, nxt, d):
    """Cheap pattern filter. Returns X (the mono colour) or None."""
    if cur[0] != cur[1]:
        return None
    x = cur[0]
    if nxt[0] != x and nxt[1] != x:
        return None
    t = top_row(col, d)
    if t is None or t < 2:                 # need the column occupied and >= 2 free rows
        return None
    if col[t * COLS + d] != x:             # exposed top cell must BE the mono colour
        return None
    return x


class P0Scanner:
    """Verifies a P0 line end to end. Shares Scanner's kernel discipline (own buffers)."""

    def __init__(self):
        self.a = tuple(np.empty(NCELL, np.int8) for _ in range(3))
        self.b = tuple(np.empty(NCELL, np.int8) for _ in range(3))
        self.mk = np.empty(NCELL, np.int8)

    def _place(self, col, vir, lnk, variant, column, pa, pb, out):
        return C._expand_chain(col, vir, lnk, variant, column, pa, pb,
                               out[0], out[1], out[2], self.mk, 0)

    def check(self, col, vir, lnk, cur, nxt, d):
        """-> None, or a dict describing the verified P0 line."""
        x = p0_precondition(col, cur, nxt, d)
        if x is None:
            return None
        v0 = col_viruses(col, vir, d)
        o0 = col_occupancy(col, d)
        # step 1: vert the mono onto d. Mono => variants 2 and 3 are identical; use 2.
        ok, _, cells1, _ = self._place(col, vir, lnk, 2, d, cur[0], cur[1], self.a)
        if not ok or cells1 != 0:
            return None                      # must not clear yet -- that would be a SINGLE dig
        a1, v1, l1 = self.a
        # step 2: deliver the next pill's X half onto d. Vertical with X DOWN is the
        # canonical delivery; variant 2 puts pa on top and pb below, so X must be pb.
        for variant, (pa, pb) in ((2, (nxt[0], nxt[1])), (3, (nxt[1], nxt[0]))):
            if pb != x:
                continue
            ok2, nv2, cells2, _ = self._place(a1, v1, l1, variant, d, pa, pb, self.b)
            if not ok2 or cells2 == 0:
                continue
            a2, v2p, _ = self.b
            vdug = v0 - col_viruses(a2, v2p, d)
            odug = (o0 + 4) - col_occupancy(a2, d)     # 2 mono cells + 2 next-pill cells
            if odug > 0:
                return dict(x=x, d=d, setup=(2, d), cash=(variant, d),
                            vdug=vdug, odug=odug, cleared=cells2, top_was_virus=bool(
                                vir[top_row(col, d) * COLS + d]))
        return None
