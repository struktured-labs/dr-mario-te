"""run_h13.py — H13 GATE-V2 ARM runner (sealed copy of run_oracle.py, 2026-08-15).

Deltas from run_oracle.py: trt arm is H12Arm (tie-only trigger, theta-margin dose
gate, sampled futures); adds --tie-margin. Everything else — pairing, segments,
banking, provenance, resume — is the proven harness verbatim.
---- original run_oracle.py header ----
ORACLE-CEILING RUNNER — paired-seed A/B, champion vs oracle re-ranker.

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
  trt  : OracleArm(label_mode=<--label>, future_mode=<--future>) — "true" for
         the oracle, "shuffle" for the dose-matched KILLED MUTANT (same forks,
         same cost, labels permuted and deterministically thinned).

PER-PLY FLIP PROVENANCE is on by default (`--provenance`): every flipped ply
records ply index, t_to_end, viruses, max height, d_spawn_h, the champion's rank
of the chosen action, base action, treatment action, whether the winning label
tied the champion's, and the four fork labels.  `CHAMPION_ITER_PLAN.md` makes
this mandatory for every future arm: 15,000 games produced a NO_GO with zero
mechanism because `flips` was logged as a bare integer.
"""
import argparse
import hashlib
import importlib
import json
import os
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

MAX_FLIPLOG = 400          # per game; a 300-pill game cannot exceed this
_W = {}


def _sha256(path):
    with open(path, "rb") as fh:
        return hashlib.sha256(fh.read()).hexdigest()


def runtime_manifest(model):
    """Hash the modules ACTUALLY imported by the decision path.

    Long jobs outlive edits and remote syncs.  A result without the exact code
    paths and hashes that produced it is not bankable; this project has already
    caught one cross-node skew that left every headline summary unchanged.
    """
    import oracle_arm as O
    O.init_rig(model)
    names = ("oracle_arm", "pressure_rig", "p0_ab", "bursty_model",
             "fast_rtl_x", "fast_sim_x", "root_search", "terms47", "fb",
             "nes_pills", "drmario.faithful_env", "drmario.faithful_game")
    files = {"run_oracle": os.path.abspath(__file__)}
    for name in names:
        module = importlib.import_module(name)
        path = getattr(module, "__file__", None)
        if path:
            files[name] = os.path.abspath(path)
    p0 = importlib.import_module("p0_ab")
    files["dr_lulu_fit"] = os.path.abspath(p0.LULU_FIT)
    per = {name: {"path": path, "sha256": _sha256(path)}
           for name, path in files.items()}
    rolled = hashlib.sha256("".join(
        f"{name}:{doc['sha256']}"
        for name, doc in sorted(per.items())).encode()).hexdigest()
    return {"rolled": rolled, "files": per,
            "python": sys.version.split()[0]}


def freeze_meta(outdir, meta, manifest):
    """Write META once; refuse to append rows under changed semantics/code."""
    path = os.path.join(outdir, "META.json")
    frozen = dict(meta)
    frozen["runtime_manifest"] = manifest
    if os.path.exists(path):
        old = json.load(open(path))
        # Start time and worker count do not affect which paired games are run.
        for doc in (old, frozen):
            doc.pop("started", None)
            doc.pop("workers", None)
        if old != frozen:
            raise RuntimeError(
                "refusing to resume into an output directory whose frozen "
                "settings or runtime code manifest differ")
        return
    with open(path, "w") as fh:
        json.dump(frozen, fh, indent=1)


def _winit(model, label, future, topk, horizon, fork_samples, provenance,
           null_keep_num, null_keep_den, tie_margin, maxh_thresh):
    import oracle_arm as O
    C, bmodel = O.init_rig(model)
    _W.update(O=O, C=C, bmodel=bmodel, model=model, label=label,
              future=future, topk=topk, horizon=horizon,
              fork_samples=fork_samples, provenance=provenance,
              null_keep_num=null_keep_num, null_keep_den=null_keep_den,
              tie_margin=tie_margin, maxh_thresh=maxh_thresh)


def _work(seed):
    """THREE arms per seed, sharing the seed, board, capsules and pressure.

    H13's question is H13-vs-H12, but the H12 lane's analyser is built around a
    common const control and a difference-in-differences against it. Running
    all three on the SAME seed gives both readings from one work item: the
    direct paired H12-vs-H13 contrast, and each arm's DiD against the identical
    champion trajectory. It also means the pilot re-measures H12 on ITS OWN
    seeds rather than importing the sealed endpoint's numbers from a different
    seed block, which would not be paired.

    Cost is therefore ~2x an H12 pair (two forking arms, not one).
    """
    import h13_arm as H13
    O = _W["O"]
    t0 = time.monotonic()
    ab = O.OracleArm(label_mode="const", topk=_W["topk"],
                     horizon=_W["horizon"])
    rb = O.play_one(seed, ab, _W["C"], _W["bmodel"])

    def _arm(gate_mode):
        return H13.H13Arm(gate_mode=gate_mode, maxh_thresh=_W["maxh_thresh"],
                          label_mode=_W["label"], topk=_W["topk"],
                          horizon=_W["horizon"], provenance=_W["provenance"],
                          future_mode="dist",
                          fork_samples=_W["fork_samples"],
                          null_keep_num=_W["null_keep_num"],
                          null_keep_den=_W["null_keep_den"],
                          tie_margin=_W["tie_margin"])

    a1, a2 = _arm("v1"), _arm("v2")
    r1 = O.play_one(seed, a1, _W["C"], _W["bmodel"])
    rt = O.play_one(seed, a2, _W["C"], _W["bmodel"])
    for r in (rb, r1, rt):
        r.pop("_actions", None)
    rb["arm"], r1["arm"], rt["arm"] = "base", "h12", "trt"
    r1["arm_tag"], rt["arm_tag"] = a1.arm_tag(), a2.arm_tag()
    for r, arm in ((r1, a1), (rt, a2)):
        r["v1_gated_plies"] = arm.stats["v1_gated_plies"]
        r["v2_only_gated_plies"] = arm.stats["v2_only_gated_plies"]
        r["tie_plies"] = arm.stats["tie_plies"]
        r["margin_rejected_flips"] = arm.stats["margin_rejected_flips"]
    if _W["provenance"]:
        r1["flip_log"] = a1.flip_log[:MAX_FLIPLOG]
        rt["flip_log"] = a2.flip_log[:MAX_FLIPLOG]
    return {"seed": seed, "model": _W["model"], "label": _W["label"],
            "future": _W["future"],
            "base": rb, "h12": r1, "trt": rt,
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


def _load_segment(path):
    """Load one banked segment, de-duplicated and sorted by registered seed."""
    by_seed = {}
    if not os.path.exists(path):
        return []
    for line in open(path):
        try:
            row = json.loads(line)
        except Exception:
            continue
        by_seed.setdefault(int(row["seed"]), row)
    return [by_seed[seed] for seed in sorted(by_seed)]


def _segment_summary(rows):
    """Cheap banked aggregate so a partial run is readable without analyse.py."""
    n = len(rows)
    if n == 0:
        return {"n_pairs": 0}
    def rate(arm, k):
        return sum(r[arm][k] for r in rows) / n
    fl = sum(r["trt"]["flips"] for r in rows)
    fl12 = sum(r["h12"]["flips"] for r in rows)
    pl12 = sum(r["h12"]["plies_scored"] for r in rows)
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
        "dies_ahead_h12": rate("h12", "dies_ahead"),
        "clear_h12": rate("h12", "won"),
        "topout_h12": rate("h12", "topout"),
        "stall_h12": rate("h12", "stall"),
        "flip_rate_of_plies": fl / max(1, pl),
        "flip_rate_of_plies_h12": fl12 / max(1, pl12),
        "v2_only_gated_frac": sum(r["trt"]["v2_only_gated_plies"]
                                  for r in rows) / max(1, pl),
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
    ap.add_argument("--future", choices=["clair", "dist"], default="clair",
                    help="clair = realized future (ideal ceiling); dist = "
                         "sampled garbage future")
    ap.add_argument("--seed-start", type=int, required=True)
    ap.add_argument("--seed-count", type=int, required=True)
    ap.add_argument("--segment", type=int, default=250)
    ap.add_argument("--workers", type=int, default=5)
    ap.add_argument("--topk", type=int, default=4)
    ap.add_argument("--horizon", type=int, default=15)
    ap.add_argument("--fork-samples", type=int, default=1,
                    help="K sampled pressure futures for DIST sensitivity")
    ap.add_argument("--null-keep-num", type=int, default=1,
                    help="shuffle only: numerator of fixed hash-thinning dose")
    ap.add_argument("--null-keep-den", type=int, default=1,
                    help="shuffle only: denominator of fixed hash-thinning dose")
    ap.add_argument("--outdir", required=True)
    ap.add_argument("--no-provenance", action="store_true")
    ap.add_argument("--maxh-thresh", type=int, default=13,
                    help="gate-v2 any-column height threshold T (prereg "
                         "primary 13, secondary 12)")
    ap.add_argument("--tie-margin", type=float, default=0.5,
                    help="theta_margin dose gate (calibration freeze: 0.5)")
    ap.add_argument("--allow-corpus-seeds", action="store_true",
                    help="ESCAPE HATCH for smoke tests only; never for a verdict run")
    a = ap.parse_args()

    assert 1 <= a.workers <= 12, "measured safe local worker range is 1..12"
    assert a.fork_samples >= 1
    assert 0 <= a.null_keep_num <= a.null_keep_den and a.null_keep_den > 0
    assert a.future == "dist", "H12 is sampled-futures only"
    assert a.tie_margin > 0
    if a.label != "shuffle":
        assert (a.null_keep_num, a.null_keep_den) == (1, 1), (
            "null thinning is valid only for the shuffled-label arm")
    if not a.allow_corpus_seeds:
        assert a.seed_start >= 30000, (
            "PREREG_ORACLE sec 3: oracle seeds start at 30000 -- disjoint from "
            "the corpus (2..12001) AND from the stage-2 rollout (20000..29999)")

    os.makedirs(a.outdir, exist_ok=True)
    prov = not a.no_provenance
    seeds = list(range(a.seed_start, a.seed_start + a.seed_count))
    done = _done_seeds(a.outdir)
    todo = [s for s in seeds if s not in done]
    print(f"model={a.model} label={a.label} future={a.future} topk={a.topk} "
          f"horizon={a.horizon} fork_samples={a.fork_samples} "
          f"seeds={len(seeds)} already_done={len(done)} todo={len(todo)} "
          f"segment={a.segment} workers={a.workers} null_keep="
          f"{a.null_keep_num}/{a.null_keep_den} tie_margin={a.tie_margin}", flush=True)

    meta = {"model": a.model, "label": a.label, "future": a.future,
            "topk": a.topk,
            "horizon": a.horizon, "seed_start": a.seed_start,
            "seed_count": a.seed_count, "segment": a.segment,
            "workers": a.workers, "provenance": prov,
            "fork_samples": a.fork_samples,
            "null_keep_num": a.null_keep_num,
            "null_keep_den": a.null_keep_den,
            "gate": (f"trt: max(H) >= {a.maxh_thresh} OR d_spawn_h >= 12 OR "
                     "viruses <= 8 AND exact top-2 tie; "
                     "h12: d_spawn_h >= 12 OR viruses <= 8 AND exact top-2 tie"),
            "maxh_thresh": a.maxh_thresh,
            "tie_margin": a.tie_margin, "arm_class": "H13Arm",
            "arms": ["base=const", "h12=gate_v1", "trt=gate_v2"],
            "prereg": "PREREG_H13.md",
            "started": time.strftime("%Y-%m-%dT%H:%M:%S%z")}
    manifest = runtime_manifest(a.model)
    freeze_meta(a.outdir, meta, manifest)
    print(f"runtime_manifest={manifest['rolled']}", flush=True)

    from concurrent.futures import ProcessPoolExecutor
    t_run = time.monotonic()
    n_all = 0
    todo_set = set(todo)
    with ProcessPoolExecutor(
            max_workers=a.workers, initializer=_winit,
            initargs=(a.model, a.label, a.future, a.topk, a.horizon,
                      a.fork_samples, prov, a.null_keep_num,
                      a.null_keep_den, a.tie_margin, a.maxh_thresh)) as ex:
        for s0 in range(0, len(seeds), a.segment):
            block = [s for s in seeds[s0:s0 + a.segment] if s in todo_set]
            tag = f"seg_{a.seed_start + s0:06d}"
            if not block:
                continue
            path = os.path.join(a.outdir, tag + ".jsonl")
            t0 = time.monotonic()
            with open(path, "a") as fh:
                # Executor.map computes concurrently but yields in input order.
                # Banking as_completed() made an interrupted segment a
                # game-length-biased subset, contradicting the preregistered
                # balanced-prefix early-stop claim.
                for i, r in enumerate(ex.map(_work, block), 1):
                    fh.write(json.dumps(r) + "\n")
                    fh.flush()
                    n_all += 1
                    if i % 10 == 0:
                        el = time.monotonic() - t0
                        print(f"  {tag} {i}/{len(block)} {el/60:.1f}min "
                              f"{2*i/el:.3f} games/s", flush=True)
            # Include any prefix banked by an earlier interrupted invocation;
            # summarising only newly completed rows made resume summaries lie.
            summ = _segment_summary(_load_segment(path))
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
