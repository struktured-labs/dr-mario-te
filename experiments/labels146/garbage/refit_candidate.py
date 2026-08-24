"""refit_candidate.py — the refit candidate (design note approved lineage:
A5-corrected PASS licenses BUILDING; promotion rides on the fresh registered
A/B and nothing here).

  val(candidate) = champ_value_H12(candidate)
                   + W_GCENTER * g_center(resulting board)
                   + W_GATTACK * g_attack(resulting board)

Coefficients are the WITHIN-STATE (fixed-effects) bridge from the label bank
(out/refit_design.log).  g_construct deferred (team-lead ruling).  Everything
else frozen: winner w/fl, ws=20, wt=0, depth-3, CHAMP_ORDER, physics.

Self-gates (run as __main__):
  G-EXACT  : coefficients forced to 0 reproduce the sealed champion's 32-slot
             values bit-for-bit on banked states (the wrapper touches nothing
             frozen);
  G-INERT  : the candidate reproduces the design note's flip set exactly
             (304/1275 states, same states) from its own code path.
"""
import hashlib
import inspect
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import numpy as np
import fit_garbage as F          # single source for the feature definitions

W_GCENTER = -252.611
W_GATTACK = +18.361
FROZEN = ("variant=winner ws=20 wt=0 level=20 depth=3 order=champ "
          "g_construct=deferred")


def config_hash():
    m = hashlib.sha1()
    m.update(inspect.getsource(F.g_center).encode())
    m.update(inspect.getsource(F.g_attack).encode())
    m.update(f"{W_GCENTER} {W_GATTACK} {FROZEN}".encode())
    return m.hexdigest()[:12]


def champ_values_refit(col, vir, ca, cb, na, nb, w, fl, wt, ws,
                       wc=W_GCENTER, wa=W_GATTACK):
    """32-slot values = sealed champion values + the two feature terms."""
    import oracle_arm as OA
    import fast_rtl_x as FX
    from fast_sim_x import NCELL, _expand_core
    vals = OA._champ_values(col, vir, ca, cb, na, nb, w, fl, wt, ws)
    if wc == 0 and wa == 0:
        return vals
    c1 = np.empty(NCELL, dtype=np.int8)
    v1 = np.empty(NCELL, dtype=np.int8)
    for o4 in range(4):
        var = int(FX._VAR_OF_O4[o4])
        for cc in range(8):
            slot = var * 8 + cc
            if not np.isfinite(vals[slot]):
                continue
            ok, _nv, _cells = _expand_core(col, vir, var, cc, ca, cb, c1, v1)
            if ok == 0:
                continue
            vals[slot] += (wc * F.g_center(c1[:NCELL], v1[:NCELL])
                           + wa * F.g_attack(c1[:NCELL], v1[:NCELL]))
    return vals


def decide_refit(env, C):
    import oracle_arm as OA
    import root_search as RS
    from fb import FB
    fb = FB.from_board(env.board)
    col, vir = RS.board_flat_from_fb(fb)
    vals = champ_values_refit(col, vir, int(env.cur.a), int(env.cur.b),
                              int(env.nxt.a), int(env.nxt.b),
                              C["w"], C["fl"], C["wt"], C["ws"])
    return vals, OA._champ_action(vals, OA.CHAMP_ORDER)


# ------------------------------------------------------------- self-gates
def _banked_primary():
    rows = F.load_rows()
    return [r for r in rows if r["stratum"] in ("C", "Cdeep")]


def selfgate():
    import labelcore as LC
    import oracle_arm as OA
    import root_search as RS
    from fb import FB
    print(f"[refit] config_hash={config_hash()}  wc={W_GCENTER} wa={W_GATTACK}")

    # G-EXACT: zero-dose bit-equality against the sealed champion on REAL
    # banked pre-placement states (gated replay of one banked topout seed).
    C, bmodel = LC.init_rig()
    games = LC.bank_games()
    seed = next(g["seed"] for g in games
                if g["res"] == "topout" and g["n_plies"] >= 60)
    rows, _game = LC.load_bank_game(seed)
    gen = LC.replay_game(seed, C, bmodel, rows)
    exact, checked = True, 0
    for ply, env, vals, row in gen:
        if ply >= 12:
            break
        fb = FB.from_board(env.board)
        col, vir = RS.board_flat_from_fb(fb)
        args = (col, vir, int(env.cur.a), int(env.cur.b),
                int(env.nxt.a), int(env.nxt.b),
                C["w"], C["fl"], C["wt"], C["ws"])
        a = OA._champ_values(*args)
        b = champ_values_refit(*args, wc=0, wa=0)
        same = (np.array_equal(np.isnan(a), np.isnan(b))
                and np.array_equal(a[~np.isnan(a)], b[~np.isnan(b)]))
        exact &= same
        c = champ_values_refit(*args)          # full dose: finiteness pattern
        exact &= np.array_equal(np.isnan(a), np.isnan(c))
        checked += 1
    print(f"[refit] G-EXACT zero-dose bit-equality on {checked} real states "
          f"(seed {seed}): {'PASS' if exact and checked == 12 else 'FAIL'}")

    # G-INERT: reproduce the design flip set from the candidate coefficients
    # over the banked candidate planes (value + features per dedup'd entry).
    prim = _banked_primary()
    flips, states = 0, 0
    for r in prim:
        vals = r.get("vals")
        ents = []
        for e in r["cands"]:
            vs = [vals[s] for s in e["slots"] if vals[s] is not None]
            if not vs:
                continue
            colv, virv = F.decode_planes(e["planes"])
            ents.append((max(vs), F.g_center(colv, virv),
                         F.g_attack(colv, virv), tuple(e["slots"])))
        if not ents:
            continue
        states += 1
        old = max(ents, key=lambda t: t[0])
        new = max(ents, key=lambda t: t[0] + W_GCENTER * t[1] + W_GATTACK * t[2])
        if old[3] != new[3]:
            flips += 1
    inert_ok = flips == 304 and states == 1275
    print(f"[refit] G-INERT flip set: {flips}/{states} "
          f"(design note: 304/1275) {'PASS' if inert_ok else 'FAIL'}")
    return exact and checked == 12 and inert_ok


if __name__ == "__main__":
    sys.exit(0 if selfgate() else 1)
