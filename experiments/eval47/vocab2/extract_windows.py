#!/usr/bin/env python3
"""vocab2 Phase 1 -- reconstruct decision windows from the pressured census.

MISSION (survival-term hunt): the champion is risk-neutral near the absorbing
state; the original vocabulary wall (73 failures) showed the fatal move scores
BETTER on all 11 features. This scales that analysis to the 40k-seed pressured
census (890 topouts / 927 stalls / 861 dies-ahead over seeds < 40000).

WHAT THIS BUILDS
  fatal_windows.npz   last K=10 decisions of ALL 890 topouts + a 200-game
                      sample of stalls; per decision: board (col/vir 128),
                      cur/next, all-32 candidate values (NaN = illegal),
                      chosen action, covariates, outcome labels.
  controls.npz        ALL decisions of a 1,000-game sample of CLEARED census
                      games (same drip pressure) with the same per-decision
                      schema -- the matched-control pool. Matching covariates
                      (max_height, viruses, garbage_cum) are stored raw so
                      phase 2 can re-bin; a default stratum key is included.
  dataset_meta.json   provenance (census sha256, manifest rolled hash, gate
                      results, sampling seeds, pre-registered binning).

FIDELITY GATE (must pass before any bulk extraction; this file refuses to
write the dataset otherwise): the instrumented replayer is a copy of
adversary_harness.play_seed(pressure="drip") -- the exact loop that produced
the census rows (manifest hashes verified MATCH against local code). On
GATE_N seeds spanning topouts, stalls, and clears it must reproduce the
census row EXACTLY: result, pills, viruses_left; for non-clear rows also the
FULL move trace and the terminal board snapshot (thousands of decisions
bit-for-bit -- this is the strongest available equality over the chooser).

KILLED-MUTANT GATE (house law: a check must be shown to FAIL on wrong
inputs): (a) ws=0 mutant chooser and (b) garbage-rng-offset mutant must BREAK
trace equality on gate topout seeds. A gate that passes mutants is vacuous.

PRE-REGISTERED (before extraction ran):
  K_LAST=10; stalls sample n=200, controls sample n=1000, sample rng seed
  20260809; seed 1 excluded (degenerate); seeds < 40000 only (p3 in flight);
  default stratum key = (max_height, min(viruses,30)//3, min(garbage_cum,48)//8)
  where max_height/viruses/garbage_cum are measured AT THE DECISION (board
  before placement); garbage_cum = cumulative injected halves so far (exactly
  replayable, unlike per-cell garbage identity). Raw covariates are stored so
  phase 2 may re-bin; the key above is only the default join.

Usage:
  extract_windows.py --gate-only        # run gates, write gate_result.json
  extract_windows.py --run              # gates + full extraction (<=8 workers)
"""
from __future__ import annotations

import sys
import os
import json
import time
import random
import hashlib
import argparse
from concurrent.futures import ProcessPoolExecutor, as_completed

HERE = os.path.dirname(os.path.abspath(__file__))
QA = "/home/struktured/projects/dr-mario-qa-wt/experiments"
for _p in (QA + "/adversary", QA + "/eval47", QA):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import numpy as np  # noqa: E402
import adversary_harness as AH  # noqa: E402

CENSUS = os.path.join(QA, "hetzner", "results", "pressured_drip", "census.jsonl")
MANIFEST = os.path.join(QA, "hetzner", "results", "pressured_drip", "manifest.json")

K_LAST = 10
SEED_MAX = 40000          # p3 (40000..60000) still running on Hetzner
STALL_SAMPLE = 200
CONTROL_SAMPLE = 1000
SAMPLE_RNG = 20260809
GATE_N_TOPOUT, GATE_N_STALL, GATE_N_CLEAR = 12, 6, 6
WS = AH.WS if hasattr(AH, "WS") else 20   # 20, the shipped strand20 dose

OUTCOME_CODE = {"clear": 0, "topout": 1, "stall": 2}
END_KIND = {"clear": 0, "choose_none": 1, "step_topout": 2, "garbage_topout": 3,
            "garbage_clear": 4, "stall": 5}


# ------------------------------------------------------------------ chooser
def decide_all32(col, vir, ca, cb, na, nb, ws=WS):
    """Replicated choose_base32 loop (same o4-then-cc order, same strict->
    tie-break) that ALSO dumps all 32 candidate values. vals[var*8+cc] = value,
    NaN where the drop is illegal. The fidelity gate (full-trace equality vs
    census rows produced by reach_root.choose_base32) is what licenses this
    copy."""
    import reach_root as RR
    L = RR._lazy()
    FX, FS, RS, g_stranded = L["FX"], L["FS"], L["RS"], L["g_stranded"]
    w, fl = L["w"], L["fl"]

    c1 = np.empty(FS.NCELL, dtype=np.int8)
    v1 = np.empty(FS.NCELL, dtype=np.int8)
    vals = np.full(32, np.nan, dtype=np.float32)
    best_val, best_a = None, None
    n_legal = 0
    for o4 in range(4):
        var = int(FX._VAR_OF_O4[o4])
        for cc in range(8):
            ok, nv, cells = FS._expand_core(col, vir, var, cc, ca, cb, c1, v1)
            if ok == 0:
                continue
            n_legal += 1
            val = RS._root_value(c1, v1, nv, cells, na, nb, RR.TOPK2,
                                 FX._W_EXCAV_SHIP, FX._W_HANG_SHIP, w, fl)
            val -= ws * g_stranded(c1, v1)
            vals[var * 8 + cc] = val
            if best_val is None or val > best_val:
                best_val, best_a = val, var * 8 + cc
    return best_a, vals, n_legal


def covariates(col, vir):
    """(max_height, viruses, occ) from the 128-cell flat boards (row-major,
    row 0 = top)."""
    b = np.asarray(col).reshape(16, 8)
    occ_rows = np.nonzero(b.any(axis=1))[0]
    max_h = 0 if occ_rows.size == 0 else 16 - int(occ_rows[0])
    return max_h, int(np.count_nonzero(np.asarray(vir))), int(np.count_nonzero(b))


# ------------------------------------------------------------------ replayer
def instrumented_play(seed, keep="last", ws=WS, garbage_rng_offset=0,
                      max_pills=300):
    """Copy of adversary_harness.play_seed(pressure='drip') + per-decision
    instrumentation. Must stay result/trace/board-identical to it -- the
    fidelity gate enforces this (and the mutant args exist to prove the gate
    can fail: ws!=20 or garbage_rng_offset!=0 are MUTANTS, never data).

    keep: 'last' -> keep the final K_LAST decision records; 'all' -> keep all.
    Returns (row, records); row mirrors play_seed's return (plus end_kind),
    records is a list of per-decision dicts.
    """
    L = AH._lazy()
    FaithfulDrMarioEnv, NesPillSource, FB, RS = (
        L["FaithfulDrMarioEnv"], L["NesPillSource"], L["FB"], L["RS"])

    def inject(board, s, pills):
        # mutant hook: offset shifts the drip rng stream (gate must catch it)
        if garbage_rng_offset == 0:
            return AH._inject_drip(board, s, pills)
        from drmario.faithful_game import EMPTY, LINK_NONE
        rng = random.Random(s * 1000 + pills + garbage_rng_offset)
        cols = rng.sample(range(board.cols), min(AH.GARBAGE_K, board.cols))
        placed = 0
        for c in cols:
            color = rng.randint(1, 3)
            if board.color[0, c] != EMPTY:
                continue
            r = 0
            while r < board.rows and board.color[r, c] != EMPTY:
                r += 1
            board.color[r, c] = color
            board.is_virus[r, c] = False
            board.link[r, c] = LINK_NONE
            placed += 1
        if placed:
            board._apply_gravity()
            board.resolve()
        return placed

    env = FaithfulDrMarioEnv(level=AH.LEVEL, seed=seed, max_pills=max_pills)
    env.reset()
    NesPillSource(seed=seed).attach(env)
    env.cur = env._rand_pill()
    env.nxt = env._rand_pill()

    res = "stall"
    end_kind = "stall"
    trace = []
    records = []
    first_topout_board = None
    garbage_injected = 0

    for i in range(max_pills):
        if env.board.virus_count() == 0:
            res, end_kind = "clear", "clear"
            break
        fb = FB.from_board(env.board)
        col, vir = RS.board_flat_from_fb(fb)
        ca, cb = int(env.cur.a), int(env.cur.b)
        na, nb = int(env.nxt.a), int(env.nxt.b)
        a, vals, n_legal = decide_all32(col, vir, ca, cb, na, nb, ws=ws)
        if a is None:
            res, end_kind = "topout", "choose_none"
            first_topout_board = AH._snapshot(env.board)
            break
        max_h, nvir, occ = covariates(col, vir)
        records.append({"seed": seed, "pill_idx": i,
                        "col": np.asarray(col, dtype=np.int8).copy(),
                        "vir": np.asarray(vir, dtype=np.int8).copy(),
                        "cur": (ca, cb), "nxt": (na, nb),
                        "vals": vals, "n_legal": n_legal, "action": int(a),
                        "max_height": max_h, "viruses": nvir, "occ": occ,
                        "garbage_cum": garbage_injected})
        if keep == "last" and len(records) > K_LAST:
            records.pop(0)
        trace.append((i, int(a)))
        _, _, term, trunc, info = env.step(int(a))
        if term:
            end_kind = "clear" if info["won"] else "step_topout"

        if not term and env.pills_placed >= AH.GARBAGE_MIN_PILLS \
                and env.pills_placed % AH.GARBAGE_PERIOD == 0:
            garbage_injected += inject(env.board, seed, env.pills_placed)
            if env.board.virus_count() == 0:
                term, info = True, {"won": True}
                end_kind = "garbage_clear"
            elif env.board.spawn_blocked():
                term, info = True, {"won": False}
                end_kind = "garbage_topout"

        if term:
            res = "clear" if info["won"] else "topout"
            if res == "topout":
                first_topout_board = AH._snapshot(env.board)
            break
        if trunc:
            res, end_kind = "stall", "stall"
            break

    if res == "stall" and first_topout_board is None:
        first_topout_board = AH._snapshot(env.board)

    viruses_left = int(env.board.virus_count())
    row = {"seed": seed, "result": res, "pills": env.pills_placed,
           "viruses_left": viruses_left,
           "dies_ahead": bool(res == "topout"
                              and viruses_left <= AH.DIES_AHEAD_VIRUS_THRESHOLD),
           "garbage_injected": garbage_injected, "end_kind": end_kind,
           "first_topout_board": first_topout_board, "trace": trace}
    return row, records


# ---------------------------------------------------------------------- gate
def _row_matches(census_row, mine, check_trace):
    errs = []
    for k in ("result", "pills", "viruses_left"):
        if census_row[k] != mine[k]:
            errs.append(f"{k}: census={census_row[k]} mine={mine[k]}")
    if bool(census_row["dies_ahead"]) != bool(mine["dies_ahead"]):
        errs.append("dies_ahead mismatch")
    if check_trace:
        ct = [tuple(x) for x in census_row.get("trace", [])]
        if ct != [tuple(x) for x in mine["trace"]]:
            n = sum(1 for a, b in zip(ct, mine["trace"]) if tuple(a) != tuple(b))
            errs.append(f"TRACE mismatch (len {len(ct)} vs {len(mine['trace'])}, "
                        f"{n} differing overlapped entries)")
        cb = census_row.get("board")
        mb = mine["first_topout_board"]
        if cb is not None:
            if mb is None or cb["col"] != mb["col"] or cb["vir"] != mb["vir"] \
                    or cb["lnk"] != mb["lnk"]:
                errs.append("terminal BOARD mismatch")
    return errs


def fidelity_gate(census, verbose=True):
    rng = random.Random(1234)
    tops = sorted(s for s, r in census.items() if r["result"] == "topout")
    stalls = sorted(s for s, r in census.items() if r["result"] == "stall")
    clears = sorted(s for s, r in census.items() if r["result"] == "clear")
    seeds = (rng.sample(tops, GATE_N_TOPOUT) + rng.sample(stalls, GATE_N_STALL)
             + rng.sample(clears, GATE_N_CLEAR))
    detail = []
    ok_all = True
    for s in seeds:
        row = census[s]
        mine, _ = instrumented_play(s, keep="last")
        errs = _row_matches(row, mine, check_trace=(row["result"] != "clear"))
        ok_all &= not errs
        detail.append({"seed": s, "result": row["result"], "ok": not errs,
                       "errors": errs})
        if verbose:
            tr = f" trace={len(row.get('trace', []))} moves+board" \
                if row["result"] != "clear" else ""
            print(f"  [gate] seed {s:5d} {row['result']:6s}{tr}: "
                  f"{'OK' if not errs else 'FAIL ' + '; '.join(errs)}", flush=True)

    # KILLED MUTANTS -- the equality check must fail on wrong inputs
    mutants = []
    mseeds = seeds[:3]   # 3 topout seeds (list starts with topouts)
    for tag, kw in (("ws=0", {"ws": 0}), ("garbage_rng+1", {"garbage_rng_offset": 1})):
        killed_any = False
        for s in mseeds:
            m, _ = instrumented_play(s, keep="last", **kw)
            errs = _row_matches(census[s], m, check_trace=True)
            if errs:
                killed_any = True
                break
        mutants.append({"mutant": tag, "killed": killed_any,
                        "seed": s, "first_divergence": errs[:2] if killed_any else []})
        if verbose:
            print(f"  [mutant] {tag}: {'KILLED' if killed_any else 'NOT KILLED (gate vacuous!)'}",
                  flush=True)
    ok_all &= all(m["killed"] for m in mutants)
    return {"pass": ok_all, "n_seeds": len(seeds),
            "n_topout": GATE_N_TOPOUT, "n_stall": GATE_N_STALL,
            "n_clear": GATE_N_CLEAR, "detail": detail, "mutants": mutants}


# ----------------------------------------------------------------- extraction
def _worker(args):
    seed, keep, expect = args
    row, recs = instrumented_play(seed, keep=keep)
    # per-game in-flight fidelity check against the census row (cheap fields)
    mismatch = (row["result"] != expect["result"] or row["pills"] != expect["pills"]
                or row["viruses_left"] != expect["viruses_left"])
    n_dec = len(row["trace"])
    for j, r in enumerate(recs):
        # decisions-to-end: 0 = the game's final chosen decision
        r["t_to_end"] = (n_dec - 1) - r["pill_idx"]
    return row, recs, mismatch


def pack(records, rows_by_seed):
    n = len(records)
    out = {
        "seed": np.array([r["seed"] for r in records], dtype=np.int32),
        "pill_idx": np.array([r["pill_idx"] for r in records], dtype=np.int16),
        "t_to_end": np.array([r["t_to_end"] for r in records], dtype=np.int16),
        "board_col": np.stack([r["col"] for r in records]).astype(np.int8),
        "board_vir": np.stack([r["vir"] for r in records]).astype(np.int8),
        "cur": np.array([r["cur"] for r in records], dtype=np.int8),
        "nxt": np.array([r["nxt"] for r in records], dtype=np.int8),
        "cand_vals": np.stack([r["vals"] for r in records]).astype(np.float32),
        "n_legal": np.array([r["n_legal"] for r in records], dtype=np.int8),
        "action": np.array([r["action"] for r in records], dtype=np.int8),
        "max_height": np.array([r["max_height"] for r in records], dtype=np.int8),
        "viruses": np.array([r["viruses"] for r in records], dtype=np.int16),
        "occ": np.array([r["occ"] for r in records], dtype=np.int16),
        "garbage_cum": np.array([r["garbage_cum"] for r in records], dtype=np.int16),
    }
    oc, da, ek = [], [], []
    for r in records:
        g = rows_by_seed[r["seed"]]
        oc.append(OUTCOME_CODE[g["result"]])
        da.append(int(g["dies_ahead"]))
        ek.append(END_KIND[g["end_kind"]])
    out["outcome"] = np.array(oc, dtype=np.int8)
    out["dies_ahead"] = np.array(da, dtype=np.int8)
    out["end_kind"] = np.array(ek, dtype=np.int8)
    # pre-registered default stratum key (raw covariates stored for re-binning)
    out["stratum_h"] = out["max_height"].copy()
    out["stratum_v"] = (np.minimum(out["viruses"], 30) // 3).astype(np.int8)
    out["stratum_g"] = (np.minimum(out["garbage_cum"], 48) // 8).astype(np.int8)
    assert all(v.shape[0] == n for v in out.values())
    return out


def load_census():
    census = {}
    with open(CENSUS) as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                r = json.loads(line)
            except json.JSONDecodeError:
                continue
            if r["seed"] < SEED_MAX and r["seed"] != 1:
                census[r["seed"]] = r
    return census


def run_extraction(census, workers=8):
    rng = random.Random(SAMPLE_RNG)
    tops = sorted(s for s, r in census.items() if r["result"] == "topout")
    stalls = sorted(s for s, r in census.items() if r["result"] == "stall")
    clears = sorted(s for s, r in census.items() if r["result"] == "clear")
    stall_pick = sorted(rng.sample(stalls, STALL_SAMPLE))
    control_pick = sorted(rng.sample(clears, CONTROL_SAMPLE))

    jobs = ([(s, "last", census[s]) for s in tops]
            + [(s, "last", census[s]) for s in stall_pick]
            + [(s, "all", census[s]) for s in control_pick])
    print(f"[extract] {len(tops)} topouts + {len(stall_pick)} stalls (last {K_LAST}) "
          f"+ {len(control_pick)} cleared controls (all decisions), "
          f"{workers} workers", flush=True)

    fatal_recs, control_recs, rows_by_seed = [], [], {}
    mismatches = []
    t0 = time.monotonic()
    done = 0
    with ProcessPoolExecutor(max_workers=workers, initializer=AH._lazy) as ex:
        futs = {ex.submit(_worker, j): j[0] for j in jobs}
        for fut in as_completed(futs):
            row, recs, mism = fut.result()
            rows_by_seed[row["seed"]] = row
            if mism:
                mismatches.append(row["seed"])
            if row["result"] == "clear":
                control_recs.extend(recs)
            else:
                fatal_recs.extend(recs)
            done += 1
            if done % 200 == 0 or done == len(jobs):
                dt = time.monotonic() - t0
                print(f"[extract] {done}/{len(jobs)} games  {dt:.0f}s  "
                      f"{done / dt:.2f} g/s  fatal_recs={len(fatal_recs)} "
                      f"ctrl_recs={len(control_recs)}  mismatches={len(mismatches)}",
                      flush=True)

    if mismatches:
        print(f"[extract] WARNING {len(mismatches)} games did NOT match their "
              f"census row: {sorted(mismatches)[:20]}", flush=True)
    return fatal_recs, control_recs, rows_by_seed, mismatches, \
        {"topouts": tops, "stalls": stall_pick, "controls": control_pick}


def match_coverage(fatal, ctrl):
    """Per-stratum control availability for the fatal decisions (default key)."""
    keyf = list(zip(fatal["stratum_h"].tolist(), fatal["stratum_v"].tolist(),
                    fatal["stratum_g"].tolist()))
    keyc = {}
    for h, v, g in zip(ctrl["stratum_h"].tolist(), ctrl["stratum_v"].tolist(),
                       ctrl["stratum_g"].tolist()):
        keyc[(h, v, g)] = keyc.get((h, v, g), 0) + 1
    n5 = sum(1 for k in keyf if keyc.get(k, 0) >= 5)
    n1 = sum(1 for k in keyf if keyc.get(k, 0) >= 1)
    return {"n_fatal_decisions": len(keyf),
            "fatal_with_ge1_control": n1, "fatal_with_ge5_controls": n5,
            "frac_ge1": n1 / len(keyf), "frac_ge5": n5 / len(keyf)}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--gate-only", action="store_true")
    ap.add_argument("--run", action="store_true")
    ap.add_argument("--workers", type=int, default=8)
    a = ap.parse_args()

    census = load_census()
    from collections import Counter
    c = Counter(r["result"] for r in census.values())
    print(f"[census] {len(census)} rows (seeds<{SEED_MAX}, seed 1 excluded): {dict(c)}",
          flush=True)

    AH._lazy()
    print("[gate] fidelity gate (replayer vs census rows) ...", flush=True)
    gate = fidelity_gate(census)
    with open(os.path.join(HERE, "gate_result.json"), "w") as f:
        json.dump(gate, f, indent=1)
    print(f"[gate] {'PASS' if gate['pass'] else 'FAIL'} "
          f"({gate['n_seeds']} seeds: {GATE_N_TOPOUT} topout / {GATE_N_STALL} stall / "
          f"{GATE_N_CLEAR} clear; mutants "
          f"{[m['mutant'] + ':' + ('killed' if m['killed'] else 'ALIVE') for m in gate['mutants']]})",
          flush=True)
    if not gate["pass"]:
        sys.exit("[gate] FAILED -- refusing to extract from an unverified replayer")
    if a.gate_only:
        return

    fatal_recs, control_recs, rows_by_seed, mismatches, picks = \
        run_extraction(census, workers=min(a.workers, 8))
    assert not mismatches, f"census-row mismatches during bulk run: {mismatches[:20]}"

    fatal = pack(fatal_recs, rows_by_seed)
    ctrl = pack(control_recs, rows_by_seed)
    np.savez_compressed(os.path.join(HERE, "fatal_windows.npz"), **fatal)
    np.savez_compressed(os.path.join(HERE, "controls.npz"), **ctrl)

    cov = match_coverage(fatal, ctrl)
    with open(CENSUS, "rb") as f:
        census_sha = hashlib.sha256(f.read()).hexdigest()
    manifest = json.load(open(MANIFEST))
    game_meta = {str(s): {k: rows_by_seed[s][k] for k in
                          ("result", "pills", "viruses_left", "dies_ahead",
                           "garbage_injected", "end_kind")}
                 for s in rows_by_seed}
    meta = {
        "built": time.strftime("%Y-%m-%d %H:%M:%S"),
        "census_file": CENSUS, "census_sha256": census_sha,
        "census_manifest_rolled": manifest["imports"]["rolled"],
        "seed_max": SEED_MAX, "k_last": K_LAST, "ws": WS,
        "sample_rng": SAMPLE_RNG,
        "counts": {"topout_games": len(picks["topouts"]),
                   "stall_games_sampled": len(picks["stalls"]),
                   "control_games_sampled": len(picks["controls"]),
                   "fatal_decisions": int(fatal["seed"].shape[0]),
                   "control_decisions": int(ctrl["seed"].shape[0])},
        "gate": {"pass": gate["pass"], "n_seeds": gate["n_seeds"],
                 "mutants": gate["mutants"]},
        "bulk_census_row_mismatches": mismatches,
        "stratum_key": "(max_height, min(viruses,30)//3, min(garbage_cum,48)//8)",
        "match_coverage_default_key": cov,
        "stall_seeds": picks["stalls"], "control_seeds": picks["controls"],
        "cand_vals_index": "vals[var*8+cc]; var {0,1}=HORIZ {2,3}=VERT "
                           "(o4 XOR 2 per fast_rtl_x._VAR_OF_O4); NaN = illegal drop",
        "outcome_code": OUTCOME_CODE, "end_kind_code": END_KIND,
    }
    with open(os.path.join(HERE, "dataset_meta.json"), "w") as f:
        json.dump(meta, f, indent=1)
    with open(os.path.join(HERE, "game_meta.json"), "w") as f:
        json.dump(game_meta, f)
    print(f"[done] fatal decisions {fatal['seed'].shape[0]}  "
          f"control decisions {ctrl['seed'].shape[0]}", flush=True)
    print(f"[done] match coverage (default key): {cov}", flush=True)
    print(f"[done] wrote fatal_windows.npz / controls.npz / dataset_meta.json / "
          f"game_meta.json / gate_result.json in {HERE}", flush=True)


if __name__ == "__main__":
    main()
