#!/usr/bin/env python3
"""ORACLE-CEILING RUNNER — paired-seed A/B, champion vs oracle re-ranker.

PRE-REGISTERED: `PREREG_ORACLE.md` (committed before any A/B game was played).

MATCHED-INDEX CONTROL: one work item = ONE SEED = BOTH ARMS.  The arms share the
seed, the capsule stream, the virus board and the garbage schedule; the only
difference is the label the root re-ranker is fed.  A completed item is a
COMPLETE PAIR, so an early stop yields a balanced prefix of the seed block, not
a lopsided one.  Seeds are consumed in ascending order.

SEGMENTED AND RESUMABLE, because long uninterruptible jobs starve on this box.
The seed block is cut into fixed-size segments; each segment writes its OWN
`seg_XXXX.jsonl` and, on completion, its own `seg_XXXX.summary.json`.  A killed
run loses at most one segment's in-flight pairs; re-running the identical
command skips every seed already on disk.  `--segment` never changes which seed
lands in which pair, so segmentation cannot move the estimate.

ARMS
  base : OracleArm(label_mode="const") — the shipped champion.  Proven
         outcome-identical to `pressure_rig.play` by `gate_identity.py` G1a.
  trt  : OracleArm(label_mode=<--label>) — "true" for the oracle, "shuffle" for
         the KILLED MUTANT (same forks, same cost, labels permuted).

PER-PLY FLIP PROVENANCE is on by default (`--provenance`): every flipped ply
records ply index, t_to_end, viruses, max height, d_spawn_h, the champion's rank
of the chosen action, base action, treatment action, whether the winning label
tied the champion's, and the four fork labels.  `CHAMPION_ITER_PLAN.md` makes
this mandatory for every future arm: 15,000 games produced a NO_GO with zero
mechanism because `flips` was logged as a bare integer.
"""
import argparse
import json
import os
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

MAX_FLIPLOG = 400          # per game; a 300-pill game cannot exceed this
_W = {}


def _winit(model, label, topk, horizon, provenance):
    import oracle_arm as O
    C, bmodel = O.init_rig(model)
    _W.update(O=O, C=C, bmodel=bmodel, model=model, label=label,
              topk=topk, horizon=horizon, provenance=provenance)


def _work(seed):
    O = _W["O"]
    t0 = time.monotonic()
    ab = O.OracleArm(label_mode="const", topk=_W["topk"],
                     horizon=_W["horizon"])
    rb = O.play_one(seed, ab, _W["C"], _W["bmodel"])
    at = O.OracleArm(label_mode=_W["label"], topk=_W["topk"],
                     horizon=_W["horizon"], provenance=_W["provenance"])
    rt = O.play_one(seed, at, _W["C"], _W["bmodel"])
    for r in (rb, rt):
        r.pop("_actions", None)
    rb["arm"], rt["arm"] = "base", "trt"
    if _W["provenance"]:
        rt["flip_log"] = at.flip_log[:MAX_FLIPLOG]
    return {"seed": seed, "model": _W["model"], "label": _W["label"],
            "base": rb, "trt": rt,
            "secs": round(time.monotonic() - t0, 2)}


def _done_seeds(outdir):
    done = set()
    if not os.path.isdir(outdir):
        return done
    for fn in sorted(os.listdir(outdir)):
        if not (fn.startswith("seg_") and fn.endswith(".jsonl")):
            continue
        for ln in open(os.path.join(outdir, fn)):
            try:
                done.add(json.loads(ln)["seed"])
            except Exception:
                pass
    return done


def _segment_summary(rows):
    """Cheap banked aggregate so a partial run is readable without analyse.py."""
    n = len(rows)
    if n == 0:
        return {"n_pairs": 0}
    def rate(arm, k):
        return sum(r[arm][k] for r in rows) / n
    fl = sum(r["trt"]["flips"] for r in rows)
    pl = sum(r["trt"]["plies_scored"] for r in rows)
    gp = sum(r["trt"]["gated_plies"] for r in rows)
    return {
        "n_pairs": n,
        "seed_min": min(r["seed"] for r in rows),
        "seed_max": max(r["seed"] for r in rows),
        "dies_ahead_base": rate("base", "dies_ahead"),
        "dies_ahead_trt": rate("trt", "dies_ahead"),
        "clear_base": rate("base", "won"), "clear_trt": rate("trt", "won"),
        "topout_base": rate("base", "topout"), "topout_trt": rate("trt", "topout"),
        "stall_base": rate("base", "stall"), "stall_trt": rate("trt", "stall"),
        "flip_rate_of_plies": fl / max(1, pl),
        "gated_frac_of_plies": gp / max(1, pl),
        "forks_total": sum(r["trt"]["forks"] for r in rows),
        "secs_total": sum(r["secs"] for r in rows)}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", choices=["lulu", "drip"], default="lulu")
    ap.add_argument("--label", choices=["true", "shuffle", "const"],
                    default="true",
                    help="'true' = the oracle; 'shuffle' = the KILLED MUTANT; "
                         "'const' = the identity control (must equal base)")
    ap.add_argument("--seed-start", type=int, required=True)
    ap.add_argument("--seed-count", type=int, required=True)
    ap.add_argument("--segment", type=int, default=250)
    ap.add_argument("--workers", type=int, default=5)
    ap.add_argument("--topk", type=int, default=4)
    ap.add_argument("--horizon", type=int, default=15)
    ap.add_argument("--outdir", required=True)
    ap.add_argument("--no-provenance", action="store_true")
    ap.add_argument("--allow-corpus-seeds", action="store_true",
                    help="ESCAPE HATCH for smoke tests only; never for a verdict run")
    a = ap.parse_args()

    assert a.workers <= 6, ("local worker cap is 6 (this box has been "
                            "OOM-killed 5 times)")
    if not a.allow_corpus_seeds:
        assert a.seed_start >= 30000, (
            "PREREG_ORACLE sec 3: oracle seeds start at 30000 -- disjoint from "
            "the corpus (2..12001) AND from the stage-2 rollout (20000..29999)")

    os.makedirs(a.outdir, exist_ok=True)
    prov = not a.no_provenance
    seeds = list(range(a.seed_start, a.seed_start + a.seed_count))
    done = _done_seeds(a.outdir)
    todo = [s for s in seeds if s not in done]
    print(f"model={a.model} label={a.label} topk={a.topk} horizon={a.horizon} "
          f"seeds={len(seeds)} already_done={len(done)} todo={len(todo)} "
          f"segment={a.segment} workers={a.workers}", flush=True)

    meta = {"model": a.model, "label": a.label, "topk": a.topk,
            "horizon": a.horizon, "seed_start": a.seed_start,
            "seed_count": a.seed_count, "segment": a.segment,
            "workers": a.workers, "provenance": prov,
            "gate": "d_spawn_h >= 12 OR viruses <= 8",
            "started": time.strftime("%Y-%m-%dT%H:%M:%S%z")}
    json.dump(meta, open(os.path.join(a.outdir, "META.json"), "w"), indent=1)

    from concurrent.futures import ProcessPoolExecutor, as_completed
    t_run = time.monotonic()
    n_all = 0
    with ProcessPoolExecutor(
            max_workers=a.workers, initializer=_winit,
            initargs=(a.model, a.label, a.topk, a.horizon, prov)) as ex:
        for s0 in range(0, len(seeds), a.segment):
            block = [s for s in seeds[s0:s0 + a.segment] if s in set(todo)]
            tag = f"seg_{a.seed_start + s0:06d}"
            if not block:
                continue
            path = os.path.join(a.outdir, tag + ".jsonl")
            rows = []
            t0 = time.monotonic()
            with open(path, "a") as fh:
                futs = {ex.submit(_work, s): s for s in block}
                for i, f in enumerate(as_completed(futs), 1):
                    r = f.result()
                    fh.write(json.dumps(r) + "\n")
                    fh.flush()
                    rows.append(r)
                    n_all += 1
                    if i % 10 == 0:
                        el = time.monotonic() - t0
                        print(f"  {tag} {i}/{len(block)} {el/60:.1f}min "
                              f"{2*i/el:.3f} games/s", flush=True)
            summ = _segment_summary(rows)
            summ["tag"] = tag
            summ["wall_secs"] = round(time.monotonic() - t0, 1)
            json.dump(summ, open(os.path.join(a.outdir, tag + ".summary.json"),
                                 "w"), indent=1)
            print(f"SEGMENT SUMMARY {tag}: " + json.dumps(summ), flush=True)
    el = time.monotonic() - t_run
    print(f"DONE {n_all} pairs in {el/60:.1f} min "
          f"({2*n_all/max(el,1e-9):.3f} games/s)", flush=True)


if __name__ == "__main__":
    main()
