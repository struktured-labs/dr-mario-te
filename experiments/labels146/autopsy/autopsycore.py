"""autopsycore.py — clean-solo counterfactual labeling for the L11
clean-failure autopsy (PREREG_AUTOPSY + AMENDMENT A1).

Differences from labelcore.py, each one a REGISTERED deviation:
  §1  the replay gate anchors on the census MOVE TRACE + terminal state
      (census games carry no per-ply 32-value bank);
  §2  the rig is CLEAN SOLO — level 11, ws=20, max_pills=300, NO injection;
  §3  stall games are labeled with a CLEAR claim at H_stall=50 (survival is
      vacuous when nothing can kill you);
  A1  the fork's future is resampled by SWAPPING THE CAPSULE STREAM, because
      dist_seed reaches a rollout only through garbage injection and there is
      none here.  cur/nxt are kept (visible to the champion at the decision).

Everything else — _champ_values, _champ_action, CHAMP_ORDER, _expand_core
dedup, dist_seed, PillDraw — is the sealed champion-145 oracle lineage,
imported, never reimplemented.  The replay gate proves it: OA._champ_values +
OA._champ_action reproduces the census trace action-for-action.
"""
from __future__ import annotations

import base64
import copy
import hashlib
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ORACLE = os.path.abspath(os.path.join(HERE, "..", "..", "eval47", "stage2", "oracle"))
for p in (ORACLE, os.path.join(ORACLE, "bootstrap"),
          "/home/struktured/projects/dr-mario-qa-wt/experiments",
          "/home/struktured/projects/dr-mario-qa-wt/experiments/adversary"):
    if p not in sys.path:
        sys.path.insert(0, p)

LEVEL = 11          # adversary_harness.LEVEL — the standing target class
WS = 20             # adversary_harness.WS — the shipped strand20 dose
MAX_PILLS = 300     # adversary_harness.play_seed default
H_TOPOUT = 25       # the pilot's mechanically-chosen campaign horizon
H_STALL = 50        # PREREG_AUTOPSY §3
N_SAMPLES = 8


class ReplayMismatch(AssertionError):
    """The recomputed decision diverged from the census trace — abort the seed."""


def init_rig():
    """Champion weights at L11/ws=20.  init_rig also brings up pressure_rig,
    whose injection we then never call (clean solo)."""
    import oracle_arm as OA
    C, bmodel = OA.init_rig(model="lulu", level=LEVEL, wt=0, ws=WS)
    C = dict(C)
    C["level"] = LEVEL
    return C, bmodel


def _advance_clean(env, action):
    """ONE placement, no injection — adversary_harness.play_seed's loop body.

    Returns (res, viruses_at_end) with res None while the game continues.
    """
    _obs, _r, term, trunc, info = env.step(int(action))
    if term:
        if info["won"]:
            return "clear", 0
        return "topout", int(env.board.virus_count())
    if trunc:
        return "stall", int(env.board.virus_count())
    return None, None


def make_clean_env(seed):
    import oracle_arm as OA
    return OA.make_env(seed, LEVEL, max_pills=MAX_PILLS)


def champ_decide(env, C):
    """(vals, action) for the current state.  action is None iff spawn-blocked."""
    import oracle_arm as OA
    import root_search as RS
    from fb import FB
    fb = FB.from_board(env.board)
    col, vir = RS.board_flat_from_fb(fb)
    vals = OA._champ_values(col, vir, int(env.cur.a), int(env.cur.b),
                            int(env.nxt.a), int(env.nxt.b),
                            C["w"], C["fl"], C["wt"], C["ws"])
    return vals, OA._champ_action(vals, OA.CHAMP_ORDER)


def replay_census_game(seed, C, row, want_plies=None, mutate_skip_ply=None,
                       sink=None):
    """Replay one census failure, GATED on the trace at every ply (§1).

    Yields (ply, env, vals, a_true) BEFORE the placement, for plies in
    `want_plies` (None = all).  Raises ReplayMismatch on any divergence.
    The TERMINAL gate (result, pills, viruses_left, n_moves) runs at the end.

    `sink` (a dict, optional) receives the TERMINAL board planes and result —
    the clustering rule for the last-virus notch needs the final board, and
    census rows carry one only for topouts.

    `mutate_skip_ply` is the M-stale hook: substitute a different legal action
    there, and the gate MUST then fail (liveness of the negative).
    """
    trace = [(int(i), int(a)) for i, a in row["trace"]]
    env = make_clean_env(seed)
    res, vend = "stall", None
    for ply in range(MAX_PILLS):
        if env.board.virus_count() == 0:
            res = "clear"
            break
        vals, a = champ_decide(env, C)
        if a is None:
            res = "topout"
            break
        if ply >= len(trace):
            raise ReplayMismatch((seed, ply, "replay outlived the trace"))
        i_true, a_true = trace[ply]
        if a != a_true:
            raise ReplayMismatch((seed, ply, "argmax", a, a_true))
        if want_plies is None or ply in want_plies:
            yield ply, env, vals, a_true
        if mutate_skip_ply is not None and ply == mutate_skip_ply:
            legal = [s for s in range(32) if np.isfinite(vals[s]) and s != a]
            if legal:
                a_true = legal[0]        # M-stale: a deliberately wrong action
        res, vend = _advance_clean(env, a_true)
        if res is not None:
            break
    if sink is not None:
        sink["result"] = res
        sink["color"] = np.asarray(env.board.color).tolist()
        sink["virus"] = np.asarray(env.board.is_virus).astype(int).tolist()
        sink["pills"] = int(env.pills_placed)
    # TERMINAL GATE — the second half of the §1 anchor
    if mutate_skip_ply is None:
        got = (res, int(env.pills_placed), int(env.board.virus_count()), len(trace))
        want = (row["result"], int(row["pills"]), int(row["viruses_left"]),
                int(row["n_moves"]))
        if got != want:
            raise ReplayMismatch((seed, "terminal", got, want))
    return res


# --------------------------------------------------------------- candidates
def board_key(c1, v1, ncell):
    h = hashlib.sha1()
    h.update(bytes(c1[:ncell]))
    h.update(bytes(v1[:ncell]))
    return h.hexdigest()[:12]


def enumerate_candidates(env, dedup=True):
    """Unique post-placement resolved boards for the 32 slots (labelcore's
    routine, imported by content so the autopsy is self-contained)."""
    import fast_rtl_x as FX
    from fast_sim_x import NCELL, _expand_core
    from fb import FB
    import root_search as RS
    fb = FB.from_board(env.board)
    col, vir = RS.board_flat_from_fb(fb)
    ca, cb = int(env.cur.a), int(env.cur.b)
    c1 = np.empty(NCELL, dtype=np.int8)
    v1 = np.empty(NCELL, dtype=np.int8)
    ents, bykey = [], {}
    for o4 in range(4):
        var = int(FX._VAR_OF_O4[o4])
        for cc in range(8):
            ok, _nv, _cells = _expand_core(col, vir, var, cc, ca, cb, c1, v1)
            if ok == 0:
                continue
            slot = var * 8 + cc
            key = board_key(c1, v1, NCELL)
            if dedup and key in bykey:
                bykey[key]["slots"].append(slot)
                continue
            ent = {"slots": [slot], "rep_slot": slot, "key": key,
                   "vir_after": int(np.count_nonzero(v1[:NCELL])),
                   "planes": base64.b64encode(
                       bytes(c1[:NCELL]) + bytes(v1[:NCELL])).decode()}
            ents.append(ent)
            if dedup:
                bykey[key] = ent
    if dedup:
        keys = [e["key"] for e in ents]
        assert len(keys) == len(set(keys)), "duplicate board in dedup'd set"
    return ents


def champ_entry(ents, a):
    for e in ents:
        if a in e["slots"]:
            return e
    raise AssertionError(("champion slot not among candidates", a))


# -------------------------------------------------------------------- forks
def _swap_stream(e, fseed):
    """AMENDMENT A1.1 — resample the UNSEEN future.

    cur/nxt are already drawn and both are visible to the champion at the
    decision ply, so they are left alone; every SUBSEQUENT capsule comes from
    an independent NES stream keyed by fseed.  PillDraw (not a lambda) so the
    deepcopy cannot share a cursor.
    """
    import oracle_arm as OA
    from nes_pills import NesPillSource
    e._rand_pill = OA.PillDraw(NesPillSource(seed=int(fseed) & 0xFFFF))


def fork_clean(env, action, C, horizon, fseed=None, extend_cap=False):
    """Play `action` then up to horizon-1 champion pills on a CLONE.

    fseed None  -> CLAIRVOYANT (the true stream continues; A1.2)
    fseed set   -> DIST (stream swapped after the visible capsules; A1.1)

    Returns dict(res, survived, cleared, vir_cleared, pills, plies).
    Mirrors oracle_arm._fork_label's structure exactly; the return is richer
    because §3's stall claim needs CLEARED, which _fork_label's survived=1
    conflates with "still alive at the horizon".
    """
    e = copy.deepcopy(env)
    if fseed is not None:
        _swap_stream(e, fseed)
    if extend_cap:
        # PREREG_AUTOPSY §3: a stall fork must get its FULL horizon — the
        # original 300-pill cap would truncate it near the end of the game and
        # silently score "could not clear" for states that were never given
        # the plies to try.
        e.max_pills = int(e.pills_placed) + int(horizon) + 1
    v0 = int(e.board.virus_count())
    p0 = int(e.pills_placed)
    res, vend = _advance_clean(e, action)
    n = 1
    while res is None and n < horizon:
        if e.board.virus_count() == 0:
            res = "clear"
            break
        _vals, a = champ_decide(e, C)
        if a is None:
            res = "topout"
            break
        res, vend = _advance_clean(e, a)
        n += 1
    if res is None:
        res = "alive"
    vleft = 0 if res == "clear" else int(e.board.virus_count())
    return {"res": res,
            "survived": int(res != "topout"),
            "cleared": int(res == "clear"),
            "vir_cleared": v0 - vleft,
            "pills": int(e.pills_placed) - p0,
            "plies": n}


def label_state(env, C, seed, ply, horizon, n_samples=N_SAMPLES,
                clair=True, swap=True, extend_cap=False, sample_offset=0):
    """Label every unique candidate: n_samples DIST forks (+1 clair fork).

    `swap=False` is M-INERT — the dose exactly as originally registered, which
    A1.3 requires to show ZERO spread.  `sample_offset` shifts the CRN sample
    indices: the §4 POSITIVE CONTROL re-labels a firing ply at offset 1000, and
    the claim must re-fire on futures it has never seen.
    """
    import oracle_arm as OA
    ents = enumerate_candidates(env)
    for e in ents:
        e["surv"], e["clear"], e["vc"] = [], [], []
    for s in range(sample_offset, sample_offset + n_samples):
        fseed = OA.dist_seed(seed, ply, s)      # candidate-independent: CRN
        for e in ents:
            r = fork_clean(env, e["rep_slot"], C, horizon,
                           fseed=(fseed if swap else None),
                           extend_cap=extend_cap)
            e["surv"].append(r["survived"])
            e["clear"].append(r["cleared"])
            e["vc"].append(r["vir_cleared"])
    if clair:
        for e in ents:
            r = fork_clean(env, e["rep_slot"], C, horizon, fseed=None,
                           extend_cap=extend_cap)
            e["clair_surv"] = r["survived"]
            e["clair_clear"] = r["cleared"]
            e["clair_vc"] = r["vir_cleared"]
    return ents


# ------------------------------------------------------------- claim rules
def _best(ents, key_fn, vals):
    """argmax of key_fn, ties broken by CHAMPION VALUE then CHAMPION SCAN
    ORDER (PREREG_LABELS §5, inherited).  Deterministic by construction."""
    import oracle_arm as OA
    rank = {s: i for i, s in enumerate(OA.CHAMP_ORDER)}

    def sort_key(e):
        v = vals[e["rep_slot"]]
        v = float(v) if np.isfinite(v) else -np.inf
        return (key_fn(e), v, -rank[e["rep_slot"]])
    return max(ents, key=sort_key)


def claim_topout(ents, a_champ, vals):
    """§4: surv_best - surv_champ >= 5 of 8.  Returns None or a claim dict."""
    ch = champ_entry(ents, a_champ)
    sc = sum(ch["surv"])
    best = _best(ents, lambda e: sum(e["surv"]), vals)
    sb = sum(best["surv"])
    if sb - sc >= 5:
        return {"kind": "topout", "surv_champ": sc, "surv_best": sb,
                "d": sb - sc, "champ_key": ch["key"], "best_key": best["key"],
                "best_slot": int(best["rep_slot"])}
    return None


def claim_stall(ents, a_champ, vals):
    """§4: clear_best >= 6 of 8 AND clear_champ <= 2 of 8."""
    ch = champ_entry(ents, a_champ)
    cc = sum(ch["clear"])
    best = _best(ents, lambda e: sum(e["clear"]), vals)
    cb = sum(best["clear"])
    if cb >= 6 and cc <= 2:
        return {"kind": "stall", "clear_champ": cc, "clear_best": cb,
                "d": cb - cc, "champ_key": ch["key"], "best_key": best["key"],
                "best_slot": int(best["rep_slot"])}
    return None
