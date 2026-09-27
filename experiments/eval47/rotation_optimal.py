"""Is a player's CW/CCW mix the RIGHT mix for the placements they actually made?

MODEL. A pill spawns at H and the orientation ring is ORIENT_CYCLE = [H, V, HF, VF],
so the rotation distance from spawn to the locked orientation is delta = index(final):

    delta 0  H   no rotation needed
    delta 1  V   1 press CW      -- 3 presses if taken CCW  => CW-efficient
    delta 2  HF  2 presses either way, cost-identical       => FREE choice
    delta 3  VF  1 press CCW     -- 3 presses if taken CW   => CCW-efficient

Everything here lives inside the TRACKER's own ring, so it does not depend on the
unresolved question of whether the tracker's ring runs the same direction as the ROM's
$A5 (which is why the notebook still labels buttons CW/CCW rather than A/B).

CONTROL. For every non-monocolor pill, (cw - ccw) mod 4 must equal delta. If the ring,
the spawn orientation or the direction labels were wrong this would fail. Measured:
233/233 and 52/52, zero mismatches.

WASTE is charged only where it is unambiguous: a pill rotated entirely in ONE direction
whose delta was cheaper the other way. Pills that mix directions are counted separately
as corrections -- overshoot-and-come-back is already the film review's own correction
taxonomy and is not a direction-choice error. Free (delta 2) pills are NEVER charged;
a mutant that charges them is one of the three this file must kill.
"""
import collections
import csv
import os
import sys

EVAL47 = os.path.dirname(os.path.abspath(__file__))
LE = os.path.join(EVAL47, "results", "latency_events")
RING = ["H", "V", "HF", "VF"]

PLAYERS = {
    "struktured": [os.path.join(LE, "film_20260804", f"{m}.csv") for m in ("m1", "m2", "m3", "m4")],
    "dr. lulu": [os.path.join(LE, "film_20260808", "p1_m3.csv")],
}


def load(paths):
    return [r for p in paths for r in csv.DictReader(open(p))]


def classify(rows, charge_free=False, swap_forced=False):
    """-> per-player aggregate. charge_free / swap_forced exist for the mutant gate."""
    agg = collections.Counter()
    waste = 0
    waste_pills = 0
    mixed = 0
    for r in rows:
        toks = [t.split("@")[0] for t in r["rotation_seq"].split(",") if t]
        if "tog" in toks:
            agg["monocolor"] += 1
            continue
        if r["final_orient"] not in RING:
            agg["unparsed"] += 1
            continue
        cw, ccw = toks.count("cw"), toks.count("ccw")
        d = RING.index(r["final_orient"])
        if swap_forced:
            d = (4 - d) % 4
        agg["pills"] += 1
        agg["cw"] += cw
        agg["ccw"] += ccw
        agg[f"delta{d}"] += 1
        minimal = min(d, 4 - d)
        agg["ideal_presses"] += minimal

        match (cw > 0 and ccw > 0):
            case True:
                mixed += 1
            case False:
                used = cw + ccw
                # A delta-2 pill taken in ONE direction always costs exactly 2, which
                # IS its minimum -- so subtracting the minimum already makes free
                # choices unchargeable, and an `if d == 2: extra = 0` guard on top is
                # dead code (it was, and it made the mutant below equivalent). The
                # mutant therefore has to attack the minimum itself.
                floor = 0 if (d == 2 and charge_free) else minimal
                extra = used - floor
                if extra > 0:
                    waste += extra
                    waste_pills += 1
    agg["waste"] = waste
    agg["waste_pills"] = waste_pills
    agg["mixed"] = mixed
    return agg


def ideal_mix(a):
    n1, n2, n3 = a["delta1"], a["delta2"], a["delta3"]
    dump_cw = n1 + 2 * n2
    dump_cw_total = dump_cw + n3
    split_cw = n1 + n2
    split_total = n1 + n3 + 2 * n2
    return {
        "forced_cw": n1, "forced_ccw": n3, "free": n2,
        "dump_cw_pct": 100.0 * dump_cw / dump_cw_total if dump_cw_total else None,
        "split_cw_pct": 100.0 * split_cw / split_total if split_total else None,
    }


def mutants():
    rows = load(PLAYERS["struktured"])
    base = classify(rows)
    ok = True

    m1 = classify(rows, swap_forced=True)
    b_ideal, m_ideal = ideal_mix(base), ideal_mix(m1)
    hit = abs(b_ideal["dump_cw_pct"] - m_ideal["dump_cw_pct"]) > 1e-9
    print(f"  mutant: forced classes swapped (delta -> 4-delta)   "
          f"{'KILLED' if hit else '*** SURVIVED'} "
          f"(ideal CW {b_ideal['dump_cw_pct']:.1f}% -> {m_ideal['dump_cw_pct']:.1f}%)")
    ok &= hit

    m2 = classify(rows, charge_free=True)
    hit2 = m2["waste"] > base["waste"]
    print(f"  mutant: free (delta-2) choices charged as waste     "
          f"{'KILLED' if hit2 else '*** SURVIVED'} "
          f"(waste {base['waste']} -> {m2['waste']})")
    ok &= hit2

    # Consistency control doubles as a mutant: corrupt the ring, it must break.
    bad = 0
    for r in rows:
        toks = [t.split("@")[0] for t in r["rotation_seq"].split(",") if t]
        if "tog" in toks or r["final_orient"] not in RING:
            continue
        cw, ccw = toks.count("cw"), toks.count("ccw")
        if (cw - ccw) % 4 != (RING.index(r["final_orient"]) + 1) % 4:
            bad += 1
    print(f"  mutant: ring rotated by one (delta+1)               "
          f"{'KILLED' if bad else '*** SURVIVED'} ({bad} consistency violations)")
    ok &= bad > 0
    return ok


def main():
    print("KILLED-MUTANT GATE")
    if not mutants():
        print("GATE FAILED"); return 1
    print("  GATE: PASS\n")

    for name, paths in PLAYERS.items():
        rows = load(paths)
        a = classify(rows)
        idl = ideal_mix(a)
        directional = a["cw"] + a["ccw"]
        actual_cw = 100.0 * a["cw"] / directional if directional else None
        n_all = len(rows)

        print(f"== {name}  ({n_all} pills; {a['pills']} non-monocolor, "
              f"{a['monocolor']} monocolor excluded)")
        print(f"  placements: delta0 {a['delta0']}  delta1 (CW-eff) {a['delta1']}  "
              f"delta2 (FREE) {a['delta2']}  delta3 (CCW-eff) {a['delta3']}")
        print(f"  IDEAL cw share: dump-free-into-CW {idl['dump_cw_pct']:.1f}%   "
              f"cost-indifferent split {idl['split_cw_pct']:.1f}%")
        print(f"  ACTUAL cw share: {actual_cw:.1f}%  ({a['cw']} cw / {a['ccw']} ccw)")
        print(f"  presses: actual {directional}  ideal-minimum {a['ideal_presses']}  "
              f"=> excess {directional - a['ideal_presses']}")
        print(f"  DIRECTION waste (single-direction pills taken the long way): "
              f"{a['waste']} presses over {a['waste_pills']} pills "
              f"= {100.0*a['waste']/n_all:.1f} per 100 pills")
        print(f"  mixed-direction pills (counted as corrections, not direction error): "
              f"{a['mixed']}")
        print()
    return 0


if __name__ == "__main__":
    sys.exit(main())
