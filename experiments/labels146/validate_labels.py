"""validate_labels.py — claim extraction + forced-move OUTCOME validation
(PREREG §5) with the mutant label sources (§6.5, §6.6).

--labels true    : claims from the harvested rollout labels.
--labels shuffle : per-state permutation of the candidate label vectors
                   (seeded rng, recorded) — dose-matched mutant; must NOT
                   outperform true.
--labels mimic   : the preference-mimicking labeler — candidate ranking = the
                   champion's own values.  Its top candidate is by definition
                   the champion's pick, so it can make ZERO counterfactual
                   claims; the verdict is FAIL_NO_CLAIMS by construction.

Validation per claim: arm A = the banked game outcome (already on disk);
arm B = gated replay to the claim ply, FORCE the claimed action, then the
unmodified champion continues under the true injection to game end.
"""
import argparse
import glob
import gzip
import json
import os
import random
import time
from math import comb

import numpy as np

import labelcore as LC

CLAIM_H = 25          # PREREG §3/§5: pilot claims are read at H=25
CLAIM_DSURV = 3       # max_c surv - surv_champ >= 3 (of N=8)
CLAIM_CHAMP_MAX = 5   # and surv_champ <= 5


def load_labels(out_dir):
    rows = []
    for f in sorted(glob.glob(os.path.join(out_dir, "labels_*.jsonl.gz"))):
        with gzip.open(f, "rt") as fh:
            rows += [json.loads(l) for l in fh]
    return rows


def order_pos(slot):
    import oracle_arm as OA
    return int(np.where(OA.CHAMP_ORDER == slot)[0][0])


def extract_claims(rows, mode):
    claims = []
    for r in rows:
        if r["H"] != CLAIM_H:
            continue
        cands = r["cands"]
        if mode == "mimic":
            # rank = champion values; champion's pick is rank-0 by definition
            surv = [r["N"] if r["a"] in e["slots"] else 0 for e in cands]
        else:
            surv = [sum(e["surv"]) for e in cands]
            if mode == "shuffle":
                rng = random.Random(r["seed"] * 100003 + r["ply"])
                perm = list(range(len(cands)))
                rng.shuffle(perm)
                surv = [surv[i] for i in perm]
        ci = next(i for i, e in enumerate(cands) if r["a"] in e["slots"])
        best = max(range(len(cands)),
                   key=lambda i: (surv[i],
                                  r["vals"][cands[i]["rep_slot"]] or -1e18,
                                  -order_pos(cands[i]["rep_slot"])))
        dsurv = surv[best] - surv[ci]
        if dsurv >= CLAIM_DSURV and surv[ci] <= CLAIM_CHAMP_MAX:
            claims.append({
                "seed": r["seed"], "ply": r["ply"], "stratum": r["stratum"],
                "k": r["k"], "action": cands[best]["rep_slot"],
                "base_action": r["a"], "dsurv": int(dsurv),
                "surv_champ": int(surv[ci]), "surv_best": int(surv[best]),
                "N": r["N"], "game_res": r["game_res"]})
    return claims


def forced_game(seed, ply, action):
    """Arm B: gated replay to `ply`, force `action`, champion continues."""
    import oracle_arm as OA
    C, bmodel = LC.init_rig()
    rows, game = LC.load_bank_game(seed)
    gen = LC.replay_game(seed, C, bmodel, rows)
    env = None
    for p, e, _vals, _row in gen:
        if p == ply:
            env = e
            break
    assert env is not None, (seed, ply)
    res, v_end = OA._advance(env, action, C, seed, bmodel)
    p = ply + 1
    while res is None and p < LC.MAX_PILLS:
        if env.board.virus_count() == 0:
            res = "clear"
            break
        vals = LC.compute_vals(env, C["w"], C["fl"], C["wt"], C["ws"])
        a = OA._champ_action(vals, OA.CHAMP_ORDER)
        if a is None:
            break
        res, v_end = OA._advance(env, a, C, seed, bmodel)
        p += 1
    if res is None:
        res = "stall"
    return {"res": res, "end_ply": p,
            "viruses_left": int(v_end) if v_end is not None else -1}


def _worker(c):
    b = forced_game(c["seed"], c["ply"], c["action"])
    a_fail = int(c["game_res"] != "clear")
    b_fail = int(b["res"] != "clear")
    return dict(c, b_res=b["res"], b_end_ply=b["end_ply"],
                a_fail=a_fail, b_fail=b_fail)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--labels", choices=["true", "shuffle", "mimic"],
                    default="true")
    ap.add_argument("--out", default=os.path.join(LC.HERE, "out", "labels"))
    ap.add_argument("--workers", type=int, default=4)
    ap.add_argument("--claims-only", action="store_true")
    args = ap.parse_args()

    rows = load_labels(args.out)
    assert rows, "no labels harvested"
    claims = extract_claims(rows, args.labels)
    n_states = len([r for r in rows if r["H"] == CLAIM_H])
    print(f"[validate:{args.labels}] states={n_states} claims={len(claims)}",
          flush=True)

    tag = args.labels
    cpath = os.path.join(LC.HERE, "out", f"claims_{tag}.jsonl")
    vpath = os.path.join(LC.HERE, "out", f"validate_{tag}.json")

    if args.labels == "mimic":
        verdict = {"mode": "mimic", "n_states": n_states, "n_claims": 0,
                   "verdict": "FAIL_NO_CLAIMS"}
        assert len(claims) == 0, ("mimic produced claims", claims[:3])
        with open(vpath, "w") as fh:
            json.dump(verdict, fh, indent=1)
        print("MIMIC FAIL_NO_CLAIMS (by construction: the preference-"
              "mimicking labeler makes no counterfactual claim, and "
              "absence-is-not-pass)", flush=True)
        return

    with open(cpath, "w") as fh:
        for c in claims:
            fh.write(json.dumps(c) + "\n")
    if args.claims_only:
        print(f"CLAIMS_OK {tag} n={len(claims)}", flush=True)
        return

    from concurrent.futures import ProcessPoolExecutor
    t0 = time.time()
    with ProcessPoolExecutor(max_workers=args.workers) as ex:
        results = list(ex.map(_worker, claims))
    rescued = sum(1 for r in results if r["a_fail"] and not r["b_fail"])
    broken = sum(1 for r in results if not r["a_fail"] and r["b_fail"])
    d = rescued + broken
    p_sign = (sum(comb(d, i) for i in range(rescued, d + 1)) / 2 ** d
              if d else None)
    pred = (np.mean([c["dsurv"] / c["N"] for c in claims])
            if claims else None)
    realized = (rescued - broken) / len(results) if results else None
    verdict = {
        "mode": tag, "n_states": n_states, "n_claims": len(claims),
        "n_pairs": len(results), "rescued": rescued, "broken": broken,
        "discordant": d, "sign_test_p_one_sided": p_sign,
        "mean_predicted_dsurv": None if pred is None else round(float(pred), 4),
        "realized_rescue_minus_break_rate":
            None if realized is None else round(realized, 4),
        "wall_s": round(time.time() - t0, 1),
        "per_claim": results,
    }
    with open(vpath, "w") as fh:
        json.dump(verdict, fh, indent=1)
    print(f"VALIDATE_OK {tag} claims={len(claims)} rescued={rescued} "
          f"broken={broken} p={p_sign} pred_dsurv={pred} "
          f"realized={realized}", flush=True)


if __name__ == "__main__":
    main()
