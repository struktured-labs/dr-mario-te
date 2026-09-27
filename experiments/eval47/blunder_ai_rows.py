#!/usr/bin/env python3
"""AI (champion) rows of the Dr. Mario BLUNDER BATTERY (task battery-5).

Produces the champion-side numbers that the human rows of
`experiments/eval47/battery4_compute.py` are to be compared against.  Every row
states the instrument it came from; rows no instrument here supports are printed
as `NOT COMPUTABLE: <reason>` rather than estimated.

THE HARD CONSTRAINT
-------------------
The fast sim (`FaithfulDrMarioEnv` / `fast_rtl_x` / `pressure_rig`) is TURN-BASED:
it has no frames and no wall clock.  NOTHING on the time axis is derived from it.
The only time-axis number below (row 5, drop speed) comes from the Mesen census
CSVs, which carry real 60 Hz NES frame counters.

ARM
---
Champion = wt=0, ws=20 (`terms47.g_stranded`), root-only base search on the
`fast_rtl_x.variant("winner")` leaf -- i.e. `eval47/ab47.py::_choose_base`, reused
here through `portfolio/endgame-policy/seal_probe.py::_choose_base` (same imports,
same call convention, same 128-cell row-major col/vir representation, row 0 = TOP,
colours 1-based).  No new decision logic is written here, only instrumentation.

SEED BLOCK
----------
`SEED0 + 2*k`, k = 0..N-1 (default 2000, 2002, ... 2498).  DISJOINT from
`seal_probe.py`'s published block (1000-1199) and from its out-of-sample block
(0-199) and from `jointdig/p0_corpus.py` (2-123).  Step 2 because the NES pill
LFSR gives seeds 2k and 2k+1 the IDENTICAL capsule stream (memory:
`dr-mario-seed-space-is-32767`); only the numpy-drawn virus layout differs, so
consecutive seeds are half-redundant games.  Verified empirically in the control
block.

GATES (a check that cannot fail proves nothing)
-----------------------------------------------
CONTROL BLOCK (prints first):
  * detector gate -- synthetic boards where the route/narrow seal detectors MUST
    fire and MUST NOT fire, plus mutant detectors that must break those asserts;
  * seed-degeneracy control -- 2k and 2k+1 share a pill stream (printed, so the
    step-2 block is justified by measurement, not assertion);
  * FIDELITY GATE -- `instrumented_play()` must reproduce the published prior-art
    loop `seal_probe.play()` EXACTLY on the gate seeds, on BOTH the game result
    (won/topout/pills/final virus count) AND the narrow seal/re-open event counts.
    This is the `jointdig/p0_corpus.py` pattern: the instrumented copy is only
    trusted because this comparison can fail.
  * referee cross-check -- the candidate-enumeration clone's cascade result must
    equal what the real engine's `resolve()` actually returned, every placement.

KILLED-MUTANT GATE (prints second, exits 1 if anything SURVIVES): every published
number carries a mutant that must CHANGE it.
"""
from __future__ import annotations

import argparse
import collections
import json
import os
import random
import statistics as st
import sys
from concurrent.futures import ProcessPoolExecutor

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = "/home/struktured/projects/dr_mario_rl"
QA = "/home/struktured/projects/dr-mario-qa-wt/experiments"
ENDGAME_POLICY = os.path.join(QA, "portfolio", "endgame-policy")
for _p in (ROOT + "/tmp/combo_term", ROOT + "/tmp/endgame", ROOT + "/tmp/tuck",
           ROOT + "/tmp/pillrng", ROOT + "/.claude/worktrees/faithful-sim/src", QA,
           QA + "/tuck_v3", QA + "/eval47", ENDGAME_POLICY):
    if _p not in sys.path:
        sys.path.insert(0, _p)

CENSUS_GLOB = "/mnt/data/drmario/pocket-copro/mesen_copro_qa/census/logs/**/census.csv"
RESULTS = os.path.join(HERE, "results")
OUT_JSON = os.path.join(RESULTS, "blunder_ai_rows.json")

ROWS, COLS, NCELL_ = 16, 8, 128
H0 = 8
SEAL_VC_THRESHOLD = 6       # identical to seal_probe.py, so the contrast is controlled
TIER_O_HORIZON = 3          # "within 3 pills"
GATE_SEEDS = (1000, 1001, 1002, 1003, 1004, 1005)

_C = {}


# ===========================================================================
# champion decision path -- VERBATIM from seal_probe.py::_choose_base, which is
# itself verbatim from eval47/ab47.py::_choose_base.  Do not edit.
# ===========================================================================
def _init(level, wt, ws):
    import numpy as np
    import fast_rtl_x as FX
    FX.warmup_ship_eh(topk2=8)
    w, fl = FX.variant("winner")
    from terms47 import g_tower, g_stranded
    z = np.zeros(128, dtype=np.int8)
    g_tower(z, z, H0)
    g_stranded(z, z)
    _C.update(level=level, wt=wt, ws=ws, w=w, fl=fl)


def _choose_base(col, vir, ca, cb, na, nb, w, fl, wt, ws):
    import numpy as np
    import fast_rtl_x as FX
    import root_search as RS
    from fast_sim_x import NCELL, _expand_core
    from terms47 import g_tower, g_stranded

    c1 = np.empty(NCELL, dtype=np.int8)
    v1 = np.empty(NCELL, dtype=np.int8)
    best_val, best_a, best_c1 = None, None, None
    for o4 in range(4):
        var = int(FX._VAR_OF_O4[o4])
        for cc in range(8):
            ok, nv, cells = _expand_core(col, vir, var, cc, ca, cb, c1, v1)
            if ok == 0:
                continue
            val = RS._root_value(c1, v1, nv, cells, na, nb, 8,
                                 FX._W_EXCAV_SHIP, FX._W_HANG_SHIP, w, fl)
            if wt:
                val -= wt * g_tower(c1, v1, H0)
            if ws:
                val -= ws * g_stranded(c1, v1)
            if best_val is None or val > best_val:
                best_val, best_a, best_c1 = val, var * 8 + cc, c1.copy()
    return best_a, best_c1


# ===========================================================================
# geometry: reachability, access ROUTES, narrow cover
# ===========================================================================
def landing_row(col, c):
    """Row a dropped half comes to rest on in column `c` (row 0 = TOP).

    = (topmost occupied row) - 1, or ROWS-1 for an empty column, or -1 when the
    column is occupied all the way to the top (nothing can enter it)."""
    for r in range(ROWS):
        if col[r * COLS + c] != 0:
            return r - 1
    return ROWS - 1


def _window_ok(col, cells, x, need_reach=True, need_colour=True):
    """`cells` (flat indices) is a candidate line window for colour `x`.

    Qualifies when every cell is EMPTY or colour `x` (`need_colour`) and every
    EMPTY cell is reachable from above, i.e. at or above its column's landing row
    (`need_reach`).  Returns the set of columns of its empty cells (the ROUTES the
    window offers), or None when the window does not qualify."""
    empt_cols = set()
    for idx in cells:
        v = col[idx]
        if v == 0:
            r, c = divmod(idx, COLS)
            if need_reach and r > landing_row(col, c):
                return None
            empt_cols.add(c)
        elif need_colour and v != x:
            return None
    return empt_cols


def virus_routes(col, vir, i, need_reach=True, need_colour=True):
    """ACCESS ROUTES of the virus at flat index `i`: the set of COLUMNS from which
    matching material can still be dropped in to complete a line-of-4 through it.

    A route exists when some length-4 window containing the virus is
    all-same-colour-or-empty AND its empty cells are reachable from above.  The
    routes that window offers are the columns of its empty cells (for a vertical
    window that is the virus's own column; for a horizontal one it is wherever the
    gaps are).  Strictly RICHER than the narrow `covered directly above` detector:
    a same-colour cover leaves the vertical route alive, and a horizontal route
    survives a cover entirely."""
    r0, c0 = divmod(i, COLS)
    x = col[i]
    routes = set()
    for cs in range(max(0, c0 - 3), min(COLS - 4, c0) + 1):      # horizontal
        got = _window_ok(col, [r0 * COLS + cs + k for k in range(4)], x,
                         need_reach, need_colour)
        if got:
            routes |= got
    for rs in range(max(0, r0 - 3), min(ROWS - 4, r0) + 1):      # vertical
        got = _window_ok(col, [(rs + k) * COLS + c0 for k in range(4)], x,
                         need_reach, need_colour)
        if got:
            routes |= got
    return routes


def pred_route(col, vir, i):
    """SEALED (route definition): the virus has ZERO access routes left."""
    return len(virus_routes(col, vir, i)) == 0


def pred_route_noreach(col, vir, i):        # MUTANT: reachability ignored
    return len(virus_routes(col, vir, i, need_reach=False)) == 0


def pred_route_nocolour(col, vir, i):       # MUTANT: colour compatibility ignored
    return len(virus_routes(col, vir, i, need_colour=False)) == 0


def pred_narrow(col, vir, i):
    """SEALED (narrow definition, seal_probe.py / endgame-policy REPORT.md): the
    cell DIRECTLY ABOVE holds non-virus material of a DIFFERENT colour."""
    r, _c = divmod(i, COLS)
    if r == 0:
        return False
    j = i - COLS
    return col[j] != 0 and vir[j] == 0 and col[j] != col[i]


def pred_narrow_nocolour(col, vir, i):      # MUTANT: colour check dropped
    r, _c = divmod(i, COLS)
    if r == 0:
        return False
    j = i - COLS
    return col[j] != 0 and vir[j] == 0


def window_alive(col, cells, x):
    """Is a recorded clear window still completable? (tier-O opportunity liveness)"""
    return _window_ok(col, cells, x) is not None


# ===========================================================================
# seal / re-open transition tracker
# ===========================================================================
class SealTracker:
    """OPEN -> SEALED fires a seal event; SEALED -> OPEN fires a re-open event.

    `gated=True` reproduces seal_probe.py exactly: the tracker is only advanced on
    steps where 0 < virus_count <= SEAL_VC_THRESHOLD, so a virus already sealed
    when the endgame window opens fires a seal event on entry.  `gated=False`
    tracks the whole game."""

    def __init__(self, pred, gated):
        self.pred, self.gated = pred, gated
        self.state = set()
        self.seals, self.reopens = [], []
        self.cleared_while_sealed = 0
        self.ever_sealed = collections.Counter()

    def update(self, col, vir, vc, pill_idx):
        if self.gated and not (0 < vc <= SEAL_VC_THRESHOLD):
            return
        live = {i for i in range(NCELL_) if vir[i]}
        for i in list(self.state):
            if i not in live:                     # virus went away while SEALED
                self.cleared_while_sealed += 1
                self.state.discard(i)
        for i in live:
            sealed = self.pred(col, vir, i)
            was = i in self.state
            if sealed and not was:
                self.state.add(i)
                self.seals.append((pill_idx, int(vc), i))
                self.ever_sealed[i] += 1
            elif not sealed and was:
                self.state.discard(i)
                self.reopens.append((pill_idx, int(vc), i))

    def summary(self):
        return {"seals": len(self.seals), "reopens": len(self.reopens),
                "viruses_ever_sealed": len(self.ever_sealed),
                "cleared_while_sealed": self.cleared_while_sealed,
                "still_sealed_at_end": len(self.state),
                "seal_events": self.seals, "reopen_events": self.reopens}


TRACKERS = (
    ("narrow_gated", pred_narrow, True),
    ("route_gated", pred_route, True),
    ("narrow_all", pred_narrow, False),
    ("route_all", pred_route, False),
    # mutants (never published on their own; only used to kill the gate)
    ("M_narrow_nocolour_gated", pred_narrow_nocolour, True),
    ("M_route_noreach_gated", pred_route_noreach, True),
    ("M_route_nocolour_gated", pred_route_nocolour, True),
)


# ===========================================================================
# candidate enumeration (tier-O + cascade sizes), refereed by the real engine
# ===========================================================================
def enumerate_clearing_candidates(env, col, vir):
    """Every legal placement of the CURRENT pill that clears something.

    Two-stage, for speed and for correctness: the numba `_expand_core` cap-1
    targeted resolve is EXACT as a yes/no first-step clear test (the board was
    settled, only the two placed cells are new, so any new run must contain one of
    them) -- so `cells == 0` provably rules out a cascade too.  The survivors are
    then re-simulated on a CLONE of the real `FaithfulBoard`, whose `resolve()`
    runs clear -> link-aware gravity -> clear to FIXPOINT and returns
    (total_cells, viruses, chain).  `total_cells` is summed over all cascade steps,
    which is the ROM's combo-counter rule.

    Returns {action: (total_cells, viruses, chain, first_step_mask_cells)}."""
    import numpy as np
    import fast_rtl_x as FX
    from fast_sim_x import NCELL, _expand_core

    c1 = np.empty(NCELL, dtype=np.int8)
    v1 = np.empty(NCELL, dtype=np.int8)
    out = {}
    ca, cb = int(env.cur.a), int(env.cur.b)
    for o4 in range(4):
        var = int(FX._VAR_OF_O4[o4])
        for cc in range(8):
            ok, _nv, cells = _expand_core(col, vir, var, cc, ca, cb, c1, v1)
            if ok == 0 or cells == 0:
                continue
            a = var * 8 + cc
            orient, colnum, pill = env._decode(a)
            b = env.board.clone()
            if not b.place_pill(pill, orient, colnum):
                continue
            mask = b._find_clears()
            first = [int(r) * COLS + int(c) for r, c in zip(*np.where(mask))]
            total, vcl, chain = b.resolve()
            out[a] = (int(total), int(vcl), int(chain), first)
    return out


def best_window(col_after_place, first_cells):
    """The dominant line the argmax candidate would have completed: the largest
    same-colour group of its first clear step.  (A single step can retire two
    lines of different colours; the opportunity is the bigger one.)"""
    by = collections.defaultdict(list)
    for idx in first_cells:
        by[int(col_after_place[idx])].append(idx)
    x, cells = max(by.items(), key=lambda kv: len(kv[1]))
    return int(x), sorted(cells)


# ===========================================================================
# play loops
# ===========================================================================
def baseline_play(seed):
    """UNINSTRUMENTED champion loop -- the fidelity-gate reference twin."""
    from drmario.faithful_env import FaithfulDrMarioEnv
    from nes_pills import NesPillSource
    from fb import FB
    import root_search as RS

    level, wt, ws, w, fl = _C["level"], _C["wt"], _C["ws"], _C["w"], _C["fl"]
    env = FaithfulDrMarioEnv(level=level, seed=seed, max_pills=300)
    env.reset()
    NesPillSource(seed=seed).attach(env)
    env.cur = env._rand_pill()
    env.nxt = env._rand_pill()
    res, final_vc = "stall", None
    for _ in range(300):
        fb = FB.from_board(env.board)
        vc0 = fb.virus_count()
        final_vc = vc0
        if vc0 == 0:
            res = "clear"
            break
        col, vir = RS.board_flat_from_fb(fb)
        a, _c1b = _choose_base(col, vir, int(env.cur.a), int(env.cur.b),
                               int(env.nxt.a), int(env.nxt.b), w, fl, wt, ws)
        if a is None:
            break
        _, _, term, trunc, info = env.step(int(a))
        final_vc = env.board.virus_count()
        if term:
            res = "clear" if info["won"] else "topout"
            break
        if trunc:
            break
    return {"seed": seed, "won": int(res == "clear"), "topout": int(res == "topout"),
            "stall": int(res == "stall"), "pills": env.pills_placed,
            "final_virus_count": int(final_vc) if final_vc is not None else None}


def instrumented_play(seed):
    """The same loop with instrumentation bolted on.  Every added call is either a
    read of the board or a simulation on a CLONE; nothing touches `env`'s RNG,
    pill cursor or board, so this is result-identical to `baseline_play` by
    construction -- and the fidelity gate proves it rather than asserting it."""
    import numpy as np
    from drmario.faithful_env import FaithfulDrMarioEnv
    from nes_pills import NesPillSource
    from fb import FB
    import root_search as RS

    level, wt, ws, w, fl = _C["level"], _C["wt"], _C["ws"], _C["w"], _C["fl"]
    env = FaithfulDrMarioEnv(level=level, seed=seed, max_pills=300)
    env.reset()
    NesPillSource(seed=seed).attach(env)
    env.cur = env._rand_pill()
    env.nxt = env._rand_pill()

    # referee tap: record exactly what the real engine's resolve() returned
    resolved = []
    _orig_resolve = env.board.resolve

    def _spy_resolve():
        out = _orig_resolve()
        resolved.append(out)
        return out
    env.board.resolve = _spy_resolve

    trackers = [(name, SealTracker(pred, gated)) for name, pred, gated in TRACKERS]
    placements = []          # (var, total_cells, viruses, chain, first_step_cells)
    avail_sizes = []         # S_t over decisions where a clear was available
    watches, tier_o = [], []
    referee_agree, referee_total = 0, 0
    res, final_vc = "stall", None

    for pill_idx in range(300):
        fb = FB.from_board(env.board)
        vc0 = fb.virus_count()
        final_vc = vc0
        if vc0 == 0:
            res = "clear"
            break
        col, vir = RS.board_flat_from_fb(fb)
        cands = enumerate_clearing_candidates(env, col, vir)
        s_t = max((v[0] for v in cands.values()), default=0)
        if s_t > 0:
            avail_sizes.append(s_t)
            best_a = max(cands, key=lambda k: cands[k][0])

        a, _c1b = _choose_base(col, vir, int(env.cur.a), int(env.cur.b),
                               int(env.nxt.a), int(env.nxt.b), w, fl, wt, ws)
        if a is None:
            break

        # window of the DECLINED opportunity, recorded before the board changes
        pending_watch = None
        if s_t > 0 and a not in cands:
            orient, colnum, pill = env._decode(best_a)
            bb = env.board.clone()
            bb.place_pill(pill, orient, colnum)
            wx, wcells = best_window(bb.color.reshape(-1), cands[best_a][3])
            pending_watch = {"pill": pill_idx, "size": s_t, "colour": wx,
                             "cells": wcells, "first_size": len(cands[best_a][3]),
                             "destroyed_k": None, "cashed_window_k": None,
                             "cashed_alt_k": None}

        n_before = len(resolved)
        _, _, term, trunc, info = env.step(int(a))
        tot, vcl, chain = resolved[-1] if len(resolved) > n_before else (0, 0, 0)
        placements.append((a // 8, int(tot), int(vcl), int(chain),
                           len(cands[a][3]) if a in cands else 0))
        referee_total += 1
        referee_agree += int((cands[a][0] if a in cands else 0) == int(tot)
                             and (cands[a][2] if a in cands else 0) == int(chain))

        fb2 = FB.from_board(env.board)
        vc1 = fb2.virus_count()
        final_vc = vc1
        col2, vir2 = fb2.col, fb2.vir
        for _name, tr in trackers:
            tr.update(col2, vir2, vc1, pill_idx)

        # ---- tier-O watch bookkeeping -------------------------------------
        # cashed_window_k : the RECORDED window itself cleared (its cells are a
        #                   subset of what this placement's FIRST clear step
        #                   removed -- pre-gravity, so the coordinates line up).
        # cashed_alt_k    : the line the champion took instead paid at least as
        #                   much within the horizon ("the alternative cashed").
        chosen_first = set(cands[a][3]) if a in cands else set()
        if pending_watch is not None:
            watches.append(pending_watch)
        for wobj in list(watches):
            k = pill_idx - wobj["pill"]
            if k >= 1:
                if wobj["cashed_alt_k"] is None and tot >= wobj["size"]:
                    wobj["cashed_alt_k"] = k
                if set(wobj["cells"]) <= chosen_first:
                    # the window itself cleared -> the watch is RESOLVED here.  It
                    # must not also be scored "destroyed": a cleared window empties
                    # and is instantly refilled from above by gravity, which would
                    # otherwise read as destruction one line later.
                    wobj["cashed_window_k"] = k
                    tier_o.append(wobj)
                    watches.remove(wobj)
                    continue
            if wobj["destroyed_k"] is None and not window_alive(col2, wobj["cells"],
                                                                wobj["colour"]):
                wobj["destroyed_k"] = k
            if k >= TIER_O_HORIZON:
                tier_o.append(wobj)
                watches.remove(wobj)

        if term:
            res = "clear" if info["won"] else "topout"
            break
        if trunc:
            break
    tier_o.extend(watches)

    out = {"seed": seed, "won": int(res == "clear"), "topout": int(res == "topout"),
           "stall": int(res == "stall"), "pills": env.pills_placed,
           "final_virus_count": int(final_vc) if final_vc is not None else None,
           "placements": placements, "avail_sizes": avail_sizes,
           "tier_o": tier_o, "referee_agree": referee_agree,
           "referee_total": referee_total,
           "trackers": {name: tr.summary() for name, tr in trackers}}
    return out


def _strip(d):
    return {k: d[k] for k in ("seed", "won", "topout", "stall", "pills",
                              "final_virus_count")}


# ===========================================================================
# CONTROL BLOCK
# ===========================================================================
def detector_gate():
    """Synthetic boards where the detectors MUST fire / MUST NOT fire, plus mutant
    detectors that must break at least one of those asserts."""
    import numpy as np
    ok = True

    def blank():
        return np.zeros(NCELL_, dtype=np.int8), np.zeros(NCELL_, dtype=np.int8)

    # (a) lone virus on the floor of an empty column: routes alive (vertical +
    #     horizontal), narrow says OPEN.
    col, vir = blank()
    i = 15 * COLS + 3
    col[i], vir[i] = 1, 1
    assert virus_routes(col, vir, i), "lone virus must have routes"
    assert not pred_route(col, vir, i) and not pred_narrow(col, vir, i)

    # (b) SAME-colour cover directly above.  narrow: OPEN (colour matches).
    #     route: still OPEN -- the vertical route is alive through the cover.
    col, vir = blank()
    col[i], vir[i] = 1, 1
    col[i - COLS] = 1
    assert not pred_narrow(col, vir, i) and not pred_route(col, vir, i)

    # (c) DIFFERENT-colour cover directly above.  narrow: SEALED.  route: still
    #     OPEN, because the virus's own ROW is empty -> a horizontal line-of-4 can
    #     still be built.  THIS IS THE HEADLINE CONTRAST.
    col, vir = blank()
    col[i], vir[i] = 1, 1
    col[i - COLS] = 2
    assert pred_narrow(col, vir, i), "narrow must fire on a mismatched cover"
    assert not pred_route(col, vir, i), "route must NOT fire while the row is open"

    # (d) COLOUR-poisoned: every horizontal window through the virus carries a
    #     mismatched cell (gaps at cols 4,5 are still REACHABLE, so only colour
    #     rules them out) and the column above is mismatched too.
    def board_d():
        col, vir = blank()
        col[i], vir[i] = 1, 1
        col[15 * COLS + 2] = 2          # poisons windows [0-3],[1-4],[2-5]
        col[15 * COLS + 6] = 2          # poisons window  [3-6]
        for r in range(12, 15):
            col[r * COLS + 3] = 2       # poisons the only vertical window
        return col, vir
    col, vir = board_d()
    assert pred_route(col, vir, i), "route must fire when every window is poisoned"
    assert pred_narrow(col, vir, i)

    # (e) REACHABILITY-poisoned: the vertical window is colour-clean but its empty
    #     cells sit under an overhang, so nothing can be dropped into them; the row
    #     is mismatched on both sides.  (Synthetic overhang -- legal in Dr. Mario
    #     when the covering half's partner is supported.)
    def board_e():
        col, vir = blank()
        col[i], vir[i] = 1, 1
        col[15 * COLS + 2] = 2
        col[15 * COLS + 6] = 2
        col[12 * COLS + 3] = 1          # matching cap, rows 13/14 left empty
        return col, vir
    col, vir = board_e()
    assert pred_route(col, vir, i), "route must fire when nothing can be dropped in"

    # ---- mutant detectors: each must FAIL a case the real one passes ----
    def probe(pred, board_case):
        col, vir, want = board_case
        return pred(col, vir, i) == want

    # case (c) is the discriminator for the narrow colour check
    colc, virc = blank()
    colc[i], virc[i] = 1, 1
    colc[i - COLS] = 1                       # SAME colour: narrow must stay OPEN
    m1 = not probe(pred_narrow_nocolour, (colc, virc, False))
    print(f"  detector mutant: narrow drops the colour check              "
          f"{'KILLED' if m1 else '*** SURVIVED'}")
    ok &= m1

    # case (e) is the discriminator for the route reachability check
    m2 = not probe(pred_route_noreach, board_e() + (True,))
    print(f"  detector mutant: route drops the reachability check         "
          f"{'KILLED' if m2 else '*** SURVIVED'}")
    ok &= m2

    # case (d) is the discriminator for the route colour check
    m3 = not probe(pred_route_nocolour, board_d() + (True,))
    print(f"  detector mutant: route drops the colour check               "
          f"{'KILLED' if m3 else '*** SURVIVED'}")
    ok &= m3

    # window_alive must reject a covered window (tier-O liveness)
    colw, virw = blank()
    cells = [15 * COLS + c for c in range(4)]
    colw[cells[0]] = 1
    assert window_alive(colw, cells, 1)
    colw[cells[1]] = 2
    m4 = not window_alive(colw, cells, 1)
    print(f"  detector mutant: window_alive on a poisoned window          "
          f"{'KILLED' if m4 else '*** SURVIVED'}")
    ok &= m4
    return ok


def seed_degeneracy_control():
    """2k and 2k+1 share the NES capsule stream -- print the measurement that
    justifies the step-2 seed block instead of asserting it."""
    from drmario.faithful_env import FaithfulDrMarioEnv
    from nes_pills import NesPillSource
    import hashlib

    def fingerprint(s):
        env = FaithfulDrMarioEnv(level=_C["level"], seed=s, max_pills=300)
        env.reset()
        NesPillSource(seed=s).attach(env)
        pills = tuple((p.a, p.b) for p in (env._rand_pill() for _ in range(12)))
        return hashlib.md5(env.board.color.tobytes()).hexdigest()[:8], pills

    b0, p0 = fingerprint(2000)
    b1, p1 = fingerprint(2001)
    b2, p2 = fingerprint(2002)
    same_stream = (p0 == p1) and (p0 != p2)
    diff_board = (b0 != b1)
    print(f"  seed control: stream(2000)==stream(2001) {p0 == p1}, "
          f"stream(2000)!=stream(2002) {p0 != p2}, board(2000)!=board(2001) {diff_board}"
          f"  -> {'step-2 block JUSTIFIED' if same_stream and diff_board else '*** UNEXPECTED'}")
    return same_stream and diff_board


def fidelity_gate():
    """`instrumented_play` must reproduce the PUBLISHED prior-art loop
    `portfolio/endgame-policy/seal_probe.py::play` exactly -- both the game result
    and its narrow seal/re-open event counts -- and must equal the local
    uninstrumented twin."""
    import importlib.util
    spec = importlib.util.spec_from_file_location(
        "seal_probe_prior", os.path.join(ENDGAME_POLICY, "seal_probe.py"))
    sp = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(sp)
    sp._C.update(_C)

    ok = True
    for s in GATE_SEEDS:
        ref = sp.play(s)
        base = baseline_play(s)
        mine = instrumented_play(s)
        same_result = _strip(ref) == _strip(mine) == _strip(base)
        nar = mine["trackers"]["narrow_gated"]
        same_detector = (nar["seals"] == ref["n_seal_events"]
                         and nar["reopens"] == ref["n_reopen_events"])
        ok &= same_result and same_detector
        print(f"  seed {s}: result {'MATCH' if same_result else '*** MISMATCH'} "
              f"(won={mine['won']} pills={mine['pills']} vc={mine['final_virus_count']})"
              f"  narrow-detector {'MATCH' if same_detector else '*** MISMATCH'} "
              f"(seals {nar['seals']}/{ref['n_seal_events']}, "
              f"reopens {nar['reopens']}/{ref['n_reopen_events']})")
    return ok


# ===========================================================================
# corpus reduction + rows
# ===========================================================================
def orient_split(placements, horiz=(0, 1)):
    h = sum(1 for p in placements if p[0] in horiz)
    return h, len(placements) - h


def pct(a, b):
    return (100.0 * a / b) if b else float("nan")


def decile(xs, q=0.90):
    if not xs:
        return None
    s = sorted(xs)
    k = min(len(s) - 1, int(q * (len(s) - 1) + 0.9999))
    return s[k]


def reduce_corpus(rows):
    R = {}
    placements = [p for r in rows for p in r["placements"]]
    R["n_games"] = len(rows)
    R["n_placements"] = len(placements)
    R["won"] = sum(r["won"] for r in rows)
    R["topout"] = sum(r["topout"] for r in rows)
    R["stall"] = sum(r["stall"] for r in rows)
    R["mean_pills"] = st.mean([r["pills"] for r in rows]) if rows else 0.0

    # --- row 1: orientation of VIRUS-clearing placements -------------------
    vclear = [p for p in placements if p[2] > 0]
    h, v = orient_split(vclear)
    R["row1"] = {"n": len(vclear), "horiz": h, "vert": v, "horiz_pct": pct(h, len(vclear))}

    # --- row 2: cascade share of clear events ------------------------------
    clears = [p for p in placements if p[1] > 0]
    casc = [p for p in clears if p[3] >= 2]
    R["row2"] = {
        "n_clear_events": len(clears), "n_cascade": len(casc),
        "cascade_pct": pct(len(casc), len(clears)),
        "chain_hist": dict(sorted(collections.Counter(p[3] for p in clears).items())),
        "mean_cells_all": st.mean([p[1] for p in clears]) if clears else 0.0,
        "mean_cells_cascade": st.mean([p[1] for p in casc]) if casc else 0.0,
        "mean_cells_single": (st.mean([p[1] for p in clears if p[3] == 1])
                              if any(p[3] == 1 for p in clears) else 0.0),
        "n_virus_clear_cascade": sum(1 for p in casc if p[2] > 0),
    }

    # --- row 3: seals ------------------------------------------------------
    R["row3"] = {}
    for name, _pred, _g in TRACKERS:
        s = [r["trackers"][name] for r in rows]
        tot = sum(x["seals"] for x in s)
        R["row3"][name] = {
            "seals": tot, "reopens": sum(x["reopens"] for x in s),
            "games_with_seal": sum(1 for x in s if x["seals"] > 0),
            "cleared_while_sealed": sum(x["cleared_while_sealed"] for x in s),
            "still_sealed_at_end": sum(x["still_sealed_at_end"] for x in s),
            "seals_per_game": tot / len(rows) if rows else 0.0,
            "reopen_rate": pct(sum(x["reopens"] for x in s), tot),
            "per_game": [x["seals"] for x in s],
        }

    # --- row 4: tier-O -----------------------------------------------------
    sizes = [s for r in rows for s in r["avail_sizes"]]
    d9 = decile(sizes)
    watches = [w for r in rows for w in r["tier_o"]]
    R["row4"] = {"d9": d9, "n_avail_decisions": len(sizes),
                 "n_declines": len(watches),
                 "avail_size_hist": dict(sorted(collections.Counter(sizes).items()))}
    for tag, sel in (("topdecile", lambda w: w["size"] >= d9),
                     ("any_size", lambda w: True)):
        sub = [w for w in watches if sel(w)]
        # "the window never cashed" is NOT a separate condition here, and adding it
        # would be an EQUIVALENT mutant twice over: (i) a window-cash resolves the
        # watch, so `destroyed_k is not None` already implies it, and (ii) cashing
        # the window IS a clear of >= the declined size, so it always sets
        # cashed_alt_k in the same step.  Only the two independent conditions run.
        evap = [w for w in sub if w["destroyed_k"] is not None
                and w["cashed_alt_k"] is None]
        R["row4"][tag] = {
            "n_declines": len(sub), "n_evaporated": len(evap),
            "per_100_placements": pct(len(evap), R["n_placements"]),
            "destroyed": sum(1 for w in sub if w["destroyed_k"] is not None),
            "cashed_window": sum(1 for w in sub if w["cashed_window_k"] is not None),
            "cashed_alt": sum(1 for w in sub if w["cashed_alt_k"] is not None),
            "survived_horizon": sum(1 for w in sub if w["destroyed_k"] is None),
            "destroyed_k_hist": dict(sorted(collections.Counter(
                w["destroyed_k"] for w in sub if w["destroyed_k"] is not None).items())),
        }
    R["_watches"] = watches
    R["_placements"] = placements
    R["referee_agree"] = sum(r["referee_agree"] for r in rows)
    R["referee_total"] = sum(r["referee_total"] for r in rows)
    return R


def mutant_gate(R, rows):
    """Every mutant must CHANGE a published number.  Equivalent mutants are
    failures of the gate, not passes."""
    ok = True

    def rep(label, hit, detail):
        nonlocal ok
        print(f"  mutant: {label:<52s} {'KILLED' if hit else '*** SURVIVED'}  {detail}")
        ok &= bool(hit)

    P = R["_placements"]

    # row 1
    h, v = R["row1"]["horiz"], R["row1"]["vert"]
    h2, v2 = orient_split([p for p in P if p[2] > 0], horiz=(2, 3))
    rep("row1 orientation classes swapped", (h, v) != (h2, v2), f"{h}/{v} -> {h2}/{v2}")
    h3, v3 = orient_split(P)
    rep("row1 every placement counted as clearing", (h, v) != (h3, v3),
        f"{h}/{v} -> {h3}/{v3}")
    h4, v4 = orient_split([p for p in P if p[1] > 0])   # ANY clear, not virus clear
    rep("row1 any-cell clear instead of virus-count drop", (h, v) != (h4, v4),
        f"{h}/{v} -> {h4}/{v4}")

    # row 2
    base = R["row2"]["cascade_pct"]
    clears = [p for p in P if p[1] > 0]
    mut = pct(sum(1 for p in clears if p[3] >= 1), len(clears))
    rep("row2 cascade threshold chain>=1 instead of >=2", abs(base - mut) > 1e-9,
        f"{base:.2f}% -> {mut:.2f}%")
    b_sz, m_sz = R["row2"]["mean_cells_all"], st.mean([p[4] for p in clears])
    rep("row2 size = FIRST step only (breaks ROM combo sum)", abs(b_sz - m_sz) > 1e-9,
        f"{b_sz:.2f} -> {m_sz:.2f} cells")

    # row 3
    for mname, real in (("M_narrow_nocolour_gated", "narrow_gated"),
                        ("M_route_noreach_gated", "route_gated"),
                        ("M_route_nocolour_gated", "route_gated")):
        a, b = R["row3"][real]["seals"], R["row3"][mname]["seals"]
        rep(f"row3 {mname}", a != b, f"{real} {a} -> {b} seals")
    a, b = R["row3"]["narrow_gated"]["seals"], R["row3"]["route_gated"]["seals"]
    rep("row3 narrow and route are NOT the same detector", a != b,
        f"narrow {a} vs route {b} seals")

    # row 4
    W = R["_watches"]
    d9 = R["row4"]["d9"]
    # Row 4 publishes TWO counts (top-decile and any-size); a mutant qualifies when
    # it moves the PAIR.  Scoring against the top-decile count alone would let a
    # mutant pass as "equivalent" purely because that bucket is small.
    def evap(cond, td_only):
        return sum(1 for w in W if (w["size"] >= d9 or not td_only) and cond(w))

    basep = (R["row4"]["topdecile"]["n_evaporated"], R["row4"]["any_size"]["n_evaporated"])
    for label, cond in (
        ("row4 drop the 'alternative never cashed' condition",
         lambda w: w["destroyed_k"] is not None),
        ("row4 drop the 'destroyed' condition",
         lambda w: w["cashed_alt_k"] is None),
        (f"row4 horizon {TIER_O_HORIZON} pills -> 1 pill",
         lambda w: w["destroyed_k"] is not None and w["destroyed_k"] <= 1
         and (w["cashed_alt_k"] is None or w["cashed_alt_k"] > 1)),
    ):
        mutp = (evap(cond, True), evap(cond, False))
        rep(label, basep != mutp, f"(topdecile,any) {basep} -> {mutp} events")
    rep("row4 top-decile filter actually selects", basep[0] != basep[1],
        f"topdecile {basep[0]} vs any-size {basep[1]} events")
    return ok


# ===========================================================================
# row 5 -- MESEN CENSUS (the ONLY time-axis source)
# ===========================================================================
def census_rows():
    import csv
    import glob
    files = sorted(glob.glob(CENSUS_GLOB, recursive=True))
    out, hdrs, empty = [], collections.Counter(), 0
    for f in files:
        with open(f) as fh:
            rd = csv.DictReader(fh)
            if rd.fieldnames is None:
                empty += 1
                continue
            hdrs[tuple(rd.fieldnames)] += 1
            top = os.path.relpath(f, CENSUS_GLOB.split("**")[0]).split(os.sep)[0]
            for r in rd:
                r["_file"], r["_top"] = f, top
                out.append(r)
    return out, hdrs, empty, len(files)


def cells_of(r):
    """`newcells` is the board delta at lock, formatted `row:col:TILEHEX`."""
    o = []
    for p in r["newcells"].split(";"):
        if not p:
            continue
        a, b, _t = p.split(":")
        o.append((int(a), int(b)))
    return o


def census_drop_speed():
    rows, hdrs, empty, nfiles = census_rows()
    ok = [r for r in rows if r["flag"] == "ok"]
    cols_union = sorted({c for h in hdrs for c in h})
    keep, spawn_row, bad = [], 0, 0
    per_top = collections.defaultdict(list)
    for r in ok:
        cs = cells_of(r)
        if not cs:
            bad += 1
            continue
        if any(rr == 0 for rr, _cc in cs):     # spawn-row lock -> tracker artifact
            spawn_row += 1
            continue
        d = int(r["lock_f"]) - int(r["go_f"])
        keep.append(d)
        per_top[r["_top"]].append(d)
    # orientation of virus-clearing placements, silicon side (DIFFERENT ARM);
    # plus the lock -> next-GO gap, which BOUNDS how far the GO strobe can be from
    # the true spawn frame (it is the whole inter-pill interval: clear animation +
    # respawn + driver reaction), and the level check (viruses on the first pill).
    h = v = unk = 0
    gap, first_vc = [], collections.Counter()
    byfile = collections.defaultdict(list)
    for r in ok:
        byfile[r["_file"]].append(r)
    for f, rs in byfile.items():
        rs.sort(key=lambda r: int(r["seq"]))
        seen_round = set()
        for r in rs:
            if r["round"] not in seen_round:
                seen_round.add(r["round"])
                first_vc[int(r["vc_go"])] += 1
        for i in range(len(rs) - 1):
            a, b = rs[i], rs[i + 1]
            if a["round"] == b["round"]:
                gap.append(int(b["go_f"]) - int(a["lock_f"]))
            if a["round"] != b["round"] or int(b["vc_go"]) >= int(a["vc_go"]):
                continue
            cs = cells_of(a)
            if len(cs) != 2:
                unk += 1
            elif cs[0][0] == cs[1][0] and abs(cs[0][1] - cs[1][1]) == 1:
                h += 1
            elif cs[0][1] == cs[1][1] and abs(cs[0][0] - cs[1][0]) == 1:
                v += 1
            else:
                unk += 1
    return {"files": nfiles, "empty_files": empty, "header_variants": len(hdrs),
            "columns": cols_union, "rows": len(rows), "ok": len(ok),
            "flags": dict(collections.Counter(r["flag"] for r in rows)),
            "n": len(keep), "spawn_row_excluded": spawn_row, "unparsable": bad,
            "min": min(keep) if keep else None, "max": max(keep) if keep else None,
            "median": st.median(keep) if keep else None,
            "mean": st.mean(keep) if keep else None,
            "p25": decile(keep, 0.25), "p75": decile(keep, 0.75),
            "per_corpus": {k: {"n": len(x), "median": st.median(x),
                               "min": min(x), "max": max(x)}
                           for k, x in sorted(per_top.items())},
            "orient_clearing": {"horiz": h, "vert": v, "unknown": unk,
                                "horiz_pct": pct(h, h + v)},
            "lock_to_next_go": {"n": len(gap), "min": min(gap) if gap else None,
                                "median": st.median(gap) if gap else None,
                                "mean": st.mean(gap) if gap else None},
            "first_pill_virus_count": dict(first_vc)}


# ===========================================================================
def boot_ci(xs, n=10000, seed=12345):
    if not xs:
        return (float("nan"), float("nan"))
    rng = random.Random(seed)
    k = len(xs)
    reps = sorted(st.mean([xs[rng.randrange(k)] for _ in range(k)]) for _ in range(n))
    return reps[int(0.025 * n)], reps[int(0.975 * n)]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--games", type=int, default=250)
    ap.add_argument("--seed0", type=int, default=2000)
    ap.add_argument("--step", type=int, default=2)
    ap.add_argument("--level", type=int, default=11)
    ap.add_argument("--workers", type=int, default=6)
    ap.add_argument("--wt", type=int, default=0)
    ap.add_argument("--ws", type=int, default=20)
    a = ap.parse_args()
    assert a.workers <= 6, "budget: never more than 6 worker processes"
    seeds = [a.seed0 + a.step * k for k in range(a.games)]

    print("=" * 78)
    print("BLUNDER BATTERY -- AI (CHAMPION) ROWS")
    print(f"arm: wt={a.wt} ws={a.ws} (g_stranded), root-only base search on "
          f"fast_rtl_x.variant('winner'); L{a.level}")
    print(f"seed block: {seeds[0]}..{seeds[-1]} step {a.step} (n={len(seeds)}) -- "
          f"disjoint from seal_probe 1000-1199 / out-of-sample 0-199 / p0_corpus 2-123")
    print("=" * 78)

    print("\nCONTROL BLOCK")
    _init(a.level, a.wt, a.ws)
    dg = detector_gate()
    sd = seed_degeneracy_control()
    print("  fidelity gate (vs published portfolio/endgame-policy/seal_probe.py::play):")
    fg = fidelity_gate()
    if not (dg and sd and fg):
        print("CONTROL BLOCK FAILED -- not reporting numbers")
        return 1
    print("  CONTROL: PASS")

    print(f"\n  running corpus: {len(seeds)} games, {a.workers} workers ...", flush=True)
    rows = []
    with ProcessPoolExecutor(max_workers=a.workers, initializer=_init,
                             initargs=(a.level, a.wt, a.ws)) as ex:
        for r in ex.map(instrumented_play, seeds, chunksize=4):
            rows.append(r)
            if len(rows) % 50 == 0:
                print(f"    {len(rows)}/{len(seeds)}", flush=True)
    R = reduce_corpus(rows)
    print(f"  corpus: {R['n_games']} games, {R['n_placements']} placements, "
          f"won {R['won']} topout {R['topout']} stall {R['stall']}, "
          f"mean {R['mean_pills']:.1f} pills/game")
    ref_ok = R["referee_agree"] == R["referee_total"]
    print(f"  referee cross-check (candidate clone == engine resolve): "
          f"{R['referee_agree']}/{R['referee_total']} "
          f"{'PASS' if ref_ok else '*** FAIL'}")
    if not ref_ok:
        print("CONTROL BLOCK FAILED -- not reporting numbers")
        return 1

    print("\nKILLED-MUTANT GATE")
    if not mutant_gate(R, rows):
        print("GATE FAILED -- not reporting numbers")
        return 1
    print("  GATE: PASS")

    cs = census_drop_speed()
    n = R["n_placements"]

    print("\n" + "=" * 78)
    print(f"AI ROWS  (champion, L{a.level}, n={R['n_games']} games / {n} placements)")
    print("=" * 78)

    r1 = R["row1"]
    print(f"\n 1. ORIENTATION OF VIRUS-CLEARING PLACEMENTS   [fast sim, champion]")
    print(f"    n={r1['n']} virus-clearing placements of {n}  "
          f"HORIZONTAL {r1['horiz']} ({r1['horiz_pct']:.1f}%)  "
          f"VERTICAL {r1['vert']} ({100 - r1['horiz_pct']:.1f}%)")
    print(f"    [same semantics as battery4_compute.py metric 1: counted when the VIRUS")
    print(f"     COUNT DROPS after the pill locks; split is the orientation of the")
    print(f"     CLEARING PILL (action//8 in 0,1 = H / HF), not of the cleared line]")
    co = cs["orient_clearing"]
    print(f"    silicon cross-reference, DIFFERENT ARM (Mesen census, d1-greedy Lua")
    print(f"     brain, NOT the champion): n={co['horiz'] + co['vert']}  "
          f"H {co['horiz']} ({co['horiz_pct']:.1f}%)  V {co['vert']} "
          f"({100 - co['horiz_pct']:.1f}%)  unclassifiable {co['unknown']}")

    r2 = R["row2"]
    print(f"\n 2. CASCADE / COMBO SHARE OF CLEAR EVENTS      [fast sim, champion]")
    print(f"    clear events n={r2['n_clear_events']}  CASCADE (chain>=2) "
          f"{r2['n_cascade']} ({r2['cascade_pct']:.1f}%)  "
          f"single-step {r2['n_clear_events'] - r2['n_cascade']} "
          f"({100 - r2['cascade_pct']:.1f}%)")
    print(f"    chain-length histogram: {r2['chain_hist']}")
    print(f"    mean cells cleared (SUMMED over cascade steps, the ROM combo-counter")
    print(f"     rule): all {r2['mean_cells_all']:.2f}  cascades {r2['mean_cells_cascade']:.2f}"
          f"  single-step {r2['mean_cells_single']:.2f}")
    print(f"    cascades that took a virus: {r2['n_virus_clear_cascade']}/{r2['n_cascade']}")

    print(f"\n 3. TIER-F ANALOG -- SELF-SEAL                 [fast sim, champion]")
    print(f"    NARROW vs ROUTE, both on the same corpus and the same vc<={SEAL_VC_THRESHOLD} gate:")
    for name, label in (("narrow_gated", "NARROW (cell directly above is non-matching"
                                         " non-virus)"),
                        ("route_gated", "ROUTE  (zero access-route columns remain)")):
        d = R["row3"][name]
        lo, hi = boot_ci(d["per_game"])
        print(f"      {label}")
        print(f"        seals {d['seals']} over {R['n_games']} games = "
              f"{d['seals_per_game']:.3f}/game [{lo:.3f},{hi:.3f}] 95% CI  |  "
              f"games with >=1 seal {d['games_with_seal']} "
              f"({pct(d['games_with_seal'], R['n_games']):.1f}%)")
        print(f"        re-opened later {d['reopens']} ({d['reopen_rate']:.1f}% of seals)"
              f"  |  virus cleared WHILE STILL SEALED {d['cleared_while_sealed']}"
              f"  |  still sealed at game end {d['still_sealed_at_end']}")
    nar, rou = R["row3"]["narrow_gated"], R["row3"]["route_gated"]
    print(f"      CONTRAST: the narrow detector fires {nar['seals']} times, the route")
    print(f"      detector {rou['seals']}. A mismatched cover blocks only the VERTICAL")
    print(f"      route; the virus's own ROW is usually still open, which is why")
    print(f"      REPORT.md found 42/126 narrow seals ended with the virus cleared")
    print(f"      WHILE STILL COVERED (here: {nar['cleared_while_sealed']} narrow vs "
          f"{rou['cleared_while_sealed']} route).")
    print(f"    whole-game (ungated) variants, for scale:")
    for name in ("narrow_all", "route_all"):
        d = R["row3"][name]
        print(f"      {name:12s} seals {d['seals']} ({d['seals_per_game']:.3f}/game)  "
              f"reopens {d['reopens']} ({d['reopen_rate']:.1f}%)  "
              f"cleared-while-sealed {d['cleared_while_sealed']}")

    r4 = R["row4"]
    td = r4["topdecile"]
    print(f"\n 4. TIER-O ANALOG -- EVAPORATED OPPORTUNITY    [fast sim, champion]")
    print(f"    decisions with a clear available: {r4['n_avail_decisions']}/{n}  "
          f"top-decile size threshold D9 = {r4['d9']} cells")
    print(f"    declined (a clear was available, the champion played a non-clearing move):"
          f" {r4['n_declines']}  of which top-decile {td['n_declines']}")
    print(f"    of those top-decile declines: destroyed within {TIER_O_HORIZON} pills "
          f"{td['destroyed']}, still alive at the horizon {td['survived_horizon']}, "
          f"the WINDOW itself later cashed {td['cashed_window']}, the alternative "
          f"line cashed >= the declined size {td['cashed_alt']}")
    print(f"    EVAPORATED (destroyed uncashed AND the alternative never cashed) "
          f"{td['n_evaporated']}  = {td['per_100_placements']:.3f} per 100 placements")
    print(f"    (any-size comparison: {r4['any_size']['n_evaporated']} events = "
          f"{r4['any_size']['per_100_placements']:.3f} per 100 placements)")
    print(f"    destroyed-at-pill-offset histogram (0 = the declining move itself): "
          f"{td['destroyed_k_hist']}")

    print(f"\n 5. DROP SPEED spawn->lock IN 60 fps FRAMES    [MESEN CENSUS ONLY]")
    if not cs["n"]:
        print(f"    NOT COMPUTABLE: no usable rows under {CENSUS_GLOB} "
              f"({cs['files']} files, {cs['rows']} rows). The fast sim cannot "
              f"substitute -- it is turn-based, with no frames and no wall clock.")
        cs["not_computable"] = "no usable census rows"
        _dump(a, seeds, R, cs, rows)
        return 0
    print(f"    source: {cs['files']} census.csv ({cs['empty_files']} empty), "
          f"{cs['header_variants']} header variants, {cs['rows']} rows, flags {cs['flags']}")
    print(f"    columns present: {','.join(cs['columns'])}")
    print(f"    n={cs['n']} pills ({cs['spawn_row_excluded']} spawn-row locks excluded, "
          f"same control as battery4 metric 2)")
    print(f"    min {cs['min']} f ({cs['min'] / 60:.2f} s)  max {cs['max']} f "
          f"({cs['max'] / 60:.2f} s)  median {cs['median']:.0f} f  "
          f"mean {cs['mean']:.1f} f  IQR [{cs['p25']},{cs['p75']}]")
    for k, x in cs["per_corpus"].items():
        print(f"      {k:20s} n={x['n']:5d}  median {x['median']:.0f} f  "
              f"range [{x['min']},{x['max']}]")
    lg = cs["lock_to_next_go"]
    print(f"    level parity with the fast-sim rows: viruses on the first pill of every "
          f"round = {cs['first_pill_virus_count']} -> L11 (4*(11+1)=48), the same level")
    print(f"    the champion corpus above was played at.")
    print(f"    DIFFERS FROM THE HUMAN METRIC IN TWO NAMED WAYS:")
    print(f"      (a) the clock starts at the DRIVER'S GO STROBE to the copro "
          f"($5084 write),")
    print(f"          not at the ROM's spawn frame. The census cannot separate the "
          f"two; what")
    print(f"          it BOUNDS is the whole lock->next-GO interval (clear animation + "
          f"respawn")
    print(f"          + driver reaction): n={lg['n']} min {lg['min']} f, median "
          f"{lg['median']:.0f} f, mean {lg['mean']:.1f} f. The GO offset is somewhere")
    print(f"          inside that, so row 5 is an UNDER-estimate of the "
          f"human-comparable")
    print(f"          spawn->lock lifetime by an unmeasured amount <= that gap;")
    print(f"      (b) the placement is chosen by the census harness's d1-greedy Lua "
          f"brain,")
    print(f"          NOT the champion (tools/census/census_run*.lua all embed the same")
    print(f"          `d1 greedy color-matching brain`). Drop time is dominated by "
          f"gravity")
    print(f"          and the driver's nav, but the TARGET distribution is a different")
    print(f"          arm's, so read this as the copro-cart AI, not as the champion.")
    print(f"    lock frame is detected in endFrame from the >=2-new-cell board delta, "
          f"so it")
    print(f"    carries up to 1 frame of detection latency.")

    print(f"\n NOT COMPUTABLE")
    print(f"    * champion drop-speed / any per-pill timing for the CHAMPION arm: no "
          f"Mesen")
    print(f"      census run exists that is driven by the wt=0/ws=20 search -- every")
    print(f"      census_run*.lua serves a d1-greedy Lua brain. The fast sim cannot "
          f"supply")
    print(f"      it: it is turn-based, with no frames and no wall clock.")
    print(f"    * rotation-direction split (battery4 metric 3): the champion emits a")
    print(f"      (variant, column) placement, never a rotation SEQUENCE; there is no")
    print(f"      cw/ccw/tog event to count. The census logs a final orientation "
          f"(co4 /")
    print(f"      capor_lock) but no rotation sequence either.")
    print(f"    * decision latency (think time): the census's res_f/done_f are the "
          f"harness's")
    print(f"      OWN synthetic CEN_RLAT/CEN_DLAT constants, not a measured search "
          f"time.")

    _dump(a, seeds, R, cs, rows)
    return 0


def _dump(a, seeds, R, cs, rows):
    os.makedirs(RESULTS, exist_ok=True)
    payload = {
        "arm": {"wt": a.wt, "ws": a.ws, "level": a.level,
                "search": "root-only base, fast_rtl_x.variant('winner') + terms47.g_stranded",
                "loop": "eval47/ab47.py::_choose_base via portfolio/endgame-policy/seal_probe.py"},
        "seed_block": {"seed0": seeds[0], "step": a.step, "n": len(seeds),
                       "last": seeds[-1],
                       "disjoint_from": ["seal_probe 1000-1199", "seal_probe oos 0-199",
                                         "p0_corpus 2-123"]},
        "corpus": {k: R[k] for k in ("n_games", "n_placements", "won", "topout",
                                     "stall", "mean_pills", "referee_agree",
                                     "referee_total")},
        "row1_orientation_virus_clearing": R["row1"],
        "row2_cascade": R["row2"],
        "row3_selfseal": {k: {kk: vv for kk, vv in v.items() if kk != "per_game"}
                          for k, v in R["row3"].items()},
        "row4_tier_o": {k: v for k, v in R["row4"].items() if not k.startswith("_")},
        "row5_drop_speed_mesen": cs,
        "not_computable": [
            "champion-arm drop speed / per-pill timing (no champion-driven Mesen "
            "census exists; fast sim is turn-based, no frames)",
            "rotation-direction split (no rotation sequence in either source)",
            "decision latency (census res_f/done_f are synthetic harness constants)",
        ],
        "per_game": [{k: r[k] for k in ("seed", "won", "topout", "stall", "pills",
                                        "final_virus_count")} for r in rows],
    }
    with open(OUT_JSON, "w") as fh:
        json.dump(payload, fh, indent=1, default=str)
    print(f"\nwrote {OUT_JSON}")


if __name__ == "__main__":
    sys.exit(main())
