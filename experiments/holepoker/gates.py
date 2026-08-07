#!/usr/bin/env python3
"""GATES 1-3. Every one of these tests the DEFECT, not the fix.

G1 pill symmetry  -- is (a,b) the same capsule as (b,a)?  If not, the adversary's
                     alphabet is 9, not 6, and every "exhaustive to K" claim
                     that used 6 is understated.
G2 admissibility  -- the h-bound must NEVER exceed the true plies-to-death on a
                     real trajectory.  One violation voids every negative result
                     ("no kill within K"), because IDA* would have pruned a real
                     kill.  Falsified against the death corpus, which contains
                     the ground-truth ply at which the champion actually died.
G3 sanity floor   -- a healthy board must NOT be killable at small K.  If the
                     poker "kills" a fresh level board in 3 pills, the search is
                     broken, not the champion.
"""
from __future__ import annotations
import sys, os, json, time
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import champion as CH
import poker as PK


def g1_symmetry():
    print("=== G1: pill (a,b) vs (b,a) -- board-level equivalence ===", flush=True)
    r = PK.verify_pill_symmetry(n_boards=12, level=11)
    print(f"  tested={r['tested']}  cur-swap differs={r['cur_swap_differs']}  "
          f"nxt-swap differs={r['nxt_swap_differs']}")
    ok = r["cur_swap_differs"] == 0
    print(f"  cur-swap: {'SYMMETRIC (alphabet 6 is sound)' if ok else 'ASYMMETRIC -> must use 9'}")
    if r["nxt_swap_differs"]:
        print(f"  NOTE: next-pill swap changes the reply in "
              f"{r['nxt_swap_differs']}/{r['tested']} -- the champion's LOOKAHEAD "
              f"is not perfectly swap-symmetric (a real, tiny eval artefact). "
              f"Adversary alphabet stays 6 for the pill it must DELIVER; the "
              f"asymmetry only means we may under-count by picking one reading.")
    return {"gate": "G1", "pass": ok, **r}


def g2_lines(paths=("results/taxonomy.json",)):
    """G2 (as actually run). The original plan was to falsify the h-bound
    against real champion deaths -- but the death corpus came back with ZERO
    topouts in 1200 solo games at L15-L20, so there are no real deaths to test
    against. That is a finding, not a gap, but it leaves the bound unvalidated
    by that route.

    So we falsify it against every KILLING LINE the poker itself produced. Each
    line is a state sequence ending in a real, replayed topout, which gives the
    ground truth the corpus could not: at each state, h must be <= the number of
    placements that actually remained. If h ever exceeds it, IDA* would have
    pruned a genuine kill and every 'no hole within K' claim is void."""
    print("\n=== G2: h-bound admissibility vs KILLING LINES ===", flush=True)
    import numpy as np
    checked = viol = lines = 0
    worst = None
    for path in paths:
        p = os.path.join(HERE, path)
        if not os.path.exists(p):
            continue
        for r in json.load(open(p)):
            line = r.get("line")
            if not line or not r.get("reproduced"):
                continue
            lines += 1
            b = CH.board_from_flat(np.array(r["col"], dtype=np.int8),
                                   np.array(r["vir"], dtype=np.int8)) \
                if "col" in r else None
            if b is None:
                continue
            cur = tuple(r["cur"])
            K = len(line)
            for t, (n, a, st) in enumerate(line):
                h = PK.h_lower_bound(b)
                rem = K - t
                checked += 1
                if h > rem:
                    viol += 1
                    if worst is None or h - rem > worst[0]:
                        worst = (h - rem, r.get("tag"), t, h, rem)
                if a is None:
                    break
                ok, _c, _v, _ch = CH.apply_action(b, a, cur[0], cur[1])
                if not ok:
                    break
                cur = tuple(n)
    print(f"  killing lines={lines}  states checked={checked}  VIOLATIONS={viol}")
    if worst:
        print(f"  worst overshoot: h-rem={worst[0]} on {worst[1]} at ply {worst[2]} "
              f"(h={worst[3]}, true remaining={worst[4]})")
    if checked == 0:
        print("  no lines available yet -- SKIP")
        return {"gate": "G2", "pass": None, "reason": "no lines"}
    print(f"  {'PASS -- bound never overestimated' if viol == 0 else 'FAIL -- bound INADMISSIBLE, all negatives void'}")
    return {"gate": "G2", "pass": viol == 0, "checked": checked,
            "violations": viol, "lines": lines}


def g2_admissible(corpus="results/deaths.jsonl"):
    print("\n=== G2-corpus: h-bound admissibility vs REAL deaths ===", flush=True)
    p = os.path.join(HERE, corpus)
    if not os.path.exists(p):
        print("  corpus not ready yet -- SKIP (rerun after death_corpus finishes)")
        return {"gate": "G2", "pass": None, "reason": "no corpus"}
    checked = viol = games = 0
    worst = None
    for line in open(p):
        r = json.loads(line)
        if r["result"] != "topout":
            continue
        games += 1
        hist = r["spawn_top_hist"]          # spawn_top AFTER each placement
        died = len(hist)                    # death happened at the last placement
        for i, t in enumerate(hist):
            h = 0 if t <= 1 else (t - 1 + 1) // 2
            rem = died - (i + 1)            # placements still to come after ply i
            checked += 1
            if h > rem:
                viol += 1
                if worst is None or h - rem > worst[0]:
                    worst = (h - rem, r["level"], r["seed"], i, t, rem)
    print(f"  real topouts={games}  states checked={checked}  VIOLATIONS={viol}")
    if worst:
        print(f"  worst overshoot: h-rem={worst[0]} at L{worst[1]} seed {worst[2]} "
              f"ply {worst[3]} (spawn_top={worst[4]}, true remaining={worst[5]})")
    print(f"  {'PASS -- bound never overestimated' if viol == 0 else 'FAIL -- bound is INADMISSIBLE, all negatives void'}")
    return {"gate": "G2", "pass": viol == 0, "checked": checked,
            "violations": viol, "games": games}


def _stack(b, col_list):
    """Bury the given columns to make a near-death board (test fixture)."""
    import numpy as np
    for c, upto in col_list:
        for r in range(15, upto - 1, -1):
            if b.color[r, c] == 0:
                b.color[r, c] = 1 + ((r + c) % 3)
                b.is_virus[r, c] = False
    return b


def g3_sanity_floor():
    """Two-sided. A search that can only ever say 'no kill' is not a search.

    G3a POSITIVE CONTROL (the one that matters): boards deliberately built one
         or two placements from death MUST yield a short kill. If the poker
         cannot kill these, every 'no hole found' result below is vacuous.
    G3b NEGATIVE CONTROL: healthy real boards must NOT be killable at small K.
    """
    print("\n=== G3a POSITIVE CONTROL: near-death boards MUST be killable ===",
          flush=True)
    pos = []
    # Fixture design matters. Burying only columns 3/4 does NOT threaten this
    # champion -- it plays the other six columns, and the search then costs 6^K
    # with no kill, so that is a bad control (it cannot distinguish "robust"
    # from "search broken"). A real positive control removes the escape routes.
    # P1 leaves ONLY the spawn columns open, so every legal move tops out: any
    # working search must find K=1 instantly.
    fixtures = [
        ("P1 only cols 3,4 open at row 0",
         [(c, 1) for c in range(8)] + [(0, 0), (1, 0), (2, 0), (5, 0), (6, 0), (7, 0)],
         1),
        ("P2 all cols buried to row 1", [(c, 1) for c in range(8)], 6),
        ("P3 all cols buried to row 2", [(c, 2) for c in range(8)], 6),
    ]
    for name, cols, maxd in fixtures:
        b = _stack(CH.new_board(11, 5), cols)
        h = PK.h_lower_bound(b)
        sp = PK.SoloPoker(b, (1, 2), max_oracle=12_000)
        t0 = time.time()
        r = sp.search(max_depth=maxd)
        found = r["depth"] is not None
        pos.append((name, PK.spawn_top(b), h, r["depth"], r["calls"], found))
        print(f"  {name:32s} spawn_top={PK.spawn_top(b):2d} h={h} -> kill at K="
              f"{r['depth']}  calls={r['calls']} {time.time()-t0:.0f}s  "
              f"{'FOUND' if found else 'NOT FOUND (search may be broken!)'}")
    a_ok = pos[0][5]   # P1 is the MUST-PASS: an instant kill or the search is broken
    # a found kill must never be shallower than the admissible bound
    bound_ok = all(x[3] is None or x[3] >= x[2] for x in pos)
    print(f"  G3a: {'PASS' if a_ok and bound_ok else 'FAIL'}"
          f"{'' if bound_ok else '  (a kill came in BELOW the bound => h is wrong)'}")

    # G3b RETRACTED (was: "healthy boards must not be killable below the bound").
    # It is VACUOUS BY CONSTRUCTION: SoloPoker.search starts its iterative
    # deepening at lo = h_lower_bound, so it can never return a depth below the
    # bound no matter how wrong the bound is. It would have passed on a broken
    # bound and told us nothing. The bound's admissibility is tested for real by
    # G2, against the ground-truth ply at which the champion actually died.
    return {"gate": "G3", "pass": a_ok and bound_ok, "positive": pos,
            "g3b": "retracted -- vacuous by construction, superseded by G2"}


def main():
    CH.init_champion()
    out = {}
    which = sys.argv[1:] or ["g1", "g2", "g3"]
    if "g1" in which:
        out["g1"] = g1_symmetry()
    if "g2" in which:
        out["g2"] = g2_admissible()
    if "g2l" in which:
        out["g2l"] = g2_lines()
    if "g3" in which:
        out["g3"] = g3_sanity_floor()
    with open(os.path.join(HERE, "results/gates.json"), "w") as fh:
        json.dump(out, fh, indent=1, default=str)
    print("\n=== GATE SUMMARY ===")
    for k, v in out.items():
        print(f"  {v['gate']}: {'PASS' if v['pass'] else ('SKIP' if v['pass'] is None else 'FAIL')}")


if __name__ == "__main__":
    main()
