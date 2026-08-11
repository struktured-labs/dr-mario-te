#!/usr/bin/env python3
"""Audit whether first action flips are exact linked-board aliases."""
from __future__ import annotations

import argparse
import collections
import hashlib
import importlib
import json
import os
import sys
import time
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
ORACLE = HERE.parent / "oracle"
for path in (str(HERE), str(ORACLE)):
    if path not in sys.path:
        sys.path.insert(0, path)

import dspawn_tie_v8 as D  # noqa: E402
import firmware_v8_policy as V8  # noqa: E402
import oracle_arm as O  # noqa: E402

FIT = ("/home/struktured/projects/dr-mario-te/source/experiments/eval47/results/"
       "dr_lulu_20260808_fit.json")
N_FINAL = 9000
_W = {}


def sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def load_rows(root):
    root = Path(root)
    meta_path = root / "META.json"
    if not meta_path.exists():
        raise RuntimeError("input META.json is missing")
    meta = json.loads(meta_path.read_text())
    rows, paths = {}, []
    for path in sorted(root.glob("seg_*.jsonl")):
        paths.append(path)
        for lineno, line in enumerate(path.open(), 1):
            try:
                row = json.loads(line)
            except Exception as exc:
                raise RuntimeError(f"{path.name}:{lineno}: invalid JSON: {exc}")
            seed = int(row["seed"])
            if seed in rows:
                raise RuntimeError(f"duplicate seed {seed}")
            rows[seed] = row
    ordered = [rows[s] for s in sorted(rows)]
    if [int(r["seed"]) for r in ordered] != list(range(61000, 61000 + len(ordered))):
        raise RuntimeError("input is not the registered ascending seed prefix")
    digest = hashlib.sha256()
    for path in paths:
        digest.update(path.name.encode() + b"\0")
        digest.update(path.read_bytes())
    return ordered, paths, digest.hexdigest(), meta_path, meta


def runtime_manifest():
    names = ("dspawn_tie_v8", "firmware_v8_policy", "oracle_arm",
             "pressure_rig", "p0_ab", "bursty_model", "exogenous_pressure",
             "cascade_chain_x", "cascade_link_x", "cascade_stranded_x",
             "fast_rtl_x", "fast_sim_x", "nes_pills", "drmario.faithful_env",
             "drmario.faithful_game")
    files = {"audit": str(Path(__file__).resolve()), "fit": FIT}
    for name in names:
        files[name] = str(Path(importlib.import_module(name).__file__).resolve())
    docs = {name: {"path": path, "sha256": sha256(path)}
            for name, path in files.items()}
    rolled = hashlib.sha256("".join(
        f"{name}:{doc['sha256']}" for name, doc in sorted(docs.items()))
        .encode()).hexdigest()
    return {"rolled": rolled, "files": docs, "python": sys.version.split()[0]}


def first_targets(row):
    out = []
    for arm in ("treatment", "null"):
        logs = row[arm].get("flip_log", [])
        if logs:
            out.append({"arm": arm, "flip": min(logs, key=lambda f: int(f["ply"]))})
    return out


def _init():
    os.environ["DR_LULU_FIT"] = FIT
    C, model = O.init_rig("exo_lulu")
    _W.update(C=C, model=model)


def post_root(col, vir, lnk, ca, cb, action):
    c = np.empty(V8.CH.NCELL, dtype=np.int8)
    v = np.empty(V8.CH.NCELL, dtype=np.int8)
    l = np.empty(V8.CH.NCELL, dtype=np.int8)
    mask = np.empty(V8.CH.NCELL, dtype=np.int8)
    action = int(action)
    ok, nv, cells, chain = V8.CH._expand_chain(
        col, vir, lnk, action // 8, action % 8, int(ca), int(cb),
        c, v, l, mask, 0)
    if not ok:
        raise RuntimeError(f"logged action {action} is illegal")
    return c.copy(), v.copy(), l.copy(), (int(nv), int(cells), int(chain))


def lane_height(col):
    height = 0
    for lane in (3, 4):
        for row in range(16):
            if col[row * 8 + lane] != 0:
                height = max(height, 16 - row)
                break
    return height


def exact_alias(left, right):
    return (left[3] == right[3]
            and np.array_equal(left[0], right[0])
            and np.array_equal(left[1], right[1])
            and np.array_equal(left[2], right[2]))


def base_action_matches(actual, logged):
    return int(actual) == int(logged)


def target_accounting(expected, consumed):
    return sorted(expected) == sorted(consumed)


def audit_seed(item):
    seed, targets = item
    C, model = _W["C"], _W["model"]
    by_ply = collections.defaultdict(list)
    for target in targets:
        by_ply[int(target["flip"]["ply"])].append(target)
    expected = [(t["arm"], int(t["flip"]["ply"])) for t in targets]
    max_ply = max(by_ply)
    env = O.make_env(seed, C["level"])
    consumed, records, errors = [], [], []
    for ply in range(max_ply + 1):
        if env.board.virus_count() == 0:
            errors.append(f"base cleared before target ply {max_ply}")
            break
        col, vir, lnk = D.board_inputs(env)
        vals = V8.candidate_values(
            col, vir, lnk, int(env.cur.a), int(env.cur.b),
            int(env.nxt.a), int(env.nxt.b), C["w"], C["fl"])
        base = V8.choose_seeded(vals, O.policy_tie_seed(seed, "p2_surrogate"))
        if base is None:
            errors.append(f"base topout before target ply {max_ply}")
            break
        for target in by_ply.get(ply, []):
            f, arm = target["flip"], target["arm"]
            consumed.append((arm, ply))
            if not base_action_matches(base, f["base_action"]):
                errors.append(
                    f"{arm} ply {ply}: base {base} != log {f['base_action']}")
                continue
            alt = int(f["treatment_action"])
            pb = post_root(col, vir, lnk, env.cur.a, env.cur.b, base)
            pa = post_root(col, vir, lnk, env.cur.a, env.cur.b, alt)
            hb, ha = lane_height(pb[0]), lane_height(pa[0])
            if hb != int(f["base_post_d_spawn_h"]):
                errors.append(f"{arm} ply {ply}: base sensor mismatch")
            if ha != int(f["chosen_post_d_spawn_h"]):
                errors.append(f"{arm} ply {ply}: chosen sensor mismatch")
            records.append({
                "seed": int(seed), "arm": arm, "ply": int(ply),
                "semantic_alias": bool(exact_alias(pb, pa)),
                "color_hamming": int(np.count_nonzero(pb[0] != pa[0])),
                "virus_hamming": int(np.count_nonzero(pb[1] != pa[1])),
                "link_hamming": int(np.count_nonzero(pb[2] != pa[2])),
                "metadata_equal": bool(pb[3] == pa[3]),
                "same_color_pill": bool(int(env.cur.a) == int(env.cur.b)),
                "base_action": int(base), "alternative_action": alt,
                "base_variant": int(base // 8), "alternative_variant": int(alt // 8),
                "base_col": int(base % 8), "alternative_col": int(alt % 8),
                "sensor_drop": int(hb - ha),
            })
        if ply < max_ply:
            out, _vir = O._advance(env, base, C, seed, model)
            if out is not None:
                errors.append(f"base ended {out} before target ply {max_ply}")
                break
    if not target_accounting(expected, consumed):
        errors.append(f"target accounting {consumed} != {expected}")
    return {"seed": int(seed), "records": records, "errors": errors}


def hist(values):
    count = collections.Counter(values)
    return {str(k): int(count[k]) for k in sorted(count)}


def summarize(records):
    n = len(records)
    alias = [r for r in records if r["semantic_alias"]]
    distinct = [r for r in records if not r["semantic_alias"]]
    return {
        "n": n, "aliases": len(alias), "distinct_boards": len(distinct),
        "alias_fraction": len(alias) / n if n else None,
        "color_hamming": hist(r["color_hamming"] for r in records),
        "virus_hamming": hist(r["virus_hamming"] for r in records),
        "link_hamming": hist(r["link_hamming"] for r in records),
        "sensor_drop": hist(r["sensor_drop"] for r in records),
        "same_color_pill": int(sum(r["same_color_pill"] for r in records)),
        "variant_transition": hist(
            f"{r['base_variant']}->{r['alternative_variant']}" for r in records),
        "column_transition": hist(
            f"{r['base_col']}->{r['alternative_col']}" for r in records),
        "alias_split": {
            "alias_same_color": int(sum(r["same_color_pill"] for r in alias)),
            "alias_sensor_drop": hist(r["sensor_drop"] for r in alias),
            "distinct_same_color": int(sum(r["same_color_pill"] for r in distinct)),
            "distinct_sensor_drop": hist(r["sensor_drop"] for r in distinct),
        },
    }


def killed_mutants():
    z = np.zeros(128, dtype=np.int8)
    good = (z.copy(), z.copy(), z.copy(), (0, 0, 0))
    bad = (z.copy(), z.copy(), z.copy(), (0, 0, 0))
    bad[0][0] = 1
    return {
        "self_board_alias_positive": bool(exact_alias(good, good)),
        "one_color_byte_rejected": bool(not exact_alias(good, bad)),
        "changed_logged_base_rejected": bool(not base_action_matches(4, 5)),
        "missing_target_rejected": bool(not target_accounting(
            [("null", 3)], [])),
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default=str(HERE / "out" / "evaluation"))
    ap.add_argument("--workers", type=int, default=16)
    ap.add_argument("--allow-partial", action="store_true")
    ap.add_argument("--limit", type=int, default=0,
                    help="implementation smoke only: first N rows with a flip")
    ap.add_argument("--out", default=str(HERE / "out" / "null_semantic_audit.json"))
    args = ap.parse_args()
    rows, paths, input_hash, meta_path, meta = load_rows(args.root)
    if len(rows) != N_FINAL and not args.allow_partial:
        raise SystemExit(f"refusing final audit: have {len(rows)}/{N_FINAL} rows")
    work = [(int(r["seed"]), first_targets(r)) for r in rows if first_targets(r)]
    if args.limit:
        work = work[:args.limit]
    mutants = killed_mutants()
    if not all(mutants.values()):
        raise SystemExit("killed-mutant gate failed")
    t0 = time.monotonic()
    with ProcessPoolExecutor(max_workers=args.workers, initializer=_init) as ex:
        games = list(ex.map(audit_seed, work, chunksize=1))
    errors = [{"seed": g["seed"], "errors": g["errors"]}
              for g in games if g["errors"]]
    if errors:
        raise SystemExit("replay gate failed: " + json.dumps(errors[:5]))
    records = [r for g in games for r in g["records"]]
    by_arm = {arm: [r for r in records if r["arm"] == arm]
              for arm in ("treatment", "null")}
    summary = {arm: summarize(by_arm[arm]) for arm in by_arm}
    dt, dn = (summary[a]["distinct_boards"] for a in ("treatment", "null"))
    complete = len(rows) == N_FINAL and not args.limit
    if complete:
        if len(paths) != 36:
            raise SystemExit(f"final audit requires 36 raw segments, found {len(paths)}")
        if (meta.get("n_seeds") != N_FINAL
                or meta.get("seeds") != [61000, 69999]
                or meta.get("policy_semantics") != "firmware_v8/p2_surrogate"
                or meta.get("pressure") != "exo_lulu"):
            raise SystemExit("final input META contract mismatch")
    result = {
        "version": "dspawn-null-semantic-audit-v1",
        "authority": "FINAL_9000" if complete else "PARTIAL_IMPLEMENTATION_SMOKE",
        "prereg": "PREREG_NULL_SEMANTIC_AUDIT.md",
        "n_input_pairs": len(rows), "n_games_audited": len(games),
        "complete": complete,
        "input": {"root": str(Path(args.root).resolve()),
                  "combined_sha256": input_hash,
                  "files": [p.name for p in paths],
                  "meta_path": str(meta_path.resolve()),
                  "meta_sha256": sha256(meta_path),
                  "eval_runtime_rolled": meta.get("runtime_manifest", {}).get("rolled")},
        "runtime_manifest": runtime_manifest(),
        "replay_gate": {"pass": True, "errors": [],
                        "killed_mutants": mutants},
        "arms": summary,
        "distinct_first_flip_ratio_treatment_over_null":
            dt / dn if dn else None,
        "seconds": round(time.monotonic() - t0, 2),
        "note": ("first logged action flip only; common predecessor replay; exact "
                 "color+virus+link+metadata equality"),
    }
    out = Path(args.out)
    if not complete:
        out = out.with_name("partial_" + out.name)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(result, indent=1) + "\n")
    print(json.dumps(result, indent=1))


if __name__ == "__main__":
    main()
