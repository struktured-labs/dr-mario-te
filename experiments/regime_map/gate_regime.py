#!/usr/bin/env python3
"""Instrument gate suite for the failure-regime map (regime-141), 12-rule standard.

Every detector is proven ALIVE by a mutant it must kill (rule 7); the suite
fails unless every real check passes AND every mutant is caught. Gate sheet by
last line: GATE_REGIME_PASS / GATE_REGIME_FAIL.

Pure gates (instant)
  g1  amplifier binds       : bursty_x2 fire prob == min(1, 2p) and strictly
                              above base somewhere.        [M1: alpha inert]
  g2  aim binds             : aimed column draw leads with spawn cols (3,4),
                              size + column count preserved. [M2: aim inert]
  g3  aim replay-determinism: sample(seed,gp) idempotent (game.py re-samples).
  g4  level binds (env)     : virus count = min(4*(lvl+1), 84) at 11 and 20.
                                                           [M3: level inert]
  g5  reader alive          : analyze summarize/validate move when a row is
                              edited.                      [M4: reader mutant]
  g6  POPULATION gate alive : validate() rejects out-of-block seeds, mislabeled
                              pressure, wrong fw, duplicates. [M5: population
                              mutant -- the rule-7 required one]

RTL gates (real games, run with --rtl; ~20 min wall, parallel)
  g7  end-to-end variants   : one short L11 game per bursty variant on the same
                              seed -- rows carry the volleys capture; aimed rows
                              aim; all deciders are the champion RTL (fw md5).
  g8  end-to-end level      : one short L20 clean game -- start_viruses == 84
                              through the actual farm loop.
(g-a determinism, fresh-vs-fresh and fresh-vs-reused, is gate_validate.py in
cosim_farm, run separately by the chain -- not duplicated here.)
"""
from __future__ import annotations

import json
import os
import sys
from concurrent.futures import ProcessPoolExecutor

HERE = os.path.dirname(os.path.abspath(__file__))
FARM = os.path.normpath(os.path.join(HERE, "..", "cosim_farm"))
RL = "/home/struktured/projects/dr_mario_rl"
QA = "/home/struktured/projects/dr-mario-qa-wt/experiments"
for _p in (HERE, FARM, RL + "/.claude/worktrees/faithful-sim/src", QA, QA + "/eval47"):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import regime_pressure as RP                       # noqa: E402
from regime_pressure import AmplifiedModel, AimedModel  # noqa: E402

FW = "/mnt/data/drmario_cosim/fw/s20b"
CHAMPION_MD5 = "e970e9ab0208cdbce1d39ed33e2f51ee"

RESULTS = []


def check(name, ok, detail=""):
    RESULTS.append((name, bool(ok), detail))
    print(f"  {'PASS' if ok else 'FAIL'}  {name}  {detail}")
    return bool(ok)


# --------------------------------------------------------------- pure gates
def base_model():
    import run_bursty_v1_1_validity as V11
    m = V11.build_v1_1()
    m.meta = {k: v for k, v in m.meta.items() if k != "raw_events"}
    return m


def detector_amplified(base, cand):
    """True iff cand's fire prob is exactly min(1, 2*base) and above base somewhere."""
    strictly_above = False
    for cs in range(0, 16):
        pb, _ = base.fire_probability(cs)
        pc, _ = cand.fire_probability(cs)
        if abs(pc - min(1.0, 2 * pb)) > 1e-12:
            return False
        if pc > pb + 1e-12:
            strictly_above = True
    return strictly_above


def detector_aimed(base, cand, n_draws=300):
    """True iff cand aims every draw at (3,4)-first with size/count preserved."""
    for i in range(n_draws):
        seed, gp = 30000 + 2 * (i % 97), 25 + (i % 60)
        nb, cb = base.sample(seed, gp)
        nc, cc = cand.sample(seed, gp)
        if nb != nc or len(cb) != len(cc):
            return False
        want = [3, 4][:len(cc)]
        if list(cc[:len(want)]) != want:
            return False
        if len(set(cc)) != len(cc):
            return False
    return True


def pure_gates():
    b = base_model()
    x2 = AmplifiedModel(b, 2.0)
    aim = AimedModel(b)

    check("g1 amplifier binds", detector_amplified(b, x2))
    check("g1-M1 mutant killed (alpha inert -> detector rejects)",
          not detector_amplified(b, b))

    check("g2 aim binds", detector_aimed(b, aim))
    check("g2-M2 mutant killed (aim inert -> detector rejects)",
          not detector_aimed(b, b))

    ok3 = all(aim.sample(s, gp) == aim.sample(s, gp)
              for s in (30000, 30002, 31004) for gp in (25, 40, 77))
    check("g3 aim replay-determinism", ok3)

    from drmario.faithful_env import FaithfulDrMarioEnv

    def viruses_at(level):
        e = FaithfulDrMarioEnv(level=level, seed=30000, max_pills=10)
        e.reset()
        return e.board.virus_count()

    def det_level(vfn):
        return vfn(11) == 48 and vfn(20) == 84

    check("g4 level binds (env)", det_level(viruses_at),
          f"L11={viruses_at(11)} L20={viruses_at(20)}")
    check("g4-M3 mutant killed (level inert -> detector rejects)",
          not det_level(lambda _lvl: viruses_at(11)))

    # g5 reader + g6 population, against analyze_regime's real code paths
    import analyze_regime as AR

    def mkrow(arm, seed, result, **kw):
        variant, level, max_pills, s0, mx = AR.CELLS[arm]
        r = dict(seed=seed, arm=arm, level=level, result=result,
                 pills=90, garbage=10, dies_ahead=0,
                 pressure_model=variant, fw_md5=CHAMPION_MD5, volleys=[],
                 wall_secs=1000.0)
        r.update(kw)
        return r

    rows = [mkrow("c1_L11_bursty", 30000 + 2 * i, "clear") for i in range(10)]
    s_before = AR.summarize(rows)["c1_L11_bursty"]["failures"]
    rows_mut = [dict(r) for r in rows]
    rows_mut[3]["result"] = "topout"
    s_after = AR.summarize(rows_mut)["c1_L11_bursty"]["failures"]
    check("g5 reader alive (edited row moves the summary)",
          s_before == 0 and s_after == 1, f"{s_before}->{s_after}")

    check("g6 population gate: clean baseline accepted",
          AR.validate(rows) == [])
    check("g6-M5a population mutant killed (out-of-block seed)",
          AR.validate(rows + [mkrow("c1_L11_bursty", 52100, "clear")]) != [])
    check("g6-M5b population mutant killed (mislabeled pressure)",
          AR.validate([mkrow("c1_L11_bursty", 30020, "clear",
                             pressure_model="bursty_x2")]) != [])
    check("g6-M5c population mutant killed (wrong firmware)",
          AR.validate([mkrow("c1_L11_bursty", 30020, "clear",
                             fw_md5="deadbeef")]) != [])
    check("g6-M5d population mutant killed (duplicate row)",
          AR.validate(rows + [dict(rows[0])]) != [])
    check("g6-M5e population mutant killed (unaimed volley in aim cell)",
          AR.validate([mkrow("c3_L11_aim", 31000, "clear",
                             volleys=[[30, 2, 2, [6, 1]]])]) != [])


# ---------------------------------------------------------------- RTL gates
def _rtl_game(args):
    variant, level, max_pills, seed = args
    import game as G
    from cosim import Cosim
    m, pressure = RP.wrap_model(None if variant == "clean" else base_model(), variant)
    with Cosim(os.path.join(os.environ.get("COSIM_FARM_BUILD",
                                           os.path.join(FARM, "build")),
                            "obj_farm", "farm_vsim"), FW) as cs:
        return variant, G.play_game(cs, seed=seed, level=level,
                                    max_pills=max_pills, pressure=pressure, model=m)


def rtl_gates():
    # seeds 33000/33002 sit OUTSIDE every registered cell block (30000-32998) so
    # instrument games never touch a seed the map will report on.
    jobs = [("bursty", 11, 90, 33000), ("bursty_x2", 11, 90, 33000),
            ("bursty_aim", 11, 90, 33000), ("clean", 20, 30, 33002)]
    with ProcessPoolExecutor(max_workers=4) as ex:
        got = dict(ex.map(_rtl_game, jobs))

    for v in ("bursty", "bursty_x2", "bursty_aim"):
        r = got[v]
        check(f"g7 {v}: champion RTL decided", r["fw_md5"] == CHAMPION_MD5)
        check(f"g7 {v}: volley capture present",
              isinstance(r.get("volleys"), list) and
              (r["garbage"] == 0 or len(r["volleys"]) > 0),
              f"garbage={r['garbage']} volleys={len(r.get('volleys', []))}")
    aimed = got["bursty_aim"]["volleys"]
    ok_aim = aimed and all(cols[:len([3, 4][:len(cols)])] == [3, 4][:len(cols)]
                           for _, _, _, cols in aimed)
    check("g7 aim end-to-end (every RTL volley aimed)", bool(ok_aim),
          f"n_volleys={len(aimed)}")
    r20 = got["clean"]
    check("g8 L20 end-to-end (84 viruses through the farm loop)",
          r20["start_viruses"] == 84 and r20["fw_md5"] == CHAMPION_MD5,
          f"start_viruses={r20['start_viruses']}")


def main():
    rtl = "--rtl" in sys.argv
    print("== pure gates ==")
    pure_gates()
    if rtl:
        print("== RTL gates ==")
        rtl_gates()
    n_fail = sum(1 for _, ok, _ in RESULTS if not ok)
    out = {"results": [{"name": n, "pass": ok, "detail": d} for n, ok, d in RESULTS],
           "pass": n_fail == 0, "rtl_included": rtl}
    with open(os.path.join(HERE, "gates",
                           "gate_regime_rtl.json" if rtl else "gate_regime_pure.json"),
              "w") as f:
        json.dump(out, f, indent=1)
    print("GATE_REGIME_" + ("PASS" if n_fail == 0 else f"FAIL ({n_fail})"))
    sys.exit(0 if n_fail == 0 else 1)


if __name__ == "__main__":
    main()
