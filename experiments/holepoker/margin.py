#!/usr/bin/env python3
"""SURVIVAL MARGIN + ESCAPE DEPTH -- the two numbers the hole taxonomy is built on.

For a position (board, cur):

  KILL DEPTH K   = the length of the SHORTEST pill sequence that forces the
                   champion to top out (IDA*, exact when it terminates).
                   K is the position's survival margin in pills. Large K = the
                   champion is robust here even against a stream chosen by an
                   omniscient enemy.

  ESCAPE DEPTH E = given that killing line, the LATEST ply j at which ONE
                   different champion move would have survived it; E = K - j.
                   E is exactly "how many plies ahead the champion would have
                   had to see to dodge this". E=2 means depth-4 search fixes it
                   (d3 already sees 3). No j at all means the line was
                   unavoidable from the start -- ALREADY LOST, not myopia.

The distinction between K and E is the whole argument. K says how dangerous the
spot is; E says whether SEARCH DEPTH could have saved it. A hole with large K
and small E is a myopia hole (buy depth). A hole with small E unavailable --
i.e. no single deviation escapes -- is not a search problem at all.
"""
from __future__ import annotations
import sys, os, json, argparse, time
from concurrent.futures import ProcessPoolExecutor, as_completed

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import champion as CH   # noqa: E402
import poker as PK      # noqa: E402

ALL_ACTIONS = [v * 8 + c for v in range(4) for c in range(8)]


def shortest_kill(board, cur, max_depth=7, max_oracle=30_000, log=None):
    sp = PK.SoloPoker(board, cur, max_oracle=max_oracle, log=log)
    return sp.search(max_depth=max_depth)


def replay(board, cur, line):
    """Replay a killing line, returning the board/pill at each ply."""
    b = board.clone()
    states = [(b.clone(), cur)]
    c = cur
    for (n, a, st) in line:
        ok, _cl, _v, _ch = CH.apply_action(b, a, c[0], c[1])
        if not ok:
            break
        states.append((b.clone(), n))
        c = n
    return states


def escape_depth(board, cur, line, max_E=8):
    """Latest ply with a ONE-MOVE escape from this killing line.
    Returns dict(E=..., ply=..., alt_action=..., avoidable=bool).

    We scan only the last `max_E` plies. E > 8 is not an actionable finding
    anyway -- no feasible search depth reaches it -- and the scan is quadratic
    in K, so an unbounded scan would spend its whole budget proving something
    we could not act on. E reported as '>max_E' when nothing is found."""
    K = len(line)
    states = replay(board, cur, line)
    pills = [cur] + [n for (n, _a, _st) in line]
    lo_j = max(0, K - max_E)

    for j in range(K - 1, lo_j - 1, -1):    # latest first => smallest E
        b_j, cur_j = states[j]
        played = line[j][1]
        nxt_j = pills[j + 1] if j + 1 < len(pills) else pills[-1]
        for alt in ALL_ACTIONS:
            if alt == played:
                continue
            nb = b_j.clone()
            ok, _c, _v, _ch = CH.apply_action(nb, alt, cur_j[0], cur_j[1])
            if not ok:
                continue
            if nb.virus_count() == 0:
                return {"E": K - j, "ply": j, "alt": alt, "avoidable": True,
                        "how": "clear"}
            if nb.spawn_blocked():
                continue
            # champion plays on from here under the SAME remaining pills
            alive = True
            bb, cc = nb, pills[j + 1]
            for t in range(j + 1, K):
                nn = pills[t + 1] if t + 1 < len(pills) else pills[-1]
                col, vir = CH.board_to_flat(bb)
                a2 = CH.champion_move(col, vir, cc[0], cc[1], nn[0], nn[1])
                if a2 is None:
                    alive = False; break
                b2 = bb.clone()
                ok2, _c2, _v2, _ch2 = CH.apply_action(b2, a2, cc[0], cc[1])
                if not ok2:
                    alive = False; break
                if b2.virus_count() == 0:
                    break
                if b2.spawn_blocked():
                    alive = False; break
                bb, cc = b2, nn
            if alive:
                return {"E": K - j, "ply": j, "alt": alt, "avoidable": True,
                        "how": "survives"}
    scanned_all = (lo_j == 0)
    return {"E": None, "ply": None, "alt": None, "avoidable": False,
            "scanned_all": scanned_all,
            "how": ("no single deviation escapes -- already lost when the line began"
                    if scanned_all else
                    f"no escape in the last {max_E} plies (earlier plies not scanned)")}


def describe(board, cur, line, K, esc):
    """Plain-language description of the champion's mistake."""
    states = replay(board, cur, line)
    if not esc["avoidable"]:
        return (f"Unavoidable: from this board every one of the champion's own "
                f"moves loses to this {K}-pill stream. Not a search failure.")
    j = esc["ply"]
    b_j, cur_j = states[j]
    played = line[j][1]
    alt = esc["alt"]
    pv, pc = played // 8, played % 8
    av, ac = alt // 8, alt % 8
    heights = [b_j.top_occupied_row(c) for c in range(8)]
    return (f"At ply {j} (spawn_top={PK.spawn_top(b_j)}, column tops={heights}) "
            f"the champion played a {'vertical' if pv >= 2 else 'horizontal'} in "
            f"column {pc}; a {'vertical' if av >= 2 else 'horizontal'} in column "
            f"{ac} survives. It needed to see {esc['E']} plies ahead "
            f"(it searches 3) to prefer the alternative.")


# ---------------------------------------------------------------- parallel
def _init():
    CH.init_champion()


def _job(spec):
    """spec: dict(tag, col, vir, link, cur, max_depth, max_oracle)"""
    import numpy as np
    CH.init_champion()
    b = CH.board_from_flat(np.array(spec["col"], dtype=np.int8),
                           np.array(spec["vir"], dtype=np.int8),
                           np.array(spec["link"], dtype=np.int8)
                           if spec.get("link") else None)
    cur = tuple(spec["cur"])
    t0 = time.time()
    r = shortest_kill(b, cur, max_depth=spec.get("max_depth", 7),
                      max_oracle=spec.get("max_oracle", 30_000))
    out = {"tag": spec["tag"], "spawn_top": PK.spawn_top(b),
           "h": PK.h_lower_bound(b), "K": r["depth"],
           "budget_hit": r["budget_hit"], "searched_to": r["searched_to"],
           "calls": r["calls"], "secs": round(time.time() - t0, 1),
           "viruses": int(b.virus_count())}
    if r["depth"] is not None:
        esc = escape_depth(b, cur, r["line"])
        out.update(E=esc["E"], escape_ply=esc["ply"], avoidable=esc["avoidable"],
                   how=esc["how"], story=describe(b, cur, r["line"], r["depth"], esc),
                   line=[[list(n), int(a) if a is not None else None, st]
                         for (n, a, st) in r["line"]])
    return out


def run_specs(specs, workers=6, out=None, label=""):
    print(f"=== MARGIN: {len(specs)} positions, {workers} workers {label} ===",
          flush=True)
    rows = []
    t0 = time.time()
    with ProcessPoolExecutor(max_workers=workers, initializer=_init) as ex:
        futs = {ex.submit(_job, s): s["tag"] for s in specs}
        for i, f in enumerate(as_completed(futs)):
            r = f.result()
            rows.append(r)
            print(f"  [{i+1}/{len(specs)}] {r['tag']:28s} spawn_top={r['spawn_top']:2d} "
                  f"h={r['h']} K={r['K']} E={r.get('E')} "
                  f"{'BUDGET' if r['budget_hit'] else ''} {r['secs']}s", flush=True)
    if out:
        with open(os.path.join(HERE, out), "w") as fh:
            json.dump(rows, fh, indent=1, default=str)
        print(f"wrote {out}  ({time.time()-t0:.0f}s total)")
    return rows
