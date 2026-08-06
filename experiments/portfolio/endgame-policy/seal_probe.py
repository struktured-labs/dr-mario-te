#!/usr/bin/env python3
"""endgame-policy thread: does the CHAMPION commit the human's measured
endgame error -- SELF-SEALING its own last targets under approach, per
FILM_REVIEW_20260804_SCORECARD.md / player_styles/struktured.md (8
self-inflicted seal events of 21 total in the m4 endgame, several
re-opened, one triple-seal decisive)?

CHAMPION per spec: fast_rtl_x.variant("winner") leaf + eval47/terms47.
g_stranded ws=20, root-only base search -- i.e. exactly the wt=0, ws=20
arm of eval47/ab47.py::_choose_base. Reused verbatim (same imports, same
call convention, same board flat-list col/vir/lnk-via-FB.from_board
representation: row-major idx=r*8+c, row 0 = TOP, colours 1-based, vir
1/0 flag) so this is not a new engine, just new instrumentation bolted
onto the existing play loop.

SEAL EVENT (operational definition, symmetric with the human film-review
language "settled-material seal episodes over remaining viruses"):
  While virus_count <= SEAL_VC_THRESHOLD (6, per task spec) after a
  placement resolves (post cascade/gravity), for every virus cell i at
  (r,c) with r>0: let j = i-8 (the cell directly above, same column).
  If col[j] is occupied by NON-virus material whose colour differs from
  the virus's own colour, the virus is COVERED. A seal EVENT fires on the
  OPEN->COVERED transition (so re-covering after a re-open counts again,
  matching "sealed four separate times" in the human case study). A
  RE-OPEN event fires on the COVERED->OPEN transition (j clears to empty)
  while the virus is still present.
  This only counts material the AI PLACED ITSELF -- garbage-cell arrival
  is not modelled in this offline env (single-player FaithfulDrMarioEnv,
  no incoming volleys), so every seal counted here is inherently
  self-inflicted; there is no "AI volleys" bucket to subtract, unlike the
  human's 21-total/8-self split which happened in a two-player match.

CAVEAT (per portfolio rules): python/py65-style offline env. This is the
FaithfulDrMarioEnv used throughout eval47/ab47.py for the champion's own
paired A/B testing (not py65-NES-cycle-accurate), so it inherits whatever
fidelity that harness already has for measuring the champion's placement
choices -- it is NOT validated against Verilator/RTL move-for-move. If
seal rate turns out interesting enough to act on (i.e. this survives),
the eval-term prescription must be re-validated through the cosim farm
before being called a fix, per the standing rule.
"""
from __future__ import annotations

import sys
import os
import json
import random
import argparse
import statistics as st
from concurrent.futures import ProcessPoolExecutor, as_completed

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = "/home/struktured/projects/dr_mario_rl"
QA = "/home/struktured/projects/dr-mario-qa-wt/experiments"
for _p in (ROOT + "/tmp/combo_term", ROOT + "/tmp/endgame", ROOT + "/tmp/tuck",
           ROOT + "/tmp/pillrng", ROOT + "/.claude/worktrees/faithful-sim/src", QA,
           QA + "/tuck_v3", QA + "/eval47"):
    if _p not in sys.path:
        sys.path.insert(0, _p)

SEAL_VC_THRESHOLD = 6
H0 = 8
_C = {}


def _init(level, wt, ws):
    import numpy as np
    import fast_rtl_x as FX
    FX.warmup_ship_eh(topk2=8)
    w, fl = FX.variant("winner")
    from terms47 import g_tower, g_stranded
    z = np.zeros(128, dtype=np.int8)
    g_tower(z, z, H0)
    g_stranded(z, z)
    _C.update(level=level, wt=wt, ws=ws, w=w, fl=fl)


def _choose_base(col, vir, ca, cb, na, nb, w, fl, wt, ws):
    import numpy as np
    import fast_rtl_x as FX
    import root_search as RS
    from fast_sim_x import NCELL, _expand_core
    from terms47 import g_tower, g_stranded

    c1 = np.empty(NCELL, dtype=np.int8)
    v1 = np.empty(NCELL, dtype=np.int8)
    best_val, best_a, best_c1 = None, None, None
    for o4 in range(4):
        var = int(FX._VAR_OF_O4[o4])
        for cc in range(8):
            ok, nv, cells = _expand_core(col, vir, var, cc, ca, cb, c1, v1)
            if ok == 0:
                continue
            val = RS._root_value(c1, v1, nv, cells, na, nb, 8,
                                 FX._W_EXCAV_SHIP, FX._W_HANG_SHIP, w, fl)
            if wt:
                val -= wt * g_tower(c1, v1, H0)
            if ws:
                val -= ws * g_stranded(c1, v1)
            if best_val is None or val > best_val:
                best_val, best_a, best_c1 = val, var * 8 + cc, c1.copy()
    return best_a, best_c1


def play(seed):
    """One champion game (wt=0, ws=20 per _C), instrumented for seal events."""
    import numpy as np
    from drmario.faithful_env import FaithfulDrMarioEnv
    from nes_pills import NesPillSource
    from fb import FB
    import root_search as RS

    level, wt, ws, w, fl = _C["level"], _C["wt"], _C["ws"], _C["w"], _C["fl"]
    env = FaithfulDrMarioEnv(level=level, seed=seed, max_pills=300)
    env.reset()
    NesPillSource(seed=seed).attach(env)
    env.cur = env._rand_pill()
    env.nxt = env._rand_pill()

    res = "stall"
    seal_state = {}          # virus cell idx -> covering cell idx while COVERED (else absent)
    seal_events = []         # (pill_idx, vc_after, virus_idx, cover_idx)
    reopen_events = []       # (pill_idx, vc_after, virus_idx)
    reseal_max = {}          # virus idx -> times sealed
    endgame_pill_first = None  # first pill_idx where vc<=SEAL_VC_THRESHOLD
    final_vc = None
    col = vir = None

    for pill_idx in range(300):
        fb = FB.from_board(env.board)
        vc0 = fb.virus_count()
        final_vc = vc0
        if vc0 == 0:
            res = "clear"
            break
        col, vir = RS.board_flat_from_fb(fb)
        a, c1b = _choose_base(col, vir, int(env.cur.a), int(env.cur.b),
                              int(env.nxt.a), int(env.nxt.b), w, fl, wt, ws)
        if a is None:
            break
        _, _, term, trunc, info = env.step(int(a))

        fb2 = FB.from_board(env.board)
        vc1 = fb2.virus_count()
        final_vc = vc1
        if vc1 <= SEAL_VC_THRESHOLD and vc1 > 0:
            if endgame_pill_first is None:
                endgame_pill_first = pill_idx
            col2, vir2 = fb2.col, fb2.vir
            live_viruses = set(i for i in range(128) if vir2[i])
            # drop tracking for viruses that got cleared since last check
            for vi in list(seal_state):
                if vi not in live_viruses:
                    del seal_state[vi]
            for i in live_viruses:
                r, c = divmod(i, 8)
                covered = False
                cover_j = -1
                if r > 0:
                    j = i - 8
                    if col2[j] != 0 and vir2[j] == 0 and col2[j] != col2[i]:
                        covered = True
                        cover_j = j
                was = i in seal_state
                if covered and not was:
                    seal_state[i] = cover_j
                    seal_events.append((pill_idx, vc1, i, cover_j))
                    reseal_max[i] = reseal_max.get(i, 0) + 1
                elif covered and was and seal_state[i] != cover_j:
                    # covering cell changed identity (old one cleared+refilled) --
                    # still "covered" continuously; do not double-count as new seal
                    seal_state[i] = cover_j
                elif not covered and was:
                    del seal_state[i]
                    reopen_events.append((pill_idx, vc1, i))

        if term:
            res = "clear" if info["won"] else "topout"
            break
        if trunc:
            break

    still_sealed_at_end = len(seal_state)
    return {
        "seed": seed, "won": int(res == "clear"), "topout": int(res == "topout"),
        "stall": int(res == "stall"), "pills": env.pills_placed,
        "final_virus_count": int(final_vc) if final_vc is not None else None,
        "reached_endgame": int(endgame_pill_first is not None),
        "endgame_first_pill": endgame_pill_first,
        "n_seal_events": len(seal_events),
        "n_reopen_events": len(reopen_events),
        "n_viruses_ever_sealed": len(reseal_max),
        "max_reseals_single_virus": max(reseal_max.values()) if reseal_max else 0,
        "still_sealed_at_end": still_sealed_at_end,
        "seal_events": seal_events,
        "reopen_events": reopen_events,
    }


def _log_rss(tag):
    import subprocess
    try:
        out = subprocess.run(
            ["bash", "-c", "ps -o rss= -C python 2>/dev/null | awk '{s+=$1} END {print s+0}'"],
            capture_output=True, text=True, timeout=10)
        print(f"  [RSS] {tag}: {int(out.stdout.strip() or 0)/1024:.0f} MB total python", flush=True)
    except Exception as e:
        print(f"  [RSS] {tag}: failed ({e})", flush=True)


def boot_ci(xs, stat=st.mean, n=10000, seed=12345):
    if not xs:
        return (float("nan"), float("nan"))
    rng = random.Random(seed)
    k = len(xs)
    reps = [stat([xs[rng.randrange(k)] for _ in range(k)]) for _ in range(n)]
    reps.sort()
    return reps[int(0.025 * n)], reps[int(0.975 * n)]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--seeds", type=int, default=200)
    ap.add_argument("--seed0", type=int, default=0)
    ap.add_argument("--level", type=int, default=11)
    ap.add_argument("--workers", type=int, default=4)
    ap.add_argument("--wt", type=int, default=0)
    ap.add_argument("--ws", type=int, default=20)
    ap.add_argument("--out", type=str, default="seal_probe_out.json")
    a = ap.parse_args()

    seeds = list(range(a.seed0, a.seed0 + a.seeds))
    print(f"=== SEAL PROBE: champion (wt={a.wt} ws={a.ws}) L{a.level} n={len(seeds)} "
          f"seal_vc_threshold={SEAL_VC_THRESHOLD} ===", flush=True)

    rows = []
    with ProcessPoolExecutor(max_workers=a.workers, initializer=_init,
                             initargs=(a.level, a.wt, a.ws)) as ex:
        futs = {ex.submit(play, s): s for s in seeds}
        for i, f in enumerate(as_completed(futs)):
            try:
                rows.append(f.result())
            except Exception as e:
                rows.append({"seed": futs[f], "error": str(e)})
            if (i + 1) % max(1, len(seeds) // 10) == 0 or (i + 1) == len(seeds):
                _log_rss(f"{i + 1}/{len(seeds)}")

    ok = [r for r in rows if "error" not in r]
    err = [r for r in rows if "error" in r]
    if err:
        print(f"  {len(err)} games errored: {[e['seed'] for e in err][:10]}...", flush=True)

    reached = [r for r in ok if r["reached_endgame"]]
    n = len(ok)
    n_reached = len(reached)
    total_seals = sum(r["n_seal_events"] for r in reached)
    total_reopens = sum(r["n_reopen_events"] for r in reached)
    games_with_seal = sum(1 for r in reached if r["n_seal_events"] > 0)
    seal_rates = [r["n_seal_events"] for r in reached]
    lo, hi = boot_ci(seal_rates) if reached else (float("nan"), float("nan"))

    print(f"\n=== RESULTS: {n} games ({n} ok, {len(err)} errored) ===", flush=True)
    print(f"  reached endgame (vc<={SEAL_VC_THRESHOLD}): {n_reached}/{n} "
          f"({n_reached/n:.1%})" if n else "  n=0", flush=True)
    if n_reached:
        print(f"  won: {sum(r['won'] for r in ok)}/{n} ({sum(r['won'] for r in ok)/n:.1%})", flush=True)
        print(f"  total seal events: {total_seals} over {n_reached} endgame games "
              f"= {total_seals/n_reached:.3f}/game [{lo:.3f},{hi:.3f}] 95% CI", flush=True)
        print(f"  games with >=1 seal event: {games_with_seal}/{n_reached} "
              f"({games_with_seal/n_reached:.1%})", flush=True)
        print(f"  total re-open events: {total_reopens}", flush=True)
        print(f"  max single-game seal count: {max(seal_rates)}", flush=True)
        print(f"  human benchmark (struktured m4, one endgame): 8 self-seals of 21 total "
              f"(13 from AI volleys, not modelled here)", flush=True)

    with open(a.out, "w") as fh:
        json.dump({
            "args": vars(a), "seal_vc_threshold": SEAL_VC_THRESHOLD,
            "n_games": n, "n_errored": len(err), "n_reached_endgame": n_reached,
            "total_seal_events": total_seals, "total_reopen_events": total_reopens,
            "games_with_seal_event": games_with_seal,
            "seal_events_per_endgame_game_mean": (total_seals / n_reached) if n_reached else None,
            "seal_events_ci95": [lo, hi],
            "rows": ok, "errors": err,
        }, fh, indent=2)
    print(f"\nwrote {a.out}", flush=True)
    print("DONE", flush=True)


if __name__ == "__main__":
    main()
