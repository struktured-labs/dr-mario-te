"""OWNER-2026-09 opponent (OPP1): the phase-flat refit from this week's couch footage
(experiments/couch_forensics/owner_fit_202609.json, RESULT_OWNER_SENDS.md `a46b8ba`).

  * NOT linked to the AI's clears (owner: sends are organic; data: rate flat across AI progress) -> an independent
    RENEWAL process of volleys.
  * Time base: gate (b) has its own clock, so the renewal runs in AI PLACEMENTS. Couch conversion measured from the
    same 11 L11 games: the AI places 28.9 pills/min (2.08 s/placement) -> gap_placements = gap_seconds / 2.08.
    Gaps are resampled from the empirical L11 inter-volley gaps (not a fitted parametric law).
  * Size pmf {2: .854, 3: .024, 4: .122}; with p = 0.016 a second volley lands in the same placement interval.
  * Columns: 2-cell -> 77% two distinct columns, 23% one column; 3-cell -> 3 columns; 4-cell -> 62% three columns
    (2+1+1), 38% two columns (2+2). Drop mechanics = the bursty/striker drop (first empty row from the top, random
    colour 1..3, unlinked single, gravity BEFORE resolve).
  * Garbage only from gate (b)'s GARBAGE_MIN_PILLS onward (same instrument gate as every other opponent); the renewal
    clock starts there (first volley one gap after the first eligible placement), so there is no backlog dump.
Deterministic per seed.
"""
from __future__ import annotations
import json, os, random

S_PER_PLACEMENT = 2.08
FIT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "couch_forensics", "owner_fit_202609.json")


class Owner202609:
    name = "owner202609"

    def __init__(self, fit_path=FIT):
        d = json.load(open(fit_path))
        self.gaps = [g / S_PER_PLACEMENT for g in d["inter_volley_gap_s"]["samples_L11"]]
        pmf = {int(k): v for k, v in d["size_pmf"].items() if k.isdigit()}
        tot = sum(pmf.values())
        self.sizes = sorted(pmf); self.cum = []
        acc = 0.0
        for s in self.sizes:
            acc += pmf[s] / tot; self.cum.append(acc)
        self.p_double = float(d["p_double_in_one_placement_interval"])
        self.reset(0)

    def reset(self, seed):
        self.rng = random.Random(seed * 7727 + 202609)
        self.next_at = None                              # renewal clock starts at the first eligible placement
        self.nvol = 0; self.cells = 0

    def _size(self):
        x = self.rng.random()
        for s, c in zip(self.sizes, self.cum):
            if x <= c:
                return s
        return self.sizes[-1]

    def _columns(self, n):
        cols = list(range(8))
        if n == 2:
            return [self.rng.choice(cols)] * 2 if self.rng.random() < 0.23 else self.rng.sample(cols, 2)
        if n == 3:
            return self.rng.sample(cols, 3)
        if n == 4:
            if self.rng.random() < 0.62:
                a, b, c = self.rng.sample(cols, 3)
                return [a, a, b, c]
            a, b = self.rng.sample(cols, 2)
            return [a, a, b, b]
        return [self.rng.choice(cols) for _ in range(n)]

    def _drop(self, board, colist):
        from drmario.faithful_game import EMPTY, LINK_NONE
        placed = 0
        for c in colist:
            if board.color[0, c] != EMPTY:
                continue
            r = 0
            while r < board.rows and board.color[r, c] != EMPTY:
                r += 1
            if r >= board.rows:
                continue
            board.color[r, c] = self.rng.randint(1, 3)
            board.is_virus[r, c] = False
            board.link[r, c] = LINK_NONE
            placed += 1
        if placed:
            board._apply_gravity()
            board.resolve()
        return placed

    def after_placement(self, board, seed, pills_placed, clear_size):
        landed = 0
        if self.next_at is None:                         # gate (b) calls from GARBAGE_MIN_PILLS on: no backlog dump
            self.next_at = pills_placed + self.rng.choice(self.gaps)
        while pills_placed >= self.next_at:
            n_vol = 2 if self.rng.random() < self.p_double else 1
            for _ in range(n_vol):
                landed += self._drop(board, self._columns(self._size()))
                self.nvol += 1
            self.next_at += self.rng.choice(self.gaps)
        self.cells += landed
        return landed

    def summary(self):
        return {"volleys": self.nvol, "cells": self.cells}


def make():
    return Owner202609()
