#!/usr/bin/env python3
"""One full Dr. Mario game where the REAL RTL makes every placement decision.

Division of labour, stated precisely because it is the whole point of this lane:

  RTL (CoproDrMario.sv + LeafEval.sv + copro6502.v, verilated)
      chooses the placement. Every placement. There is no Python decider, no
      fallback, no "if the search looks wrong do X". If the co-sim fails, the game
      raises.

  Faithful sim (drmario.faithful_game / faithful_env)
      owns everything that is NOT a decision: virus layout, gravity, clear
      resolution, cascades, spawn-blocked detection, and the pill stream.

The pill stream is the REAL NES capsule generator (experiments/nes_pills.NesPillSource),
not faithful_env's uniform `_rand_pill`, because adjacent-capsule correlation is exactly
what a placement planner exploits (see nes_pills.py's own docstring).

APPLYING THE DECISION
---------------------
The copro publishes four bytes: best_col ($5085), best_orient o4 ($5086), tuck approach
column ($5087, 0xFF = none), tuck trigger row ($5088, raw board row, 0 = top).

Whether the last two do anything is a property of the CART, not the core, and it was
checked rather than assumed. `roms/manifests/latch-converged-native-probe.json` records
the exact flag set the deployed probe cart was built with; `DRTUCK` is not in it, and
`patch_cartridge_copro.py` at that manifest's own commit (b3b9b402, emitter md5
661ffa62 -- matches the manifest byte-for-byte) defaults `DRTUCK` to "0", which compiles
the tuck executor out entirely. **The deployed cart therefore never reads $5087/$5088:
it steers to best_col and plain-drops.** Two execution modes exist here for that reason:

  exec="drop"  (DEFAULT, silicon-faithful)
      Always a plain drop to (best_col, best_orient), through the faithful env's own
      `step()` -- its validated physics, not a reimplementation. This is what the cart
      that ran the physical s20b-vs-s20t3 A/B actually does.

  exec="tuck"  (counterfactual)
      Honours the descriptor: the pill rests strictly deeper than a plain drop (the
      firmware's CANDLIST admission rule guarantees `rf > straight_drop`), so `step()`
      cannot express it; the resting row is recovered by falling from the published
      trigger row and the two cells are written directly -- the same mutation
      `firmware_tier3_ab.py` performs for its tuck arm. `fall_from()` is gated against
      the faithful sim's own `resting_position()` in gate_validate.py, so it is validated
      physics rather than a second opinion. The approach column is deliberately unused:
      it decides whether the maneuver is *executable* on silicon, not where the pill ends
      up. Use this to price what a DRTUCK=1 cart would buy -- not to describe today's.
"""
from __future__ import annotations

import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
RL = "/home/struktured/projects/dr_mario_rl"
QA = "/home/struktured/projects/dr-mario-qa-wt/experiments"
# bursty_model lives in eval47/, not experiments/ directly -- same sys.path shape
# firmware_tier3_ab.py uses for its own pressure arm.
QA47 = QA + "/eval47"
for _p in (HERE, RL + "/.claude/worktrees/faithful-sim/src", QA, QA47):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from cosim import Cosim, CosimError, board_to_nes, VAR_OF_O4  # noqa: E402

ROWS, COLS = 16, 8
NO_TUCK = 0xFF

# RTL o4 -> tuck "ring" orientation (0=H, 1=V, 2=RH, 3=RV), from tuck_v3.py's
# O4_TABLE = [2,1,3,0] read backwards. Cross-checked against VAR_OF_O4 (recovered
# independently, from the pinned RTL node corpus): the two agree on all four codes --
# ring H/RH <-> a horizontal variant and ring V/RV <-> a vertical variant, with the
# same colour order. gate_validate.py asserts that agreement rather than trusting it.
RING_OF_O4 = (3, 1, 0, 2)
RING_IS_H = (True, False, True, False)
RING_FLIP = (0, 1, 1, 0)          # 1 => cell0 takes colour b (tuck_enum._FLIP)


def fall_from(color, col, ring, start_row):
    """Resting anchor row for a pill entering column `col` at anchor row `start_row`.

    Anchor convention matches translate_ref.py: the BOTTOM cell for a vertical pill, the
    LEFT cell for a horizontal one. Returns None if the entry row is itself blocked.
    """
    is_h = RING_IS_H[ring]

    def blocked(r):
        if r < 0 or r >= ROWS:
            return True
        if color[r, col] != 0:
            return True
        if is_h:
            if col + 1 >= COLS or color[r, col + 1] != 0:
                return True
        else:
            if r - 1 < 0 or color[r - 1, col] != 0:
                return True
        return False

    if blocked(start_row):
        return None
    r = start_row
    while not blocked(r + 1):
        r += 1
    return r


def cells_of(ring, col, rest):
    if RING_IS_H[ring]:
        return (rest, col), (rest, col + 1)
    return (rest - 1, col), (rest, col)


def apply_tuck(board, ring, col, rest, ca, cb):
    """Write the two capsule halves + their link nibbles, exactly as
    firmware_tier3_ab.py does for its tuck arm."""
    from drmario.faithful_game import LINK_LEFT, LINK_RIGHT, LINK_UP, LINK_DOWN
    (r0, c0), (r1, c1) = cells_of(ring, col, rest)
    col0, col1 = (cb, ca) if RING_FLIP[ring] else (ca, cb)
    board.color[r0, c0] = col0
    board.color[r1, c1] = col1
    if r0 == r1:
        board.link[r0, c0] = LINK_RIGHT
        board.link[r1, c1] = LINK_LEFT
    else:
        board.link[r0, c0] = LINK_DOWN
        board.link[r1, c1] = LINK_UP
    board.is_virus[r0, c0] = False
    board.is_virus[r1, c1] = False


def col_heights(color):
    """Stack height of every column (0 = empty; row 0 = top, so height = ROWS - top
    occupied row). READ-ONLY observation used by the latency capture below -- its
    result never feeds a decision."""
    out = []
    for c in range(COLS):
        h = 0
        for r in range(ROWS):
            if color[r, c] != 0:
                h = ROWS - r
                break
        out.append(h)
    return out


def col_occupancy(color):
    """Occupied cell COUNT per column. Diagnostic only -- see garbage_hit_h on why
    NO board-difference quantity, occupancy included, may source the hit set."""
    return [sum(1 for r in range(ROWS) if color[r, c] != 0) for c in range(COLS)]


def garbage_hit_h(h_before, cols):
    """h for the window formula W = 264 - 16*h; -1 only if no column was targeted.

    MIN over the volley's columns, of the PRE-garbage heights. Both choices are
    load-bearing and both were wrong before #124, as was the source of `cols` --
    see play_game's docstring. Named so test_gw_hhit.py can gate and mutate it.

    ★ `cols` MUST be the volley's own column set, re-derived from the model, and NOT
    inferred from a board difference. Every inference -- height delta or occupancy
    delta alike -- is wrong in a way that does not announce itself: if garbage lands
    in column c and c then CLEARS, it grows in neither height nor occupancy and is
    silently dropped from a still-non-empty hit set, so the min is taken over the
    survivors and the answer looks perfectly reasonable. That error concentrates in
    clear-triggering volleys, i.e. precisely the releases with the LONGEST windows,
    so it biases hardest where it matters most. (Height delta additionally over-
    includes: a clear elsewhere settles an unhit column. Occupancy delta fixes only
    that half -- which is why "occupancy growth" was not good enough either.)

    A column the injector SKIPPED (full to row 0) is harmless in `cols`: skipping
    requires h_before == ROWS, the maximum, which can never lower a min. It would
    corrupt a max -- one more reason the min form is the right shape."""
    return min(h_before[c] for c in cols) if cols else -1


GARBAGE_MIN_PILLS = 25          # reach_root_ab.GARBAGE_MIN_PILLS, not re-chosen here
DIES_AHEAD_VIRUS_THRESHOLD = 12  # reach_root_ab.DIES_AHEAD_VIRUS_THRESHOLD


def play_game(cosim: Cosim, seed: int, level: int = 11, max_pills: int = 300,
              trace: bool = False, exec_mode: str = "drop",
              pressure: str = "clean", model=None):
    """Play one game. Returns a result dict; raises CosimError if the RTL fails.

    exec_mode: "drop" = the deployed cart's behaviour (descriptor ignored);
               "tuck" = honour the published tuck descriptor.
    pressure:  "clean"  = no garbage. The champion has ~0 failures on a clean L11
                          stream (1,474-game census), so a clean arm measures SPEED
                          (pills-to-clear), not survival.
               "bursty" = the project's fitted volley model (bursty_model), injected on
                          the player's own clears exactly as reach_root_ab/
                          firmware_tier3_ab do. This is where survival differences live.

    LATENCY CAPTURE (report-only). Every result dict carries "lat": one entry per
    decision, `[clocks, entry_row, max_h, post_garbage, h_hit]`:

      clocks        raw co-sim clocks for this single decide() -- the per-decision
                    value that used to be summed into `clocks` and discarded. Stored
                    RAW on purpose: the verilated sim ticks clk and clk_cpu in
                    lockstep (48 master clocks per NES CPU cycle) while real silicon
                    runs the copro on its own 54.669 MHz async tap, so conversion
                    belongs at ANALYSIS time, reporting BOTH domains:
                    silicon frames = clocks/909,650 (54.669e6/60.0988) and
                    sim-lockstep frames = clocks/(48*29780.5).
      entry_row     resting anchor row of the placement actually made (bottom cell
                    for vertical, the row for horizontal; row 0 = top). -1 when no
                    placement was applied (the illegal-placement topout path).
      max_h         max column stack height of the board the decision was made ON
                    (before this pill was placed) -- prices the fall-time budget
                    (13 frames/row at L11).
      post_garbage  1 iff this decision immediately follows a bursty garbage
                    injection, i.e. it sits at the release+settle edge where the
                    264 - 16*h frame window applies. Always 0 under pressure="clean".
                    It is its OWN flag and is NOT `h_hit >= 0`: a release whose hit
                    columns cannot be identified is still a release, and collapsing
                    the two would drop it from the denominator.
      h_hit         when post_garbage=1: the MINIMUM PRE-GARBAGE stack height over
                    the volley's own target columns; -1 when post_garbage=0.
                    W = 264 - 16*h_hit.

                    ⚠ THIS FIELD WAS WRONG IN THREE WAYS UNTIL 2026-08-19 (#124), and
                    every "% of releases" figure computed from it before that date is
                    invalid -- conservatively so, the true windows are LONGER. Do not
                    mix pre- and post-fix jsonl. The three, all on one line:

                      1. it took the MAX over hit columns. A garbage tile spawns at
                         row 0 and falls 15 - h to rest on its column's stack, so the
                         animation ends when the tile falling FURTHEST lands -- the
                         one in the SHALLOWEST hit column. The tallest hit column has
                         the shortest fall and binds nothing.
                      2. it sampled heights AFTER the garbage settled. h_after is
                         h_before plus the tiles that just landed there, so every hit
                         column was over-counted by >= 1 => W understated by >= 16 f,
                         compounding with (1). The window is set by the stack the tile
                         falls ONTO.
                      3. the hit set was INFERRED FROM THE BOARD -- columns whose
                         height changed -- with a fallback of max() over ALL columns
                         when that came up empty. The empty case is the loud one; the
                         dangerous case is a NON-EMPTY WRONG set, which never triggers
                         the fallback and yields a plausible number silently. Garbage
                         that lands and then clears leaves its column unchanged and
                         drops the binding column; a clear elsewhere settles a column
                         that was never hit and adds it. Both can happen in one volley.
                         The set now comes from the volley's own model.sample() draw,
                         so no inference is involved at all.

                    (1) and (2) agree only on a flat stack where every column has the
                    same height, which is exactly why synthetic flat boards never
                    exposed either. (3) is invisible on any board where nothing clears,
                    and it concentrates in clear-triggering volleys -- the releases
                    with the LONGEST windows, so it biases hardest where it matters.
                    Reference for (1) and (2), independently written:
                    experiments/gw_design/screen_gw.py:362.

                    ⚠ SEPARATE AND STILL OPEN (fidelity, not correctness): the model
                    draws random DISTINCT columns, while the ROM uses maximally spread
                    sets -- {c,c+4}, {c,c+2,c+4}, {c,c+2,c+4,c+6} per checkReleaseAttack
                    ($9C01, Rev 0). A spread set straddles the board and finds a
                    shallower column more often, so real h_min is LOWER and real windows
                    LONGER than even a corrected farm will show. Filed separately; do
                    not fold it in here.

    Nothing in the capture feeds back into any decision -- it is pure observation,
    and gate_validate.py's determinism key (result, pills, viruses_cleared, clocks,
    moves) is untouched because the field is additive.
    """
    if exec_mode not in ("drop", "tuck"):
        raise ValueError("exec_mode must be 'drop' or 'tuck'")
    if pressure not in ("clean", "bursty"):
        raise ValueError("pressure must be 'clean' or 'bursty'")
    import numpy as np
    from drmario.faithful_env import FaithfulDrMarioEnv
    from nes_pills import NesPillSource
    if pressure == "bursty":
        from bursty_model import inject_bursty_garbage

    env = FaithfulDrMarioEnv(level=level, seed=seed, max_pills=max_pills)
    env.reset()
    NesPillSource(seed=seed).attach(env)
    env.cur = env._rand_pill()
    env.nxt = env._rand_pill()

    start_viruses = env.board.virus_count()
    res = "stall"
    n_tuck = 0             # tucks actually EXECUTED (always 0 when exec_mode == "drop")
    n_tuck_published = 0   # descriptors the copro published, executed or not
    n_incoherent = 0       # published but UNPERFORMABLE (see below)
    n_illegal = 0
    garbage = 0
    clocks = 0
    moves = []
    lat = []               # per-decision latency capture, see the docstring
    pending_pg = 0         # 1 iff the NEXT decision sits at a release+settle edge
    pending_gh = -1        # min PRE-garbage height over the hit columns; -1 = unknown

    for _ in range(max_pills):
        if env.board.virus_count() == 0:
            res = "clear"
            break
        b128 = board_to_nes(env.board)
        # Faithful-sim Pill colours are 1..3; the copro mailbox takes 0..2. Keep both:
        # ca/cb (1-based) are what apply_tuck writes into the board, ca0/cb0 (0-based) are
        # what the copro is told. Cosim.decide() range-checks the 0-based pair.
        ca, cb = int(env.cur.a), int(env.cur.b)
        na, nb = int(env.nxt.a), int(env.nxt.b)
        d = cosim.decide(b128, ca - 1, cb - 1, na - 1, nb - 1)
        clocks += d["clocks"]
        # Latency capture: record the per-decision cost with the board it was paid on.
        # entry_row (slot 1) is back-filled once the placement is known; it stays -1
        # only on the illegal-placement path, where nothing is applied.
        lat.append([int(d["clocks"]), -1, max(col_heights(env.board.color)),
                    pending_pg, pending_gh])
        pending_pg, pending_gh = 0, -1
        col, o4, tcol, trow = d["col"], d["o4"], d["tcol"], d["trow"]
        if trace:
            moves.append((col, o4, tcol, trow))
        if tcol != NO_TUCK:
            n_tuck_published += 1

        occ_before = int(np.count_nonzero(env.board.color)) if pressure == "bursty" else 0

        do_tuck = (tcol != NO_TUCK and exec_mode == "tuck")
        rest = None
        if do_tuck:
            rest = fall_from(env.board.color, col, RING_OF_O4[o4], trow)
            if rest is None:
                # INCOHERENT descriptor: the pill cannot enter best_col at the published
                # trigger row, so the maneuver is unperformable. Measured on real L11
                # boards, 15 of 26 tuck-v1 descriptors are like this (descriptor_audit.py)
                # -- v1 enumerates over ALL target columns and keeps the globally deepest
                # rest, while the driver takes its destination from best_col, so the two
                # need not describe the same column.
                #
                # Modelled as degrading to a plain drop at best_col. That is CONSERVATIVE:
                # on silicon the pill keeps falling wherever the DAS hold left it and can
                # land in a different column entirely, i.e. worse than modelled here.
                # Counted separately so this fallback can never hide inside the tuck rate.
                n_incoherent += 1
                do_tuck = False

        if do_tuck:
            lat[-1][1] = int(rest)
            apply_tuck(env.board, RING_OF_O4[o4], col, rest, ca, cb)
            env.board.resolve()
            n_tuck += 1
            env.pills_placed += 1
            if env.board.virus_count() == 0:
                res = "clear"
                break
            if env.board.spawn_blocked():
                res = "topout"
                break
            env.cur = env.nxt
            env.nxt = env._rand_pill()
            if not env.action_masks().any():
                res = "topout"
                break
        else:
            action = VAR_OF_O4[o4] * COLS + col
            orient, acol, pill = env._decode(action)
            rcells = env.board.resting_position(pill, orient, acol)
            if rcells is None:
                # The RTL named a placement that does not fit. On silicon the driver
                # would fail to seat the pill and the stack tops out; scoring it as a
                # topout is the faithful outcome, and it is counted separately so a
                # harness bug could never hide inside the topout rate.
                n_illegal += 1
                res = "topout"
                break
            lat[-1][1] = int(rcells[1][0])
            _, _, term, trunc, info = env.step(int(action))
            if term:
                res = "clear" if info["won"] else "topout"
                break
            if trunc:
                break

        if pressure == "bursty" and env.pills_placed >= GARBAGE_MIN_PILLS:
            occ_after = int(np.count_nonzero(env.board.color))
            clear_size = max(0, occ_before + 2 - occ_after)
            if clear_size > 0:
                h_before = col_heights(env.board.color)
                gp = env.pills_placed          # bound so the re-sample below cannot
                                               # drift from the injector's own draw
                added = inject_bursty_garbage(
                    env.board, model, seed, gp, clear_size)
                garbage += added
                if added > 0:
                    # Release+settle edge: the NEXT decision is made inside the
                    # 264 - 16*h_hit garbage window. See the docstring for the three
                    # ways this was wrong before #124.
                    #
                    # The column set comes from a SECOND model.sample() call, not from
                    # any board difference. That is free and side-effect-free: sample()
                    # builds a fresh random.Random(seed*1000 + pills_placed) locally,
                    # reads only the immutable size pool, and holds no instance RNG
                    # state -- verified deterministic across interleaved calls. The
                    # injector made this exact call with these exact arguments, so the
                    # two draws are the same volley by construction rather than by
                    # reconstruction.
                    _n_cells, gcols = model.sample(seed, gp)
                    pending_pg = 1
                    pending_gh = garbage_hit_h(h_before, gcols)
            if env.board.virus_count() == 0:
                res = "clear"
                break
            if env.board.spawn_blocked():
                res = "topout"
                break

    viruses_left = env.board.virus_count()
    out = {
        "seed": seed, "level": level, "result": res,
        "won": int(res == "clear"), "topout": int(res == "topout"),
        "stall": int(res == "stall"),
        "pills": env.pills_placed,
        "start_viruses": start_viruses,
        "viruses_left": viruses_left,
        "viruses_cleared": start_viruses - viruses_left,
        "dies_ahead": int(res == "topout" and viruses_left <= DIES_AHEAD_VIRUS_THRESHOLD),
        "n_tuck": n_tuck, "n_tuck_published": n_tuck_published,
        "n_incoherent": n_incoherent, "n_illegal": n_illegal,
        "garbage": garbage,
        "clocks": clocks,
        "lat": lat,
        "exec_mode": exec_mode, "pressure": pressure,
        "fw_md5": cosim.fw_md5,
    }
    if trace:
        out["moves"] = moves
    return out
