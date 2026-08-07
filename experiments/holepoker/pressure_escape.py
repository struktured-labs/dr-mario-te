#!/usr/bin/env python3
"""ESCAPE DEPTH ON THE DEATHS THAT ACTUALLY HAPPEN.

My VS lane produced a clean null once its garbage bug was fixed (0/40 kills), and
solo produced zero topouts in 1200 games. The regime that genuinely kills this
champion is sustained garbage pressure — the drip/bursty models the rest of the
project uses — so that is where "would more search depth have saved it?" has to
be asked.

WHY THIS COUNTERFACTUAL IS CLEAN, where the VS one was not.
`pressure_rig._inject_garbage` seeds its RNG on `(seed, pills_placed)`, so the
garbage schedule is EXOGENOUS: it depends on the ply index, never on what the
champion played. Changing one champion move therefore leaves the entire future
garbage stream identical, and the comparison isolates the move. In the VS rig
the champion's own clears fed the opponent, so any deviation changed the
pressure and the "escape" was partly the adversary going quiet. This has no such
confound.

(It also uses the gravity-correct injection: `_apply_gravity()` before
`resolve()`, with a comment naming the exact float-at-row-0 failure that this
session found still live in `vs_env_exact`.)

OUTPUT, per death: E = the smallest number of plies past its 3-ply horizon at
which ONE different champion move survives past the fatal ply.
  E <= 1  already inside depth-3's horizon -> an EVAL error
  E = 2-3 depth 4-6 would dodge it -> depth is the lever
  E >= 5  no feasible search reaches it -> the eval must encode the pattern
"""
from __future__ import annotations
import sys, os, json, argparse, random, time
from concurrent.futures import ProcessPoolExecutor, as_completed

HERE = os.path.dirname(os.path.abspath(__file__))
QA = "/home/struktured/projects/dr-mario-qa-wt/experiments"
for _p in (HERE, QA, QA + "/eval47"):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import champion as CH      # noqa: E402
import poker as PK         # noqa: E402
import classify as CL      # noqa: E402

ALL_ACTIONS = [v * 8 + c for v in range(4) for c in range(8)]


def inject(board, seed, pills_placed, k):
    """pressure_rig._inject_garbage, verbatim in behaviour (incl. the
    _apply_gravity() that stops halves floating at row 0)."""
    from drmario.faithful_game import EMPTY, LINK_NONE
    rng = random.Random(seed * 1000 + pills_placed)
    cols = rng.sample(range(board.cols), k)
    placed = 0
    for c in cols:
        color = rng.randint(1, 3)
        if board.color[0, c] != EMPTY:
            continue
        r = 0
        while r < board.rows and board.color[r, c] != EMPTY:
            r += 1
        board.color[r, c] = color
        board.is_virus[r, c] = False
        board.link[r, c] = LINK_NONE
        placed += 1
    if placed:
        board._apply_gravity()
        board.resolve()
    return placed


def stream_for(seed, level, n=340):
    from drmario.faithful_env import FaithfulDrMarioEnv
    from nes_pills import NesPillSource
    env = FaithfulDrMarioEnv(level=level, seed=seed, max_pills=n + 8)
    env.reset(); NesPillSource(seed=seed).attach(env)
    return [(int(p.a), int(p.b)) for p in (env._rand_pill() for _ in range(n + 8))]


def play(seed, level, k, period, after, max_pills=300, record=True,
         override=None, stop_at=None):
    """One pressured game. `override=(ply, action)` forces one champion move.
    Returns (result, plies, trace)."""
    from terms47 import g_stranded
    stream = stream_for(seed, level, max_pills)
    b = CH.new_board(level, seed)
    v0 = b.virus_count()
    trace = []
    for i in range(max_pills):
        if b.virus_count() == 0:
            return "clear", i, trace, v0
        # ---- exogenous garbage: depends only on (seed, ply)
        g = 0
        if i >= after and period and (i - after) % period == 0:
            g = inject(b, seed, i, k)
            if b.spawn_blocked():
                if record:
                    trace.append({"ply": i, "garbage_in": g, "legal": 0,
                                  "stranded": 0, "cleared": 0, "chain": 0,
                                  "spawn_top": PK.spawn_top(b),
                                  "died_on_delivery": True})
                return "topout", i, trace, v0
        col, vir = CH.board_to_flat(b)
        ca, cb = stream[i]
        na, nb = stream[i + 1]
        if override is not None and override[0] == i:
            a = override[1]
        else:
            a = CH.champion_move(col, vir, ca, cb, na, nb)
        if a is None:
            return "nomove", i, trace, v0
        if record:
            legal = len(CH.legal_actions(b, ca, cb))
            trace.append({"ply": i, "garbage_in": g, "legal": legal,
                          "stranded": int(g_stranded(col, vir)), "cleared": 0,
                          "chain": 0, "spawn_top": PK.spawn_top(b),
                          "died_on_delivery": False,
                          "col": col.tolist(), "vir": vir.tolist(),
                          "cur": [ca, cb], "act": int(a)})
        ok, cleared, _vc, chain = CH.apply_action(b, a, ca, cb)
        if not ok:
            return "illegal", i, trace, v0
        if record and trace:
            trace[-1]["cleared"] = int(cleared)
            trace[-1]["chain"] = int(chain)
        if b.virus_count() == 0:
            return "clear", i + 1, trace, v0
        if b.spawn_blocked():
            return "topout", i + 1, trace, v0
        if stop_at is not None and i + 1 >= stop_at:
            return "alive", i + 1, trace, v0
    return "stall", max_pills, trace, v0


def survives_with(seed, level, k, period, after, ply, action, death_ply,
                  max_pills=300):
    """Replay forcing `action` at `ply`; does the champion get past death_ply?"""
    res, plies, _t, _v = play(seed, level, k, period, after, max_pills,
                              record=False, override=(ply, action),
                              stop_at=death_ply + 2)
    if res in ("clear", "alive", "stall"):
        return True
    return plies > death_ply


def escape_depth(seed, level, k, period, after, trace, death_ply, max_E=8):
    """Latest ply with a ONE-MOVE escape. Smallest E is the honest requirement."""
    real = [t for t in trace if not t.get("died_on_delivery")]
    for t in reversed(real):
        j = t["ply"]
        if death_ply - j > max_E:
            break
        played = t["act"]
        b = CH.board_from_flat(t["col"], t["vir"])
        for alt in CH.legal_actions(b, t["cur"][0], t["cur"][1]):
            if alt == played:
                continue
            if survives_with(seed, level, k, period, after, j, alt, death_ply,
                             max_pills=300):
                return {"E": death_ply - j, "ply": j, "alt": int(alt),
                        "avoidable": True}
    return {"E": None, "ply": None, "alt": None, "avoidable": False}


def _init():
    CH.init_champion()
    import memo_db
    db = memo_db.ChampionMemo(max_local=200_000, flush_every=20_000)
    CH.attach_db(db)
    globals()["_DB"] = db


def _job(spec):
    seed, level, k, period, after = (spec["seed"], spec["level"], spec["k"],
                                     spec["period"], spec["after"])
    t0 = time.time()
    res, plies, trace, v0 = play(seed, level, k, period, after)
    out = {"seed": seed, "result": res, "plies": plies, "v0": v0,
           "secs": round(time.time() - t0, 1)}
    if res in ("topout", "nomove"):
        # the LAST entry may be a died-on-delivery record, which carries no
        # board (the garbage blocked the spawn before a move was chosen), so
        # read the board from the last entry that actually has one
        withb = [t for t in trace if "col" in t]
        b = CH.board_from_flat(withb[-1]["col"], withb[-1]["vir"]) if withb else None
        esc = escape_depth(seed, level, k, period, after, trace, plies)
        out.update(E=esc["E"], escape_ply=esc["ply"], alt=esc["alt"],
                   avoidable=esc["avoidable"])
        tail = [{kk: t[kk] for kk in ("garbage_in", "legal", "stranded",
                                      "cleared", "chain", "spawn_top",
                                      "died_on_delivery") if kk in t}
                for t in trace[-10:]]
        v_left = int(sum(withb[-1]["vir"])) if withb else None
        out["v_left"] = v_left
        out["dies_ahead"] = (v_left is not None and v_left <= 12)
        if b is not None:
            out["descriptor"] = CL.descriptor(esc["E"], b, v_left or 0, v0, tail)
        out["tail"] = tail
    db = globals().get("_DB")
    if db is not None:
        db.flush()
        out["db"] = db.info()
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--seeds", type=int, default=120)
    ap.add_argument("--level", type=int, default=11)
    ap.add_argument("--k", type=int, default=2, help="garbage halves per drip")
    ap.add_argument("--period", type=int, default=5)
    ap.add_argument("--after", type=int, default=20)
    ap.add_argument("--workers", type=int, default=10)
    ap.add_argument("--out", type=str, default="results/pressure_escape.json")
    a = ap.parse_args()
    print(f"=== PRESSURE ESCAPE: L{a.level}, drip k={a.k} p={a.period} "
          f"after={a.after}, {a.seeds} seeds, {a.workers} workers ===", flush=True)
    specs = [{"seed": s, "level": a.level, "k": a.k, "period": a.period,
              "after": a.after} for s in range(a.seeds)]
    rows = []
    t0 = time.time()
    with ProcessPoolExecutor(max_workers=a.workers, initializer=_init) as ex:
        futs = [ex.submit(_job, s) for s in specs]
        for i, f in enumerate(as_completed(futs)):
            r = f.result()
            rows.append(r)
            if r["result"] in ("topout", "nomove"):
                print(f"  [{i+1}/{len(specs)}] seed={r['seed']:3d} DEATH@{r['plies']} "
                      f"E={r.get('E')} v_left={r.get('v_left')} "
                      f"ahead={r.get('dies_ahead')} "
                      f"mech={(r.get('descriptor') or {}).get('mechanism')} "
                      f"{r['secs']}s", flush=True)
            elif (i + 1) % 20 == 0:
                dbi = r.get("db") or {}
                print(f"  [{i+1}/{len(specs)}] {r['result']}  memo="
                      f"{dbi.get('entries','-')} hit={dbi.get('hit_rate',0):.1%} "
                      f"{(time.time()-t0)/60:.0f}min", flush=True)
            with open(os.path.join(HERE, a.out), "w") as fh:
                json.dump(rows, fh, default=str)

    deaths = [r for r in rows if r["result"] in ("topout", "nomove")]
    from collections import Counter
    print(f"\n=== RESULT ===")
    print(f"games {len(rows)}  deaths {len(deaths)} ({len(deaths)/len(rows):.1%})  "
          f"clears {sum(1 for r in rows if r['result']=='clear')}  "
          f"stalls {sum(1 for r in rows if r['result']=='stall')}")
    ahead = sum(1 for r in deaths if r.get("dies_ahead"))
    print(f"dies-ahead (<=12 viruses left): {ahead}/{len(deaths)}")
    es = [r.get("E") for r in deaths]
    print("\nESCAPE DEPTH E (plies past the champion's 3-ply horizon):")
    for kk, v in sorted(Counter("none" if e is None else e for e in es).items(),
                        key=lambda x: (99 if x[0] == "none" else x[0])):
        print(f"  E={str(kk):>4s}: {v}")
    fix = sum(1 for e in es if e is not None and e <= 3)
    print(f"\n  E<=3 (a depth-4..6 search would dodge it): {fix}/{len(deaths)}")
    print(f"  mechanisms: {dict(Counter((r.get('descriptor') or {}).get('mechanism') for r in deaths))}")
    print(f"wrote {a.out}  ({(time.time()-t0)/60:.1f} min)")


if __name__ == "__main__":
    main()
