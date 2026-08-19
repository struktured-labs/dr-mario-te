#!/usr/bin/env python3
"""Lulu-proxy STRIKER: bank-and-strike garbage pressure timed to the
defender's construction window.

Mechanism (player_styles/dr_lulu.md dossier): dr. lulu keeps a low flat
stack and releases garbage exactly when the AI's scaffold is tall -- the
construction window.  No existing lab opponent times attacks; bursty fires
on the blind clear-triggered schedule, the drip fires on a fixed period.
This model EARNS volleys with the exact bursty-v1 fire/size draws (identical
random numbers at identical (seed, pills_placed) call points) but BANKS them
and RELEASES only when the defending AI's max stack height >= H_RELEASE, or
when the oldest banked volley times out.

BANK TIMEOUT derivation (documented, not invented): the fitted bursty model
(fit_struktured_20260804, n=53 gaps) has median inter-volley gap 15s / mean
22.7s and fires within k_seconds=5s of the earning clear.  At L11 tempo
(fall 13 f/row, tempo-chew memo; humans lock in ~2-3s with soft drop) a
placement is ~2.5s, so the mean natural inter-volley interval is ~9
placements.  BANK_TIMEOUT_PILLS = 9: the striker may delay a volley by at
most one natural inter-volley interval past its earn point -- any longer
would no longer be Lulu-plausible cadence (she strikes within her own
sending rhythm, she does not hoard for a whole game).

HEIGHT METRIC -- measured, not assumed: the dossier's trigger is "releases
garbage while the Stomper's SCAFFOLD is tall".  Raw max stack height at L11
is dominated by the virus field itself: measured over full clean champion
games (seeds 7/12/33, 2026-08-08) raw h_max never drops below 6 and sits at
median 10 -- so a raw-height predicate with H in {5,6,8} is vacuously
always-true at H<=6 and ~87%-true at H=8, degenerating the striker to
immediate release (the same duty-cycle collapse that killed reactive mode
#59).  The SCAFFOLD metric -- per column, the contiguous run of NON-virus
occupied cells from the top of the stack down to the first virus, maxed
over columns -- measures the AI's own construction and ranges 0..8 with
median 3-5 on the same games: H in {5,6,8} is a genuine sweep on it.
Default metric = "scaffold"; "stack" (raw) is kept selectable for the
literal reading.

Drop mechanics are VERBATIM adversary_search.adversarial_inject (first
empty row from top, unlinked single half LINK_NONE, color rng.randint(1,3),
skip cols full at row 0, cap at n_cells, then board._apply_gravity() BEFORE
board.resolve() -- the floating-at-row-0 trap).  Column policy: "random"
(pure timing test; spawn-targeting is a separate, already-proven lever --
ADVERSARY_FINDINGS.md + dr-mario-ci-overlap-false-negative.md -- and is
deliberately NOT conflated with timing here).

KILLED-MUTANT GATE: check_release_log() verifies every logged release was
height-justified (reason "height" -> h_at_release >= H) or timeout-justified
(reason "timeout" -> age_oldest >= timeout).  Mutant release predicates
("inverted": fire when h_max <= 2; "random": fire with p=0.15 per placement
regardless of height) log reason "height" ON PURPOSE so only the NUMERIC
check can catch them -- run_striker_ab.py --gate-demo demonstrates the
checker FAILS on both mutants and on the blind control's log.
"""
from __future__ import annotations

import random

H_RELEASE_DEFAULT = 6
BANK_TIMEOUT_PILLS = 9          # see derivation in the module docstring
EXPOSURE_H = 6                  # pre-registered exposure threshold
MUTANTS = ("none", "inverted", "random")
RANDOM_MUTANT_P = 0.15          # per-placement fire prob for the "random" mutant


def col_heights(board):
    """Per-column stack heights (0 = empty col), same convention as
    adversary_search._col_heights: height = rows - topmost occupied row."""
    import numpy as np
    heights = []
    for c in range(board.cols):
        occ = np.nonzero(board.color[:, c])[0]
        heights.append(int(board.rows - occ.min()) if len(occ) else 0)
    return heights


def max_height(board):
    return max(col_heights(board))


def scaffold_max_height(board):
    """Max over columns of the contiguous NON-virus occupied run at the top
    of the column's stack (0 for empty columns or virus-topped columns) --
    the AI's own construction, the dossier's 'scaffold'."""
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


HEIGHT_METRICS = ("scaffold", "stack")


def measure_height(board, metric):
    if metric == "scaffold":
        return scaffold_max_height(board)
    if metric == "stack":
        return max_height(board)
    raise ValueError(f"unknown height metric {metric!r}")


def earn_volley(model, seed, pills_placed, clear_size):
    """The EARN step: same draws as bursty_model.inject_bursty_garbage's
    decision step, byte-for-byte -- rng consumes one random() for the fire
    decision, then model.sample() re-seeds from the same (seed, pills)
    convention for the size draw.  Returns n_cells (0 = no volley earned).
    Columns are NOT drawn here: the board at release time differs, so column
    choice belongs to the release step."""
    rng = random.Random(seed * 1000 + pills_placed)
    p_fire, _n = model.fire_probability(clear_size)
    if rng.random() >= p_fire:
        return 0
    n_cells, _cols = model.sample(seed, pills_placed)
    return n_cells


def drop_volley(board, n_cells, rng):
    """VERBATIM drop mechanics of adversary_search.adversarial_inject
    (only the decision differs; the physics must not).  Returns halves
    actually placed (cols full to row 0 are skipped silently)."""
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
        # resolve() only runs gravity AFTER a clear step; a half parked at
        # row 0 with no match floats forever and fakes a spawn-block.
        board._apply_gravity()
        board.resolve()
    return placed


def release_fires(mutant, h_max, h_release, rng):
    """The timing predicate under test (and its non-equivalent mutants).
    "none" = the real striker: fire iff h_max >= h_release.
    "inverted" = fire in the trough (h_max <= 2) -- differs whenever the
      stack is mid-height or tall, non-equivalent by construction.
    "random" = fire with p=RANDOM_MUTANT_P regardless of height."""
    if mutant == "none":
        return h_max >= h_release
    if mutant == "inverted":
        return h_max <= 2
    if mutant == "random":
        return rng.random() < RANDOM_MUTANT_P
    raise ValueError(f"unknown mutant {mutant!r}")


def check_release_log(releases, h_release, timeout=BANK_TIMEOUT_PILLS):
    """The GATE: every release must be height- or timeout-justified.
    Returns a list of violation strings (empty = pass).  Demonstrated to
    FAIL on the inverted/random mutants and on the blind control's log
    (run_striker_ab.py --gate-demo) before being trusted -- the
    killed-mutant standard (dr-mario-gate-standard-killed-mutants.md)."""
    bad = []
    for ev in releases:
        reason = ev.get("reason")
        if reason == "height":
            if ev["h_at_release"] < h_release:
                bad.append(f"pill {ev['pill']}: height-release at "
                           f"h={ev['h_at_release']} < H={h_release}")
        elif reason == "timeout":
            if ev.get("age_oldest", 0) < timeout:
                bad.append(f"pill {ev['pill']}: timeout-release at "
                           f"age={ev.get('age_oldest')} < {timeout}")
        else:
            bad.append(f"pill {ev['pill']}: unjustified release reason "
                       f"{reason!r}")
    return bad


def build_blind_schedule(release_log, horizon, seed, min_pills):
    """VOLUME-MATCHED BLIND CONTROL schedule for one seed: the IDENTICAL
    multiset of volley sizes the striker actually released in that seed's
    game, at placement indices drawn uniform over [min_pills, horizon].

    `horizon` must be the striker game's LAST RELEASE pill index (its actual
    delivery window), NOT the game's final pills_placed: the 2026-08-08
    smoke (n=12, excluded from inference) drew over [25, final_pills] and
    left 92 volleys undelivered because indices landed after the blind
    game's own end -- blind delivered 48.4 halves/game vs striker 68.2, the
    exact volume confound this control exists to kill.  Matching the
    striker's delivery window keeps the volume honest; the residual
    undelivered tail (blind game ends before an index) is reported per run,
    broken down by blind outcome.

    Deterministic per seed; independent of the striker's release rng stream
    (different salt).  Returns a sorted list of (pills_index, n_cells)."""
    sizes = [s for ev in release_log for s in ev["sizes"]]
    rng = random.Random(seed * 99991 + 7)
    lo = min_pills
    hi = max(horizon, lo + 1)
    idxs = sorted(rng.randint(lo, hi) for _ in sizes)
    return list(zip(idxs, sizes))
