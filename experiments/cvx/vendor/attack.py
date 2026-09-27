#!/usr/bin/env python3
"""ROM-TRUE attack detection, replacing vs_env's `cells >= 7` proxy.

★ CORRECTED 2026-07-31 (opening-book, task #12; cited to the disassembly and re-verified
here). This file previously used `any(step >= 2)` -- ">=2 runs in the SAME clear step" --
on the premise that a cascade of singles sends nothing. THAT PREMISE WAS WRONG.
`currentP_comboCounter` increments once per matched run (game_logic.asm:1176 horizontal,
:1623 vertical) and is never reset inside the cascade: @finishedUpdatingField (:1474-1485)
re-enters checkDrop while matchFlag is set, and resetMatchFlag (:1495) clears only the
flag. The counter is consumed once, AFTER the cascade, in checkComboCounterForAttack
($9C03, :2875-2888). So runs from different cascade steps SUM, and `[1, 1]` DOES attack.
The rule is `sum(steps) >= 2`.

Cost of the old rule: it under-counted attacks 6.7x (2.3% vs 15.1% of clearing placements
over 120 L11 games); 85% of real attacks are cascade-formed. Note this is the OPPOSITE
direction to the `cells >= 7` proxy critique, which still stands on its own terms -- the
proxy was wrong for the wrong reasons and the line-accurate replacement inherited a
different wrong trigger.

One useful property: since only the SUM matters, the ROM rule is insensitive to how a
cascade is decomposed into steps, so it is strictly harder to get wrong than a step-local
rule. `lines_per_step` is still the right primitive; only the predicate over it changed.
"""
from __future__ import annotations
import numpy as np
from rom_attack_rule import combo_from_cascade, attack_size, ATTACK_SIZE_MIN

EMPTY = 0


def count_runs(color: np.ndarray) -> int:
    """Number of distinct maximal runs of >=4 same-coloured cells (H and V)."""
    rows, cols = color.shape
    n = 0
    for r in range(rows):
        c = 0
        while c < cols:
            v = color[r, c]
            if v == EMPTY:
                c += 1
                continue
            c2 = c
            while c2 < cols and color[r, c2] == v:
                c2 += 1
            if c2 - c >= 4:
                n += 1
            c = c2
    for c in range(cols):
        r = 0
        while r < rows:
            v = color[r, c]
            if v == EMPTY:
                r += 1
                continue
            r2 = r
            while r2 < rows and color[r2, c] == v:
                r2 += 1
            if r2 - r >= 4:
                n += 1
            r = r2
    return n


def lines_per_step(board) -> list:
    """Destructively resolve `board`, returning the run count of each clear step."""
    steps = []
    while True:
        mask = board._find_clears()
        if not mask.any():
            break
        steps.append(count_runs(board.color))
        board._apply_clear(mask)
        board._apply_gravity()
    return steps


def probe_placement(env, action) -> dict:
    """Replay `action` on a CLONE of env.board; report what the clear would look like.

    `cells` is the TRUE number of cleared cells. vs_env never has this number: it computes
    occupancy(before_step) - occupancy(after_step), and `env.step` places the pill (+2
    cells) before resolving, so its delta is `cleared - 2` and its `>= 7` test is really
    `cleared >= 9`. Credit to selfplay-opt for spotting the off-by-2. Readings:
      attack        ROM rule: sum(runs over the whole cascade) >= 2
      atk_size      ROM attackSize -> 2/3/4 garbage tiles (>=4 saturates at 4)
      attack_step   the OLD, WRONG rule (>=2 runs in one step), kept to quantify the delta
      attack_intent cells >= 7  -- the cell proxy as DOCUMENTED
      attack_vsenv  cells >= 9  -- the cell proxy as IMPLEMENTED
    """
    orient, col, pill = env._decode(int(action))
    b = env.board.clone()
    before = int((b.color != EMPTY).sum())
    if not b.place_pill(pill, orient, col):
        return {"lines": [], "cells": 0, "attack": False, "atk_size": 0,
                "attack_step": False, "attack_proxy": False,
                "attack_intent": False, "attack_vsenv": False}
    steps = lines_per_step(b)
    cells = before + 2 - int((b.color != EMPTY).sum())
    combo = combo_from_cascade(steps)
    size = attack_size(combo)
    return {"lines": steps, "cells": cells,
            "attack": size >= ATTACK_SIZE_MIN,      # ROM-true
            "atk_size": size,
            "attack_step": any(s >= 2 for s in steps),   # old rule, for the delta only
            "attack_proxy": cells >= 7,
            "attack_intent": cells >= 7,
            "attack_vsenv": cells - 2 >= 7}
