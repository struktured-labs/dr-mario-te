"""harvest_labels.py — replay banked games under the replay gate and label
target plies with dedup'd-candidate x N CRN dist-future forks (PREREG §1-3).

Work item = one SEED (per-seed atomic, resumable): one gated replay pass
labels all that seed's target plies.  Output out/labels/labels_<seed>.jsonl.gz,
one row per (state, horizon).
"""
import argparse
import gzip
import json
import os
import time

import labelcore as LC

N_SAMPLES = 8   # PREREG §3


def harvest_seed(seed, targets, out_dir):
    C, bmodel = LC.init_rig()
    rows, game = LC.load_bank_game(seed)
    want = {t["ply"]: t for t in targets}
    assert len(want) == len(targets), (seed, "duplicate target ply")
    out, t0 = [], time.time()
    forks = 0
    gen = LC.replay_game(seed, C, bmodel, rows)
    try:
        while True:
            ply, env, vals, row = next(gen)
            t = want.get(ply)
            if t is None:
                continue
            for H in t["Hs"]:
                ents = LC.label_state(env, C, bmodel, seed, ply,
                                      N_SAMPLES, H)
                forks += sum(len(e["surv"]) for e in ents)
                out.append({
                    "seed": seed, "ply": ply, "stratum": t["stratum"],
                    "k": t["k"], "H": H, "N": N_SAMPLES,
                    "vir": row["vir"], "dsh": row["dsh"],
                    "maxh": row["maxh"], "gate": row["gate"],
                    "a": row["a"], "vals": row["vals"],
                    "game_res": game["res"], "game_n_plies": game["n_plies"],
                    "cands": ents,
                })
    except StopIteration as stop:
        res = stop.value
    assert res == game["res"], (seed, res, game["res"])
    assert len(out) == sum(len(t["Hs"]) for t in targets), (seed, len(out))
    tmp = os.path.join(out_dir, f".labels_{seed}.tmp")
    dst = os.path.join(out_dir, f"labels_{seed}.jsonl.gz")
    with gzip.open(tmp, "wt") as fh:
        for r in out:
            fh.write(json.dumps(r) + "\n")
    os.replace(tmp, dst)
    return {"seed": seed, "rows": len(out), "forks": forks,
            "cpu_s": round(time.time() - t0, 1)}


def _worker(args):
    return harvest_seed(*args)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--targets", default=os.path.join(LC.HERE, "out",
                                                      "targets.json"))
    ap.add_argument("--out", default=os.path.join(LC.HERE, "out", "labels"))
    ap.add_argument("--workers", type=int, default=4)
    args = ap.parse_args()

    with open(args.targets) as fh:
        targets = json.load(fh)
    assert len(targets) == 80, len(targets)   # PREREG §2 startup assert
    by_seed = {}
    for t in targets:
        by_seed.setdefault(t["seed"], []).append(t)
    os.makedirs(args.out, exist_ok=True)
    todo = [(s, ts, args.out) for s, ts in sorted(by_seed.items())
            if not os.path.exists(os.path.join(args.out,
                                               f"labels_{s}.jsonl.gz"))]
    print(f"[harvest] seeds={len(by_seed)} todo={len(todo)} "
          f"workers={args.workers}", flush=True)
    from concurrent.futures import ProcessPoolExecutor, as_completed
    t0 = time.time()
    with ProcessPoolExecutor(max_workers=args.workers) as ex:
        futs = [ex.submit(_worker, w) for w in todo]
        done = 0
        for f in as_completed(futs):
            r = f.result()
            done += 1
            print(f"[harvest] {done}/{len(todo)} seed={r['seed']} "
                  f"rows={r['rows']} forks={r['forks']} "
                  f"cpu_s={r['cpu_s']} wall={time.time()-t0:.0f}s",
                  flush=True)
    print("HARVEST_OK", flush=True)


if __name__ == "__main__":
    main()
