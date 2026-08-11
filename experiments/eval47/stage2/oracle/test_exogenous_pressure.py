#!/usr/bin/env python3
"""Unit tests for the exo_lulu_v1 pressure schedule."""
from __future__ import annotations

import copy
import os
import sys
import unittest

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
STAGE2 = os.path.dirname(HERE)
EV = os.path.dirname(STAGE2)
QA = os.path.dirname(EV)
ROOT = "/home/struktured/projects/dr_mario_rl"
for p in (HERE, EV, QA, ROOT + "/.claude/worktrees/faithful-sim/src"):
    if p not in sys.path:
        sys.path.insert(0, p)

import exogenous_pressure as X  # noqa: E402


class FakeModel:
    volley_sizes = [2, 3, 4]

    def sample(self, seed, pills_placed):
        import random
        rng = random.Random(seed * 1000 + pills_placed)
        n = rng.choice(self.volley_sizes)
        nc = max(1, min(8, round(n / 2)))
        return n, rng.sample(range(8), nc)

    def fire_probability(self, clear_size):
        return ({4: 0.25, 7: 0.75, 11: 0.0}.get(clear_size, 0.5), 10)


def blank_board():
    from drmario.faithful_env import FaithfulDrMarioEnv
    e = FaithfulDrMarioEnv(level=0, seed=1, max_pills=10)
    e.reset()
    e.board.color[:] = 0
    e.board.is_virus[:] = False
    e.board.link[:] = 0
    return e.board


class TestExogenousPressure(unittest.TestCase):
    def setUp(self):
        self.model = FakeModel()

    def test_offer_is_deterministic_and_board_free(self):
        for seed in (1, 50_000, (50_000 << 32) | (17 << 16)):
            for pill in (25, 26, 199, 300):
                a = X.pressure_offer(self.model, seed, pill)
                b = X.pressure_offer(self.model, seed, pill)
                self.assertEqual(a, b)
                self.assertEqual(a.digest(), b.digest())

    def test_coupled_clear_mutant_is_killed(self):
        killed = False
        for seed in range(1, 200):
            vals = {X.coupled_fire_mutant(self.model, seed, 25, c)
                    for c in (4, 7, 11)}
            if len(vals) > 1:
                killed = True
                break
        self.assertTrue(killed)

    def test_precommitted_colours_survive_full_other_column(self):
        offer = None
        for seed in range(1, 2000):
            q = X.pressure_offer(self.model, seed, 25)
            if q.fires and len(q.columns) >= 2:
                offer = q
                break
        self.assertIsNotNone(offer)
        c0, c1 = offer.columns[:2]
        clean = blank_board()
        blocked = copy.deepcopy(clean)
        blocked.color[:, c0] = np.resize(np.array([1, 2, 3], dtype=np.int8), 16)

        X.apply_offer(clean, offer)
        X.apply_offer(blocked, offer)
        self.assertTrue(np.array_equal(clean.color[:, c1], blocked.color[:, c1]))

    def test_multiheight_offer_lands_every_cell(self):
        offer = X.PressureOffer(X.SCHEDULE_VERSION, 1, 25, True, 4,
                                (2, 6), ((2, 1), (2, 2), (6, 3), (6, 1)))
        board = blank_board()
        self.assertEqual(X.apply_offer(board, offer), 4)
        self.assertEqual(int(np.count_nonzero(board.color)), 4)
        self.assertEqual(int(np.count_nonzero(board.color[:, 2])), 2)
        self.assertEqual(int(np.count_nonzero(board.color[:, 6])), 2)

    def test_apply_time_colour_mutant_is_killed(self):
        columns = (0, 5)
        killed = False
        for colour_seed in range(1, 100):
            clean = blank_board()
            blocked = copy.deepcopy(clean)
            blocked.color[:, columns[0]] = np.resize(
                np.array([1, 2, 3], dtype=np.int8), 16)
            ca = X.apply_time_colour_mutant(clean, 4, columns, colour_seed)
            cb = X.apply_time_colour_mutant(blocked, 4, columns, colour_seed)
            clean_other = tuple(col for c, col in ca if c == columns[1])
            blocked_other = tuple(col for c, col in cb if c == columns[1])
            if clean_other != blocked_other:
                killed = True
                break
        self.assertTrue(killed)

    def test_arm_keyed_schedule_mutant_is_killed(self):
        killed = any(
            X.pressure_offer(self.model, 50_000, p).digest()
            != X.pressure_offer(self.model, 50_000 ^ 0xA5A5A5A5, p).digest()
            for p in range(25, 80))
        self.assertTrue(killed)


if __name__ == "__main__":
    unittest.main()
