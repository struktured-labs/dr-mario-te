# COPY of reach-wt experiments/reach/reach_fw.py @ 826f4e0 (tap=P superset; tap=None == reach_fw.py). For STEER3 alignment.
"""Closed-form REACH RULE for the copro firmware (STEER2): the reach-root mask without a frame simulator.
Validated == the frame simulator (steer_model, strict: the capsule lands EXACTLY on the brain's straight-drop
cells) on 46,272 root candidates / 1,446 boards (L11 + L15): 100% per candidate, 100% argmax
(reach_fw_validate.py).

    allowed = reach_mask_fw(color, thr)          # int8[32]; sim action a = var*8 + col; color[row][col], 0 = empty

Constants (silicon-fitted, see steer_model.py):
  T_LAT = 19   frames from the new-pill edge to the driver's first answer action (silicon median, n=384)
  G0    = 8    first frame the ROM's gravity counter runs (driver settle pin ends; fitted 7|8)
  F0    = 3    first frame lateral input is processed (DRPROPH moves at f3-4)
  thr   = speedCounterTable[baseSpeedSettingValue[speed] + speedUps]   (P2: speed $038B, speedUps $038A)
          a row lasts thr+1 frames; gravity tick n (row n -> n+1) happens at frame T(n) = G0 + thr + n*(thr+1);
          row(t) = 0 if t < G0+thr else (t - G0 - thr) // (thr+1) + 1
  NROT  = {var0: 0, var1: 2, var2: 1, var3: 1} rotation presses (DRROTDIR shortest direction), one per frame
  DAS   : 1st column on the press frame t1, 2nd at t1+16, then every 6 (t_i = t1 + 16 + 6*(i-2))
Cell-level helpers: fits(x,row,shape) = the capsule's cells are empty (V: (row-1,x),(row,x); H: (row,x),(row,x+1));
  rest_from(x,row,shape) = fall while fits(row+1); lock frame of a capsule resting at R = T(R).

Rule for candidate (var, col), capsule spawning horizontal at x=3, row 0:
  0. PROPH (cart DRPROPH): armed iff min(top3, top4) <= 2; direction = the deeper throat (ties LEFT) if its gate
     cells (rows 0-1 of col 2 / col 5) are empty, else the other side if its gate is empty, else none. The cart
     pulses on odd frames 3, 5, ... < T_LAT: each pulse moves one column if fits (H) at row(f); the lock re-bases.
     If the capsule locks at or before T_LAT, only that landing is reachable (var0, that column, straight rest).
  1. Rotation presses from T_LAT at the capsule's column, one per frame, retried every frame while blocked, until
     the capsule locks (-> unreachable). 1st press -> vertical (no kick); var1's 2nd press -> horizontal (if blocked,
     the ROM wall-kicks one column left). t1 = the frame after the last successful press (T_LAT if NROT = 0).
  2. Lateral steps i = 1..|col - x| at t_i. Each step needs:
       (a) t_i < the current lock frame (the gravity step happens before the lateral step within a frame)
       (c) the row directly below the capsule's row(t_i - 1) is ENTIRELY EMPTY across columns
           [min(x, col) .. max(x, col)] (else DRDISTGATE's budget is 0: the driver aims at the current column and
           soft-drops short; any budget >= 1 only re-aims and the hold continues)
       (b) fits at the destination column at row(t_i)
     then the lock re-bases on rest_from(new x, row(t_i)).
  3. Aligned: it falls straight from its row; reachable iff that rest row == the straight-drop rest row
     (so a capsule that slid under an overhang is NOT the brain's landing).
Legal candidates only (straight-drop cells exist). If none is allowed, the mask is all-ones (no filtering).

TAP MODE (tap=P, cart DRTAPP=P; owner ruling 2026-09-25): every P2 press -- PROPH pulse, rotation, lateral -- is a
one-frame tap from ONE shared scheduler, the next press no sooner than P frames later (cart tap filter, reach-wt
patch_cartridge_copro.py). Timing, replacing the DAS schedule above:
  0. PROPH presses at f = F0, F0+P, F0+2P, ... (< T_LAT, < lock); a blocked press still spends its slot.
     s = T_LAT, or max(T_LAT, last PROPH press + P) if PROPH pressed.
  1. rotation attempts at s, s+P, ... (a blocked attempt costs a slot, retried P frames later); t1 = last press + P
     (t1 = s if NROT = 0).
  2. lateral steps at t_i = t1 + (i-1)*P, same (a)(b)(c) checks.
"""
ROWS, COLS = 16, 8
T_LAT, G0, F0 = 19, 8, 3
NROT = {0: 0, 1: 2, 2: 1, 3: 1}
DT = [0, 2, 5, 7, 7, 7, 7, 7, 7, 7, 7, 7, 7, 7, 7, 7]


def tops(color):
    return [next((r for r in range(ROWS) if color[r][c] != 0), ROWS) for c in range(COLS)]


def rest(top, x, vert):
    if vert:
        return top[x] - 1
    return min(top[x], top[x + 1]) - 1


def tick_frame(n, thr):
    return G0 + thr + n * (thr + 1)


def row_at(t, thr):
    """Row after the gravity step of frame t, in free fall from row 0."""
    if t < G0 + thr:
        return 0
    return (t - G0 - thr) // (thr + 1) + 1


def fits(top, x, row, vert, color=None):
    """Capsule cells free at (row, x). With `color`, a cell-level check (sees overhangs); else column tops."""
    if vert:
        if not (0 <= x < COLS) or row >= ROWS:
            return False
        if color is not None:
            return color[row][x] == 0 and (row - 1 < 0 or color[row - 1][x] == 0)
        return row <= top[x] - 1
    if not (0 <= x and x + 1 < COLS) or row >= ROWS:
        return False
    if color is not None:
        return color[row][x] == 0 and color[row][x + 1] == 0
    return row <= min(top[x], top[x + 1]) - 1


def free_rows_below(color, row, lo, hi):
    y = 0
    for r in range(row + 1, ROWS):
        if all(color[r][c] == 0 for c in range(lo, hi + 1)):
            y += 1
        else:
            break
    return y


def proph_dir(color, top):
    f3, f4 = top[3], top[4]
    if f3 > 2 and f4 > 2:
        return None
    gl = color[0][2] == 0 and color[1][2] == 0
    gr = color[0][5] == 0 and color[1][5] == 0
    if f4 > f3:
        return "R" if gr else ("L" if gl else None)
    return "L" if gl else ("R" if gr else None)


def rest_from(color, x, row, vert):
    """Cell-level rest row of a capsule at (x, row): fall while the next row is free. Assumes it fits at row."""
    r = row
    while fits(None, x, r + 1, vert, color):
        r += 1
    return r


def straight_rest(top, x, vert):
    return top[x] - 1 if vert else min(top[x], top[x + 1]) - 1


def reachable(color, top, thr, var, col, tap=None, rot_margin=0):
    """True iff the couch driver lands the capsule EXACTLY on the straight-drop cells of (var, col).
    tap=None: today's DAS driver; tap=P: the DRTAPP=P tap driver (see the module docstring)."""
    vert = var in (2, 3)
    x = 3
    last_press = None
    # ---- 0. PROPH pulse phase (capsule horizontal, rot 0, until the answer at T_LAT)
    pd = proph_dir(color, top)
    if pd is not None:
        step = 1 if pd == "R" else -1
        lockf = tick_frame(rest_from(color, x, 0, False), thr)
        for f in (range(F0, T_LAT) if tap is None else range(F0, T_LAT, tap)):
            if f >= lockf:
                break
            if tap is not None or f % 2 == 1:                  # DAS: pulse on odd frames; TAP: every P from F0
                last_press = f
                r = row_at(f, thr)
                if fits(None, x + step, r, False, color):
                    x += step
                    lockf = tick_frame(rest_from(color, x, r, False), thr)
        if lockf <= T_LAT:                                     # locked before the answer: landing is fixed
            r = row_at(lockf, thr) if lockf > G0 + thr else 0
            land = rest_from(color, x, min(r, rest_from(color, x, 0, False)), False)
            return var == 0 and x == col and land == straight_rest(top, x, False)
    r = row_at(T_LAT - 1, thr)
    lockf = tick_frame(rest_from(color, x, r, False), thr)
    # ---- 1. rotation presses, one per frame from T_LAT, at the capsule's column
    # A blocked press is undone and the driver presses again next frame (fresh edge) until it succeeds or the
    # capsule locks; each successful press re-bases the lock on the new shape.
    nrot = NROT[var]
    f = T_LAT
    if tap is not None and last_press is not None:
        f = max(T_LAT, last_press + tap)                       # the shared scheduler's next press slot
    if nrot:
        f += rot_margin                                        # STEER4 arm 3: rotation conservatism (k61 fix)
    rstep = 1 if tap is None else tap
    done = 0
    while done < nrot:
        if f >= lockf:
            return False
        r = row_at(f, thr)
        if done == 0:                                          # first press always makes it vertical
            if fits(None, x, r, True, color):
                done = 1
                lockf = tick_frame(rest_from(color, x, r, True), thr)
        else:                                                  # var1 second press: back to H (kick one left)
            if fits(None, x, r, False, color):
                done = 2
            elif fits(None, x - 1, r, False, color):
                x -= 1
                done = 2
            if done == 2:
                lockf = tick_frame(rest_from(color, x, r, False), thr)
        f += rstep
    t1 = f
    # ---- 2. lateral steps; the driver decides frame t with the row after frame t-1
    d = abs(col - x)
    r = row_at(max(t1 - 1, 0), thr)
    sd = 1 if col > x else -1
    for i in range(1, d + 1):
        if tap is None:
            ti = t1 if i == 1 else t1 + 16 + 6 * (i - 2)
        else:
            ti = t1 + (i - 1) * tap
        if ti >= lockf:                                        # (a) locked in the previous column first
            return False
        y = free_rows_below(color, row_at(ti - 1, thr), min(x, col), max(x, col))
        if DT[y] == 0:                                         # (c) DISTGATE budget 0 -> aim = here -> soft drop
            return False
        r = row_at(ti, thr)
        if not fits(None, x + sd, r, vert, color):             # (b) destination blocked at this row
            return False
        x += sd
        lockf = tick_frame(rest_from(color, x, r, vert), thr)
    # ---- 3. aligned: it falls straight from its current row; exact iff that is the straight-drop rest
    return rest_from(color, x, r, vert) == straight_rest(top, x, vert)


def reach_mask_fw(color, thr, tap=None, rot_margin=0):
    top = tops(color)
    out = [0] * 32
    for a in range(32):
        var, col = a // 8, a % 8
        vert = var in (2, 3)
        if col < 0 or (not vert and col + 1 >= COLS):
            continue
        if rest(top, col, vert) - (1 if vert else 0) < 0:
            continue
        out[a] = 1 if reachable(color, top, thr, var, col, tap, rot_margin) else 0
    if not any(out):
        out = [1] * 32
    return out
