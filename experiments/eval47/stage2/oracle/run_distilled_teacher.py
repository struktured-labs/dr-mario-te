#!/usr/bin/env python3
"""Resumable triple-paired runner: champion vs teacher vs shuffled teacher."""
from __future__ import annotations

import argparse
import hashlib
import importlib
import json
import os
import sys
import time
from concurrent.futures import ProcessPoolExecutor

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

MAX_FLIPLOG = 400
_W = {}


def _sha256(path):
    return hashlib.sha256(open(path, "rb").read()).hexdigest()


def runtime_manifest(policy_path):
    import distilled_teacher_arm as D
    import oracle_arm as O

    O.init_rig("exo_lulu")
    names = ("distilled_teacher_arm", "oracle_arm", "exogenous_pressure",
             "pressure_rig", "p0_ab", "bursty_model", "fast_rtl_x",
             "fast_sim_x", "root_search", "terms47", "s2_features",
             "feature_battery", "fb", "nes_pills", "drmario.faithful_env",
             "drmario.faithful_game")
    files = {"runner": os.path.abspath(__file__),
             "policy": os.path.abspath(policy_path)}
    for name in names:
        module = importlib.import_module(name)
        path = getattr(module, "__file__", None)
        if path:
            files[name] = os.path.abspath(path)
    per = {name: {"path": path, "sha256": _sha256(path)}
           for name, path in files.items()}
    rolled = hashlib.sha256("".join(
        f"{name}:{doc['sha256']}" for name, doc in sorted(per.items())
    ).encode()).hexdigest()
    return {"rolled": rolled, "files": per,
            "python": sys.version.split()[0]}


def freeze_meta(outdir, meta):
    path = os.path.join(outdir, "META.json")
    if os.path.exists(path):
        old = json.load(open(path))
        for doc in (old, meta):
            doc.pop("started", None)
            doc.pop("workers", None)
        if old != meta:
            raise RuntimeError("refusing to resume under changed settings/code")
        return
    with open(path, "w") as f:
        json.dump(meta, f, indent=1)


def _winit(policy_path, provenance):
    import distilled_teacher_arm as D
    import oracle_arm as O

    C, model = O.init_rig("exo_lulu")
    _W.update(D=D, O=O, C=C, model=model, bundle=D.load_policy(policy_path),
              provenance=provenance)


def _work(seed):
    O, D = _W["O"], _W["D"]
    t0 = time.monotonic()
    arms = {
        "base": O.OracleArm(label_mode="const"),
        "true": D.DistilledTeacherArm(
            _W["bundle"], "true", provenance=_W["provenance"]),
        "null": D.DistilledTeacherArm(
            _W["bundle"], "null", provenance=_W["provenance"]),
    }
    out = {"seed": int(seed), "model": "exo_lulu",
           "policy": "oracle-teacher-dt2-v1"}
    for name, arm in arms.items():
        row = O.play_one(seed, arm, _W["C"], _W["model"])
        row.pop("_actions", None)
        row["arm"] = name
        row["policy_eligible"] = int(arm.stats.get("eligible", 0))
        if name != "base" and _W["provenance"]:
            row["flip_log"] = arm.flip_log[:MAX_FLIPLOG]
        out[name] = row
    out["secs"] = round(time.monotonic() - t0, 2)
    return out


def _load_rows(outdir):
    by_seed = {}
    if not os.path.isdir(outdir):
        return []
    for fn in sorted(os.listdir(outdir)):
        if not (fn.startswith("seg_") and fn.endswith(".jsonl")):
            continue
        for line in open(os.path.join(outdir, fn)):
            try:
                row = json.loads(line)
                by_seed.setdefault(int(row["seed"]), row)
            except Exception:
                pass
    return [by_seed[s] for s in sorted(by_seed)]


def _summary(rows):
    n = len(rows)
    if not n:
        return {"n_triples": 0}
    out = {"n_triples": n, "seed_min": rows[0]["seed"],
           "seed_max": rows[-1]["seed"]}
    for arm in ("base", "true", "null"):
        plies = sum(r[arm]["plies_scored"] for r in rows)
        out[arm] = {
            "clear": sum(r[arm]["won"] for r in rows) / n,
            "topout": sum(r[arm]["topout"] for r in rows) / n,
            "stall": sum(r[arm]["stall"] for r in rows) / n,
            "bad_end": sum(r[arm]["topout"] or r[arm]["stall"]
                           for r in rows) / n,
            "dies_ahead": sum(r[arm]["dies_ahead"] for r in rows) / n,
            "flips": sum(r[arm]["flips"] for r in rows),
            "plies": plies,
            "flip_rate": sum(r[arm]["flips"] for r in rows) / max(1, plies),
            "garbage_per_ply": sum(r[arm]["garbage"] for r in rows)
                               / max(1, plies),
            "forks": sum(r[arm]["forks"] for r in rows),
        }
    out["core_seconds"] = round(sum(r["secs"] for r in rows), 2)
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--seed-start", type=int, required=True)
    ap.add_argument("--seed-count", type=int, required=True)
    ap.add_argument("--segment", type=int, default=30)
    ap.add_argument("--workers", type=int, default=4)
    ap.add_argument("--policy", default=os.path.join(
        HERE, "oracle_teacher_dt2_v1.json"))
    ap.add_argument("--outdir", required=True)
    ap.add_argument("--no-provenance", action="store_true")
    ap.add_argument("--allow-unregistered", action="store_true")
    a = ap.parse_args()
    if not a.allow_unregistered:
        assert (a.seed_start, a.seed_count) == (51300, 60), (
            "PREREG_DISTILLED_TEACHER fixes E0 at seeds 51300..51359")
    assert 1 <= a.workers <= 12
    a.policy = os.path.abspath(a.policy)
    os.makedirs(a.outdir, exist_ok=True)
    manifest = runtime_manifest(a.policy)
    meta = {
        "seed_start": a.seed_start, "seed_count": a.seed_count,
        "segment": a.segment, "workers": a.workers,
        "model": "exo_lulu", "pressure_mode": "candidate-independent",
        "policy": a.policy, "policy_sha256": _sha256(a.policy),
        "provenance": not a.no_provenance,
        "prereg": "PREREG_DISTILLED_TEACHER.md",
        "runtime_manifest": manifest,
        "started": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
    }
    freeze_meta(a.outdir, meta)
    rows = _load_rows(a.outdir)
    done = {r["seed"] for r in rows}
    seeds = list(range(a.seed_start, a.seed_start + a.seed_count))
    print(f"runtime_manifest={manifest['rolled']} policy={meta['policy_sha256']}")
    print(f"seeds={len(seeds)} done={len(done)} workers={a.workers}", flush=True)
    with ProcessPoolExecutor(
            max_workers=a.workers, initializer=_winit,
            initargs=(a.policy, not a.no_provenance)) as ex:
        for off in range(0, len(seeds), a.segment):
            block_all = seeds[off:off + a.segment]
            block = [s for s in block_all if s not in done]
            if not block:
                continue
            tag = f"seg_{block_all[0]:06d}"
            path = os.path.join(a.outdir, tag + ".jsonl")
            t0 = time.monotonic()
            with open(path, "a") as f:
                for i, row in enumerate(ex.map(_work, block, chunksize=1), 1):
                    f.write(json.dumps(row) + "\n")
                    f.flush()
                    if i % 5 == 0:
                        print(f"  {tag} {i}/{len(block)} "
                              f"{(time.monotonic()-t0)/60:.1f}min", flush=True)
            rows = _load_rows(a.outdir)
            summary = _summary([r for r in rows if r["seed"] in block_all])
            with open(os.path.join(a.outdir, tag + ".summary.json"), "w") as f:
                json.dump(summary, f, indent=1)
            print("SEGMENT " + json.dumps(summary), flush=True)
    rows = _load_rows(a.outdir)
    print("FINAL " + json.dumps(_summary(rows), indent=1), flush=True)


if __name__ == "__main__":
    main()

