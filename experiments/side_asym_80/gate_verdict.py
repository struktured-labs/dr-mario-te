#!/usr/bin/env python3
"""Killed-mutant gate for the #80 VERDICT SCRIPT and the SIDE COUNTER.

Two separate things get gated here, because they fail differently:

  A. THE COUNTER. Synthetic game rows with a KNOWN side asymmetry are fed to
     analyse_adv/analyse_mirror; the recovered rates must equal the injected ones,
     and the `swap_scoring` relabelling must exchange them EXACTLY. A counter that
     survives the swap is not reading the side at all.
     Plus the POPULATION check (gate standard rule 7): the mirror arm is only
     meaningful if the two sides genuinely play different boards. That is measured
     against the live env, not assumed.

  B. THE VERDICT FUNCTION. Seven synthetic tables sitting on both sides of every
     registered threshold, including the two that this design is most likely to get
     wrong: a significant-but-tiny effect (must NOT read as CONFIRM) and a null at
     an n too small to exclude the claim (must NOT read as REFUTE).

Exits non-zero if any case fails, so it can gate a launch.
"""
from __future__ import annotations

import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

from analyze_side_asym import (analyse_adv, analyse_mirror, verdict_adv,  # noqa: E402
                               verdict_mirror, gate_swap_mutant, CLAIM_DELTA_PP)

FAILS = []


def check(name, got, want):
    ok = got == want
    print(f"  {'PASS' if ok else 'FAIL'}  {name}: got {got!r} want {want!r}")
    if not ok:
        FAILS.append(name)
    return ok


def adv_rows(n_seeds, d0, d1, overlap=0):
    """Synthetic adv-arm rows: `d0` seeds where the champion dies seated at side 0,
    `d1` where it dies seated at side 1, `overlap` where it dies in both."""
    rows = []
    for s in range(n_seeds):
        die0 = s < d0 or (n_seeds - 1 - s) < overlap
        die1 = (d0 <= s < d0 + d1) or (n_seeds - 1 - s) < overlap
        for cs, died in ((0, die0), (1, die1)):
            rows.append({"seed": s, "arm": "adv", "champ_side": cs,
                         "champ_died": bool(died), "winner_side": 1 - cs if died else cs,
                         "reason": "topout" if died else "clear", "stall": False,
                         "death_side": cs if died else -1, "board_orient": 0})
    return rows


def mirror_rows(n_seeds, seat0_wins_both, board_splits, seat1_wins_both=0):
    """`seat0_wins_both` seeds where side 0 wins in BOTH board orientations (pure
    seat effect); `board_splits` seeds where the winner follows the board;
    `seat1_wins_both` the mirror-image seat effect. The last one exists so the
    per-seed statistic can take BOTH extreme values 0 and 1 -- without it every
    synthetic table has artificially low variance and the INDETERMINATE branch of
    verdict_mirror is unreachable, i.e. shipped untested."""
    rows = []
    for s in range(n_seeds):
        if s < seat0_wins_both:
            ws = (0, 0)
        elif s < seat0_wins_both + seat1_wins_both:
            ws = (1, 1)
        elif s < seat0_wins_both + seat1_wins_both + board_splits:
            ws = (0, 1)
        else:
            ws = (1, 0)
        for bo in (0, 1):
            w = ws[bo]
            rows.append({"seed": s, "arm": "mirror", "champ_side": 0,
                         "board_orient": bo, "winner_side": w, "reason": "topout",
                         "stall": False, "death_side": 1 - w, "champ_died": False})
    return rows


print("A. COUNTER -- recovery of an injected asymmetry")
r = analyse_adv(adv_rows(1000, d0=60, d1=7))
check("deaths_side0", r["deaths_side0"], 60)
check("deaths_side1", r["deaths_side1"], 7)
check("discordant b/c", (r["discordant_b"], r["discordant_c"]), (60, 7))
print(f"       rate0={r['rate_side0']:.4f} rate1={r['rate_side1']:.4f} "
      f"delta={r['delta_pp']:.2f}pp p={r['mcnemar_p']:.3g}")

print("\nA2. COUNTER -- the swap_scoring MUTANT must exchange the counts exactly")
base = adv_rows(1000, d0=60, d1=7)
mut = []
for x in base:
    y = dict(x)
    y["champ_side"] = 1 - x["champ_side"]
    y["death_side"] = x["death_side"] if x["death_side"] < 0 else 1 - x["death_side"]
    mut.append(y)
g = gate_swap_mutant(base, mut)
check("mutant exchanges deaths", g["deaths_exchanged"], True)
check("mutant gate pass", g["pass"], True)

print("\nA3. COUNTER -- an INERT counter (ignores the side) must FAIL the gate")
inert = [dict(x, champ_side=0) for x in base]
g_bad = gate_swap_mutant(base, inert)
check("inert counter is rejected", g_bad["pass"], False)

print("\nA4. MIRROR counter -- seat/board decomposition")
m = analyse_mirror(mirror_rows(1000, seat0_wins_both=1000, board_splits=0))
check("pure-seat win0 rate", round(m["win0_rate"], 6), 1.0)
check("pure-seat seat_determined", m["seat_determined_seeds"], 1000)
m = analyse_mirror(mirror_rows(1000, seat0_wins_both=0, board_splits=500))
check("pure-board win0 rate", round(m["win0_rate"], 6), 0.5)
check("pure-board board_determined", m["board_determined_seeds"], 1000)

print("\nB. VERDICT FUNCTION -- seven tables straddling the registered bands")
cases = [
    # (label, rows, expected verdict)
    ("claim reproduced (60 vs 7 @1500)", adv_rows(1500, 60, 7), "CONFIRM"),
    ("exact null @1500", adv_rows(1500, 45, 45), "REFUTE"),
    ("near-null @1500", adv_rows(1500, 50, 42), "REFUTE"),
    ("zero deaths anywhere", adv_rows(1500, 0, 0), "UNMEASURABLE"),
    # the two the design is most likely to get wrong:
    ("underpowered null @80 (orig n)", adv_rows(80, 3, 3), "INDETERMINATE"),
    ("significant but TINY ratio", adv_rows(20000, 300, 200), "INDETERMINATE"),
    ("large effect, wrong direction", adv_rows(1500, 7, 60), "CONFIRM"),
]
for label, rows, want in cases:
    a = analyse_adv(rows)
    v, why = verdict_adv(a)
    check(label, v, want)
    print(f"        -> {why}")

print("\nB2. MIRROR verdict bands")
mcases = [
    ("pure seat bias @1000", mirror_rows(1000, 1000, 0), "STRUCTURAL_BIAS"),
    ("perfect symmetry @1000", mirror_rows(1000, 0, 500), "NO_STRUCTURAL_BIAS"),
    ("mild bias @1000 (55/45)", mirror_rows(1000, 100, 450), "STRUCTURAL_BIAS"),
    # n too small to BOUND: a genuine 50/50 seat split, but at n=30 the CI is wider
    # than the registered 0.05 bound, so the honest answer is INDETERMINATE and NOT
    # "no bias". This is the branch that stops an underpowered null being reported
    # as a negative (measurement-rules #13).
    ("too few seeds to bound", mirror_rows(30, 15, 0, seat1_wins_both=15),
     "INDETERMINATE"),
    ("same split, n large enough", mirror_rows(2000, 1000, 0, seat1_wins_both=1000),
     "NO_STRUCTURAL_BIAS"),
]
for label, rows, want in mcases:
    m = analyse_mirror(rows)
    v, why = verdict_mirror(m)
    check(label, v, want)
    print(f"        -> {why}")

print("\nC. POPULATION NON-DEGENERACY -- the mirror arm's two sides must play "
      "DIFFERENT boards")
ROOT = "/home/struktured/projects/dr_mario_rl"
for _p in (ROOT + "/tmp/vs_aware", ROOT + "/tmp/champion", ROOT + "/tmp/pillrng",
           ROOT + "/.claude/worktrees/faithful-sim/src"):
    if _p not in sys.path:
        sys.path.insert(0, _p)
from vs_env import VsMatch  # noqa: E402

diff = same_pills = 0
N = 40
for s in range(53000, 53000 + N):
    m = VsMatch(s, 11, 300, True)
    b0, b1 = m.env[0].board, m.env[1].board
    if (b0.color != b1.color).any():
        diff += 1
    if m.env[0].cur == m.env[1].cur and m.env[0].nxt == m.env[1].nxt:
        same_pills += 1
check("virus boards differ on every seed", diff, N)
check("capsule streams identical on every seed", same_pills, N)
print("       (boards differ + pills shared is exactly the mechanic the mirror arm "
      "relies on:\n        a real contest, with the ONLY seat-linked variable being "
      "turn order)")

print("\n" + ("ALL GATES PASSED" if not FAILS else f"FAILED: {FAILS}"))
sys.exit(1 if FAILS else 0)
