"""Faithful Dr. Mario rules engine.

This implements the *actual* NES Dr. Mario mechanics, in contrast to the toy
``game.py`` (which used 4-connected flood-fill matching). The differences that
matter for a transferable agent:

  * Matching is **4+ in a row OR column**, never diagonal / flood-fill.
  * Viruses are **immovable**; only capsule (pill) halves fall under gravity.
  * Gravity is **rigid-body**: a still-linked pill pair falls together; a half
    whose partner was cleared becomes a loose single and falls alone.
  * Clears cascade: after gravity settles, re-check for new lines (combos).
  * Win = all viruses cleared. Loss = the spawn cells are blocked.

Colors are 1=red, 2=yellow, 3=blue (0 = empty). This is mechanics-faithful, not
byte-for-byte RNG-identical to the NES (pill/virus RNG is uniform here); that is
sufficient for training a transferable strategic policy and is validated against
the real ROM separately.
"""
from __future__ import annotations

import numpy as np
from dataclasses import dataclass

# Cell colors
EMPTY = 0
RED = 1
YELLOW = 2
BLUE = 3
COLORS = (RED, YELLOW, BLUE)

# link[] codes: which direction this cell's pill partner lies (0 = single/none)
LINK_NONE = 0
LINK_UP = 1
LINK_DOWN = 2
LINK_LEFT = 3
LINK_RIGHT = 4

_OPP = {LINK_UP: LINK_DOWN, LINK_DOWN: LINK_UP, LINK_LEFT: LINK_RIGHT, LINK_RIGHT: LINK_LEFT}
_DELTA = {LINK_UP: (-1, 0), LINK_DOWN: (1, 0), LINK_LEFT: (0, -1), LINK_RIGHT: (0, 1)}

# Orientation codes for a placed pill
ORIENT_H = 0   # horizontal: colorA at (r, c),   colorB at (r, c+1)
ORIENT_V = 1   # vertical:   colorA at (r, c),   colorB at (r+1, c)  (A on top)


@dataclass
class Pill:
    """The active capsule: two halves with (possibly distinct) colors."""
    a: int  # primary half color
    b: int  # secondary half color


class FaithfulBoard:
    def __init__(self, rows: int = 16, cols: int = 8, rng=None):
        self.rows = rows
        self.cols = cols
        self.rng = rng or np.random.default_rng()
        self.color = np.zeros((rows, cols), dtype=np.int8)
        self.is_virus = np.zeros((rows, cols), dtype=bool)
        self.link = np.zeros((rows, cols), dtype=np.int8)

    # ------------------------------------------------------------------ setup
    def clone(self) -> "FaithfulBoard":
        b = FaithfulBoard(self.rows, self.cols, self.rng)
        b.color = self.color.copy()
        b.is_virus = self.is_virus.copy()
        b.link = self.link.copy()
        return b

    def virus_count(self) -> int:
        return int(self.is_virus.sum())

    def virus_counts_by_color(self) -> dict:
        return {c: int(np.sum(self.is_virus & (self.color == c))) for c in COLORS}

    def clear_readiness(self) -> float:
        """How close the viruses are to being cleared.

        For each virus, take the longest same-color contiguous run through it in
        its row OR column, and accumulate run_len**2. A virus sitting in a run of
        3 (one cell from a clearing line of 4) contributes far more than an
        isolated one, so maximizing this rewards setting up virus clears -- a much
        more directional signal than counting generic "near-lines".
        """
        total = 0.0
        rs, cs = np.where(self.is_virus)
        for r, c in zip(rs, cs):
            color = self.color[r, c]
            # horizontal run length through (r,c)
            hr = 1
            cc = c - 1
            while cc >= 0 and self.color[r, cc] == color:
                hr += 1; cc -= 1
            cc = c + 1
            while cc < self.cols and self.color[r, cc] == color:
                hr += 1; cc += 1
            # vertical run length through (r,c)
            vr = 1
            rr = r - 1
            while rr >= 0 and self.color[rr, c] == color:
                vr += 1; rr -= 1
            rr = r + 1
            while rr < self.rows and self.color[rr, c] == color:
                vr += 1; rr += 1
            total += float(max(hr, vr) ** 2)
        return total

    def clear_readiness_ext(self) -> float:
        """Extendability-aware clear_readiness: a direction only counts if its line can
        still geometrically reach 4 (contiguous span of same-color-or-EMPTY cells through
        the virus >= 4). Dead directions contribute 0, so building 3-stacks that can never
        complete earns nothing, and killing a virus's last viable line costs its run^2."""
        total = 0.0
        rs, cs = np.where(self.is_virus)
        for r, c in zip(rs, cs):
            color = self.color[r, c]
            # horizontal run + span
            hr = 1; cc = c - 1
            while cc >= 0 and self.color[r, cc] == color:
                hr += 1; cc -= 1
            span_lo = cc
            while span_lo >= 0 and self.color[r, span_lo] in (0, color):
                span_lo -= 1
            cc = c + 1
            while cc < self.cols and self.color[r, cc] == color:
                hr += 1; cc += 1
            span_hi = cc
            while span_hi < self.cols and self.color[r, span_hi] in (0, color):
                span_hi += 1
            h_ok = (span_hi - span_lo - 1) >= 4
            # vertical run + span
            vr = 1; rr = r - 1
            while rr >= 0 and self.color[rr, c] == color:
                vr += 1; rr -= 1
            vspan_lo = rr
            while vspan_lo >= 0 and self.color[vspan_lo, c] in (0, color):
                vspan_lo -= 1
            rr = r + 1
            while rr < self.rows and self.color[rr, c] == color:
                vr += 1; rr += 1
            vspan_hi = rr
            while vspan_hi < self.rows and self.color[vspan_hi, c] in (0, color):
                vspan_hi += 1
            v_ok = (vspan_hi - vspan_lo - 1) >= 4
            best = max(hr * hr if h_ok else 0, vr * vr if v_ok else 0)
            total += float(best)
        return total

    def clear_readiness_soft(self) -> float:
        """Like clear_readiness_ext but dead directions score run (linear) instead of 0:
        capped runs keep some retention value (spans can reopen after nearby clears)."""
        total = 0.0
        rs, cs = np.where(self.is_virus)
        for r, c in zip(rs, cs):
            color = self.color[r, c]
            hr = 1; cc = c - 1
            while cc >= 0 and self.color[r, cc] == color:
                hr += 1; cc -= 1
            lo = cc
            while lo >= 0 and self.color[r, lo] in (0, color):
                lo -= 1
            cc = c + 1
            while cc < self.cols and self.color[r, cc] == color:
                hr += 1; cc += 1
            hi = cc
            while hi < self.cols and self.color[r, hi] in (0, color):
                hi += 1
            h_ok = (hi - lo - 1) >= 4
            vr = 1; rr = r - 1
            while rr >= 0 and self.color[rr, c] == color:
                vr += 1; rr -= 1
            vlo = rr
            while vlo >= 0 and self.color[vlo, c] in (0, color):
                vlo -= 1
            rr = r + 1
            while rr < self.rows and self.color[rr, c] == color:
                vr += 1; rr += 1
            vhi = rr
            while vhi < self.rows and self.color[vhi, c] in (0, color):
                vhi += 1
            v_ok = (vhi - vlo - 1) >= 4
            total += float(max(hr * hr if h_ok else hr, vr * vr if v_ok else vr))
        return total

    def vertical_clear_readiness(self) -> float:
        """VERTICAL-only analogue of clear_readiness: for each virus, the same-color
        contiguous run length **down its column**, accumulated as run**2.

        ``clear_readiness`` takes max(horizontal, vertical), so it never *prefers*
        a vertical setup; combined with the height penalty (vertical stacking is
        tall) the planner drifts toward horizontal lines. Weighting this term makes
        the planner actively pursue vertical virus clears (stacking matching colors
        above/below a virus toward a 4-in-column)."""
        total = 0.0
        rs, cs = np.where(self.is_virus)
        for r, c in zip(rs, cs):
            color = self.color[r, c]
            vr = 1
            rr = r - 1
            while rr >= 0 and self.color[rr, c] == color:
                vr += 1; rr -= 1
            rr = r + 1
            while rr < self.rows and self.color[rr, c] == color:
                vr += 1; rr += 1
            total += float(vr ** 2)
        return total

    def buried_virus_count(self) -> int:
        """Sum over viruses of occupied cells stacked directly above them in
        their column. A buried virus must wait for everything above it to clear,
        so minimizing this keeps viruses reachable -- the key to finishing high
        levels (empirically: lifts level-7 win-rate 33%->58%, level-11 0%->25%)."""
        total = 0
        for c in range(self.cols):
            col = self.color[:, c]
            vir = self.is_virus[:, c]
            for r in range(self.rows):
                if vir[r]:
                    total += int(np.count_nonzero(col[:r] != EMPTY))
        return total

    def color_pollution(self) -> int:
        """For each virus, count non-virus pill cells in its row+column whose color
        differs from the virus color. Lower = more setup-completability for endgame.

        Observed live: as the planner clears viruses one-by-one, cells AROUND the
        remaining viruses become color-polluted (mixed R/Y/B). By the endgame
        (~2-5 viruses left) no monochrome 3-in-a-row exists near remaining viruses
        to build a 4-line into, so the planner stalls for 20-40 pills with no
        progress before topping out. Penalizing this rewards placements that keep
        a clear runway in each virus's row and column.

        The virus cell itself is skipped. Empty cells are skipped (they're not yet
        pollution). Other viruses sharing the row/column are also skipped (they're
        targets, not clutter). Same-color pill cells are not pollution -- they're
        helping build the clearing line.
        """
        total = 0
        rs, cs = np.where(self.is_virus)
        for r, c in zip(rs, cs):
            v_color = self.color[r, c]
            # Row r: count non-virus, non-empty cells whose color != v_color.
            row = self.color[r, :]
            row_v = self.is_virus[r, :]
            # mask: same row, not virus, not empty, color differs, NOT this virus's column
            for cc in range(self.cols):
                if cc == c:
                    continue
                if row_v[cc]:
                    continue
                col_val = row[cc]
                if col_val == EMPTY:
                    continue
                if col_val != v_color:
                    total += 1
            # Column c: same rule, skip the virus's own row.
            col = self.color[:, c]
            col_v = self.is_virus[:, c]
            for rr in range(self.rows):
                if rr == r:
                    continue
                if col_v[rr]:
                    continue
                col_val = col[rr]
                if col_val == EMPTY:
                    continue
                if col_val != v_color:
                    total += 1
        return total

    def spawn_block_risk(self) -> int:
        """Occupied cells in the spawn columns (3,4) in the top rows, weighted by
        height. Stacking the spawn columns blocks the next capsule spawn = an instant
        top-out -- the dominant high-level failure mode (viruses sit near the top, so
        clearing them tempts a greedy planner to stack cols 3-4 and top out in a few
        pills). Penalizing this keeps the spawn lane open. Verified live: the planner
        topped out in ~9 pills by clustering cols 2-3 on real (correlated) pill seqs."""
        risk = 0
        top = min(6, self.rows)
        for c in self.SPAWN_COLS:
            for r in range(top):
                if self.color[r, c] != EMPTY:
                    risk += (top - r)  # higher up (smaller r) = closer to a top-out
        return risk

    def spawn_col_height(self) -> int:
        """Sum of stack heights in spawn columns (3,4), counting non-virus cells only.

        Counterpart to ``spawn_block_risk`` that fires from the FIRST cell the
        player places in the spawn lane, not only once the stack reaches the top
        rows. The gradient on every placement steers the greedy planner away from
        spawn cols when alternatives exist; this is the lever the prior
        ``spawn_pen`` could not pull (it only saw cells in rows 0-5, by which time
        clustering had already happened).

        Viruses are excluded: original viruses in cols 3-4 are the *target*, not
        clutter -- penalizing them would discourage ever clearing them. A placed
        cell at row r contributes (rows - r), so a cell at row 15 contributes 1
        and a cell at row 0 contributes ``rows`` (and is a top-out anyway)."""
        pen = 0
        for c in self.SPAWN_COLS:
            for r in range(self.rows):
                if self.color[r, c] != EMPTY and not self.is_virus[r, c]:
                    pen += (self.rows - r)
        return pen

    def column_heights(self) -> np.ndarray:
        """Height of the stack in each column (0 = empty column)."""
        heights = np.zeros(self.cols, dtype=np.int32)
        for c in range(self.cols):
            occ = np.where(self.color[:, c] != EMPTY)[0]
            heights[c] = 0 if occ.size == 0 else (self.rows - int(occ.min()))
        return heights

    def top_occupied_row(self, c: int) -> int:
        """Lowest row index that is occupied in column ``c`` (``rows`` if empty)."""
        occ = np.where(self.color[:, c] != EMPTY)[0]
        return self.rows if occ.size == 0 else int(occ.min())

    def place_viruses(self, level: int) -> int:
        """Place viruses for ``level`` per the NES count formula.

        Count = min((level+1)*4, 84). Placement is uniform-random within a
        level-scaled ceiling, rejecting any cell that would create a starting
        line of 4 same-color cells (no free clears at the start).
        """
        count = min((level + 1) * 4, 84)
        # Highest row that may hold a virus (smaller index = higher up the board).
        # FAITHFUL to the ROM: the NES never places viruses above row 6 (rows 0-5
        # are the bottle neck) until the count can't fit in rows 6-15. Measured
        # live: L7/L11/L14 all top out at row 6. The old count-scaled formula put
        # L7 viruses at row 8 (too low = too easy -> sim win rate over-estimated
        # live by ~4x). See LIVE_CONTROL_NOTES / dr-mario-projects-map memory.
        needed_rows = -(-count // self.cols)  # ceil(count / cols)
        vtop = max(0, min(6, self.rows - needed_rows))
        placed = 0
        attempts = 0
        max_attempts = count * 200
        while placed < count and attempts < max_attempts:
            attempts += 1
            r = int(self.rng.integers(vtop, self.rows))
            c = int(self.rng.integers(0, self.cols))
            if self.color[r, c] != EMPTY:
                continue
            color = int(self.rng.integers(1, 4))
            if self._would_make_line(r, c, color, n=3):
                # discourage easy triples too (NES avoids near-clears); fall back
                # to allowing them only if we're struggling to place
                if attempts < max_attempts * 0.7:
                    continue
            if self._would_make_line(r, c, color, n=4):
                continue
            self.color[r, c] = color
            self.is_virus[r, c] = True
            placed += 1
        return placed

    def _would_make_line(self, r: int, c: int, color: int, n: int) -> bool:
        """Would putting ``color`` at (r,c) create a run of >= n in row or col?"""
        # horizontal run length through (r,c)
        run = 1
        cc = c - 1
        while cc >= 0 and self.color[r, cc] == color:
            run += 1; cc -= 1
        cc = c + 1
        while cc < self.cols and self.color[r, cc] == color:
            run += 1; cc += 1
        if run >= n:
            return True
        # vertical run length through (r,c)
        run = 1
        rr = r - 1
        while rr >= 0 and self.color[rr, c] == color:
            run += 1; rr -= 1
        rr = r + 1
        while rr < self.rows and self.color[rr, c] == color:
            run += 1; rr += 1
        return run >= n

    # ------------------------------------------------------------- placement
    def resting_position(self, pill: Pill, orientation: int, col: int):
        """Return ((r0,c0),(r1,c1)) resting cells for a dropped pill, or None
        if it cannot fit (board too full in that column)."""
        if orientation == ORIENT_H:
            if col < 0 or col + 1 >= self.cols:
                return None
            r = min(self.top_occupied_row(col), self.top_occupied_row(col + 1)) - 1
            if r < 0:
                return None
            return ((r, col), (r, col + 1))
        else:  # vertical, A on top
            if col < 0 or col >= self.cols:
                return None
            bottom = self.top_occupied_row(col) - 1
            top = bottom - 1
            if top < 0:
                return None
            return ((top, col), (bottom, col))

    def place_pill(self, pill: Pill, orientation: int, col: int) -> bool:
        """Lock a pill at its resting position. Returns False if it cannot fit."""
        cells = self.resting_position(pill, orientation, col)
        if cells is None:
            return False
        (r0, c0), (r1, c1) = cells
        if orientation == ORIENT_H:
            self.color[r0, c0] = pill.a
            self.color[r1, c1] = pill.b
            self.link[r0, c0] = LINK_RIGHT
            self.link[r1, c1] = LINK_LEFT
        else:
            self.color[r0, c0] = pill.a  # top
            self.color[r1, c1] = pill.b  # bottom
            self.link[r0, c0] = LINK_DOWN
            self.link[r1, c1] = LINK_UP
        self.is_virus[r0, c0] = False
        self.is_virus[r1, c1] = False
        return True

    # --------------------------------------------------------------- clears
    def _find_clears(self) -> np.ndarray:
        """Boolean mask of all cells in a horizontal or vertical run of >= 4."""
        mask = np.zeros((self.rows, self.cols), dtype=bool)
        g = self.color
        # horizontal runs
        for r in range(self.rows):
            c = 0
            while c < self.cols:
                v = g[r, c]
                if v == EMPTY:
                    c += 1
                    continue
                c2 = c
                while c2 < self.cols and g[r, c2] == v:
                    c2 += 1
                if c2 - c >= 4:
                    mask[r, c:c2] = True
                c = c2
        # vertical runs
        for c in range(self.cols):
            r = 0
            while r < self.rows:
                v = g[r, c]
                if v == EMPTY:
                    r += 1
                    continue
                r2 = r
                while r2 < self.rows and g[r2, c] == v:
                    r2 += 1
                if r2 - r >= 4:
                    mask[r:r2, c] = True
                r = r2
        return mask

    def _apply_clear(self, mask: np.ndarray) -> int:
        """Remove masked cells; un-link surviving partners. Returns viruses cleared."""
        viruses_cleared = int(np.sum(mask & self.is_virus))
        rs, cs = np.where(mask)
        # break links from surviving partners pointing into cleared cells
        for r, c in zip(rs, cs):
            lk = self.link[r, c]
            if lk != LINK_NONE:
                dr, dc = _DELTA[lk]
                pr, pc = r + dr, c + dc
                if 0 <= pr < self.rows and 0 <= pc < self.cols and not mask[pr, pc]:
                    self.link[pr, pc] = LINK_NONE
        self.color[mask] = EMPTY
        self.is_virus[mask] = False
        self.link[mask] = LINK_NONE
        return viruses_cleared

    # -------------------------------------------------------------- gravity
    def _bodies(self):
        """Group movable (non-virus) cells into rigid bodies (singles or pairs)."""
        seen = np.zeros((self.rows, self.cols), dtype=bool)
        bodies = []
        for r in range(self.rows):
            for c in range(self.cols):
                if self.color[r, c] == EMPTY or self.is_virus[r, c] or seen[r, c]:
                    continue
                lk = self.link[r, c]
                if lk == LINK_NONE:
                    seen[r, c] = True
                    bodies.append([(r, c)])
                else:
                    dr, dc = _DELTA[lk]
                    pr, pc = r + dr, c + dc
                    if 0 <= pr < self.rows and 0 <= pc < self.cols and not seen[pr, pc]:
                        seen[r, c] = True
                        seen[pr, pc] = True
                        bodies.append([(r, c), (pr, pc)])
                    else:
                        # dangling link (shouldn't happen) -> treat as single
                        seen[r, c] = True
                        bodies.append([(r, c)])
        return bodies

    def _can_fall(self, body) -> bool:
        bodyset = set(body)
        for (r, c) in body:
            nr = r + 1
            if nr >= self.rows:
                return False
            if (nr, c) not in bodyset and self.color[nr, c] != EMPTY:
                return False
        return True

    def _apply_gravity(self) -> bool:
        """Drop all unsupported bodies until stable. Returns True if anything moved."""
        moved_any = False
        while True:
            bodies = self._bodies()
            # process lowest cells first so a falling body doesn't overlap another
            bodies.sort(key=lambda b: max(r for r, _ in b), reverse=True)
            moved_this_pass = False
            for body in bodies:
                if self._can_fall(body):
                    self._move_body_down(body)
                    moved_this_pass = True
                    moved_any = True
            if not moved_this_pass:
                break
        return moved_any

    def _move_body_down(self, body):
        # snapshot cell attributes, clear, then rewrite one row lower
        cells = [(r, c, self.color[r, c], self.is_virus[r, c], self.link[r, c]) for r, c in body]
        for r, c, *_ in cells:
            self.color[r, c] = EMPTY
            self.is_virus[r, c] = False
            self.link[r, c] = LINK_NONE
        for r, c, col, vir, lk in cells:
            self.color[r + 1, c] = col
            self.is_virus[r + 1, c] = vir
            self.link[r + 1, c] = lk

    # --------------------------------------------------------------- resolve
    def resolve(self):
        """Run clear -> gravity -> clear ... until stable.

        Returns (total_cells_cleared, viruses_cleared, chain_len) where chain_len
        is the number of distinct clear steps (combo depth)."""
        total_cleared = 0
        viruses_cleared = 0
        chain = 0
        while True:
            mask = self._find_clears()
            n = int(mask.sum())
            if n == 0:
                break
            chain += 1
            total_cleared += n
            viruses_cleared += self._apply_clear(mask)
            self._apply_gravity()
        return total_cleared, viruses_cleared, chain

    # ------------------------------------------------------------- game over
    SPAWN_COLS = (3, 4)

    def spawn_blocked(self) -> bool:
        """True if the pill spawn cells (row 0, center) are occupied = top-out."""
        return any(self.color[0, c] != EMPTY for c in self.SPAWN_COLS)

    def ascii(self) -> str:
        glyph = {EMPTY: ".", RED: "R", YELLOW: "Y", BLUE: "B"}
        out = []
        for r in range(self.rows):
            row = []
            for c in range(self.cols):
                ch = glyph[int(self.color[r, c])]
                if self.is_virus[r, c]:
                    ch = ch.lower()  # lowercase = virus
                row.append(ch)
            out.append("".join(row))
        return "\n".join(out)
