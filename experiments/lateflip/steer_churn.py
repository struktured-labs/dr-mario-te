"""ANSWER-CHURN steering model: the couch P2 driver (ANTIBODY_DIST couch cart c960dd49, DRTAPP=2) executing a REAL
copro publish timeline, on the ROM physics of experiments/cvx/steer_model.py (checkYMove / checkXMove / checkRotate
copied unchanged in spirit). Optional DRLATEGUARD (dr-mario-te claude/late-flip) gate.

Why: steer_model.Steer.execute takes ONE answer at one latency and slams on alignment, so it cannot produce the
10/03 G2 failure class: the copro's running best is published early (the Pass-0 top, ~1-8 f after GO), the driver
commits to it, the search's own argmax arrives 7-30 f later, and the driver re-targets (column always, orientation
via DRRELATCH while $0386 >= 8, i.e. always on a tall board) into a move it cannot finish -> a HYBRID landing.
This model takes the publish timeline (from the Verilator co-sim of the shipped copro, pubtrace_g2.py) and
reproduces the cart's state machine per frame:

  f = 1 is the first frame whose hook sees the new pill (the edge); GO at f = 8 (DELAY2 = 15 hooks); gravity pinned
  until GO (freeze_pending + DRPENDBOUND); publish visible from frame 8 + t_pub; DONE at 8 + done_f.
  pend / no answer : DRPROPH pulse (if armed) else nothing
  live publish     : TGT col := pub col; orient := pub orient if not committed, else DRRELATCH (Y >= 8 & changed ->
                     re-open the latch);  [DRLATEGUARD: committed + changed + infeasible -> ignore, freeze the pill]
  DONE             : TGT := final  [gated likewise];  DRRECOMMIT re-opens the latch if Y >= 8 and orient differs
  act_p2           : pre-phase rotate (DRROTDIR) -> think gate (DONE | 6 f after GO | SLAM_ARM & Y < 8) -> commit;
                     column: DISTGATE (budget 0 iff no empty row below the [x..target] span -> clamp to x);
                     aligned: slam (DOWN) at DONE, or when SLAM_ARM and the target has been stable K hooks
                     (K = 8 if Y < 8, 255 if viruses < 10, else 32 -- the couch cart's DRSLAM_KOPEN=32).
  every press (A/B/L/R) passes the DRTAPP tap filter (one press per P frames, released frame between).

Usage (validation vs Mesen): steer_churn.py PUBTRACE.jsonl MESEN_LOG_OFF [MESEN_LOG_ON]
"""
from __future__ import annotations

import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "cvx"))
import steer_model as SM  # noqa: E402

ROWS, COLS = SM.ROWS, SM.COLS
RIGHT, LEFT, DOWN, BTN_B, BTN_A = SM.RIGHT, SM.LEFT, SM.DOWN, SM.BTN_B, SM.BTN_A
C2G = {0: 3, 1: 1, 2: 0, 3: 2}                       # copro orient4 -> game rot (handle()'s map)
GO_F = 8
MIN_THINK_F = 6                                     # DRMINTHINK=12 hooks
CROSS_LOWY = 8


def board_color(upload_line):
    b = [int(v, 16) for v in upload_line.split()[4:]]
    return [[0 if b[r * 8 + c] in (0x00, 0xFF) else 1 for c in range(COLS)] for r in range(ROWS)]


def lateguard_ok(color, x, row, rot, grav, c2, o2, thr, P=2, M=0, rowcap=2):
    """The DRLATEGUARD rule (patch_cartridge_copro.py lg_gate; gate_lateguard.py reference)."""
    d = (o2 - rot) & 3
    need = (abs(c2 - x) + (0 if d == 0 else 2 if d == 2 else 1)) * P + M
    lo = min(x, c2)
    hi = max(x, min(7, c2 + (1 if o2 % 2 == 0 else 0)))
    y = min(15, ROWS - 1 - row)
    r = 15 - y
    if any(color[r][c] for c in range(lo, hi + 1)):
        return False
    avail = max(0, thr - grav)
    k = 0
    while k < min(y, rowcap) and not any(color[r + 1 + k][c] for c in range(lo, hi + 1)):
        k += 1; avail += thr + 1
    if c2 != x:
        avail -= thr + 1
        if avail < 0:
            return False
    return avail >= need


def refuse(policy, color, x, row, rot, spd, c2, o2, thr, tgt_c, tgt_o, tall, tap):
    """True = the committed driver ignores this changed target (and freezes the pill)."""
    if policy == "guard":
        return not lateguard_ok(color, x, row, rot, spd, c2, o2, thr, P=tap)
    if policy == "freeze":                                  # execute the at-commit running best, always
        return True
    if policy == "tallfreeze":                              # coordinator's option: tall board + reversal/rotation
        if not tall:
            return False
        rev = (c2 != x) and (tgt_c is not None) and (tgt_c != x) and ((c2 > x) != (tgt_c > x))
        return rev or o2 != tgt_o
    return False


def execute(color, pubs, done_f, final, k_pills, vc, slam_arm=True, guard=False, tap=2, k_open=32, trace=False,
            policy=None, tall=False):
    """pubs: [(t_frames_after_GO, col, o4), ...]; final: (col, o4). Returns dict(var, col, lock_f, ...)."""
    thr = SM.table_threshold(k_pills, 1)
    if policy is None:
        policy = "guard" if guard else "ship"
    x, row, rot = 3, 0, 0
    spd, v = 0, 0
    tgt_c, tgt_o = None, None
    rd2 = cmt = lock2 = False
    armed = False; done_seen = False
    stable = 0
    last_tap = None; prev_held = 0
    pd = None
    armed_proph = SM.proph_throat(color)
    if armed_proph in ("L", "R"):
        pd = armed_proph
    tr = []
    lock_f = None
    for f in range(1, 400):
        t = f - GO_F
        # ---------------- driver (hook) ----------------
        want, raw = None, 0
        pend = f < GO_F
        if not pend and not done_seen and t >= done_f:
            # handle(): DONE -> final answer
            done_seen = True; armed = False
            c2, o2 = final[0], C2G[final[1] if final[1] != 0xFF else 0]
            if policy != "ship" and cmt and not lock2 and (c2, o2) != (tgt_c, tgt_o):
                if refuse(policy, color, x, row, rot, spd, c2, o2, thr, tgt_c, tgt_o, tall, tap):
                    lock2 = True
            if not (policy != "ship" and cmt and lock2):
                if (c2, o2) != (tgt_c, tgt_o):
                    stable = 0
                tgt_c, tgt_o = c2, o2
                if rd2 and (ROWS - 1 - row) >= CROSS_LOWY and tgt_o != rot:
                    rd2 = False                                    # DRRECOMMIT
        elif not pend:
            armed = True
        mailbox = None
        if armed and not done_seen:
            cur = None
            for tp, c, o in pubs:
                if tp <= t:
                    cur = (c, o)
            mailbox = cur
        act = True
        if pend or (armed and not done_seen and mailbox is None):
            act = False
            if pd is not None:
                want = RIGHT if pd == "R" else LEFT
        elif armed and not done_seen:
            c2, o2 = mailbox[0], C2G[mailbox[1]]
            adopt = True
            if policy != "ship" and cmt and (lock2 or (c2, o2) != (tgt_c, tgt_o)):
                if lock2 or refuse(policy, color, x, row, rot, spd, c2, o2, thr, tgt_c, tgt_o, tall, tap):
                    lock2 = True; adopt = False
            if adopt:
                if (c2, o2) != (tgt_c, tgt_o) and tgt_c is not None and (c2 != tgt_c or not rd2):
                    pass
                old = (tgt_c, tgt_o)
                tgt_c = c2
                if not rd2:
                    tgt_o = o2
                elif (ROWS - 1 - row) >= CROSS_LOWY and o2 != tgt_o:       # DRRELATCH
                    tgt_o = o2; rd2 = False
                if (tgt_c, tgt_o) != old:
                    stable = 0
        if act and tgt_c is not None:
            stable = min(254, stable + 2)
            if not rd2:
                if rot != tgt_o:
                    want = BTN_B if ((tgt_o - rot) & 3) == 1 else BTN_A
                else:
                    y = ROWS - 1 - row
                    if (not armed or done_seen) or t >= MIN_THINK_F or (slam_arm and y < CROSS_LOWY):
                        rd2 = True; cmt = True
            if rd2 and want is None:
                eff = tgt_c
                if eff != x:
                    lo, hi = min(x, eff), max(x, eff)
                    if not (row + 1 < ROWS and all(color[row + 1][c] == 0 for c in range(lo, hi + 1))):
                        eff = x                                         # DISTGATE: no empty row below -> budget 0
                if x != eff:
                    want = RIGHT if x < eff else LEFT
                else:
                    y = ROWS - 1 - row
                    if done_seen:
                        raw = DOWN
                    elif slam_arm:
                        kk = 8 if y < CROSS_LOWY else (255 if vc < 10 else k_open)
                        if stable >= kk:
                            raw = DOWN
        if want is not None:
            if (last_tap is None or f - last_tap >= tap) and not (prev_held & want):
                raw = want; last_tap = f
        held_prev = prev_held
        pressed = raw & ~held_prev
        held = raw
        prev_held = held & (LEFT | RIGHT | BTN_A | BTN_B)
        # ---------------- ROM (main loop) ----------------
        lower = False
        if (f % 2 == 1) and (held & 0x0F) == DOWN:
            lower = True
        elif not pend:
            spd += 1
            if spd > thr:
                lower = True
        else:
            spd = 1                                                    # freeze_pending pin (0 at the hook, +1 here)
        if lower:
            spd = 0
            if SM.valid(color, x, row + 1, rot):
                row += 1
            else:
                lock_f = f
                break
        if pressed & (LEFT | RIGHT):
            if held & RIGHT and x != (COLS - 2 + (rot & 1)) and SM.valid(color, x + 1, row, rot):
                x += 1
            if held & LEFT and x != 0 and SM.valid(color, x - 1, row, rot):
                x -= 1
        for btn, dr in ((BTN_A, -1), (BTN_B, 1)):
            if pressed & btn:
                r0, x0 = rot, x
                rot = (rot + dr) & 3
                if rot % 2 == 0:
                    if not SM.valid(color, x, row, rot):
                        x -= 1
                        if not SM.valid(color, x, row, rot):
                            rot, x = r0, x0
                elif not SM.valid(color, x, row, rot):
                    rot, x = r0, x0
        if trace:
            tr.append((f, x, row, rot, tgt_c, tgt_o, int(rd2), raw))
    var = SM.VAR_OF_ROT[rot]
    return {"action": var * 8 + x, "lock_f": lock_f, "frozen": lock2, "done_before_lock": done_seen,
            "trace": tr}


def main():
    sys.path.insert(0, "/home/struktured/projects/dr-mario-lateflip-wt/tools/lateflip")
    from parse_lateflip import load
    recs = {json.loads(l)["p"]: json.loads(l) for l in open(sys.argv[1])}
    for li, log in enumerate(sys.argv[2:4]):
        guard = li == 1
        L = load(log)
        agree = n = 0
        slam = True
        bad = []
        for p in sorted(recs):
            r = recs[p]
            if p not in L or not L[p]["land"]:
                continue
            color = board_color(r["upload"])
            res = execute(color, [(a, b, c) for a, b, c, _ in r["pubs"]], r["done_f"], r["final"][:2], p,
                          r["vc"], slam_arm=slam, guard=guard)
            slam = res["done_before_lock"]                          # LOCK-WHILE-ARMED disarms the next pill
            n += 1
            ok = res["action"] == L[p]["land"]["act"]
            agree += ok
            if not ok:
                bad.append((p, res["action"], L[p]["land"]["act"]))
        print(f"{'guard' if guard else 'ship '} model vs Mesen landing: {agree}/{n}   mismatches {bad[:30]}")


if __name__ == "__main__":
    main()
