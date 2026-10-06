"""STEER11 clock tests (run before any couch11 farm game).
  T1  sim cascade timing (vs_race._cascade_falls) == the calibration's feature code (steer11_clockcal.cascade_timed: its
      own gravity copy + fair_20261004.count_runs) on EVERY clearing placement of the T3 games (both code paths on the
      same board), and on all 32 actions of every 10th board
  T2  sim garbage fall rows (gravity passes after the row-0 write) == the calibration's definition (max over the
      volley's columns of top - 1 of the pre-drop stack) on every release of the T3 games
  T3  end-to-end R100 on 3 couch11 LULU-race games: t_end == sum(traced charges) / FPS, every traced charge == the clock
      formula recomputed from its traced features (independent arithmetic), garbage charges == nrel, pill charges == pills
  T4  POSITIVE CONTROL: the same games on the legacy clock reproduce the banked STEER10 rows, and couch11 changes t_end
      (a clock that changed nothing would pass T3 vacuously)
"""
import sys, os, json
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
os.chdir(HERE)
import import_pin; import_pin.pin()
import vs_race as V
import steer11_clockcal as CC
import steer10_run as S10
import steer11_run as S11
import stuck_probe as SP

ok = True
stat = {"t1": 0, "t1bad": 0, "t1all": 0, "t1allbad": 0, "t2": 0, "t2bad": 0, "boards": 0}
_orig_cf = V._cascade_falls
_orig_gd = V.garbage_drop_timed


def _cf_checked(b):
    b2 = b.clone()
    f1 = _orig_cf(b)
    st = CC.cascade_timed(b2)
    stat["t1"] += 1
    if [s[2] for s in st] != f1:
        stat["t1bad"] += 1
    return f1


def _gd_checked(board, size, colours, phase):
    from rom_attack_rule import garbage_columns
    exp = 0
    for c in garbage_columns(size, phase):
        if 0 <= c < board.cols:
            top = next((r for r in range(16) if board.color[r, c] > 0), 16)
            exp = max(exp, top - 1)
    n0 = len(V.TRACE) if V.TRACE is not None else 0
    out = _orig_gd(board, size, colours, phase)
    if V.TRACE is not None and len(V.TRACE) > n0:
        stat["t2"] += 1
        if V.TRACE[-1][2] != exp:
            stat["t2bad"] += 1
    return out


_orig_pf = V.pill_frames


def _pf_all_actions(hmax, pp, env=None, action=None):
    """every 10th board: both cascade implementations on all 32 straight placements"""
    stat["boards"] += 1
    if V.CLOCK is not None and stat["boards"] % 10 == 0:
        for a in range(32):
            o, c, p = env._decode(a)
            b = env.board.clone()
            if not b.place_pill(p, o, c):
                continue
            b2 = b.clone()
            f1 = _orig_cf(b); st = CC.cascade_timed(b2)
            stat["t1all"] += 1
            stat["t1allbad"] += [s[2] for s in st] != f1
    return _orig_pf(hmax, pp, env, action)


V._cascade_falls = _cf_checked
V.garbage_drop_timed = _gd_checked
V.pill_frames = _pf_all_actions

SEEDS = (39134, 39136, 39138)
bank = {}
for l in open("steer10/lulu10b_s10_base_39134.jsonl"):
    x = json.loads(l); bank[x["seed"]] = x
V.SIZES = S10.SIZES["lulu202610b"]
steer, choose, dec = S10.make("s10_base")
clock = S11.load_clock("couch11")
print("clock", clock)
FPS = V.FPS


def formula(e):
    c = clock
    if e[0] == "p":
        _, fall, ns, cf, f = e
        return c["base"] + c["fall"] * fall + c["step"] * ns + c["cfall"] * cf, f
    _, cells, gf, gs, gcf, f = e
    return (c["vol"] + c["gsize"] * cells + c["gfall"] * gf + (c["gclear"] if gs else 0.0) + c["gstep"] * gs
            + c["gcfall"] * gcf), f


for s in SEEDS:
    V.CLOCK = None; V.TRACE = None
    r0 = SP.play_race(s, "s10_base", 2.84, level=11, steer=steer, probe=None, choose=choose)
    same_legacy = r0["t_end"] == bank[s]["t_end"] and r0["pills"] == bank[s]["pills"] and r0["how"] == bank[s]["how"]
    V.CLOCK = clock; V.TRACE = []
    r1 = SP.play_race(s, "s10_base", 2.84, level=11, steer=steer, probe=None, choose=choose)
    tr = V.TRACE; V.TRACE = None; V.CLOCK = None
    tot = sum(e[-1] for e in tr) / FPS
    mism = sum(1 for e in tr if abs(formula(e)[0] - formula(e)[1]) > 1e-9)
    ng = sum(1 for e in tr if e[0] == "g"); npl = sum(1 for e in tr if e[0] == "p")
    t3 = abs(round(tot, 2) - r1["t_end"]) <= 0.011 and mism == 0 and ng == r1["nrel"] and npl == r1["pills"]
    t4 = same_legacy and abs(r1["t_end"] - r0["t_end"]) > 1.0
    ok &= t3 and t4
    gcl = sum(1 for e in tr if e[0] == "g" and e[3])
    pf = [e for e in tr if e[0] == "p"]
    print(f"T3 seed {s}: couch11 t_end {r1['t_end']} vs sum of charges {tot:.2f} s; {npl} pill + {ng} garbage charges "
          f"({gcl} set off a clear), formula mismatches {mism}; nrel {r1['nrel']}, garb_s {r1['garb_s']}, how {r1['how']}, "
          f"s/pill {r1['t_end'] / r1['pills']:.2f} (pill charges mean {np.mean([e[-1] for e in pf]) / FPS:.2f} s) "
          f"-> {'ok' if t3 else 'FAIL'}")
    print(f"T4 seed {s}: legacy replay t_end {r0['t_end']} == banked {bank[s]['t_end']}: {same_legacy}; couch11 differs by "
          f"{r1['t_end'] - r0['t_end']:+.1f} s (pills {r0['pills']} -> {r1['pills']}, recv {r0['tiles_recv']} -> "
          f"{r1['tiles_recv']}) -> {'ok' if t4 else 'FAIL'}")
print(f"T1 cascade falls, sim == calibration code: chosen placements {stat['t1'] - stat['t1bad']}/{stat['t1']}, "
      f"all-32-action sweep {stat['t1all'] - stat['t1allbad']}/{stat['t1all']}")
print(f"T2 garbage fall rows, sim == calibration definition: {stat['t2'] - stat['t2bad']}/{stat['t2']}")
ok &= stat["t1bad"] == 0 and stat["t1"] > 50 and stat["t1allbad"] == 0 and stat["t1all"] > 500 and stat["t2bad"] == 0 and stat["t2"] > 5
print("CLOCK TESTS", "PASS" if ok else "FAIL")
sys.exit(0 if ok else 1)
