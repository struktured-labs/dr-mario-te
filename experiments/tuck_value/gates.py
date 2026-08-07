#!/usr/bin/env python3
"""The two gates that self-consistency cannot substitute for.

Written after the co-sim farm found a 1-based/0-based pill-colour bug at its
copro mailbox that was invisible to EVERY structural gate it had — its
agreement gate fed two binaries the same (wrong) input, and its corpus
generator shared an encoder with its game loop, so a systematic input error
cancelled out of both sides. Only an outcome-plausibility check could see it.

Two gates here, and they are different in kind from the ten in
`selftest_2x2.py`. Those prove internal consistency: that this rig agrees with
itself and with the engine it runs on. These two ask whether the rig agrees
with the OUTSIDE WORLD — the encoding the rest of the project uses, and a
known real play rate.

GATE 1  COLOUR CONVENTION, checked empirically at every boundary.
GATE 2  OUTCOME PLAUSIBILITY, anchored to the 1,474-game clean census.

Usage:
  gates.py                      # both gates, plus results-file audit
  gates.py --colours-only
"""
from __future__ import annotations

import argparse
import glob
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
EXPERIMENTS = os.path.dirname(HERE)
EVAL47 = os.path.join(EXPERIMENTS, "eval47")
for _p in (HERE, EXPERIMENTS, EVAL47):
    if _p not in sys.path:
        sys.path.insert(0, _p)

# The champion's measured clean-L11 record: 0 failures in 1,474 games. A rig
# whose clean champion arm falls below this floor is broken, not interesting.
# Set well below the census rate so it fires on breakage, not on noise: at a
# true 99.9%, P(<97% of 400) is negligible; at a genuinely broken rig the clean
# arm collapses by tens of points, as arm B does.
CLEAN_CHAMPION_CLEAR_FLOOR = 0.97
CHAMPION_ARMS = ("v1_drop",)          # arm A is the shipped champion, unmodified


# ==========================================================================
# GATE 1 -- colour convention
# ==========================================================================
def gate_colours(n_games=6, steps=40, seed0=31337):
    """Every boundary this rig crosses, checked on live data.

    THE STRUCTURAL POINT, which is why this rig was never exposed to the
    co-sim's bug: the fast-sim arms never talk to a copro mailbox. Pill
    colours go faithful-sim -> tuck_enum -> fast-sim eval and back, all in the
    sim's native 1..3 space, and the only 0-based encoding anywhere in the
    project (the $5080-$5083 mailbox, and the hostdata corpus written from
    `rng.randint(0, 2)`) is read in exactly one file here --
    `calibrate_theta.py`, a diagnostic, not a game arm.

    AND THE ENCODING IS FAIL-LOUD IN THIS DIRECTION. The co-sim's bug was
    silent because 1..3 written into a 2-bit 0..2 field still looks like a
    valid colour. The reverse -- 0-based colours arriving in the faithful
    sim's plane -- CANNOT be silent, because 0 is EMPTY there: a 0-based board
    loses every cell of its first colour outright. `_selftest_zero_based_board_
    is_loud` demonstrates that rather than asserting it.
    """
    import numpy as np
    import reach_root as RR
    RR._lazy()
    import tuck_enum as TE
    import run_2x2 as R2
    import divergence as DV
    L = RR._lazy()
    FB, RS = L["FB"], L["RS"]

    bad = []
    seen_pill, seen_board, seen_te, seen_placed = set(), set(), set(), set()

    for g in range(n_games):
        env, src = DV._new_game(11, seed0 + g)
        for _ in range(steps):
            if env.board.virus_count() == 0:
                break
            # (a) capsule stream out of NesPillSource
            ca, cb = int(env.cur.a), int(env.cur.b)
            na, nb = int(env.nxt.a), int(env.nxt.b)
            seen_pill.update((ca, cb, na, nb))

            # (b) board colour plane as the eval chain sees it
            fb = FB.from_board(env.board)
            col, vir = RS.board_flat_from_fb(fb)
            seen_board.update(int(x) for x in np.unique(col))

            # (c) tuck_enum's returned colours
            for p in TE.enumerate(fb, ca, cb, mode="free")[:24]:
                seen_te.update(int(x) for x in p["colors"])

            # (d) what the tuck path actually writes to the board
            pick, base_action = R2.choose_with_base(
                fb, col, vir, ca, cb, na, nb, "t3", R2.FIRMWARE_THETA)
            if pick["kind"] == "tuck":
                seen_placed.update((int(pick["ca"]), int(pick["cb"])))
                if {int(pick["ca"]), int(pick["cb"])} - {ca, cb}:
                    bad.append(("tuck colours not drawn from the capsule",
                                (pick["ca"], pick["cb"]), (ca, cb)))
            act = base_action if pick["kind"] != "tuck" else None
            if act is None:
                break
            _, _, term, trunc, _ = env.step(int(act))
            if term or trunc:
                break

    def check(name, seen, allowed):
        extra = seen - allowed
        print(f"  {name:<44} saw {sorted(seen)}"
              + (f"   UNEXPECTED {sorted(extra)}" if extra else ""))
        if extra:
            bad.append((name, sorted(extra)))

    print("  boundary                                     observed values")
    check("(a) NesPillSource capsule colours", seen_pill, {1, 2, 3})
    check("(b) board colour plane (0 = EMPTY)", seen_board, {0, 1, 2, 3})
    check("(c) tuck_enum placement colours", seen_te, {1, 2, 3})
    check("(d) colours written by the tuck path", seen_placed, {1, 2, 3})

    ok_loud = _selftest_zero_based_board_is_loud()
    ok_hostdata = _selftest_hostdata_decode()
    for b in bad[:5]:
        print(f"    {b}")
    return not bad and ok_loud and ok_hostdata


def _selftest_zero_based_board_is_loud():
    """A 0-based board arriving in the faithful sim's plane must be LOUD, not
    silent. Demonstrated: shift a real board down by one and count the cells
    that vanish. If the answer were 0 this rig would share the co-sim's
    silent-failure mode."""
    import numpy as np
    import reach_root as RR
    import divergence as DV
    L = RR._lazy()
    FB, RS = L["FB"], L["RS"]
    env, _src = DV._new_game(11, 4242)
    fb = FB.from_board(env.board)
    col, _vir = RS.board_flat_from_fb(fb)
    occupied = int(np.count_nonzero(col))
    zero_based = np.where(col > 0, col - 1, col)     # 1..3 -> 0..2
    lost = occupied - int(np.count_nonzero(zero_based))
    print(f"  0-based board would lose {lost} of {occupied} occupied cells "
          f"({lost / max(1, occupied):.0%}) -- "
          f"{'LOUD, cannot pass unnoticed' if lost else 'SILENT -- BAD'}")
    return lost > 0


def _selftest_hostdata_decode():
    """The one place this rig reads the project's 0-based encoding:
    calibrate_theta.py, reading the co-sim's hostdata corpus. Its decode must
    produce a board the faithful sim would recognise — colours in 1..3 and a
    virus count consistent with the level, not an off-by-one smear."""
    import calibrate_theta as CT
    path = "/mnt/data/drmario_cosim/gate/hostdata_l11_20.txt"
    if not os.path.exists(path):
        print("  hostdata decode: corpus absent, SKIPPED")
        return True
    import numpy as np
    cases = CT.read_hostdata_full(path)
    bad_col, virus_counts, pill_vals = 0, [], set()
    for cA, cB, nA, nB, board in cases:
        col, vir = CT.planes(board)
        vals = set(int(x) for x in np.unique(col))
        if vals - {0, 1, 2, 3}:
            bad_col += 1
        virus_counts.append(int(vir.sum()))
        pill_vals.update((cA, cB, nA, nB))
    ok = (bad_col == 0 and pill_vals <= {1, 2, 3}
          and all(0 < v <= 48 for v in virus_counts))
    print(f"  hostdata decode ({len(cases)} boards): colour values ok on "
          f"{len(cases) - bad_col}/{len(cases)}, pill colours {sorted(pill_vals)}, "
          f"virus counts {min(virus_counts)}-{max(virus_counts)} (L11 starts at 48)")
    if not ok:
        print("    DECODE LOOKS WRONG -- 0/1 base or nibble layout is off")
    return ok


# ==========================================================================
# GATE 2 -- outcome plausibility
# ==========================================================================
def gate_outcomes(results_dir):
    """Anchor to a known real rate. The shipped champion has 0 failures in
    1,474 clean L11 games, so this rig's clean champion arm must clear
    essentially everything. If it does not, something upstream is wrong and no
    A/B computed from it means anything -- STOP rather than report.

    Deliberately checks the arm that is supposed to be NORMAL. Arms B/C/D are
    expected to be bad in some configurations, so a floor on them would be a
    floor on the finding rather than on the rig."""
    ok = True
    checked = 0
    for path in sorted(glob.glob(os.path.join(results_dir, "*.json"))):
        with open(path) as fh:
            d = json.load(fh)
        cfg = d.get("config") or {}
        if cfg.get("pressure") != "clean" or "rows" not in d:
            continue
        for arm in CHAMPION_ARMS:
            if arm not in d["rows"]:
                continue
            r = d["rows"][arm]
            rate = sum(x["won"] for x in r) / len(r)
            checked += 1
            verdict = "PASS" if rate >= CLEAN_CHAMPION_CLEAR_FLOOR else "**FAIL**"
            print(f"  {os.path.basename(path):<28} {arm:<9} clean clear "
                  f"{rate:6.1%} of n={len(r)}  (floor "
                  f"{CLEAN_CHAMPION_CLEAR_FLOOR:.0%})  {verdict}")
            ok = ok and rate >= CLEAN_CHAMPION_CLEAR_FLOOR
    if not checked:
        print("  no clean-pressure champion arm found to check")
    return ok


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--results", default=os.path.join(HERE, "results"))
    ap.add_argument("--colours-only", action="store_true")
    a = ap.parse_args()

    print("=== GATE 1: colour convention at every boundary ===")
    g1 = gate_colours()
    print(f"  -> {'PASS' if g1 else 'FAIL'}")

    if a.colours_only:
        return 0 if g1 else 1

    print("\n=== GATE 2: outcome plausibility vs the 1,474-game clean census ===")
    g2 = gate_outcomes(a.results)
    print(f"  -> {'PASS' if g2 else 'FAIL'}")

    print("\nBOTH GATES PASS" if (g1 and g2) else "\nGATE FAILURE -- do not trust results")
    return 0 if (g1 and g2) else 1


if __name__ == "__main__":
    sys.exit(main())
