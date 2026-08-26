"""H12ArmWithBoards — READ-ONLY capture of EVERY TIE PLY (keeps included).

⚠ THE SEALED FILE `h12_arm.py` IS NOT MODIFIED, AND THE DECISION PATH IS NOT
RE-IMPLEMENTED. `super().choose()` is called verbatim and its result returned unchanged.

WHY THE CAPTURE MOVED FROM FLIPS TO TIES — the defect this replaces:
`h12_arm.py:113` guards the flip log with `if a != base_a:`, so it records ONLY plies where
H12 changed the champion's move. Scoring on that population is SELECTION ON THE OUTCOME: the
champion's move is by construction the one H12 rejected, so any champion-correlated ranker
scores badly automatically. Measured on 259 banked seeds: champion −93.7%, worst −97.4%,
random 0%, H12 +100%. The registered estimand (§4) is transfer over champion-value TIE GROUPS
— the KEEPS are exactly what makes it unbiased, and they were never recorded.

HOW TIES ARE CAPTURED WITHOUT TOUCHING THE DECISION PATH:
H12 only calls `_fork_label` inside the fork loop, which is reached ONLY after the gate fires
and the top-2 are exactly tied. So wrapping that function observes precisely the tie-ply
candidate set and its labels — keeps included — by recording each call's arguments and return
value.

⚠⚠ PATCH `h12_arm._fork_label`, NOT `oracle_arm._fork_label`. `h12_arm.py:24` does
`from oracle_arm import (... _fork_label ...)` and calls it BARE at :83, so it holds its own
module-level binding taken at import time. Rebinding the source module has NO effect on the
importer. The first version of this file patched `oracle_arm` and recorded ZERO ties and ZERO
flips on 4 seeds — a silent total failure, caught only because a banked KEEP record was required
as proof before committing the full run. The wrapper is a pure observer: it forwards to the original and returns its value
unchanged, so it cannot alter a decision. It is installed for the duration of one `choose` and
removed immediately after.
"""
import base64
import numpy as np
from h12_arm import H12Arm


class H12ArmWithBoards(H12Arm):
    """Certified H12, plus a record for EVERY tie ply (flip or keep) with planes."""

    def __init__(self, *a, **kw):
        super().__init__(*a, **kw)
        self.tie_log = []

    def choose(self, env, seed, C, bmodel, w, fl, wt, ws, ply):
        from fb import FB
        import root_search as RS
        from fast_sim_x import NCELL, _expand_core
        import h12_arm as HA          # NOT oracle_arm: see note below

        fb = FB.from_board(env.board)
        col, vir = RS.board_flat_from_fb(fb)
        ca, cb = int(env.cur.a), int(env.cur.b)

        acc = {}            # candidate slot -> [survived_sum, progress_sum, n_forks]
        order = []
        orig = HA._fork_label

        def _observer(env_, action, *args, **kw):
            out = orig(env_, action, *args, **kw)      # forward verbatim
            s, p = out
            k = int(action)
            if k not in acc:
                acc[k] = [0, 0, 0]; order.append(k)
            acc[k][0] += int(s); acc[k][1] += int(p); acc[k][2] += 1
            return out                                  # return verbatim

        HA._fork_label = _observer
        try:
            a, base_a = super().choose(env, seed, C, bmodel, w, fl, wt, ws, ply)
        finally:
            HA._fork_label = orig                       # always restore

        if acc and a is not None:
            c1 = np.empty(NCELL, dtype=np.int8)
            v1 = np.empty(NCELL, dtype=np.int8)
            planes = {}
            for slot in order:
                var, cc = divmod(int(slot), 8)
                ok, _nv, _cells = _expand_core(col, vir, var, cc, ca, cb, c1, v1)
                if ok:
                    planes[str(int(slot))] = base64.b64encode(
                        c1.tobytes() + v1.tobytes()).decode("ascii")
            labels = [[acc[k][0], acc[k][1]] for k in order]
            prog = [acc[k][1] for k in order]
            best = max(prog); second = sorted(prog)[-2] if len(prog) > 1 else best
            self.tie_log.append({
                "seed": int(seed), "ply": int(ply),
                "arm": f"h12_true_m{self.tie_margin}_e{self.trigger_eps}",
                "cands": [int(k) for k in order],
                "labels": labels,
                "base_action": int(base_a), "trt_action": int(a),
                "is_flip": int(a != base_a),             # ← keeps are recorded too
                "margin_sum": int(best - second),
                "fork_samples": int(self.fork_samples),
                "horizon": int(self.horizon),
                "planes": planes,
            })
        return a, base_a


class H12ArmMutantNoMargin(H12ArmWithBoards):
    """MUTANT for G-IDENTITY — margin gate disabled. MUST FAIL the identity check."""

    def __init__(self, *a, **kw):
        super().__init__(*a, **kw)
        self.margin_sum = 0
