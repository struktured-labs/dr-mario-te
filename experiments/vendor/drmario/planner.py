"""Greedy lookahead planner for the faithful Dr. Mario engine.

This is a placement-level planner: given the current board and the active pill
(optionally the next pill), it enumerates every legal landing spot, simulates the
resulting clears/cascades, and scores the outcome. It is deliberately fast and
``numpy``-light -- a board ``clone()`` is a few array copies, and the engine's
``resolve()`` does the heavy lifting -- so depth-1 and depth-2 search stay cheap.

It serves three roles in this project:
  * a strong immediate agent (clearly beats the 124-byte heuristic),
  * a self-play opponent, and
  * a teacher whose decisions can be distilled into a decision tree.

Action encoding matches :class:`~drmario.faithful_env.FaithfulDrMarioEnv`:
``action = variant * cols + col`` with
``0 = H(a,b)``, ``1 = H(b,a)``, ``2 = V(a top, b bottom)``, ``3 = V(b top, a bottom)``.
"""
from __future__ import annotations

from dataclasses import dataclass
from itertools import product
from typing import List, Optional, Tuple

import numpy as np

from .faithful_game import (
    FaithfulBoard, Pill, COLORS, EMPTY, ORIENT_H, ORIENT_V,
)

# Map a placement variant -> (orientation, swap_colors?). Mirrors env._decode.
_VARIANTS = {
    0: (ORIENT_H, False),
    1: (ORIENT_H, True),
    2: (ORIENT_V, False),
    3: (ORIENT_V, True),
}


@dataclass
class PlannerWeights:
    """Tunable scoring weights for :class:`GreedyPlanner`.

    The first three (``virus``, ``clear_cell``, ``combo``) reward what a move
    *accomplishes* during ``resolve()``; the rest score the *resulting* board
    shape (lower stacks, fewer holes, less top-row crowding, more "almost-lines"
    that touch a virus).

    Defaults are the ``setup_max`` config selected by the weight sweep in
    ``scripts/benchmark.py`` (best avg virus-clear rate for greedy1 on levels
    5 & 10; see BENCHMARK.md). High ``virus``/``combo`` weights make the planner
    chase clears and cascades, while the heavier shape penalties keep it from
    burying viruses under junk -- the dominant failure mode of 1-ply greedy.
    """
    virus: float = 18.0        # per virus cleared by the move
    clear_cell: float = 0.6    # per cell cleared (rewards junk removal too)
    combo: float = 6.0         # per chain step (combo depth)
    height_pen: float = 1.2    # penalty * tallest column height
    holes_pen: float = 2.5     # penalty * buried empty cells
    top_risk_pen: float = 4.5  # penalty * occupied cells in the top 3 rows
    setup_bonus: float = 4.0   # bonus * virus-adjacent length-3 same-color runs
    buried_pen: float = 3.0    # penalty * cells stacked above viruses (keeps them reachable)
    readiness_bonus: float = 0.4  # bonus * clear_readiness (viruses near a clearing line)
    v_readiness_bonus: float = 0.0  # bonus * vertical_clear_readiness (pursue vertical clears)
    spawn_pen: float = 0.0     # penalty * spawn_block_risk (keep cols 3-4 open -> no fast top-out)
    spawn_col_pen: float = 0.0 # penalty * spawn_col_height (fires on EVERY placement in cols 3-4, unlike spawn_pen which only fires in the top rows -- this is what actually steers placements away from the spawn lane early)
    junk_bonus: float = 0.0    # bonus * (total_cleared - viruses_cleared); rewards non-virus 4-in-a-row self-clears to breathe in the endgame without the eval-hacking trap from boosting clear_cell across the board
    pollution_pen: float = 0.0 # penalty * color_pollution; discourages stuffing the row/col of a remaining virus with wrong-color pill cells (the endgame "no-monochrome-runway" trap observed live -- planner clears viruses then stalls 20-40 pills because nothing matches the survivors' color in their lines)
    dual_end_bonus: float = 0.0 # bonus per pill-half that lands adjacent to a same-color cell (4-neighbour). For multicolor pills both halves should contribute, not just one — the planner enumerates the swap but the magnitude of the productive-both-halves signal is weak without this term. Counts surviving halves only; cleared halves don't contribute.
    # NOTE: an earlier vertical_pref_bonus weight was REMOVED — the user clarified
    # the "horizontal bias" they observed is about preferring HORIZONTAL CLEAR
    # LINES (4-in-row) rather than vertical clear lines. Pill orientation itself
    # is fine either way. The real lever is rebalancing v_readiness vs (implicit)
    # h_readiness, which goes through `readiness_bonus` + `v_readiness_bonus` —
    # not a per-move pill-orientation tilt.


# Result of a simulated placement. cells = the two pre-resolve placement cells
# ((r0,c0),(r1,c1)); orient = ORIENT_H or ORIENT_V. Carried through so per-move
# heuristics like dual_end_bonus / vertical_pref_bonus can score the placement
# itself, not just the resulting board.
SimResult = Tuple[FaithfulBoard, int, int, int, Tuple[Tuple[int,int], Tuple[int,int]], int]
Placement = Tuple[int, int, int, Pill]           # (action, orient, col, pill)


class GreedyPlanner:
    """Greedy one- or two-ply placement planner."""

    def __init__(self, weights: Optional[PlannerWeights] = None, depth: int = 1,
                 endgame_weights: Optional[PlannerWeights] = None,
                 endgame_virus_threshold: int = 10,
                 endgame_depth: int = 0, endgame_top_k: int = 8):
        self.weights = weights or PlannerWeights()
        self.depth = depth
        self.endgame_weights = endgame_weights
        self.endgame_virus_threshold = endgame_virus_threshold
        # When the board enters endgame (virus_count <= threshold), swap to a
        # deeper search (endgame_depth) with top-K pruning (endgame_top_k) at
        # each ply. Setting endgame_depth=0 disables the swap (default behavior).
        self.endgame_depth = endgame_depth
        self.endgame_top_k = endgame_top_k
        self._active_depth = self.depth
        self._active_top_k = 0  # 0 = no pruning
        # Active weights default to the mid-game profile; choose() swaps to
        # endgame_weights once virus_count falls at/below the threshold.
        self._active_weights = self.weights

    # --------------------------------------------------------- enumeration
    def enumerate_placements(self, board: FaithfulBoard, pill: Pill) -> List[Placement]:
        """All legal landing placements for ``pill`` on ``board``.

        Returns ``(action_index, orient, col, pill_with_correct_color_order)``
        for every variant x column whose resting position exists.
        """
        out: List[Placement] = []
        for variant, (orient, swap) in _VARIANTS.items():
            p = Pill(pill.b, pill.a) if swap else Pill(pill.a, pill.b)
            for col in range(board.cols):
                if board.resting_position(p, orient, col) is not None:
                    out.append((variant * board.cols + col, orient, col, p))
        return out

    # --------------------------------------------------------- simulation
    def simulate(self, board: FaithfulBoard, action: int,
                 pill: Pill) -> Optional[SimResult]:
        """Clone ``board``, place ``pill`` per ``action``, and ``resolve()``.

        ``action`` is the env encoding ``variant * cols + col`` and ``pill`` is
        the *current* pill (its ``a``/``b`` are reordered per the variant).
        Returns ``(resulting_board, viruses_cleared, total_cleared, chain)`` or
        ``None`` if the placement is illegal (column full / off the edge).
        """
        variant = action // board.cols
        col = action % board.cols
        orient, swap = _VARIANTS[variant]
        p = Pill(pill.b, pill.a) if swap else Pill(pill.a, pill.b)
        return self._simulate(board, orient, col, p)

    def _simulate(self, board: FaithfulBoard, orient: int, col: int,
                  pill: Pill) -> Optional[SimResult]:
        cells = board.resting_position(pill, orient, col)
        if cells is None:
            return None
        clone = board.clone()
        if not clone.place_pill(pill, orient, col):
            return None
        total_cleared, viruses_cleared, chain = clone.resolve()
        return clone, viruses_cleared, total_cleared, chain, cells, orient

    # ------------------------------------------------------------- scoring
    # Win-state bonus -- dominates any shape penalty so a move that clears the
    # last virus is always preferred. Without this, the planner can rank a no-clear
    # move ABOVE a winning move because the post-win board has high shape penalties
    # (lots of debris) while the still-virus board carries readiness/setup bonuses.
    # Verified on real failure boards: seed-104 winning move scored -21 in the deep
    # eval (post-win penalties) vs +17 for a no-clear move (sustained readiness).
    WIN_BONUS: float = 100000.0

    def score_board(self, board: FaithfulBoard) -> float:
        """Heuristic value of a resting board state (higher = better).

        Fully vectorized: ``max_height`` and ``holes`` come from a single
        cumulative-occupancy pass, top-row crowding from a slice, and the
        virus-adjacent length-3 run count from array shifts (see ``_setup_runs``).
        """
        if board.virus_count() == 0:
            # Terminal win state: dominates all other terms so any path to a win
            # is always preferred over any non-winning path, regardless of debris.
            return self.WIN_BONUS
        w = getattr(self, "_active_weights", None) or self.weights
        occ = board.color != EMPTY              # occupied mask
        rows, cols = board.rows, board.cols

        # Per-column "is there anything at or above this row" via cumulative-or
        # from the top. A hole is an empty cell that has occupancy above it.
        covered = np.cumsum(occ, axis=0) > 0    # True from the topmost block down
        holes = int(np.count_nonzero(covered & ~occ))

        # Tallest column: rows minus the highest occupied row index.
        any_col = occ.any(axis=0)
        if any_col.any():
            first_occ = occ.argmax(axis=0)      # topmost occupied row per column
            max_height = int(rows - first_occ[any_col].min())
        else:
            max_height = 0

        # Top-row crowding (proximity to a top-out).
        top_band = min(3, rows)
        top_risk = int(np.count_nonzero(occ[:top_band, :]))

        setup = self._setup_runs(board)

        value = (-w.height_pen * max_height
                 - w.holes_pen * holes
                 - w.top_risk_pen * top_risk
                 + w.setup_bonus * setup
                 - w.buried_pen * board.buried_virus_count()
                 + w.readiness_bonus * board.clear_readiness())
        if w.v_readiness_bonus:
            value += w.v_readiness_bonus * board.vertical_clear_readiness()
        if w.spawn_pen:
            value -= w.spawn_pen * board.spawn_block_risk()
        if w.spawn_col_pen:
            value -= w.spawn_col_pen * board.spawn_col_height()
        if w.pollution_pen:
            value -= w.pollution_pen * board.color_pollution()
        return value

    def _setup_runs(self, board: FaithfulBoard) -> int:
        """Count length-3 same-color runs (row or col) that touch a virus.

        These are "one cell from clearing a virus" setups -- the chain-setup
        potential the planner should cultivate. A run counts if any of its three
        cells, or either end-adjacent cell in line, is a same-color virus.

        Vectorized via shifted-array equality. ``vcol`` holds a virus's color (a
        sentinel ``-1`` elsewhere) so ``vcol == c`` is true only at a same-color
        virus. Verified equal to the obvious double-loop in tests.
        """
        color = board.color
        # Virus color where a virus sits, sentinel -1 otherwise (never matches).
        vcol = np.where(board.is_virus, color, np.int8(-1))

        def count_axis(axis: int) -> int:
            n = color.shape[axis]
            if n < 3:
                return 0
            c0 = np.take(color, range(0, n - 2), axis=axis)   # window start cell i
            c1 = np.take(color, range(1, n - 1), axis=axis)   # i+1
            c2 = np.take(color, range(2, n - 0), axis=axis)   # i+2
            run = (c0 != EMPTY) & (c0 == c1) & (c1 == c2)     # length-3 same-color

            v0 = np.take(vcol, range(0, n - 2), axis=axis)
            v1 = np.take(vcol, range(1, n - 1), axis=axis)
            v2 = np.take(vcol, range(2, n - 0), axis=axis)
            touch = (v0 == c0) | (v1 == c0) | (v2 == c0)      # virus in the window

            # End-adjacent virus: cell i-1 (for i>=1) or i+3 (for i+3 < n).
            ends = np.zeros_like(run)
            if n >= 4:
                prev_v = np.take(vcol, range(0, n - 3), axis=axis)  # i-1, windows i>=1
                cur_a = np.take(c0, range(1, n - 2), axis=axis)     # those windows
                idx = [slice(None)] * ends.ndim
                idx[axis] = slice(1, n - 2)
                ends[tuple(idx)] |= (prev_v == cur_a)

                next_v = np.take(vcol, range(3, n), axis=axis)      # i+3, windows i<=n-4
                cur_b = np.take(c0, range(0, n - 3), axis=axis)
                idx2 = [slice(None)] * ends.ndim
                idx2[axis] = slice(0, n - 3)
                ends[tuple(idx2)] |= (next_v == cur_b)

            return int(np.count_nonzero(run & (touch | ends)))

        return count_axis(1) + count_axis(0)

    # ----------------------------------------------------- move evaluation
    def _move_value(self, sim: SimResult) -> Tuple[float, float]:
        """Return ``(immediate_reward, resulting_board_score)`` for a simulated move.

        ``immediate_reward`` rewards what the move accomplished (viruses, cells
        cleared, combo depth); the board score rates the leftover shape.
        """
        w = getattr(self, "_active_weights", None) or self.weights
        resulting, viruses, total, chain, cells, orient = sim
        junk = max(0, total - viruses)   # cells cleared that were NOT viruses
        immediate = (w.virus * viruses + w.clear_cell * total
                     + w.combo * max(0, chain - 1)
                     + w.junk_bonus * junk)
        # Per-move heuristics that need the placement context:
        # dual_end: count placed-cell halves that survived AND have a same-color
        # 4-neighbour on the post-resolve board (encourages BOTH halves of a
        # multicolor pill to land productively, not just one).
        if w.dual_end_bonus:
            productive = 0
            rows, cols_ = resulting.rows, resulting.cols
            for (r, c) in cells:
                # if 0 <= r < rows etc, and cell wasn't cleared, check neighbors
                if r < 0 or r >= rows or c < 0 or c >= cols_:
                    continue
                col_here = int(resulting.color[r, c])
                if col_here == EMPTY:
                    continue   # the half was cleared as part of this move
                found = False
                for dr, dc in ((-1, 0), (1, 0), (0, -1), (0, 1)):
                    nr, nc = r + dr, c + dc
                    if 0 <= nr < rows and 0 <= nc < cols_ and (nr, nc) not in cells:
                        if int(resulting.color[nr, nc]) == col_here:
                            found = True
                            break
                if found:
                    productive += 1
            immediate += w.dual_end_bonus * productive
        return immediate, self.score_board(resulting)

    # --------------------------------------------------------------- choose
    def choose(self, board: FaithfulBoard, cur_pill: Pill,
               next_pill: Optional[Pill] = None) -> Optional[int]:
        """Return the best action index, or ``None`` if no legal move exists.

        Deterministic: ties are broken by the lowest action index (placements
        are enumerated in increasing action order).
        """
        # Endgame swap: heavier weights + deeper search with pruning kick in
        # once only a few viruses remain (often piled under debris). Depth-3
        # endgame can find multi-pill clear sequences depth-2 can't see.
        in_endgame = board.virus_count() <= self.endgame_virus_threshold
        if in_endgame and self.endgame_weights is not None:
            self._active_weights = self.endgame_weights
        else:
            self._active_weights = self.weights
        if in_endgame and self.endgame_depth > 0:
            self._active_depth = self.endgame_depth
            self._active_top_k = self.endgame_top_k
        else:
            self._active_depth = self.depth
            self._active_top_k = 0

        placements = self.enumerate_placements(board, cur_pill)
        if not placements:
            return None

        rest = [next_pill] if next_pill is not None else []
        best_action = None
        best_value = -np.inf
        for action, orient, col, pill in placements:
            sim = self._simulate(board, orient, col, pill)
            if sim is None:
                continue
            immediate, _ = self._move_value(sim)
            value = immediate + self._evaluate(sim[0], rest, self._active_depth - 1)
            if value > best_value:
                best_value = value
                best_action = action
        return best_action

    def _evaluate(self, board: FaithfulBoard, pills: List[Pill], ply: int) -> float:
        """Best value reachable from ``board`` with ``ply`` further placements.

        ``pills`` are the known upcoming pills; once they run out the remaining
        plies marginalize over the 9 equally-likely color pairs (the engine draws
        colors uniformly). ``ply == 0`` scores the resting board. This recursion
        subsumes depth-1 (ply 0), depth-2 (one known next pill), and depth-3 (known
        next + marginalized pill-after-next).
        """
        if ply <= 0:
            return self.score_board(board)
        if pills:
            return self._eval_pill(board, pills[0], pills[1:], ply)
        total = 0.0
        for a, b in product(COLORS, COLORS):
            total += self._eval_pill(board, Pill(a, b), [], ply)
        return total / 9.0

    def _eval_pill(self, board: FaithfulBoard, pill: Pill,
                   rest: List[Pill], ply: int) -> float:
        """Best ``immediate + deeper`` value over all placements of ``pill``.

        When ``self._active_top_k > 0``, scores all placements at depth-0
        (immediate + board_score) and only recurses into the top K. This bounds
        the branching factor at deep plies (essential for pruned depth-3 endgame)
        while still considering every placement for the immediate score.
        """
        placements = self.enumerate_placements(board, pill)
        if not placements:
            # No legal placement (near top-out): score the board as-is.
            return self.score_board(board)

        top_k = getattr(self, "_active_top_k", 0)
        if top_k > 0 and ply > 1 and len(placements) > top_k:
            # Rank by depth-0 (immediate + resulting-board score); recurse into top-K.
            shortlist = []
            for _action, orient, col, p in placements:
                sim = self._simulate(board, orient, col, p)
                if sim is None:
                    continue
                immediate, bs = self._move_value(sim)
                shortlist.append((immediate + bs, immediate, sim))
            shortlist.sort(key=lambda x: x[0], reverse=True)
            shortlist = shortlist[:top_k]
            best = -np.inf
            for _depth0, immediate, sim in shortlist:
                v = immediate + self._evaluate(sim[0], rest, ply - 1)
                if v > best:
                    best = v
            return best

        best = -np.inf
        for _action, orient, col, p in placements:
            sim = self._simulate(board, orient, col, p)
            if sim is None:
                continue
            immediate, _ = self._move_value(sim)
            v = immediate + self._evaluate(sim[0], rest, ply - 1)
            if v > best:
                best = v
        return best
