"""validate_cdeep.py — forced-move validation of the C-deep claims (§7 /
C-DEEP REGISTRATION secondary bar).

Per claim (seed, ply, claimed slot): arm A = the banked outcome (every C-deep
game is a topout); arm B = labelcore gated replay to the claim ply, FORCE the
claimed action, then champion-const continuation under the TRUE injection
(the rig's own path keyed on the game seed), max_pills=400.  Endpoint = game
failure (topout|stall) vs clear.  Rescued = arm B clears.  Broken (arm A
survived, arm B failed) is structurally impossible here — reported as such.

Resumable: one JSON per claim under out/val_cdeep/.
"""
import argparse
import glob
import gzip
import json
import os
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import numpy as np
import garbcore as G
import labelcore as LC

OUT = os.path.join(HERE, "out", "val_cdeep")


def cdeep_claims():
    claims = []
    for p in sorted(glob.glob(os.path.join(HERE, "out", "labels",
                                           "C_*.jsonl.gz"))):
        r = json.loads(gzip.open(p, "rt").readline())
        if r["stratum"] != "Cdeep":
            continue
        c = G.claims_from_row(r)
        if c:
            claims.append({"id": r["id"], "seed": r["seed"], "ply": r["ply"],
                           "k": r["k"], "slot": c["best_slot"],
                           "champ_surv": c["champ_surv"],
                           "best_surv": c["best_surv"]})
    return claims


def validate_one(cl):
    import oracle_arm as OA
    t0 = time.time()
    C, bmodel = LC.init_rig()
    seed = cl["seed"]
    rows, game = LC.load_bank_game(seed)
    assert game["res"] == "topout", (seed, game["res"])
    gen = LC.replay_game(seed, C, bmodel, rows)
    env = None
    while True:
        ply, env, vals, row = next(gen)
        if ply == cl["ply"]:
            break
    # FORCE the claimed action, then champion-const under TRUE injection
    res, _v = OA._advance(env, cl["slot"], C, seed, bmodel)
    plies = 1
    while res is None:
        if env.board.virus_count() == 0:
            res = "clear"
            break
        v = LC.compute_vals(env, C["w"], C["fl"], C["wt"], C["ws"])
        a = OA._champ_action(v, OA.CHAMP_ORDER)
        if a is None:
            res = "topout"
            break
        res, _v = OA._advance(env, a, C, seed, bmodel)
        plies += 1
    return {**cl, "armB_res": res, "rescued": res == "clear",
            "armB_plies": plies, "cpu_s": round(time.time() - t0, 1)}


def _worker(cl):
    return validate_one(cl)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--workers", type=int, default=12)
    args = ap.parse_args()
    os.makedirs(OUT, exist_ok=True)
    claims = cdeep_claims()
    todo = [c for c in claims
            if not os.path.exists(os.path.join(OUT, c["id"] + ".json"))]
    print(f"[val] claims={len(claims)} todo={len(todo)} "
          f"workers={args.workers}", flush=True)
    from concurrent.futures import ProcessPoolExecutor, as_completed
    t0 = time.time()
    with ProcessPoolExecutor(max_workers=args.workers) as ex:
        futs = {ex.submit(_worker, c): c for c in todo}
        for i, f in enumerate(as_completed(futs), 1):
            try:
                r = f.result()
            except LC.ReplayMismatch as ex_:
                r = {**futs[f], "armB_res": "REPLAY_ABORT",
                     "rescued": False, "abort": repr(ex_)}
            with open(os.path.join(OUT, r["id"] + ".json"), "w") as fh:
                json.dump(r, fh)
            print(f"[val] {i}/{len(todo)} {r['id']} k={r['k']} "
                  f"champ={r['champ_surv']} best={r['best_surv']} "
                  f"-> {r['armB_res']} wall={time.time()-t0:.0f}s", flush=True)

    done = [json.load(open(p)) for p in glob.glob(os.path.join(OUT, "*.json"))]
    ab = sum(d["armB_res"] == "REPLAY_ABORT" for d in done)
    ok = [d for d in done if d["armB_res"] != "REPLAY_ABORT"]
    resc = sum(d["rescued"] for d in ok)
    print(f"[val ledger] claims={len(claims)} validated={len(ok)} "
          f"aborts={ab} rescued={resc} rescue_rate={resc/max(1,len(ok)):.3f} "
          f"(broken structurally impossible: every arm A is a topout)",
          flush=True)
    # calibration: predicted dsurv vs realized rescue rate
    for lo, hi in ((3, 4), (5, 6), (7, 8)):
        b = [d for d in ok if lo <= d["best_surv"] - d["champ_surv"] <= hi]
        if b:
            print(f"[val calib] dsurv {lo}-{hi}: n={len(b)} "
                  f"rescue={sum(d['rescued'] for d in b)/len(b):.3f}",
                  flush=True)
    ks = {}
    for d in ok:
        ks.setdefault(d["k"], []).append(d["rescued"])
    for k in sorted(ks):
        v = ks[k]
        print(f"[val by-k] k={k}: n={len(v)} rescue={sum(v)/len(v):.3f}",
              flush=True)
    print("VAL_OK" if len(ok) + ab == len(claims) else "VAL_INCOMPLETE",
          flush=True)


if __name__ == "__main__":
    main()
