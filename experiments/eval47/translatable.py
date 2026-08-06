#!/usr/bin/env python3
"""Translatability predicate for the #17-unified reachable-root reconciliation rig.

WHY THIS EXISTS. reach_root.py's reachfull/reachfull2 arms score every BFS-reachable
tuck-class candidate (tuck_enum.py, mode="free") as if it were unconditionally
executable. It isn't: the real firmware only fires a tuck by publishing a single-
adjacent-column (approach, trigger) descriptor to the driver's steering mailbox
(TUCK_COL/TUCK_ROW) via tuck_v3.py's CANDLIST -- and dr-mario-canonical-wt's
tuck-bfs-6502 branch measured that only ~11% of BFS-reachable tuck candidates HAVE such
a descriptor (median 2 of 36 raw candidates/board survive; see TUCK_BFS_PORT_REPORT.md
section 8.1). This module exposes that same accept/reject boundary to this rig so
reconciliation can score the REAL executable set, not the full reachable one.

EXECUTABLE SET, the composition rule the rig arm should use:

    executable_set = straight_drops UNION {tuck-class candidates : translatable}

Straight drops (the base-32 (variant, col) family `fast_sim_x._expand_core` enumerates)
bypass CANDLIST entirely -- they are the search's native action space and are always
directly executable, independent of anything in this module. The translatability
predicate below is a gate ONLY for tuck-class candidates (`is_tuck=True` in tuck_enum.py's
own dicts, i.e. TE.enumerate(...)'s "reachfull"-style output already used throughout
reach_root.py). `is_straight_drop()`/`executable()` below encode this split explicitly so
callers don't have to re-derive it.

WRAPS, does not re-derive: dr-mario-canonical-wt/tests/translate_ref.py's already-
validated CANDLIST derivation (0/732 mismatches vs tuck_scan_v3_ref.py's own uncapped
rule on 400 random boards; the ACTUAL 6502 firmware chain matched this reference exactly
on 50/50 real L11 corpus boards -- see TUCK_BFS_PORT_REPORT.md section 8.2/8.4 on that
branch). Only the board representation differs at the boundary and is converted once,
at the top of is_translatable() -- nothing in translate_ref.py's logic is touched, copied,
or reimplemented here.

BOARD/CANDIDATE CONVENTIONS. This module speaks reach_root.py's own house conventions
(its module docstring, verified there, not re-verified here): `col` is a row-major
NCELL=128 int8 array (or any 128-length sequence), idx = r*8+c, colours 1-based, 0=empty.
Candidates are tuck_enum.py-style dicts (or bare (col, row, orient) tuples) carrying at
least 'col' (target column), 'row' (rest row), 'orient' (0=H,1=V,2=RH,3=RV) -- exactly
what `TE.enumerate(fb, ca, cb, mode="free")` and reach_root.py's own `tuck_cands` lists
already produce, so callers pass those dicts straight through without reshaping them.

translate_ref.py's OWN convention (matching primitives.py / the real 6502 firmware's
NES-tile board representation) uses EMPTY=0xFF as the empty-cell sentinel instead of 0.
`_to_nes_board()` is the one-line adapter; the colour VALUE written for occupied cells
doesn't matter to the derivation (only empty/non-empty is ever tested), so passing the
1-based colour straight through as the "tile byte" is correct -- the same convention
tuck_bfs_6502.py's own test harnesses use (fb_to_nes()).
"""
from __future__ import annotations

import sys
import os

CANON = "/home/struktured/projects/dr-mario-canonical-wt"
_TESTS = os.path.join(CANON, "tests")
if _TESTS not in sys.path:
    sys.path.insert(0, _TESTS)
import translate_ref as TR  # noqa: E402  -- the validated derivation; wrapped, not re-derived

_EXPERIMENTS = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _EXPERIMENTS not in sys.path:
    sys.path.insert(0, _EXPERIMENTS)
import tuck_enum as TE  # noqa: E402  -- ground truth for tier 3-5 (its own BFS parent

EMPTY_NES = 0xFF
ROWS, COLS, NCELL = 16, 8, 128


def _to_nes_board(col):
    """reach_root.py convention (0=empty, 1..3=colour) -> translate_ref.py convention
    (EMPTY=0xFF sentinel, occupied=colour byte). Accepts a numpy int8 array or any
    128-length sequence; always returns a plain list of Python ints (translate_ref.py's
    own functions index it with plain int arithmetic, no numpy dependency)."""
    return [EMPTY_NES if int(c) == 0 else int(c) for c in col]


def _unpack(candidate):
    """candidate -> (target, rest, orient) as plain ints. Accepts a tuck_enum.py-style
    dict ('col'/'row'/'orient' keys) or a bare (col, row, orient) tuple/list."""
    if isinstance(candidate, dict):
        return int(candidate["col"]), int(candidate["row"]), int(candidate["orient"])
    target, rest, orient = candidate
    return int(target), int(rest), int(orient)


def is_straight_drop(candidate):
    """True iff `candidate` is a base-32 (variant, col) straight drop rather than a
    tuck-class placement -- i.e. it bypasses CANDLIST entirely and is always executable
    without consulting is_translatable() at all. Recognises reach_root.py's own two
    candidate shapes: a `{"kind": "base"/"tuck", ...}` root-choice dict (choose_base32/
    choose_reachfull's return value) or a raw tuck_enum.py placement dict (`is_tuck`
    key, as found in TE.enumerate()'s output / reach_root.py's own `tuck_cands` lists)."""
    if isinstance(candidate, dict):
        if "kind" in candidate:
            return candidate["kind"] == "base"
        if "is_tuck" in candidate:
            return not candidate["is_tuck"]
    raise ValueError(f"is_straight_drop: unrecognised candidate shape {candidate!r}")


def precompute_visited(col):
    """Precompute the BFS visited plane for a board once, to pass into repeated
    is_translatable()/executable() calls across many candidates on that SAME board --
    the visited-plane computation (translate_ref.row_bfs_visited) is the dominant cost
    per call and does not depend on the candidate, only the board."""
    return TR.row_bfs_visited(_to_nes_board(col))


def is_translatable(col, candidate, visited=None):
    """True iff `candidate` (a tuck-class placement -- see module docstring for the
    accepted shapes) would survive the real 6502 CANDLIST translation: a valid,
    BFS-visited-verified single-adjacent-column (approach, trigger) descriptor exists
    for it in tuck_scan_v3's motion vocabulary. Only meaningful for tuck-class
    candidates; straight drops don't need this gate (see is_straight_drop/executable).

    `visited`: optional, from precompute_visited(col) -- pass it when checking many
    candidates on the same board to skip recomputing the visited plane each call."""
    target, rest, orient = _unpack(candidate)
    board = _to_nes_board(col)
    if visited is None:
        visited = TR.row_bfs_visited(board)
    return TR.derive_verified(board, target, rest, orient, visited) is not None


def executable(col, candidate, visited=None):
    """The rig arm's composition rule, as a per-candidate predicate:
    executable_set = straight_drops UNION {tucks : translatable}.
    A candidate is executable iff it's a base-32 straight drop (always executable) OR
    it's a tuck-class candidate with a verified CANDLIST descriptor."""
    if is_straight_drop(candidate):
        return True
    return is_translatable(col, candidate, visited=visited)


# ============================================================================
# EXECUTABILITY TIERS (task #67, 2026-08-05): the reconciliation gate found the
# pressure win COLLAPSES to today's executable subset (reachexec bad-ends 30/120 ~=
# base32's 32, vs the full-set oracle's 18, p=0.036) -- the deep tuck candidates
# is_translatable() gates OUT are exactly the ones saving games under pressure. This
# section exposes a RECOVERY CURVE: a monotone ladder of progressively general
# execution models, so the silicon session can buy exactly as much vocabulary as the
# win curve justifies, not all-or-nothing.
#
# tier_fn CONTRACT (matches reach_root.py's `_stub_tier_of` placeholder exactly, so
# `tier_fn=translatable.tier_of` is a drop-in swap for the sweep harness -- see
# reach_root.py's `choose_reach_tier`/`_stub_tier_of` docstrings, READ but not edited
# here): `tier_of(col, candidate) -> int`, lower = cheaper/narrower, and
# `tier_of(col,p) <= 1  <=>  is_translatable(col,p)` must hold EXACTLY (the stub's own
# endpoint guarantee: `tier_fn(col,p)<=1` must reproduce `TL.executable`'s tuck branch
# bit-for-bit). This is why NOT-REACHABLE-AT-ALL cannot be tier 0 -- it has to sort
# ABOVE every real tier (see TIER_UNREACHABLE below), otherwise `tier<=1` would wrongly
# accept unreachable candidates that `is_translatable` correctly rejects.
#
# THE LADDER (5 tiers; monotonicity of {c : tier_of(c) <= N} is guaranteed BY
# CONSTRUCTION -- tier_of tests the tiers 1..5 in strictly increasing generality and
# returns the FIRST that accepts, so a smaller returned tier can never fail to satisfy
# `<= N` for any N at or above it; see the "monotonicity guarantee" note on tier_of
# itself for why this holds regardless of whether each tier's own raw acceptance set
# happens to nest inside the next):
#
#   TIER 1 -- today's shipped vocabulary. EXACTLY is_translatable(): a single
#   adjacent-column (target-1 or target+1) approach, one ascending-bounded trigger
#   row (tuck_scan_v3's own fc..ra range), BFS-visited-verified. Cost: $0 -- this is
#   what's already in tuck_bfs_translate_6502.py (612B/92 labels, shipped on
#   tuck-bfs-6502). MUST stay bit-identical to today's is_translatable; this is the
#   sweep's endpoint-reproduction self-test's foundation.
#
#   TIER 2 -- two-column approach, UNBOUNDED trigger row. Same target-1/target+1
#   approach-column restriction as tier 1, but the trigger-row search is not bounded
#   by first_occ(approach) (translate_ref.py's own docstring names this exact bound
#   as a known over-approximation in the shipped rule) -- instead every row is
#   accepted iff the approach's (approach,row,orient) entry state is itself
#   BFS-visited, the genuine reachability test. This provably WIDENS tier 1 alone:
#   tier 1's own derive_verified() already requires that same visited check on its
#   result, so anything tier 1 accepts, tier 2's unbounded row scan finds too.
#   Cost estimate (gut-level, informed by porting tr_try_vert/tr_try_horiz): reuses
#   the SAME subroutine shape already built for tier 1, just widens the trigger-row
#   loop bound to ROWS-1 and swaps the "empty down to depth" gate for a
#   tb_vis_test(approach,row,orient) call against the bitplane the BFS phase already
#   leaves resident -- no new RAM, roughly +40-80 bytes of code. Cheapest non-zero
#   step on the ladder.
#
#   TIER 3 -- single direction-change paths. Approach column is UNRESTRICTED (any of
#   0..7, not just target+-1); accepted iff tuck_enum.py's own free-mode BFS path to
#   the (target,rest,orient) resting state has AT MOST ONE reversal among its lateral
#   (Left/Right) moves -- a player/driver steering one broad way, changing their mind
#   at most once, with rotates and the fall itself unconstrained. This is "what a
#   simple D-pad sweep can execute."
#   Cost estimate: answering "is there a <=1-direction-change path" is NOT just the
#   existing visited bitmask -- either (a) 2 extra bits/state during the BFS closure
#   (last lateral direction + a saturating change counter: ~128B of new RAM packed
#   across the existing 512-state space) or (b) a second, direction-constrained
#   closure pass reusing the same row-fixed-point machinery. Rough estimate:
#   +150-250B code, +~128B RAM -- a genuinely new pass, not a tweak to tier 1/2's.
#
#   TIER 4 -- bounded-length path playback. The path-shape constraint drops entirely;
#   accepted iff the STEERING length (lateral + rotate moves; falls/"Down" excluded,
#   since gravity is automatic in the real game and free-mode's per-row Down edges
#   are a BFS-graph artefact, not a player action) of tuck_enum's shortest free-mode
#   path is <= TIER4_MAX_STEER (see that constant's own docstring for how it was set
#   from this module's corpus measurement). "The BFS parent chain IS the move script"
#   -- the driver would literally walk tuck_enum's own pred chain and replay it.
#   Cost estimate: the biggest lift on the ladder. Needs the 6502 BFS to retain
#   PARENT POINTERS per visited state, not just a visited bit -- roughly 1 byte/state
#   (2-bit move kind + predecessor offset) x up to 512 states = up to 512B of NEW RAM
#   (more than doubling tuck_bfs_6502.py's current ~448B footprint), plus a replay
#   routine (~100-150B) walking the chain and feeding the driver's input queue in
#   order. Flagged as needing its own capacity/RAM audit before committing to it, not
#   priced as free.
#
#   TIER 5 (MAX) -- unbounded playback = the full BFS-reachable set, no path-shape or
#   length constraint at all: exactly what tuck_bfs_6502.py's existing BFS already
#   computes (bit-exact vs tuck_enum.py mode="free", 200/200 -- see
#   TUCK_BFS_PORT_REPORT.md section 3 on the tuck-bfs-6502 branch) and, by that
#   already-established bit-exact equivalence, exactly what
#   `translate_ref.row_bfs_visited`'s own plane agrees with. Cost estimate: NOT a
#   firmware/enumeration cost -- the bitplane is already computed before any
#   translation step runs. The open question is entirely on the DRIVER/input-model
#   side: can the real frame-by-frame input pipeline execute an arbitrarily long,
#   possibly-backtracking move sequence within the frames available before the pill
#   locks? That's a feasibility question, not a byte count, and is left OPEN here
#   rather than priced.
# ============================================================================

MAX_TIER = 5
TIER_UNREACHABLE = 99  # sorts above every real tier; see the CONTRACT note above for
                        # why "not reachable at all" cannot be tier 0

# Steering-length bound for tier 4, in NON-Down moves (Left/Right/Rotate presses).
#
# HONEST STATUS: tier 4 is UNEXERCISED by every corpus checked so far -- validate_
# tiers.py's run over the 200-board real-L11 corpus (1490 tuck candidates) AND a
# separate pass over the synthetic 110-candidate overflow_board.json (80 tuck
# candidates, deliberately denser/more adversarial) both come back with 0 hits at
# tier 4 and tier 5: every candidate that fails tier 1/2 already has <=1 direction
# change (tier 3 absorbs it). So there is currently no candidate anywhere in this
# module's test data whose classification actually depends on this constant's value
# -- do not read the number below as corpus-fit; it isn't.
#
# What IS measured (pooled across both corpora, so at least grounded in something
# real): of the 66 candidates with >=2 direction changes -- the population tier 4
# would eventually need to discriminate within, once boards exist that don't get
# fully absorbed by tier 1/2/3 first -- steering length ranges min=4 to max=23,
# median=17, p90=21. The ones at the LOW end (4-9) all turned out to already have a
# valid tier-1/2 descriptor anyway (short paths tend to correlate with a simple
# adjacent-column tuck existing), so they never actually reach this check either.
# TIER4_MAX_STEER=12 is a provisional midpoint between that absorbed low cluster
# (<=9) and the unexercised tail's median (17) -- not a measured knee, since there
# is no knee to measure yet. The sweep should treat this as the first thing to
# recalibrate once it runs over boards deep/dense enough to actually produce a
# tier-4-classified candidate (deeper levels, near-endgame low-virus-count boards,
# and multi-well cave boards are the likeliest source, going by which corpus entries
# had the highest direction-change counts here). A tunable, not a physical constant.
TIER4_MAX_STEER = 12


def _derive_tier2(board, target, rest, orient, visited):
    """Tier-2 derivation: same target-1/target+1 approach-column restriction as
    translate_ref.derive_vert/derive_horiz (tier 1), but the trigger-row search is
    NOT bounded by first_occ(approach) -- translate_ref.py's own module docstring
    names that bound as a known, pre-existing over-approximation in the shipped v1/v3
    rule ("tuck_scan_v3's own rule uses ONLY first_occ(approach) as its depth bound
    ... it does NOT verify the approach column is actually REACHABLE at that shallow
    row"). This closes that gap directly: every row 0..ROWS-1 is tried, gated on the
    approach entry state being itself BFS-VISITED (the real reachability test) rather
    than merely empty down to a proxy depth. The final-rest-row projection and the
    "not secretly a straight drop" (`rf <= sd`) checks are otherwise identical to
    translate_ref's own rule, so this differs from tier 1 along exactly one axis."""
    board_ = board
    is_vert = orient in (1, 3)
    fc = (TR.first_occ(board_, target) if is_vert
          else min(TR.first_occ(board_, target), TR.first_occ(board_, target + 1)))
    if fc == 0:
        return None
    sd = fc - 1
    for a in (target - 1, target + 1):
        if is_vert:
            if not (0 <= a < TR.COLS):
                continue
        else:
            if a < 0 or a + 1 >= TR.COLS:
                continue
        for r in range(TR.ROWS):
            if not TR.visited_test(visited, a, r, orient):
                continue
            if is_vert:
                if TR.occ(board_, r, target):
                    continue
                if r - 1 < 0 or TR.occ(board_, r - 1, target):
                    continue
                rf = r
                while rf + 1 < TR.ROWS and not TR.occ(board_, rf + 1, target):
                    rf += 1
            else:
                if TR.occ(board_, r, target) or TR.occ(board_, r, target + 1):
                    continue
                rf = r
                while (rf + 1 < TR.ROWS and not TR.occ(board_, rf + 1, target)
                       and not TR.occ(board_, rf + 1, target + 1)):
                    rf += 1
            if rf != rest or rf <= sd:
                continue
            return (a, r)
    return None


def _free_path_for(col, target, rest, orient, candidate=None):
    """The free-mode BFS move-token path (list[str], e.g. ["Left","Down","Down",
    "RotB(+1)", ...]) tuck_enum.py's own reachability search recorded for reaching
    (target, rest, orient), or None if that resting state is not free-mode-reachable
    at all. Reuses `candidate['path']` directly when candidate is a dict already
    carrying it -- the expected shape per this module's own docstring (callers pass
    TE.enumerate(fb, ca, cb, mode="free")'s own dicts straight through) -- so the BFS
    only actually re-runs for the bare-tuple candidate shape, or a dict missing
    'path' for some other reason."""
    if isinstance(candidate, dict) and "path" in candidate:
        return candidate["path"]
    placements = TE.enumerate(col, 1, 1, mode="free")
    for p in placements:
        if (p["col"] == target and p["row"] == rest and p["orient"] == orient
                and p["reachable"]):
            return p["path"]
    return None


def _direction_changes(path):
    """Reversals within the LATERAL (Left/Right) subsequence of a free-mode path;
    rotates and falls don't count as a "direction" at all, so they never break up a
    lateral run. ["Left","Down","Left","RotB(+1)","Right"] -> 1 (one L-run then one
    R-run)."""
    lateral = [t for t in path if t in ("Left", "Right")]
    return sum(1 for i in range(1, len(lateral)) if lateral[i] != lateral[i - 1])


def _steer_len(path):
    """Path length EXCLUDING "Down" tokens -- see TIER 4's docstring above for why:
    gravity is automatic in the real game, so free-mode's one-Down-per-row graph
    edges measure board height, not steering complexity."""
    return sum(1 for t in path if t != "Down")


def tier_of(col, candidate):
    """Executability tier for a tuck-class `candidate` (see module docstring for the
    accepted shapes) -- lower is cheaper/narrower. Returns 1-5 (see the ladder
    documented above `MAX_TIER`) for anything free-mode-reachable, or
    TIER_UNREACHABLE for a candidate no execution model here can place at all.

    CONTRACT (see the section docstring above): `tier_of(col,p) <= 1` must be exactly
    `is_translatable(col,p)` -- this holds because tier 1 is tested FIRST and returns
    immediately on success, and the not-reachable case returns TIER_UNREACHABLE (99),
    never 0, so it can never satisfy `<= 1` the way a real translatable candidate does.

    Signature matches reach_root.py's `_stub_tier_of(col, candidate)` (2 positional
    args, no `visited`) so `tier_fn=translatable.tier_of` drops straight into
    `choose_reach_tier` in place of the stub -- see that file's own docstrings (READ,
    not edited, by agreement with whoever owns it mid-run). `is_translatable`'s own
    `visited` cache parameter is still available to OTHER callers that want it; this
    entry point recomputes it once internally per call to keep the 2-arg contract."""
    target, rest, orient = _unpack(candidate)
    board = _to_nes_board(col)
    visited = TR.row_bfs_visited(board)

    if TR.derive_verified(board, target, rest, orient, visited) is not None:
        return 1
    if _derive_tier2(board, target, rest, orient, visited) is not None:
        return 2

    path = _free_path_for(col, target, rest, orient, candidate)
    if path is None:
        return TIER_UNREACHABLE
    if _direction_changes(path) <= 1:
        return 3
    if _steer_len(path) <= TIER4_MAX_STEER:
        return 4
    return MAX_TIER
