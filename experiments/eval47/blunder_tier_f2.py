"""TIER F2 -- LAST-ACCESS SEAL. Engine-free, oracle-free, attribution by construction.

THE CLASS. For a live virus, an ACCESS ROUTE is a column from which the virus can still
be reached by dropping matching material down. Concretely: some line-of-4 window (vertical
in the virus's column, or horizontal in its row) that contains the virus and is entirely
"its colour or empty", every empty cell of which is REACHABLE -- at or above that column's
landing row, so a drop can actually get there. Holes under a stack are not routes. The
route COUNT is the number of distinct columns that can deliver into any such window.
A tier-F2 blunder is a self-placement that takes some virus's route count from >0 to 0.

WHY ROUTES, NOT COVERS. The narrow detector already in the tree
(`portfolio/endgame-policy/seal_probe.py`) fires when the cell directly above a virus is
non-matching non-virus. That over-fires by construction, and its own REPORT.md measures
how much: 42 of its 126 seals ended with the virus CLEARED WHILE STILL COVERED, because a
cover blocks only the VERTICAL route and leaves every horizontal one intact. Routes model
that directly. The AI-side run of this same definition (`blunder_ai_rows.py`) puts a number
on the difference: cleared-while-sealed falls from 25.0% under the narrow rule to 9.8%
under routes -- routes are a far better predictor of "actually blocked".

SELF-PLACEMENT IS STRUCTURAL, NOT INFERRED. The before-board is read from frames before
the pill spawns; the after-board is that same board plus THIS PILL'S OWN TWO CELLS. Nothing
else can move between them, so an incoming garbage volley cannot produce a flag -- it is
already in both boards, and a route the volley closed is already 0 before. That is what
makes the film review's 13 volley-caused seals structurally unflaggable here rather than
merely filtered, and the mutant gate shows the alternative (diffing two read boards)
manufacturing exactly those flags.

MATCHED-REOPEN GATE. A seal that the player can undo is not the blunder the owner is
after. Before flagging, every blocking cell that itself sits in a completable own-colour
window is removed and the routes are recomputed; if the virus comes back, no flag. This is
the one-step version of "no matched-reopen path", and it is deliberately conservative --
it suppresses flags, never adds them.

SCOPE: THE ENDGAME, because that is what the ledger counted. struktured.md's 21 seal
episodes are "over his REMAINING viruses, m4 close", and the AI-side prior art
(seal_probe.py) gates on `virus_count <= 6` for the same reason. Sealing a virus in the
opening is ordinary play -- there are eighty pills left to dig it out -- and ungated this
tier fires on a quarter of all placements, which measures Dr. Mario, not blunders. The
ungated number is printed too, so the gate's effect is visible rather than assumed.

SPAWN-ROW LOCKS ARE EXCLUDED, reusing battery4_compute.py's control verbatim: a pill the
tracker finalised still in row 0 is a known mistrack (task #95), and it is the single most
destructive input here -- material in row 0 makes its whole column unreachable and seals
half the board at once.

VALIDATION is against the m4 ledger in player_styles/FILM_REVIEW_20260804_SCORECARD.md and
player_styles/struktured.md: a single self-placement sealing three viruses at once, 13
volley-caused seals that must not flag, and most seals re-opening.
"""
import collections
import os
import sys

import blunder_boards as BB
from battery4_compute import is_spawn_row_lock

ROWS, COLS = BB.ROWS, BB.COLS
ENDGAME_VC = 6          # same threshold as portfolio/endgame-policy/seal_probe.py


def landing_row(col, c):
    """Row a dropped half comes to rest in column c: one above the topmost occupied."""
    for r in range(ROWS):
        if col[BB.idx(r, c)]:
            return r - 1
    return ROWS - 1


def windows_through(r, c):
    """Every line-of-4 window containing (r,c): vertical then horizontal."""
    out = []
    for s in range(max(0, r - 3), min(r, ROWS - 4) + 1):
        out.append([(s + k, c) for k in range(4)])
    for s in range(max(0, c - 3), min(c, COLS - 4) + 1):
        out.append([(r, s + k) for k in range(4)])
    return out


def routes(col, r, c, colour, require_reachable=True, colour_blind=False):
    """-> set of columns that can still deliver matching material into (r,c)'s clear."""
    land = [landing_row(col, cc) for cc in range(COLS)]
    got = set()
    for w in windows_through(r, c):
        empties = []
        ok = True
        for (rr, cc) in w:
            v = col[BB.idx(rr, cc)]
            if v == 0:
                if require_reachable and rr > land[cc]:
                    ok = False           # a hole under the stack: unreachable
                    break
                empties.append(cc)
            elif not colour_blind and v != colour:
                ok = False               # wrong colour in the window kills it
                break
        if ok and empties:
            got.update(empties)
    return got


def completes_line(col, r, c, colour):
    """Is (r,c) part of a finished line-of-4 of its own colour? Then it just CLEARED.

    Without this, filling the last empty cell of a virus's own window scores as a seal:
    `routes` reports no route because there is no empty cell left to deliver into, which
    is exactly what winning looks like. Measured on m4 pill 88, where the player's Y-Y
    completes four yellows over the (14,2) yellow virus and the tier called it a seal.
    """
    return any(all(col[BB.idx(rr, cc)] == colour for (rr, cc) in w)
               for w in windows_through(r, c))


def completable(col, r, c):
    """Can the material at (r,c) itself be cleared by matching? (one-step reopen)"""
    colour = col[BB.idx(r, c)]
    return bool(colour) and bool(routes(col, r, c, colour))


def reopen_board(col, r, c, colour):
    """The board with every one-step-clearable blocker removed.

    Blockers are the occupied cells of the wrong colour sitting in (r,c)'s windows, plus
    the material stacked above them in the same columns -- removing a cell that still has
    a tower on it does not reopen anything, so the tower goes with it.
    """
    out = col.copy()
    doomed = set()
    for w in windows_through(r, c):
        for (rr, cc) in w:
            v = col[BB.idx(rr, cc)]
            if v and v != colour and (rr, cc) != (r, c) and completable(col, rr, cc):
                doomed.add((rr, cc))
    for (rr, cc) in list(doomed):
        for up in range(rr):
            if col[BB.idx(up, cc)]:
                doomed.add((up, cc))
    for (rr, cc) in doomed:
        out[BB.idx(rr, cc)] = 0
    return out


def analyse(match, require_reachable=True, colour_blind=False, no_reopen_gate=False,
            diff_read_boards=False, endgame_vc=ENDGAME_VC, keep_spawn_row=False,
            no_clear_guard=False):
    """-> (counters, flagged events) for one match."""
    out = collections.Counter()
    flags, narrow_flags, ungated_flags = [], [], []
    for k, row in enumerate(match.rows):
        before = match.boards[k]
        pill = BB.placed_cells(row)
        if before is None or pill is None:
            out["no_board"] += 1
            continue
        if is_spawn_row_lock(row) and not keep_spawn_row:
            out["excl_spawn_row"] += 1
            continue
        if endgame_vc is not None and len(match.live_viruses(k)) > endgame_vc:
            out["excl_not_endgame"] += 1
            continue
        # CONTROL: the placement must be physically consistent with the board it lands on
        # -- both target cells empty before, and the pill resting on something.
        cells = [((r, c), colour) for (r, c), colour in pill]
        if any(before[BB.idx(r, c)] for (r, c), _q in cells):
            out["control_fail_occupied"] += 1
            continue
        after = before.copy()
        for (r, c), colour in cells:
            after[BB.idx(r, c)] = colour
        if diff_read_boards and k + 1 < len(match.rows):
            nxt = match.boards[k + 1]      # mutant: let every later board change count
            if nxt is not None:
                after = nxt
        out["scored"] += 1

        live = match.live_viruses(k)
        for i, colour in live.items():
            r, c = BB.rc(i)
            if before[i] != colour:
                out["virus_not_read"] += 1
                continue
            r0 = routes(before, r, c, colour, require_reachable, colour_blind)
            if not r0:
                out["already_sealed"] += 1
                continue
            # NARROW, the ledger's own definition (seal_probe.py): the cell directly
            # above goes from open to covered by non-matching non-virus material.
            if r > 0:
                j = BB.idx(r - 1, c)
                cov_b = before[j] and before[j] != colour and j not in match.virus_sites
                cov_a = after[j] and after[j] != colour and j not in match.virus_sites
                if cov_a and not cov_b:
                    out["narrow"] += 1
                    narrow_flags.append(dict(pill=row["pill_id"], virus=(r, c), k=k))

            r1 = routes(after, r, c, colour, require_reachable, colour_blind)
            if r1:
                continue
            if not no_clear_guard and completes_line(after, r, c, colour):
                out["excl_cleared_it"] += 1
                continue
            out["ungated"] += 1
            ungated_flags.append(dict(pill=row["pill_id"], virus=(r, c), k=k,
                                      colour=BB.COLOR_CH[colour], routes_before=sorted(r0)))
            if not no_reopen_gate:
                rb = reopen_board(after, r, c, colour)
                if routes(rb, r, c, colour, require_reachable, colour_blind):
                    out["excl_reopenable"] += 1
                    continue
            out["gated"] += 1
            flags.append(dict(match=match.name, pill=row["pill_id"],
                              lock=int(row["lock_frame"]),
                              t=float(row["spawn_t_abs"]) + (int(row["lock_frame"])
                                                            - int(row["spawn_frame"])) / 60.0,
                              virus=(r, c), colour=BB.COLOR_CH[colour],
                              routes_before=sorted(r0), k=k,
                              cells=[rc_ for rc_, _q in cells],
                              vl=int(row["viruses_left_p1"])))
    return out, flags, narrow_flags, ungated_flags


def later_reopened(match, flags):
    """FP estimate: did the sealed virus regain a route on any later pill?"""
    n = 0
    for f in flags:
        r, c = f["virus"]
        colour = BB.COLOR_ID[f["colour"]]
        for k in range(f["k"] + 1, len(match.rows)):
            b = match.boards[k]
            if b is None or b[BB.idx(r, c)] != colour:
                continue
            if routes(b, r, c, colour):
                n += 1
                break
    return n


def run(matches, **kw):
    agg, allflags = collections.Counter(), []
    for m in matches:
        o, f, _nf, _uf = analyse(m, **kw)
        agg.update(o)
        allflags += f
    return agg, allflags


def main():
    data = BB.load_all()
    flat = [(p, m) for p, ms in data.items() for m in ms]

    print("CONTROL -- placement consistent with the board it lands on (endgame window)")
    for p, m in flat:
        o, _f, _nf, _uf = analyse(m)
        tot = o["scored"] + o["control_fail_occupied"]
        pct = 100 * o["scored"] / tot if tot else float("nan")
        print(f"  {p[:9]:9s}/{m.name:5s} endgame placements {o['scored']:3d} "
              f"(of {len(m.rows):3d}: {o['excl_not_endgame']:3d} pre-endgame, "
              f"{o['excl_spawn_row']:2d} spawn-row locks)  "
              f"target-cell-occupied {o['control_fail_occupied']:2d} => control pass {pct:5.1f}%")

    m4 = [m for p, m in flat if p == "struktured" and m.name == "m4"][0]
    base4, flags4, narrow4, ung4 = analyse(m4)

    allm = [m for _p, m in flat]
    base_eg, _ = run(allm)
    base_ug, _ = run(allm, endgame_vc=None)

    print("\nKILLED-MUTANT GATE -- pooled corpus, against BOTH published numbers")
    print("  (endgame-gated is the headline; the whole-match figure is published too, so a")
    print("   mutant that moves either one is killed. m4's endgame subset alone contains no")
    print("   spawn-row lock and no colour-discriminating case -- scoring there only would")
    print("   score equivalent mutants as passes.)")
    ok = True
    for tag, kw, why in (
        ("routes ignore reachability", dict(require_reachable=False),
         "holes under a stack would count as live routes"),
        ("routes ignore colour", dict(colour_blind=True),
         "any occupied cell would count as matching material"),
        ("matched-reopen gate off", dict(no_reopen_gate=True),
         "seals the player can undo would be flagged"),
        ("attribute by diffing two READ boards", dict(diff_read_boards=True),
         "garbage volleys would be scored as self-placements"),
        ("keep spawn-row locks", dict(keep_spawn_row=True),
         "a row-0 mistrack makes its whole column unreachable"),
        ("no endgame gate (whole match)", dict(endgame_vc=None),
         "opening seals are ordinary play, not blunders"),
        ("clear guard off", dict(no_clear_guard=True),
         "completing a virus's own line-of-4 would score as sealing it"),
    ):
        eg, _ = run(allm, **kw)
        moved = [f"endgame {base_eg['gated']}->{eg['gated']}"] if eg["gated"] != base_eg["gated"] else []
        if kw.get("endgame_vc", ENDGAME_VC) is not None:
            ug, _ = run(allm, endgame_vc=None, **kw)
            if ug["gated"] != base_ug["gated"]:
                moved.append(f"whole-match {base_ug['gated']}->{ug['gated']}")
        hit = bool(moved)
        ok &= hit
        print(f"  {tag:38s} {'KILLED' if hit else '*** SURVIVED'}  "
              f"{'; '.join(moved) if moved else 'no published number moved'}   [{why}]")
    if not ok:
        print("GATE FAILED -- not publishing rates")
        return 1

    print("\nVALIDATION vs the m4 ledger (struktured.md / FILM_REVIEW_20260804_SCORECARD.md)")
    nar_by_pill = collections.Counter(f["pill"] for f in narrow4)
    rt_by_pill = collections.Counter(f["pill"] for f in flags4)
    print(f"  L4 ledger: 8 self-inflicted seals of 21 in the m4 close, the rest volleys.")
    print(f"      NARROW (the ledger's own rule, cover-above): {base4['narrow']:2d} self-seals")
    print(f"      ROUTE  (this tier, last access closed):      {base4['ungated']:2d} ungated, "
          f"{base4['gated']:2d} after the matched-reopen gate")
    print(f"  L1 ledger: ONE placement sealed three viruses at once.")
    ung_by_pill = collections.Counter(f["pill"] for f in ung4)
    for name, byp, src in (("NARROW", nar_by_pill, narrow4),
                           ("ROUTE-ungated", ung_by_pill, ung4),
                           ("ROUTE-flagged", rt_by_pill, flags4)):
        multi = sorted({p for p, n in byp.items() if n >= 2})
        print(f"      {name:6s} multi-virus placements: {len(multi)}"
              f"{'  -> pills ' + ', '.join(multi) if multi else ''}")
        for p in multi:
            hits = [f for f in src if f["pill"] == p]
            k = hits[0]["k"]
            t = (float(m4.rows[k]["spawn_t_abs"])
                 + (int(m4.rows[k]["lock_frame"]) - int(m4.rows[k]["spawn_frame"])) / 60.0)
            print(f"         pill {p:>3s} t={t:7.1f}s cells "
                  f"{[c for c, _q in BB.placed_cells(m4.rows[k])]} sealed "
                  f"{[h['virus'] for h in hits]}")
    print(f"      every ROUTE seal in the m4 close, with its timestamp:")
    for f in sorted(ung4, key=lambda x: x["k"]):
        row = m4.rows[f["k"]]
        t = (float(row["spawn_t_abs"])
             + (int(row["lock_frame"]) - int(row["spawn_frame"])) / 60.0)
        print(f"         pill {f['pill']:>3s} t={t:7.1f}s cells "
              f"{[c for c, _q in BB.placed_cells(row)]} closed the last route "
              f"(col {f['routes_before']}) to virus {f['virus']} {f['colour']}")
    print(f"  L2 volley-caused seals cannot be flagged: STRUCTURAL -- only this pill's own")
    print(f"      two cells separate the two boards. The mutant above shows the alternative")
    print(f"      attribution manufacturing them.")
    reop = later_reopened(m4, flags4)
    print(f"  L3 'nearly every sealed virus shows a later RE-OPENED state':")
    print(f"      of {base4['ungated']} route-killing placements, {base4['excl_reopenable']} were "
          f"suppressed as reopenable by matching; of the {len(flags4)} that survived, "
          f"{reop} regained a route later.")

    print("\n  ROUTE CENSUS, m4 close (what the tape shows at the ledger's t=1348)")
    print(f"      {'pill':>4s} {'t(s)':>8s} {'placed':22s} live viruses -> route columns")
    for k, row in enumerate(m4.rows):
        if not (78 <= int(row["pill_id"]) <= 100):
            continue
        b = m4.boards[k]
        t = (float(row["spawn_t_abs"])
             + (int(row["lock_frame"]) - int(row["spawn_frame"])) / 60.0)
        cellsq = [c for c, _q in (BB.placed_cells(row) or [])]
        bits = []
        for i, colour in sorted(m4.live_viruses(k).items()):
            r, c = BB.rc(i)
            rs = routes(b, r, c, colour) if b[i] == colour else None
            bits.append(f"({r},{c}){BB.COLOR_CH[colour]}="
                        f"{sorted(rs) if rs is not None else 'unread'}")
        print(f"      {row['pill_id']:>4s} {t:8.1f} {str(cellsq):22s} {'  '.join(bits)}")

    print("\nTIER F2 RATES PER 100 PILLS")
    for p, ms in data.items():
        agg, fl = run(ms)
        reopened = sum(later_reopened(m, [f for f in fl if f["match"] == m.name]) for m in ms)
        n = agg["scored"]
        print(f"  {p:12s} n={n:4d} placements   UNGATED {agg['ungated']:3d} = "
              f"{100 * agg['ungated'] / n:5.2f}/100   FLAGGED {agg['gated']:3d} = "
              f"{100 * agg['gated'] / n:5.2f}/100   "
              f"(reopenable-suppressed {agg['excl_reopenable']}, later-reopened {reopened})")

    print("\nFLAGGED CASES")
    for p, ms in data.items():
        _agg, fl = run(ms)
        for f in sorted(fl, key=lambda x: x["t"])[:6]:
            print(f"  {p:12s} {f['match']} pill {f['pill']:>3s} t={f['t']:7.1f}s lock f{f['lock']}  "
                  f"placed {f['cells']} -> sealed virus {f['virus']} {f['colour']}  "
                  f"(routes before: {f['routes_before']}, viruses left {f['vl']})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
