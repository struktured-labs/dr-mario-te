#!/usr/bin/env python3
"""THE HOLE TAXONOMY.

Two-stage, because the two questions have very different costs:

  STAGE 1 (beam, cheap)  -- does a killing pill sequence exist from this real
        position AT ALL, and how long is it?  Beam search over the adversary's
        pill choices costs width*6*depth oracle calls and reaches depth 25+,
        where exhaustive IDA* costs 6^K and dies at K=6.  The beam's K is an
        UPPER bound on the hole depth (not minimal) -- stated as such.

  STAGE 2 (escape depth, cheap)  -- given a killing line, how many plies ahead
        would the champion have had to see to dodge it?  That is E, and E is
        the number that prices the depth-vs-eval argument: E=2 means depth 4
        fixes it; E=8 means no feasible search does and the eval must encode
        the pattern instead.

Exact minimality (IDA*) is run separately on the shortest beam hits only --
that is where minimality actually matters and where it is affordable.

EVERY REPORTED HOLE IS REPLAYED from its saved board before it is counted
(replay_check), because a hole you cannot reproduce is an anecdote.
"""
from __future__ import annotations
import sys, os, json, argparse, time
from collections import Counter
from concurrent.futures import ProcessPoolExecutor, as_completed

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)


def _init():
    import champion as CH
    CH.init_champion()


def _board_of(spec):
    import numpy as np
    import champion as CH
    return CH.board_from_flat(np.array(spec["col"], dtype=np.int8),
                              np.array(spec["vir"], dtype=np.int8),
                              np.array(spec["link"], dtype=np.int8))


def replay_check(spec, line):
    """Replay the killing line from the saved board and confirm the SAME death.
    A hole that does not reproduce is not reported."""
    import champion as CH
    b = _board_of(spec)
    cur = tuple(spec["cur"])
    for (n, a, st) in line:
        col, vir = CH.board_to_flat(b)
        a2 = CH.champion_move(col, vir, cur[0], cur[1], n[0], n[1])
        if a2 != a:
            return False, "champion replied differently on replay"
        if a2 is None:
            return (st == "nomove"), "nomove"
        ok, _c, _v, _ch = CH.apply_action(b, a2, cur[0], cur[1])
        if not ok:
            return (st == "nomove"), "illegal"
        cur = tuple(n)
    return b.spawn_blocked(), ("topout" if b.spawn_blocked() else "survived")


def _job(spec):
    import champion as CH
    import poker as PK
    import margin as MG
    CH.init_champion()
    b = _board_of(spec)
    cur = tuple(spec["cur"])
    t0 = time.time()
    out = {"tag": spec.get("tag", f"L{spec['level']}s{spec['seed']}p{spec['ply']}"),
           "level": spec["level"], "seed": spec["seed"], "ply": spec["ply"],
           "spawn_top": PK.spawn_top(b), "h": PK.h_lower_bound(b),
           "viruses": int(b.virus_count())}
    r = PK.beam_kill(b, cur, width=spec.get("width", 24),
                     max_depth=spec.get("max_depth", 22))
    out["K_beam"] = r["depth"]
    out["beam_calls"] = r["calls"]
    if r["depth"] is None:
        out["reason"] = r.get("reason")
        out["secs"] = round(time.time() - t0, 1)
        return out
    ok, why = replay_check(spec, r["line"])
    out["reproduced"] = bool(ok)
    out["replay_note"] = why
    if not ok:
        out["secs"] = round(time.time() - t0, 1)
        return out
    esc = MG.escape_depth(b, cur, r["line"], max_E=8)
    out.update(E=esc["E"], escape_ply=esc["ply"], avoidable=esc["avoidable"],
               how=esc["how"],
               story=MG.describe(b, cur, r["line"], r["depth"], esc),
               line=[[list(n), int(a) if a is not None else None, st]
                     for (n, a, st) in r["line"]],
               # the board travels WITH the hole so it is independently
               # replayable (G2 admissibility, fixtures, RTL validation)
               col=spec["col"], vir=spec["vir"], cur=list(cur))
    out["secs"] = round(time.time() - t0, 1)
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--positions", type=str, default="results/positions.json")
    ap.add_argument("--workers", type=int, default=6)
    ap.add_argument("--width", type=int, default=24)
    ap.add_argument("--max-depth", type=int, default=22)
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--out", type=str, default="results/taxonomy.json")
    a = ap.parse_args()

    specs = json.load(open(os.path.join(HERE, a.positions)))
    if a.limit:
        specs = specs[:a.limit]
    for s in specs:
        s["width"] = a.width
        s["max_depth"] = a.max_depth
    print(f"=== TAXONOMY: {len(specs)} real positions, beam width={a.width}, "
          f"max_depth={a.max_depth}, workers={a.workers} ===", flush=True)

    rows = []
    t0 = time.time()
    outp = os.path.join(HERE, a.out)
    with ProcessPoolExecutor(max_workers=a.workers, initializer=_init) as ex:
        futs = [ex.submit(_job, s) for s in specs]
        for i, f in enumerate(as_completed(futs)):
            r = f.result()
            rows.append(r)
            print(f"  [{i+1}/{len(specs)}] {r['tag']:20s} st={r['spawn_top']:2d} "
                  f"v={r['viruses']:2d} K={r['K_beam']} E={r.get('E')} "
                  f"repro={r.get('reproduced')} {r['secs']}s", flush=True)
            if (i + 1) % 10 == 0:
                with open(outp, "w") as fh:
                    json.dump(rows, fh, indent=1, default=str)
    with open(outp, "w") as fh:
        json.dump(rows, fh, indent=1, default=str)

    # ------------------------------------------------------------- aggregate
    print(f"\n=== SUMMARY ({time.time()-t0:.0f}s) ===")
    killed = [r for r in rows if r.get("K_beam") is not None and r.get("reproduced")]
    print(f"positions: {len(rows)}   killable within beam reach: {len(killed)} "
          f"({len(killed)/max(1,len(rows)):.1%})")
    kh = Counter(r["K_beam"] for r in killed)
    print("\nKILL DEPTH K (upper bound, beam):")
    for k in sorted(kh):
        print(f"  K={k:2d}: {kh[k]:3d}")
    eh = Counter((r.get("E") if r.get("E") is not None else ">8") for r in killed)
    print("\nESCAPE DEPTH E (plies the champion would need to see):")
    for k in sorted(eh, key=lambda x: (99 if isinstance(x, str) else x)):
        frac = eh[k] / max(1, len(killed))
        print(f"  E={str(k):>2s}: {eh[k]:3d}  ({frac:.1%})")
    fixable = sum(v for k, v in eh.items() if isinstance(k, int) and k <= 1)
    print(f"\n  E<=1 (already visible to depth-3, an EVAL error not a depth error): "
          f"{fixable}  ({fixable/max(1,len(killed)):.1%})")
    for lim in (2, 3, 5):
        n = sum(v for k, v in eh.items() if isinstance(k, int) and k <= lim)
        print(f"  E<={lim} (a depth-{3+lim} search would dodge it): {n} "
              f"({n/max(1,len(killed)):.1%})")
    print(f"\nwrote {a.out}")


if __name__ == "__main__":
    main()
