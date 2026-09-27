"""OPP1 opponent suite for the steering-on gate (b) (PREREG_OPP1.md). Each opponent decides, after every AI placement,
what garbage lands on the AI's board. Deterministic per (seed, pills_placed).

  OwnerBursty(model)   the OWNER burst model (bursty_model.BurstyPressureModel): linked fire after the AI's clears,
                       exactly gate_b.play's injection (identity-tested against banked gate_b rows). With the 0804 fit
                       this is also the COMMON BLIND BASELINE (reconciliation rule: compare every arm against one
                       common blind condition, never an arm-specific volume-matched control).
  Striker(model, H)    the lulu147 STRIKER (dr-mario-lulu147-wt experiments/eval47/lulu_proxy/striker_model.py @1049308,
                       ported, not rebuilt): EARNS volleys with the identical bursty-v1 fire/size draws on the AI's
                       clears, BANKS them, and RELEASES ALL banked volleys when the AI's SCAFFOLD height >= H (the
                       contiguous non-virus run at the top of a column, maxed over columns) or when the oldest volley
                       has waited BANK_TIMEOUT_PILLS = 9 placements. Release is evaluated BEFORE earn (runner order).
                       Drop mechanics verbatim (adversary_search.adversarial_inject). Same earned volume as the blind
                       bursty baseline; only the TIMING differs (minus any volleys still banked at game end).
"""
from __future__ import annotations
import random

BANK_TIMEOUT_PILLS = 9
RELEASE_SALT = 0x5EED


# ---------------- VERBATIM from striker_model.py @1049308 (function bodies unchanged) ----------------
def scaffold_max_height(board):
    best = 0
    for c in range(board.cols):
        occ = [r for r in range(board.rows) if board.color[r, c] != 0]
        if not occ:
            continue
        h = 0
        r = occ[0]
        while (r < board.rows and board.color[r, c] != 0
               and not board.is_virus[r, c]):
            h += 1
            r += 1
        best = max(best, h)
    return best


def earn_volley(model, seed, pills_placed, clear_size):
    rng = random.Random(seed * 1000 + pills_placed)
    p_fire, _n = model.fire_probability(clear_size)
    if rng.random() >= p_fire:
        return 0
    n_cells, _cols = model.sample(seed, pills_placed)
    return n_cells


def drop_volley(board, n_cells, rng):
    from drmario.faithful_game import EMPTY, LINK_NONE

    if n_cells <= 0:
        return 0
    n_cols = max(1, min(board.cols, round(n_cells / 2)))
    cols = rng.sample(range(board.cols), n_cols)
    rows_per_col = max(1, n_cells // max(1, len(cols)))
    placed = 0
    for c in cols:
        if placed >= n_cells:
            break
        if board.color[0, c] != EMPTY:
            continue
        for _ in range(rows_per_col):
            if placed >= n_cells:
                break
            r = 0
            while r < board.rows and board.color[r, c] != EMPTY:
                r += 1
            if r >= board.rows:
                break
            board.color[r, c] = rng.randint(1, 3)
            board.is_virus[r, c] = False
            board.link[r, c] = LINK_NONE
            placed += 1
    if placed:
        board._apply_gravity()
        board.resolve()
    return placed
# ------------------------------------------------------------------------------------------------------


class OwnerBursty:
    def __init__(self, model, name="owner0804"):
        self.model, self.name = model, name

    def reset(self, seed):
        pass

    def after_placement(self, board, seed, pills_placed, clear_size):
        from bursty_model import inject_bursty_garbage
        if clear_size > 0:
            return inject_bursty_garbage(board, self.model, seed, pills_placed, clear_size)
        return 0


class Striker:
    def __init__(self, model, h_release=6, timeout=BANK_TIMEOUT_PILLS):
        self.model, self.h, self.timeout = model, int(h_release), int(timeout)
        self.name = f"striker{self.h}"
        self.reset(0)

    def reset(self, seed):
        self.bank = []; self.release_log = []; self.earned = 0

    def after_placement(self, board, seed, pills_placed, clear_size):
        landed = 0
        if self.bank:
            h_rel = scaffold_max_height(board)
            age_oldest = pills_placed - self.bank[0]["earned_pill"]
            age_newest = pills_placed - self.bank[-1]["earned_pill"]
            rng_rel = random.Random((seed * 1000 + pills_placed) ^ RELEASE_SALT)
            reason = "height" if h_rel >= self.h else ("timeout" if age_oldest >= self.timeout else None)
            if reason:
                sizes = [b["n_cells"] for b in self.bank]
                self.bank = []
                placed = 0
                for s in sizes:
                    placed += drop_volley(board, s, rng_rel)
                self.release_log.append({"pill": pills_placed, "reason": reason, "h_at_release": h_rel,
                                         "sizes": sizes, "placed": placed, "age_oldest": age_oldest,
                                         "age_newest": age_newest})
                landed = placed
        if clear_size > 0:
            n = earn_volley(self.model, seed, pills_placed, clear_size)
            if n > 0:
                self.bank.append({"earned_pill": pills_placed, "n_cells": n})
                self.earned += n
        return landed

    def summary(self):
        return {"releases": len(self.release_log),
                "height": sum(1 for e in self.release_log if e["reason"] == "height"),
                "timeout": sum(1 for e in self.release_log if e["reason"] == "timeout"),
                "earned": self.earned, "banked_undelivered": sum(b["n_cells"] for b in self.bank)}
