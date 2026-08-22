"""H12 arm: the SHIPPABLE gated rollout, as calibrated 2026-08-15.

Differences from OracleArm (each is a frozen design choice, see
H12_CALIBRATION_NOTES.md on v8-rematch):
  1. TIE-ONLY TRIGGER: intervenes only when gate_fires AND the top-2 champion
     values are EXACTLY tied (the near-tie world where all 7 certified gaps live).
  2. THETA-MARGIN DOSE GATE: a flip is accepted only if the winner's fork
     progress SUM beats the champion action's by >= ceil(tie_margin*fork_samples)
     (theta=0.5 x 5 samples -> sum diff >= 3). Undosed arm is churn: median
     fair gain at the raw tie is 0.00.
  3. SAMPLED FUTURES ONLY: future_mode='dist' (on-cart observation set —
     the arm never sees the true capsule stream beyond cur+next).

label_mode='true'  -> the H12 treatment arm.
label_mode='shuffle' -> the dose-matched null (same trigger + margin machinery,
     shuffled labels, thinned by null_keep_* per the A13 procedure).
"""
import math
import random

import numpy as np

from oracle_arm import (OracleArm, CHAMP_ORDER, _champ_values, _champ_action,
                        gate_fires, dist_seed, _fork_label, heights,
                        null_keeps_flip)


class H12Arm(OracleArm):
    def __init__(self, tie_margin=0.5, trigger_eps=0.0, **kw):
        kw.setdefault("future_mode", "dist")
        kw.setdefault("fork_samples", 5)
        assert kw["future_mode"] == "dist", "H12 is sampled-futures only"
        super().__init__(**kw)
        self.tie_margin = float(tie_margin)
        # trigger_eps=0.0 reproduces the certified exact-tie trigger exactly:
        # `fv[0] - fv[1] > 0.0` is the same predicate as `fv[0] != fv[1]`.
        # eps>0 widens the trigger to near-ties (H14 AMENDMENT 1).
        self.trigger_eps = float(trigger_eps)
        assert self.trigger_eps >= 0.0
        self.margin_sum = math.ceil(self.tie_margin * self.fork_samples - 1e-9)
        self.stats["tie_plies"] = 0
        self.stats["margin_rejected_flips"] = 0

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

        legal = [int(s) for s in order if np.isfinite(vals[int(s)])]
        if len(legal) < 2:
            return base_a, base_a
        fv = sorted((float(vals[c]) for c in legal), reverse=True)
        if fv[0] - fv[1] > self.trigger_eps:    # H12 delta 1 (eps=0: exact tie)
            return base_a, base_a
        self.stats["tie_plies"] += 1

        ranked = sorted(range(len(legal)),
                        key=lambda i: (-vals[legal[i]], i))[:self.topk]
        cands = [legal[i] for i in ranked]
        assert cands[0] == base_a, "rank-0 candidate must be the champion's pick"
        if self.trigger_eps > 0.0:
            # keep only candidates inside the eps window (plus the champion)
            cands = [c for c in cands
                     if float(vals[c]) >= fv[0] - self.trigger_eps]
        if len(cands) <= 1:
            return base_a, base_a

        labels = [(0, 0) for _ in cands]
        if self.label_mode != "const":
            for sample in range(self.fork_samples):
                fork_seed = dist_seed(seed, ply, sample)   # H12 delta 3: sampled
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
            # H12 delta 2: theta-margin on fork progress sums
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
                    "arm": (f"h12_{self.label_mode}_m{self.tie_margin}"
                            f"_e{self.trigger_eps}"),
                    "ply": ply, "viruses": viruses, "maxh": int(H.max()),
                    "d_spawn_h": d_spawn_h,
                    "base_action": int(base_a), "trt_action": int(a),
                    "champ_rank_chosen": int(best_i),
                    "labels": [list(map(int, l)) for l in labels],
                    "cands": [int(c) for c in cands],
                    "margin_sum": int(labels[best_i][1] - labels[0][1]),
                    "fork_samples": self.fork_samples})
        return a, base_a
