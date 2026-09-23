"""vs_sim — offline TWO-BOARD Dr. Mario VS simulator (the self-play arena).

Event-driven race on the travel-time clock (dt = 0.6s + 0.35s/row of fall): whichever side's
placement completes first acts; combos transfer garbage to the OTHER board per the extracted ROM
rules (MECHANICS_NES.md sec 5): 2+ simultaneous lines send, more lines = more halves, and garbage
lands only in columns {1,2,3,5,6,7} (cols 0/4 immune -- extracted, UNVERIFIED vs ROM).
Line count is approximated from cleared CELLS (halves = min(4, cells//3), sent when cells>=6);
refine against the disassembly before any ship-adjacent claim.
Both sides draw the same pill stream (same seed -> same viruses + same sequence, NES VS convention).
Win = clear all viruses; loss = spawn blocked; cap = tie on remaining viruses.
"""
import numpy as np, random

T_LAT, FPR = 0.6, 0.35
GCOLS = [1, 2, 3, 5, 6, 7]

def _mk_env(level, seed):
    from drmario.faithful_env import FaithfulDrMarioEnv
    from nes_pills import NesPillSource
    env = FaithfulDrMarioEnv(level=level, seed=seed, max_pills=1200)
    env.reset(); NesPillSource(seed=seed).attach(env)
    env.cur = env._rand_pill(); env.nxt = env._rand_pill()
    return env


def _n_simultaneous_lines(board):
    """Count distinct H and V runs of >=4 on the current board (pre-resolve)."""
    g = board.color
    n = 0
    rows, cols = board.rows, board.cols
    empty = 0
    for r in range(rows):
        c = 0
        while c < cols:
            v = int(g[r, c])
            if v == empty:
                c += 1
                continue
            c2 = c
            while c2 < cols and int(g[r, c2]) == v:
                c2 += 1
            if c2 - c >= 4:
                n += 1
            c = c2
    for c in range(cols):
        r = 0
        while r < rows:
            v = int(g[r, c])
            if v == empty:
                r += 1
                continue
            r2 = r
            while r2 < rows and int(g[r2, c]) == v:
                r2 += 1
            if r2 - r >= 4:
                n += 1
            r = r2
    return n

def _inject(board, rng, halves, gcols=None):
    # Reuse pressure_rig's proven injector (first-empty-row, LINK_NONE, settle) but restrict the
    # column draw to the garbage-legal set by retrying the rng seed convention is bypassed here:
    # we inline the same body with GCOLS.
    from drmario.faithful_game import EMPTY, LINK_NONE
    pool = list(gcols) if gcols is not None else list(GCOLS)
    cols = rng.sample(pool, min(halves, len(pool)))
    placed = 0
    for c in cols:
        color = rng.randint(1, 3)
        if board.color[0, c] != EMPTY: continue
        r = 0
        while r < board.rows and board.color[r, c] != EMPTY: r += 1
        board.color[r, c] = color; board.is_virus[r, c] = False; board.link[r, c] = LINK_NONE
        placed += 1
    if placed:
        board._apply_gravity()
        board.resolve()
    return placed

def _col_h_board(board, c):
    color = board.color
    rows = board.rows
    for r in range(rows):
        if int(color[r, c]) != 0:
            return rows - r
    return 0


def _bottle_feats(board):
    maxh = 0
    for c in range(board.cols):
        h = _col_h_board(board, c)
        if h > maxh:
            maxh = h
    return {
        "maxh": maxh,
        "spawn_h": max(_col_h_board(board, 3), _col_h_board(board, 4)),
        "fill": int(np.count_nonzero(board.color)),
    }


def play_vs(seed, level, wA, flA, wB, flB, wt=0, ws=0, send_rule="cells",
            gcols=None, halves_cap=4):
    """ws=0 matches cart DRSTRAND default. Loop gens 0-2 used ws=20.
    send_rule: 'cells' (v1 proxy, cells>=6 -> min(4,cells//3)) or
    'lines' (ROM-shaped: first-step simultaneous lines>=2 -> min(4, n_lines)).
    gcols=None uses GCOLS {1,2,3,5,6,7}; pass range(8) to include spawn-adjacent 0/4.
    halves_cap default 4 (ROM-ish)."""
    gcols = list(GCOLS if gcols is None else gcols)
    import pressure_rig as PR
    from fb import FB
    import root_search as RS
    S = []
    for w, fl in ((wA, flA), (wB, flB)):
        S.append({"env": _mk_env(level, seed), "w": w, "fl": fl, "t": 0.0,
                  "pills": 0, "sent": 0, "recv": 0, "combo_events": 0, "mode_swaps": 0})
    rng = random.Random(seed * 77 + 5)
    while True:
        i = 0 if S[0]["t"] <= S[1]["t"] else 1
        me, op = S[i], S[1 - i]
        env = me["env"]
        if env.board.virus_count() == 0: return _fin(S, i, "clear")
        fb = FB.from_board(env.board)
        col, vir = RS.board_flat_from_fb(fb)
        # OPPONENT CONTEXT (owner directive 9/19: "add state for p2, the entire board really").
        # P2's board is CONSTANT for the whole search of one pill, so context enters as a per-pill
        # weight-set selection — silicon-cheap (latched regs + compares), zero cost per leaf.
        w_use, fl_use = me["w"], me["fl"]
        opp_env = op["env"]
        own_f = _bottle_feats(env.board)
        opp_f = _bottle_feats(opp_env.board)
        ctx = {"own_vleft": env.board.virus_count(), "opp_vleft": opp_env.board.virus_count(),
               "own_t": me["t"], "opp_t": op["t"],
               "own_maxh": own_f["maxh"], "opp_maxh": opp_f["maxh"],
               "own_spawn_h": own_f["spawn_h"], "opp_spawn_h": opp_f["spawn_h"],
               "own_fill": own_f["fill"], "opp_fill": opp_f["fill"],
               "own_recv": me["recv"], "opp_recv": op["recv"]}
        if hasattr(me["w"], "decide"):
            a = me["w"].decide(col, vir, int(env.cur.a), int(env.cur.b),
                               int(env.nxt.a), int(env.nxt.b), ctx)
            c1b = None
        else:
            if callable(me["w"]):
                opp_pills = max(1, op["pills"])
                ctx.update({"opp_combo_rate": op["combo_events"] / opp_pills,
                            "opp_send_per_combo": op["sent"] / max(1, op["combo_events"]),
                            "opp_pace": op["t"] / opp_pills,
                            "opp_maxh": max((16 - min((r for r in range(16) if opp_env.board.color[r][c] != 0), default=16))
                                             for c in range(8))})
                w_use, fl_use, swapped = me["w"](ctx)
                me["mode_swaps"] += int(swapped)
            a, c1b = PR._choose_base(col, vir, int(env.cur.a), int(env.cur.b),
                                     int(env.nxt.a), int(env.nxt.b), w_use, fl_use, wt, ws)
        if a is None: return _fin(S, 1 - i, "opp_stuck")
        var, cc = a // 8, a % 8
        cols_involved = [cc] if var in (2, 3) else [cc, min(cc + 1, 7)]
        hmax = 0
        for tc in cols_involved:
            filled = [r for r in range(16) if col[r * 8 + tc] != 0]
            h = 16 - min(filled) if filled else 0
            hmax = max(hmax, h)
        me["t"] += T_LAT + FPR * max(0, 16 - hmax)
        n_lines = 0
        if send_rule == "lines":
            clone = env.board.clone()
            orient, col, pill = env._decode(int(a))
            if clone.place_pill(pill, orient, col):
                n_lines = _n_simultaneous_lines(clone)
        occ_before = int(np.count_nonzero(env.board.color))
        _, _, term, trunc, info = env.step(int(a))
        me["pills"] += 1
        if term:
            if info["won"]: return _fin(S, i, "clear")
            return _fin(S, 1 - i, "opp_topout")
        if trunc: return _fin(S, None, "cap")
        cleared = max(0, occ_before + 2 - int(np.count_nonzero(env.board.color)))
        if send_rule == "lines":
            fire = n_lines >= 2
            halves = min(halves_cap, n_lines) if fire else 0
        else:
            fire = cleared >= 6
            halves = min(halves_cap, cleared // 3) if fire else 0
        if fire:
            me["combo_events"] += 1
            got = _inject(op["env"].board, rng, halves, gcols=gcols)
            me["sent"] += got; op["recv"] += got
            if op["env"].board.spawn_blocked(): return _fin(S, i, "opp_crushed")
        if me["pills"] > 1100: return _fin(S, None, "cap")

def _fin(S, winner, how):
    return {"winner": winner, "how": how,
            "t": [round(s["t"], 1) for s in S], "pills": [s["pills"] for s in S],
            "sent": [s["sent"] for s in S], "combos": [s["combo_events"] for s in S],
            "vleft": [s["env"].board.virus_count() for s in S], "swaps": [s["mode_swaps"] for s in S]}
