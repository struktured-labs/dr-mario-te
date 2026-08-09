"""Owner's four-metric battery, computed only where an instrument supports it.

Each metric states what it CAN answer and what it cannot. Every classifier carries a
killed mutant: a check that cannot fail proves nothing (dr-mario-gate-standard-killed-mutants).

Sources are the vendored per-pill tracker CSVs under results/latency_events/, the same
files (and the same spawn-row-lock control) the latency columns already use.
"""
import collections
import csv
import os
import statistics as st
import sys

EVAL47 = os.path.dirname(os.path.abspath(__file__))
LAT = os.path.join(EVAL47, "results", "latency_events")

PLAYERS = {
    "struktured": [os.path.join(LAT, "film_20260804", f"{m}.csv") for m in ("m1", "m2", "m3", "m4")],
    "dr. lulu": [os.path.join(LAT, "film_20260808", "p1_m3.csv")],
}

HORIZ = {"H", "HF"}
VERT = {"V", "VF"}


def rows_for(paths):
    out = []
    for p in paths:
        with open(p) as fh:
            out.append(list(csv.DictReader(fh)))
    return out


def clearing_pills(match_rows):
    """A pill is 'clearing' if the virus count DROPS after it locks.

    LIMIT, stated rather than hidden: this detects VIRUS clears only. A clear made
    entirely of pill cells leaves viruses_left unchanged and is invisible here, so
    these are virus-clearing placements, not all clearing placements.
    """
    out = []
    for rows in match_rows:
        vl = [int(r["viruses_left_p1"]) for r in rows]
        for i, r in enumerate(rows[:-1]):
            if vl[i + 1] < vl[i]:
                out.append(r)
    return out


def orient_split(pills, horiz=HORIZ):
    h = sum(1 for r in pills if r["final_orient"] in horiz)
    v = len(pills) - h
    return h, v, (100.0 * h / len(pills) if pills else None)


def is_spawn_row_lock(row):
    """Tracker finalized the pill still in spawn row 0 -- the known failure signature
    the latency control counts (task #95), not a real placement."""
    import re
    return any(int(m) == 0 for m in re.findall(r"\((\d+),\d+\)", row["final_cells"]))


def drop_frames(match_rows):
    """spawn -> lock, in 60fps frames. Whole-pill lifetime, not decision latency.

    Spawn-row locks are EXCLUDED. Left in, they contribute ~0-frame lifetimes and the
    'fastest drop' becomes a tracker artifact rather than a thing the player did --
    the min is exactly the statistic such an artifact captures.
    """
    keep, dropped = [], 0
    for rows in match_rows:
        for r in rows:
            if is_spawn_row_lock(r):
                dropped += 1
                continue
            keep.append(int(r["lock_frame"]) - int(r["spawn_frame"]))
    return keep, dropped


def rotation_dirs(match_rows):
    """Tracker labels: 'cw'/'ccw' are VISUAL directions; 'tog' is a monocolor pill
    whose direction is unknowable (both halves identical), and is reported, never
    folded into either side."""
    c = collections.Counter()
    for rows in match_rows:
        for r in rows:
            for tok in filter(None, r["rotation_seq"].split(",")):
                c[tok.split("@")[0]] += 1
    return c


def mutants():
    """Each must CHANGE a published answer. An equivalent mutant proves nothing."""
    ok = True
    rows = rows_for(PLAYERS["struktured"])
    pills = clearing_pills(rows)

    h, v, pct = orient_split(pills)
    h_m, v_m, pct_m = orient_split(pills, horiz=VERT)   # swap the orientation classes
    hit = (h, v) != (h_m, v_m)
    print(f"  mutant: orientation classes swapped                  "
          f"{'KILLED' if hit else '*** SURVIVED'} ({h}/{v} -> {h_m}/{v_m})")
    ok &= hit

    # A cascade-style mutant: treat EVERY pill as clearing. Must move the split.
    all_pills = [r for rs in rows for r in rs]
    h2, v2, _ = orient_split(all_pills)
    hit2 = (h2, v2) != (h, v)
    print(f"  mutant: every pill counted as clearing               "
          f"{'KILLED' if hit2 else '*** SURVIVED'} ({h}/{v} -> {h2}/{v2})")
    ok &= hit2

    # Rotation: folding 'tog' into 'cw' must change the ratio.
    c = rotation_dirs(rows)
    base = c["cw"] / (c["cw"] + c["ccw"])
    mut = (c["cw"] + c["tog"]) / (c["cw"] + c["tog"] + c["ccw"])
    hit3 = abs(base - mut) > 1e-9
    print(f"  mutant: 'tog' folded into cw                         "
          f"{'KILLED' if hit3 else '*** SURVIVED'} ({100*base:.1f}% -> {100*mut:.1f}%)")
    ok &= hit3
    return ok


def main():
    print("KILLED-MUTANT GATE")
    if not mutants():
        print("GATE FAILED -- not reporting numbers")
        return 1
    print("  GATE: PASS\n")

    for name, paths in PLAYERS.items():
        rows = rows_for(paths)
        n_pills = sum(len(r) for r in rows)
        pills = clearing_pills(rows)
        h, v, pct = orient_split(pills)
        d, d_excl = drop_frames(rows)
        c = rotation_dirs(rows)
        cw, ccw, tog = c["cw"], c["ccw"], c["tog"]
        directional = cw + ccw

        print(f"== {name}  ({n_pills} pills over {len(rows)} match window(s))")
        print(f"  1. virus-clearing placements: n={len(pills)}  "
              f"HORIZONTAL {h} ({pct:.1f}%)  VERTICAL {v} ({100-pct:.1f}%)")
        print(f"     [orientation of the CLEARING PILL -- not the direction of the cleared line]")
        print(f"  2. drop speed spawn->lock, n={len(d)} "
              f"({d_excl} spawn-row locks excluded): "
              f"min {min(d)} f ({min(d)/60:.2f} s)  max {max(d)} f ({max(d)/60:.2f} s)  "
              f"median {st.median(d):.0f} f")
        print(f"  3. rotation direction: cw {cw}  ccw {ccw}  (tog {tog} = monocolor, "
              f"direction unknowable)")
        if directional:
            print(f"     directional n={directional}: CW {100*cw/directional:.1f}%  "
                  f"CCW {100*ccw/directional:.1f}%")
        print()
    return 0


if __name__ == "__main__":
    sys.exit(main())
