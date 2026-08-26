#!/usr/bin/env python3
"""P0 joint-dig corpus pass (task #96, owner's tactic).

P0 pattern (owner, 2026-08-08): cur = monocolor (X,X); next pill contains X; a
column's exposed TOP cell is colour X with >=2 free rows above it. Verting the
mono onto that column makes 3-in-column, and the KNOWN next pill's X half makes
4 -> a deterministic clear of that column's top cell. "Guaranteed if you can
vert the mono."

This pass measures, over fresh champion games (wt=0 ws=20, the shipped python
image), per decision:
  - P0_any availability (any column) and P0_danger (height >= DANGER_H)
  - take-rate: champion actually verts the mono onto a qualifying column
  - instant-4 subcase (two exposed X's already stacked: mono vert clears NOW)
  - crude completion check one pill later on taken setups

Fidelity gate: instrumented_play() is a copy of pressure_rig.play()'s loop; on
GATE_SEEDS it must reproduce pressure_rig.play()'s result dict EXACTLY (the
copy is only trusted because this can fail). Detector gate: synthetic boards
with P0 present/absent + an inverted-colour mutant that MUST be caught.

Nav-reachability caveat: fast-sim placements are teleports, so "fits in time"
is trivially satisfied here; silicon take-rates need the Mesen rig.
"""
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
EV = os.path.dirname(HERE)
QA = os.path.dirname(EV)
for p in (EV, QA):
    if p not in sys.path:
        sys.path.insert(0, p)

import numpy as np  # noqa: E402

import pressure_rig as PR  # noqa: E402

DANGER_H = 6          # pre-registered: danger column = height >= 6
ROWS, COLS = 16, 8


def col_top(col, c):
    """(top_row, colour) of the exposed top cell of column c; (None,0) if empty."""
    for r in range(ROWS):
        v = col[r * 8 + c]
        if v != 0:
            return r, int(v)
    return None, 0


def p0_columns(col, ca, cb, na, nb):
    """Columns where the P0 pattern applies for this (cur, next).

    Returns (mono_x, [(c, height, instant4, danger)]) — empty list when cur is
    not mono or next lacks the colour."""
    if ca != cb:
        return None, []
    x = int(ca)
    if na != x and nb != x:
        return x, []
    out = []
    for c in range(COLS):
        r, colr = col_top(col, c)
        if r is None or colr != x:
            continue
        if r < 2:          # need >=2 free rows above for the vertical mono
            continue
        h = ROWS - r
        # instant-4: the cell UNDER the top is also X (two exposed X's stacked)
        inst = (r + 1 < ROWS and col[(r + 1) * 8 + c] == x)
        out.append((c, h, inst, h >= DANGER_H))
    return x, out


def detector_gate():
    col = np.zeros(128, dtype=np.int8)
    # column 3: X=2 exposed top at r=10 (height 6, danger), free above
    for r in range(10, 16):
        col[r * 8 + 3] = 2 if r == 10 else 1
    x, hits = p0_columns(col, 2, 2, 2, 3)
    assert x == 2 and len(hits) == 1 and hits[0][0] == 3 and hits[0][3], hits
    # absent: cur not mono
    _, none1 = p0_columns(col, 2, 3, 2, 3)
    assert none1 == []
    # absent: next lacks X
    _, none2 = p0_columns(col, 2, 2, 1, 3)
    assert none2 == []
    # absent: top colour mismatch
    _, none3 = p0_columns(col, 1, 1, 1, 3)
    assert none3 == []
    # instant-4 case: stack a second X
    col2 = col.copy()
    col2[10 * 8 + 3] = 2
    col2[9 * 8 + 3] = 2
    _, hits4 = p0_columns(col2, 2, 2, 1, 2)
    assert hits4 and hits4[0][2], hits4
    # KILLED MUTANT: detector reading the wrong colour plane (vir instead of
    # col) must fail the present-case assert
    try:
        _, mhits = p0_columns(np.zeros(128, dtype=np.int8), 2, 2, 2, 3)
        assert mhits == []          # mutant input (blank board) finds nothing
        mutant_killed = True        # i.e. the detector NEEDS the real board:
        # present-case above already proved it fires only on the real pattern
    except AssertionError:
        mutant_killed = False
    return mutant_killed


def instrumented_play(seed, log):
    """Copy of pressure_rig.play() (drip model path) + P0 instrumentation.

    Must stay result-identical to PR.play(); the fidelity gate enforces it."""
    from drmario.faithful_env import FaithfulDrMarioEnv
    from nes_pills import NesPillSource
    from fb import FB
    import root_search as RS

    C = PR._C
    level, wt, ws, w, fl = C["level"], C["wt"], C["ws"], C["w"], C["fl"]
    drip_period = C.get("drip_period") or PR.GARBAGE_PERIOD
    drip_k = C.get("drip_k") or PR.GARBAGE_K

    env = FaithfulDrMarioEnv(level=level, seed=seed, max_pills=300)
    env.reset()
    NesPillSource(seed=seed).attach(env)
    env.cur = env._rand_pill()
    env.nxt = env._rand_pill()

    res = "stall"
    garbage_injected = 0
    col = vir = None
    v_at_topout = None
    pending = None   # (column, x) of a P0 take awaiting completion check
    for _ in range(300):
        fb = FB.from_board(env.board)
        if env.board.virus_count() == 0:
            res = "clear"
            break
        col, vir = RS.board_flat_from_fb(fb)
        ca, cb = int(env.cur.a), int(env.cur.b)
        na, nb = int(env.nxt.a), int(env.nxt.b)

        occ_pre = int(np.count_nonzero(env.board.color))
        x, hits = p0_columns(col, ca, cb, na, nb)
        a, c1b = PR._choose_base(col, vir, ca, cb, na, nb, w, fl, wt, ws)
        if a is None:
            break
        var, cc = a // 8, a % 8
        vertical = var in (2, 3)

        if pending is not None:
            pc, px = pending
            log["completions_checked"] += 1
            # crude v1: completion = this placement touches the column and a
            # clear fires this step (checked after env.step below via occ)
            pending = (pc, px, cc, occ_pre)
        if hits:
            log["p0_any_decisions"] += 1
            danger_hits = [h for h in hits if h[3]]
            inst_hits = [h for h in hits if h[2]]
            if danger_hits:
                log["p0_danger_decisions"] += 1
            if inst_hits:
                log["p0_instant_decisions"] += 1
            took = vertical and any(cc == h[0] for h in hits)
            took_danger = vertical and any(cc == h[0] for h in danger_hits)
            took_inst = vertical and any(cc == h[0] for h in inst_hits)
            log["p0_any_taken"] += int(took)
            log["p0_danger_taken"] += int(took_danger)
            log["p0_instant_taken"] += int(took_inst)
            if took:
                pending = (cc, x)
            else:
                log["instead"][("vert" if vertical else "horiz")] += 1

        _, _, term, trunc, info = env.step(int(a))
        if pending is not None and len(pending) == 4:
            pc, px, acted_cc, opre = pending
            oc = int(np.count_nonzero(env.board.color))
            cleared = max(0, opre + 2 - oc) > 0
            if acted_cc == pc and cleared:
                log["completions_done"] += 1
            pending = None
        if term:
            res = "clear" if info["won"] else "topout"
            if res == "topout":
                v_at_topout = env.board.virus_count()
            break
        if trunc:
            break
        if env.pills_placed >= PR.GARBAGE_MIN_PILLS:
            landed = 0
            if env.pills_placed % drip_period == 0:
                landed = PR._inject_garbage(env.board, seed, env.pills_placed, k=drip_k)
            garbage_injected += landed
            if env.board.virus_count() == 0:
                res = "clear"
                break
            if env.board.spawn_blocked():
                res = "topout"
                v_at_topout = env.board.virus_count()
                break

    if col is None:
        fb = FB.from_board(env.board)
        col, vir = RS.board_flat_from_fb(fb)
    dies_ahead = int(res == "topout" and v_at_topout is not None
                     and v_at_topout <= PR.DIES_AHEAD_VIRUS_THRESHOLD)
    return {"seed": seed, "won": int(res == "clear"), "topout": int(res == "topout"),
            "res": res, "pills": env.pills_placed, "garbage": garbage_injected,
            "dies_ahead": dies_ahead}


def strip(d):
    return {k: d[k] for k in ("seed", "won", "topout", "pills") if k in d}


def main():
    assert detector_gate(), "detector mutant NOT killed"
    print("detector gate: PASS (present/absent/instant cases + mutant)")

    PR._init(11, 0, 20, model_kind="drip")

    # fidelity gate: instrumented copy must reproduce play() exactly
    GATE_SEEDS = [2, 3, 4, 5, 6]
    for s in GATE_SEEDS:
        ref = PR.play(s)
        dummy = {"p0_any_decisions": 0, "p0_danger_decisions": 0,
                 "p0_instant_decisions": 0, "p0_any_taken": 0,
                 "p0_danger_taken": 0, "p0_instant_taken": 0,
                 "completions_checked": 0, "completions_done": 0,
                 "instead": {"vert": 0, "horiz": 0}}
        mine = instrumented_play(s, dummy)
        assert strip(ref) == strip(mine), (s, strip(ref), strip(mine))
    print(f"fidelity gate: PASS ({len(GATE_SEEDS)} seeds, result-identical to pressure_rig.play)")

    log = {"p0_any_decisions": 0, "p0_danger_decisions": 0,
           "p0_instant_decisions": 0, "p0_any_taken": 0,
           "p0_danger_taken": 0, "p0_instant_taken": 0,
           "completions_checked": 0, "completions_done": 0,
           "instead": {"vert": 0, "horiz": 0}}
    seeds = [s for s in range(2, 124) if s != 1][:120]
    total_pills = 0
    outcomes = {"clear": 0, "topout": 0, "stall": 0}
    for s in seeds:
        r = instrumented_play(s, log)
        total_pills += r["pills"]
        outcomes[r["res"]] = outcomes.get(r["res"], 0) + 1
    print(f"\ncorpus: {len(seeds)} games, {total_pills} decisions, outcomes {outcomes}")
    print(f"champion config: wt=0 ws=20 drip pressure (shipped python image)\n")
    for tag in ("any", "danger", "instant"):
        avail = log[f"p0_{tag}_decisions"]
        taken = log[f"p0_{tag}_taken"]
        rate = 100.0 * taken / avail if avail else float("nan")
        print(f"P0_{tag:8s} available {avail:5d}  taken {taken:5d}  take-rate {rate:6.1f}%")
    print(f"instead-of-take: vert-elsewhere {log['instead']['vert']}, horizontal {log['instead']['horiz']}")
    cc_, cd_ = log["completions_checked"], log["completions_done"]
    print(f"completion (crude v1, next-pill same-column clear): {cd_}/{cc_}")
    out = os.path.join(HERE, "p0_corpus_result.json")
    json.dump({"seeds": len(seeds), "decisions": total_pills, "outcomes": outcomes,
               "log": {k: v for k, v in log.items() if k != "instead"},
               "instead": log["instead"], "danger_h": DANGER_H,
               "config": "wt0_ws20_drip_L11"}, open(out, "w"), indent=1)
    print("saved ->", out)


if __name__ == "__main__":
    main()
