#!/usr/bin/env python3
"""audit_pill_streams.py -- which of the 65,536 seeds produce a PLAYABLE capsule
stream, and which are degenerate?

WHY. Census seed 1 spent 300 plies emitting one move, cleared 0 of 48 viruses,
and cycled between exactly 2 board states. The cause is not the decider: its
capsule stream is **constant (1,1) forever**, and with only colour-1 capsules
you cannot clear a colour-2 or colour-3 virus. Stacking four and clearing your
own pills is the correct response to an impossible input.

THE MECHANISM. `NesPillSource` maps `s0,s1 = seed>>8, seed&0xFF`, and the LFSR
    fb = bit1(s0) XOR bit1(s1);  s0 = (fb<<7)|(s0>>1);  s1 = (c0<<7)|(s1>>1)
has **(0,0) as an ABSORBING state** — zero feeds back zero. seed=1 gives
(s0,s1)=(0,1), which steps directly to (0,0); the low nibble is then 0 forever,
`acc` never changes, and all 128 buffer entries are capsule id 0 = (1,1).
`NesPillSource` already special-cases seed 0x0000 ("never used by the ROM") but
nothing catches the seeds that COLLAPSE INTO it after one or more steps.

WHY IT MATTERS BEYOND ONE ROW. A degenerate seed is not a hard game, it is a
non-game. Counting it as a play failure inflates the failure rate with rows the
AI could not possibly have won, and it destroys the real signature (the genuine
clean failures all end at the LAST virus; a bogus row with 48 left would bury
that). Auditing all 65,536 seeds is ~8M LFSR steps — seconds — so there is no
excuse for not knowing exactly which seeds are valid before censusing them.

Emits `degenerate_seeds.json`: the exclusion list the census applies.

Usage: audit_pill_streams.py --out degenerate_seeds.json
"""
from __future__ import annotations

import sys
import json
import argparse
from collections import Counter

QA = "/home/struktured/projects/dr-mario-qa-wt/experiments"
sys.path.insert(0, QA)

from nes_pills import gen_sequence, PILL_COLORS  # noqa: E402

# A stream is UNPLAYABLE if the colours it can ever deliver cannot clear all
# three virus colours. The sharp test is not "how many distinct capsule ids"
# but "how many distinct COLOURS appear across all halves" -- a stream of only
# {1,2} can never clear a colour-3 virus no matter how many ids it uses.
MIN_COLOURS = 3


def audit_seed(seed):
    s0, s1 = (seed >> 8) & 0xFF, seed & 0xFF
    if (s0, s1) == (0, 0):
        s0, s1 = 0x89, 0x88          # NesPillSource's own substitution
    ids, _, _ = gen_sequence(s0, s1)
    colours = set()
    for i in ids:
        a, b = PILL_COLORS[i]
        colours.add(a)
        colours.add(b)
    return {"seed": seed, "n_ids": len(set(ids)), "n_colours": len(colours),
            "colours": sorted(colours)}


def stream_key(seed):
    """The 128-capsule buffer itself, hashable -- for finding seeds that are
    the SAME GAME under a different number."""
    s0, s1 = (seed >> 8) & 0xFF, seed & 0xFF
    if (s0, s1) == (0, 0):
        s0, s1 = 0x89, 0x88
    ids, _, _ = gen_sequence(s0, s1)
    return tuple(ids)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="degenerate_seeds.json")
    ap.add_argument("--lo", type=int, default=0)
    ap.add_argument("--hi", type=int, default=65536)
    a = ap.parse_args()

    # ALIAS CHECK. NesPillSource remaps the unusable state (0,0) onto the ROM's
    # warm-boot seed (0x89,0x88) -- so seed 0 plays the SAME GAME as seed
    # 0x8988 = 35208. A census billed as "exhaustive over 65,536" that quietly
    # contains a duplicated pair is exactly what a careful reader finds later,
    # so count DISTINCT STREAMS instead of assuming distinct seeds are distinct
    # games. Done exhaustively rather than by checking the one pair we expect.
    streams = {}
    for seed in range(a.lo, a.hi):
        streams.setdefault(stream_key(seed), []).append(seed)
    dupes = sorted((v for v in streams.values() if len(v) > 1), key=lambda v: v[0])

    bad, id_hist, col_hist = [], Counter(), Counter()
    for seed in range(a.lo, a.hi):
        r = audit_seed(seed)
        id_hist[r["n_ids"]] += 1
        col_hist[r["n_colours"]] += 1
        if r["n_colours"] < MIN_COLOURS:
            bad.append(r)

    n = a.hi - a.lo
    print(f"audited {n} seeds\n")
    print("distinct capsule IDS in the 128-buffer:")
    for k in sorted(id_hist):
        print(f"  {k:>3} ids : {id_hist[k]:>6} seeds ({100 * id_hist[k] / n:.3f}%)")
    print("\ndistinct COLOURS available:")
    for k in sorted(col_hist):
        print(f"  {k} colours: {col_hist[k]:>6} seeds ({100 * col_hist[k] / n:.3f}%)")

    print(f"\nUNPLAYABLE (fewer than {MIN_COLOURS} colours): {len(bad)} seeds "
          f"({100 * len(bad) / n:.4f}%)")
    for r in bad[:20]:
        print(f"  seed {r['seed']:>6}  ids={r['n_ids']}  colours={r['colours']}")
    if len(bad) > 20:
        print(f"  ... and {len(bad) - 20} more")

    print(f"\nALIASED seeds (identical 128-capsule buffer): {len(dupes)} group(s)")
    for grp in dupes[:10]:
        print(f"  seeds {grp} play the SAME game")
    if len(dupes) > 10:
        print(f"  ... and {len(dupes) - 10} more groups")

    bad_set = {r["seed"] for r in bad}
    # Canonical seed per alias group = the lowest; the rest are redundant work.
    redundant = {s for grp in dupes for s in grp[1:]}
    distinct_playable = len({k for k, v in streams.items()
                             if v[0] not in bad_set})
    print(f"\nDISTINCT PLAYABLE STREAMS: {distinct_playable}")
    print(f"  = {n} seeds - {len(bad)} degenerate - {len(redundant)} aliased duplicate(s)")

    # ⚠ THERE IS DELIBERATELY NO "skip_seeds" KEY. An earlier revision emitted
    # one (degenerate + redundant, pre-unioned) and the census consumed it as a
    # dedup list -- which HALVED ITS COVERAGE. `FaithfulDrMarioEnv` draws the
    # VIRUS LAYOUT from numpy(seed) and only the PILLS come from this LFSR, so
    # twins there share a stream but play different boards: 292 of 299 twin
    # pairs reached different outcomes. A single pre-unioned "skip" list is an
    # invitation to that mistake, so the two sets are exposed separately with
    # their scope in the key name. Callers must choose knowingly.
    with open(a.out, "w") as f:
        json.dump({
            "min_colours": MIN_COLOURS,
            "n_audited": n,
            # ALWAYS safe to skip: unplayable under ANY board generator.
            "degenerate_seeds": sorted(bad_set),
            # Safe ONLY where the virus layout ALSO derives from this LFSR
            # (the ROM-true m2a engine). Never for a numpy-seeded-board harness.
            "stream_redundant_seeds__rom_true_engines_only": sorted(redundant),
            "alias_groups": dupes,
            "distinct_playable_streams": distinct_playable,
            "WARNING": ("stream_redundant_seeds duplicate the CAPSULE STREAM "
                        "only. Do not skip them unless the VIRUS LAYOUT also "
                        "derives from this LFSR. In FaithfulDrMarioEnv the "
                        "board comes from numpy(seed), so twins are DIFFERENT "
                        "GAMES and skipping them halves coverage."),
            "detail": bad}, f, indent=2)
    print(f"\nwrote {a.out}")
    print("⚠ stream_redundant_seeds are STREAM duplicates only — safe to skip "
          "ONLY on ROM-true engines. See the WARNING field.")


if __name__ == "__main__":
    main()
