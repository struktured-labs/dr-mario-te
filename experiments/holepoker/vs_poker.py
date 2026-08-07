#!/usr/bin/env python3
"""VS HOLE POKER -- deep search for an opponent line that kills the champion.

Same single-agent formulation as the solo poker, but now the adversary is a
REAL PLAYER on a real board, and its lever is not the pill stream (nobody gets
to choose your capsules in VS) but GARBAGE: clear two lines simultaneously and
two tiles drop on the champion. So the adversary branches over ITS OWN
PLACEMENTS -- which cost no oracle calls at all -- while the champion answers
once per ply through the oracle. That asymmetry is what makes deep VS search
affordable: cost is O(width * plies) oracle calls, not O(branching^plies).

Mechanics are vs_env_exact's, unmodified and imported rather than re-derived:
the ROM-true attack rule (>=2 simultaneous maximal runs -> 2 tiles), the immune
columns (0 and 4), and the shared capsule stream.

The adversary's objective is NOT to win the race -- it is to make the champion
top out as early as possible, which is a different and harder target. A normal
VS opponent that merely out-races the champion tells us nothing about holes.
"""
from __future__ import annotations
import sys, os, json, argparse, time, copy, random
from concurrent.futures import ProcessPoolExecutor, as_completed

HERE = os.path.dirname(os.path.abspath(__file__))
QA = "/home/struktured/projects/dr-mario-qa-wt/experiments"
for _p in (HERE, QA):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import champion as CH   # noqa: E402
import poker as PK      # noqa: E402

ALL_ACTIONS = [v * 8 + c for v in range(4) for c in range(8)]
ADV, CHAMP = 0, 1


def new_match(seed, level, max_pills=300, chain_mode="first"):
    from vs_env_exact import VsMatch
    return VsMatch(seed, level=level, max_pills=max_pills, nes_pills=True,
                   chain_mode=chain_mode, garbage=True)


def champ_decide(m):
    e = m.env[CHAMP]
    col, vir = CH.board_to_flat(e.board)
    return CH.champion_move(col, vir, int(e.cur.a), int(e.cur.b),
                            int(e.nxt.a), int(e.nxt.b))


def adv_legal(m):
    e = m.env[ADV]
    return [a for a in ALL_ACTIONS if e.action_masks()[a]]


def score_state(m, sent):
    """Adversary's objective, lower is better.

    GARBAGE SENT IS PRIMARY, and it has to be: garbage is the adversary's ONLY
    causal channel to the champion's board, so a score that reads only the
    champion's stack has no gradient at all until tiles have already landed --
    the beam then ranks moves it cannot distinguish and wanders. Ranking on
    attacks sent gives the search something to climb from ply 1.

    SELF-PRESERVATION IS SECOND, and it was missing in the first run: an
    adversary rewarded only for attacking stacks its own board chasing double
    clears and tops itself out, which ends the line before the pressure lands.
    Measured: 13 of 14 seeds ended 'no surviving lines' -- every beam line had
    killed ITSELF, so that run bounded my adversary's competence, not the
    champion's robustness. Sorting ascending on -adv_spawn_top prefers the
    adversary's own stack to stay LOW."""
    b = m.env[CHAMP].board
    a = m.env[ADV].board
    return (-sent, -PK.spawn_top(a), PK.spawn_top(b), -int((b.color != 0).sum()))


def ply(m, adv_action):
    """One full round: adversary places, champion receives garbage and replies.
    Returns (status, sent) where status in {None, 'champ_dead', 'adv_dead',
    'champ_clear', 'adv_clear'}."""
    # --- adversary
    m.deliver(ADV)
    if m.env[ADV].board.spawn_blocked():
        return "adv_dead", 0
    before = m.attacks_sent[ADV]
    done, res = m.step(ADV, adv_action)
    sent = m.attacks_sent[ADV] - before
    if done:
        return ("adv_clear" if res == "clear" else "adv_dead"), sent
    # --- champion
    m.deliver(CHAMP)
    if m.env[CHAMP].board.spawn_blocked():
        return "champ_dead", sent
    a = champ_decide(m)
    if a is None:
        return "champ_dead", sent
    done, res = m.step(CHAMP, a)
    if done:
        return ("champ_clear" if res == "clear" else "champ_dead"), sent
    return None, sent


def vs_beam(seed, level, width=16, max_plies=80, log=None):
    """Beam over the ADVERSARY's placements; champion answers via the oracle."""
    log = log or (lambda *a: None)
    m0 = new_match(seed, level)
    frontier = [(m0, [], 0)]          # (match, adversary action path, garbage sent)
    calls = 0
    for d in range(max_plies):
        nxt = []
        for m, path, sent in frontier:
            for a in adv_legal(m):
                mm = copy.deepcopy(m)
                calls += 1
                st, s = ply(mm, a)
                if st == "champ_dead":
                    return {"killed": True, "plies": d + 1, "path": path + [a],
                            "garbage_sent": sent + s, "calls": calls,
                            "seed": seed, "level": level, "width": width}
                if st is not None:
                    continue          # adversary died / someone cleared: dead end
                nxt.append((mm, path + [a], sent + s))
        if not nxt:
            return {"killed": False, "plies": d, "reason": "no surviving lines",
                    "calls": calls, "seed": seed, "level": level, "width": width}
        nxt.sort(key=lambda t: score_state(t[0], t[2]))
        frontier = nxt[:width]
        if d % 10 == 0:
            b = frontier[0][0].env[CHAMP].board
            log(f"    vs d={d} champ spawn_top={PK.spawn_top(b)} "
                f"v={b.virus_count()} sent={frontier[0][2]} calls={calls}")
    b = frontier[0][0].env[CHAMP].board
    return {"killed": False, "plies": max_plies, "reason": "cap",
            "best_spawn_top": PK.spawn_top(b), "garbage_sent": frontier[0][2],
            "calls": calls, "seed": seed, "level": level, "width": width}


def champion_vs_champion(seed, level, max_plies=300):
    """CONTROL: the champion playing the adversary seat with its own eval. If
    deep search does not beat this, deep search bought nothing."""
    m = new_match(seed, level)
    for d in range(max_plies):
        m.deliver(ADV)
        if m.env[ADV].board.spawn_blocked():
            return {"killed": False, "plies": d, "reason": "adv_dead", "seed": seed}
        e = m.env[ADV]
        col, vir = CH.board_to_flat(e.board)
        a = CH.champion_move(col, vir, int(e.cur.a), int(e.cur.b),
                             int(e.nxt.a), int(e.nxt.b))
        if a is None:
            return {"killed": False, "plies": d, "reason": "adv_nomove", "seed": seed}
        st, _s = ply(m, a)
        if st == "champ_dead":
            return {"killed": True, "plies": d + 1, "seed": seed}
        if st is not None:
            return {"killed": False, "plies": d + 1, "reason": st, "seed": seed}
    return {"killed": False, "plies": max_plies, "reason": "cap", "seed": seed}


def _init():
    CH.init_champion()


def _job(spec):
    CH.init_champion()
    t0 = time.time()
    if spec["mode"] == "beam":
        r = vs_beam(spec["seed"], spec["level"], width=spec["width"],
                    max_plies=spec["max_plies"])
    else:
        r = champion_vs_champion(spec["seed"], spec["level"])
    r["mode"] = spec["mode"]
    r["secs"] = round(time.time() - t0, 1)
    return r


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--seeds", type=int, default=12)
    ap.add_argument("--seed0", type=int, default=0)
    ap.add_argument("--no-control", action="store_true")
    ap.add_argument("--level", type=int, default=11)
    ap.add_argument("--width", type=int, default=16)
    ap.add_argument("--max-plies", type=int, default=80)
    ap.add_argument("--workers", type=int, default=6)
    ap.add_argument("--out", type=str, default="results/vs_poker.json")
    a = ap.parse_args()

    rng = range(a.seed0, a.seed0 + a.seeds)
    specs = [{"mode": "beam", "seed": s, "level": a.level, "width": a.width,
              "max_plies": a.max_plies} for s in rng]
    if not a.no_control:
        specs += [{"mode": "control", "seed": s, "level": a.level, "width": 0,
                   "max_plies": a.max_plies} for s in rng]
    print(f"=== VS HOLE POKER: L{a.level}, {a.seeds} seeds, beam width={a.width}, "
          f"vs champion-seat control ===", flush=True)
    rows = []
    with ProcessPoolExecutor(max_workers=a.workers, initializer=_init) as ex:
        futs = [ex.submit(_job, s) for s in specs]
        for i, f in enumerate(as_completed(futs)):
            r = f.result()
            rows.append(r)
            print(f"  [{i+1}/{len(specs)}] {r['mode']:7s} seed={r['seed']:3d} "
                  f"killed={r['killed']} plies={r['plies']} "
                  f"{r.get('reason','')} {r['secs']}s", flush=True)
            with open(os.path.join(HERE, a.out), "w") as fh:
                json.dump(rows, fh, indent=1, default=str)
    for mode in ("beam", "control"):
        sub = [r for r in rows if r["mode"] == mode]
        k = sum(1 for r in sub if r["killed"])
        print(f"\n{mode}: killed {k}/{len(sub)} ({k/max(1,len(sub)):.1%})"
              + (f"  median plies-to-kill "
                 f"{sorted(r['plies'] for r in sub if r['killed'])[k//2] if k else '-'}"
                 if k else ""))
    print(f"wrote {a.out}")


if __name__ == "__main__":
    main()
