#!/usr/bin/env python3
"""BEHAVIOUR DESCRIPTOR for a kill — the axes the MAP-Elites archive bins on.

The point of the archive is COVERAGE, not damage: 40 variants of one trap tell
us nothing about whether depth or eval is the lever, whereas one exemplar per
mechanism tells us exactly that, per mechanism. So every descriptor here is a
CHARACTER of the kill, never its severity.

AXES (4, as specified):
  1 escape_bin   -- plies past its horizon the champion needed: 1,2,3,4,5,6,7,8+
                    or "none" (no single-move escape in the scanned window).
                    This is the axis the depth-vs-eval argument reads off.
  2 region       -- where the trap closed: 'spawn' (col 3-4), 'mid' (2,5),
                    'edge' (0,1,6,7). Computed from the column that actually
                    blocked, not from where the garbage landed.
  3 mechanism    -- spawn_congestion | garbage_flood | colour_starvation |
                    forced_overstack | cascade_backfire. Classified from the
                    champion's own final window, by falsifiable signatures
                    (below), not by narrative.
  4 virus_bin    -- champion's virus count when it died: 'ahead' (<=25% of its
                    starting load left), 'even', 'behind' (>75% left). The field
                    disease -- dying while ahead -- lives in the first bin, so
                    an archive with an empty 'ahead' column would be reassuring
                    and a full one is the thing to chase.

An EMPTY CELL IS A RESULT: it means that kind of hole does not exist for this
champion (within the search effort spent), which is exactly what a covering
archive is for.
"""
from __future__ import annotations
import numpy as np

REGIONS = ("spawn", "mid", "edge")
MECHANISMS = ("spawn_congestion", "garbage_flood", "colour_starvation",
              "forced_overstack", "cascade_backfire")
VIRUS_BINS = ("ahead", "even", "behind")
ESCAPE_BINS = ("1", "2", "3", "4", "5", "6", "7", "8+", "none")


def escape_bin(E):
    if E is None:
        return "none"
    return str(E) if E <= 7 else "8+"


def region_of(board):
    """Which column actually blocked. Prefer a spawn column when one is full,
    since that IS the topout condition; otherwise the tallest column."""
    tops = [board.top_occupied_row(c) for c in range(8)]
    for c in (3, 4):
        if tops[c] == 0:
            return "spawn", c
    c = int(np.argmin(tops))
    if c in (3, 4):
        return "spawn", c
    if c in (2, 5):
        return "mid", c
    return "edge", c


def virus_bin(v_left, v_start):
    if v_start <= 0:
        return "even"
    f = v_left / v_start
    if f <= 0.25:
        return "ahead"
    if f >= 0.75:
        return "behind"
    return "even"


def mechanism_of(trace):
    """Classify from the champion's OWN final window.

    `trace` is a list of per-ply dicts over the last plies before death, each:
      garbage_in   int   tiles delivered to the champion this ply
      legal        int   legal placements the champion had
      stranded     int   terms47.g_stranded of its board
      cleared      int   cells it cleared this ply
      chain        int   cascade length this ply
      spawn_top    int   min top_occupied_row over cols 3,4

    Signatures are ordered most-specific first; each is a claim that could be
    false on a given kill, which is what makes the label mean something.
    """
    if not trace:
        return "spawn_congestion"
    last = trace[-1]
    n = len(trace)
    gin = sum(t["garbage_in"] for t in trace)

    # DELIVERED KILL: the garbage tiles themselves blocked the spawn cells, so
    # the champion never got a move. That is unambiguously the garbage channel
    # whatever the board looked like.
    if last.get("died_on_delivery") and last["garbage_in"] > 0:
        return "garbage_flood"
    # cascade backfire: the champion cleared into its own death -- a resolve on
    # the final ply that dropped material back into the spawn lane
    if last["cleared"] > 0 and last["chain"] >= 2:
        return "cascade_backfire"
    # garbage flood: sustained external pressure rather than self-inflicted
    if gin >= max(2, n):
        return "garbage_flood"
    # forced overstack: its options collapsed before the board did. Measured on
    # the last ply with a REAL legal count -- at a death-by-delivery ply the
    # count is 0 by definition, and using it would make this fire on every kill.
    real = [t for t in trace if not t.get("died_on_delivery")]
    if len(real) >= 2:
        lo, hi = real[-1]["legal"], real[0]["legal"]
        if lo <= 4 and hi >= 2 * max(1, lo):
            return "forced_overstack"
    # colour starvation: material it could never match kept accumulating
    if last["stranded"] >= 4 and last["stranded"] > trace[0]["stranded"]:
        return "colour_starvation"
    return "spawn_congestion"


def descriptor(E, board, v_left, v_start, trace):
    reg, col = region_of(board)
    return {
        "escape_bin": escape_bin(E),
        "region": reg,
        "block_col": int(col),
        "mechanism": mechanism_of(trace),
        "virus_bin": virus_bin(v_left, v_start),
    }


def cell_key(d):
    return (d["escape_bin"], d["region"], d["mechanism"], d["virus_bin"])


def total_cells():
    return len(ESCAPE_BINS) * len(REGIONS) * len(MECHANISMS) * len(VIRUS_BINS)


def all_cells():
    for e in ESCAPE_BINS:
        for r in REGIONS:
            for m in MECHANISMS:
                for v in VIRUS_BINS:
                    yield (e, r, m, v)
