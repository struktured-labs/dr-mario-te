#!/usr/bin/env python3
"""Registered pressure-regime variants for the failure-regime map (regime-141).

Each variant is a thin deterministic wrapper around the honest bursty v1.1
BurstyPressureModel. game.py and inject_bursty_garbage() see only the model
interface (fire_probability, sample), so wrapping the MODEL — not the injector —
keeps the injector's own draw and game.py's verification re-sample coherent by
construction: sample(seed, gp) is a pure function of its arguments in the base
model and stays one here.

Variants
--------
  bursty      : the base v1.1 model, untouched (identity — no wrapper).
  bursty_x2   : fire probability doubled, capped at 1.0. Volley sizes, columns,
                gap structure untouched. A registered SYNTHETIC intensity dial —
                provenance is "honest v1.1 × alpha", not a fitted human.
  bursty_aim  : honest fire probability and volley size; the COLUMN draw is
                redirected to the spawn columns (3, 4) first, then random others.
                Volume-neutral by construction (same n_cells, same n_cols as the
                base draw). This is the farm-servable analog of the tier-3
                adversarial scheduler finding (ci-overlap lane: aiming at spawn
                columns raises dies-ahead 5-13x at honest volume).

Determinism: every draw is a pure function of (seed, pills_placed). The aim
column shuffle uses random.Random(seed*1000 + pills_placed ^ AIM_SALT), a salt
so it never replays the base model's own stream.
"""
from __future__ import annotations

import random

NCOLS = 8
AIM_COLS = (3, 4)      # spawn columns — the throw/spawn lane
AIM_SALT = 0xA13


class AmplifiedModel:
    """fire_probability scaled by alpha (capped at 1.0); everything else passthrough."""

    def __init__(self, base, alpha: float):
        self.base = base
        self.alpha = float(alpha)

    def fire_probability(self, clear_size):
        p, n = self.base.fire_probability(clear_size)
        return min(1.0, self.alpha * p), n

    def sample(self, seed, pills_placed):
        return self.base.sample(seed, pills_placed)


class AimedModel:
    """Column draw redirected to AIM_COLS first; size and count preserved."""

    def __init__(self, base):
        self.base = base

    def fire_probability(self, clear_size):
        return self.base.fire_probability(clear_size)

    def sample(self, seed, pills_placed):
        n_cells, cols = self.base.sample(seed, pills_placed)
        if not cols:
            return n_cells, cols
        k = len(cols)
        aimed = list(AIM_COLS[:k])
        if k > len(AIM_COLS):
            rng = random.Random((seed * 1000 + pills_placed) ^ AIM_SALT)
            others = [c for c in range(NCOLS) if c not in AIM_COLS]
            aimed += rng.sample(others, k - len(AIM_COLS))
        return n_cells, aimed


VARIANTS = ("clean", "bursty", "bursty_x2", "bursty_aim")


def wrap_model(base, variant: str):
    """Return (model_for_game_py, pressure_arg_for_game_py)."""
    if variant == "clean":
        return None, "clean"
    if variant == "bursty":
        return base, "bursty"
    if variant == "bursty_x2":
        return AmplifiedModel(base, 2.0), "bursty"
    if variant == "bursty_aim":
        return AimedModel(base), "bursty"
    raise ValueError(f"unknown variant {variant!r}")
