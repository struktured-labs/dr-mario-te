"""H12ArmDataset — LOGGING-ONLY DERIVATIVE of the sealed H12Arm (2026-08-17).

WHY A DERIVATIVE AND NOT AN EDIT
--------------------------------
`h12_arm.py` / `run_h12.py` are SEALED: they produced the certified H12 endpoint
GO (clear +8.5pp, DA 12.52 -> 7.74, N=9000) and their bytes are hashed into
every META.json runtime manifest on disk.  Editing them in place would make
those results unreproducible.  This file therefore COPIES `H12Arm.choose`'s body
verbatim and adds ONE thing: at every gated exact-tie ply it appends a record to
`self.tie_log`.  Nothing else differs.

THE CLAIM THIS FILE MAKES, AND THE GATE THAT CAN FALSIFY IT
-----------------------------------------------------------
CLAIM: logging is causally inert — H12ArmDataset plays byte-for-byte the same
game as H12Arm on every seed.
GATE : `gate_dataset_identity.py` replays N seeds under both arms and compares
the FULL action sequence, not just the outcome.  Its killed mutant is
`perturb_first_tie=True`, which flips the first tie ply to rank-1; that arm MUST
diverge, otherwise the gate is measuring nothing.

WHY THE LOGGING IS FREE
-----------------------
H12Arm already forks all top-4 candidates at every tie ply (the fork loop runs
before the flip decision, not after it), so the rollout labels for CONFIRMED
plies — the negative class of the distillation dataset — are already computed
and then thrown away.  This file keeps them.  Zero extra forks, so the pilot
costs exactly what an H12 true-arm run costs.

WHAT IS LOGGED, AND WHAT IS DELIBERATELY NOT
--------------------------------------------
Per tie ply, per top-4 candidate: the 26 silicon-feasible features (11 champion
eval terms from `_base_scan` on the candidate's POST board + the 15 vocab2
candidate features), the champion value, and the rollout label (survived_sum,
progress_sum).  Plus the pre-board context (viruses, maxh, d_spawn_h, heights,
n_legal).

NON-CAUSAL FIELDS ARE PREFIXED `nc_` AND MUST NEVER ENTER A FEATURE MATRIX.
`nc_t_to_end` and `nc_res` are known only after the game ends; the runner stamps
them for stratification and error analysis only.  This is the trap that a
distillation dataset invites, so the naming makes a leak visible in a column
list rather than hidden in a join.

FEATURE REIMPLEMENTATION IS ON PURPOSE
--------------------------------------
`vocab2/feature_battery.py` hardcodes `/home/struktured/projects/dr-mario-qa-wt/
experiments` onto the FRONT of sys.path at import time, which would silently
re-resolve `nes_pills`/`fast_rtl_x`/`root_search` mid-run and break the runtime
manifest this lane just proved.  So the 15 candidate features are reimplemented
here from their definitions.  `analyse_h12_dataset.py --gate-features` then
cross-checks these values against feature_battery's own code OFFLINE (where
sys.path damage is harmless).  Two independent implementations agreeing is a
stronger check than importing one of them.
"""
import math
import random

import numpy as np

from h12_arm import H12Arm
from oracle_arm import (CHAMP_ORDER, _champ_values, _champ_action, gate_fires,
                        dist_seed, _fork_label, heights, null_keeps_flip)
from temporal_accum import (TemporalState, CAND_TEMPORAL_NAMES,
                            STATE_TEMPORAL_NAMES)

MAX_TIELOG = 400            # a 300-pill game at a ~2% tie dose cannot approach this

BASE_NAMES = ["MAXH", "HOLES", "TOPRISK", "SPAWN", "SETUP", "MATCHED", "BURIED",
              "RDYEXT", "VRDY", "CROSS", "POLL"]
CAND_NAMES = ["a_topout_dist", "a_d_maxh", "b_spawn_prox", "b_spawn_prox_strict",
              "c_das_reach", "c_d_das_reach", "c_nlegal_probe", "c_d_nlegal",
              "d_gvuln_mass", "d_crit_cols", "d_spawn_h",
              "e_escape_routes", "e_escape_reach", "x_hvar", "x_jagged"]
FEAT_NAMES = BASE_NAMES + CAND_NAMES

# vocab2 PREREG sec 8 silicon tagging, quoted verbatim so the feature budget in
# phase 2 is the one that was declared BEFORE anything was fitted.
FREE_IN_COLWALK = {"MAXH", "HOLES", "TOPRISK", "SPAWN", "a_topout_dist",
                   "a_d_maxh", "b_spawn_prox", "b_spawn_prox_strict",
                   "d_spawn_h", "d_crit_cols", "d_gvuln_mass", "x_jagged",
                   "x_hvar", "e_escape_routes", "c_nlegal_probe", "c_d_nlegal"}
OFF_BUDGET = {"c_das_reach", "c_d_das_reach", "e_escape_reach"}

_ALLOW = np.array([15 - abs(c - 3) // 2 for c in range(8)])


def _hexb(arr):
    """128 cells -> 256 hex chars.  Compact, diff-able, and json-safe."""
    return np.asarray(arr, dtype=np.uint8).tobytes().hex()


def _bhash(post_col, post_vir):
    """Stable 12-hex identity of a POST board (colour plane AND virus plane).

    The top-2 champion values tie EXACTLY, which in this game usually means the
    two slots are the same physical placement under two orientation encodings
    (var 2 vs var 3 of a same-colour capsule).  Those candidates are the SAME
    BOARD and carry identical rollout labels, so any "which candidate did the
    rollout prefer" target must dedupe on the board, not on the slot index.
    Features alone are a lossy hash; this is exact.
    """
    import hashlib
    h = hashlib.sha256(np.asarray(post_col, dtype=np.uint8).tobytes()
                       + np.asarray(post_vir, dtype=np.uint8).tobytes())
    return h.hexdigest()[:12]


# ------------------------------------------------- feature kernels (reimpl)
def _heights_flat(cols):
    """cols (n,128) -> (n,8) heights, row 0 = top.  Mirrors
    feature_battery.heights_from_boards."""
    b = np.asarray(cols).reshape(-1, 16, 8) != 0
    first = np.argmax(b, axis=1)
    return np.where(b.any(axis=1), 16 - first, 0).astype(np.int64)


def _das_reach(H):
    """# columns path-reachable from col 3 under H[j] <= 15 - |j-3|//2."""
    ok = H <= _ALLOW[None, :]
    R = np.zeros_like(ok)
    R[:, 3] = ok[:, 3]
    for c in range(2, -1, -1):
        R[:, c] = R[:, c + 1] & ok[:, c]
    for c in range(4, 8):
        R[:, c] = R[:, c - 1] & ok[:, c]
    return R


def _nlegal_probe(H):
    """Engine-true legal placement count (color-independent legality)."""
    horiz = (np.maximum(H[:, :-1], H[:, 1:]) < 16).sum(axis=1)
    vert = (H <= 14).sum(axis=1)
    return 2 * horiz + 2 * vert


def _cand_features(post_cols, Hpost, Hpre, n_legal_pre):
    """The 15 vocab2 candidate features for a batch of POST boards."""
    n = Hpost.shape[0]
    b = np.asarray(post_cols).reshape(n, 16, 8) != 0
    R = _das_reach(Hpost)
    Rpre = _das_reach(Hpre)
    out = {}
    out["a_topout_dist"] = 16 - Hpost.max(axis=1)
    out["a_d_maxh"] = Hpost.max(axis=1) - Hpre.max(axis=1)
    out["b_spawn_prox"] = b[:, 0:3, 2:6].sum(axis=(1, 2))
    out["b_spawn_prox_strict"] = b[:, 0:2, 3:5].sum(axis=(1, 2))
    out["c_das_reach"] = R.sum(axis=1)
    out["c_d_das_reach"] = R.sum(axis=1) - Rpre.sum(axis=1)
    out["c_nlegal_probe"] = _nlegal_probe(Hpost)
    out["c_d_nlegal"] = _nlegal_probe(Hpost) - n_legal_pre
    out["d_gvuln_mass"] = np.maximum(0, Hpost - 11).sum(axis=1)
    out["d_crit_cols"] = (Hpost >= 14).sum(axis=1)
    out["d_spawn_h"] = np.maximum(Hpost[:, 3], Hpost[:, 4])
    out["e_escape_routes"] = (Hpost <= 10).sum(axis=1)
    out["e_escape_reach"] = (R & (Hpost <= 10)).sum(axis=1)
    out["x_hvar"] = Hpost.astype(np.float64).var(axis=1)
    out["x_jagged"] = np.abs(np.diff(Hpost.astype(np.int64), axis=1)).sum(axis=1)
    return out


def candidate_feature_rows(col, vir, ca, cb, cands, fl):
    """(len(cands), 26) feature matrix + the pre-board context.

    Pure function of the CURRENT board and the capsule: it re-expands each
    candidate into scratch buffers and never touches `env`.  That is what makes
    the identity gate passable rather than merely lucky.
    """
    import fast_rtl_x as FX
    from fast_sim_x import NCELL, _expand_core

    n = len(cands)
    posts = np.zeros((n, NCELL), dtype=np.int8)
    postv = np.zeros((n, NCELL), dtype=np.int8)
    base11 = np.zeros((n, 11), dtype=np.float64)
    post_nvir = np.zeros(n, dtype=np.int64)
    ok_all = np.zeros(n, dtype=np.int64)
    c1 = np.empty(NCELL, dtype=np.int8)
    v1 = np.empty(NCELL, dtype=np.int8)
    base = np.empty(FX.NBASE, dtype=np.int64)

    FX._base_scan(np.asarray(col, dtype=np.int8), np.asarray(vir, dtype=np.int8),
                  fl, base)
    pre11 = np.array([float(base[k]) for k in range(11)])
    pre_nvir = int(base[11])

    for i, slot in enumerate(cands):
        var, cc = int(slot) // 8, int(slot) % 8
        ok, nv, _cells = _expand_core(col, vir, var, cc, ca, cb, c1, v1)
        ok_all[i] = ok
        if ok == 0:                      # cannot happen: cands are finite-valued
            continue
        posts[i] = c1
        postv[i] = v1
        FX._base_scan(c1, v1, fl, base)
        for k in range(11):
            base11[i, k] = float(base[k])
        post_nvir[i] = int(base[11])

    Hpre = _heights_flat(np.asarray(col).reshape(1, -1))
    Hpost = _heights_flat(posts)
    n_legal_pre = _nlegal_probe(Hpre)
    cf = _cand_features(posts, Hpost, np.repeat(Hpre, n, axis=0),
                        int(n_legal_pre[0]))
    X = np.concatenate(
        [base11, np.stack([np.asarray(cf[k], dtype=np.float64)
                           for k in CAND_NAMES], axis=1)], axis=1)
    # RAW BOARDS ARE STORED, NOT JUST FEATURES.  The expensive thing in this
    # dataset is the 15-pill rollout label (~200 core-seconds per seed); the
    # features are microseconds.  Storing the pre- and post-boards means phase 2
    # can revise the entire feature vocabulary — the exact failure mode of the
    # vocabulary wall — without re-paying for a single fork.
    ctx = {"pre_feats": [round(float(v), 4) for v in pre11],
           "pre_nvir": pre_nvir,
           "pre_H": [int(h) for h in Hpre[0]],
           "n_legal_pre": int(n_legal_pre[0]),
           "post_nvir": [int(v) for v in post_nvir],
           "expand_ok": [int(v) for v in ok_all],
           "pre_col": _hexb(col), "pre_vir": _hexb(vir),
           "post_col": [_hexb(p) for p in posts],
           "post_vir": [_hexb(p) for p in postv],
           "post_hash": [_bhash(posts[i], postv[i]) for i in range(n)]}
    return X, ctx


# ---------------------------------------------------------------- the arm
class H12ArmDataset(H12Arm):
    """H12Arm + a tie-ply record.  `perturb_first_tie` is the killed mutant."""

    def __init__(self, perturb_first_tie=False, temporal=True, **kw):
        super().__init__(**kw)
        self.perturb_first_tie = bool(perturb_first_tie)
        self._perturbed = False
        self.temporal = bool(temporal)
        self.tstate = TemporalState() if self.temporal else None
        self.tie_log = []

    def choose(self, env, seed, C, bmodel, w, fl, wt, ws, ply):
        # ---- body copied verbatim from H12Arm.choose (sealed 2026-08-15) ----
        from fb import FB
        import root_search as RS

        fb = FB.from_board(env.board)
        col, vir = RS.board_flat_from_fb(fb)

        # TEMPORAL FOLD.  Runs at EVERY ply, gated or not, and BEFORE any early
        # return, because the accumulators are per-GAME history: a counter that
        # skipped the ungated ~62% of plies would be measuring something else
        # and would not match what a cart accumulates.  It reads the board and
        # writes only to self, so it cannot reach the decision — which the
        # identity gate then PROVES rather than assumes.  Forks never call
        # choose(), so fork play cannot contaminate the counters.
        if self.temporal:
            self.tstate.observe(col, vir)

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

        legal = [int(s) for s in order if np.isfinite(vals[int(s)])]
        if len(legal) < 2:
            return base_a, base_a
        fv = sorted((float(vals[c]) for c in legal), reverse=True)
        if fv[0] != fv[1]:
            return base_a, base_a
        self.stats["tie_plies"] += 1

        ranked = sorted(range(len(legal)),
                        key=lambda i: (-vals[legal[i]], i))[:self.topk]
        cands = [legal[i] for i in ranked]
        assert cands[0] == base_a, "rank-0 candidate must be the champion's pick"
        if len(cands) <= 1:
            return base_a, base_a

        labels = [(0, 0) for _ in cands]
        if self.label_mode != "const":
            for sample in range(self.fork_samples):
                fork_seed = dist_seed(seed, ply, sample)
                for i, candidate in enumerate(cands):
                    survived, progress = _fork_label(
                        env, candidate, C, fork_seed, bmodel, w, fl, wt, ws,
                        self.horizon)
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
            if labels[best_i][1] - labels[0][1] < self.margin_sum:
                self.stats["margin_rejected_flips"] += 1
                a = base_a
                raw_flip = False
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
                self.flip_log.append({
                    "seed": int(seed),
                    "arm": f"h12_{self.label_mode}_m{self.tie_margin}",
                    "ply": ply, "viruses": viruses, "maxh": int(H.max()),
                    "d_spawn_h": d_spawn_h,
                    "base_action": int(base_a), "trt_action": int(a),
                    "champ_rank_chosen": int(best_i),
                    "labels": [list(map(int, l)) for l in labels],
                    "cands": [int(c) for c in cands],
                    "margin_sum": int(labels[best_i][1] - labels[0][1]),
                    "fork_samples": self.fork_samples})
        # ---- end verbatim body; everything below is LOGGING ONLY -----------

        self._log_tie(env, seed, ply, col, vir, cands, vals, labels, best_i,
                      base_a, a, viruses, d_spawn_h, fl)

        if self.perturb_first_tie and not self._perturbed and len(cands) > 1:
            # KILLED MUTANT: a deliberate decision change.  The identity gate
            # must report divergence here, or it cannot report agreement above.
            self._perturbed = True
            return cands[1], base_a
        return a, base_a

    def _log_tie(self, env, seed, ply, col, vir, cands, vals, labels, best_i,
                 base_a, a, viruses, d_spawn_h, fl):
        if len(self.tie_log) >= MAX_TIELOG:
            return
        X, ctx = candidate_feature_rows(col, vir, int(env.cur.a),
                                        int(env.cur.b), cands, fl)
        H = heights(env.board.color)
        rec = {
            "seed": int(seed), "ply": int(ply),
            "viruses": int(viruses), "maxh": int(H.max()),
            "d_spawn_h": int(d_spawn_h),
            "pills_placed": int(env.pills_placed),
            "cur": [int(env.cur.a), int(env.cur.b)],
            "nxt": [int(env.nxt.a), int(env.nxt.b)],
            "cands": [int(c) for c in cands],
            "champ_vals": [round(float(vals[c]), 6) for c in cands],
            "labels": [[int(l[0]), int(l[1])] for l in labels],
            "rollout_rank1": int(best_i),
            "base_action": int(base_a), "chosen_action": int(a),
            "flipped": int(a != base_a),
            "margin_sum": int(labels[best_i][1] - labels[0][1]),
            "fork_samples": int(self.fork_samples),
            "feats": [[round(float(v), 6) for v in row] for row in X],
        }
        rec.update(ctx)
        if self.temporal:
            # State is candidate-INVARIANT and so cancels in any difference
            # design; it is logged once per event and consumed as context.
            # Only tfeats varies by candidate and gets differenced.
            rec["tstate"] = self.tstate.state_features()
            tf = []
            for i in range(len(cands)):
                d = self.tstate.candidate_features(
                    col,
                    np.frombuffer(bytes.fromhex(ctx["post_col"][i]),
                                  dtype=np.uint8),
                    np.frombuffer(bytes.fromhex(ctx["post_vir"][i]),
                                  dtype=np.uint8))
                tf.append([float(d[k]) for k in CAND_TEMPORAL_NAMES])
            rec["tfeats"] = tf
        self.tie_log.append(rec)
