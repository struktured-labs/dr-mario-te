"""TIER D2 -- HARD BURIAL. Mismatched material dropped over a virus that is already
unreachable from above, when the player had somewhere else to put it.

THE CLASS. A live virus at (r,c) is HARD-BURIED when no vertical line-of-4 through it in
its own column is still viable -- every such window contains material of the wrong colour,
or an empty cell that no drop can reach. Colour-matching from above cannot dig it out; only
clearing the blocking material first can. A tier-D2 event is a placement that adds
MISMATCHED material into column c above (r,c) and leaves the virus in that state.

WHY THIS IS NOT TIER F2. F2 asks whether the LAST access route closed, counting horizontal
routes as fully as vertical ones. D2 asks a narrower and more common question -- is the
player stacking wrong-colour material on top of a virus he can no longer dig vertically --
and it fires on the accumulation, not just on the final straw. The two are reported
separately for that reason and must not be pooled.

THE THREE GATES, all from the owner's brief:
  MATCHED COVERS ARE EXCLUDED. Adding the virus's own colour above it is progress toward a
  vertical clear, not burial, and the mutant gate shows what including them would do.
  FORCED POSITIONS ARE EXCLUDED. If every legal alternative placement of the same capsule
  also hard-buries some live virus, the player had no clean square and the event is not a
  choice. Alternatives are enumerated with this file's own drop model.
  ENDGAME PROXIMITY IS REPORTED, NOT BAKED IN. Rates are split by live virus count using
  analysis/endgame.md's own bins, so a burial with 30 viruses left and one with 3 are never
  averaged into a single number.

THE DROP MODEL IS CONTROLLED, NOT ASSUMED. Enumerating alternatives needs a landing rule,
and a wrong one would invent options the player never had. So the same rule is first run on
the placement the player ACTUALLY made and compared against the tracker's recorded
final_cells. That is the same control the film review's reconstruction reports as
`resting_ok` (297/330 = 90.0%, the residue being mostly the unmodelled tuck mechanic), and
pills that fail it are excluded and counted out loud.

FALSE-POSITIVE ESTIMATE. Every burial is followed forward: if the virus's vertical route
returns on any later pill's board, the player dug it out and the event was survivable. That
later-reopened rate is the tier's own FP estimate, reported next to the raw count.
"""
import collections
import sys

import blunder_boards as BB
from battery4_compute import is_spawn_row_lock
from blunder_tier_f2 import landing_row, windows_through

ROWS, COLS = BB.ROWS, BB.COLS
BINS = ((">20", 21, 99), ("20-11", 11, 20), ("10-6", 6, 10), ("<=5", 0, 5))


def bin_of(vc):
    for name, lo, hi in BINS:
        if lo <= vc <= hi:
            return name
    return ">20"


def vertical_open(col, r, c, colour):
    """Can (r,c) still be cleared by matching DOWN its own column?"""
    land = landing_row(col, c)
    for w in windows_through(r, c):
        if w[0][1] != w[1][1]:
            continue                       # horizontal window, not this question
        ok = True
        for (rr, cc) in w:
            v = col[BB.idx(rr, cc)]
            if v == 0:
                if rr > land:
                    ok = False
                    break
            elif v != colour:
                ok = False
                break
        if ok:
            return True
    return False


def drops(col, ca, cb):
    """Every legal placement of a capsule -> (variant, column, [((r,c), colour), ...]).

    variant 0/1 = horizontal a-left / b-left, 2/3 = vertical a-top / b-top, matching the
    engine's convention. Tucks are not modelled: this is the plain drop rule, and the
    control measures exactly how often that costs us the real landing.
    """
    land = [landing_row(col, c) for c in range(COLS)]
    out = []
    for c in range(COLS - 1):
        r = min(land[c], land[c + 1])
        if r < 0:
            continue
        out.append((0, c, [((r, c), ca), ((r, c + 1), cb)]))
        out.append((1, c, [((r, c), cb), ((r, c + 1), ca)]))
    for c in range(COLS):
        if land[c] < 1:
            continue
        out.append((2, c, [((land[c] - 1, c), ca), ((land[c], c), cb)]))
        out.append((3, c, [((land[c] - 1, c), cb), ((land[c], c), ca)]))
    return out


def buries(col, cells, live, allow_matched=False):
    """-> set of virus cells hard-buried by dropping `cells` onto `col`."""
    after = col.copy()
    for (r, c), colour in cells:
        after[BB.idx(r, c)] = colour
    hit = set()
    for i, vcol in live.items():
        r, c = BB.rc(i)
        if col[i] != vcol:
            continue                       # virus colour not read on this board
        added = [(rr, q) for (rr, cc), q in cells if cc == c and rr < r]
        if not added:
            continue
        if not allow_matched and all(q == vcol for _rr, q in added):
            continue                       # a matched cover is progress, not burial
        if not vertical_open(after, r, c, vcol):
            hit.add(i)
    return hit


def analyse(match, allow_matched=False, no_forced_gate=False, no_control=False):
    out = collections.Counter()
    events = []
    for k, row in enumerate(match.rows):
        col = match.boards[k]
        pill = BB.placed_cells(row)
        if col is None or pill is None or is_spawn_row_lock(row):
            out["excluded"] += 1
            continue
        ca, cb = pill[0][1], pill[1][1]
        cand = drops(col, ca, cb)
        actual = sorted((rc_, q) for rc_, q in pill)
        # CONTROL: this file's drop model must reproduce the landing the tracker recorded
        if not no_control and not any(sorted(cells) == actual for _v, _c, cells in cand):
            out["control_fail_landing"] += 1
            continue
        out["scored"] += 1

        live = match.live_viruses(k)
        hit = buries(col, pill, live, allow_matched)
        if not hit:
            continue
        out["ungated"] += 1
        if not no_forced_gate:
            clean = [cells for _v, _c, cells in cand
                     if not buries(col, cells, live, allow_matched)]
            if not clean:
                out["excl_forced"] += 1
                continue
        out["gated"] += 1
        b = bin_of(len(live))
        out["bin_" + b] += 1
        for i in hit:
            events.append(dict(match=match.name, pill=row["pill_id"], k=k,
                               virus=BB.rc(i), colour=BB.COLOR_CH[live[i]],
                               vc=len(live), bin=b,
                               cells=[rc_ for rc_, _q in pill],
                               t=float(row["spawn_t_abs"])
                               + (int(row["lock_frame"]) - int(row["spawn_frame"])) / 60.0))
    return out, events


def later_reopened(match, events):
    n = 0
    for e in events:
        r, c = e["virus"]
        colour = BB.COLOR_ID[e["colour"]]
        for k in range(e["k"] + 1, len(match.rows)):
            b = match.boards[k]
            if b is not None and b[BB.idx(r, c)] == colour and vertical_open(b, r, c, colour):
                n += 1
                break
    return n


def run(matches, **kw):
    agg, evs = collections.Counter(), []
    for m in matches:
        o, e = analyse(m, **kw)
        agg.update(o)
        evs += e
    return agg, evs


def main():
    data = BB.load_all()
    flat = [(p, m) for p, ms in data.items() for m in ms]

    print("CONTROL -- this file's drop model vs the tracker's recorded landing")
    print("  (prior art for the same check: reconstruct2.py resting_ok = 297/330 = 90.0%)")
    tot_s = tot_f = 0
    for p, m in flat:
        o, _e = analyse(m)
        n = o["scored"] + o["control_fail_landing"]
        tot_s += o["scored"]
        tot_f += o["control_fail_landing"]
        print(f"  {p[:9]:9s}/{m.name:5s} scored {o['scored']:4d}/{n:4d} "
              f"({100 * o['scored'] / n:5.1f}%)  landing-mismatch {o['control_fail_landing']:3d} "
              f"(unmodelled tucks)  other exclusions {o['excluded']:2d}")
    print(f"  POOLED {tot_s}/{tot_s + tot_f} = {100 * tot_s / (tot_s + tot_f):.1f}%")

    allm = [m for _p, m in flat]
    base, base_ev = run(allm)

    print("\nKILLED-MUTANT GATE")
    ok = True
    for tag, kw, why in (
        ("matched covers counted as burial", dict(allow_matched=True),
         "adding the virus's own colour is progress, not burial"),
        ("forced-position gate off", dict(no_forced_gate=True),
         "a capsule with no clean square is not a choice"),
        ("drop-model control off", dict(no_control=True),
         "pills whose real landing the model cannot reproduce would be scored anyway"),
    ):
        mut, _me = run(allm, **kw)
        hit = mut["gated"] != base["gated"] or mut["ungated"] != base["ungated"]
        ok &= hit
        print(f"  {tag:36s} {'KILLED' if hit else '*** SURVIVED'}  "
              f"gated {base['gated']}->{mut['gated']}, ungated {base['ungated']}->{mut['ungated']}"
              f"   [{why}]")
    if not ok:
        print("GATE FAILED -- not publishing rates")
        return 1

    print("\nTIER D2 -- hard burials per 100 placements, BY ENDGAME PROXIMITY")
    print(f"  {'player':12s} {'n':>5s} {'ungated':>8s} {'forced':>7s} {'events':>7s} "
          f"{'/100':>6s}   " + "  ".join(f"{b:>7s}" for b, _lo, _hi in BINS)
          + "   later-reopened")
    for p, ms in data.items():
        agg, evs = run(ms)
        n = agg["scored"]
        reop = sum(later_reopened(m, [e for e in evs if e["match"] == m.name]) for m in ms)
        bins = "  ".join(f"{agg['bin_' + b]:>7d}" for b, _lo, _hi in BINS)
        print(f"  {p:12s} {n:>5d} {agg['ungated']:>8d} {agg['excl_forced']:>7d} "
              f"{agg['gated']:>7d} {100 * agg['gated'] / n:>6.2f}   {bins}   "
              f"{reop}/{len(evs)} = {100 * reop / len(evs) if evs else 0:.1f}%")
    print("  bins are live virus counts (analysis/endgame.md's own bins); 'events' counts")
    print("  PLACEMENTS, the per-bin columns and later-reopened count BURIED VIRUSES, so a")
    print("  placement burying two viruses contributes one event and two virus rows.")
    print("  later-reopened = the virus's vertical route came back on a later board. That is")
    print("  this tier's false-positive estimate: those burials were survivable.")

    print("\nBURIAL EVENTS NEAREST THE END (lowest virus count first)")
    for p, ms in data.items():
        _agg, evs = run(ms)
        for e in sorted(evs, key=lambda x: (x["vc"], x["t"]))[:5]:
            print(f"  {p:12s} {e['match']} pill {e['pill']:>3s} t={e['t']:7.1f}s  "
                  f"placed {e['cells']} over virus {e['virus']} {e['colour']}  "
                  f"({e['vc']} viruses left, bin {e['bin']})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
