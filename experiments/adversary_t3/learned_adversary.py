#!/usr/bin/env python3
"""The distilled off-policy adversary: depth-1 candidate enumeration (the same
`_expand_core` primitive ab47.py's base-only decider uses -- cheap, validated,
already this project's convention for a shallow root scan) + the trained value
model scoring each candidate's resulting board against the CURRENT opponent
board, picking the candidate with the highest predicted P(champion dies within
N pills).

This trades search DEPTH for a LEARNED value estimate at depth 1 -- a standard
and well-justified trade (leaf value functions approximating deeper search is
the core idea behind most strong game-playing search, not a new risk introduced
here). It is a different kind of thing from the project's prior "imitation
fails" finding (compressing the CHAMPION's own planner into a learned model, so
the compressed copy had to BE correct to be useful): here the model only needs
to be SUGGESTIVE, because every game it plays is replayed and scored by the real
vs_harness match loop before any number counts. See ADVERSARY_T3.md's off-policy
section for the full statement of why these are not the same claim.

EXPLORATION: `epsilon` (softmax temperature over the top predictions) is
available for use during ITERATIVE data regeneration (retrain-on-new-rollouts
loops), but the policy evaluated in the five-way comparison uses epsilon=0
(pure argmax) -- that is the number that should be reported as "how good is
this policy", not an exploration-inflated one.
"""
from __future__ import annotations

import sys
import os
import pickle
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = "/home/struktured/projects/dr_mario_rl"
QA = "/home/struktured/projects/dr-mario-qa-wt/experiments"
for _p in (HERE, ROOT + "/tmp/combo_term", ROOT + "/tmp/endgame", ROOT + "/tmp/tuck",
           ROOT + "/tmp/pillrng", ROOT + "/.claude/worktrees/faithful-sim/src", QA,
           QA + "/tuck_v3"):
    if _p not in sys.path:
        sys.path.insert(0, _p)

DEFAULT_MODEL_PATH = "/mnt/data/drmario_adversary_t3/checkpoints/adversary_value_model.pkl"

_MODEL_CACHE = {}


def load_model(path=DEFAULT_MODEL_PATH):
    if path not in _MODEL_CACHE:
        with open(path, "rb") as fh:
            _MODEL_CACHE[path] = pickle.load(fh)
    return _MODEL_CACHE[path]


class LearnedAdversaryDecider:
    """Opponent-aware: choose(board, cur, nxt, opp_board). Depth-1 candidate
    enumeration scored by the trained value model. `epsilon>0` samples from a
    softmax over predicted kill-probabilities instead of taking the argmax --
    exploration knob for data regeneration, NOT for the reported comparison."""

    _opponent_aware = True

    def __init__(self, model_path=DEFAULT_MODEL_PATH, epsilon=0.0, rng=None):
        bundle = load_model(model_path)
        self.model = bundle["model"]
        self.feature_names = bundle["feature_names"]
        self.epsilon = float(epsilon)
        self.rng = rng or np.random.default_rng(0)
        self._counters = None   # RunningAttackCounters, set by reset_game()
        self._ply = 0

    def reset_game(self):
        from adversary_features import RunningAttackCounters
        self._counters = RunningAttackCounters()
        self._ply = 0

    def note_attack_sent(self):
        if self._counters is not None:
            self._counters.note_attack_sent()

    def note_attack_received(self):
        if self._counters is not None:
            self._counters.note_attack_received()

    def choose(self, board, cur, nxt, opp_board):
        import fast_rtl_x as FX
        from fast_sim_x import NCELL, _expand_core
        from cascade_chain_x import _leaf_chain, _base_scan, NBASE, NT
        import adversary_features as AF

        if self._counters is None:
            self.reset_game()

        own_col, own_vir = FX.board_flat(board)
        opp_col, opp_vir = FX.board_flat(opp_board)
        own_lnk = np.ascontiguousarray(board.link, dtype=np.int8).reshape(-1)
        w, fl = FX.variant("winner")

        base1 = np.empty(NBASE, dtype=np.int64)
        _base_scan(own_col, own_vir, fl, base1)
        c1 = np.empty(NCELL, dtype=np.int8); v1 = np.empty(NCELL, dtype=np.int8)
        l1 = np.empty(NCELL, dtype=np.int8); mask = np.empty(NCELL, dtype=np.int8)
        terms = np.empty(NT, dtype=np.int64)

        cands = []   # (action, feature_row)
        for o4 in range(4):
            var = int(FX._VAR_OF_O4[o4])
            for cc in range(8):
                ok, nv, cells, leaf1, ch1 = _leaf_chain(
                    own_col, own_vir, own_lnk, base1, var, cc, cur.a, cur.b, w, fl,
                    c1, v1, l1, mask, terms, 0, True)
                if ok == 0:
                    continue
                feat = AF.extract(c1, v1, opp_col, opp_vir,
                                  cells_cleared=int(cells), chain_depth=int(ch1),
                                  atk_sent_running=self._counters.sent,
                                  atk_recv_running=self._counters.received,
                                  ply=self._ply)
                cands.append((var * 8 + cc, feat))

        self._ply += 1
        if not cands:
            return None

        X = np.stack([f for _, f in cands])
        probs = self.model.predict_proba(X)[:, 1]

        if self.epsilon > 0:
            t = max(self.epsilon, 1e-3)
            logits = probs / t
            logits -= logits.max()
            p = np.exp(logits); p /= p.sum()
            idx = self.rng.choice(len(cands), p=p)
        else:
            idx = int(np.argmax(probs))
        return cands[idx][0]
