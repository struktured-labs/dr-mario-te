"""run_h12_dataset.py — DISTILLATION DATASET runner (derivative of run_h12.py).

SEALED SOURCE, UNMODIFIED: `run_h12.py` and `h12_arm.py` produced the certified
H12 endpoint GO and are hashed into every META.json on disk.  This file and
`h12_arm_dataset.py` are clearly-labelled derivatives; neither edits a sealed
byte.  `gate_dataset_identity.py` proves the derivative plays identical games.

DELTAS FROM run_h12.py
  1. trt arm is `H12ArmDataset` — H12Arm plus a per-tie-ply record.
  2. Tie records are banked to their OWN file, `ties_<tag>.jsonl`, one JSON
     object per gated exact-tie ply.  They are NOT nested inside the pair rows:
     the pair rows stay shaped exactly like the sealed runner's so
     `analyse_oracle.py` can read this run's endpoint unchanged.
  3. Non-causal stamps (`nc_t_to_end`, `nc_res`) are added AFTER the game ends,
     for stratification only.  They are named so a leak into a feature matrix is
     visible in a column list.
  4. Seeds must be >= 60000 unless --allow-corpus-seeds: the H12 endpoint owns
     30000..50100 and the pilot must not touch a seed that carries a verdict.

Everything else — pairing, segmentation, banking, resume, freeze_meta — is the
proven harness, imported from run_h12 rather than re-typed, so it cannot drift.
"""
import argparse
import json
import os
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

from run_h12 import (freeze_meta, runtime_manifest, _done_seeds,  # noqa: E402
                     _load_segment, _segment_summary, MAX_FLIPLOG, _sha256)

_W = {}


def dataset_manifest(model):
    """`run_h12.runtime_manifest` PLUS the two derivative files.

    Inherited unchanged, the manifest hashes `run_h12.py` (its own __file__) and
    never sees `run_h12_dataset.py` or `h12_arm_dataset.py` — so a dataset would
    carry a code fingerprint that does not include the code that produced it.
    This project has already been bitten once by a cross-node skew that left
    every headline summary unchanged; an unhashed instrument is the same hole.
    """
    m = runtime_manifest(model)
    import hashlib
    for name in ("run_h12_dataset", "h12_arm_dataset"):
        path = os.path.join(HERE, name + ".py")
        m["files"][name] = {"path": path, "sha256": _sha256(path)}
    m["rolled"] = hashlib.sha256("".join(
        f"{n}:{d['sha256']}" for n, d in sorted(m["files"].items())
    ).encode()).hexdigest()
    return m


def _winit(model, label, topk, horizon, fork_samples, provenance,
           null_keep_num, null_keep_den, tie_margin):
    import oracle_arm as O
    C, bmodel = O.init_rig(model)
    _W.update(O=O, C=C, bmodel=bmodel, model=model, label=label, topk=topk,
              horizon=horizon, fork_samples=fork_samples,
              provenance=provenance, null_keep_num=null_keep_num,
              null_keep_den=null_keep_den, tie_margin=tie_margin)


def _work(seed):
    O = _W["O"]
    t0 = time.monotonic()
    ab = O.OracleArm(label_mode="const", topk=_W["topk"],
                     horizon=_W["horizon"])
    rb = O.play_one(seed, ab, _W["C"], _W["bmodel"])
    import h12_arm_dataset as D
    at = D.H12ArmDataset(label_mode=_W["label"], topk=_W["topk"],
                         horizon=_W["horizon"], provenance=_W["provenance"],
                         future_mode="dist",
                         fork_samples=_W["fork_samples"],
                         null_keep_num=_W["null_keep_num"],
                         null_keep_den=_W["null_keep_den"],
                         tie_margin=_W["tie_margin"])
    rt = O.play_one(seed, at, _W["C"], _W["bmodel"])
    for r in (rb, rt):
        r.pop("_actions", None)
    rb["arm"], rt["arm"] = "base", "trt"
    if _W["provenance"]:
        rt["flip_log"] = at.flip_log[:MAX_FLIPLOG]
    n_plies = rt["n_plies"]
    ties = at.tie_log
    for rec in ties:
        # NON-CAUSAL: unknown at decision time.  Stratify with these; never fit.
        rec["nc_t_to_end"] = n_plies - 1 - rec["ply"]
        rec["nc_res"] = rt["res"]
        rec["nc_dies_ahead"] = rt["dies_ahead"]
        rec["nc_base_res"] = rb["res"]
    rt["tie_plies"] = at.stats["tie_plies"]
    rt["margin_rejected_flips"] = at.stats["margin_rejected_flips"]
    rt["n_tie_records"] = len(ties)
    return ({"seed": seed, "model": _W["model"], "label": _W["label"],
             "future": "dist", "base": rb, "trt": rt,
             "secs": round(time.monotonic() - t0, 2)}, ties)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", choices=["lulu", "drip"], default="lulu")
    ap.add_argument("--label", choices=["true", "shuffle"], default="true")
    ap.add_argument("--seed-start", type=int, required=True)
    ap.add_argument("--seed-count", type=int, required=True)
    ap.add_argument("--segment", type=int, default=125)
    ap.add_argument("--workers", type=int, default=11)
    ap.add_argument("--topk", type=int, default=4)
    ap.add_argument("--horizon", type=int, default=15)
    ap.add_argument("--fork-samples", type=int, default=5)
    ap.add_argument("--null-keep-num", type=int, default=1)
    ap.add_argument("--null-keep-den", type=int, default=1)
    ap.add_argument("--tie-margin", type=float, default=0.5)
    ap.add_argument("--outdir", required=True)
    ap.add_argument("--no-provenance", action="store_true")
    ap.add_argument("--allow-corpus-seeds", action="store_true")
    a = ap.parse_args()

    assert 1 <= a.workers <= 12, "measured safe local worker range is 1..12"
    assert a.fork_samples >= 1 and a.tie_margin > 0
    if not a.allow_corpus_seeds:
        assert a.seed_start >= 60000, (
            "the H12 endpoint owns 30000..50100 and the stage-2/corpus blocks "
            "own 2..29999; the distillation pilot starts at 60000")

    os.makedirs(a.outdir, exist_ok=True)
    prov = not a.no_provenance
    seeds = list(range(a.seed_start, a.seed_start + a.seed_count))
    done = _done_seeds(a.outdir)
    todo = [s for s in seeds if s not in done]
    print(f"DATASET RUN model={a.model} label={a.label} topk={a.topk} "
          f"horizon={a.horizon} fork_samples={a.fork_samples} "
          f"seeds={len(seeds)} already_done={len(done)} todo={len(todo)} "
          f"segment={a.segment} workers={a.workers} "
          f"tie_margin={a.tie_margin}", flush=True)

    meta = {"model": a.model, "label": a.label, "future": "dist",
            "topk": a.topk, "horizon": a.horizon, "seed_start": a.seed_start,
            "seed_count": a.seed_count, "segment": a.segment,
            "workers": a.workers, "provenance": prov,
            "fork_samples": a.fork_samples,
            "null_keep_num": a.null_keep_num,
            "null_keep_den": a.null_keep_den,
            "gate": "d_spawn_h >= 12 OR viruses <= 8 AND exact top-2 tie",
            "tie_margin": a.tie_margin,
            "arm_class": "H12ArmDataset",
            "purpose": "H12 distillation phase-1 dataset (logging-only arm)",
            "started": time.strftime("%Y-%m-%dT%H:%M:%S%z")}
    manifest = dataset_manifest(a.model)
    freeze_meta(a.outdir, meta, manifest)
    print(f"runtime_manifest={manifest['rolled']}", flush=True)

    from concurrent.futures import ProcessPoolExecutor
    t_run = time.monotonic()
    n_all = n_ties = 0
    todo_set = set(todo)
    with ProcessPoolExecutor(
            max_workers=a.workers, initializer=_winit,
            initargs=(a.model, a.label, a.topk, a.horizon, a.fork_samples,
                      prov, a.null_keep_num, a.null_keep_den,
                      a.tie_margin)) as ex:
        for s0 in range(0, len(seeds), a.segment):
            block = [s for s in seeds[s0:s0 + a.segment] if s in todo_set]
            tag = f"seg_{a.seed_start + s0:06d}"
            if not block:
                continue
            path = os.path.join(a.outdir, tag + ".jsonl")
            tpath = os.path.join(a.outdir, "ties_" + tag + ".jsonl")
            t0 = time.monotonic()
            with open(path, "a") as fh, open(tpath, "a") as tfh:
                for i, (row, ties) in enumerate(ex.map(_work, block), 1):
                    fh.write(json.dumps(row) + "\n")
                    for rec in ties:
                        tfh.write(json.dumps(rec) + "\n")
                    fh.flush()
                    tfh.flush()
                    n_all += 1
                    n_ties += len(ties)
                    if i % 10 == 0:
                        el = time.monotonic() - t0
                        print(f"  {tag} {i}/{len(block)} {el/60:.1f}min "
                              f"{2*i/el:.3f} games/s ties={n_ties}", flush=True)
            summ = _segment_summary(_load_segment(path))
            summ["tag"] = tag
            summ["wall_secs"] = round(time.monotonic() - t0, 1)
            summ["tie_records"] = n_ties
            json.dump(summ, open(os.path.join(a.outdir, tag + ".summary.json"),
                                 "w"), indent=1)
            print(f"SEGMENT SUMMARY {tag}: " + json.dumps(summ), flush=True)
    el = time.monotonic() - t_run
    print(f"DONE {n_all} pairs, {n_ties} tie records in {el/60:.1f} min "
          f"({2*n_all/max(el,1e-9):.3f} games/s)", flush=True)


if __name__ == "__main__":
    main()
