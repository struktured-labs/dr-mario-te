#!/usr/bin/env python3
"""KILLED-MUTANT GATE for the per-ply flip provenance log.

A check that cannot fail is not a check.  This gate is written so BOTH
directions of the instrument's job can go red:

  T1  NULL DIRECTION.  Treatment policy == base policy (Delta identically
      zero) over whole real games.  The log must contain ZERO flip records.
      A logger that emits on every ply, or that mis-derives `base_a`, fails.

  T2  POSITIVE DIRECTION.  A Delta that is zero everywhere EXCEPT one
      candidate at one INJECTED ply forces exactly one argmax flip, at a
      known ply, to a known action.  The log must contain exactly one record,
      at exactly that ply, with base_a == the champion's own pick and
      trt_a == the champion's rank-1 alternative.  A logger that drops
      records, or stamps the wrong ply, fails.

  T3  FIELD CORRECTNESS.  Every field of the injected record is re-derived by
      an INDEPENDENT probe on a pure-champion replay -- and deliberately in a
      different idiom (plain-Python scans, not the numpy helpers the logger
      uses) so that a wrong-array / wrong-axis mutant cannot pass by symmetry.

  T4  CSV round-trip.

Run:  python test_flip_provenance.py     -> exit 0 iff every case passes.
Mutation evidence (each of these actually going red) is in PROVENANCE.md.
"""
from __future__ import annotations

import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import numpy as np  # noqa: E402

import arm_lut as AL  # noqa: E402

FAILS = []


def check(name, cond, detail=""):
    cond = bool(cond)
    print(f"  [{'PASS' if cond else 'FAIL'}] {name}"
          f"{('  ' + detail) if detail else ''}")
    if not cond:
        FAILS.append(name)
    return cond


def _init(model="lulu"):
    sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(HERE)),
                                    "jointdig"))
    import p0_ab as P
    import pressure_rig as PR
    obj = P.load_lulu() if model == "lulu" else None
    PR._init(11, 0, 20, model_kind=("bursty" if model == "lulu" else "drip"),
             bursty_model_obj=obj)


# --------------------------------------------------------------- the probe
class ChampionProbe:
    """Captures, at ply `target` of a PURE-CHAMPION game, everything the
    provenance record claims -- computed independently of the logger.

    Deliberately plain-Python: `maxh` by scanning the 16x8 grid row by row,
    `viruses` by counting truthy cells.  The logger uses numpy `_heights` and
    `count_nonzero`.  A mutant that scans the wrong plane or the wrong axis
    therefore disagrees with this probe instead of agreeing with itself.
    """

    def __init__(self, target):
        self.target = target
        self.base_a = self.alt_a = None
        self.finite_slots = None
        self.viruses = self.maxh = self.tie = self.val_gap = None

    def wrap(self, arm):
        orig = arm.choose

        def choose(col, vir, ca, cb, na, nb, w, fl, wt, ws):
            ply = arm.stats["plies"]
            a, vals = orig(col, vir, ca, cb, na, nb, w, fl, wt, ws)
            if ply == self.target and vals is not None:
                order = AL.CHAMP_ORDER
                fin = [i for i in range(len(order))
                       if np.isfinite(vals[order[i]])]
                slots = [int(order[i]) for i in fin]
                ovals = [float(vals[s]) for s in slots]
                pref = [s for _, s in
                        sorted(zip(range(len(slots)), slots),
                               key=lambda t: (-ovals[t[0]], t[0]))]
                self.finite_slots = slots
                self.base_a = int(pref[0])
                self.alt_a = int(pref[1])
                best = max(ovals)
                self.tie = int(sum(1 for v in ovals if v == best) > 1)
                self.val_gap = best - float(vals[self.alt_a])
                # plain-Python board scans
                grid = [int(x) for x in np.asarray(col).reshape(-1)]
                hmax = 0
                for c in range(8):
                    for r in range(16):
                        if grid[r * 8 + c] != 0:
                            hmax = max(hmax, 16 - r)
                            break
                self.maxh = hmax
                self.viruses = sum(1 for x in np.asarray(vir).reshape(-1)
                                   if int(x) != 0)
            return a, vals

        return choose


class SlotPenaltyDelta:
    """Delta term: +BIG on ONE candidate at ONE ply, 0 everywhere else.

    Arm.choose walks `for slot in posts_c`, whose insertion order is the
    champion enumeration order (var-major over _VAR_OF_O4 = [2,3,0,1], then
    column) restricted to FEASIBLE slots -- i.e. exactly CHAMP_ORDER filtered
    to finite values.  With prune=False every feasible candidate reaches the
    Delta call, so the k-th call in a ply is the k-th entry of that list.
    `finite_slots` is handed in from the champion probe, which is legitimate
    because the injected game is bit-identical to the champion game up to and
    including the target ply (Delta is 0 before it).
    """

    BIG = 1e9

    def __init__(self, arm_stats, target_ply, blocked_slot, finite_slots):
        self.stats = arm_stats
        self.target = target_ply
        self.blocked = blocked_slot
        self.finite_slots = list(finite_slots)
        self.span = 0.0
        self.feats = []
        self._ply = None
        self._k = 0
        self.hits = 0

    def feats_of(self, base, H):
        return None

    def delta_from_feats(self, _x):
        ply = self.stats["plies"] - 1
        if ply != self._ply:
            self._ply, self._k = ply, 0
        k, self._k = self._k, self._k + 1
        if ply != self.target:
            return 0
        if k < len(self.finite_slots) and self.finite_slots[k] == self.blocked:
            self.hits += 1
            return self.BIG
        return 0


# ------------------------------------------------------------------- gate
def run():
    print("== flip-provenance killed-mutant gate ==")
    _init("lulu")
    lut = AL.load_recommended()

    # ---- T1 NULL DIRECTION -------------------------------------------------
    print("\nT1  identical policies (Delta == 0) must log ZERO flips")
    zero = lut.zeroed()
    tot_recs = tot_plies = 0
    for s in (20000, 20001, 20002, 20003, 20005):
        arm = AL.Arm(lut=zero, prune=False, provenance=True, tag="trt")
        r = AL.play_one(s, arm)
        tot_recs += len(r["_flips"])
        tot_plies += arm.stats["plies"]
    check("T1 zero flip records over identical policies", tot_recs == 0,
          f"records={tot_recs} plies={tot_plies}")
    check("T1 the games were non-trivial (this check COULD have failed)",
          tot_plies > 200, f"plies={tot_plies}")

    # ---- T2 POSITIVE DIRECTION --------------------------------------------
    print("\nT2  a Delta injected at ONE ply must log exactly ONE record there")
    seed, target = 20000, 7
    probe = ChampionProbe(target)
    parm = AL.Arm(lut=None)
    parm.choose = probe.wrap(parm)
    rref = AL.play_one(seed, parm)
    if probe.base_a is None:
        check("T2 probe reached the target ply", False,
              f"game only {rref['n_plies']} plies")
        return False

    iarm = AL.Arm(lut=None, prune=False, provenance=True, tag="trt")
    iarm.lut = SlotPenaltyDelta(iarm.stats, target, probe.base_a,
                               probe.finite_slots)
    rinj = AL.play_one(seed, iarm)
    recs = rinj["_flips"]

    check("T2 the injection actually fired", iarm.lut.hits == 1,
          f"hits={iarm.lut.hits}")
    check("T2 exactly one flip record", len(recs) == 1,
          f"n={len(recs)} plies={iarm.stats['plies']}")
    if len(recs) != 1:
        print("\nFAILED:", FAILS)
        return False
    rec = recs[0]
    check("T2 record is at the injected ply", rec["ply"] == target,
          f"ply={rec['ply']} expected={target}")
    check("T2 base_a is the champion's own pick", rec["base_a"] == probe.base_a,
          f"logged={rec['base_a']} champion={probe.base_a}")
    check("T2 trt_a is the rank-1 alternative, and differs from base",
          rec["trt_a"] == probe.alt_a and rec["trt_a"] != rec["base_a"],
          f"logged={rec['trt_a']} expected={probe.alt_a}")

    # ---- T3 FIELD CORRECTNESS ---------------------------------------------
    print("\nT3  every field re-derived independently must match")
    check("T3 rank == 1 (the penalty demotes base by exactly one place)",
          rec["rank"] == 1, f"rank={rec['rank']}")
    check("T3 t_to_end", rec["t_to_end"] == rinj["n_plies"] - 1 - target,
          f"{rec['t_to_end']} vs {rinj['n_plies'] - 1 - target}")
    check("T3 viruses (plain-Python recount)", rec["viruses"] == probe.viruses,
          f"logged={rec['viruses']} probe={probe.viruses}")
    check("T3 maxh (plain-Python column scan)", rec["maxh"] == probe.maxh,
          f"logged={rec['maxh']} probe={probe.maxh}")
    check("T3 tie flag", rec["tie"] == probe.tie,
          f"logged={rec['tie']} probe={probe.tie}")
    check("T3 val_gap", abs(rec["val_gap"] - probe.val_gap) < 1e-3,
          f"logged={rec['val_gap']} probe={round(probe.val_gap, 3)}")
    check("T3 seed stamped", rec["seed"] == seed)
    check("T3 arm tag stamped", rec["arm"] == "trt")
    check("T3 res stamped", rec["res"] == rinj["res"])

    # ---- T4 CSV round-trip -------------------------------------------------
    print("\nT4  CSV round-trip")
    hdr = AL.flip_csv_header().strip().split(",")
    row = AL.flip_csv_row(rec).strip().split(",")
    back = dict(zip(hdr, row))
    check("T4 column count", len(hdr) == len(row) == len(AL.FLIP_COLS))
    check("T4 values survive",
          int(back["ply"]) == rec["ply"]
          and int(back["trt_a"]) == rec["trt_a"]
          and int(back["t_to_end"]) == rec["t_to_end"]
          and float(back["val_gap"]) == rec["val_gap"])

    print("\n" + ("ALL PASS" if not FAILS else f"FAILED: {FAILS}"))
    return not FAILS


if __name__ == "__main__":
    sys.exit(0 if run() else 1)
