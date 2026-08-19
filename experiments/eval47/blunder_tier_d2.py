"""TIER D2 -- HARD BURIAL.  *** NOT QUOTABLE -- SEE THE LIMITATION BLOCK BELOW. ***

THE CLASS. A live virus at (r,c) is HARD-BURIED when no vertical line-of-4 through it in
its own column is still viable -- every such window contains material of the wrong colour,
or an empty cell that no drop can reach. Colour-matching from above cannot dig it out; only
clearing the blocking material first can. A tier-D2 event is a placement that adds
MISMATCHED material into column c above (r,c) and leaves the virus in that state.

*** THE LIMITATION, FIRST, BECAUSE IT GOVERNS EVERY NUMBER IN THIS FILE ***
The tier's own false-positive estimate is 77.5% (struktured) and 92.1% (dr. lulu): that
share of the viruses it calls hard-buried had their vertical route BACK on a later board,
i.e. the player dug them out and the burial was not fatal. The rate is therefore NOT a
blunder rate and must not be quoted as one. It is published only as a censused count with
its FP estimate attached, and every consumer -- this script's stdout, results/blunder_
battery.json (`quotable: false`) and the notebook table -- carries the marker.

The owner predicted this tier would be the false-positive problem. It is.

WHAT WAS TRIED TO RESCUE IT, AND WHAT IT ACHIEVED. Three board-state tightenings, each
measured and each printed by this script under TIGHTENING ATTEMPTED:
  (1) MATCHED-REOPEN GATE, ported from tier F2 (`reopen_board` below). It suppresses 37 of
      259 ungated placements -- and moves the FP estimate 77.5% -> 72.8% and 92.1% -> 97.4%.
      One player's precision gets WORSE. It also *raises* the headline, because the same
      predicate feeds the forced-position enumeration: under a stricter burial test more
      alternatives look clean, so fewer placements are excused as forced (116 -> 68).
  (2) LAST-STRAW REQUIREMENT: flag only the placement that takes the virus from vertically
      open to vertically closed, instead of every later top-up. Volume falls 3.4x
      (130 -> 32 pooled) and the FP estimate does not move at all: 78.4% and 100.0%.
  (3) BOTH TOGETHER: 130 -> 21 pooled, FP 76.2% and 100.0%.
No candidate reaches a defensible precision, and no stratifier does either -- burial depth,
virus row, column-top fill and the endgame bins were all swept, and the only cell that gets
under 40% is struktured's depth>=7 (n=6, 33.3%) where dr. lulu sits at 87.5% (n=8). (The
column-top-fill split is degenerate: no flagged burial has its column filled to row 0.)

WHY NO BOARD-STATE GATE CAN RESCUE IT, structurally. In dr. lulu's m3 the board instrument
maps 39 virus sites and ALL 39 leave the board: she full-cleared the level. Every virus
this tier flags in a level the player goes on to clear is a false positive by construction,
whatever the gate. Hard vertical burial is a normal, recoverable state in Dr. Mario -- the
blocking material gets cleared and the route comes back -- so "no vertical route right now"
is a description of ordinary play, not of a mistake. Tier F2 asks the strictly harder
question (ALL routes, vertical and horizontal, and only the transition to zero) and is the
tier to quote.

THE TWO QUANTITIES ARE STRICTLY SEPARATE, AND MUST STAY THAT WAY. `reopen_board` is a
BOARD-STATE test evaluated on the board as it stands the instant the pill locks; it never
reads a later board. `later_reopened` is the future-looking FP estimate. Gating on
later-reopened would be circular -- it is the very quantity the gate would then be reported
as having improved -- so the gate is not allowed to see it, and the FP estimate is computed
independently of every gate in this file.

THE THREE ORIGINAL GATES, all from the owner's brief:
  MATCHED COVERS ARE EXCLUDED. Adding the virus's own colour above it is progress toward a
  vertical clear, not burial, and the mutant gate shows what including them would do.
  FORCED POSITIONS ARE EXCLUDED. If every legal alternative placement of the same capsule
  also hard-buries some live virus, the player had no clean square and the event is not a
  choice. Alternatives are enumerated with this file's own drop model.
  ENDGAME PROXIMITY IS REPORTED, NOT BAKED IN. Rates are split by live virus count using
  analysis/endgame.md's own bins, so a burial with 30 viruses left and one with 3 are never
  averaged into a single number.

WHY THIS IS NOT TIER F2. F2 asks whether the LAST access route closed, counting horizontal
routes as fully as vertical ones. D2 asks a narrower and more common question -- is the
player stacking wrong-colour material on top of a virus he can no longer dig vertically --
and it fires on the accumulation, not just on the final straw. The two are reported
separately for that reason and must not be pooled. The measurement above is what that
narrowness costs: 92.2% of D2's flagged burials (238 of 258; 93.4% struktured, 89.5% dr.
lulu) have no horizontal route either, so the difference between the tiers is not the
horizontal escape -- it is that D2 fires on states F2 already counts as sealed, and that
most such states are dug back out anyway.

THE DROP MODEL IS CONTROLLED, NOT ASSUMED. Enumerating alternatives needs a landing rule,
and a wrong one would invent options the player never had. So the same rule is first run on
the placement the player ACTUALLY made and compared against the tracker's recorded
final_cells. That is the same control the film review's reconstruction reports as
`resting_ok` (297/330 = 90.0%, the residue being mostly the unmodelled tuck mechanic), and
pills that fail it are excluded and counted out loud.
"""
import collections
import sys

import blunder_boards as BB
from battery4_compute import is_spawn_row_lock
from blunder_tier_f2 import completable, landing_row, windows_through

ROWS, COLS = BB.ROWS, BB.COLS
BINS = ((">20", 21, 99), ("20-11", 11, 20), ("10-6", 6, 10), ("<=5", 0, 5))

NOT_QUOTABLE = ("hard vertical burial is recoverable: 77.5% / 92.1% of flagged burials "
                "were dug back out. Count only; not a blunder rate.")


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


def reopen_board(col, r, c, colour):
    """MATCHED-REOPEN GATE, tier F2's `reopen_board` ported to D2's vertical question.

    The board with every one-step-clearable blocker ABOVE (r,c) in its own column removed,
    plus the material stacked above each -- removing a cell that still has a tower on it
    reopens nothing, so the tower goes with it. `completable` is F2's, unchanged: a blocker
    counts as removable when it itself sits in a line-of-4 window (vertical OR horizontal)
    that is entirely its own colour or reachable-empty.

    Only blockers ABOVE the virus are considered, and that costs nothing: viruses do not
    fall, so while (r,c) is occupied every empty cell below it is under the stack and fails
    `vertical_open`'s reachability test regardless. Clearing below can never reopen the
    column.

    THIS IS A BOARD-STATE TEST. It reads the board as it stands the instant the pill locks
    and nothing else. It deliberately does NOT consult `later_reopened` -- that is the
    tier's future-looking FP estimate, and gating on it would be circular, since the gate
    would then be scored against the very quantity it was given.
    """
    out = col.copy()
    doomed = set()
    for w in windows_through(r, c):
        if w[0][1] != w[1][1]:
            continue                       # vertical windows only: this tier's question
        for (rr, cc) in w:
            if rr >= r:
                continue
            v = col[BB.idx(rr, cc)]
            if v and v != colour and completable(col, rr, cc):
                doomed.add((rr, cc))
    for (rr, cc) in list(doomed):
        for up in range(rr):
            if col[BB.idx(up, cc)]:
                doomed.add((up, cc))
    for (rr, cc) in doomed:
        out[BB.idx(rr, cc)] = 0
    return out


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


def buries(col, cells, live, allow_matched=False, reopen_gate=False, last_straw=False):
    """-> set of virus cells hard-buried by dropping `cells` onto `col`.

    `reopen_gate` and `last_straw` are the two tightenings measured under TIGHTENING
    ATTEMPTED. Both are applied here rather than at the call site so that the alternative
    placements the forced-position gate enumerates are judged by the SAME predicate as the
    placement the player actually made.
    """
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
        if last_straw and not vertical_open(col, r, c, vcol):
            continue                       # already closed before this pill: not its doing
        if vertical_open(after, r, c, vcol):
            continue
        if reopen_gate and vertical_open(reopen_board(after, r, c, vcol), r, c, vcol):
            continue                       # the player can undo it by matching: no flag
        hit.add(i)
    return hit


def analyse(match, allow_matched=False, no_forced_gate=False, no_control=False,
            reopen_gate=False, last_straw=False):
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
        # `ungated` keeps its original meaning -- no reopen gate, no last-straw rule -- so
        # the variants below stay comparable against the published headline.
        raw = buries(col, pill, live, allow_matched)
        if raw:
            out["ungated"] += 1
        hit = buries(col, pill, live, allow_matched, reopen_gate, last_straw)
        if not hit:
            if raw:
                out["excl_suppressed"] += 1
            continue
        if not no_forced_gate:
            clean = [cells for _v, _c, cells in cand
                     if not buries(col, cells, live, allow_matched, reopen_gate, last_straw)]
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
    """THE FP ESTIMATE. Future-looking by design and computed independently of every gate
    above: did the buried virus's vertical route come back on a later board?"""
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


def later_cleared(match, events):
    """The stronger survivability check: did the buried virus LEAVE THE BOARD later?

    A virus dug out horizontally never shows a reopened VERTICAL route, so `later_reopened`
    scores it as a true positive. This counts those too, using the board instrument's own
    clear times, and is the reason the FP estimate above is a floor rather than a bound.
    """
    return sum(1 for e in events
               if match.cleared_at.get(BB.idx(*e["virus"]), len(match.rows)) < len(match.rows))


def run(matches, **kw):
    agg, evs = collections.Counter(), []
    for m in matches:
        o, e = analyse(m, **kw)
        agg.update(o)
        evs += e
    return agg, evs


def survival(matches, evs):
    """-> (n_buried, later_reopened, later_cleared) over one player's matches."""
    reop = sum(later_reopened(m, [e for e in evs if e["match"] == m.name]) for m in matches)
    clr = sum(later_cleared(m, [e for e in evs if e["match"] == m.name]) for m in matches)
    return len(evs), reop, clr


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
    reop_v, _ = run(allm, reopen_gate=True)          # published under TIGHTENING ATTEMPTED
    straw_v, _ = run(allm, last_straw=True)          # published under TIGHTENING ATTEMPTED

    print("\nKILLED-MUTANT GATE")
    print("  every published figure has a mutant: the headline (gated/ungated) and both")
    print("  tightening figures. A gate that fired on nothing would be an EQUIVALENT mutant")
    print(f"  and would prove nothing -- the reopen gate suppresses {reop_v['excl_suppressed']}"
          f" of {base['ungated']} ungated placements")
    print(f"  and the last-straw rule {straw_v['excl_suppressed']}, so neither is equivalent.")
    ok = True
    for tag, kw, ref, key, why in (
        ("matched covers counted as burial", dict(allow_matched=True), base, "gated",
         "adding the virus's own colour is progress, not burial"),
        ("forced-position gate off", dict(no_forced_gate=True), base, "gated",
         "a capsule with no clean square is not a choice"),
        ("drop-model control off", dict(no_control=True), base, "gated",
         "pills whose real landing the model cannot reproduce would be scored anyway"),
        ("matched-reopen gate off", dict(reopen_gate=False), reop_v, "reopen-gated",
         "burials the player can undo with one matched clear would be flagged"),
        ("last-straw requirement off", dict(last_straw=False), straw_v, "last-straw",
         "top-ups of an already-closed column would be attributed to this pill"),
    ):
        mut, _me = run(allm, **kw)
        hit = mut["gated"] != ref["gated"] or mut["ungated"] != ref["ungated"]
        ok &= hit
        print(f"  {tag:36s} {'KILLED' if hit else '*** SURVIVED'}  "
              f"{key} {ref['gated']}->{mut['gated']}, ungated {ref['ungated']}->{mut['ungated']}"
              f"   [{why}]")
    if not ok:
        print("GATE FAILED -- not publishing rates")
        return 1

    print("\n" + "*" * 78)
    print("*** TIER D2 IS NOT QUOTABLE AS A BLUNDER RATE ***")
    print(f"    {NOT_QUOTABLE}")
    print("    Every figure below is printed with its own FP estimate attached. Quote tier")
    print("    F2 for sealing; this tier is a censused count of a recoverable state.")
    print("*" * 78)

    print("\nTIER D2 -- hard burials per 100 placements, BY ENDGAME PROXIMITY [NOT QUOTABLE]")
    print(f"  {'player':12s} {'n':>5s} {'ungated':>8s} {'forced':>7s} {'events':>7s} "
          f"{'/100':>6s}   " + "  ".join(f"{b:>7s}" for b, _lo, _hi in BINS)
          + "   later-reopened = FP est")
    for p, ms in data.items():
        agg, evs = run(ms)
        n = agg["scored"]
        nb, reop, _clr = survival(ms, evs)
        bins = "  ".join(f"{agg['bin_' + b]:>7d}" for b, _lo, _hi in BINS)
        print(f"  {p:12s} {n:>5d} {agg['ungated']:>8d} {agg['excl_forced']:>7d} "
              f"{agg['gated']:>7d} {100 * agg['gated'] / n:>6.2f}   {bins}   "
              f"{reop}/{nb} = {100 * reop / nb if nb else 0:.1f}%  NOT QUOTABLE")
    print("  bins are live virus counts (analysis/endgame.md's own bins); 'events' counts")
    print("  PLACEMENTS, the per-bin columns and later-reopened count BURIED VIRUSES, so a")
    print("  placement burying two viruses contributes one event and two virus rows.")
    print("  later-reopened = the virus's vertical route came back on a later board. That is")
    print("  this tier's false-positive estimate: those burials were survivable.")

    print("\nTIGHTENING ATTEMPTED -- what each board-state gate achieved (FP is the target)")
    print(f"  {'variant':28s} {'player':12s} {'events':>6s} {'/100':>6s} {'buried':>7s} "
          f"{'reopen':>7s} {'FP est':>7s} {'cleared':>8s}")
    for tag, kw in (("baseline (published)", {}),
                    ("+ matched-reopen gate", dict(reopen_gate=True)),
                    ("+ last-straw only", dict(last_straw=True)),
                    ("+ both", dict(reopen_gate=True, last_straw=True))):
        for p, ms in data.items():
            agg, evs = run(ms, **kw)
            n = agg["scored"]
            nb, reop, clr = survival(ms, evs)
            print(f"  {tag:28s} {p:12s} {agg['gated']:>6d} {100 * agg['gated'] / n:>6.2f} "
                  f"{nb:>7d} {reop:>7d} {100 * reop / nb if nb else 0:>6.1f}% "
                  f"{100 * clr / nb if nb else 0:>7.1f}%")
    print("  'cleared' = the buried virus left the board later, by ANY route. It is the")
    print("  stronger survivability check and it is worse than the FP estimate everywhere,")
    print("  which is why the FP estimate is a FLOOR. No variant reaches a defensible")
    print("  precision, and the reopen gate makes dr. lulu's estimate worse, not better.")

    print("\nWHY NO BOARD-STATE GATE CAN RESCUE IT -- virus sites that leave the board")
    for p, ms in data.items():
        for m in ms:
            ns = len(m.virus_sites)
            cl = sum(1 for i in m.virus_sites if m.cleared_at[i] < len(m.rows))
            print(f"  {p[:9]:9s}/{m.name:5s} mapped sites {ns:3d}  cleared later {cl:3d} "
                  f"({100 * cl / ns:5.1f}%)")
    print("  dr. lulu full-cleared m3: 39 of 39 sites go. Every virus this tier flags in a")
    print("  level the player goes on to clear is a false positive BY CONSTRUCTION, whatever")
    print("  the gate -- which is why tightening moves volume and not precision.")

    print("\nBURIAL EVENTS NEAREST THE END (lowest virus count first) [NOT QUOTABLE]")
    for p, ms in data.items():
        _agg, evs = run(ms)
        for e in sorted(evs, key=lambda x: (x["vc"], x["t"]))[:5]:
            print(f"  {p:12s} {e['match']} pill {e['pill']:>3s} t={e['t']:7.1f}s  "
                  f"placed {e['cells']} over virus {e['virus']} {e['colour']}  "
                  f"({e['vc']} viruses left, bin {e['bin']})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
