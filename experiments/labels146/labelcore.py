"""labelcore.py — shared machinery for the labels-146 lane.

Everything here leans on the sealed champion-145 oracle lineage
(`experiments/eval47/stage2/oracle`, content from d3cb836): `_fork_label`,
`dist_seed`, `make_env`, `_advance`, `init_rig`.  This module adds only
(a) a REPLAY-WITH-GATE generator that walks a banked game and asserts, at
every ply, that the recomputed 32-candidate value vector and argmax equal the
banked row (cell-for-cell provenance for the state being labeled), and
(b) the per-state labeling routine (dedup'd candidates x N CRN dist-futures
forks).
"""
import base64
import gzip
import hashlib
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ORACLE = os.path.abspath(os.path.join(HERE, "..", "eval47", "stage2", "oracle"))
sys.path.insert(0, ORACLE)

import numpy as np  # noqa: E402

BANK = os.environ.get(
    "DRM_BANK",
    "/home/struktured/projects/dr-mario-champ145-wt/experiments/champ145/"
    "out/states")
LEVEL = 20
MAX_PILLS = 400
SEED_LO, SEED_HI = 30000, 32998


class ReplayMismatch(AssertionError):
    """The recomputed state diverged from the banked row — abort the seed."""


def load_bank_game(seed):
    """(rows, game) for one banked seed; rows exclude the trailing game row."""
    path = os.path.join(BANK, f"states_{seed}.jsonl.gz")
    with gzip.open(path, "rt") as fh:
        recs = [json.loads(l) for l in fh]
    assert "game" in recs[-1], path
    game = recs[-1]["game"]
    rows = recs[:-1]
    assert len(rows) == game["n_plies"], (seed, len(rows), game["n_plies"])
    return rows, game


def bank_games():
    """All banked game rows, ascending seed. Startup assert: 1,500 exactly."""
    seeds = sorted(int(f.split("_")[1].split(".")[0])
                   for f in os.listdir(BANK) if f.startswith("states_"))
    assert len(seeds) == 1500, len(seeds)
    assert all(SEED_LO <= s <= SEED_HI and s % 2 == 0 for s in seeds)
    out = []
    for s in seeds:
        _, g = load_bank_game(s)
        out.append(g)
    return out


def board_key(c1, v1, ncell):
    h = hashlib.sha1()
    h.update(bytes(c1[:ncell]))
    h.update(bytes(v1[:ncell]))
    return h.hexdigest()[:12]


def _round3(x):
    return None if not np.isfinite(x) else round(float(x), 3)


def compute_vals(env, w, fl, wt, ws):
    import oracle_arm as OA
    from fb import FB
    import root_search as RS
    fb = FB.from_board(env.board)
    col, vir = RS.board_flat_from_fb(fb)
    return OA._champ_values(col, vir, int(env.cur.a), int(env.cur.b),
                            int(env.nxt.a), int(env.nxt.b), w, fl, wt, ws)


def replay_game(seed, C, bmodel, rows, mutate_skip_ply=None):
    """Replay the banked game, GATED against the bank at every ply.

    Yields (ply, env, vals, row) BEFORE the banked action is applied, so the
    yielded env is the pre-placement decision state the bank describes.
    `mutate_skip_ply` is the M-stale mutant hook: at that ply the banked
    action is replaced with a different legal one — the NEXT ply's gate MUST
    then raise ReplayMismatch (gate liveness).
    Returns the terminal result string.
    """
    import oracle_arm as OA
    w, fl, wt, ws = C["w"], C["fl"], C["wt"], C["ws"]
    env = OA.make_env(seed, LEVEL, max_pills=MAX_PILLS)
    res = "stall"
    for ply in range(MAX_PILLS):
        if env.board.virus_count() == 0:
            res = "clear"
            break
        if ply >= len(rows):
            raise ReplayMismatch((seed, ply, "replay outlived bank"))
        row = rows[ply]
        vals = compute_vals(env, w, fl, wt, ws)
        got = [_round3(vals[s]) for s in range(32)]
        if got != row["vals"]:
            raise ReplayMismatch((seed, ply, "vals", got, row["vals"]))
        a = OA._champ_action(vals, OA.CHAMP_ORDER)
        if a != row["a"]:
            raise ReplayMismatch((seed, ply, "argmax", a, row["a"]))
        yield ply, env, vals, row
        if mutate_skip_ply is not None and ply == mutate_skip_ply:
            legal = [s for s in range(32) if np.isfinite(vals[s]) and s != a]
            a = legal[0]  # deliberately wrong action (M-stale mutant)
        r, _v = OA._advance(env, a, C, seed, bmodel)
        if r is not None:
            res = r
            break
    if mutate_skip_ply is None:
        ok_end = (ply == len(rows) - 1) or (res == "clear" and ply == len(rows))
        if not ok_end:
            raise ReplayMismatch((seed, "length", ply, len(rows), res))
    return res


def enumerate_candidates(env, dedup=True):
    """Unique post-placement resolved boards for the 32 slots.

    Returns list of dicts {slots, rep_slot, key, planes(b64 c1+v1)}, ordered
    by champion scan order of the representative (first-seen) slot.
    Unconditional never-same-board assert inside the dedup'd set (rule 7).
    """
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
                   "planes": base64.b64encode(
                       bytes(c1[:NCELL]) + bytes(v1[:NCELL])).decode()}
            ents.append(ent)
            if dedup:
                bykey[key] = ent
    if dedup:
        keys = [e["key"] for e in ents]
        assert len(keys) == len(set(keys)), "duplicate board in dedup'd set"
    return ents


def label_state(env, C, bmodel, seed, ply, n_samples, horizon):
    """Label every unique candidate with N CRN dist-future forks at `horizon`.

    Returns list (parallel to enumerate_candidates(env)) of
    {slots, rep_slot, key, planes, surv:[N], prog:[N]}.
    """
    import oracle_arm as OA
    w, fl, wt, ws = C["w"], C["fl"], C["wt"], C["ws"]
    ents = enumerate_candidates(env)
    for e in ents:
        e["surv"], e["prog"] = [], []
    for s in range(n_samples):
        fseed = OA.dist_seed(seed, ply, s)   # candidate-independent: CRN
        for e in ents:
            surv, prog = OA._fork_label(env, e["rep_slot"], C, fseed, bmodel,
                                        w, fl, wt, ws, horizon)
            e["surv"].append(int(surv))
            e["prog"].append(int(prog))
    return ents


def init_rig():
    import oracle_arm as OA
    C, bmodel = OA.init_rig(model="lulu", level=LEVEL)
    C = dict(C)
    C["level"] = LEVEL
    return C, bmodel


def champ_entry(ents, a):
    """The candidate entry containing the champion's chosen slot."""
    for e in ents:
        if a in e["slots"]:
            return e
    raise AssertionError(("champion slot not among candidates", a))
