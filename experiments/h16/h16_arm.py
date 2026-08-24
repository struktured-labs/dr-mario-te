"""h16_arm.py — H16: the rollout-gated champion (REGISTRATION_H16.md sec 1/4).

H16Arm = certified H12Arm, bit-identical when quiet, plus one additive
pre-pass at each decision ply:

  TRIGGER   d_spawn_h >= 13 with cooldown 5 (re-fires early iff dsh grew).
  SCREEN    every dedup'd-by-resulting-board candidate x 2 CRN forks, H=25.
  CONFIRM   top-8 of the screen (+ the evaluator's pick) x 6 fresh forks.
  OVERRIDE  iff surv6(champ) <= 3 AND surv6(best) - surv6(champ) >= 3;
            play best by (surv6, H12 value).  Otherwise IDENTICAL H12
            behaviour (its certified tie machinery untouched).

The H12 substrate always runs label_mode='true' — the E2 mutant shuffles
ONLY the H16 confirm labels (h16_label_mode='shuffle'), because the
combination is its own object and the substrate is already certified.

Mutant knobs (gate_h16.py): never_fire (m-neverfire bit-identity),
no_cooldown (m-cooldown ~3.5x growth), h16_no_dedup (m-nodedup population).
"""
import os
import random
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "eval47", "stage2", "oracle"))
sys.path.insert(0, os.path.join(HERE, "..", "labels146"))

from h12_arm import H12Arm                                  # noqa: E402
from oracle_arm import (_champ_values, _champ_action, _fork_label,  # noqa: E402
                        dist_seed, heights, null_keeps_flip, CHAMP_ORDER)

# registered constants (REGISTRATION_H16.md; do not tune)
TRIGGER_DSH = 13
COOLDOWN = 5
SCREEN_FORKS = 2
KEEP = 8
CONFIRM_FORKS = 6
ROLLOUT_H = 25
OVR_CHAMP_MAX = 3          # confirm-surv(champ) <= 3 of 6
OVR_DELTA_MIN = 3          # confirm-surv(best) - champ >= 3 of 6


class H16Arm(H12Arm):
    def __init__(self, trigger_dsh=TRIGGER_DSH, cooldown=COOLDOWN,
                 screen_forks=SCREEN_FORKS, keep=KEEP,
                 confirm_forks=CONFIRM_FORKS, rollout_horizon=ROLLOUT_H,
                 never_fire=False, no_cooldown=False, h16_no_dedup=False,
                 h16_label_mode="true", h16_null_keep_num=1,
                 h16_null_keep_den=1, **kw):
        assert h16_label_mode in ("true", "shuffle")
        kw.setdefault("label_mode", "true")     # H12 substrate stays certified
        super().__init__(**kw)
        self.trigger_dsh = int(trigger_dsh)
        self.cooldown = int(cooldown)
        self.screen_forks = int(screen_forks)
        self.keep = int(keep)
        self.confirm_forks = int(confirm_forks)
        self.rollout_horizon = int(rollout_horizon)
        self.never_fire = bool(never_fire)
        self.no_cooldown = bool(no_cooldown)
        self.h16_no_dedup = bool(h16_no_dedup)
        self.h16_label_mode = h16_label_mode
        self.h16_null_keep_num = int(h16_null_keep_num)
        self.h16_null_keep_den = int(h16_null_keep_den)
        self._last_adj_ply = -(10 ** 9)
        self._last_adj_dsh = -1
        for k in ("h16_trigger_plies", "h16_adjudications", "h16_overrides",
                  "h16_null_rejected", "h16_screen_forks",
                  "h16_confirm_forks", "h16_cand_width"):
            self.stats[k] = 0

    # ------------------------------------------------------------- pre-pass
    def choose(self, env, seed, C, bmodel, w, fl, wt, ws, ply):
        if not self.never_fire:
            H = heights(env.board.color)
            dsh = int(max(H[3], H[4]))
            if dsh >= self.trigger_dsh:
                self.stats["h16_trigger_plies"] += 1
                if (self.no_cooldown
                        or ply - self._last_adj_ply >= self.cooldown
                        or dsh > self._last_adj_dsh):
                    a, base_a = self._adjudicate(env, seed, C, bmodel,
                                                 w, fl, wt, ws, ply, dsh)
                    self._last_adj_ply, self._last_adj_dsh = ply, dsh
                    if a is not None:
                        # parity with play_one's stats readers: this ply is
                        # scored here, not by the substrate.
                        self.stats["plies"] += 1
                        return a, base_a
        return super().choose(env, seed, C, bmodel, w, fl, wt, ws, ply)

    # -------------------------------------------------------- adjudication
    def _adjudicate(self, env, seed, C, bmodel, w, fl, wt, ws, ply, dsh):
        """Returns (override_action, base_action) or (None, None)."""
        import labelcore as LC
        from fb import FB
        import root_search as RS

        fb = FB.from_board(env.board)
        col, vir = RS.board_flat_from_fb(fb)
        vals = _champ_values(col, vir, int(env.cur.a), int(env.cur.b),
                             int(env.nxt.a), int(env.nxt.b), w, fl, wt, ws)
        base_a = _champ_action(vals, CHAMP_ORDER)
        if base_a is None:
            return None, None
        ents = LC.enumerate_candidates(env, dedup=not self.h16_no_dedup)
        if len(ents) < 2:
            return None, None
        self.stats["h16_adjudications"] += 1
        self.stats["h16_cand_width"] += len(ents)
        champ_ent = None
        for e in ents:
            e["val"] = float(vals[e["rep_slot"]])
            if base_a in e["slots"]:
                champ_ent = e
        assert champ_ent is not None, (seed, ply, base_a)

        # SCREEN: samples 0..m1-1, all candidates
        for e in ents:
            e["s1"] = 0
        for s in range(self.screen_forks):
            fseed = dist_seed(seed, ply, s)
            for e in ents:
                surv, _prog = _fork_label(env, e["rep_slot"], C, fseed,
                                          bmodel, w, fl, wt, ws,
                                          self.rollout_horizon)
                e["s1"] += int(surv)
                self.stats["h16_screen_forks"] += 1

        ranked = sorted(ents, key=lambda e: (-e["s1"], -e["val"]))
        short = ranked[:self.keep]
        if champ_ent not in short:
            short = short + [champ_ent]

        # CONFIRM: samples m1..m1+m2-1, shortlist only (fresh futures)
        for e in short:
            e["s2"] = 0
        for s in range(self.screen_forks,
                       self.screen_forks + self.confirm_forks):
            fseed = dist_seed(seed, ply, s)
            for e in short:
                surv, _prog = _fork_label(env, e["rep_slot"], C, fseed,
                                          bmodel, w, fl, wt, ws,
                                          self.rollout_horizon)
                e["s2"] += int(surv)
                self.stats["h16_confirm_forks"] += 1

        if self.h16_label_mode == "shuffle":       # E2 dose-matched null
            rng = random.Random(seed * 100003 + ply)
            s2s = [e["s2"] for e in short]
            rng.shuffle(s2s)
            for e, v in zip(short, s2s):
                e["s2"] = v

        best = max(short, key=lambda e: (e["s2"], e["val"]))
        if not (champ_ent["s2"] <= OVR_CHAMP_MAX
                and best["s2"] - champ_ent["s2"] >= OVR_DELTA_MIN):
            return None, None
        if best is champ_ent:
            return None, None
        if (self.h16_label_mode == "shuffle"
                and not null_keeps_flip(seed, ply, self.h16_null_keep_num,
                                        self.h16_null_keep_den)):
            self.stats["h16_null_rejected"] += 1
            return None, None

        self.stats["h16_overrides"] += 1
        if self.provenance:
            self.flip_log.append({
                "seed": int(seed), "arm": f"h16_{self.h16_label_mode}",
                "kind": "h16_override", "ply": int(ply), "dsh": int(dsh),
                "viruses": int(env.board.virus_count()),
                "base_action": int(base_a),
                "trt_action": int(best["rep_slot"]),
                "champ_s2": int(champ_ent["s2"]), "best_s2": int(best["s2"]),
                "champ_s1": int(champ_ent["s1"]), "best_s1": int(best["s1"]),
                "n_cands": len(ents), "n_short": len(short),
                "val_gap": round(champ_ent["val"] - best["val"], 3)})
        return int(best["rep_slot"]), int(base_a)
