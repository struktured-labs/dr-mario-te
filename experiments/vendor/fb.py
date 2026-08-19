#!/usr/bin/env python3
"""Flat-list clone of drmario.faithful_game.FaithfulBoard mechanics.

Same rules, ~5x faster (no numpy scalar indexing), so a plan search can afford
thousands of place+resolve calls.  `difftest()` proves cell-for-cell equality
with the real engine on random boards -- run it before trusting anything here.
"""
from __future__ import annotations

ROWS, COLS, NCELL = 16, 8, 128
EMPTY = 0
LINK_NONE, LINK_UP, LINK_DOWN, LINK_LEFT, LINK_RIGHT = 0, 1, 2, 3, 4
_DELTA = {LINK_UP: (-1, 0), LINK_DOWN: (1, 0), LINK_LEFT: (0, -1), LINK_RIGHT: (0, 1)}
SPAWN_COLS = (3, 4)
GLYPH = {0: ".", 1: "R", 2: "Y", 3: "B"}


class FB:
    __slots__ = ("col", "vir", "lnk")

    def __init__(self, col=None, vir=None, lnk=None):
        self.col = list(col) if col is not None else [0] * NCELL
        self.vir = list(vir) if vir is not None else [0] * NCELL
        self.lnk = list(lnk) if lnk is not None else [0] * NCELL

    # ------------------------------------------------------------------ basics
    def clone(self):
        return FB(self.col, self.vir, self.lnk)

    def key(self):
        return (bytes(self.col), bytes(self.vir), bytes(self.lnk))

    def virus_count(self):
        return sum(self.vir)

    def virus_cells(self):
        return [i for i in range(NCELL) if self.vir[i]]

    def top_occ(self, c):
        col = self.col
        for r in range(ROWS):
            if col[r * COLS + c]:
                return r
        return ROWS

    def spawn_blocked(self):
        return self.col[3] != 0 or self.col[4] != 0

    def ascii(self, mark=()):
        out = []
        for r in range(ROWS):
            row = []
            for c in range(COLS):
                i = r * COLS + c
                ch = GLYPH[self.col[i]]
                if self.vir[i]:
                    ch = ch.lower()
                if i in mark:
                    ch = "*" if ch == "." else ch
                row.append(ch)
            out.append("".join(row))
        return "\n".join(out)

    @staticmethod
    def from_lists(color, virus, link):
        return FB(color, virus, link)

    @staticmethod
    def from_board(b):
        return FB(b.color.reshape(-1).astype(int).tolist(),
                  b.is_virus.reshape(-1).astype(int).tolist(),
                  b.link.reshape(-1).astype(int).tolist())

    # --------------------------------------------------------------- placement
    def resting(self, orient, c):
        """orient 0 = horizontal (c, c+1), 1 = vertical (top, bottom) in c."""
        if orient == 0:
            if c < 0 or c + 1 >= COLS:
                return None
            t0, t1 = self.top_occ(c), self.top_occ(c + 1)
            r = (t0 if t0 < t1 else t1) - 1
            if r < 0:
                return None
            return (r, c, r, c + 1)
        if c < 0 or c >= COLS:
            return None
        bot = self.top_occ(c) - 1
        top = bot - 1
        if top < 0:
            return None
        return (top, c, bot, c)

    def place_at(self, r0, c0, x, r1, c1, y):
        """Lock a pill with half `x` at (r0,c0) and half `y` at (r1,c1).
        cell0 = left (horizontal) or top (vertical)."""
        i0, i1 = r0 * COLS + c0, r1 * COLS + c1
        self.col[i0] = x
        self.col[i1] = y
        if r0 == r1:
            self.lnk[i0] = LINK_RIGHT
            self.lnk[i1] = LINK_LEFT
        else:
            self.lnk[i0] = LINK_DOWN
            self.lnk[i1] = LINK_UP
        self.vir[i0] = 0
        self.vir[i1] = 0

    # ------------------------------------------------------------------ clears
    def _find_clears(self):
        col = self.col
        mask = [0] * NCELL
        for r in range(ROWS):
            base = r * COLS
            c = 0
            while c < COLS:
                v = col[base + c]
                if v == 0:
                    c += 1
                    continue
                c2 = c
                while c2 < COLS and col[base + c2] == v:
                    c2 += 1
                if c2 - c >= 4:
                    for k in range(c, c2):
                        mask[base + k] = 1
                c = c2
        for c in range(COLS):
            r = 0
            while r < ROWS:
                v = col[r * COLS + c]
                if v == 0:
                    r += 1
                    continue
                r2 = r
                while r2 < ROWS and col[r2 * COLS + c] == v:
                    r2 += 1
                if r2 - r >= 4:
                    for k in range(r, r2):
                        mask[k * COLS + c] = 1
                r = r2
        return mask

    def _apply_clear(self, mask):
        col, vir, lnk = self.col, self.vir, self.lnk
        nv = 0
        for i in range(NCELL):
            if not mask[i]:
                continue
            if vir[i]:
                nv += 1
            lk = lnk[i]
            if lk:
                dr, dc = _DELTA[lk]
                r, c = divmod(i, COLS)
                pr, pc = r + dr, c + dc
                if 0 <= pr < ROWS and 0 <= pc < COLS and not mask[pr * COLS + pc]:
                    lnk[pr * COLS + pc] = LINK_NONE
        for i in range(NCELL):
            if mask[i]:
                col[i] = 0
                vir[i] = 0
                lnk[i] = LINK_NONE
        return nv

    # ----------------------------------------------------------------- gravity
    def _bodies(self):
        col, vir, lnk = self.col, self.vir, self.lnk
        seen = [False] * NCELL
        out = []
        for i in range(NCELL):
            if col[i] == 0 or vir[i] or seen[i]:
                continue
            lk = lnk[i]
            if lk == LINK_NONE:
                seen[i] = True
                out.append((i, -1))
                continue
            dr, dc = _DELTA[lk]
            r, c = divmod(i, COLS)
            pr, pc = r + dr, c + dc
            if 0 <= pr < ROWS and 0 <= pc < COLS and not seen[pr * COLS + pc]:
                j = pr * COLS + pc
                seen[i] = True
                seen[j] = True
                out.append((i, j))
            else:
                seen[i] = True
                out.append((i, -1))
        return out

    def _can_fall(self, b):
        col = self.col
        i, j = b
        for k in (i, j):
            if k < 0:
                continue
            n = k + COLS
            if n >= NCELL:
                return False
            if n != i and n != j and col[n] != 0:
                return False
        return True

    def _move_down(self, b):
        col, vir, lnk = self.col, self.vir, self.lnk
        cells = [(k, col[k], vir[k], lnk[k]) for k in b if k >= 0]
        for k, *_ in cells:
            col[k] = 0
            vir[k] = 0
            lnk[k] = LINK_NONE
        for k, cv, vv, lv in cells:
            n = k + COLS
            col[n] = cv
            vir[n] = vv
            lnk[n] = lv

    def _apply_gravity(self):
        while True:
            bodies = self._bodies()
            bodies.sort(key=lambda b: max(b[0], b[1]) // COLS, reverse=True)
            moved = False
            for b in bodies:
                if self._can_fall(b):
                    self._move_down(b)
                    moved = True
            if not moved:
                break

    # ----------------------------------------------------------------- resolve
    def resolve(self):
        total = vtot = chain = 0
        while True:
            mask = self._find_clears()
            n = sum(mask)
            if n == 0:
                break
            chain += 1
            total += n
            vtot += self._apply_clear(mask)
            self._apply_gravity()
        return total, vtot, chain


# ------------------------------------------------------------------ difftest
def difftest(n=400, seed=11, verbose=True):
    """FB must agree with FaithfulBoard cell-for-cell after place + resolve."""
    import sys, os
    import numpy as np
    SIM = "/home/struktured/projects/dr_mario_rl/.claude/worktrees/faithful-sim/src"
    if SIM not in sys.path:
        sys.path.insert(0, SIM)
    from drmario.faithful_game import FaithfulBoard, Pill, ORIENT_H, ORIENT_V

    rng = np.random.default_rng(seed)
    bad = 0
    checked = 0
    for t in range(n):
        b = FaithfulBoard(ROWS, COLS, rng=rng)
        b.place_viruses(int(rng.integers(4, 20)))
        # settle some random pills to build links / overhangs
        for _ in range(int(rng.integers(0, 45))):
            o = ORIENT_H if rng.random() < 0.5 else ORIENT_V
            c = int(rng.integers(0, COLS))
            p = Pill(int(rng.integers(1, 4)), int(rng.integers(1, 4)))
            if b.place_pill(p, o, c):
                b.resolve()
        for _ in range(6):
            o = ORIENT_H if rng.random() < 0.5 else ORIENT_V
            c = int(rng.integers(0, COLS))
            pa, pb = int(rng.integers(1, 4)), int(rng.integers(1, 4))
            ref = b.clone()
            cells = ref.resting_position(Pill(pa, pb), o, c)
            if cells is None:
                continue
            ref.place_pill(Pill(pa, pb), o, c)
            r_res = ref.resolve()
            f = FB.from_board(b)
            (r0, c0), (r1, c1) = cells
            f.place_at(r0, c0, pa, r1, c1, pb)
            f_res = f.resolve()
            checked += 1
            same = (list(ref.color.reshape(-1).astype(int)) == f.col
                    and list(ref.is_virus.reshape(-1).astype(int)) == f.vir
                    and list(ref.link.reshape(-1).astype(int)) == f.lnk
                    and tuple(r_res) == tuple(f_res))
            if not same:
                bad += 1
                if verbose and bad <= 2:
                    print("MISMATCH", (o, c, pa, pb), r_res, f_res)
                    print(ref.ascii())
                    print("--")
                    print(f.ascii())
    if verbose:
        print(f"difftest: {checked} place+resolve compared, {bad} mismatches")
    return bad == 0, checked


if __name__ == "__main__":
    ok, n = difftest()
    raise SystemExit(0 if ok else 1)
