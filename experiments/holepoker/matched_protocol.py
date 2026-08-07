#!/usr/bin/env python3
"""THE MATCHED PROTOCOL — one comparable number per adversary arm.

⚠ BUILT, NOT RUN. Cores are committed to the experiments that gate decisions
(#78's guard, the tuck 2x2, PONR, the census, the dose curve). Run this when a
lane frees up: `matched_protocol.py --arms champion beam --seeds 120`.

WHY IT EXISTS. Tier-4 reported 26.7% and tier-3 ~3% and the two do not stack,
because they were not measuring the same EVENT: different kill conditions,
different seats, different caps, different per-game definitions. Normalising
incompatible numbers afterwards cannot fix that. This fixes the event instead.

THE SIX RULES (approved 2026-08-07)
  1 UNIT = one game, one victim. P(the champion tops out), champion in a FIXED
    seat. No opponent-seat/victim ambiguity.
  2 FIXED BUDGET. 300 placements, L11, the seed's real NES capsule stream.
    No ply caps -- a 70-ply cap silently converts "survived" into "not measured".
  3 PAIRED SEEDS, BOTH SIDES. Every seed played with the champion in each seat;
    the SEED is the unit of analysis (score in {0, 0.5, 1}), because board luck
    dominates the variance. Bootstrap the CI over seeds, never over matches.
  4 ONE GARBAGE RULE for every arm: vs_harness's ROM-true path. The 'exact' rev
    under-counts attacks ~6.7x, so mixing them compares deciders through
    different physics.
  5 POWER off the 22.5-point #47 reference effect, so arms are comparably
    POWERED rather than comparably sized.
  6 REPORT BAD-ENDS AND DIES-AHEAD TOGETHER. Never dies-ahead alone: the
    self-seal lane's ungated arm showed dies-ahead IMPROVING (18 -> 12) while
    bad-ends went 39 -> 152. The denominator moved, not the outcome.

ADDING AN ARM: register a decider factory in ARMS. It must accept
(board, cur, nxt, opp_board) and return an action, i.e. the vs_harness decider
contract, so no arm gets to bring its own match loop.
"""
from __future__ import annotations
import sys, os, json, math, random, argparse, statistics as st
from concurrent.futures import ProcessPoolExecutor, as_completed

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = "/home/struktured/projects/dr_mario_rl"
for _p in (HERE, "/home/struktured/projects/dr-mario-qa-wt/experiments",
           ROOT + "/tmp/vs_aware", ROOT + "/tmp/champion", ROOT + "/tmp/combo_term",
           ROOT + "/tmp/pillrng", ROOT + "/.claude/worktrees/faithful-sim/src"):
    if _p not in sys.path:
        sys.path.insert(0, _p)

LEVEL = 11
MAX_PILLS = 300
DIES_AHEAD_VIRUS = 12
REF_EFFECT = 0.225          # the #47 reference effect, for the power floor


# --------------------------------------------------------------------- arms
def arm_champion():
    """The shipped champion in the adversary seat -- the CONTROL every arm is
    measured against."""
    import fast_rtl_x as F
    F.warmup_delta(topk2=8)
    w, fl = F.variant("winner")
    d = F.FastShipD3DeciderEHDelta(w, fl, topk2=8)
    return lambda b, c, n, opp: d.choose(b, c, n)


def arm_beam():
    """Tier-4's deep-search adversary, adapted to the vs_harness contract.
    Placeholder: the searcher needs the full match state, not just the boards,
    so this arm is registered but must be wired to a lookahead that vs_harness
    can drive. Left explicit rather than silently substituting a weaker policy."""
    raise NotImplementedError(
        "tier-4 beam needs match-level lookahead; wire before running")


ARMS = {"champion": arm_champion, "beam": arm_beam}


# ------------------------------------------------------------------- runner
_D = {}


def _init(arm):
    import vs_harness  # noqa: F401
    _D["fn"] = ARMS[arm]()
    _D["arm"] = arm


def _play(spec):
    """One seed, ONE seat assignment. champ_seat says where the champion sits."""
    import vs_harness as VH
    import fast_rtl_x as F
    seed, champ_seat = spec["seed"], spec["champ_seat"]
    F.warmup_delta(topk2=8)
    w, fl = F.variant("winner")
    champ = F.FastShipD3DeciderEHDelta(w, fl, topk2=8)

    class _B:
        def __init__(s, fn): s.fn = fn
        def choose(s, b, c, n): return s.fn(b, c, n, None)

    champ_fn = VH.blind(_B(lambda b, c, n, o: champ.choose(b, c, n)))
    adv_fn = VH.blind(_B(_D["fn"]))
    d0, d1 = (champ_fn, adv_fn) if champ_seat == 0 else (adv_fn, champ_fn)
    r = VH.play_match(seed, d0, d1, level=LEVEL, max_pills=MAX_PILLS)

    virus = r.get("virus", [0, 0])
    winner = r.get("winner", -1)
    reason = r.get("reason")
    champ_lost = (winner is not None and winner != -1 and winner != champ_seat)
    champ_topped = bool(champ_lost and reason in ("topout", "no-move"))
    v_left = virus[champ_seat] if len(virus) > champ_seat else None
    return {"seed": seed, "champ_seat": champ_seat, "arm": _D["arm"],
            "reason": reason, "winner": winner,
            "champ_topout": champ_topped,
            "champ_virus_left": v_left,
            "dies_ahead": bool(champ_topped and v_left is not None
                               and v_left <= DIES_AHEAD_VIRUS),
            "pills": r.get("pills")}


def boot_ci(xs, n=10000, seed=12345):
    if not xs:
        return (float("nan"), float("nan"))
    rng = random.Random(seed)
    k = len(xs)
    reps = sorted(st.mean([xs[rng.randrange(k)] for _ in range(k)]) for _ in range(n))
    return reps[int(0.025 * n)], reps[int(0.975 * n)]


def power_floor(effect=REF_EFFECT, alpha=0.05, power=0.8, p0=0.20):
    """Seeds needed to detect `effect` on a proportion near p0, paired."""
    z_a, z_b = 1.96, 0.84
    p1 = min(0.99, p0 + effect)
    pbar = (p0 + p1) / 2
    n = ((z_a * math.sqrt(2 * pbar * (1 - pbar))
          + z_b * math.sqrt(p0 * (1 - p0) + p1 * (1 - p1))) ** 2) / (effect ** 2)
    return int(math.ceil(n))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--arms", nargs="+", default=["champion"])
    ap.add_argument("--seeds", type=int, default=0,
                    help="0 = use the power floor from the #47 reference effect")
    ap.add_argument("--workers", type=int, default=8)
    ap.add_argument("--out", type=str, default="results/matched_protocol.json")
    a = ap.parse_args()
    n = a.seeds or power_floor()
    print(f"=== MATCHED PROTOCOL  L{LEVEL}, {MAX_PILLS} placements, "
          f"{n} seeds x 2 seats, arms={a.arms} ===")
    print(f"    power floor for a {REF_EFFECT:.1%} effect at 80%/0.05: {power_floor()} seeds")
    all_rows = []
    for arm in a.arms:
        specs = [{"seed": s, "champ_seat": seat}
                 for s in range(n) for seat in (0, 1)]
        rows = []
        with ProcessPoolExecutor(max_workers=a.workers, initializer=_init,
                                 initargs=(arm,)) as ex:
            for f in as_completed([ex.submit(_play, s) for s in specs]):
                rows.append(f.result())
        all_rows += rows
        by_seed = {}
        for r in rows:
            by_seed.setdefault(r["seed"], []).append(r)
        scores = [sum(x["champ_topout"] for x in v) / len(v)
                  for v in by_seed.values()]
        lo, hi = boot_ci(scores)
        bad = sum(r["champ_topout"] for r in rows)
        ahead = sum(r["dies_ahead"] for r in rows)
        print(f"\n  arm={arm}: champion topout {bad}/{len(rows)} "
              f"({bad/len(rows):.1%})  seed-paired {st.mean(scores):.3f} "
              f"[{lo:.3f},{hi:.3f}]")
        print(f"    dies-ahead {ahead}/{len(rows)}   "
              f"(REPORTED WITH bad-ends, never alone -- the denominator moves)")
    with open(os.path.join(HERE, a.out), "w") as fh:
        json.dump(all_rows, fh, default=str)
    print(f"\nwrote {a.out}")


if __name__ == "__main__":
    main()
