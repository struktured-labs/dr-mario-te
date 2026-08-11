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
with the selected pressure environment running exactly as in the live game.
The historical `lulu` mode is self-coupled: firing also depends on that line's
own clear size.  The separately pre-registered `exo_lulu` sensitivity offers a
complete volley from `(seed, pills_placed)` only, so candidates share an actual
external schedule.  See `PREREG_EXOGENOUS_PRESSURE.md`.

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
`future_mode` selects which future the forks see:
  "clair"   the realized capsule and garbage future.  This is deliberately
            unfair: it is the programme's IDEAL-HEADROOM measurement.
  "dist"    the realized capsule stream but sampled garbage futures, with
            common random numbers across candidates.  This decomposes how
            much of CLAIR's headroom requires opponent clairvoyance.

`label_mode` selects what the re-ranker is fed:
  "true"    the real forward-rollout label.
  "shuffle" THE KILLED MUTANT.  The identical forks are run and their labels
            are PERMUTED among candidates.  A pre-registered deterministic hash
            thinning then matches its accepted flip dose to the true arm.  The
            oracle is re-ranking on a survival label that carries no information
            about which candidate produced it.  This arm MUST NOT clear the
            endpoint gate.
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
DIST_KEY_VERSION = "pack-v1"
POLICY_SEMANTICS = ("historical_compact", "firmware_v8")
TIE_SEED_MODES = ("seed0", "p2_surrogate")

# The champion's scan order over the 32-slot index (var*8+cc, var = [2,3,0,1]).
CHAMP_ORDER = np.array([v * 8 + c for v in (2, 3, 0, 1) for c in range(8)],
                       dtype=np.int64)


def dist_seed(seed, ply, sample=0):
    """Collision-free synthetic pressure key for ORACLE-DIST.

    The abandoned `seed + 7919*(ply+1)` proposal collided between adjacent
    plies of seeds 7,919 apart inside the registered 9,000-seed block.  Packing
    the tuple is injective for all non-negative values below 2**32/2**16 and is
    easy for a gate to prove exhaustively.  It depends on seed/ply/sample but
    never on candidate, preserving common random numbers across candidates.
    """
    seed, ply, sample = int(seed), int(ply), int(sample)
    assert 0 <= seed < 2**32 and 0 <= ply < 2**16 - 1
    assert 0 <= sample < 2**16
    return (seed << 32) | ((ply + 1) << 16) | sample


def _mix64(x):
    """Stable SplitMix64 finalizer; unlike hash(), stable across processes."""
    x = (int(x) + 0x9E3779B97F4A7C15) & 0xFFFFFFFFFFFFFFFF
    x = ((x ^ (x >> 30)) * 0xBF58476D1CE4E5B9) & 0xFFFFFFFFFFFFFFFF
    x = ((x ^ (x >> 27)) * 0x94D049BB133111EB) & 0xFFFFFFFFFFFFFFFF
    return x ^ (x >> 31)


def null_keeps_flip(seed, ply, numerator, denominator):
    """Deterministic, endpoint-blind thinning for the shuffled-label null."""
    numerator, denominator = int(numerator), int(denominator)
    assert 0 <= numerator <= denominator and denominator > 0
    key = (int(seed) << 32) | int(ply)
    return (_mix64(key) % denominator) < numerator


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
    env._oracle_garbage = 0
    env._oracle_pressure_offers = 0
    env._oracle_offered_cells = 0
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


def policy_tie_seed(seed, mode):
    """Explicit tie model; `p2_surrogate` is reproducible, not a NAV_T claim."""
    assert mode in TIE_SEED_MODES
    if mode == "seed0":
        return 0
    nav = ((73 * int(seed) + 41) & 255) | 1
    return nav ^ 0xA4


def _policy_values(col, vir, lnk, ca, cb, na, nb, w, fl, wt, ws, semantics):
    """Candidate values for one explicitly named base-policy semantics."""
    assert semantics in POLICY_SEMANTICS
    if semantics == "historical_compact":
        return _champ_values(col, vir, ca, cb, na, nb, w, fl, wt, ws)
    if wt != 0 or ws != 20:
        raise ValueError("hardware-validated firmware_v8 mode requires wt=0, ws=20")
    if lnk is None:
        raise ValueError("firmware_v8 policy requires the parent link plane")
    import firmware_v8_policy as V8
    return V8.candidate_values(col, vir, lnk, ca, cb, na, nb, w, fl)


def _policy_rank_values(vals, semantics, tie_seed):
    if semantics == "historical_compact":
        if int(tie_seed) != 0:
            raise ValueError("historical_compact has only registered seed-zero tie behavior")
        return vals
    import firmware_v8_policy as V8
    return V8.jittered_values(vals, tie_seed)


def _advance(env, action, C, seed, bmodel):
    """ONE placement + the rig's injection step.  Returns (res, v_at_topout).

    res is None if the game continues.  This is the rig's own loop body, kept
    in one place so the live game and every fork execute identical physics.
    """
    import pressure_rig as PR
    model_kind = C.get("model_kind", "drip")
    pressure_mode = C.get("pressure_mode", "coupled")
    drip_period = C.get("drip_period") or PR.GARBAGE_PERIOD
    drip_k = C.get("drip_k") or PR.GARBAGE_K

    occ_before = (int(np.count_nonzero(env.board.color))
                  if model_kind == "bursty" and pressure_mode == "coupled"
                  else 0)
    _, _, term, trunc, info = env.step(int(action))
    if term:
        if info["won"]:
            return "clear", None
        return "topout", env.board.virus_count()
    if trunc:
        return "stall", None
    if env.pills_placed >= PR.GARBAGE_MIN_PILLS:
        landed = 0
        if model_kind == "drip":
            if env.pills_placed % drip_period == 0:
                landed = PR._inject_garbage(
                    env.board, seed, env.pills_placed, k=drip_k)
        elif pressure_mode == "exogenous":
            from exogenous_pressure import inject_exogenous_garbage
            landed, offer = inject_exogenous_garbage(
                env.board, bmodel, seed, env.pills_placed)
            env._oracle_pressure_offers += int(offer.fires)
            env._oracle_offered_cells += len(offer.cells)
        else:  # historical solo proxy: receiver's own clear drives pressure
            from bursty_model import inject_bursty_garbage
            occ_after = int(np.count_nonzero(env.board.color))
            clear_size = max(0, occ_before + 2 - occ_after)
            if clear_size > 0:
                landed = inject_bursty_garbage(
                    env.board, bmodel, seed, env.pills_placed, clear_size)
        env._oracle_garbage += int(landed)
        if env.board.virus_count() == 0:
            return "clear", None
        if env.board.spawn_blocked():
            return "topout", env.board.virus_count()
    return None, None


# --------------------------------------------------------------------- forks
def _fork_label(env, action, C, seed, bmodel, w, fl, wt, ws, horizon,
                policy_semantics="historical_compact", tie_seed=0):
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
        lnk = (np.ascontiguousarray(e.board.link, dtype=np.int8).reshape(-1)
               if policy_semantics == "firmware_v8" else None)
        vals = _policy_values(col, vir, lnk, int(e.cur.a), int(e.cur.b),
                              int(e.nxt.a), int(e.nxt.b), w, fl, wt, ws,
                              policy_semantics)
        ranked_vals = _policy_rank_values(vals, policy_semantics, tie_seed)
        a = _champ_action(ranked_vals, CHAMP_ORDER)
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
                 horizon=HORIZON, provenance=False, future_mode="clair",
                 fork_samples=1, null_keep_num=1, null_keep_den=1,
                 policy_semantics="historical_compact", tie_seed_mode="seed0"):
        assert label_mode in ("true", "shuffle", "const")
        assert future_mode in ("clair", "dist")
        assert int(fork_samples) >= 1
        assert 0 <= int(null_keep_num) <= int(null_keep_den)
        assert int(null_keep_den) > 0
        assert policy_semantics in POLICY_SEMANTICS
        assert tie_seed_mode in TIE_SEED_MODES
        if policy_semantics == "historical_compact" and tie_seed_mode != "seed0":
            raise ValueError("historical_compact supports only tie_seed_mode=seed0")
        if future_mode == "clair":
            assert int(fork_samples) == 1, (
                "repeating the same realized future is not a new sample")
        self.label_mode = label_mode
        self.order_flip = order_flip
        self.topk = topk
        self.horizon = horizon
        self.provenance = provenance
        self.future_mode = future_mode
        self.fork_samples = int(fork_samples)
        self.null_keep_num = int(null_keep_num)
        self.null_keep_den = int(null_keep_den)
        self.policy_semantics = policy_semantics
        self.tie_seed_mode = tie_seed_mode
        self.stats = {"plies": 0, "gated_plies": 0, "flips": 0,
                      "raw_flips": 0, "null_rejected_flips": 0, "forks": 0}
        self.flip_log = []

    @property
    def is_identity(self):
        return self.label_mode == "const" and not self.order_flip

    def choose(self, env, seed, C, bmodel, w, fl, wt, ws, ply):
        from fb import FB
        import root_search as RS

        fb = FB.from_board(env.board)
        col, vir = RS.board_flat_from_fb(fb)
        lnk = (np.ascontiguousarray(env.board.link, dtype=np.int8).reshape(-1)
               if self.policy_semantics == "firmware_v8" else None)
        vals = _policy_values(col, vir, lnk, int(env.cur.a), int(env.cur.b),
                              int(env.nxt.a), int(env.nxt.b), w, fl, wt, ws,
                              self.policy_semantics)
        tie_seed = policy_tie_seed(seed, self.tie_seed_mode)
        ranked_vals = _policy_rank_values(vals, self.policy_semantics, tie_seed)
        order = CHAMP_ORDER[::-1] if self.order_flip else CHAMP_ORDER
        base_a = _champ_action(ranked_vals, order)
        if base_a is None:
            return None, None
        self.stats["plies"] += 1

        fires, d_spawn_h, viruses = gate_fires(env)
        if not fires:
            return base_a, base_a
        self.stats["gated_plies"] += 1

        # top-k by champion value, ties broken by the champion's scan order
        legal = [int(s) for s in order if np.isfinite(ranked_vals[int(s)])]
        ranked = sorted(range(len(legal)),
                        key=lambda i: (-ranked_vals[legal[i]], i))[:self.topk]
        cands = [legal[i] for i in ranked]
        if len(cands) <= 1:
            return base_a, base_a

        labels = [(1, 0) for _ in cands]
        if self.label_mode != "const":
            labels = [(0, 0) for _ in cands]
            for sample in range(self.fork_samples):
                fork_seed = (seed if self.future_mode == "clair"
                             else dist_seed(seed, ply, sample))
                for i, candidate in enumerate(cands):
                    survived, progress = _fork_label(
                        env, candidate, C, fork_seed, bmodel, w, fl, wt, ws,
                        self.horizon, self.policy_semantics, tie_seed)
                    labels[i] = (labels[i][0] + survived,
                                 labels[i][1] + progress)
                    self.stats["forks"] += 1
        if self.label_mode == "shuffle":
            rng = random.Random(seed * 100003 + ply)
            rng.shuffle(labels)

        best_i = 0
        for i in range(1, len(cands)):
            if labels[i] > labels[best_i]:
                best_i = i
        a = cands[best_i]
        raw_flip = a != base_a
        if raw_flip:
            self.stats["raw_flips"] += 1
        if (raw_flip and self.label_mode == "shuffle"
                and not null_keeps_flip(seed, ply, self.null_keep_num,
                                        self.null_keep_den)):
            a = base_a
            self.stats["null_rejected_flips"] += 1

        if a != base_a:
            self.stats["flips"] += 1
            if self.provenance:
                H = heights(env.board.color)
                champion_best = float(ranked_vals[base_a])
                chosen_score = labels[best_i]
                self.flip_log.append({
                    "seed": int(seed),
                    "arm": (f"oracle_{self.future_mode}"
                            if self.label_mode == "true"
                            else f"{self.label_mode}_{self.future_mode}"),
                    "pressure_mode": C.get("pressure_mode", "coupled"),
                    "ply": ply, "viruses": viruses, "maxh": int(H.max()),
                    "d_spawn_h": d_spawn_h,
                    "base_action": int(base_a), "trt_action": int(a),
                    "champ_rank_chosen": int(best_i),
                    "policy_semantics": self.policy_semantics,
                    "tie_seed_mode": self.tie_seed_mode,
                    "tie_seed": int(tie_seed),
                    "labels": [list(map(int, l)) for l in labels],
                    "cands": [int(c) for c in cands],
                    "tie": bool(sum(float(ranked_vals[c]) == champion_best
                                     for c in legal) > 1),
                    "tie_score": bool(sum(l == chosen_score
                                           for l in labels) > 1),
                    "val_gap": round(champion_best - float(ranked_vals[a]), 3),
                    "fork_samples": self.fork_samples})
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
            f["t_to_end"] = n_plies - 1 - f["ply"]
            f["res"] = res
    return {"seed": seed, "res": res, "won": int(res == "clear"),
            "topout": int(res == "topout"), "stall": int(res == "stall"),
            "pills": env.pills_placed, "dies_ahead": dies_ahead,
            "viruses_left": (int(v_at_topout) if v_at_topout is not None
                             else -1),
            "n_plies": n_plies,
            "garbage": int(env._oracle_garbage),
            "pressure_offers": int(env._oracle_pressure_offers),
            "offered_cells": int(env._oracle_offered_cells),
            "flips": arm.stats["flips"],
            "raw_flips": arm.stats["raw_flips"],
            "null_rejected_flips": arm.stats["null_rejected_flips"],
            "gated_plies": arm.stats["gated_plies"],
            "plies_scored": arm.stats["plies"],
            "forks": arm.stats["forks"],
            "_actions": actions}


def init_rig(model="lulu", level=11, wt=0, ws=20):
    """Bring up pressure_rig exactly as the stage-2 rollout does."""
    import p0_ab as P
    import pressure_rig as PR
    if os.environ.get("DR_LULU_FIT"):
        P.LULU_FIT = os.environ["DR_LULU_FIT"]
    obj = P.load_lulu() if model in ("lulu", "exo_lulu") else None
    PR._init(level, wt, ws,
             model_kind=("bursty" if model in ("lulu", "exo_lulu") else "drip"),
             bursty_model_obj=obj)
    C = dict(PR._C)
    C["pressure_mode"] = "exogenous" if model == "exo_lulu" else "coupled"
    return C, obj


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

    # 2. const-label arm == its champion reference, outcome for outcome.
    # pressure_rig.play is a valid independent reference for legacy lulu/drip;
    # exo_lulu deliberately uses a different pressure hook, so repeat it and
    # require action-for-action identity instead.
    for s in range(500, 500 + n):
        arm = OracleArm(label_mode="const")
        r = play_one(s, arm, C, bmodel)
        if model == "exo_lulu":
            ref = play_one(s, OracleArm(label_mode="const"), C, bmodel)
            same = (r["_actions"] == ref["_actions"] and r["res"] == ref["res"]
                    and r["pills"] == ref["pills"]
                    and r["garbage"] == ref["garbage"])
            ref_desc = f"repeat={ref['res']}/{ref['pills']}"
        else:
            ref = PR.play(s)
            same = (r["won"] == ref["won"] and r["topout"] == ref["topout"]
                    and r["stall"] == ref["stall"]
                    and r["pills"] == ref["pills"]
                    and r["dies_ahead"] == ref["dies_ahead"])
            ref_desc = f"pressure_rig won={ref['won']}/{ref['pills']}"
        print(f"  seed {s}: const-arm identity : {same} "
              f"({r['res']}/{r['pills']} vs {ref_desc}) "
              f"gated={r['gated_plies']}/{r['plies_scored']}")
        ok &= same
    print("SELFTEST", "PASS" if ok else "FAIL")
    return ok


if __name__ == "__main__":
    sys.exit(0 if selftest() else 1)
