#!/usr/bin/env python3
"""FORCED-FIRST-MOVE-FROM-BOARD harness (task #112).

WHAT IT IS FOR. A VOD audit produces a claim of the form "that col-2 placement is
what killed him". Nothing in the existing rigs can price that claim: every rig
starts a game at pill 0 from a seed, so a board seen on a stream is unreachable.
This module takes an ARBITRARY transcribed board, forces move 1 to a SPECIFIED
placement, and then rolls the game forward under the ordinary champion decider on
FAIR capsule streams, so two candidate placements can be compared from the same
position.

THE FAIRNESS CONVENTION IS CAPSULE-REFORK. Both arms see the same forced pill
(`cur`) and the same set of continuation stream seeds; only the first placement
differs. A single shared continuation would price seed-peeking rather than the
placement (see memory `dr-mario-flip-fairness-screen`), so the deliverable is a
PAIRED delta over n>=17 independently sampled streams.

THREE TRAPS THIS CODE IS BUILT AROUND, all previously paid for:

  * `dr-mario-import-mutates-board` -- import must not alias or mutate the caller's
    arrays. `planes_from_spec` always allocates fresh arrays and `make_env` copies
    into the env's own buffers with `[:]`.
  * `dr-mario-deepcopy-pill-closure` -- a pill source shared by reference makes
    every branch of an experiment steal each other's capsules, and it fails
    SILENTLY: boards stay plausible and the run stays deterministic. Every rollout
    here builds its OWN `NesPillSource`, and the gate is a REPLAY, which is the
    only check that catches it.
  * `dr-mario-garbage-floats-at-row0` -- writing cells into `board.color` does not
    drop them; `resolve()` only runs gravity AFTER a clear step. `make_env` calls
    `_apply_gravity()` explicitly and REPORTS whether it moved anything, so a
    transcription that was not settled cannot pass silently as one that was.

LINK-PLANE CAVEAT (READ BEFORE BELIEVING A NUMBER). A board transcribed from a
video frame carries no link information -- you cannot see from a still which two
halves are still a capsule. With `lnk` absent this module imports every non-virus
cell as an UNLINKED single. That is exactly right until the first clear, and after
a clear it is a real physics deviation: a surviving half of a linked pair would
fall WITH its partner on the real ROM and falls ALONE here. Pass `lnk` when you
have it; otherwise treat cascade-heavy trajectories as approximate and say so.
"""
from __future__ import annotations

import os
import sys

ROWS, COLS = 16, 8
NCELL = ROWS * COLS

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = "/home/struktured/projects/dr_mario_rl"
QA = os.path.dirname(HERE)          # .../experiments
for _p in (HERE, QA, QA + "/eval47", QA + "/tuck_v3",
           ROOT + "/tmp/combo_term", ROOT + "/tmp/endgame", ROOT + "/tmp/tuck",
           ROOT + "/tmp/pillrng", ROOT + "/.claude/worktrees/faithful-sim/src"):
    if _p not in sys.path:
        sys.path.insert(0, _p)

GLYPH_TO_COLOR = {".": 0, " ": 0, "R": 1, "Y": 2, "B": 3}


# --------------------------------------------------------------------- import

class BoardSpecError(ValueError):
    """The transcribed board is not a board this harness will run."""


def planes_from_spec(spec):
    """Board spec (JSON dict) -> freshly allocated (color, is_virus, link) planes.

    Accepted shapes, all row-major with row 0 = TOP and colours 1=R 2=Y 3=B:
      * flat:  {"col": [128 ints], "vir": [128 0/1], "lnk": [128 ints]  (optional)}
      * rows:  {"rows": ["...RY..", ...]}  -- 16 strings of 8 glyphs, lowercase
               glyph = virus (matches FaithfulBoard.ascii()).

    `spec` is never read destructively and never retained.
    """
    import numpy as np

    if "rows" in spec:
        rows = spec["rows"]
        if len(rows) != ROWS or any(len(r) != COLS for r in rows):
            raise BoardSpecError(f"rows must be {ROWS} strings of {COLS} glyphs")
        col = [0] * NCELL
        vir = [0] * NCELL
        for r, line in enumerate(rows):
            for c, ch in enumerate(line):
                up = ch.upper()
                if up not in GLYPH_TO_COLOR:
                    raise BoardSpecError(f"bad glyph {ch!r} at ({r},{c})")
                col[r * COLS + c] = GLYPH_TO_COLOR[up]
                vir[r * COLS + c] = int(ch.islower() and up != ".")
        lnk = spec.get("lnk")
    else:
        try:
            col, vir, lnk = spec["col"], spec["vir"], spec.get("lnk")
        except KeyError as e:
            raise BoardSpecError(f"spec needs 'rows' or 'col'+'vir' (missing {e})")

    if len(col) != NCELL or len(vir) != NCELL:
        raise BoardSpecError(f"col/vir must be {NCELL} long, got {len(col)}/{len(vir)}")
    if lnk is not None and len(lnk) != NCELL:
        raise BoardSpecError(f"lnk must be {NCELL} long, got {len(lnk)}")

    color = np.array(col, dtype=np.int8).reshape(ROWS, COLS)
    is_virus = np.array(vir, dtype=bool).reshape(ROWS, COLS)
    link = (np.zeros((ROWS, COLS), dtype=np.int8) if lnk is None
            else np.array(lnk, dtype=np.int8).reshape(ROWS, COLS))

    if color.min() < 0 or color.max() > 3:
        raise BoardSpecError("colours must be 0..3")
    if (is_virus & (color == 0)).any():
        raise BoardSpecError("a cell is marked virus but has colour 0")
    if (link != 0)[is_virus].any():
        raise BoardSpecError("a virus cell carries a link (viruses are immovable)")
    _check_links(color, link)
    return color, is_virus, link


def _check_links(color, link):
    """Every link must point at an occupied cell that links back. A dangling link
    is tolerated by FaithfulBoard._bodies() as a silent single -- which means an
    inconsistent transcription would run, and run WRONG, without complaint."""
    from drmario.faithful_game import LINK_NONE, _DELTA, _OPP
    for r in range(ROWS):
        for c in range(COLS):
            lk = int(link[r, c])
            if lk == LINK_NONE:
                continue
            if color[r, c] == 0:
                raise BoardSpecError(f"empty cell ({r},{c}) carries link {lk}")
            dr, dc = _DELTA[lk]
            pr, pc = r + dr, c + dc
            if not (0 <= pr < ROWS and 0 <= pc < COLS):
                raise BoardSpecError(f"link at ({r},{c}) points off the board")
            if int(link[pr, pc]) != _OPP[lk] or color[pr, pc] == 0:
                raise BoardSpecError(f"link at ({r},{c}) is not reciprocated by ({pr},{pc})")


def make_env(planes, stream_seed, cur=None, nxt=None, stream_skip=0,
             level=11, max_pills=300, settle=True):
    """A FaithfulDrMarioEnv holding the imported board, with its OWN pill source.

    `cur`/`nxt` are (a, b) colour pairs; either may be None to draw from the
    stream instead. Returns (env, src, meta) where meta['settle_moved'] records
    whether importing needed gravity (True on an already-settled transcription
    means the transcription was wrong, or the link plane is).
    """
    from drmario.faithful_env import FaithfulDrMarioEnv, Pill
    from nes_pills import NesPillSource

    color, is_virus, link = planes
    env = FaithfulDrMarioEnv(level=level, seed=stream_seed, max_pills=max_pills)
    env.reset()                       # allocates the board; contents overwritten below
    src = NesPillSource(seed=stream_seed, skip=stream_skip)
    src.attach(env)                   # _PillDraw, not a lambda -- deepcopy-safe

    env.board.color[:] = color        # copy in; the caller's arrays stay untouched
    env.board.is_virus[:] = is_virus
    env.board.link[:] = link
    settle_moved = bool(env.board._apply_gravity()) if settle else False

    env.pills_placed = 0
    env._start_viruses = env.board.virus_count()
    env.cur = Pill(*cur) if cur is not None else env._rand_pill()
    env.nxt = Pill(*nxt) if nxt is not None else env._rand_pill()
    return env, src, {"settle_moved": settle_moved,
                      "viruses": env._start_viruses,
                      "cur": (int(env.cur.a), int(env.cur.b)),
                      "nxt": (int(env.nxt.a), int(env.nxt.b))}


# -------------------------------------------------------------------- actions

VARIANT_NAME = {0: "H_ab", 1: "H_ba", 2: "V_ab", 3: "V_ba"}


def legal_placements(env):
    """Every legal action for env.cur, with the cells it would occupy.

    Action encoding is the env's own: action = variant * 8 + col, variant
    0/1 = horizontal (ab / ba), 2/3 = vertical (a on top / b on top). This is the
    same integer `pressure_rig._choose_base` returns, so a forced action and a
    chosen action are directly comparable.
    """
    out = []
    for a in range(env.n_actions):
        orient, col, pill = env._decode(a)
        cells = env.board.resting_position(pill, orient, col)
        if cells is None:
            continue
        (r0, c0), (r1, c1) = cells
        out.append({"action": a, "variant": a // COLS, "col": a % COLS,
                    "orient": VARIANT_NAME[a // COLS],
                    "cells": [(r0, c0, int(pill.a)), (r1, c1, int(pill.b))],
                    "top_row": min(r0, r1)})
    return out


def resolve_forced(env, want):
    """Turn a human-written placement request into an action int, or raise.

    `want` is a dict with 'col' plus EITHER 'variant' (0..3 / 'H_ab'...) or
    'cells' (list of (row, col, colour) the placement must occupy, order-free).
    An optional 'row' is checked against the landing row -- a mismatch means the
    board or the request is wrong, and it raises rather than silently placing the
    piece somewhere else.
    """
    legal = legal_placements(env)
    cands = [p for p in legal if p["col"] == want["col"]]
    if "variant" in want:
        v = want["variant"]
        if isinstance(v, str):
            v = {n: k for k, n in VARIANT_NAME.items()}[v]
        cands = [p for p in cands if p["variant"] == v]
    if "cells" in want:
        target = sorted(tuple(int(x) for x in cc) for cc in want["cells"])
        cands = [p for p in cands if sorted(tuple(map(int, cc)) for cc in p["cells"]) == target]
    if "row" in want:
        cands = [p for p in cands if p["top_row"] == want["row"]]
    if len(cands) != 1:
        raise BoardSpecError(
            f"forced placement {want} matched {len(cands)} legal actions "
            f"(legal here: {[(p['action'], p['orient'], p['col'], p['top_row']) for p in legal]})")
    return cands[0]["action"]


# ------------------------------------------------------------------- rollouts

def board_key(board):
    """Cell-for-cell identity of a board, links included."""
    return (board.color.tobytes(), board.is_virus.tobytes(), board.link.tobytes())


class Decider:
    """The champion root chooser, as used by pressure_rig (same function, same
    weights), wrapped so a rollout can be re-run identically."""

    def __init__(self, wt=0, ws=20, level=11):
        import pressure_rig as PR
        PR._init(level, wt, ws)
        self.PR = PR
        self.C = dict(PR._C)

    def __call__(self, env):
        import root_search as RS
        from fb import FB
        C = self.C
        fb = FB.from_board(env.board)
        col, vir = RS.board_flat_from_fb(fb)
        a, _ = self.PR._choose_base(col, vir, int(env.cur.a), int(env.cur.b),
                                    int(env.nxt.a), int(env.nxt.b),
                                    C["w"], C["fl"], C["wt"], C["ws"])
        return a


DIES_AHEAD_VIRUS_THRESHOLD = 12   # same threshold as pressure_rig


def rollout(env, decider, horizon, forced_action=None, record=True, after_lock=None):
    """Play `horizon` pills from the current env state; move 1 is `forced_action`
    if given, every later move comes from `decider`.

    `after_lock(env, i)` runs once per fully-resolved placement and may return
    'topout' or 'clear' to end the rollout -- the hook the garbage injector uses,
    kept out of this function so the gate exercises the SAME code path the
    pricing does, minus the injection.

    Returns outcome stats plus, when `record`, a per-lock trajectory of board
    keys -- the only artifact strong enough to gate this harness, because a
    matching FINAL board can be reached by different play.
    """
    from terms47 import g_stranded, g_tower
    import root_search as RS
    from fb import FB

    traj = []
    res = "ran"
    v_at_end = None
    forced_ok = True

    for i in range(horizon):
        if env.board.virus_count() == 0:
            res = "clear"
            break
        if i == 0 and forced_action is not None:
            a = forced_action
            if not any(p["action"] == a for p in legal_placements(env)):
                forced_ok = False
                res = "forced_illegal"
                break
        else:
            a = decider(env)
        if a is None:
            res = "no_move"
            break
        pill = (int(env.cur.a), int(env.cur.b))
        _, _, term, trunc, info = env.step(int(a))
        if record:
            traj.append({"i": i, "action": int(a), "pill": pill,
                         "key": board_key(env.board),
                         "viruses": env.board.virus_count()})
        if term:
            res = "clear" if info["won"] else "topout"
            if res == "topout":
                v_at_end = env.board.virus_count()
            break
        if trunc:
            res = "truncated"
            break
        if after_lock is not None:
            ev = after_lock(env, i)
            if ev:
                res = ev
                if res == "topout":
                    v_at_end = env.board.virus_count()
                break

    fb = FB.from_board(env.board)
    col, vir = RS.board_flat_from_fb(fb)
    viruses_left = env.board.virus_count() if v_at_end is None else v_at_end
    return {
        "result": res,
        "forced_ok": forced_ok,
        "pills": len(traj),
        "topout": int(res == "topout"),
        "clear": int(res == "clear"),
        "survived": int(res in ("ran", "truncated", "clear")),
        "viruses_left": int(viruses_left),
        "viruses_cleared": int(env._start_viruses - viruses_left),
        "dies_ahead": int(res == "topout" and viruses_left <= DIES_AHEAD_VIRUS_THRESHOLD),
        "stranded_final": int(g_stranded(col, vir)),
        "tower_final": int(g_tower(col, vir, 8)),
        "max_height": int(env.board.column_heights().max()),
        "spawn_height": int(max(env.board.column_heights()[c] for c in (3, 4))),
        "traj": traj,
    }
