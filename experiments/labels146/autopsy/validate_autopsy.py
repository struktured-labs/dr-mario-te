#!/usr/bin/env python3
"""validate_autopsy.py — PREREG_AUTOPSY §5/§6.

  --labels true     the real labels: per-game verdict, then FORCED-MOVE
                    confirmation at each avoidable game's DEEPEST firing ply
  --labels shuffle  M-SHUFFLE: per-state seeded permutation of the label
                    vectors across candidates.  Must make claims (dose check)
                    and must NOT outperform true on confirmation.
  --labels mimic    M-MIMIC: labels := champion preference.  MUST yield ZERO
                    claims (absence-is-not-pass — a required FAILURE verdict).
  --positive-control  re-label each firing ply with FRESH sample indices
                    (offset +1000); the claim must re-fire.  Required before
                    any DOOMED verdict is reportable (§4, rule 8).
"""
from __future__ import annotations

import argparse
import gzip
import json
import os
import random
import sys
import time
from concurrent.futures import ProcessPoolExecutor, as_completed

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import autopsycore as AC   # noqa: E402

OUT = os.path.join(HERE, "out")
LABELS = os.path.join(OUT, "labels")
SHUFFLE_SEED = 20260822


def load_docs():
    docs = []
    for f in sorted(os.listdir(LABELS)):
        if f.startswith("autopsy_") and f.endswith(".json.gz"):
            with gzip.open(os.path.join(LABELS, f), "rt") as fh:
                docs.append(json.load(fh))
    docs.sort(key=lambda d: d["seed"])
    return docs


def relabel(doc, mode):
    """Rewrite every state's per-candidate label vectors for a mutant labeler.

    true    — untouched
    shuffle — the (surv, clear, vc) triples are permuted ACROSS candidates
              within a state, so the dose is preserved and only the
              attribution is destroyed
    mimic   — the labeler expresses the CHAMPION'S PREFERENCE: the candidate
              with the highest champion value gets a perfect label, the rest
              get zero.  Its claim rule then compares the champion against
              itself, which is why it cannot make a claim.
    """
    if mode == "true":
        return doc
    rng = random.Random(SHUFFLE_SEED ^ doc["seed"])
    for st in doc["states"]:
        ents = st["cands"]
        if mode == "shuffle":
            vecs = [(e["surv"], e["clear"], e["vc"]) for e in ents]
            rng.shuffle(vecs)
            for e, (s, c, v) in zip(ents, vecs):
                e["surv"], e["clear"], e["vc"] = s, c, v
        else:  # mimic
            vals = st["vals"]
            best = max(ents, key=lambda e: (vals[e["rep_slot"]]
                                            if vals[e["rep_slot"]] is not None
                                            else -1e18))
            for e in ents:
                hit = 1 if e is best else 0
                n = len(e["surv"])
                e["surv"] = [hit] * n
                e["clear"] = [hit] * n
                e["vc"] = [0] * n
    return doc


def claims_of(doc):
    """Re-run the registered claim rule over every scanned ply."""
    stall = (doc["result"] == "stall")
    out = []
    for st in doc["states"]:
        import numpy as np
        vals = np.array([np.nan if v is None else v for v in st["vals"]])
        cl = (AC.claim_stall if stall else AC.claim_topout)(
            st["cands"], st["a_champ"], vals)
        if cl:
            cl = dict(cl, ply=st["ply"], k=st["k"])
            out.append(cl)
    return out


def _forced(args):
    """Arm B: replay under the gate, force the claimed action, continue clean
    on the TRUE stream to the 300-pill cap."""
    seed, ply, slot, result_a, nmoves_a = args
    import adversary_harness as AH
    AH._lazy()
    C, _b = AC.init_rig()
    row = _CROWS[seed]
    env_at = None
    for p, env, vals, a in AC.replay_census_game(seed, C, row, want_plies={ply}):
        env_at = env
        break
    if env_at is None:
        return {"seed": seed, "ply": ply, "error": "ply not reached"}
    import copy
    e = copy.deepcopy(env_at)
    res, _v = AC._advance_clean(e, int(slot))
    n = 1
    while res is None:
        if e.board.virus_count() == 0:
            res = "clear"
            break
        _vals, a = AC.champ_decide(e, C)
        if a is None:
            res = "topout"
            break
        res, _v = AC._advance_clean(e, a)
        n += 1
    plies_b = ply + n
    H = AC.H_STALL if result_a == "stall" else AC.H_TOPOUT
    if result_a == "stall":
        confirmed = (res == "clear")
    else:
        confirmed = (res == "clear") or (plies_b - nmoves_a >= H)
    return {"seed": seed, "ply": ply, "forced_slot": int(slot),
            "res_b": res, "plies_b": plies_b, "vir_b": int(e.board.virus_count()),
            "res_a": result_a, "plies_a": nmoves_a,
            "label_endpoint": int(n >= H or res == "clear"),
            "confirmed": bool(confirmed)}


_CROWS = {}


def _init(crows):
    global _CROWS
    _CROWS = crows
    import adversary_harness as AH
    AH._lazy()


def census_rows_for(seeds):
    path = os.path.join(OUT, "census", "census.jsonl")
    want = set(seeds)
    rows = {}
    with open(path) as f:
        for line in f:
            try:
                r = json.loads(line)
            except json.JSONDecodeError:
                continue
            if r["seed"] in want:
                rows[r["seed"]] = r
    return rows


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--labels", default="true",
                    choices=["true", "shuffle", "mimic"])
    ap.add_argument("--workers", type=int, default=4)
    a = ap.parse_args()

    docs = load_docs()
    assert docs, "no autopsy label files"
    per_game, n_claims = [], 0
    for d in docs:
        cls = claims_of(relabel(d, a.labels))
        n_claims += len(cls)
        deepest = max(cls, key=lambda c: c["k"]) if cls else None
        per_game.append({"seed": d["seed"], "result": d["result"],
                         "viruses_left": d["viruses_left"],
                         "n_moves": d["n_moves"], "anchor": d["anchor"],
                         "n_scanned": len(d["states"]),
                         "verdict": "AVOIDABLE" if cls else "DOOMED",
                         "n_firing": len(cls),
                         "firing_k": [c["k"] for c in cls],
                         "deepest": deepest})

    n_av = sum(1 for g in per_game if g["verdict"] == "AVOIDABLE")
    print(f"[{a.labels}] games={len(per_game)} claims={n_claims} "
          f"AVOIDABLE={n_av} DOOMED={len(per_game) - n_av}", flush=True)

    if a.labels == "mimic":
        if n_claims != 0:
            sys.exit(f"V4 VOID: M-mimic produced {n_claims} claims — the claim "
                     f"rule is satisfiable by pure champion preference, so it "
                     f"is not measuring a counterfactual")
        print("MIMIC FAIL_NO_CLAIMS", flush=True)
        with open(os.path.join(OUT, "validate_mimic.json"), "w") as f:
            json.dump({"labeler": "mimic", "claims": 0,
                       "verdict": "FAIL_NO_CLAIMS"}, f, indent=2)
        print(f"VALIDATE_OK {a.labels}", flush=True)
        return

    # ------------------------------------------------ forced-move confirmation
    jobs = [(g["seed"], g["deepest"]["ply"], g["deepest"]["best_slot"],
             g["result"], g["n_moves"])
            for g in per_game if g["verdict"] == "AVOIDABLE"]
    crows = census_rows_for([j[0] for j in jobs]) if jobs else {}
    conf = []
    if jobs:
        t0 = time.time()
        with ProcessPoolExecutor(max_workers=a.workers, initializer=_init,
                                 initargs=(crows,)) as ex:
            futs = [ex.submit(_forced, j) for j in jobs]
            for i, fut in enumerate(as_completed(futs), 1):
                r = fut.result()
                conf.append(r)
                print(f"  forced {i}/{len(jobs)} seed {r['seed']} ply "
                      f"{r.get('ply')} -> {r.get('res_b')} "
                      f"confirmed={r.get('confirmed')}", flush=True)
        print(f"  ({time.time() - t0:.0f}s)", flush=True)
    n_conf = sum(1 for r in conf if r.get("confirmed"))
    rate = (n_conf / len(conf)) if conf else None
    print(f"[{a.labels}] forced-move confirmed {n_conf}/{len(conf)}"
          + (f" = {rate:.1%}" if rate is not None else ""), flush=True)

    doc = {"labeler": a.labels, "n_games": len(per_game), "n_claims": n_claims,
           "n_avoidable": n_av, "n_doomed": len(per_game) - n_av,
           "forced_confirmed": n_conf, "forced_n": len(conf),
           "confirm_rate": rate, "per_game": per_game, "forced": conf,
           "shuffle_seed": SHUFFLE_SEED if a.labels == "shuffle" else None}
    with open(os.path.join(OUT, f"validate_{a.labels}.json"), "w") as f:
        json.dump(doc, f, indent=2)
    print(f"VALIDATE_OK {a.labels}", flush=True)


if __name__ == "__main__":
    main()
