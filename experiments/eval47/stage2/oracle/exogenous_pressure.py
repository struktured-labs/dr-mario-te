#!/usr/bin/env python3
"""Candidate-independent pressure offers for the oracle sensitivity arm.

The legacy solo Lulu rig decides whether an incoming volley fires from the
receiver's own clear size.  That makes the external pressure policy-dependent.
`exo_lulu_v1` samples the complete offered volley from `(seed, pill)` only and
precommits its columns and colours before seeing the receiver board.

Frozen design: PREREG_EXOGENOUS_PRESSURE.md @ 5f0b431.
"""
from __future__ import annotations

import hashlib
import json
import random
from dataclasses import asdict, dataclass


SCHEDULE_VERSION = "exo_lulu_v1"
FIRE_NUM = 187_891
FIRE_DEN = 1_000_000


def _mix64(x):
    """Stable SplitMix64 finalizer."""
    x = (int(x) + 0x9E3779B97F4A7C15) & 0xFFFFFFFFFFFFFFFF
    x = ((x ^ (x >> 30)) * 0xBF58476D1CE4E5B9) & 0xFFFFFFFFFFFFFFFF
    x = ((x ^ (x >> 27)) * 0x94D049BB133111EB) & 0xFFFFFFFFFFFFFFFF
    return x ^ (x >> 31)


def _key(seed, pills_placed, lane):
    """Key arbitrary-size seed values without Python's process-random hash()."""
    x = _mix64(int(seed))
    x ^= _mix64((int(pills_placed) << 16) | int(lane))
    return _mix64(x)


@dataclass(frozen=True)
class PressureOffer:
    version: str
    seed: int
    pills_placed: int
    fires: bool
    n_cells: int
    columns: tuple[int, ...]
    # One precommitted colour for every attempted cell, in column-major order.
    cells: tuple[tuple[int, int], ...]

    def digest(self):
        doc = asdict(self)
        payload = json.dumps(doc, sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(payload.encode()).hexdigest()


def pressure_offer(model, seed, pills_placed):
    """Return the immutable offer for this game/pill, independent of a board."""
    seed, pills_placed = int(seed), int(pills_placed)
    fires = (_key(seed, pills_placed, 0) % FIRE_DEN) < FIRE_NUM
    if not fires:
        return PressureOffer(SCHEDULE_VERSION, seed, pills_placed, False,
                             0, (), ())

    # Keep the fitted size/column sampler, but give it a domain-separated key.
    draw_seed = _key(seed, pills_placed, 1)
    n_cells, cols = model.sample(draw_seed, pills_placed)
    cols = tuple(int(c) for c in cols)
    if not cols or int(n_cells) <= 0:
        return PressureOffer(SCHEDULE_VERSION, seed, pills_placed, False,
                             0, (), ())

    rows_per_col = max(1, int(n_cells) // len(cols))
    colour_rng = random.Random(_key(seed, pills_placed, 2))
    cells = tuple((c, colour_rng.randint(1, 3))
                  for c in cols for _ in range(rows_per_col))
    return PressureOffer(SCHEDULE_VERSION, seed, pills_placed, True,
                         int(n_cells), cols, cells)


def apply_offer(board, offer):
    """Apply a precommitted offer; receiver occupancy may only veto cells.

    This deliberately does not draw randomness.  A full earlier column cannot
    shift the colour stream seen by a later column.
    """
    if not offer.fires:
        return 0
    from drmario.faithful_game import EMPTY, LINK_NONE

    placed = 0
    by_column = {c: [] for c in offer.columns}
    for c, colour in offer.cells:
        by_column[c].append(colour)
    for c in offer.columns:
        if board.color[0, c] != EMPTY:
            continue
        # Match bursty_model.inject_bursty_garbage: the row-0 capacity check
        # happens once per column, then all cells assigned to that column are
        # inserted before gravity.  Rechecking row 0 per cell silently capped
        # every multi-height volley at one cell/column; E4 caught the dose loss.
        for colour in by_column[c]:
            r = 0
            while r < board.rows and board.color[r, c] != EMPTY:
                r += 1
            if r >= board.rows:
                break
            board.color[r, c] = int(colour)
            board.is_virus[r, c] = False
            board.link[r, c] = LINK_NONE
            placed += 1
    if placed:
        board._apply_gravity()
        board.resolve()
    return placed


def inject_exogenous_garbage(board, model, seed, pills_placed):
    """Convenience wrapper returning `(landed_cells, immutable_offer)`."""
    offer = pressure_offer(model, seed, pills_placed)
    return apply_offer(board, offer), offer


def coupled_fire_mutant(model, seed, pills_placed, receiver_clear_size):
    """The historical defect, retained only as E1's killed mutant."""
    receiver_clear_size = int(receiver_clear_size)
    if receiver_clear_size <= 0:
        return False
    rng = random.Random(int(seed) * 1000 + int(pills_placed))
    p_fire, _n = model.fire_probability(receiver_clear_size)
    return rng.random() < p_fire


def apply_time_colour_mutant(board, n_cells, columns, colour_seed):
    """Killed E2 mutant: draw colours only after occupancy-dependent skips."""
    from drmario.faithful_game import EMPTY, LINK_NONE

    rng = random.Random(int(colour_seed))
    rows_per_col = max(1, int(n_cells) // max(1, len(columns)))
    offered = []
    for c in columns:
        if board.color[0, c] != EMPTY:
            continue
        for _ in range(rows_per_col):
            r = 0
            while r < board.rows and board.color[r, c] != EMPTY:
                r += 1
            if r >= board.rows:
                break
            colour = rng.randint(1, 3)
            offered.append((int(c), colour))
            board.color[r, c] = colour
            board.is_virus[r, c] = False
            board.link[r, c] = LINK_NONE
    return tuple(offered)
