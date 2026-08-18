#!/usr/bin/env python3
"""S0-A — argmax-flip screen for the 2-candidate deepening (task #117 step 1).

Pre-registered in PREREG_S0A.md BEFORE any row here was produced.  Read it
first; this file implements it and adds nothing it does not declare.

ARCHITECTURE, and it is the whole safety argument: the game is played by the
SHIPPED CHAMPION from start to finish.  This screen is a pure OBSERVER that
wakes at post-garbage plies, measures two things on boards the champion is about
to act on, and never changes an action.  `gate_s0a.py` S1 proves that by
comparing the action sequence against `oracle_arm.play_one` with the plain
const-label arm — the object that actually runs, not a parent of it.

TWO READOUTS, both stratified by board fill (PREREG sec 4):
  PRIMARY (sec 5)   at post-garbage plies where the top-2 champion values are
                    EXACTLY tied: does deepening the two by one ply change the
                    pick?
  SECONDARY (sec 6) at EVERY post-garbage ply: does the champion's argmax differ
                    between the PRE-garbage and the settled POST-garbage board?
                    This re-derives the 50.5% (task #121), which currently has no
                    reproducible artifact anywhere.

WHY THE ADVANCE IS INLINED.  `oracle_arm._advance` performs the placement and
the garbage injection in one call, so it never exposes the board BETWEEN them —
and that intermediate board is exactly what the secondary readout needs.
`advance_split` is that function with the two steps separated and nothing else
changed.  Every physics line is the rig's.  S1 in the gate exists because an
inlined copy is a fork that can drift.
"""
from __future__ import annotations

import argparse
import copy
import hashlib
import json
import math
import os
import sys
import time

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
# Cross-worktree import, recorded in the manifest.  See task #118: absolute-path
# literals into sibling worktrees are a known reproducibility hazard, so the path
# is overridable and always hashed into the output.
ORACLE_DIR = os.environ.get(
    "GW_ORACLE_DIR",
    "/home/struktured/projects/dr-mario-te/h13-gate/experiments/eval47/stage2/oracle")

FILL_BINS = ((0.00, 0.30, "<30"), (0.30, 0.45, "30-45"),
             (0.45, 0.60, "45-60"), (0.60, 1.01, ">=60"))
HIGH_FILL = ("45-60", ">=60")
NCELL = 128


def _boot():
    if ORACLE_DIR not in sys.path:
        sys.path.insert(0, ORACLE_DIR)


# ------------------------------------------------------------------- helpers
def fill_of(board):
    return float(np.count_nonzero(board.color)) / NCELL


def fill_bin(f):
    for lo, hi, name in FILL_BINS:
        if lo <= f < hi:
            return name
    return ">=60"


def col_heights(board):
    """Stack height per column: rows from the floor to the topmost occupied."""
    import oracle_arm as O
    return O.heights(board.color)


def hit_columns(pre, post):
    """Columns whose occupancy grew across the injection step."""
    a = (np.asarray(pre.color) != 0).sum(axis=0)
    b = (np.asarray(post.color) != 0).sum(axis=0)
    return [int(c) for c in range(len(a)) if b[c] > a[c]]


def champ_values_of(board, ca, cb, na, nb, w, fl, wt, ws):
    """The champion's 32 candidate values on an ARBITRARY board object."""
    import root_search as RS
    from fb import FB
    from oracle_arm import _champ_values
    col, vir = RS.board_flat_from_fb(FB.from_board(board))
    return _champ_values(col, vir, int(ca), int(cb), int(na), int(nb),
                         w, fl, wt, ws)


def sampled_capsule(seed, ply):
    """ONE capsule from a stream keyed by (seed, ply).

    PREREG sec 3.1: the next-next capsule is NOT observable on-cart, so the arm
    samples it -- k=1, because k>1 costs 2k x C and nothing fits above k=1.
    PREREG sec 3.2: the SAME draw is handed to both candidates (common random
    numbers), so the comparison prices position quality and not draw luck.
    """
    from nes_pills import NesPillSource
    from oracle_arm import PillDraw
    alt = (int(seed) * 1000003 + int(ply) * 7919) % (2 ** 31 - 1)
    return PillDraw(NesPillSource(seed=int(alt)))()


# ------------------------------------------------------------------ the arm
def board_key(board):
    return np.asarray(board.color).tobytes()


def representatives(env, legal, vals, dedup=True):
    """Collapse actions that produce the SAME board (PREREG v2 sec B).

    A capsule is a double one time in three, and a double is symmetric under
    180 degrees -- orientations 0/2 and 1/3 are the same placement with exactly
    equal value.  Without this collapse, 87% of "exact top-2 ties" are a
    placement paired with its own mirror and the deepening compares a board with
    itself.  That voided the v1 pre-registration.

    Returns (representatives, identical_pair) where `identical_pair` reports
    whether the top-2 returned produce the same board -- which must be False
    under v2 and is asserted by the gate.

    ⚠ SILICON: the cart needs no board comparison for this.  `cur.a == cur.b ->
    skip orientations 2 and 3` captures the whole effect in one byte compare.
    """
    ranked = sorted(legal, key=lambda c: (-float(vals[c]), int(c)))
    if not dedup:                                   # M-D3
        top = ranked[:2]
        return top, _same_board(env, top)
    seen, reps = set(), []
    for c in ranked:
        e = copy.deepcopy(env)
        e.step(int(c))
        k = board_key(e.board)
        if k in seen:
            continue
        seen.add(k)
        reps.append(c)
        if len(reps) == 2:
            break
    return reps, _same_board(env, reps)


def _same_board(env, cands):
    if len(cands) < 2:
        return False
    keys = []
    for c in cands[:2]:
        e = copy.deepcopy(env)
        e.step(int(c))
        keys.append(board_key(e.board))
    return keys[0] == keys[1]


def deepen(env, cands, C, seed, bmodel, w, fl, wt, ws, ply, disable=False,
           unpaired=False):
    """Score `cands` by one extra ply and return (pick, scores).

    Observation set (PREREG sec 3.1): the settled board, `cur`, `nxt`.  The
    next-next capsule is SAMPLED; no future garbage, no opponent board, no
    outcome label.  A candidate that tops out scores -inf; one that clears
    scores +inf; ties keep the champion's pick.

    `disable` / `unpaired` exist only for the killed mutants (M-D1 / M-D2) and
    are never set by the screen itself.
    """
    if disable:                                    # M-D1
        return cands[0], [0.0 for _ in cands]

    shared = sampled_capsule(seed, ply)
    scores = []
    for i, c in enumerate(cands):
        nxtnxt = sampled_capsule(seed * 31 + i, ply) if unpaired else shared
        e = copy.deepcopy(env)
        _, _, term, trunc, info = e.step(int(c))
        if term:
            scores.append(math.inf if info.get("won") else -math.inf)
            continue
        if trunc:
            scores.append(-math.inf)
            continue
        vals = champ_values_of(e.board, e.cur.a, e.cur.b,
                               nxtnxt.a, nxtnxt.b, w, fl, wt, ws)
        finite = vals[np.isfinite(vals)]
        scores.append(float(np.max(finite)) if finite.size else -math.inf)
    best = 0
    for i in range(1, len(cands)):
        if scores[i] > scores[best]:               # strict: ties keep champion
            best = i
    return cands[best], scores


# --------------------------------------------------------------- the physics
def advance_split(env, action, C, seed, bmodel):
    """`oracle_arm._advance`, with placement and injection separated.

    Returns (res, v_at_topout, pre_board_or_None).  `pre_board` is a snapshot of
    the board AFTER the placement and BEFORE the volley, returned only when a
    volley actually landed.  Every other line is the rig's own.
    """
    import pressure_rig as PR
    model_kind = C.get("model_kind", "drip")
    drip_period = C.get("drip_period") or PR.GARBAGE_PERIOD
    drip_k = C.get("drip_k") or PR.GARBAGE_K

    occ_before = (int(np.count_nonzero(env.board.color))
                  if model_kind == "bursty" else 0)
    _, _, term, trunc, info = env.step(int(action))
    if term:
        if info["won"]:
            return "clear", None, None
        return "topout", env.board.virus_count(), None
    if trunc:
        return "stall", None, None

    pre = None
    if env.pills_placed >= PR.GARBAGE_MIN_PILLS:
        if model_kind == "drip":
            if env.pills_placed % drip_period == 0:
                pre = copy.deepcopy(env.board)
                PR._inject_garbage(env.board, seed, env.pills_placed, k=drip_k)
        else:
            from bursty_model import inject_bursty_garbage
            occ_after = int(np.count_nonzero(env.board.color))
            clear_size = max(0, occ_before + 2 - occ_after)
            if clear_size > 0:
                snap = copy.deepcopy(env.board)
                placed = inject_bursty_garbage(env.board, bmodel, seed,
                                               env.pills_placed, clear_size)
                if placed:
                    pre = snap
        if env.board.virus_count() == 0:
            return "clear", None, pre
        if env.board.spawn_blocked():
            return "topout", env.board.virus_count(), pre
    return None, None, pre


# ------------------------------------------------------------------ the loop
def play_one_screened(seed, C, bmodel, rows, mut=None):
    """The champion's game loop with an observer at post-garbage plies."""
    import pressure_rig as PR
    from oracle_arm import make_env, _champ_action, CHAMP_ORDER, heights
    mut = mut or {}
    level, wt, ws, w, fl = C["level"], C["wt"], C["ws"], C["w"], C["fl"]

    env = make_env(seed, level)
    res, v_at_topout = "stall", None
    actions = []
    pending_pre = None

    for ply in range(300):
        if env.board.virus_count() == 0:
            res = "clear"
            break

        vals = champ_values_of(env.board, env.cur.a, env.cur.b,
                               env.nxt.a, env.nxt.b, w, fl, wt, ws)
        base_a = _champ_action(vals, CHAMP_ORDER)
        if base_a is None:
            break

        if pending_pre is not None:
            _observe(env, pending_pre, vals, base_a, seed, ply, C, bmodel,
                     w, fl, wt, ws, rows, mut)
            pending_pre = None

        actions.append(int(base_a))
        r, v, pending_pre = advance_split(env, base_a, C, seed, bmodel)
        if r is not None:
            res, v_at_topout = r, v
            break

    dies_ahead = int(res == "topout" and v_at_topout is not None
                     and v_at_topout <= PR.DIES_AHEAD_VIRUS_THRESHOLD)
    return {"seed": seed, "res": res, "won": int(res == "clear"),
            "topout": int(res == "topout"), "stall": int(res == "stall"),
            "pills": env.pills_placed, "dies_ahead": dies_ahead,
            "n_plies": len(actions), "actions": actions}


def _observe(env, pre, vals_post, a_post, seed, ply, C, bmodel,
             w, fl, wt, ws, rows, mut):
    """Both readouts, at one post-garbage ply.  Never mutates `env`."""
    from oracle_arm import _champ_action, CHAMP_ORDER

    post = env.board
    f = fill_of(post)
    fb = fill_bin(f)
    hits = hit_columns(pre, post)
    h_pre = col_heights(pre)
    h_hit = int(min(h_pre[c] for c in hits)) if hits else -1
    H = col_heights(post)
    common = dict(seed=int(seed), ply=int(ply), fill=round(f, 4), fill_bin=fb,
                  h_hit=h_hit, viruses=int(post.virus_count()),
                  max_h=int(max(H)), d_spawn_h=int(max(H[3], H[4])))

    # ---- SECONDARY (PREREG sec 6): pre- vs post-garbage champion argmax
    vals_pre = champ_values_of(pre, env.cur.a, env.cur.b,
                               env.nxt.a, env.nxt.b, w, fl, wt, ws)
    a_pre = _champ_action(vals_pre, CHAMP_ORDER)
    if a_pre is not None and a_post is not None:
        rows.append(dict(kind="prepost", flip=int(int(a_pre) != int(a_post)),
                         a_pre=int(a_pre), a_post=int(a_post), **common))

    # ---- PRIMARY (PREREG v2 sec B): deepening at ties over DE-DUPLICATED candidates
    order = CHAMP_ORDER
    legal = [int(s) for s in order if np.isfinite(vals_post[int(s)])]
    if len(legal) < 2:
        return
    cands, dup = representatives(env, legal, vals_post,
                                 dedup=not mut.get("nodedup"))
    if len(cands) < 2:
        return
    if float(vals_post[cands[0]]) != float(vals_post[cands[1]]):
        return
    if int(cands[0]) != int(a_post):
        return                       # champion's pick must be rank-0 by construction
    pick, scores = deepen(env, cands, C, seed, bmodel, w, fl, wt, ws, ply,
                          disable=bool(mut.get("disable")),
                          unpaired=bool(mut.get("unpaired")))
    s0, s1 = scores[0], scores[1]
    rows.append(dict(kind="deepen", flip=int(int(pick) != int(cands[0])),
                     champ_pick=int(cands[0]), alt_cand=int(cands[1]),
                     deep_pick=int(pick), dup_pair=int(bool(dup)),
                     double_capsule=int(env.cur.a == env.cur.b),
                     score_c1=(None if math.isinf(s0) else round(s0, 4)),
                     score_c2=(None if math.isinf(s1) else round(s1, 4)),
                     **common))


# ------------------------------------------------------------------- driver
def run(seed_start, seed_count, workers, out, model="lulu", mut=None):
    _boot()
    import oracle_arm as O
    C, bmodel = O.init_rig(model)
    seeds = list(range(seed_start, seed_start + seed_count))

    t0 = time.time()
    if workers <= 1:
        results = [_one(s, C, bmodel, mut) for s in seeds]
    else:
        from concurrent.futures import ProcessPoolExecutor
        with ProcessPoolExecutor(max_workers=workers,
                                 initializer=_winit,
                                 initargs=(model, mut)) as ex:
            results = list(ex.map(_wrun, seeds, chunksize=1))

    with open(out, "w") as fh:
        for r in results:
            fh.write(json.dumps(r) + "\n")
    n_rows = sum(len(r["rows"]) for r in results)
    print(f"{len(seeds)} seeds, {n_rows} observation rows, "
          f"{time.time() - t0:.1f}s -> {out}")
    return results


def _one(seed, C, bmodel, mut):
    rows = []
    g = play_one_screened(seed, C, bmodel, rows, mut)
    g.pop("actions", None)
    g["rows"] = rows
    return g


_WS = {}


def _winit(model, mut):
    _boot()
    import oracle_arm as O
    C, bmodel = O.init_rig(model)
    _WS.update(C=C, bmodel=bmodel, mut=mut)


def _wrun(seed):
    return _one(seed, _WS["C"], _WS["bmodel"], _WS["mut"])


def manifest():
    """Hash every module on the decision path (rule: results without code
    provenance are not bankable; this project has caught a cross-node skew)."""
    _boot()
    import importlib
    import oracle_arm as O
    O.init_rig("lulu")
    names = ("oracle_arm", "pressure_rig", "p0_ab", "bursty_model",
             "fast_rtl_x", "fast_sim_x", "root_search", "terms47", "fb",
             "nes_pills")
    files = {"screen_gw": os.path.abspath(__file__), "ORACLE_DIR": ORACLE_DIR}
    per = {}
    for name in names:
        m = importlib.import_module(name)
        p = getattr(m, "__file__", None)
        if p:
            per[name] = {"path": os.path.abspath(p),
                         "sha256": hashlib.sha256(
                             open(p, "rb").read()).hexdigest()}
    per["screen_gw"] = {"path": files["screen_gw"],
                        "sha256": hashlib.sha256(
                            open(__file__, "rb").read()).hexdigest()}
    rolled = hashlib.sha256(
        "".join(sorted(v["sha256"] for v in per.values())).encode()).hexdigest()
    return {"oracle_dir": ORACLE_DIR, "modules": per, "rolled": rolled[:16]}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--seed-start", type=int, default=110000)
    ap.add_argument("--seed-count", type=int, default=1000)
    ap.add_argument("--workers", type=int, default=1)
    ap.add_argument("--out", default=os.path.join(HERE, "out", "s0a.jsonl"))
    ap.add_argument("--model", default="lulu")
    ap.add_argument("--mut-disable", action="store_true", help="M-D1")
    ap.add_argument("--mut-unpaired", action="store_true", help="M-D2")
    ap.add_argument("--manifest", action="store_true")
    a = ap.parse_args()
    if a.manifest:
        print(json.dumps(manifest(), indent=2))
        return
    os.makedirs(os.path.dirname(a.out), exist_ok=True)
    mut = {"disable": a.mut_disable, "unpaired": a.mut_unpaired}
    run(a.seed_start, a.seed_count, a.workers, a.out, a.model, mut)


if __name__ == "__main__":
    main()
