#!/usr/bin/env python3
"""STAGE 2 corpus builder -- `s2lulu`: per-decision records for the champion
under dr. lulu's fitted bursty pressure.

PRE-REGISTERED in PREREG_STAGE2.md (commit b9725fc), written and committed
BEFORE this file ran and before any model saw any data.

WHAT THIS FIXES vs stage 1 (recon A's ranked leak risks):
  #4 COVERAGE COLLAPSE -- stage 1 kept only the last K=10 decisions of failure
     games and matched controls on EXACT max_height, which collapsed the whole
     corpus to max_height >= 13. It never saw an ordinary-play board, i.e. never
     saw the population where the STRUCTURAL LAW says breakage is decided.
     HERE: EVERY decision of every extracted game is kept, and there is NO
     stratum matching and NO dropping. Height is a SLICE, never a filter.
  #5 MOST-DANGEROUS ROWS DROPPED -- nothing is dropped.
  #7 THE LABEL DOESN'T VARY WITH THE MOVE -- boards + all 32 candidate root
     values are stored, so per-candidate features for every sibling of every
     decision are DERIVABLE without a re-run (see s2_features.py). That is what
     makes a within-decision endpoint (prereg B3) possible at all.
  #8 EVAL-HACKING ON THE INJECTION SCHEDULE -- `end_kind`, `since_last_garbage`,
     `clear_size_this_ply` and `garbage_this_ply` are stored so the model can be
     held out on them.
  split -- BY GAME (seed % 10 in {7,8,9}), never by decision.

FIDELITY GATE (this file refuses to write a corpus otherwise). The replayer is a
copy of p0_ab.play_one(seed, forced=False) -- the exact loop that produced
lulu_census.jsonl -- plus per-decision instrumentation. On the gate seeds it must
reproduce BOTH:
  (a) the census row: res, pills, garbage, dies_ahead; AND
  (b) the FULL return dict of the real rig pressure_rig.play(seed), which
      includes funnel / funnel_mm / mm_vert / stranded_final / tower_final /
      viruses_left_at_end. Those are TRACE-DERIVED statistics (funnel_mm counts
      repeated same-column verticals landing on a mismatched colour), so
      agreeing on them is a far stronger equality than res/pills/garbage: it
      pins the whole action sequence, not just the outcome. The census rows
      carry no trace and no terminal board, so this is the strongest equality
      available for the lulu regime.

KILLED MUTANTS (house law: a check that cannot fail is not a check). Three, each
of which MUST break the gate:
  M1 ws=0            -- wrong evaluator weights
  M2 garbage rng +1  -- wrong injection stream
  M3 tie-break flip  -- same values, columns enumerated in reverse. Recon C
     measured 36.0% of all plies have the top value TIED among >=2 legal
     actions, so a tie-break change alone must move the trace. This mutant
     exists to prove the gate is sensitive to the ENUMERATION ORDER, which is
     what actually decides a third of the champion's moves.

Usage:
  build_s2_corpus.py --gate-only
  build_s2_corpus.py --run --workers 6 --classes fail,stall,ctrl
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import random
import sys
import time
from concurrent.futures import ProcessPoolExecutor, as_completed

HERE = os.path.dirname(os.path.abspath(__file__))
EV = os.path.dirname(HERE)                      # .../experiments/eval47
QA = os.path.dirname(EV)                        # .../experiments
JD = os.path.join(EV, "jointdig")
for _p in (EV, QA, JD, os.path.join(EV, "vocab2")):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import numpy as np  # noqa: E402

import pressure_rig as PR  # noqa: E402

RESULTS = os.path.join(HERE, "results")
CENSUS = os.path.join(JD, "results_hetzner", "lulu_census.jsonl")
CENSUS_REMOTE = "/home/struktured/projects/dr-mario-qa-wt/experiments/eval47/" \
                "jointdig/results_hetzner/lulu_census.jsonl"

# ---- PRE-REGISTERED CONSTANTS (PREREG_STAGE2.md sections 2.4, 4) ------------
SAMPLE_RNG = 20260810          # cleared-game sample + label permutation
CTRL_SAMPLE_LOCAL = 1700       # local half; the Hetzner job takes ALL clears
HOLD_MOD, HOLD_SET = 10, (7, 8, 9)
GATE_N_TOPOUT, GATE_N_STALL, GATE_N_CLEAR = 12, 6, 6
GATE_RNG = 1234
LEVEL, WT, WS = 11, 0, 20

OUTCOME_CODE = {"clear": 0, "topout": 1, "stall": 2}
# end_kind doubles as recon C's MECHANISM partition:
#   T_GARB  = garbage_topout            (spawn blocked right after a volley)
#   T_PLACE = step_topout               (env.step returned terminal, self-inflicted)
#   T_TRUNC = stall                     (300-pill budget expired, still alive)
#   T_NOMOVE= choose_none               (recon C measured this as EXACTLY ZERO)
END_KIND = {"clear": 0, "step_clear": 1, "garbage_clear": 2,
            "step_topout": 3, "garbage_topout": 4, "stall": 5, "choose_none": 6}
MECHANISM = {"T_GARB": 0, "T_PLACE": 1, "T_TRUNC": 2, "T_NOMOVE": 3, "CLEAR": 4}


def load_lulu():
    from bursty_model import BurstyPressureModel
    j = json.load(open(os.path.join(EV, "results", "dr_lulu_20260808_fit.json")))
    return BurstyPressureModel(
        volley_sizes=j["volley_sizes"], gap_samples=j["gap_samples"],
        p_within_k=j["p_within_k"], k_seconds=j["k_seconds"],
        n_volleys=j["n_volleys"], n_clears=j["n_clears"],
        n_matches=j["n_matches"], opponent_of=j["opponent_of"], meta=j["meta"])


# ------------------------------------------------------------------ chooser
def decide_all32(col, vir, ca, cb, na, nb, w, fl, wt, ws, tie_flip=False):
    """Replica of pressure_rig._choose_base that ALSO dumps all 32 candidate
    root values. vals[var*8+cc] = value, NaN where the drop is illegal.

    The o4-then-column enumeration order and the STRICT `>` comparison are
    load-bearing: recon C measured 36.0% of plies with a tied top value, so the
    order IS the tie-break and a copy that gets it wrong picks different moves.
    Mutant M3 (tie_flip) reverses the column order to prove the gate sees this.
    """
    import fast_rtl_x as FX
    import root_search as RS
    from fast_sim_x import NCELL, _expand_core
    from terms47 import g_tower, g_stranded

    c1 = np.empty(NCELL, dtype=np.int8)
    v1 = np.empty(NCELL, dtype=np.int8)
    vals = np.full(32, np.nan, dtype=np.float32)
    best_val, best_a, best_c1 = None, None, None
    n_legal = 0
    ccs = range(7, -1, -1) if tie_flip else range(8)
    for o4 in range(4):
        var = int(FX._VAR_OF_O4[o4])
        for cc in ccs:
            ok, nv, cells = _expand_core(col, vir, var, cc, ca, cb, c1, v1)
            if ok == 0:
                continue
            n_legal += 1
            val = RS._root_value(c1, v1, nv, cells, na, nb, 8,
                                 FX._W_EXCAV_SHIP, FX._W_HANG_SHIP, w, fl)
            if wt:
                val -= wt * g_tower(c1, v1, PR.H0)
            if ws:
                val -= ws * g_stranded(c1, v1)
            vals[var * 8 + cc] = val
            if best_val is None or val > best_val:
                best_val, best_a, best_c1 = val, var * 8 + cc, c1.copy()
    return best_a, best_c1, vals, n_legal


def covariates(col, vir):
    b = np.asarray(col).reshape(16, 8)
    occ_rows = np.nonzero(b.any(axis=1))[0]
    max_h = 0 if occ_rows.size == 0 else 16 - int(occ_rows[0])
    return max_h, int(np.count_nonzero(np.asarray(vir))), int(np.count_nonzero(b))


# ----------------------------------------------------------------- replayer
def instrumented_play(seed, ws=WS, garbage_rng_offset=0, tie_flip=False,
                      keep=True):
    """Copy of p0_ab.play_one(seed, forced=False) on the BURSTY (lulu) path,
    with per-decision instrumentation and recon C's mechanism label.

    ws / garbage_rng_offset / tie_flip are MUTANT HOOKS, never data: the
    fidelity gate must BREAK when any of them is set.
    """
    from drmario.faithful_env import FaithfulDrMarioEnv
    from nes_pills import NesPillSource
    from fb import FB
    import root_search as RS
    from terms47 import g_tower, g_stranded
    from bursty_model import inject_bursty_garbage

    C = PR._C
    level, wt, w, fl = C["level"], C["wt"], C["w"], C["fl"]
    bmodel = C["bursty_model_obj"]

    env = FaithfulDrMarioEnv(level=level, seed=seed, max_pills=300)
    env.reset()
    NesPillSource(seed=seed).attach(env)
    env.cur = env._rand_pill()
    env.nxt = env._rand_pill()

    res, end_kind = "stall", "stall"
    garbage_injected = 0
    v_at_topout = None
    col = vir = None
    # trace-derived statistics -- copied verbatim from pressure_rig.play so the
    # gate can compare them against the REAL rig's return dict
    funnel = funnel_mm = mm_vert = 0
    last_vert_col = -1
    last_garbage_pill = -1
    recs = []
    trace = []

    for _ in range(300):
        fb = FB.from_board(env.board)
        if env.board.virus_count() == 0:
            res, end_kind = "clear", "clear"
            break
        col, vir = RS.board_flat_from_fb(fb)
        ca, cb = int(env.cur.a), int(env.cur.b)
        na, nb = int(env.nxt.a), int(env.nxt.b)
        a, c1b, vals, n_legal = decide_all32(col, vir, ca, cb, na, nb, w, fl,
                                             wt, ws, tie_flip=tie_flip)
        if a is None:
            end_kind = "choose_none"      # recon C: measured ZERO times
            break
        var, cc = a // 8, a % 8
        vertical = var in (2, 3)
        mism = False
        if vertical:
            newr = [r for r in range(16) if c1b[r * 8 + cc] != col[r * 8 + cc]]
            if newr:
                rb = max(newr)
                if rb < 15 and col[(rb + 1) * 8 + cc] != 0:
                    mism = c1b[rb * 8 + cc] != col[(rb + 1) * 8 + cc]
        if mism:
            mm_vert += 1
        if vertical and cc == last_vert_col:
            funnel += 1
            if mism:
                funnel_mm += 1
        last_vert_col = cc if vertical else -1

        if keep:
            max_h, nvir, occ = covariates(col, vir)
            recs.append({
                "seed": seed, "pill_idx": int(env.pills_placed),
                "col": np.asarray(col, dtype=np.int8).copy(),
                "vir": np.asarray(vir, dtype=np.int8).copy(),
                "cur": (ca, cb), "nxt": (na, nb), "vals": vals,
                "n_legal": n_legal, "action": int(a),
                "max_height": max_h, "viruses": nvir, "occ": occ,
                "garbage_cum": garbage_injected,
                "since_last_garbage": (999 if last_garbage_pill < 0
                                       else int(env.pills_placed - last_garbage_pill)),
            })
        trace.append((int(env.pills_placed), int(a)))

        occ_before = int(np.count_nonzero(env.board.color))
        _, _, term, trunc, info = env.step(int(a))
        clear_size = 0
        landed = 0
        if term:
            res = "clear" if info["won"] else "topout"
            end_kind = "step_clear" if info["won"] else "step_topout"
            if res == "topout":
                v_at_topout = env.board.virus_count()
        if not term and not trunc and env.pills_placed >= PR.GARBAGE_MIN_PILLS:
            occ_after = int(np.count_nonzero(env.board.color))
            clear_size = max(0, occ_before + 2 - occ_after)
            if clear_size > 0:
                rng = None
                if garbage_rng_offset:
                    rng = random.Random(seed * 1000 + env.pills_placed
                                        + garbage_rng_offset)
                landed = inject_bursty_garbage(env.board, bmodel, seed,
                                               env.pills_placed, clear_size,
                                               rng=rng)
            garbage_injected += landed
            if landed:
                last_garbage_pill = int(env.pills_placed)
        if keep:
            recs[-1]["clear_size_this_ply"] = clear_size
            recs[-1]["garbage_this_ply"] = landed
        if term:
            break
        if trunc:
            res, end_kind = "stall", "stall"
            break
        if env.pills_placed >= PR.GARBAGE_MIN_PILLS:
            if env.board.virus_count() == 0:
                res, end_kind = "clear", "garbage_clear"
                break
            if env.board.spawn_blocked():
                res, end_kind = "topout", "garbage_topout"
                v_at_topout = env.board.virus_count()
                break

    if col is None:
        fb = FB.from_board(env.board)
        col, vir = RS.board_flat_from_fb(fb)
    dies_ahead = int(res == "topout" and v_at_topout is not None
                     and v_at_topout <= PR.DIES_AHEAD_VIRUS_THRESHOLD)
    row = {"seed": seed, "res": res, "won": int(res == "clear"),
           "topout": int(res == "topout"), "stall": int(res == "stall"),
           "pills": env.pills_placed, "garbage": garbage_injected,
           "dies_ahead": dies_ahead, "end_kind": end_kind,
           "funnel": funnel, "funnel_mm": funnel_mm, "mm_vert": mm_vert,
           "stranded_final": int(g_stranded(col, vir)),
           "tower_final": int(g_tower(col, vir, PR.H0)),
           "viruses_left_at_end": (v_at_topout if v_at_topout is not None
                                   else env.board.virus_count()),
           "n_decisions": len(trace)}
    return row, recs


def mechanism_of(row):
    ek = row["end_kind"]
    if row["res"] == "clear":
        return "CLEAR"
    if ek == "garbage_topout":
        return "T_GARB"
    if ek == "step_topout":
        return "T_PLACE"
    if ek == "choose_none":
        return "T_NOMOVE"
    return "T_TRUNC"


# --------------------------------------------------------------------- gate
CENSUS_FIELDS = ("res", "pills", "garbage", "dies_ahead")
RIG_FIELDS = ("won", "topout", "pills", "garbage_injected", "funnel",
              "funnel_mm", "mm_vert", "stranded_final", "tower_final",
              "viruses_left_at_end", "dies_ahead")


def _cmp_census(crow, mine):
    errs = []
    for k in CENSUS_FIELDS:
        cv, mv = crow[k], mine[k]
        bad = (cv != mv) if k == "res" else (int(cv) != int(mv))
        if bad:
            errs.append(f"census.{k}: {cv} != {mv}")
    return errs


def _cmp_rig(rig, mine):
    errs = []
    for k in RIG_FIELDS:
        mv = mine["garbage"] if k == "garbage_injected" else mine[k]
        if int(rig[k]) != int(mv):
            errs.append(f"rig.{k}: {rig[k]} != {mv}")
    return errs


def _gate_one(args):
    seed, crow = args
    mine, _ = instrumented_play(seed, keep=False)
    rig = PR.play(seed)
    return seed, crow["res"], _cmp_census(crow, mine) + _cmp_rig(rig, mine)


def _mutant_one(args):
    seed, crow, tag, kw = args
    m, _ = instrumented_play(seed, keep=False, **kw)
    rig = PR.play(seed)
    return tag, seed, _cmp_census(crow, m) + _cmp_rig(rig, m)


def fidelity_gate(census, workers):
    rng = random.Random(GATE_RNG)
    by = {k: sorted(s for s, r in census.items() if r["res"] == k)
          for k in ("topout", "stall", "clear")}
    seeds = (rng.sample(by["topout"], GATE_N_TOPOUT)
             + rng.sample(by["stall"], GATE_N_STALL)
             + rng.sample(by["clear"], GATE_N_CLEAR))
    detail, ok_all = [], True
    mseeds = seeds[:4]
    mut_jobs = []
    for tag, kw in (("ws=0", {"ws": 0}),
                    ("garbage_rng+1", {"garbage_rng_offset": 1}),
                    ("tiebreak_flip", {"tie_flip": True})):
        mut_jobs += [(s, census[s], tag, kw) for s in mseeds]

    with ProcessPoolExecutor(max_workers=workers, initializer=_winit) as ex:
        futs = [ex.submit(_gate_one, (s, census[s])) for s in seeds]
        mfuts = [ex.submit(_mutant_one, j) for j in mut_jobs]
        for f in as_completed(futs):
            s, resk, errs = f.result()
            ok_all &= not errs
            detail.append({"seed": s, "res": resk, "ok": not errs,
                           "errors": errs[:4]})
            print(f"  [gate] seed {s:6d} {resk:6s}: "
                  f"{'OK' if not errs else 'FAIL ' + '; '.join(errs[:3])}",
                  flush=True)
        mres = {}
        for f in as_completed(mfuts):
            tag, s, errs = f.result()
            mres.setdefault(tag, []).append((s, bool(errs)))

    mutants = []
    for tag, hits in sorted(mres.items()):
        killed = sum(1 for _s, e in hits if e)
        mutants.append({"mutant": tag, "killed_on": killed,
                        "n_seeds": len(hits), "killed": killed > 0})
        print(f"  [mutant] {tag}: "
              f"{'KILLED on %d/%d seeds' % (killed, len(hits)) if killed else 'NOT KILLED (gate vacuous!)'}",
              flush=True)
    ok_all &= all(m["killed"] for m in mutants)
    return {"pass": bool(ok_all), "n_seeds": len(seeds),
            "gate_rng": GATE_RNG, "detail": sorted(detail, key=lambda d: d["seed"]),
            "mutants": mutants,
            "compared_fields": {"census": list(CENSUS_FIELDS),
                                "rig": list(RIG_FIELDS)}}


# --------------------------------------------------------------- extraction
def _winit():
    PR._init(LEVEL, WT, WS, model_kind="bursty", bursty_model_obj=load_lulu())


def _worker(args):
    seed, expect = args
    row, recs = instrumented_play(seed, keep=True)
    mism = _cmp_census(expect, row)
    n = row["n_decisions"]
    for r in recs:
        r["t_to_end"] = None
    for j, r in enumerate(recs):
        r["t_to_end"] = (n - 1) - j
    return pack_game(row, recs), row, mism


FKEYS = ("seed", "pill_idx", "t_to_end", "n_legal", "action", "max_height",
         "viruses", "occ", "garbage_cum", "since_last_garbage",
         "clear_size_this_ply", "garbage_this_ply")


def pack_game(row, recs):
    n = len(recs)
    if n == 0:
        return None
    mech = MECHANISM[mechanism_of(row)]
    d = {
        "seed": np.full(n, row["seed"], dtype=np.int32),
        "pill_idx": np.array([r["pill_idx"] for r in recs], dtype=np.int16),
        "t_to_end": np.array([r["t_to_end"] for r in recs], dtype=np.int16),
        "board_col": np.stack([r["col"] for r in recs]),
        "board_vir": np.stack([r["vir"] for r in recs]),
        "cur": np.array([r["cur"] for r in recs], dtype=np.int8),
        "nxt": np.array([r["nxt"] for r in recs], dtype=np.int8),
        "cand_vals": np.stack([r["vals"] for r in recs]).astype(np.float32),
        "n_legal": np.array([r["n_legal"] for r in recs], dtype=np.int8),
        "action": np.array([r["action"] for r in recs], dtype=np.int8),
        "max_height": np.array([r["max_height"] for r in recs], dtype=np.int8),
        "viruses": np.array([r["viruses"] for r in recs], dtype=np.int16),
        "occ": np.array([r["occ"] for r in recs], dtype=np.int16),
        "garbage_cum": np.array([r["garbage_cum"] for r in recs], dtype=np.int16),
        "since_last_garbage": np.array([r["since_last_garbage"] for r in recs],
                                       dtype=np.int16),
        "clear_size_this_ply": np.array([r["clear_size_this_ply"] for r in recs],
                                        dtype=np.int16),
        "garbage_this_ply": np.array([r["garbage_this_ply"] for r in recs],
                                     dtype=np.int16),
        "outcome": np.full(n, OUTCOME_CODE[row["res"]], dtype=np.int8),
        "dies_ahead": np.full(n, row["dies_ahead"], dtype=np.int8),
        "end_kind": np.full(n, END_KIND[row["end_kind"]], dtype=np.int8),
        "mechanism": np.full(n, mech, dtype=np.int8),
        "viruses_left_at_end": np.full(n, row["viruses_left_at_end"], dtype=np.int16),
        "game_pills": np.full(n, row["pills"], dtype=np.int16),
    }
    return d


def merge(shards):
    keys = shards[0].keys()
    return {k: np.concatenate([s[k] for s in shards]) for k in keys}


def game_labels(out):
    """PRE-REGISTERED primary label (PREREG sec 3.1), computed at GAME level.

      y = 1  <=>  dies_ahead == 1 AND end_kind == garbage_topout  (DA x T_GARB)
      y = 0  <=>  the game CLEARED
      y = -1 <=>  excluded from the primary contrast (T_PLACE topouts,
                  not-ahead topouts, stalls) -- recon C's do-not-pool cells.
    """
    gmap = {}
    for d in out.values():
        uniq, first = np.unique(d["seed"], return_index=True)
        g_out = d["outcome"][first]
        g_da = d["dies_ahead"][first]
        g_ek = d["end_kind"][first]
        gy = np.full(uniq.shape[0], -1, dtype=np.int8)
        gy[(g_da == 1) & (g_ek == END_KIND["garbage_topout"])] = 1
        gy[g_out == OUTCOME_CODE["clear"]] = 0
        for s, v in zip(uniq.tolist(), gy.tolist()):
            gmap[int(s)] = int(v)
    return gmap


def shuffle_game_labels(gmap, rng_seed=SAMPLE_RNG):
    """SHUFFLED-LABEL CONTROL (PREREG sec 3.3), built INTO the pipeline.

    The permutation is over GAMES, globally across the whole contrast, so the
    positive-game count AND the decision-cluster structure survive and only the
    association between board and outcome is destroyed. Stage 1's shuffle was
    decision-level and therefore anti-conservative.
    """
    keys = np.array(sorted(k for k, v in gmap.items() if v >= 0), dtype=np.int64)
    vals = np.array([gmap[int(k)] for k in keys], dtype=np.int8)
    perm = np.random.default_rng(rng_seed).permutation(keys.shape[0])
    return {int(k): int(v) for k, v in zip(keys, vals[perm])}


def _bcast(gmap, seeds, default=-1):
    keys = np.array(sorted(gmap.keys()), dtype=np.int64)
    vals = np.array([gmap[int(k)] for k in keys], dtype=np.int8)
    idx = np.searchsorted(keys, seeds)
    idx = np.clip(idx, 0, max(0, keys.shape[0] - 1))
    hit = keys.shape[0] > 0
    out = np.full(seeds.shape[0], default, dtype=np.int8)
    if hit:
        ok = keys[idx] == seeds
        out[ok] = vals[idx[ok]]
    return out


def apply_labels_and_split(d, gmap, gmap_shuf, rng_seed=SAMPLE_RNG):
    seed = d["seed"].astype(np.int64)
    d["y"] = _bcast(gmap, seed)
    d["y_shuf"] = _bcast(gmap_shuf, seed)
    # leak positive control: MUST read AUC > 0.95 vs y and ~0.5 vs y_shuf.
    # If it does not separate on y, the pipeline is broken and the corpus is void.
    lr = np.random.default_rng(rng_seed + 1)
    d["f_leak"] = (d["y"].astype(np.float32)
                   + lr.normal(0, 0.1, size=seed.shape[0]).astype(np.float32))
    # split BY GAME (never by decision), deterministic and feature-independent
    d["hold"] = np.isin(d["seed"] % HOLD_MOD, np.array(HOLD_SET)).astype(np.int8)
    return d


def load_census(path):
    out = {}
    with open(path) as f:
        for ln in f:
            ln = ln.strip()
            if not ln:
                continue
            r = json.loads(ln)
            if r["seed"] == 1:
                continue
            out[r["seed"]] = r
    return out


def code_hash():
    h = hashlib.sha256()
    for p in (os.path.abspath(__file__),
              os.path.join(EV, "pressure_rig.py"),
              os.path.join(EV, "bursty_model.py"),
              os.path.join(JD, "p0_ab.py"),
              os.path.join(EV, "results", "dr_lulu_20260808_fit.json")):
        with open(p, "rb") as f:
            h.update(hashlib.sha256(f.read()).digest())
    return h.hexdigest()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--gate-only", action="store_true")
    ap.add_argument("--run", action="store_true")
    ap.add_argument("--workers", type=int, default=6)
    ap.add_argument("--ctrl-sample", type=int, default=CTRL_SAMPLE_LOCAL,
                    help="cleared games to extract; 0 = ALL (the Hetzner job)")
    ap.add_argument("--census", default=CENSUS)
    ap.add_argument("--tag", default="local")
    ap.add_argument("--stall-sample", type=int, default=0,
                    help="stall games to extract; 0 = ALL")
    ap.add_argument("--limit", type=int, default=0,
                    help="smoke test: cap games per class (0 = no cap)")
    ap.add_argument("--skip-gate", action="store_true",
                    help="smoke test ONLY; a real corpus always runs the gate")
    a = ap.parse_args()
    workers = min(a.workers, 6) if a.tag == "local" else a.workers
    os.makedirs(RESULTS, exist_ok=True)

    census = load_census(a.census)
    from collections import Counter
    comp = Counter(r["res"] for r in census.values())
    n_da = sum(r["dies_ahead"] for r in census.values())
    clear_rate = comp["clear"] / len(census)
    print(f"[census] {len(census)} games {dict(comp)} dies_ahead={n_da} "
          f"CLEAR RATE {clear_rate:.4%}  "
          f"({'BELOW' if clear_rate < 0.969 else 'above'} the 96.9% "
          f"label-quality screen -- see PREREG_STAGE2.md sec 7)", flush=True)

    _winit()
    if a.skip_gate:
        print("[gate] SKIPPED (--skip-gate: smoke test only, NOT a corpus)", flush=True)
        gate = {"pass": False, "SKIPPED": True}
    else:
        print("[gate] fidelity gate: replayer vs census row AND vs the real rig "
              "(trace-derived fields) ...", flush=True)
        t0 = time.monotonic()
        gate = fidelity_gate(census, workers)
        gate["seconds"] = round(time.monotonic() - t0, 1)
        with open(os.path.join(RESULTS, f"gate_{a.tag}.json"), "w") as f:
            json.dump(gate, f, indent=1)
        print(f"[gate] {'PASS' if gate['pass'] else 'FAIL'} in {gate['seconds']}s",
              flush=True)
        if not gate["pass"]:
            sys.exit("[gate] FAILED -- refusing to extract from an unverified replayer")
    if a.gate_only:
        return

    tops = sorted(s for s, r in census.items() if r["res"] == "topout")
    stalls = sorted(s for s, r in census.items() if r["res"] == "stall")
    clears = sorted(s for s, r in census.items() if r["res"] == "clear")
    rng = random.Random(SAMPLE_RNG)
    ctrl_pick = sorted(clears) if a.ctrl_sample == 0 else \
        sorted(rng.sample(clears, min(a.ctrl_sample, len(clears))))
    if a.stall_sample:
        stalls = sorted(rng.sample(stalls, min(a.stall_sample, len(stalls))))

    if a.limit:
        tops, stalls, ctrl_pick = (tops[:a.limit], stalls[:a.limit],
                                   ctrl_pick[:a.limit])
    jobs = ([(s, census[s]) for s in tops]
            + [(s, census[s]) for s in stalls]
            + [(s, census[s]) for s in ctrl_pick])
    print(f"[extract] {len(tops)} topout + {len(stalls)} stall + "
          f"{len(ctrl_pick)} clear = {len(jobs)} games, ALL decisions, "
          f"{workers} workers", flush=True)

    # ---- SHARDED + RESUMABLE. Scar tissue: a first attempt held all 4,124
    # games in the parent and was killed at 3,200 with nothing on disk. Shards
    # flush every SHARD_EVERY games and completed seeds are skipped on restart,
    # so a kill costs at most one chunk.
    SHARD_EVERY = 300
    shard_dir = os.path.join(RESULTS, f"shards_{a.tag}")
    os.makedirs(shard_dir, exist_ok=True)
    done_seeds, rows = set(), {}
    for fn in sorted(os.listdir(shard_dir)):
        if fn.startswith("rows_") and fn.endswith(".json"):
            for s, r in json.load(open(os.path.join(shard_dir, fn))).items():
                rows[int(s)] = r
                done_seeds.add(int(s))
    if done_seeds:
        jobs = [j for j in jobs if j[0] not in done_seeds]
        print(f"[extract] RESUME: {len(done_seeds)} games already sharded, "
              f"{len(jobs)} to go", flush=True)

    buf = {"fail": [], "stall": [], "ctrl": []}
    buf_rows = {}
    mism = []
    shard_id = len([f for f in os.listdir(shard_dir) if f.startswith("rows_")])
    t0, done = time.monotonic(), 0

    def flush():
        nonlocal shard_id
        if not buf_rows:
            return
        for nm, sh in buf.items():
            if sh:
                np.savez(os.path.join(shard_dir, f"{nm}_{shard_id:04d}.npz"),
                         **merge(sh))
                sh.clear()
        with open(os.path.join(shard_dir, f"rows_{shard_id:04d}.json"), "w") as fh:
            json.dump(buf_rows, fh)
        buf_rows.clear()
        shard_id += 1

    with ProcessPoolExecutor(max_workers=workers, initializer=_winit) as ex:
        futs = [ex.submit(_worker, j) for j in jobs]
        for f in as_completed(futs):
            d, row, errs = f.result()
            rows[row["seed"]] = row
            buf_rows[row["seed"]] = row
            if errs:
                mism.append({"seed": row["seed"], "errors": errs})
            if d is not None:
                buf["ctrl" if row["res"] == "clear"
                    else "stall" if row["res"] == "stall" else "fail"].append(d)
            done += 1
            if done % SHARD_EVERY == 0:
                flush()
            if done % 200 == 0 or done == len(jobs):
                dt = time.monotonic() - t0
                print(f"[extract] {done}/{len(jobs)} {dt:.0f}s {done/dt:.2f} g/s "
                      f"mismatches={len(mism)} shards={shard_id}", flush=True)
    flush()

    fail_sh, stall_sh, ctrl_sh = [], [], []
    for fn in sorted(os.listdir(shard_dir)):
        if not fn.endswith(".npz"):
            continue
        z = np.load(os.path.join(shard_dir, fn))
        dd = {k: z[k] for k in z.files}
        (fail_sh if fn.startswith("fail") else
         stall_sh if fn.startswith("stall") else ctrl_sh).append(dd)
    print(f"[extract] merged {len(fail_sh)}+{len(stall_sh)}+{len(ctrl_sh)} "
          f"shards from {shard_dir}", flush=True)

    if mism:
        with open(os.path.join(RESULTS, f"MISMATCHES_{a.tag}.json"), "w") as f:
            json.dump(mism, f, indent=1)
        sys.exit(f"[extract] {len(mism)} games did NOT reproduce their census "
                 f"row -- corpus REFUSED (see MISMATCHES_{a.tag}.json)")

    pos_seeds = {s for s, r in rows.items()
                 if r["dies_ahead"] == 1 and r["end_kind"] == "garbage_topout"}
    out = {}
    for name, sh in (("fail", fail_sh), ("stall", stall_sh), ("ctrl", ctrl_sh)):
        if not sh:
            continue
        d = merge(sh)
        order = np.lexsort((d["pill_idx"], d["seed"]))
        d = {k: v[order] for k, v in d.items()}
        out[name] = d

    # labels + the shuffled control are computed ONCE over the whole contrast
    # (fail + ctrl), then broadcast; stalls carry the same columns so slices are
    # uniform, but their y is -1 by construction (never pooled -- PREREG sec 1).
    gmap = game_labels(out)
    gmap_shuf = shuffle_game_labels(gmap)
    for name, d in out.items():
        apply_labels_and_split(d, gmap, gmap_shuf)
        p = os.path.join(RESULTS, f"s2lulu_{name}_{a.tag}.npz")
        np.savez_compressed(p, **d)
        print(f"[write] {p}  {d['seed'].shape[0]} decisions  "
              f"y1={int((d['y']==1).sum())} y0={int((d['y']==0).sum())} "
              f"{os.path.getsize(p)/1e6:.1f} MB", flush=True)

    # --- measured split guards (PREREG sec 4): reported, not assumed
    all_seeds = np.unique(np.concatenate([d["seed"] for d in out.values()]))
    tr_s = {s for s in all_seeds.tolist() if s % HOLD_MOD not in HOLD_SET}
    ho_s = {s for s in all_seeds.tolist() if s % HOLD_MOD in HOLD_SET}
    lbl = {s: gmap.get(int(s), -1) for s in all_seeds.tolist()}
    twins = [(2 * t, 2 * t + 1) for t in range(1, 12002 // 2 + 1)
             if (2 * t) in lbl and (2 * t + 1) in lbl]
    straddle = [(x, y_) for x, y_ in twins
                if ((x in tr_s) != (y_ in tr_s))]
    same_class = [(x, y_) for x, y_ in straddle
                  if lbl[x] == lbl[y_] and lbl[x] >= 0]
    split_guards = {"seed_overlap_train_holdout": len(tr_s & ho_s),
                    "n_train_games": len(tr_s), "n_holdout_games": len(ho_s),
                    "twin_pairs_present": len(twins),
                    "twin_pairs_straddling_split": len(straddle),
                    "twin_pairs_straddling_AND_same_class": len(same_class)}
    assert split_guards["seed_overlap_train_holdout"] == 0, "SEED LEAK"
    print(f"[split] {split_guards}", flush=True)

    with open(a.census, "rb") as f:
        csha = hashlib.sha256(f.read()).hexdigest()
    hs = int(sum(d["hold"].sum() for d in out.values()))
    tot = int(sum(d["seed"].shape[0] for d in out.values()))
    meta = {
        "built": time.strftime("%Y-%m-%d %H:%M:%S"), "tag": a.tag,
        "prereg": "PREREG_STAGE2.md @ b9725fc",
        "census_file": a.census, "census_sha256": csha,
        "census_composition": dict(comp), "census_clear_rate": clear_rate,
        "census_dies_ahead": n_da,
        "label_quality": {
            "screen": 0.969, "measured_clear_rate": clear_rate,
            "passes_screen": bool(clear_rate > 0.969),
            "caveat": "Corpus s2lulu: generating policy = shipped champion "
                      "(bit-exact), environment = dr. lulu fitted bursty "
                      "pressure, clear rate %.2f%% -- BELOW the 96.9%% "
                      "label-quality screen. Labels are game outcomes "
                      "broadcast onto decisions; no counterfactual "
                      "attribution." % (clear_rate * 100)},
        "code_sha256": code_hash(),
        "level": LEVEL, "wt": WT, "ws": WS, "sample_rng": SAMPLE_RNG,
        "split": "hold = seed %% %d in %s (BY GAME)" % (HOLD_MOD, list(HOLD_SET)),
        "counts": {"games": {"topout": len(tops), "stall": len(stalls),
                             "clear": len(ctrl_pick)},
                   "decisions": {k: int(v["seed"].shape[0]) for k, v in out.items()},
                   "decisions_total": tot, "decisions_holdout": hs},
        "target_class_games": len(pos_seeds),
        "split_guards": split_guards,
        "gate": gate,
        "bulk_census_row_mismatches": mism,
        "outcome_code": OUTCOME_CODE, "end_kind_code": END_KIND,
        "mechanism_code": MECHANISM,
        "cand_vals_index": "vals[var*8+cc]; NaN = illegal drop",
        "ctrl_seeds": ctrl_pick,
    }
    with open(os.path.join(RESULTS, f"s2lulu_meta_{a.tag}.json"), "w") as f:
        json.dump(meta, f, indent=1)
    print(f"[done] {tot} decisions total ({hs} holdout), "
          f"{len(pos_seeds)} target-class games", flush=True)


if __name__ == "__main__":
    main()
