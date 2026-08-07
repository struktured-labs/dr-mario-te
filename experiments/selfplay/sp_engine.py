#!/usr/bin/env python3
"""Shared engine for the SELF-PLAY + LEARNED-EVAL program.

WHAT THIS IS FOR
----------------
Stage 1 of the program asks a single falsifiable question: *how much better could
ANY leaf evaluator make the shipped depth-3 search?* Answering it needs two things
the existing A/B rigs do not provide:

  1. A champion decider usable as a ROLLOUT policy. `ab47._choose_base` (the champion:
     fast_rtl_x.variant("winner") + g_stranded ws=20 applied root-only) drives its
     32-action loop from PYTHON; `champ_root` below fuses that identical loop into ONE
     njit kernel.

     ⚠ CORRECTION (hetzner-node measurement, 2026-08-06). An earlier version of this
     docstring attributed the ~190 ms/move to "paying a numba call boundary per action".
     THAT WAS WRONG, and it was my inference rather than a measurement. Interleaved A/B
     over 8 whole games: 141.1 s reference vs 129.1 s fused = 1.09x, so the 32 call
     boundaries are only ~8% of the cost. The other ~92% is inside
     `_ply2plus_value_ship_eh` -- the depth-2+ subtree per candidate -- which was
     ALREADY njit. Fusing the outer loop cannot give a large multiple because the outer
     loop was never where the time went.

     Kept so nobody re-plans against the wrong premise: a rollout costs ~8 s and
     Monte-Carlo labelling stays expensive. A real speedup must come from the INNER
     search (smaller topk2, cheaper leaf, shallower rollouts), and each of those changes
     the policy -- so it stops being the champion and needs its own gate plus an argument
     for why the label still means anything.

  2. The ability to RESUME a game from an arbitrary stored position with a fresh
     pill stream (a rollout), which the seed-coupled ab47 `play()` cannot do.

BIT-EXACTNESS IS THE WHOLE POINT of (1): a "faster champion" that plays even slightly
differently silently changes the baseline every downstream number is measured against.
`gate()` proves champ_root reproduces `_choose_base` action-for-action AND
value-for-value on random real boards. Per the house rule, the gate asserts the
ARTEFACT (chosen action + float value), not that the code merely ran.

THE LINK PLANE (a real trap, not a nicety)
------------------------------------------
`root_search.board_flat_from_fb` exports only (col, vir). The faithful sim's board
ALSO carries a `link` plane, and gravity is link-aware -- a still-linked pill half
drags its partner. A position restored from (col, vir) alone therefore has SUBTLY
DIFFERENT future dynamics than the position it was sampled from, which would show up
as label noise attributed to the eval. Every corpus position here stores (col, vir,
link) and `set_board` restores all three.

CONVENTIONS (do not rediscover -- see CLAUDE.md / the tuck_v3 header)
  boards are 128-byte row-major, idx = r*8 + c, row 0 = TOP, colours are 1-BASED
  (0 = empty, 1..3 = colour); o4 {0,1} = VERT, {2,3} = HORIZ, variant = o4 XOR 2;
  action id = variant*8 + column.
"""
from __future__ import annotations

import os
import sys

ROOT = "/home/struktured/projects/dr_mario_rl"

# DECIDE-PATH WORKTREE, PINNED DELIBERATELY TO ONE TREE.
# root_search / terms47 / fast_rtl_x exist in BOTH dr-mario-main-wt and
# dr-mario-qa-wt. Resolving them by whichever happens to land on sys.path first is
# the exact configuration that already produced a silent divergence on the Hetzner
# node: a file edited 12 minutes after an rsync made two nodes run different code,
# and the only visible symptom was one hash field on one rare seed -- result, pills,
# viruses_left and move count all matched. So the tree is named once, here, and
# `provenance()` below stamps the actual bytes into every run's output.
DECIDE_TREE = "/home/struktured/projects/dr-mario-main-wt/experiments"
for _p in (ROOT + "/tmp/combo_term", ROOT + "/tmp/endgame", ROOT + "/tmp/tuck",
           ROOT + "/tmp/pillrng", ROOT + "/.claude/worktrees/faithful-sim/src",
           DECIDE_TREE, DECIDE_TREE + "/tuck_v3", DECIDE_TREE + "/eval47"):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import numpy as np
from numba import njit, int8, int32, int64, float64

import fast_rtl_x as FX
from fast_sim_x import NCELL, _expand_core, _virus_count
import root_search as RS
from root_search import _ply2plus_value_ship_eh
from terms47 import g_stranded, g_tower
from fb import FB
import fb as fb_mod
import fast_sim_x as fast_sim_mod
import terms47 as terms_mod

# ------------------------------------------------------------------ champion spec
# Champion baseline == fast_rtl_x.variant("winner") + g_stranded ws=20 applied
# root-only, exactly as eval47/ab47.py::_choose_base runs it (wt=0, so g_tower is
# NOT applied -- ab47 guards it behind `if wt:`).
WS_CHAMP = 20
TOPK2 = 8
LEVEL = 11

_VAR_OF_O4 = FX._VAR_OF_O4          # [2, 3, 0, 1] -- o4 order is VERT then HORIZ
R_WVIR, R_WCELLS, R_VBONUS = FX.R_WVIR, FX.R_WCELLS, FX.R_VBONUS
WIN_SHIP = FX._WIN_SHIP
W_EXCAV, W_HANG = int(FX._W_EXCAV_SHIP), int(FX._W_HANG_SHIP)


@njit(cache=True, fastmath=False)
def champ_root(pcol, pvir, ca, cb, na, nb, topk2, w_excav, w_hang, w, fl, ws,
               out_val, out_ok):
    """Fused champion root search. Fills out_val[32]/out_ok[32] and returns best action.

    Arithmetic is a line-by-line transcription of ab47._choose_base:
      val = RS._root_value(c1, v1, nv, cells, na, nb, 8, W_EXCAV, W_HANG, w, fl)
            - ws * g_stranded(c1, v1)
    with _root_value inlined (imm1 in float64 + the int64 ply2plus block cast to
    float64), the SAME o4-major iteration order, and the SAME strictly-greater
    keep-first tie-break. Returns -1 if no action is legal.
    """
    c1 = np.empty(NCELL, dtype=int8)
    v1 = np.empty(NCELL, dtype=int8)
    for i in range(32):
        out_ok[i] = 0
        out_val[i] = 0.0
    best_val = 0.0
    best_act = -1
    have = False
    for o4 in range(4):
        var = _VAR_OF_O4[o4]
        for cc in range(8):
            ok, nv, cells = _expand_core(pcol, pvir, var, cc, ca, cb, c1, v1)
            if ok == 0:
                continue
            imm1 = (float64(w[R_WVIR]) * nv + float64(w[R_WCELLS]) * cells
                    + (float64(w[R_VBONUS]) if nv >= 2 else float64(0.0)))
            if _virus_count(v1) == 0:
                val = imm1 + float64(WIN_SHIP)
            else:
                val = imm1 + float64(_ply2plus_value_ship_eh(
                    c1, v1, int64(na), int64(nb), int64(topk2),
                    int64(w_excav), int64(w_hang), w, fl))
            val -= float64(ws) * float64(g_stranded(c1, v1))
            a = var * 8 + cc
            out_val[a] = val
            out_ok[a] = 1
            if not have or val > best_val:
                best_val = val
                best_act = a
                have = True
    return best_act


def provenance():
    """sha256 of every source on the decide path, plus a rolled hash and the RESOLVED
    file of each imported module.

    Stamp this into any run's output. A remote node -- or a second worktree on this
    box -- running a snapshot of an actively-edited tree drifts by default, and the
    failure mode is not a crash: it is two runs that agree on every summary statistic
    and disagree on one field of one rare case. Recording the bytes is what makes that
    detectable after the fact instead of unfalsifiable.
    """
    import hashlib
    out = {}
    # sp_engine itself is included: it CONTAINS champ_root, so a manifest that
    # hashed only the imported modules would miss a change to the champion decider
    # -- the single most important thing on the decide path.
    import sp_engine as _self
    for mod in (FX, RS, fb_mod, fast_sim_mod, terms_mod, _self):
        f = getattr(mod, "__file__", None)
        if not f or not os.path.exists(f):
            continue
        h = hashlib.sha256(open(f, "rb").read()).hexdigest()
        out[mod.__name__] = {"file": f, "sha256": h}
    rolled = hashlib.sha256(
        "".join(f"{k}:{v['sha256']}" for k, v in sorted(out.items())).encode()
    ).hexdigest()
    return {"decide_tree": DECIDE_TREE, "modules": out, "rolled": rolled}


class Champion:
    """Champion decider + scratch buffers. One instance per worker process."""

    def __init__(self, ws=WS_CHAMP, topk2=TOPK2):
        FX.warmup_ship_eh(topk2=topk2)
        self.w, self.fl = FX.variant("winner")
        self.ws = int(ws)
        self.topk2 = int(topk2)
        self.val = np.zeros(32, dtype=np.float64)
        self.ok = np.zeros(32, dtype=np.int8)

    def values(self, col, vir, ca, cb, na, nb):
        """(best_action, val[32], ok[32]) -- buffers are REUSED, copy if retaining."""
        a = champ_root(col, vir, int(ca), int(cb), int(na), int(nb), self.topk2,
                       W_EXCAV, W_HANG, self.w, self.fl, self.ws, self.val, self.ok)
        return a, self.val, self.ok

    def choose(self, col, vir, ca, cb, na, nb):
        return champ_root(col, vir, int(ca), int(cb), int(na), int(nb), self.topk2,
                          W_EXCAV, W_HANG, self.w, self.fl, self.ws, self.val, self.ok)


# ---------------------------------------------------------------- board plumbing
def board_planes(board):
    """(col, vir, link) as flat int8[128] -- the FB.from_board flatten, row-major."""
    return (board.color.reshape(-1).astype(np.int8),
            board.is_virus.reshape(-1).astype(np.int8),
            board.link.reshape(-1).astype(np.int8))


def set_board(board, col, vir, link):
    """Inverse of board_planes. Restores the LINK plane too (gravity is link-aware)."""
    board.color = np.asarray(col, dtype=np.int8).reshape(16, 8).copy()
    board.is_virus = np.asarray(vir, dtype=bool).reshape(16, 8).copy()
    board.link = np.asarray(link, dtype=board.link.dtype).reshape(16, 8).copy()


def new_env(level=LEVEL, seed=0, cap=300):
    from drmario.faithful_env import FaithfulDrMarioEnv
    env = FaithfulDrMarioEnv(level=level, seed=seed, max_pills=cap)
    env.reset()
    return env


def attach_stream(env, stream_seed):
    from nes_pills import NesPillSource
    NesPillSource(seed=stream_seed).attach(env)
    return env


def set_pills(env, ca, cb, na, nb):
    from drmario.faithful_env import Pill
    env.cur = Pill(int(ca), int(cb))
    env.nxt = Pill(int(na), int(nb))


# --------------------------------------------------------------------- rollouts
def play_from(env, champ, cap, force_first=None, trace=None):
    """Play the champion from env's CURRENT state to termination.

    Returns (outcome, pills_used) where outcome in {"clear","topout","stall"} and
    pills_used counts placements made BY THIS CALL. `force_first`, if given, is
    played as the first action instead of the champion's pick -- that is how a
    specific root action gets its value estimated under the champion's own play.

    `trace`, if a list, is appended with the virus count after EVERY pill. One
    full-horizon rollout then yields the truncated value at every horizon T for
    free, so the labelling horizon can be calibrated from evidence rather than
    guessed -- which matters because a rollout is the dominant cost in Stage 1.
    """
    used = 0
    first = force_first
    for _ in range(cap):
        if env.board.virus_count() == 0:
            return "clear", used
        if first is not None:
            a = first
            first = None
        else:
            col, vir, _lk = board_planes(env.board)
            a = champ.choose(col, vir, env.cur.a, env.cur.b, env.nxt.a, env.nxt.b)
            if a < 0:
                return "topout", used
        _o, _r, term, trunc, info = env.step(int(a))
        used += 1
        if trace is not None:
            trace.append(int(env.board.virus_count()))
        if term:
            return ("clear" if info["won"] else "topout"), used
        if trunc:
            return "stall", used
    return "stall", used


def rollout_value(pos, action, stream_seed, champ, cap=300, level=LEVEL, env=None,
                  trace=None):
    """MC sample of the champion's value of taking `action` at `pos`.

    Returns (outcome, pills_used). The pill stream is supplied by `stream_seed`;
    holding stream_seed FIXED across the actions of one position is the common-random
    -numbers pairing that makes the between-action comparison low-variance.
    """
    if env is None:
        env = new_env(level=level, seed=0, cap=cap)
    attach_stream(env, stream_seed)
    set_board(env.board, pos["col"], pos["vir"], pos["link"])
    set_pills(env, pos["ca"], pos["cb"], pos["na"], pos["nb"])
    env.pills_placed = 0
    env._start_viruses = env.board.virus_count()
    return play_from(env, champ, cap, force_first=action, trace=trace)


# ------------------------------------------------------------------------- gate
def gate(n=200, seed=20260806, verbose=True):
    """Prove champ_root == ab47._choose_base on real champion-trajectory boards.

    Asserts the ARTEFACT: the chosen action AND the per-action float value must match
    exactly, on boards drawn from actual play (not random noise), across the whole
    game arc. A pass here is what licenses using champ_root as the rollout policy.
    """
    import random
    champ = Champion()
    w, fl = champ.w, champ.fl

    def choose_base_py(col, vir, ca, cb, na, nb):
        """ab47._choose_base, wt=0/ws=WS_CHAMP, verbatim."""
        c1 = np.empty(NCELL, dtype=np.int8)
        v1 = np.empty(NCELL, dtype=np.int8)
        best_val, best_a = None, None
        vals = {}
        for o4 in range(4):
            var = int(FX._VAR_OF_O4[o4])
            for cc in range(8):
                ok, nv, cells = _expand_core(col, vir, var, cc, ca, cb, c1, v1)
                if ok == 0:
                    continue
                val = RS._root_value(c1, v1, nv, cells, na, nb, 8,
                                     FX._W_EXCAV_SHIP, FX._W_HANG_SHIP, w, fl)
                val -= WS_CHAMP * g_stranded(c1, v1)
                vals[var * 8 + cc] = val
                if best_val is None or val > best_val:
                    best_val, best_a = val, var * 8 + cc
        return best_a, vals

    rng = random.Random(seed)
    checked = act_bad = val_bad = 0
    gseed = 0
    while checked < n:
        gseed += 1
        env = new_env(level=LEVEL, seed=gseed, cap=300)
        attach_stream(env, gseed)
        env.cur = env._rand_pill()
        env.nxt = env._rand_pill()
        for _ in range(300):
            if env.board.virus_count() == 0:
                break
            col, vir, _lk = board_planes(env.board)
            ca, cb, na, nb = env.cur.a, env.cur.b, env.nxt.a, env.nxt.b
            if rng.random() < 0.25 and checked < n:
                a_py, vals_py = choose_base_py(col, vir, ca, cb, na, nb)
                a_nb, val_nb, ok_nb = champ.values(col, vir, ca, cb, na, nb)
                checked += 1
                if int(a_py if a_py is not None else -1) != int(a_nb):
                    act_bad += 1
                    if verbose and act_bad <= 3:
                        print(f"  ACTION MISMATCH py={a_py} nb={a_nb}")
                for a, v in vals_py.items():
                    if ok_nb[a] != 1 or val_nb[a] != v:
                        val_bad += 1
                        if verbose and val_bad <= 3:
                            print(f"  VALUE MISMATCH a={a} py={v!r} "
                                  f"nb={val_nb[a]!r} ok={ok_nb[a]}")
                        break
                if len(vals_py) != int(ok_nb.sum()):
                    val_bad += 1
            a = champ.choose(col, vir, ca, cb, na, nb)
            if a < 0:
                break
            _o, _r, term, trunc, _i = env.step(int(a))
            if term or trunc:
                break
        if checked >= n:
            break
    ok = (act_bad == 0 and val_bad == 0)
    if verbose:
        print(f"gate: checked={checked} action_mismatch={act_bad} "
              f"value_mismatch={val_bad} -> {'PASS' if ok else 'FAIL'}")
    return ok


if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=200)
    args = ap.parse_args()
    sys.exit(0 if gate(n=args.n) else 1)
