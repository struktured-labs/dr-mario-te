#!/usr/bin/env python3
"""FROZEN-SCHEDULE BURSTY — human cadence with a counterfactual-safe schedule.

WHY THIS EXISTS. The escape-depth instrument needs an EXOGENOUS garbage
schedule: deviating one champion move must leave the future pressure identical,
or "did it escape?" partly measures the schedule moving rather than the move.
Drip has that property; the human-fitted BURSTY model does not, because its
volleys key on the champion's OWN clear size. So the depth argument currently
lives in drip while the four-lane diagnosis is anchored on bursty, and the
gated-d4 economics were priced in the one regime where the gate is weakest
(drip fires every 5-8 plies, so `since_garbage <= 6` is open 87.5% of the time
vs #78's 47.8% on bursty).

THE FREEZE IS SURGICAL — one branch, not a reimplementation. In
`bursty_model.inject_bursty_garbage`:

    rng    = random.Random(seed*1000 + pills_placed)   # EXOGENOUS (seed, ply)
    p_fire = model.fire_probability(opponent_clear_size)  # <-- ENDOGENOUS
    if rng.random() >= p_fire: return 0                # <-- the ONLY endogenous branch
    n_cells, cols = model.sample(seed, pills_placed)   # EXOGENOUS (seed, ply)
    ... colours from rng ...                           # EXOGENOUS given the branch

Everything except the FIRE DECISION is already keyed on (seed, ply). So:

  PASS 1  play the game with the LIVE model and record WHICH PLIES FIRED. That
          is the real, human-fitted pressure the champion actually faced --
          the volley times are not modelled or re-sampled, they are observed.
  FREEZE  that set of plies.
  PASS 2+ replay with the fire decision read from the frozen set, while size,
          columns and colours are still drawn from the same (seed, ply) RNG.

⚠ THE RNG DRAW MUST STILL BE CONSUMED. The live path spends one `rng.random()`
on the fire test before drawing colours. Skipping it in frozen mode would shift
the stream and silently change the colours, so `inject_frozen` consumes the draw
and discards it. The fidelity gate below asserts byte-identical games, which is
what catches this class of mistake.

WHAT THE FREEZE COSTS, stated plainly: the counterfactual answers "given the
pressure you ACTUALLY FACED, was there a better move?" It does NOT model that a
different move might have drawn different pressure. That is a deliberate
approximation and it is the same one that makes the drip result valid -- but
under bursty it is an approximation rather than a property, because here the
real schedule genuinely would have responded.
"""
from __future__ import annotations
import sys, os, json, pickle, random, argparse, time
from concurrent.futures import ProcessPoolExecutor, as_completed

HERE = os.path.dirname(os.path.abspath(__file__))
QA = "/home/struktured/projects/dr-mario-qa-wt/experiments"
ROOT = "/home/struktured/projects/dr_mario_rl"
for _p in (HERE, QA, QA + "/eval47", ROOT + "/tmp/combo_term", ROOT + "/tmp/pillrng",
           ROOT + "/.claude/worktrees/faithful-sim/src"):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import champion as CH        # noqa: E402
import poker as PK           # noqa: E402
import classify as CL        # noqa: E402

GARBAGE_MIN_PILLS = 25   # pressure_rig.py:42 / gen_pressure_deaths.py:40, verbatim
MODEL_PKL = os.path.join(QA, "hetzner", "bursty_v1_1.pkl")
_MODEL = None


def model():
    global _MODEL
    if _MODEL is None:
        _MODEL = pickle.load(open(MODEL_PKL, "rb"))
    return _MODEL


# ------------------------------------------------------------------ injection
def _place(board, rng, n_cells, cols):
    from drmario.faithful_game import EMPTY, LINK_NONE
    rows_per_col = max(1, n_cells // max(1, len(cols)))
    placed = 0
    for c in cols:
        if board.color[0, c] != EMPTY:
            continue
        for _ in range(rows_per_col):
            r = 0
            while r < board.rows and board.color[r, c] != EMPTY:
                r += 1
            if r >= board.rows:
                break
            board.color[r, c] = rng.randint(1, 3)
            board.is_virus[r, c] = False
            board.link[r, c] = LINK_NONE
            placed += 1
    if placed:
        board._apply_gravity()      # never let a half float at row 0
        board.resolve()
    return placed


def inject_live(board, seed, ply, clear_size):
    """Faithful copy of bursty_model.inject_bursty_garbage. Returns
    (placed, fired) so pass 1 can record the schedule."""
    m = model()
    rng = random.Random(seed * 1000 + ply)
    p_fire, _n = m.fire_probability(clear_size)
    if rng.random() >= p_fire:
        return 0, False
    n_cells, cols = m.sample(seed, ply)
    if not cols:
        return 0, True          # fired, but the model drew no columns
    return _place(board, rng, n_cells, cols), True


def inject_frozen(board, seed, ply, fired_plies):
    """Same, with the fire decision READ from the frozen schedule."""
    m = model()
    rng = random.Random(seed * 1000 + ply)
    rng.random()                # ⚠ consume the draw the live path spends
    if ply not in fired_plies:
        return 0
    n_cells, cols = m.sample(seed, ply)
    if not cols:
        return 0
    return _place(board, rng, n_cells, cols)


# ----------------------------------------------------------------- game loops
def stream_for(seed, level, n=340):
    from drmario.faithful_env import FaithfulDrMarioEnv
    from nes_pills import NesPillSource
    env = FaithfulDrMarioEnv(level=level, seed=seed, max_pills=n + 8)
    env.reset(); NesPillSource(seed=seed).attach(env)
    return [(int(p.a), int(p.b)) for p in (env._rand_pill() for _ in range(n + 8))]


def play(seed, level, fired_plies=None, override=None, record=False,
         max_pills=300, stop_at=None):
    """One game. fired_plies=None -> LIVE model (pass 1, also records the
    schedule). fired_plies=set -> FROZEN replay. override=(ply, action) forces
    one champion move."""
    from terms47 import g_stranded
    stream = stream_for(seed, level, max_pills)
    b = CH.new_board(level, seed)
    v0 = b.virus_count()
    fired, trace = set(), []
    last_clear = 0
    for i in range(max_pills):
        if b.virus_count() == 0:
            return "clear", i, trace, v0, fired
        # ---- garbage for this ply.
        # ⚠ THE VOLLEY IS CONDITIONAL ON THE PREVIOUS PLACEMENT HAVING CLEARED.
        # pressure_rig's call site guards with `if clear_size > 0`, and its own
        # comment says why: "No clear this step => no volley (fire_probability
        # would otherwise fall back to a pooled unconditional rate, which is
        # wrong for a non-event)." Calling it every ply fires at p=0.348
        # unconditionally, which massively over-delivers -- measured 84% deaths
        # vs the model's documented 16.7%. That is how this was caught.
        g = 0
        if fired_plies is None:
            # LIVE: volley only after a placement that cleared, AND only once
            # past the warm-up -- exactly as pressure_rig / gen_pressure_deaths
            # gate it (`if env.pills_placed >= GARBAGE_MIN_PILLS`, then
            # `if clear_size > 0`). Omitting the warm-up injects from the very
            # first clear and inflates everything downstream: 27.0% deaths
            # without it vs the reference corpus's 16.7%.
            #
            # PLY ALIGNMENT, checked not assumed: their `env.pills_placed` is
            # post-increment, so it equals the index of the pill about to be
            # placed -- the same `i` used here. The (seed, ply) RNG keys
            # therefore line up between the two rigs.
            #
            # CLEAR-SIZE CONVENTION, verified not assumed: theirs is
            # `occ_before + 2 - occ_after`, mine is `resolve()`'s total_cleared;
            # 75/75 agreement on a real trajectory.
            if i >= GARBAGE_MIN_PILLS and last_clear > 0:
                g, did = inject_live(b, seed, i, last_clear)
                if did:
                    fired.add(i)
        else:
            # FROZEN: apply at exactly the recorded plies, UNCONDITIONALLY.
            # The clear-gate must NOT be re-evaluated here -- whether a clear
            # happened is itself endogenous, so re-testing it would let a
            # champion deviation change the schedule and reintroduce the very
            # confound this module exists to remove.
            g = inject_frozen(b, seed, i, fired_plies)
        if b.spawn_blocked():
            if record:
                trace.append({"ply": i, "garbage_in": g, "legal": 0,
                              "stranded": 0, "cleared": 0, "chain": 0,
                              "spawn_top": PK.spawn_top(b),
                              "died_on_delivery": True})
            return "topout", i, trace, v0, fired
        col, vir = CH.board_to_flat(b)
        ca, cb = stream[i]
        na, nb = stream[i + 1]
        a = override[1] if (override and override[0] == i) else \
            CH.champion_move(col, vir, ca, cb, na, nb)
        if a is None:
            return "nomove", i, trace, v0, fired
        if record:
            trace.append({"ply": i, "garbage_in": g,
                          "legal": len(CH.legal_actions(b, ca, cb)),
                          "stranded": int(g_stranded(col, vir)), "cleared": 0,
                          "chain": 0, "spawn_top": PK.spawn_top(b),
                          "died_on_delivery": False,
                          "col": col.tolist(), "vir": vir.tolist(),
                          "cur": [ca, cb], "act": int(a)})
        ok, cleared, _vc, chain = CH.apply_action(b, a, ca, cb)
        if not ok:
            return "illegal", i, trace, v0, fired
        last_clear = int(cleared)
        if record and trace:
            trace[-1]["cleared"] = int(cleared); trace[-1]["chain"] = int(chain)
        if b.virus_count() == 0:
            return "clear", i + 1, trace, v0, fired
        if b.spawn_blocked():
            return "topout", i + 1, trace, v0, fired
        if stop_at is not None and i + 1 >= stop_at:
            return "alive", i + 1, trace, v0, fired
    return "stall", max_pills, trace, v0, fired


def survives_with(seed, level, fired_plies, ply, action, death_ply):
    res, plies, _t, _v, _f = play(seed, level, fired_plies=fired_plies,
                                  override=(ply, action), stop_at=death_ply + 2)
    return res in ("clear", "alive", "stall") or plies > death_ply


def escape_depth(seed, level, fired_plies, trace, death_ply, max_E=8):
    real = [t for t in trace if not t.get("died_on_delivery")]
    for t in reversed(real):
        j = t["ply"]
        if death_ply - j > max_E:
            break
        b = CH.board_from_flat(t["col"], t["vir"])
        for alt in CH.legal_actions(b, t["cur"][0], t["cur"][1]):
            if alt == t["act"]:
                continue
            if survives_with(seed, level, fired_plies, j, alt, death_ply):
                return {"E": death_ply - j, "ply": j, "alt": int(alt),
                        "avoidable": True}
    return {"E": None, "ply": None, "alt": None, "avoidable": False}


# ---------------------------------------------------------------- the gate
def fidelity_gate(seeds=12, level=11):
    """THE GATE: a frozen replay of the baseline must reproduce it EXACTLY.
    If the freeze changed the game at all -- one shifted RNG draw, one different
    colour -- every escape measured against it is meaningless."""
    bad = []
    for s in range(seeds):
        r1, p1, t1, v1, fired = play(s, level, record=True)
        r2, p2, t2, v2, _f = play(s, level, fired_plies=fired, record=True)
        same = (r1 == r2 and p1 == p2 and len(t1) == len(t2))
        if same:
            for a, bb in zip(t1, t2):
                if a.get("col") != bb.get("col") or a.get("act") != bb.get("act"):
                    same = False
                    break
        if not same:
            bad.append((s, r1, p1, r2, p2))
    print(f"  frozen replay reproduces the live game: {seeds-len(bad)}/{seeds}")
    for x in bad[:4]:
        print(f"    MISMATCH seed={x[0]} live {x[1]}@{x[2]} frozen {x[3]}@{x[4]}")
    return len(bad) == 0


def _init():
    CH.init_champion()
    import memo_db
    db = memo_db.ChampionMemo(max_local=200_000, flush_every=20_000)
    CH.attach_db(db)


def _job(spec):
    seed, level = spec["seed"], spec["level"]
    t0 = time.time()
    res, plies, trace, v0, fired = play(seed, level, record=True)
    out = {"seed": seed, "level": level, "result": res, "plies": plies,
           "v0": v0, "n_volleys": len(fired), "secs": round(time.time()-t0, 1)}
    if res not in ("topout", "nomove"):
        return out
    # replay gate before anything is measured
    r2, p2, _t, _v, _f = play(seed, level, fired_plies=fired)
    out["reproduced"] = bool(r2 == res and p2 == plies)
    if not out["reproduced"]:
        out["reject"] = f"frozen replay {r2}@{p2} vs live {res}@{plies}"
        return out
    esc = escape_depth(seed, level, fired, trace, plies)
    out.update(E=esc["E"], escape_ply=esc["ply"], alt=esc["alt"])
    withb = [t for t in trace if "col" in t]
    if withb:
        v_left = int(sum(withb[-1]["vir"]))
        out["v_left"] = v_left
        out["dies_ahead"] = v_left <= 12
        out["delivery_death"] = bool(trace[-1].get("died_on_delivery"))
        tail = [{k: t[k] for k in ("garbage_in", "legal", "stranded", "cleared",
                                   "chain", "spawn_top", "died_on_delivery")
                 if k in t} for t in trace[-10:]]
        out["descriptor"] = CL.descriptor(
            esc["E"], CH.board_from_flat(withb[-1]["col"], withb[-1]["vir"]),
            v_left, v0, tail)
        # #78 gate-open rate under BURSTY cadence -- the number that decides
        # whether gated-d4's economics work
        last_g, opn, tot = None, 0, 0
        for t in trace:
            if t.get("garbage_in", 0) > 0:
                last_g = t["ply"]
            since = (t["ply"] - last_g) if last_g is not None else 10**6
            tot += 1
            opn += (since <= 6)
            if t["ply"] == esc["ply"]:
                out["since_garbage_at_escape"] = since
        out["gate_open_rate"] = opn / tot if tot else 0.0
        out["n_decisions"] = tot
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--seeds", type=int, default=200)
    ap.add_argument("--level", type=int, default=11)
    ap.add_argument("--workers", type=int, default=12)
    ap.add_argument("--gate-only", action="store_true")
    ap.add_argument("--out", type=str, default="results/bursty_frozen.json")
    a = ap.parse_args()
    CH.init_champion()
    print("=== FIDELITY GATE: frozen replay == live game ===")
    ok = fidelity_gate(seeds=10, level=a.level)
    print(f"  {'PASS' if ok else 'FAIL -- freeze changed the game; results void'}")
    if not ok or a.gate_only:
        return 0 if ok else 1

    print(f"\n=== BURSTY-FROZEN ESCAPE: L{a.level}, {a.seeds} seeds ===", flush=True)
    rows = []
    t0 = time.time()
    with ProcessPoolExecutor(max_workers=a.workers, initializer=_init) as ex:
        futs = [ex.submit(_job, {"seed": s, "level": a.level})
                for s in range(a.seeds)]
        for i, f in enumerate(as_completed(futs)):
            r = f.result()
            rows.append(r)
            if r["result"] in ("topout", "nomove"):
                print(f"  [{i+1}/{a.seeds}] seed={r['seed']:3d} DEATH@{r['plies']} "
                      f"E={r.get('E')} ahead={r.get('dies_ahead')} "
                      f"deliv={r.get('delivery_death')} "
                      f"gate={r.get('gate_open_rate',0):.0%} {r['secs']}s", flush=True)
            with open(os.path.join(HERE, a.out), "w") as fh:
                json.dump(rows, fh, default=str)

    from collections import Counter
    d = [r for r in rows if r["result"] in ("topout", "nomove") and r.get("reproduced")]
    print(f"\n=== RESULT ({(time.time()-t0)/60:.1f} min) ===")
    print(f"games {len(rows)}  deaths {len(d)} ({len(d)/max(1,len(rows)):.1%})  "
          f"clears {sum(1 for r in rows if r['result']=='clear')}  "
          f"stalls {sum(1 for r in rows if r['result']=='stall')}")
    if not d:
        print("no deaths"); return 0
    print(f"dies-ahead {sum(1 for r in d if r.get('dies_ahead'))}/{len(d)}   "
          f"delivery deaths {sum(1 for r in d if r.get('delivery_death'))}/{len(d)}")
    es = [r.get("E") for r in d]
    print("\nESCAPE DEPTH E:")
    for k, v in sorted(Counter("none" if e is None else e for e in es).items(),
                       key=lambda x: (99 if x[0] == "none" else x[0])):
        print(f"  E={str(k):>4s}: {v}")
    e1 = sum(1 for e in es if e == 1)
    le3 = sum(1 for e in es if e is not None and e <= 3)
    print(f"\n  E=1   {e1}/{len(d)} = {e1/len(d):.0%}   (depth-4 dodges)")
    print(f"  E<=3  {le3}/{len(d)} = {le3/len(d):.0%}")
    gr = [r["gate_open_rate"] for r in d if "gate_open_rate" in r]
    if gr:
        rate = sum(gr) / len(gr)
        print(f"\n  #78 GATE-OPEN RATE under BURSTY cadence (k=6): {rate:.1%}")
        print(f"  amortised d4 multiplier: {1 + rate*(22.9-1):.2f}x  "
              f"(drip measured 87.5% -> 20.17x)")
    print(f"\nwrote {a.out}")


if __name__ == "__main__":
    sys.exit(main() or 0)
