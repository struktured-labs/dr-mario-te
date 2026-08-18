"""H13 arm: H12 with GATE-V2 (any-column height), everything else unchanged.

MOTIVATION (task #110, [[dr-mario-gate-center-blind]]): H12's gate is
`d_spawn_h >= 12 OR viruses <= 8` where `d_spawn_h = max(H[3], H[4])` — the
SPAWN-PATH columns only. Both photographed died-ahead deaths in the owner's
2026-08-15 soak were EDGE towers (cols 1-2; col 6) with LOW centre columns, so
the gate was closed during the fatal build.

GATE-V2:  max(H) >= maxh_thresh  OR  d_spawn_h >= 12  OR  viruses <= 8

The v1 clauses are RETAINED, so gate-v2 is a strict SUPERSET of gate-v1 at any
threshold: dose is monotone and no H12 trigger is lost. Everything downstream —
exact top-2 tie trigger, top-4 candidate set, 5 sampled-future forks, theta 0.5
margin, null thinning — is H12's `choose`, inherited unchanged.

⚠ THIS ARM IS BEING PRICED, NOT ADVOCATED. The exhibit that motivated the lane
(the 13:21 col-2 "tower") was priced by the forced-move harness as the UNIQUELY
BEST move on its board — see [[dr-mario-death1321-col2-vindicated]]. A wider
gate is therefore at least as likely to add DOSE without adding JUDGMENT, and
each extra trigger costs rollout compute and risks breaking a good tie-keep. A
clean NO-GO is a fully successful outcome for this lane.

Mutants live here too (gate_mode="m_*") so the killed-mutant gate exercises the
same code path the treatment uses, not a separate transcription.
"""
import numpy as np

from oracle_arm import gate_fires, heights, GATE_DSPAWN_H, GATE_VIRUSES
from h12_arm import H12Arm

# Registered gate-v2 threshold variants. 13 is the pre-registered primary
# (one row of headroom above the v1 spawn threshold); 12 is the registered
# secondary (matches v1's threshold, applied to every column).
V2_THRESHOLDS = (12, 13)

GATE_MODES = ("v1", "v2", "m_inverted", "m_offby4_low", "m_offby4_high",
              "m_always")


def gate_v2(env, maxh_thresh):
    """Any-column height gate. Returns (fires, d_spawn_h, viruses, maxh)."""
    H = heights(env.board.color)
    d_spawn_h = int(max(H[3], H[4]))
    maxh = int(H.max())
    vir = int(env.board.virus_count())
    fires = (maxh >= int(maxh_thresh)
             or d_spawn_h >= GATE_DSPAWN_H
             or vir <= GATE_VIRUSES)
    return fires, d_spawn_h, vir, maxh


class H13Arm(H12Arm):
    """H12Arm with a swappable gate. gate_mode='v1' MUST equal sealed H12."""

    def __init__(self, gate_mode="v2", maxh_thresh=13, **kw):
        assert gate_mode in GATE_MODES, gate_mode
        super().__init__(**kw)
        self.gate_mode = gate_mode
        self.maxh_thresh = int(maxh_thresh)
        # Gate-open accounting is per-PLY and independent of whether a tie or a
        # margin followed, so a null arm's dose can be decomposed rather than
        # argued: fire rate = gate rate x tie|gate x margin-pass|tie (rule 5).
        self.stats["v1_gated_plies"] = 0
        self.stats["v2_only_gated_plies"] = 0

    def arm_tag(self):
        return (f"h13_{self.gate_mode}_t{self.maxh_thresh}_"
                f"{self.label_mode}_m{self.tie_margin}")

    def _gate(self, env):
        mode = self.gate_mode
        if mode == "v1":
            fires, d_spawn_h, vir = gate_fires(env)
            self.stats["v1_gated_plies"] += int(fires)
            return fires, d_spawn_h, vir

        thresh = self.maxh_thresh
        if mode == "m_offby4_low":
            thresh = self.maxh_thresh - 4
        elif mode == "m_offby4_high":
            thresh = self.maxh_thresh + 4
        fires, d_spawn_h, vir, _maxh = gate_v2(env, thresh)

        if mode == "m_inverted":
            fires = not fires
        elif mode == "m_always":
            fires = True

        v1_fires, _, _ = gate_fires(env)
        self.stats["v1_gated_plies"] += int(v1_fires)
        self.stats["v2_only_gated_plies"] += int(fires and not v1_fires)
        return fires, d_spawn_h, vir


# ------------------------------------------------------------------ census
# The gate-RATE half of the dose can be measured WITHOUT paying for a single
# fork: it is a function of the board the champion reaches, and the champion's
# trajectory is identical under every gate that never fires (const arm). This
# instrument is ~40x cheaper per seed than an H12/H13 pair and answers "does
# gate-v2's dose explode" on its own.
class GateCensusArm(H12Arm):
    """Plays the CHAMPION (no forks) and records both gates at every ply."""

    def __init__(self, thresholds=V2_THRESHOLDS, **kw):
        kw["label_mode"] = "const"
        super().__init__(**kw)
        self.thresholds = tuple(int(t) for t in thresholds)
        self.rows = []

    def choose(self, env, seed, C, bmodel, w, fl, wt, ws, ply):
        from fb import FB
        import root_search as RS
        from oracle_arm import CHAMP_ORDER, _champ_values, _champ_action

        fb = FB.from_board(env.board)
        col, vir_plane = RS.board_flat_from_fb(fb)
        vals = _champ_values(col, vir_plane, int(env.cur.a), int(env.cur.b),
                             int(env.nxt.a), int(env.nxt.b), w, fl, wt, ws)
        base_a = _champ_action(vals, CHAMP_ORDER)
        if base_a is None:
            return None, None
        self.stats["plies"] += 1

        H = heights(env.board.color)
        d_spawn_h = int(max(H[3], H[4]))
        maxh = int(H.max())
        vir = int(env.board.virus_count())
        legal = [int(s) for s in CHAMP_ORDER if np.isfinite(vals[int(s)])]
        fv = sorted((float(vals[c]) for c in legal), reverse=True)
        exact_tie = int(len(fv) >= 2 and fv[0] == fv[1])

        v1 = int(d_spawn_h >= GATE_DSPAWN_H or vir <= GATE_VIRUSES)
        row = {"seed": int(seed), "ply": int(ply), "maxh": maxh,
               "d_spawn_h": d_spawn_h, "viruses": vir, "n_legal": len(legal),
               "exact_tie": exact_tie, "gate_v1": v1}
        for t in self.thresholds:
            row[f"gate_v2_t{t}"] = int(v1 or maxh >= t)
        self.rows.append(row)
        return base_a, base_a
