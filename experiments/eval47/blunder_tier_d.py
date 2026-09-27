"""TIER D -- wrong-colour-phase contact blunder. Engine-free, oracle-free.

THE CLASS. A dual-colour pill locks horizontally across (r,c) and (r,c+1). Each half
has a CONTACT: the occupied cell directly beneath it. The 180 flip of that pill occupies
the SAME two cells with the colours swapped -- identical geometry, always legal, same
landing. So the two phases are directly comparable with no engine and no counterfactual
search: if the flip would have matched more contacts, the placed phase left free colour
adjacency on the table.

STRICT DOMINATION. Flag only when the flip is at least as good on EVERY contact and
strictly better on at least one. A flip that trades one match for another is not a
blunder, it is a different plan.

BOARD STATE comes from the 60fps frames via the tracker's own classifier -- the same
instrument, same crop grid, that produced the event CSVs.

CONTROL (frame indexing is the classic failure here): at the recorded lock_frame the
pill must actually BE at its recorded cells with its recorded colours. Any pill failing
that is excluded and counted out loud, never silently scored.

FP GATES, both from the owner's own concern:
  TEMPO    the matching phase can cost 2 presses the placed phase did not. Gated count
           keeps only pills with slack -- lifetime above the player's own median -- or
           where the placed phase was itself a 2-press phase (HF).
  SEEDING  a mismatched half may be seeding a column. Gated count drops pills whose
           mismatched column receives a same-colour placement within the next 3 pills.
"""
import collections
import csv
import os
import re
import statistics as st
import sys

import numpy as np
from PIL import Image

FILM = "/home/struktured/projects/dr_mario_rl/tmp/film_review_20260804"
sys.path.insert(0, FILM)
from vision import P1          # noqa: E402
import tracker as T            # noqa: E402

QA = "/home/struktured/projects/dr-mario-qa-wt/experiments/eval47"
LE = os.path.join(QA, "results", "latency_events")
CROP_DX, CROP_DY = 392, 348
P1_CROP = dict(P1, x0=P1["x0"] - CROP_DX, y0=P1["y0"] - CROP_DY)

SOURCES = {
    "struktured": [
        (os.path.join(LE, "film_20260804", f"{m}.csv"),
         os.path.join(FILM, "p1_60fps", m)) for m in ("m1", "m2", "m3", "m4")
    ],
    "dr. lulu": [
        (os.path.join(LE, "film_20260808", "p1_m3.csv"),
         os.path.join(QA, "tmp", "dr_lulu_20260808", "p1_60fps", "m3")),
    ],
}

_IDX = T.build_patch_index(P1_CROP)


def board_at(frames_dir, frame_no):
    path = os.path.join(frames_dir, f"f{frame_no:06d}.jpg")
    if not os.path.exists(path):
        return None, None
    arr = np.asarray(Image.open(path).convert("RGB"))
    return T.classify_frame_vectorized(arr, *_IDX)


def cells_of(row):
    return [(int(a), int(b)) for a, b in re.findall(r"\((\d+),(\d+)\)", row["final_cells"])]


def horizontal_dual(row):
    """-> (r, c_left, colour_left, colour_right) or None."""
    ca, _, cb = row["colors"].partition("-")
    if ca == cb or row["final_orient"] not in ("H", "HF"):
        return None
    cs = cells_of(row)
    if len(cs) != 2 or cs[0][0] != cs[1][0]:
        return None
    left_cell, right_cell = sorted(cs, key=lambda x: x[1])
    if right_cell[1] != left_cell[1] + 1:
        return None
    r, left_col = left_cell
    # H  => left half is colorA; HF => the pair is flipped
    left, right = (ca, cb) if row["final_orient"] == "H" else (cb, ca)
    return r, left_col, left, right


def evaluate(labels, r, c, left, right, swap_scorer=False):
    """-> (placed_matches, flipped_matches, per-contact domination) or None if no contact."""
    nrows = labels.shape[0]
    below = []
    for cc, colour in ((c, left), (c + 1, right)):
        rr = r + 1
        under = labels[rr, cc] if rr < nrows else "."
        below.append((cc, colour, under))
    if all(u == "." for _cc, _col, u in below):
        return None                      # both halves rest on the floor: no contact
    placed = [(col == u) for _cc, col, u in below]
    flip_cols = [right, left]
    flipped = [(flip_cols[i] == below[i][2]) for i in range(2)]
    if swap_scorer:                      # mutant: score the flip as if it were placed
        placed, flipped = flipped, placed
    dominates = all(f >= p for f, p in zip(flipped, placed)) and sum(flipped) > sum(placed)
    return sum(placed), sum(flipped), dominates, below


def analyse(csv_path, frames_dir, swap_scorer=False, always_flag=False):
    rows = list(csv.DictReader(open(csv_path)))
    lifetimes = [int(r["lock_frame"]) - int(r["spawn_frame"]) for r in rows]
    med_life = st.median(lifetimes)
    out = collections.Counter()
    flagged = []
    for i, row in enumerate(rows):
        hd = horizontal_dual(row)
        if hd is None:
            continue
        out["candidates"] += 1
        r, c, left, right = hd
        labels, _ = board_at(frames_dir, int(row["lock_frame"]))
        if labels is None:
            out["frame_missing"] += 1
            continue
        # CONTROL: the pill must be visible where the CSV says it locked.
        if not (labels[r, c] == left and labels[r, c + 1] == right):
            out["control_fail"] += 1
            continue
        out["scored"] += 1
        ev = evaluate(labels, r, c, left, right, swap_scorer=swap_scorer)
        if ev is None:
            out["no_contact"] += 1
            continue
        placed, flip, dominates, below = ev
        if always_flag:
            dominates = True             # mutant: flag everything that has contact
        if not dominates:
            continue
        out["ungated"] += 1
        life = int(row["lock_frame"]) - int(row["spawn_frame"])
        tempo_ok = life > med_life or row["final_orient"] == "HF"
        # A mismatched half is (its column, ITS OWN colour) -- the thing a later pill
        # would have to answer in that column for this to read as seeding. Comparing the
        # next pill's colours to a board cell instead (an earlier bug here) matches almost
        # anything and excluded 5 of 5.
        mismatched = [(below[k][0], below[k][1]) for k in range(2)
                      if below[k][1] != below[k][2]]
        seeded = False
        for nxt in rows[i + 1:i + 4]:
            nxt_cols = {cc for _rr, cc in cells_of(nxt)}
            nxt_colours = set(nxt["colors"].split("-"))
            for mc, half_colour in mismatched:
                if mc in nxt_cols and half_colour in nxt_colours:
                    seeded = True
        out["excl_tempo"] += (not tempo_ok)
        out["excl_seed"] += bool(seeded)
        if tempo_ok and not seeded:
            out["gated"] += 1
            flagged.append((row["pill_id"], r, c, left, right, below, placed, flip,
                            life, row["final_orient"], os.path.basename(frames_dir),
                            int(row["lock_frame"])))
    return out, flagged


def run(swap_scorer=False, always_flag=False):
    totals, flags = {}, {}
    for name, srcs in SOURCES.items():
        agg = collections.Counter()
        fl = []
        for csv_path, frames in srcs:
            o, f = analyse(csv_path, frames, swap_scorer, always_flag)
            agg.update(o)
            fl += f
        totals[name], flags[name] = agg, fl
    return totals, flags


def main():
    base, flags = run()

    print("CONTROL -- pill visible at its recorded cells in its recorded lock frame")
    for name, a in base.items():
        tot = a["scored"] + a["control_fail"] + a["frame_missing"]
        print(f"  {name:12s} candidates {a['candidates']:4d}  scored {a['scored']:4d}  "
              f"control_fail {a['control_fail']:3d}  frame_missing {a['frame_missing']:3d}  "
              f"=> control pass {100*a['scored']/tot:.1f}%")

    print("\nKILLED-MUTANT GATE")
    sw, _ = run(swap_scorer=True)
    af, _ = run(always_flag=True)
    ok = True
    for name in base:
        h1 = sw[name]["ungated"] != base[name]["ungated"]
        h2 = af[name]["ungated"] > base[name]["ungated"]
        ok &= h1 and h2
        print(f"  {name:12s} phase-swapped scorer {'KILLED' if h1 else '*** SURVIVED'} "
              f"({base[name]['ungated']} -> {sw[name]['ungated']})   "
              f"always-flag {'KILLED' if h2 else '*** SURVIVED'} "
              f"({base[name]['ungated']} -> {af[name]['ungated']})")
    if not ok:
        print("GATE FAILED"); return 1

    print("\nTIER D -- wrong-phase horizontal contact blunders")
    for name, a in base.items():
        n = a["scored"]
        if not n:
            continue
        print(f"  {name:12s} n={n:4d} dual-colour horizontal locks "
              f"({a['no_contact']} floor-only, no contact)")
        print(f"       UNGATED {a['ungated']:3d} = {100*a['ungated']/n:5.2f} /100   "
              f"GATED {a['gated']:3d} = {100*a['gated']/n:5.2f} /100   "
              f"(excluded: tempo {a['excl_tempo']}, seeding {a['excl_seed']})")

    print("\nFLAGGED CASES (for eyeball confirmation)")
    for name, fl in flags.items():
        for f in fl[:5]:
            pid, r, c, left, right, below, p, q, life, orient, mid, lock = f
            unders = "/".join(u for _cc, _col, u in below)
            print(f"  {name:12s} {mid} pill {pid:>3s} lock f{lock}  row {r} cols {c},{c+1}  "
                  f"placed {left}{right} over {unders}  matches {p} -> flip {q}  "
                  f"orient {orient}  life {life}f")
    return 0


if __name__ == "__main__":
    sys.exit(main())
