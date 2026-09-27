#!/usr/bin/env python3
"""THE consolidated VS harness. ONE change, ONE rev stamp, ONE test suite.

★ EVERY RESULT FILE MUST RECORD `HARNESS_REV`. There are three generations of VS numbers
in this project's record (cells>=7 era, step-local-rule era, and this one) and the only
way to keep them straight is an explicit stamp. A number without a rev is unusable.

WHAT THIS ASSEMBLES -- five corrections that all landed 2026-07-31, every one of them
cited to the disassembly via `rom_attack_rule.py` (opening-book, task #12) or traced here:

  1. TRIGGER = sum of matched runs over the WHOLE cascade >= 2.
     `currentP_comboCounter` increments per matched run (game_logic.asm:1176/:1623), is
     never reset inside the cascade loop (@finishedUpdatingField :1474-1485 re-enters
     checkDrop; resetMatchFlag :1495 clears only the flag), and is consumed once from a
     SINGLE call site -- action_checkAttack (:2859), a per-ACTION step, not per-step.
     ⇒ a cascade of two singles ATTACKS. The old `any(step >= 2)` had 14.9% recall.
  2. NO OFF-BY-2. vs_env measured occupancy(before)-occupancy(after) with the pill (+2)
     already placed, making its `>=7` test really `cleared >= 9` -> 23.5% recall.
     ★ For the record: `cells >= 7` AS DOCUMENTED was ROM-true all along (99.9% precision,
     100% recall over 6078 clears). The documented proxy was right; the IMPLEMENTATION was
     wrong. My original "the proxy over-counts on cascades" critique was itself incorrect --
     cascades SHOULD fire. Kept here because getting this backwards cost a sizing verdict.
  3. PAYLOAD accumulates and SATURATES. checkComboCounterForAttack adds comboCounter into
     the sender's attackSize; checkReleaseAttack releases it ONCE as 2/3/4 tiles and
     clears it (>=4 all deliver 4). Two attacks between a receiver's placements MERGE into
     one capped drop -- queueing them separately uncaps the ceiling and over-delivers.
  4. COLUMNS include {0,4}. Size-2 start is `frameCounter & 3`, stride 4 -> pairs
     {0,4}/{1,5}/{2,6}/{3,7}. Columns 0 and 4 are NOT immune, so "build through the immune
     columns" was never a real defence. Phase is keyed by (seed, volley ordinal) so that
     ablating one volley cannot reshuffle another's columns.
  5. ★ GRAVITY. `FaithfulBoard.resolve()` applies gravity only INSIDE its clear loop, so
     garbage forming no line was left FLOATING at row 0 -- which reads as a blocked spawn
     column and a bogus top-out. Settle first, THEN resolve. This defect was in vs_env and
     inflated every top-out rate this project has quoted.

ORDERING, from the nextAction jump table (:2817-2826): pillFalling -> pillPlaced ->
checkAttack. So per placement: PLACE+resolve, then bank our own combo as an attack, then
RECEIVE whatever the opponent had stored. Garbage therefore lands AFTER our placement, and
we cannot react to it until our next decision. Received garbage settles through the normal
cascade and CAN CLEAR AND COUNTER-ATTACK.
"""
from __future__ import annotations
import sys

ROOT = "/home/struktured/projects/dr_mario_rl"
for p in (ROOT+"/tmp/vs_aware", ROOT+"/tmp/champion", ROOT+"/tmp/combo_term",
          ROOT+"/tmp/pillrng", ROOT+"/.claude/worktrees/faithful-sim/src"):
    if p not in sys.path:
        sys.path.insert(0, p)

from vs_env import VsMatch                                    # noqa: E402
from attack import probe_placement, lines_per_step            # noqa: E402
from rom_attack_rule import (garbage_columns, combo_from_cascade,  # noqa: E402
                             attack_size, ATTACK_SIZE_MIN, stamp)

# Every one of opening-book's REQUIRED_MECHANICS is implemented below, so stamp() resolves
# to "(complete)". If a mechanic is ever dropped, remove it here and the stamp will name it
# as MISSING in every results file -- a half-upgraded harness cannot pass as complete.
_MECHANICS = ("tile_table_234", "column_phases_incl_04", "row0_unconditional",
              "gravity_settle",     # drop_garbage(): settle BEFORE resolve -- see fix (5)
              "receiver_timing", "counter_attack")
HARNESS_REV = "vsharness-r1 / " + stamp(_MECHANICS)

# ★ `gravity_settle` was added to REQUIRED_MECHANICS after this harness already implemented
# it, so for a while the stamp read "MISSING: gravity_settle" -- FALSE, and on every results
# file written in that window. That is the vocabulary mechanism working, not failing:
# widening the checklist forces every harness to RE-DECLARE rather than coast on a
# "(complete)" earned under a shorter list. The gap that hid the floating-garbage bug in the
# first place was that no word existed for it. Cost here: one line. Elsewhere it caught a
# harness that genuinely lacked the settle.


def blind(dec):
    """Adapt a solo decider (board, cur, nxt) to the opponent-aware signature."""
    return lambda b, c, n, opp: dec.choose(b, c, n)


def drop_garbage(board, size, colours, phase):
    """ROM-true release (checkReleaseAttack $9C1B). Returns the combo count of any cascade
    the garbage itself sets off -- the receiver's COUNTER-ATTACK."""
    for i, c in enumerate(garbage_columns(size, phase)):
        if 0 <= c < board.cols:
            # UNCONDITIONAL write: the ROM overwrites an occupied row-0 cell.
            board.color[0, c] = colours[i % len(colours)]
            board.link[0, c] = 0            # unlinked single (colour | singleHalfPill)
            board.is_virus[0, c] = False
    while board._apply_gravity():           # fix (5): settle BEFORE resolving
        pass
    return combo_from_cascade(lines_per_step(board))


def play_match(seed, dec0, dec1, level=11, max_pills=300, nes_pills=True, hook=None,
               suppress=None, garbage=True, _deliver_early=False):
    """One ROM-true VS match. Deciders take (board, cur, nxt, opp_board).

    ★ THIS IS THE ONLY SANCTIONED MATCH LOOP. Do not write another one. Five mechanics
    bugs survived simultaneously because sizing, saturation, the A/B and the ablation each
    kept a private copy of this loop and they drifted apart. Everything extends it instead:

    `hook(who, env, opp_board, action, took)` runs once per decision, after the move is
    chosen and before it is played; whatever it returns is collected into `log`.

    `suppress` = a volley ordinal to DROP (the stored attack is discarded undelivered, as
    if it had never been sent). Used by the per-volley ablation. Column phases are keyed by
    (seed, ordinal), never by a shared stream, so suppressing one volley cannot reshuffle
    another's columns -- without that, the counterfactual would differ by an RNG shift as
    well as by the ablation.

    `garbage=False` severs the attack channel entirely -- nothing is banked and nothing is
    delivered, so the two boards play out side by side without interacting. This is the
    control arm for the causal ON/OFF power question ("how much does garbage decide?"). It
    is a REAL control, not a no-op: with the same seed and deciders the ON and OFF matches
    are identical up to the first release and diverge only from there.

    `_deliver_early` is TEST-ONLY and DELIBERATELY WRONG. It restores the pre-fix ordering
    where garbage lands BEFORE the receiver's next decision instead of after their next
    placement resolves. It exists solely so the receiver_timing test has a negative control
    -- a check that cannot fail under the wrong ordering is not a test. Never set it in an
    experiment; the underscore is the warning.

    Also returns `volleys` (state at each release, for conditioning) and `trace` (each
    player's board after every placement, for a low-variance local damage window).
    """
    m = VsMatch(seed, level, max_pills, nes_pills)
    store = [0, 0]        # accumulated attackSize waiting to land on each player
    scol = [[1], [1]]
    atk = [0, 0]          # releases landed on each player
    fired = [0, 0]
    changed = [0, 0]
    vol = 0
    ply = [0, 0]
    took = [0, 0]         # size of the release that landed on us most recently
    rcv = [0, 0]          # how many releases each player has RECEIVED (per-receiver ordinal)
    log = []
    volleys = []          # state at each release, for conditional-value analysis
    trace = [[], []]      # board summary after each placement, for the damage window
    result, win = "cap", -1
    for _ in range(max_pills * 2):
        stop = False
        for who, dec in ((0, dec0), (1, dec1)):
            e = m.env[who]
            if _deliver_early and store[who] >= ATTACK_SIZE_MIN:
                # WRONG ORDERING, test-only: the receiver sees the garbage a full placement
                # early. Kept solely as the negative control for the receiver_timing board.
                drop_garbage(e.board, store[who], scol[who], seed * 7919 + vol)
                atk[who] += 1; vol += 1; took[who] = store[who]; store[who] = 0
            a = dec(e.board, e.cur, e.nxt, m.env[1 - who].board)
            if a is None:
                result, win, stop = "no-move", 1 - who, True
                break
            if hook is not None:
                r = hook(who, e, m.env[1 - who].board, a, took[who])
                if r is not None:
                    log.append(r)
            took[who] = 0
            st = getattr(dec, "stats", None)
            if st is not None:
                fired[who] += st.pop("fired", 0)
                changed[who] += st.pop("changed", 0)
            pp = probe_placement(e, a)
            before = e.board.color.copy()
            n0 = len(m.pending[1 - who])
            done, res = m.step(who, a)          # PLACE + resolve
            del m.pending[1 - who][n0:]         # discard vs_env's own proxy queueing
            ply[who] += 1
            hh = e.board.column_heights()
            trace[who].append((int((e.board.color != 0).sum()), int(hh.max()),
                               int(e.board.virus_count())))
            if pp["attack"] and garbage:        # BANK our combo against the opponent
                store[1 - who] += pp["atk_size"]
                scol[1 - who] = m._colours_of(before, e.board.color)
            if done:
                result = res
                win = -1 if res == "stall" else (who if res == "clear" else 1 - who)
                stop = True
                break
            if store[who] >= ATTACK_SIZE_MIN and not _deliver_early:  # RECEIVE
                h = e.board.column_heights()
                rcv[who] += 1
                # ★ `r_ord` = this RECEIVER's own volley index (1st, 2nd, ... they took),
                # distinct from the global `ord`. Required for matched-ordinal comparison:
                # when two arms receive UNEQUAL volley COUNTS, any raw per-volley average
                # conditioned on receiver state is selection-biased, because later volleys
                # arrive at systematically different board states. Comparing the k-th
                # volley to the k-th removes that. (Bias identified by opening-book, whose
                # raw phase gap reversed sign once matched on ordinal.)
                volleys.append({"ord": vol, "victim": who, "size": store[who],
                                "r_ord": rcv[who],
                                "v_ply": ply[who], "s_ply": ply[1 - who],
                                "r_vc": int(e.board.virus_count()),
                                "r_cells": int((e.board.color != 0).sum()),
                                "r_maxh": int(h.max()),
                                "r_spawnh": int(max(h[3], h[4])),
                                "s_vc": int(m.env[1 - who].board.virus_count())})
                if vol == suppress:             # THE ABLATION: never delivered
                    store[who] = 0
                    vol += 1
                    continue
                combo = drop_garbage(e.board, store[who], scol[who], seed * 7919 + vol)
                atk[who] += 1
                vol += 1
                took[who] = store[who]
                store[who] = 0
                if attack_size(combo) >= ATTACK_SIZE_MIN:   # counter-attack
                    store[1 - who] += attack_size(combo)
                if e.board.spawn_blocked():
                    result, win, stop = "topout", 1 - who, True
                    break
        if stop:
            break
    v = [m.env[k].board.virus_count() for k in (0, 1)]
    return {"seed": seed, "winner": win, "reason": result, "margin": v[1] - v[0],
            "virus": v, "pills": list(ply), "attacks": atk, "releases": vol,
            "fired": fired, "changed": changed, "log": log, "volleys": volleys,
            "trace": trace, "rev": HARNESS_REV}
