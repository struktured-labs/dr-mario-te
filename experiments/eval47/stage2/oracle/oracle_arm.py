#!/usr/bin/env python3
"""ORACLE-CEILING ARM — the maximum dies-ahead reduction reachable by ANY root
re-ranker, measured in endpoint units.

WHY THIS EXISTS
---------------
15,000 games were spent on a learned evaluator without ever establishing a
calibration point from offline AUC to the dies-ahead endpoint.  The one
measurement that exists (stage-2 rollout, `../rollout/RESULT.md`) is consistent
with a SLOPE OF ZERO: the fitted term moved dies-ahead -0.80pp [-2.20,+0.60]
and a dose-matched LABEL-BLIND term of the same size moved it -0.53pp.

This arm asks the prior question: **does any root re-ranker move dies-ahead at
all?**  It re-ranks the champion's own top-4 candidates using a 15-pill forward
rollout of the real policy in the real environment — i.e. with information no
leaf evaluator can ever have.  It is therefore an UPPER BOUND on the endpoint
movement available to the whole class.

DECISIVE IN BOTH DIRECTIONS, which is the point:
  * ORACLE NO_GO  => root re-ranking is structurally dead for this endpoint.
  * ORACLE GO     => the AUC gap becomes priceable for the first time.

THE ARM (pre-registered in PREREG_ORACLE.md before any data)
-----------------------------------------------------------
At every ply, the champion's 32 candidates are enumerated and valued EXACTLY as
`pressure_rig._choose_base` does (o4 = 0..3 -> var = _VAR_OF_O4[o4] = [2,3,0,1],
cc = 0..7, strict `>` so ties keep the first in that order).

GATE.  The oracle fires only where the plan says it fires:

    d_spawn_h = max(H[3], H[4])  of the CURRENT (pre-placement) board
    viruses   = current virus count
    ORACLE PLY  <=>  d_spawn_h >= 12  OR  viruses <= 8

At every other ply the champion's action is played unchanged, byte for byte.

FORK.  On an oracle ply the TOP-4 candidates by champion value (ties broken by
the champion's own enumeration order) are each forked HORIZON=15 pills forward:
the candidate action is applied, then the UNMODIFIED champion policy plays on,
with the real dr. lulu bursty injection running exactly as in the live game.
Garbage is a pure function of (seed, pills_placed), so a fork sees precisely the
volleys the real game would have delivered on that line.

LABEL.  Each fork yields `(survived, progress)`:
    survived = 0 if the fork topped out or was spawn-blocked inside the horizon
    progress = viruses_before_ply - viruses_at_end_of_fork   (>= 0)
"survivor-with-virus-progress" = argmax of that pair, scanned in the CHAMPION's
rank order with strict `>`.  A tie therefore keeps the champion's own choice, so
an uninformative oracle degrades to a NO-OP rather than to noise.

DEEPCOPY SAFETY.  Forking clones the env.  `NesPillSource.attach` installs a
`_PillDraw` OBJECT (not a lambda) precisely so `copy.deepcopy` gives each clone
an independent capsule cursor; the lambda version silently shared one advancing
cursor across every branch of a search and only a replay caught it.  This module
asserts fork independence in `selftest()` rather than assuming it.

MUTANTS (a check that cannot fail is not a check)
-------------------------------------------------
`label_mode` selects what the oracle is fed:
  "true"    the real forward-rollout label.
  "shuffle" THE KILLED MUTANT.  The identical four forks are run (identical
            cost, identical gate, identical candidate set) and their labels are
            then PERMUTED among the candidates with an rng keyed on
            (seed, ply).  The oracle is then re-ranking on a survival label that
            carries no information about which candidate produced it.  This arm
            MUST NOT clear the gate.
  "const"   every label identical => the selection can never move => must
            reproduce the champion BYTE FOR BYTE.  This is the OFF-identity
            control.
`order_flip=True` reverses the enumeration order used for the argmax scan.  It
changes tie resolution only, and it MUST break the "const" identity — that is
what makes the identity gate capable of failing.
"""
from __future__ import annotations

import copy
import os
import random
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
STAGE2 = os.path.dirname(HERE)
EV = os.path.dirname(STAGE2)
QA = os.path.dirname(EV)
ROOT = "/home/struktured/projects/dr_mario_rl"
for _p in (EV, QA, HERE, STAGE2, os.path.join(EV, "jointdig"),
           os.path.join(EV, "vocab2"), os.path.join(STAGE2, "rollout"),
           ROOT + "/tmp/combo_term", ROOT + "/tmp/endgame", ROOT + "/tmp/tuck",
           ROOT + "/tmp/pillrng",
           ROOT + "/.claude/worktrees/faithful-sim/src", QA + "/tuck_v3"):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import numpy as np  # noqa: E402

# ---- PRE-REGISTERED CONSTANTS (PREREG_ORACLE.md sec 1; do not tune) --------
GATE_DSPAWN_H = 12      # oracle fires when max(H[3],H[4]) >= this ...
GATE_VIRUSES = 8        # ... OR virus count <= this
TOPK = 4                # champion candidates forked
HORIZON = 15            # pills played forward per fork

# The champion's scan order over the 32-slot index (var*8+cc, var = [2,3,0,1]).
CHAMP_ORDER = np.array([v * 8 + c for v in (2, 3, 0, 1) for c in range(8)],
                       dtype=np.int64)


def heights(board_color):
    """Column heights from a (16,8) colour plane, row 0 = top."""
    b = np.asarray(board_color) != 0
    first = np.argmax(b, axis=0)
    return np.where(b.any(axis=0), b.shape[0] - first, 0).astype(np.int64)


def gate_fires(env):
    """The pre-registered oracle gate, evaluated on the CURRENT board."""
    H = heights(env.board.color)
    d_spawn_h = int(max(H[3], H[4]))
    vir = int(env.board.virus_count())
    return (d_spawn_h >= GATE_DSPAWN_H or vir <= GATE_VIRUSES), d_spawn_h, vir


# --------------------------------------------------------------- environment
class PillDraw:
    """Deepcopy-safe capsule draw.  DO NOT REPLACE WITH A LAMBDA.

    ⚠ `pressure_rig.py` hard-codes `/home/struktured/projects/dr-mario-qa-wt/
    experiments` onto sys.path AHEAD of `dr_mario_rl/tmp/pillrng`, so importing
    it makes `import nes_pills` resolve to the OLD copy whose `attach()` still
    installs

        env._rand_pill = lambda: Pill(*self.next_pill())

    `copy.deepcopy` treats a function as ATOMIC and returns the SAME object, so
    every clone of the env would keep drawing from ONE advancing cursor: sibling
    forks would steal each other's capsules, silently, deterministically, and
    with plausible-looking boards.  This arm forks, so it cannot rely on which
    `nes_pills` happens to win the import race — it installs its own object and
    `selftest()` ASSERTS the independence rather than assuming it.
    """

    __slots__ = ("src",)

    def __init__(self, src):
        self.src = src

    def __call__(self):
        from drmario.faithful_env import Pill
        return Pill(*self.src.next_pill())


def make_env(seed, level, max_pills=300):
    """The rig's environment, built exactly as pressure_rig.play does.

    Identical to `pressure_rig.play`'s construction except that the capsule
    source is installed through `PillDraw` (see above).  Both call
    `NesPillSource.next_pill()` in the same order, so the capsule SEQUENCE is
    bit-identical; `selftest()` proves it by reproducing `pressure_rig.play`
    exactly with the const-label arm.
    """
    from drmario.faithful_env import FaithfulDrMarioEnv
    from nes_pills import NesPillSource
    env = FaithfulDrMarioEnv(level=level, seed=seed, max_pills=max_pills)
    env.reset()
    env._rand_pill = PillDraw(NesPillSource(seed=seed))
    env.cur = env._rand_pill()
    env.nxt = env._rand_pill()
    return env


def _champ_values(col, vir, ca, cb, na, nb, w, fl, wt, ws):
    """The champion's 32 candidate values.  nan where the slot is illegal."""
    import fast_rtl_x as FX
    import root_search as RS
    import pressure_rig as PR
    from fast_sim_x import NCELL, _expand_core
    from terms47 import g_tower, g_stranded

    vals = np.full(32, np.nan)
    c1 = np.empty(NCELL, dtype=np.int8)
    v1 = np.empty(NCELL, dtype=np.int8)
    for o4 in range(4):
        var = int(FX._VAR_OF_O4[o4])
        for cc in range(8):
            ok, nv, cells = _expand_core(col, vir, var, cc, ca, cb, c1, v1)
            if ok == 0:
                continue
            val = RS._root_value(c1, v1, nv, cells, na, nb, 8,
                                 FX._W_EXCAV_SHIP, FX._W_HANG_SHIP, w, fl)
            if wt:
                val -= wt * g_tower(c1, v1, PR.H0)
            if ws:
                val -= ws * g_stranded(c1, v1)
            vals[var * 8 + cc] = val
    return vals


def _champ_action(vals, order):
    if not np.isfinite(vals).any():
        return None
    return int(order[np.nanargmax(vals[order])])


def _advance(env, action, C, seed, bmodel):
    """ONE placement + the rig's injection step.  Returns (res, v_at_topout).

    res is None if the game continues.  This is the rig's own loop body, kept
    in one place so the live game and every fork execute identical physics.
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
            return "clear", None
        return "topout", env.board.virus_count()
    if trunc:
        return "stall", None
    if env.pills_placed >= PR.GARBAGE_MIN_PILLS:
        if model_kind == "drip":
            if env.pills_placed % drip_period == 0:
                PR._inject_garbage(env.board, seed, env.pills_placed, k=drip_k)
        else:
            from bursty_model import inject_bursty_garbage
            occ_after = int(np.count_nonzero(env.board.color))
            clear_size = max(0, occ_before + 2 - occ_after)
            if clear_size > 0:
                inject_bursty_garbage(env.board, bmodel, seed,
                                      env.pills_placed, clear_size)
        if env.board.virus_count() == 0:
            return "clear", None
        if env.board.spawn_blocked():
            return "topout", env.board.virus_count()
    return None, None


# --------------------------------------------------------------------- forks
def _fork_label(env, action, C, seed, bmodel, w, fl, wt, ws, horizon):
    """Play `action` then `horizon-1` champion pills on a CLONE of `env`.

    Returns (survived, progress) where progress = viruses cleared during the
    fork.  The clone is independent: `_PillDraw` deepcopies to its own cursor.
    """
    import root_search as RS
    from fb import FB

    e = copy.deepcopy(env)
    v0 = int(e.board.virus_count())
    res, v_end = _advance(e, action, C, seed, bmodel)
    n = 1
    while res is None and n < horizon:
        if e.board.virus_count() == 0:
            res = "clear"
            break
        fb = FB.from_board(e.board)
        col, vir = RS.board_flat_from_fb(fb)
        vals = _champ_values(col, vir, int(e.cur.a), int(e.cur.b),
                             int(e.nxt.a), int(e.nxt.b), w, fl, wt, ws)
        a = _champ_action(vals, CHAMP_ORDER)
        if a is None:
            break
        res, v_end = _advance(e, a, C, seed, bmodel)
        n += 1
    if res == "clear":
        return 1, v0
    if res == "topout":
        return 0, v0 - int(v_end if v_end is not None else v0)
    return 1, v0 - int(e.board.virus_count())


# ----------------------------------------------------------------- the arm
class OracleArm:
    """Root re-ranker whose scores come from a forward rollout of the truth."""

    def __init__(self, label_mode="true", order_flip=False, topk=TOPK,
                 horizon=HORIZON, provenance=False):
        assert label_mode in ("true", "shuffle", "const")
        self.label_mode = label_mode
        self.order_flip = order_flip
        self.topk = topk
        self.horizon = horizon
        self.provenance = provenance
        self.stats = {"plies": 0, "gated_plies": 0, "flips": 0, "forks": 0}
        self.flip_log = []

    @property
    def is_identity(self):
        return self.label_mode == "const" and not self.order_flip

    def choose(self, env, seed, C, bmodel, w, fl, wt, ws, ply):
        from fb import FB
        import root_search as RS

        fb = FB.from_board(env.board)
        col, vir = RS.board_flat_from_fb(fb)
        vals = _champ_values(col, vir, int(env.cur.a), int(env.cur.b),
                             int(env.nxt.a), int(env.nxt.b), w, fl, wt, ws)
        order = CHAMP_ORDER[::-1] if self.order_flip else CHAMP_ORDER
        base_a = _champ_action(vals, order)
        if base_a is None:
            return None, None
        self.stats["plies"] += 1

        fires, d_spawn_h, viruses = gate_fires(env)
        if not fires:
            return base_a, base_a
        self.stats["gated_plies"] += 1

        # top-k by champion value, ties broken by the champion's scan order
        legal = [int(s) for s in order if np.isfinite(vals[int(s)])]
        ranked = sorted(range(len(legal)),
                        key=lambda i: (-vals[legal[i]], i))[:self.topk]
        cands = [legal[i] for i in ranked]
        if len(cands) <= 1:
            return base_a, base_a

        labels = []
        for a in cands:
            if self.label_mode == "const":
                labels.append((1, 0))
            else:
                labels.append(_fork_label(env, a, C, seed, bmodel, w, fl,
                                          wt, ws, self.horizon))
                self.stats["forks"] += 1
        if self.label_mode == "shuffle":
            rng = random.Random(seed * 100003 + ply)
            rng.shuffle(labels)

        best_i = 0
        for i in range(1, len(cands)):
            if labels[i] > labels[best_i]:
                best_i = i
        a = cands[best_i]
        if a != base_a:
            self.stats["flips"] += 1
            if self.provenance:
                H = heights(env.board.color)
                self.flip_log.append({
                    "ply": ply, "viruses": viruses, "maxh": int(H.max()),
                    "d_spawn_h": d_spawn_h,
                    "base_action": int(base_a), "trt_action": int(a),
                    "champ_rank_chosen": int(best_i),
                    "labels": [list(map(int, l)) for l in labels],
                    "cands": [int(c) for c in cands],
                    "tie": bool(labels[best_i] == labels[0])})
        return a, base_a


# ------------------------------------------------------------ game rollout
def play_one(seed, arm, C, bmodel):
    """The rig's game loop with `arm` at the decision point.

    Every non-decision line is `pressure_rig.play`'s / `arm_lut.play_one`'s.
    """
    import pressure_rig as PR
    level, wt, ws, w, fl = C["level"], C["wt"], C["ws"], C["w"], C["fl"]

    env = make_env(seed, level)
    res, v_at_topout = "stall", None
    actions = []
    for ply in range(300):
        if env.board.virus_count() == 0:
            res = "clear"
            break
        a, _base_a = arm.choose(env, seed, C, bmodel, w, fl, wt, ws, ply)
        if a is None:
            break
        actions.append(int(a))
        r, v = _advance(env, a, C, seed, bmodel)
        if r is not None:
            res, v_at_topout = r, v
            break
    dies_ahead = int(res == "topout" and v_at_topout is not None
                     and v_at_topout <= PR.DIES_AHEAD_VIRUS_THRESHOLD)
    n_plies = len(actions)
    if arm.provenance:
        for f in arm.flip_log:
            f["t_to_end"] = n_plies - f["ply"]
    return {"seed": seed, "res": res, "won": int(res == "clear"),
            "topout": int(res == "topout"), "stall": int(res == "stall"),
            "pills": env.pills_placed, "dies_ahead": dies_ahead,
            "viruses_left": (int(v_at_topout) if v_at_topout is not None
                             else -1),
            "n_plies": n_plies,
            "flips": arm.stats["flips"],
            "gated_plies": arm.stats["gated_plies"],
            "plies_scored": arm.stats["plies"],
            "forks": arm.stats["forks"],
            "_actions": actions}


def init_rig(model="lulu", level=11, wt=0, ws=20):
    """Bring up pressure_rig exactly as the stage-2 rollout does."""
    import p0_ab as P
    import pressure_rig as PR
    obj = P.load_lulu() if model == "lulu" else None
    PR._init(level, wt, ws, model_kind=("bursty" if model == "lulu" else "drip"),
             bursty_model_obj=obj)
    return dict(PR._C), obj


# ------------------------------------------------------------------ selftest
def selftest(n=3, model="lulu"):
    """Fork independence + the identity property, ASSERTED not assumed."""
    C, bmodel = init_rig(model)
    ok = True

    # 1. deepcopy gives independent capsule cursors, from a LIVE mid-game state
    import pressure_rig as PR
    import nes_pills
    print(f"  nes_pills resolved to     : {nes_pills.__file__}")
    env = make_env(101, C["level"])
    for _ in range(6):
        r, _v = _advance(env, 10, C, 101, bmodel)
        if r is not None:
            break
    a = copy.deepcopy(env)
    b = copy.deepcopy(env)
    pa = [a._rand_pill() for _ in range(4)]
    pb = [b._rand_pill() for _ in range(4)]
    indep = all((x.a, x.b) == (y.a, y.b) for x, y in zip(pa, pb))
    print(f"  fork capsule independence : {indep} "
          f"(A={[(p.a,p.b) for p in pa]} B={[(p.a,p.b) for p in pb]})")
    ok &= indep
    shared = env._rand_pill()
    print(f"  parent cursor unadvanced  : "
          f"{(shared.a, shared.b) == (pa[0].a, pa[0].b)}")
    ok &= (shared.a, shared.b) == (pa[0].a, pa[0].b)

    # 2. const-label arm == champion, outcome for outcome
    for s in range(500, 500 + n):
        arm = OracleArm(label_mode="const")
        r = play_one(s, arm, C, bmodel)
        ref = PR.play(s)
        same = (r["won"] == ref["won"] and r["topout"] == ref["topout"]
                and r["stall"] == ref["stall"] and r["pills"] == ref["pills"]
                and r["dies_ahead"] == ref["dies_ahead"])
        print(f"  seed {s}: const-arm == pressure_rig.play : {same} "
              f"({r['res']}/{r['pills']} vs won={ref['won']}"
              f"/{ref['pills']}) gated={r['gated_plies']}/{r['plies_scored']}")
        ok &= same
    print("SELFTEST", "PASS" if ok else "FAIL")
    return ok


if __name__ == "__main__":
    sys.exit(0 if selftest() else 1)
