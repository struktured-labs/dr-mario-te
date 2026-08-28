"""m1_harvest.py — M1 label-campaign harvester (REGISTRATION_M1_LABELS.md).

M1HarvestArm = OracleArm(label_mode="const") — champion-const play, the
software mirror of the baseline being replaced — plus a pure OBSERVATION side
channel at selected plies: the promoted H16 tribunal (screen SCREEN_FORKS x
ALL dedup'd candidates + confirm CONFIRM_FORKS x top-KEEP(+champ), H=25,
dist_seed CRN, samples 0..7 with the same screen/confirm index split the
teacher uses) is run and its per-fork surv AND prog labels are BANKED.
Play is never overridden; the trajectory stays exactly champion-const.

Selection per ply (registration sec 3): stratum trigger (no cooldown) · band
(quota 2/game, earliest) · healthy-tall control (1/game, ply>=60, maxh>=10,
trigger quiet) · pre-drawn random plies (L20 1/game, L11M 2/game — tagged even
when another class also applies, so the random sample stays
trigger-independent for E-M1c). Adjudications capped at CAP/game; cap hits
counted (R51: the filter is explicit and counted).

Banked per game: schema m1v1 · per-ply 8-column height trace (E-M1a/b/c read
this, not the adjudicated states) · adjudication records with per-candidate
per-fork surv/prog, the WHETHER verdict under the promoted override rule, and
the R52 degeneracy flag (all-candidate labels identical — flagged, kept).

Tribunal constants are the promoted teacher's (h16_arm.py c098f56d); asserted
against h16_arm at import so drift is loud.
"""
import os
import random
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "h16"))
sys.path.insert(0, os.path.join(HERE, "..", "eval47", "stage2", "oracle"))
sys.path.insert(0, os.path.join(HERE, "..", "labels146"))

import h16_arm as H16  # noqa: E402  (constants authority; never edited)
from oracle_arm import (OracleArm, _champ_values, _champ_action,  # noqa: E402
                        _fork_label, dist_seed, heights, CHAMP_ORDER)

SCREEN_FORKS = H16.SCREEN_FORKS          # 2
CONFIRM_FORKS = H16.CONFIRM_FORKS        # 6
KEEP = H16.KEEP                          # 8
ROLLOUT_H = H16.ROLLOUT_H                # 25
OVR_CHAMP_MAX = H16.OVR_CHAMP_MAX        # 3
OVR_DELTA_MIN = H16.OVR_DELTA_MIN        # 3
assert (SCREEN_FORKS, CONFIRM_FORKS, KEEP, ROLLOUT_H,
        OVR_CHAMP_MAX, OVR_DELTA_MIN) == (2, 6, 8, 25, 3, 3)

CAP = 15                    # adjudications/game (registration sec 3, A1)
BAND_QUOTA = 2
HEALTHY_QUOTA = 1
RAND_QUOTA = {"L20": 1, "L11M": 2}
RAND_RANGE = (10, 250)
# A1 trigger thinning: adjudicate each trigger-class ply with prob THIN_P
# (seeded, reproducible). Random-quota plies are NEVER thinned (E-M1c needs
# the trigger-independent sample intact); traces are never thinned either, so
# no registered endpoint is touched — this is a label-VOLUME knob (cost),
# targeting ~3 trigger adjudications/game against ~15-28 uncooled fires.
THIN_P = {"L20": 0.12, "L11M": 0.20}
SCHEMA = "m1v1"

# stratum triggers (registration sec 3; wide12 blessed provisional 2026-08-26)
def trig_vals(H):
    return {"dsh": int(max(H[3], H[4])), "wide": int(max(H[2:6])),
            "maxh": int(max(H))}


def stratum_fire(stratum, tv):
    if stratum == "L20":
        return tv["dsh"] >= 13, 10 <= tv["dsh"] <= 12
    if stratum == "L11M":
        return tv["wide"] >= 12, 10 <= tv["wide"] <= 11
    raise ValueError(stratum)


class M1HarvestArm(OracleArm):
    def __init__(self, stratum, seed, mode="campaign", window_start=None,
                 **kw):
        # mode="backfill" (A5, approved 2026-08-28): adjudicate EVERY trigger
        # ply with ply >= window_start — no thinning, no cap, no
        # band/healthy/random. Density rider: backfill segments oversample
        # the death window BY DESIGN and are banked separately; consumers
        # must stratify/weight, never pool silently with the base bank.
        assert mode in ("campaign", "backfill")
        assert (window_start is not None) == (mode == "backfill")
        kw.setdefault("label_mode", "const")
        kw.setdefault("provenance", False)
        super().__init__(**kw)
        assert self.label_mode == "const"
        self.mode = mode
        self.window_start = window_start
        self.stratum = stratum
        self.seed = seed
        self.trace = []                  # per-ply [8 heights]
        self.adjs = []
        self.counters = {"trigger": 0, "band": 0, "healthy": 0, "random": 0,
                         "cap_hits": 0, "thin": 0, "thinned": 0,
                         "degenerate": 0, "tribunal_forks": 0}
        rng = random.Random(seed ^ 0xD15711)
        self.rand_plies = set(rng.sample(range(*RAND_RANGE),
                                         RAND_QUOTA[stratum]))
        self.thin_rng = random.Random(seed ^ 0xC0FFEE)
        self.band_left = BAND_QUOTA
        self.healthy_left = HEALTHY_QUOTA

    # ------------------------------------------------------------ selection
    def choose(self, env, seed, C, bmodel, w, fl, wt, ws, ply):
        H = heights(env.board.color)
        Hl = [int(x) for x in H]
        self.trace.append(Hl)
        tv = trig_vals(Hl)
        fire, band = stratum_fire(self.stratum, tv)
        if self.mode == "backfill":
            if fire and ply >= self.window_start:
                rec = self._tribunal(env, seed, C, bmodel, w, fl, wt, ws,
                                     ply, tv, ["backfill"])
                if rec is not None:
                    self.adjs.append(rec)
                    self.counters["trigger"] += 1
            return super().choose(env, seed, C, bmodel, w, fl, wt, ws, ply)
        classes = []
        if fire:
            if self.thin_rng.random() < THIN_P[self.stratum]:
                classes.append("trigger")
            else:
                self.counters["thinned"] += 1
        elif band and self.band_left > 0 and ply >= 20:
            # ply floor: the L11/L20 opening fill is congenitally tall, and
            # without it the band quota burns on ply-0/1 degenerate states
            # (measured in the pre-smoke micro-test)
            classes.append("band")
        elif (self.healthy_left > 0 and ply >= 60 and tv["maxh"] >= 10):
            classes.append("healthy")
        if ply in self.rand_plies:
            classes.append("random")
        if classes:
            if len(self.adjs) < CAP:
                rec = self._tribunal(env, seed, C, bmodel, w, fl, wt, ws,
                                     ply, tv, classes)
                if rec is not None:
                    self.adjs.append(rec)
                    for c in classes:
                        self.counters[c] += 1
                    if "band" in classes:
                        self.band_left -= 1
                    if "healthy" in classes:
                        self.healthy_left -= 1
            else:
                self.counters["cap_hits"] += 1
        return super().choose(env, seed, C, bmodel, w, fl, wt, ws, ply)

    # ------------------------------------------------------------ tribunal
    def _tribunal(self, env, seed, C, bmodel, w, fl, wt, ws, ply, tv,
                  classes):
        import labelcore as LC
        from fb import FB
        import root_search as RS

        fb = FB.from_board(env.board)
        col, vir = RS.board_flat_from_fb(fb)
        vals = _champ_values(col, vir, int(env.cur.a), int(env.cur.b),
                             int(env.nxt.a), int(env.nxt.b), w, fl, wt, ws)
        base_a = _champ_action(vals, CHAMP_ORDER)
        if base_a is None:
            return None
        ents = LC.enumerate_candidates(env, dedup=True)
        if len(ents) < 2:
            self.counters["thin"] += 1
            return None
        champ_ent = None
        for e in ents:
            e["val"] = float(vals[e["rep_slot"]])
            e["s1"], e["p1"] = [], []
            if base_a in e["slots"]:
                champ_ent = e
        assert champ_ent is not None, (seed, ply, base_a)

        for s in range(SCREEN_FORKS):
            fseed = dist_seed(seed, ply, s)
            for e in ents:
                surv, prog = _fork_label(env, e["rep_slot"], C, fseed,
                                         bmodel, w, fl, wt, ws, ROLLOUT_H)
                e["s1"].append(int(surv))
                e["p1"].append(int(prog))
                self.counters["tribunal_forks"] += 1

        ranked = sorted(ents, key=lambda e: (-sum(e["s1"]), -e["val"]))
        short = ranked[:KEEP]
        if champ_ent not in short:
            short = short + [champ_ent]
        for e in short:
            e["s2"], e["p2"] = [], []
        for s in range(SCREEN_FORKS, SCREEN_FORKS + CONFIRM_FORKS):
            fseed = dist_seed(seed, ply, s)
            for e in short:
                surv, prog = _fork_label(env, e["rep_slot"], C, fseed,
                                         bmodel, w, fl, wt, ws, ROLLOUT_H)
                e["s2"].append(int(surv))
                e["p2"].append(int(prog))
                self.counters["tribunal_forks"] += 1

        best = max(short, key=lambda e: (sum(e["s2"]), e["val"]))
        whether = int(sum(champ_ent["s2"]) <= OVR_CHAMP_MAX
                      and sum(best["s2"]) - sum(champ_ent["s2"])
                      >= OVR_DELTA_MIN
                      and best is not champ_ent)
        s1sums = {sum(e["s1"]) for e in ents}
        s2sums = {sum(e["s2"]) for e in short}
        degenerate = int(len(s1sums) == 1 and len(s2sums) == 1)
        if degenerate:
            self.counters["degenerate"] += 1

        def pack(e, in_short):
            d = {"rep_slot": int(e["rep_slot"]),
                 "slots": [int(x) for x in e["slots"]],
                 "val": round(e["val"], 3),
                 "s1": e["s1"], "p1": e["p1"]}
            if in_short:
                d["s2"], d["p2"] = e["s2"], e["p2"]
            return d

        shortset = {id(e) for e in short}
        return {"ply": int(ply), "classes": classes, "trigger_vals": tv,
                "viruses": int(env.board.virus_count()),
                "champ_slot": int(base_a),
                "champ_rep": int(champ_ent["rep_slot"]),
                "best_rep": int(best["rep_slot"]),
                "champ_s2": int(sum(champ_ent["s2"])),
                "best_s2": int(sum(best["s2"])),
                "whether": whether, "degenerate": degenerate,
                "n_cands": len(ents), "n_short": len(short),
                "cands": [pack(e, id(e) in shortset) for e in ents]}


def game_record(seed, stratum, row, arm, smoke=False):
    """Merge play_one's row with the harvest side channel (schema m1v1)."""
    row.pop("_actions", None)
    return {"schema": SCHEMA, "seed": int(seed), "stratum": stratum,
            "smoke": bool(smoke), "game": row,
            "heights_trace": arm.trace, "adjudications": arm.adjs,
            "counters": arm.counters}
