#!/usr/bin/env python3
"""STAGE-2 ROLLOUT ARM: the shippable additive-LUT Delta term, wired into the
root of the champion's depth-3 search.

MANDATORY CAVEAT (rides on every number this file produces):
  Corpus s2lulu: generating policy = shipped champion (bit-exact), environment =
  dr. lulu fitted bursty pressure, clear rate 79.80% - BELOW the 96.9%
  label-quality screen.  Labels are game outcomes broadcast onto decisions; no
  counterfactual attribution.
AND: the recommended model is ROUND-2 / CONTAMINATION-FLAGGED (the eligible
feature set was corrected after a holdout-scored diagnostic).  See
PREREG_SHIPPABLE.md deviation-log entry 7.

DEPLOYED FORM (identical to the form gate B3 scored offline, round2.py:149):

    sco_i = cand_val_i  -  Delta(features(post-placement board of candidate i))
    action = first argmax of sco over the CHAMPION's enumeration order
             (o4 = 0..3 -> var = _VAR_OF_O4[o4] = [2,3,0,1], slot = var*8+cc),
             ties keep the first in THAT order (strict `>`), exactly as
             pressure_rig._choose_base does.

Delta is the pre-registered integer pipeline: uint8 feature -> table index ->
int12 table value -> int16 accumulate.  No float in the deployed path.

WHERE IT IS APPLIED, STATED PLAINLY.  The silicon target (PREREG_STAGE2 sec 5)
puts Delta in LeafEval's S_DONE2, i.e. at EVERY leaf.  Every offline gate this
lane ran - B2's AUC, B3's argmax-flip, the whole dose curve - was computed on
the ROOT re-rank above, on post-ROOT-placement features.  This rollout tests the
decision rule that was actually validated.  A leaf-level application is a
DIFFERENT (and unvalidated) intervention and is not tested here.  Reported as a
deviation, not hidden.

EXACT PRUNING (not an approximation): Delta is bounded by the fitted tables,
[DMIN, DMAX].  A candidate whose champion value is below best_val - (DMAX-DMIN)
cannot win under ANY assignment of Delta, so its Delta is never computed.  With
`prune=False` every candidate is scored; `--selftest` asserts the two agree on
every ply of several games, which is what makes the pruning a checked claim
rather than an assumed one.
"""
from __future__ import annotations

import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
STAGE2 = os.path.dirname(HERE)
EV = os.path.dirname(STAGE2)
QA = os.path.dirname(EV)
ROOT = "/home/struktured/projects/dr_mario_rl"
for _p in (EV, QA, HERE, STAGE2, os.path.join(EV, "jointdig"),
           os.path.join(EV, "vocab2"), ROOT + "/tmp/combo_term",
           ROOT + "/tmp/endgame", ROOT + "/tmp/tuck", ROOT + "/tmp/pillrng",
           ROOT + "/.claude/worktrees/faithful-sim/src", QA + "/tuck_v3"):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import numpy as np  # noqa: E402

MODEL_JSON = os.path.join(STAGE2, "shippable", "out", "RECOMMENDED_lut64.json")
MODEL_R1_PKL = os.path.join(STAGE2, "shippable", "out", "fitted.pkl")

# The champion's scan order over the 32-slot index (see s2_features.py:75).
CHAMP_ORDER = np.array([v * 8 + c for v in (2, 3, 0, 1) for c in range(8)],
                       dtype=np.int64)

# base_scan output order (feature_battery.NAMES11)
NAMES11 = ["MAXH", "HOLES", "TOPRISK", "SPAWN", "SETUP", "MATCHED", "BURIED",
           "RDYEXT", "VRDY", "CROSS", "POLL"]
_B11 = {n: i for i, n in enumerate(NAMES11)}


# --------------------------------------------------------------------- model
class LutDelta:
    """Additive per-feature LUT, integer pipeline, exactly as it would ship."""

    def __init__(self, feats, scales, tables, name="S1br2_lut8_q64"):
        self.name = name
        self.feats = list(feats)
        self.scales = np.asarray(scales, dtype=np.float64)
        self.tables = [np.asarray(t, dtype=np.int64) for t in tables]
        self.sizes = [len(t) for t in self.tables]
        self.dmin = int(sum(int(t.min()) for t in self.tables))
        self.dmax = int(sum(int(t.max()) for t in self.tables))
        self.span = self.dmax - self.dmin
        # which of the 8 come from base_scan vs from the column heights
        self._plan = []
        for j, f in enumerate(self.feats):
            if f in _B11:
                self._plan.append(("b11", _B11[f]))
            else:
                self._plan.append(("geo", f))

    # ---- feature extraction on ONE post-placement board -------------------
    def feats_of(self, base, H):
        """base = the 11 base_scan terms (int64[11+]); H = int column heights[8]."""
        out = np.empty(len(self.feats), dtype=np.float64)
        for j, (kind, key) in enumerate(self._plan):
            if kind == "b11":
                out[j] = base[key]
            elif key == "e_escape_routes":
                out[j] = int((H <= 10).sum())
            elif key == "d_spawn_h":
                out[j] = max(int(H[3]), int(H[4]))
            elif key == "a_topout_dist":
                out[j] = 16 - int(H.max())
            elif key == "x_hvar":
                out[j] = float(H.astype(np.float64).var())
            elif key == "MAXH":
                out[j] = int(H.max())
            elif key == "d_gvuln_mass":
                out[j] = int(np.maximum(0, H - 11).sum())
            elif key == "d_crit_cols":
                out[j] = int((H >= 14).sum())
            elif key == "x_jagged":
                out[j] = int(np.abs(np.diff(H.astype(np.int32))).sum())
            elif key == "e_escape_reach":
                raise ValueError("OFF_BUDGET feature in a shippable arm")
            else:
                raise KeyError(key)
        return out

    def delta_from_feats(self, x):
        """x float[nfeat] -> int Delta, via the exact shipped integer path."""
        acc = 0
        for j, t in enumerate(self.tables):
            q = int(np.clip(np.rint(x[j] * self.scales[j]), 0, 255))
            if q >= self.sizes[j]:
                q = self.sizes[j] - 1
            acc += int(t[q])
        return acc

    def delta_matrix(self, X):
        """X (n, nfeat) float -> int64[n].  Vectorised, same arithmetic."""
        acc = np.zeros(X.shape[0], dtype=np.int64)
        for j, t in enumerate(self.tables):
            q = np.clip(np.rint(X[:, j] * self.scales[j]), 0, 255).astype(np.int64)
            q = np.minimum(q, self.sizes[j] - 1)
            acc += t[q]
        return acc

    # ---- mutants (a check that cannot fail is not a check) ----------------
    def zeroed(self):
        return LutDelta(self.feats, self.scales,
                        [np.zeros_like(t) for t in self.tables],
                        name=self.name + "_OFF")

    def sign_flipped(self):
        return LutDelta(self.feats, self.scales, [-t for t in self.tables],
                        name=self.name + "_SIGNFLIP")

    def shuffled_tables(self, seed=20260810):
        rng = np.random.default_rng(seed)
        return LutDelta(self.feats, self.scales,
                        [rng.permutation(t) for t in self.tables],
                        name=self.name + "_SHUFTABLE")


def load_recommended(path=MODEL_JSON):
    j = json.load(open(path))
    return LutDelta(j["features"], j["feature_scales"], j["table_int12"])


def load_round1_clean(dose_sd=10):
    """Round-1 S1b_lut8 (the CLEAN, uncontaminated fallback), re-quantised at
    its declared ship dose from the fitted pickle."""
    import pickle
    sys.path.insert(0, os.path.join(STAGE2, "shippable"))
    import models as M  # noqa
    d = pickle.load(open(MODEL_R1_PKL, "rb"))
    m = d["models"]["S1b"]
    # ship-dose rule (PREREG_SHIPPABLE deviation entry 4): rescale so that the
    # sd of Delta over TRAIN rows is `dose_sd` champion score points.
    sd = float(d["train_delta_sd"]["S1b"]) if "train_delta_sd" in d else None
    if sd is None:
        raise RuntimeError("train Delta sd not in pickle; round-1 arm unavailable")
    scaled = M.AdditiveLUT(m.feats, m.sizes, [l * (dose_sd / sd) for l in m.luts])
    q = scaled.quantise(12)
    return LutDelta(d["sel"], d["scales"], [np.asarray(l) for l in q.luts],
                    name="S1b_lut8_round1_clean")


# ------------------------------------------------------------------ the arm
class Arm:
    """Root re-rank arm.  lut=None  => pure champion (used only for smoke
    tests; the real base arm is pressure_rig/p0_ab untouched)."""

    def __init__(self, lut=None, prune=True, tiebreak_flip=False,
                 provenance=True, tag="trt"):
        self.lut = lut
        self.prune = prune
        self.tiebreak_flip = tiebreak_flip     # MUTANT for the identity gate
        self.provenance = bool(provenance)
        self.tag = tag
        self.flips_log = []
        self.stats = {"plies": 0, "flips": 0, "delta_evals": 0, "cands": 0}

    # ---- per-flip provenance (CHAMPION_ITER_PLAN "PER-PLY FLIP PROVENANCE") -
    def _flip_record(self, a, base_a, vals, order, col, vir):
        """One row of mechanism for a single argmax flip.

        Everything here is read off the state the decision was ACTUALLY made
        on: `vals` are the champion's root values, `col`/`vir` the PRE-
        placement board.  `champ_rank_chosen` is the champion's own preference
        position of the treatment-chosen action, using the champion's
        enumeration order as the tiebreak -- so rank 0 is by construction
        `base_action`, which is asserted below.  A flip at rank 1 among tied
        candidates is a different animal from one that reaches down to rank 7
        across a strict gap, and the bare `flips` counter could not tell them
        apart.

        SCHEMA is shared with the oracle lane (experiments/eval47/stage2/
        oracle/oracle_arm.py) so records from different arms pool.  Field
        names follow theirs; `t_to_end`, `tie` and `val_gap` follow the
        definitions in PROVENANCE.md -- see the "schema convergence" section
        for the two places the two lanes had genuinely different semantics.
        """
        fin = np.where(np.isfinite(vals[order]))[0]
        o_slots = order[fin]
        o_vals = vals[order][fin]
        pref = o_slots[np.argsort(-o_vals, kind="stable")]
        assert int(pref[0]) == base_a, "rank order disagrees with base argmax"
        rank = int(np.where(pref == a)[0][0])
        best = float(o_vals.max())
        H = _heights(col)
        return {"arm": self.tag,
                "ply": int(self.stats["plies"]) - 1,
                "t_to_end": -1,             # filled in by play_one at game end
                "viruses": int(np.count_nonzero(vir)),
                "maxh": int(H.max()),
                "d_spawn_h": max(int(H[3]), int(H[4])),
                "tie": int(int((o_vals == best).sum()) > 1),
                "champ_rank_chosen": rank,
                "base_action": int(base_a),
                "trt_action": int(a),
                "val_gap": round(best - float(vals[a]), 3)}

    def choose(self, col, vir, ca, cb, na, nb, w, fl, wt, ws):
        import fast_rtl_x as FX
        import root_search as RS
        import pressure_rig as PR
        from fast_sim_x import NCELL, _expand_core
        from terms47 import g_tower, g_stranded

        vals = np.full(32, np.nan)
        posts_c = {}
        posts_v = {}
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
                slot = var * 8 + cc
                vals[slot] = val
                posts_c[slot] = c1.copy()
                posts_v[slot] = v1.copy()

        order = CHAMP_ORDER[::-1] if self.tiebreak_flip else CHAMP_ORDER
        if not np.isfinite(vals).any():
            return None, None
        base_a = int(order[np.nanargmax(vals[order])])
        self.stats["plies"] += 1
        self.stats["cands"] += int(np.isfinite(vals).sum())
        if self.lut is None:
            return base_a, vals

        best = np.nanmax(vals)
        adj = vals.copy()
        for slot in posts_c:
            if self.prune and vals[slot] < best - self.lut.span:
                adj[slot] = -np.inf            # provably cannot win
                continue
            pc, pv = posts_c[slot], posts_v[slot]
            base = np.empty(FX.NBASE, dtype=np.int64)
            FX._base_scan(pc, pv, fl, base)
            H = _heights(pc)
            adj[slot] = vals[slot] - self.lut.delta_from_feats(
                self.lut.feats_of(base, H))
            self.stats["delta_evals"] += 1
        a = int(order[np.nanargmax(adj[order])])
        if a != base_a:
            self.stats["flips"] += 1
            if self.provenance:
                self.flips_log.append(
                    self._flip_record(a, base_a, vals, order, col, vir))
        return a, vals


def _heights(colflat):
    b = np.asarray(colflat).reshape(16, 8) != 0
    first = np.argmax(b, axis=0)
    return np.where(b.any(axis=0), 16 - first, 0).astype(np.int64)


# ------------------------------------------------------------ game rollout
def play_one(seed, arm):
    """EXACT replica of p0_ab.play_one / pressure_rig.play, with the arm at the
    decision point.  Every other line is the rig's."""
    import pressure_rig as PR
    from drmario.faithful_env import FaithfulDrMarioEnv
    from nes_pills import NesPillSource
    from fb import FB
    import root_search as RS

    C = PR._C
    f0 = len(arm.flips_log)
    level, wt, ws, w, fl = C["level"], C["wt"], C["ws"], C["w"], C["fl"]
    model_kind = C.get("model_kind", "drip")
    bmodel = C.get("bursty_model_obj")
    drip_period = C.get("drip_period") or PR.GARBAGE_PERIOD
    drip_k = C.get("drip_k") or PR.GARBAGE_K
    if model_kind == "bursty":
        from bursty_model import inject_bursty_garbage

    env = FaithfulDrMarioEnv(level=level, seed=seed, max_pills=300)
    env.reset()
    NesPillSource(seed=seed).attach(env)
    env.cur = env._rand_pill()
    env.nxt = env._rand_pill()

    res, garbage_injected, v_at_topout = "stall", 0, None
    actions = []
    for _ in range(300):
        fb = FB.from_board(env.board)
        if env.board.virus_count() == 0:
            res = "clear"
            break
        col, vir = RS.board_flat_from_fb(fb)
        ca, cb = int(env.cur.a), int(env.cur.b)
        na, nb = int(env.nxt.a), int(env.nxt.b)
        a, _vals = arm.choose(col, vir, ca, cb, na, nb, w, fl, wt, ws)
        if a is None:
            break
        actions.append(int(a))
        occ_before = int(np.count_nonzero(env.board.color)) if model_kind == "bursty" else 0
        _, _, term, trunc, info = env.step(int(a))
        if term:
            res = "clear" if info["won"] else "topout"
            if res == "topout":
                v_at_topout = env.board.virus_count()
            break
        if trunc:
            break
        if env.pills_placed >= PR.GARBAGE_MIN_PILLS:
            landed = 0
            if model_kind == "drip":
                if env.pills_placed % drip_period == 0:
                    landed = PR._inject_garbage(env.board, seed,
                                                env.pills_placed, k=drip_k)
            else:
                occ_after = int(np.count_nonzero(env.board.color))
                clear_size = max(0, occ_before + 2 - occ_after)
                if clear_size > 0:
                    landed = inject_bursty_garbage(env.board, bmodel, seed,
                                                   env.pills_placed, clear_size)
            garbage_injected += landed
            if env.board.virus_count() == 0:
                res = "clear"
                break
            if env.board.spawn_blocked():
                res = "topout"
                v_at_topout = env.board.virus_count()
                break
    dies_ahead = int(res == "topout" and v_at_topout is not None
                     and v_at_topout <= PR.DIES_AHEAD_VIRUS_THRESHOLD)
    # t_to_end is only knowable once the game has ended, so it is stamped here
    # rather than at the decision point.  ply 0 of an n-ply game has
    # t_to_end = n-1; the LAST decision of a game has t_to_end = 0.
    recs = arm.flips_log[f0:]
    n_plies = len(actions)
    for r in recs:
        r["seed"] = int(seed)
        r["t_to_end"] = n_plies - 1 - r["ply"]
        r["res"] = res
    out = {"seed": seed, "res": res, "won": int(res == "clear"),
           "topout": int(res == "topout"), "stall": int(res == "stall"),
           "pills": env.pills_placed, "garbage": garbage_injected,
           "dies_ahead": dies_ahead,
           "viruses_left": (int(v_at_topout) if v_at_topout is not None else -1),
           "n_plies": len(actions), "flips": arm.stats["flips"],
           "_actions": actions}
    # `_flips` appears ONLY when provenance is armed, so the existing
    # byte-equality checks (run_ctrl --verify, gate1_identity) keep comparing
    # the same key set they always did.
    if arm.provenance:
        out["_flips"] = recs
    return out


# ------------------------------------------------------- provenance CSV sink
FLIP_COLS = ["seed", "arm", "ply", "t_to_end", "viruses", "maxh", "d_spawn_h",
             "tie", "champ_rank_chosen", "base_action", "trt_action",
             "val_gap", "res"]


def flip_csv_header():
    return ",".join(FLIP_COLS) + "\n"


def flip_csv_row(r):
    return ",".join(str(r[c]) for c in FLIP_COLS) + "\n"
