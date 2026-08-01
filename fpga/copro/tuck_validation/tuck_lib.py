ROWS, COLS, EMPTY = 16, 8, 0xFF

def occ(board, r, c):
    return board[r * COLS + c] != EMPTY

def first_occ(board, c):
    for r in range(ROWS):
        if occ(board, r, c):
            return r
    return ROWS

def rest_row(board, c, from_r):
    r = from_r
    while r + 1 < ROWS and not occ(board, r + 1, c):
        r += 1
    return r

def straight_rest(board, c):
    """resting row of a straight drop into c, or None if c is blocked at row 0"""
    if occ(board, 0, c):
        return None
    return rest_row(board, c, 0)

def enum_full(board):
    """the enumerator's own choice INCLUDING the target column it optimised for"""
    best = None
    for c in range(COLS):
        fc = first_occ(board, c)
        if fc == 0:
            continue
        sd = fc - 1
        for side in (0, 1):
            a = c - 1 if side == 0 else c + 1
            if not (0 <= a < COLS):
                continue
            fa = first_occ(board, a)
            if fa == 0:
                continue
            ra = fa - 1
            r = fc
            while r <= ra:
                if not occ(board, r, c):
                    rf = rest_row(board, c, r)
                    if rf > sd and (best is None or rf > best[0]):
                        best = (rf, a, r, c)
                r += 1
    if best is None:
        return None
    return {"rest": best[0], "approach": best[1], "trigger": best[2], "target": best[3]}
