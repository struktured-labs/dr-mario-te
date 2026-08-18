#!/usr/bin/env python3
"""Task #80 re-test: is the champion's death rate in VS games a function of which
SIDE it plays?

WHY THE PER-GAME ROW EXISTS. `adversary_t3/batch_run.evaluate()` averages the two
side-swapped games of a seed into one row before anything is persisted, so the
side label is destroyed at the point of aggregation and the original 6.0%/0.67%
claim cannot be recomputed from any committed artifact. This runner keeps the
GAME as the emitted unit and records the side; the seed remains the unit of
ANALYSIS (see analyze_side_asym.py -- per-project rule, decisions inside a game
are correlated).

TWO ARMS, and the mirror one is the load-bearing one:

  mirror : champion vs champion. NOT a degenerate self-play control here, because
           VsMatch draws each side's virus board from a DIFFERENT rng stream
           (`seed + 1000*k`, vs_env.py:43) while BOTH sides share one capsule
           stream (vs_env.py:49). So the two sides play genuinely different games
           and one of them really does lose. Any residual side preference in this
           arm cannot be skill -- it is harness or mechanics.
           ⚠ Side-SWAPPING the arms is worthless in a mirror (both deciders are
           the same object, so swap=0 and swap=1 are literally the same call).
           What DOES carry information is swapping the BOARDS, which is what
           `board_orient=1` does: it exchanges env[0] and env[1] after
           construction, so across the two orientations of a seed each physical
           side sees each board exactly once. Pooled over both orientations the
           board draw cancels EXACTLY, and any excess is purely positional.

  adv    : champion vs the evolved tier-3 adversary (search_checkpoint best_vec),
           side-swapped -- the configuration the original claim came from.

THE MECHANISM UNDER SUSPICION, named before the data exists: vs_harness.play_match
iterates `for who, dec in ((0, dec0), (1, dec1))` and `break`s out on the first
terminal result, so side 0 moves first in every round and side 1 can be denied its
move in the round the match ends. Side 0 therefore banks garbage first and wins
races it entered level. That is a real positional asymmetry in the harness, and it
is the thing arm `mirror` is pointed at.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
import time
from concurrent.futures import ProcessPoolExecutor

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = "/home/struktured/projects/dr_mario_rl"
T3 = "/home/struktured/projects/dr-mario-main-wt/experiments/adversary_t3"
QA = "/home/struktured/projects/dr-mario-qa-wt/experiments"
for _p in (HERE, T3, ROOT + "/tmp/combo_term", ROOT + "/tmp/endgame", ROOT + "/tmp/tuck",
           ROOT + "/tmp/pillrng", ROOT + "/tmp/vs_aware", ROOT + "/tmp/champion",
           ROOT + "/.claude/worktrees/faithful-sim/src", QA, QA + "/tuck_v3"):
    if _p not in sys.path:
        sys.path.insert(0, _p)

ARM_MIRROR = "mirror"
ARM_ADV = "adv"

# Mutants. `swap_scoring` is the killed-mutant gate required for the side counter:
# it flips the recorded side label, so every by-side count must exchange EXACTLY.
# `same_board` is the POPULATION mutant (gate standard rule 7): it forces both
# sides onto one virus board, which makes the mirror arm perfectly symmetric and
# must therefore collapse the decided-game population toward degeneracy. An
# instrument that reports business as usual under it is measuring nothing.
MUTANTS = ("none", "swap_scoring", "same_board")

_STATE = {}


def _rig_hash():
    """Rule 26: stamp the code that produced the row, not a reconstruction of it."""
    h = hashlib.sha256()
    import vs_harness
    for f in (os.path.abspath(__file__), vs_harness.__file__,
              os.path.join(ROOT, "tmp/champion/vs_env.py")):
        with open(f, "rb") as fh:
            h.update(fh.read())
    return h.hexdigest()[:16]


def _init_pool():
    for _v in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS",
               "NUMEXPR_NUM_THREADS"):
        os.environ.setdefault(_v, "1")
    import vs_harness as H
    import fast_rtl_x as FX  # noqa: F401  (warms the numba kernels via warmup_all)
    from vs_run import champion_decider, warmup_all
    warmup_all()
    _STATE["H"] = H
    _STATE["champ"] = champion_decider()
    _STATE["rev"] = H.HARNESS_REV
    _STATE["rig"] = _rig_hash()


def _adversary(vec):
    from adversary_search import AdversaryD3Decider
    import fast_rtl_x as FX
    w, fl = FX.variant("winner")
    d = AdversaryD3Decider.from_vector(tuple(vec), w, fl, topk2=8)
    d._opponent_aware = True
    return d


def _wrap(dec, H):
    if getattr(dec, "_opponent_aware", False):
        return lambda b, c, n, opp: dec.choose(b, c, n, opp)
    return H.blind(dec)


def _patch_boards(H, board_orient, mutant):
    """Install the VsMatch variant this job needs, then restore.

    We patch the SYMBOL vs_harness resolves rather than copying play_match, because
    a second match loop is how five mechanics bugs survived at once in this project
    (vs_harness.py module docstring). One kernel, many call sites.
    """
    import vs_env
    base = vs_env.VsMatch
    if board_orient == 0 and mutant != "same_board":
        return None

    class _V(base):
        def __init__(self, seed, level=11, max_pills=300, nes_pills=True):
            if mutant == "same_board":
                # Force BOTH sides onto side 0's virus board: the population mutant.
                import drmario.faithful_env as _fe
                super().__init__(seed, level, max_pills, nes_pills)
                self.env[1].board.color[:] = self.env[0].board.color
                self.env[1].board.link[:] = self.env[0].board.link
                self.env[1].board.is_virus[:] = self.env[0].board.is_virus
            else:
                super().__init__(seed, level, max_pills, nes_pills)
            if board_orient == 1:
                self.env[0], self.env[1] = self.env[1], self.env[0]

    prev = H.VsMatch
    H.VsMatch = _V
    return prev


def _one(job):
    seed, arm, swap, board_orient, vec, mutant, level, max_pills = job
    H = _STATE["H"]
    champ = _STATE["champ"]
    opp = champ if arm == ARM_MIRROR else _adversary(vec)

    champ_side = 0 if not swap else 1
    a = _wrap(champ if not swap else opp, H)
    b = _wrap(opp if not swap else champ, H)

    prev = _patch_boards(H, board_orient, mutant)
    try:
        t0 = time.time()
        r = H.play_match(seed, a, b, level=level, max_pills=max_pills, garbage=True)
    finally:
        if prev is not None:
            H.VsMatch = prev

    win = r["winner"]
    reason = r["reason"]
    stall = win < 0
    loser = -1 if stall else 1 - win
    # A DEATH is a topout/no-move loss. `death_side` is the PHYSICAL side that died.
    death_side = loser if (not stall and reason in ("topout", "no-move")) else -1
    vc = r["virus"]

    if mutant == "swap_scoring":
        # THE KILLED-MUTANT GATE: relabel sides at scoring time only. Every by-side
        # count must come back exactly exchanged.
        champ_side = 1 - champ_side
        win = win if stall else 1 - win
        death_side = death_side if death_side < 0 else 1 - death_side
        vc = [vc[1], vc[0]]

    other = 1 - champ_side
    champ_lost = (not stall) and win == other
    champ_died = champ_lost and reason in ("topout", "no-move")
    return {
        "seed": seed, "arm": arm, "swap": swap, "board_orient": board_orient,
        "mutant": mutant, "champ_side": champ_side,
        "winner_side": win, "reason": reason, "stall": stall,
        "death_side": death_side,
        "champ_died": bool(champ_died),
        "champ_won": bool((not stall) and win == champ_side),
        "dies_ahead": bool(champ_died and vc[champ_side] < vc[other]),
        "virus_p0": int(r["virus"][0]), "virus_p1": int(r["virus"][1]),
        "pills_p0": int(r["pills"][0]), "pills_p1": int(r["pills"][1]),
        "releases": int(r["releases"]),
        "boards_differ": None,   # filled by the non-degeneracy probe, not per game
        "rev": _STATE["rev"], "rig": _STATE["rig"],
        "secs": round(time.time() - t0, 3),
    }


def build_jobs(arm, seeds, vec, mutant, level, max_pills):
    if arm == ARM_MIRROR:
        # swap is INFORMATION-FREE in a mirror (same decider both sides); the
        # board orientation is what carries the positional signal.
        return [(s, arm, 0, bo, vec, mutant, level, max_pills)
                for s in seeds for bo in (0, 1)]
    return [(s, arm, sw, 0, vec, mutant, level, max_pills)
            for s in seeds for sw in (0, 1)]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--arm", choices=(ARM_MIRROR, ARM_ADV), required=True)
    ap.add_argument("--seed0", type=int, required=True)
    ap.add_argument("--n", type=int, required=True, help="number of SEEDS")
    ap.add_argument("--mutant", choices=MUTANTS, default="none")
    ap.add_argument("--workers", type=int, default=12)
    ap.add_argument("--level", type=int, default=11)
    ap.add_argument("--max-pills", type=int, default=300)
    ap.add_argument("--out", required=True)
    a = ap.parse_args()

    with open(os.path.join(T3, "search_checkpoint.json")) as fh:
        vec = json.load(fh)["best_vec"]

    seeds = list(range(a.seed0, a.seed0 + a.n))
    jobs = build_jobs(a.arm, seeds, vec, a.mutant, a.level, a.max_pills)

    # HEARTBEAT BEFORE ANY WORK (harness-pgrep-self-match): a zero-byte log is then
    # unambiguously "never started" rather than "started and produced nothing".
    with open(a.out, "w") as fh:
        fh.write(json.dumps({"_status": "RUNNING", "pid": os.getpid(),
                             "arm": a.arm, "mutant": a.mutant, "seed0": a.seed0,
                             "n_seeds": a.n, "n_games": len(jobs),
                             "vec": vec, "t0": time.time()}) + "\n")
        fh.flush()
        t0 = time.time()
        ex = ProcessPoolExecutor(max_workers=a.workers, initializer=_init_pool)
        done = 0
        for row in ex.map(_one, jobs, chunksize=1):
            fh.write(json.dumps(row) + "\n")
            done += 1
            if done % 50 == 0:
                fh.flush()
                print(f"{a.arm}/{a.mutant} {done}/{len(jobs)} "
                      f"{time.time()-t0:.0f}s", flush=True)
        ex.shutdown(wait=True)
        fh.write(json.dumps({"_status": "DONE", "n_games": done,
                             "elapsed_s": round(time.time() - t0, 1)}) + "\n")
    print(f"DONE {a.arm}/{a.mutant} {done} games {time.time()-t0:.0f}s -> {a.out}")


if __name__ == "__main__":
    main()
