"""Decode the flip screen's stored board planes — for the gw-design lane (#117).

HANDOFF, not analysis. gw-design asked for the PLANES rather than a computed
h_min, so their own `garbwin/hmin_neardeath.py` runs on this corpus unchanged
and the near-death and mid-game numbers stay method-identical. This module only
decodes; it deliberately computes NO h_min.

⚠ THE LAYOUT IS NOT OBVIOUS AND IS NOT DOCUMENTED ANYWHERE ELSE, so it is
verified here rather than asserted. `--selftest` decodes real banked events and
cross-checks the recovered column heights against `maxh` and `d_spawn_h`, which
were computed at capture time by a COMPLETELY DIFFERENT code path
(the rig call `heights(env.board.color)` on the live env, never from the hex).
Agreement is therefore evidence, not a tautology.

⚠ SCHEMA, stated because that expression above is a CAPTURE-TIME CALL and reads
like a field name — gw-design lost a moment to exactly that. The JSON keys are:
    pre_col   hex, 256 chars -> the (16,8) COLOUR plane   <- what you decode
    pre_vir   hex, 256 chars -> the (16,8) VIRUS plane
    cur, nxt  [a, b] capsule colours
    bhash     sha256 of colour+virus bytes, first 12 hex (board identity)
There is no `board_color` key. `iter_events()` filters on `pre_col`.

Measured on the first 80 banked events:

    (16,8) row0=TOP      maxh 80/80   d_spawn 80/80   <- correct
    (16,8) row0=bottom   maxh  8/80   d_spawn  0/80
    (8,16) row0=top      maxh  5/80   d_spawn  0/80
    (8,16) row0=bottom   maxh  8/80   d_spawn  0/80

A wrong guess is not subtly wrong — it is 0/80 on d_spawn — which is exactly why
this needed a check rather than a comment.

⚠ h_min IS NOT min(H). Per gw-design: h_min is the minimum over GARBAGE-HIT
columns. These plies are not necessarily post-volley, so the honest computation
is COUNTERFACTUAL over volley phase — size 2 -> {c, c+4}, size 3 ->
{c, c+2, c+4}, size 4 -> {c, c+2, c+4, c+6} — reporting the distribution across
phases, which is how their "adversarial worst phase" row is produced. This file
provides `column_heights()` and stops there ON PURPOSE.
"""
import argparse
import json
import sys

import numpy as np

ROWS, COLS = 16, 8


def decode_plane(hexstr):
    """Hex -> (16, 8) uint8 array, row 0 = TOP. Verified, see module docstring."""
    a = np.frombuffer(bytes.fromhex(hexstr), dtype=np.uint8)
    if a.size != ROWS * COLS:
        raise ValueError(f"expected {ROWS*COLS} cells, got {a.size}")
    return a.reshape(ROWS, COLS)


def column_heights(col_plane):
    """Per-column stack height, 0..16. Occupancy is `!= 0` on the COLOUR plane.

    Returns the count of rows from the topmost occupied cell down, matching the
    rig's own `heights()`: a column with its highest block at row r has height
    ROWS - r. This is HEIGHT, not fill — the two came apart in #121 and near-death
    boards are narrow towers with LOW fill.
    """
    b = np.asarray(col_plane) != 0
    first = np.argmax(b, axis=0)
    return np.where(b.any(axis=0), ROWS - first, 0).astype(np.int64)


def iter_events(path, with_boards_only=True):
    """Yield every screened v2-only flip event, with its game context."""
    for line in open(path):
        try:
            d = json.loads(line)
        except Exception:
            continue
        for e in d.get("events", []):
            if with_boards_only and "pre_col" not in e:
                continue
            e["_game_res"] = d.get("res")
            e["_game_dies_ahead"] = d.get("dies_ahead")
            yield e


def selftest(path, limit=200):
    """Cross-check the decode against independently-captured fields."""
    n = ok_max = ok_ds = 0
    for e in iter_events(path):
        H = column_heights(decode_plane(e["pre_col"]))
        ok_max += int(int(H.max()) == e["maxh"])
        ok_ds += int(int(max(H[3], H[4])) == e["d_spawn_h"])
        n += 1
        if n >= limit:
            break
    print(f"SELFTEST on {n} banked events (fields captured by a DIFFERENT path)")
    print(f"  max(H)            == stored maxh      : {ok_max}/{n}")
    print(f"  max(H[3], H[4])   == stored d_spawn_h : {ok_ds}/{n}")
    good = n > 0 and ok_max == n and ok_ds == n
    print("DECODE", "VERIFIED" if good else "FAILED — do not use this corpus")
    return good


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--screen", default="out/screen_90000.jsonl")
    ap.add_argument("--selftest", action="store_true")
    ap.add_argument("--dump-heights", metavar="PATH",
                    help="write one JSON row per screened flip: seed, ply, the "
                         "8 column heights, viruses, and game outcome. The "
                         "8 heights are sufficient to derive h_min under the "
                         "ROM's own column rule.")
    a = ap.parse_args()

    if a.selftest:
        sys.exit(0 if selftest(a.screen) else 1)

    if a.dump_heights:
        n = 0
        with open(a.dump_heights, "w") as fh:
            for e in iter_events(a.screen):
                H = column_heights(decode_plane(e["pre_col"]))
                fh.write(json.dumps({
                    "seed": e["seed"], "ply": e["ply"],
                    "heights": [int(x) for x in H],
                    "viruses": e["viruses"], "maxh": e["maxh"],
                    "d_spawn_h": e["d_spawn_h"],
                    "game_res": e["_game_res"],
                    "game_dies_ahead": e["_game_dies_ahead"]}) + "\n")
                n += 1
        print(f"wrote {n} rows -> {a.dump_heights}")
        print("h_min is NOT min(heights) — see the module docstring; it is the "
              "min over GARBAGE-HIT columns, counterfactual over volley phase.")
        return

    ap.print_help()


if __name__ == "__main__":
    main()
