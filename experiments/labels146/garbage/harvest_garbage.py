"""harvest_garbage.py — the garbage-board label harvest (PREREG_GARBAGE §1/§4).

Work items:
  strata A/B — one save-state each (import gates -> label_import_state);
  stratum C  — one banked SEED each (one gated replay labels its k-targets).

Per-item atomic gzip segments under out/labels/; already-present segments are
SKIPPED (resumable, movable across boxes mid-campaign).  Voids are RECORDED
(out/voids.jsonl), never silently dropped.  Close-out prints the ledger audit:
labeled+voided vs registered targets, per stratum (clean exit != completion).

  python3 harvest_garbage.py --set pilot   --workers 8
  python3 harvest_garbage.py --set campaign --workers 8
"""
import argparse
import gzip
import json
import os
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import garbcore as G
import labelcore as LC

OUT = os.path.join(HERE, "out")
LABELS = os.path.join(OUT, "labels")
C_GAMES_CAMPAIGN = 25
C_KS = (30, 40, 50)


# ------------------------------------------------------------------ targets
def targets_AB(which):
    A = sorted(G.load_sources_A(), key=lambda s: (s["row"], -s["pre_idx"]))
    B = sorted(G.load_sources_B(), key=lambda s: (s["seed"], s["row"],
                                                  s.get("bracket", ""),
                                                  -s["pre_idx"]))
    if which == "pilot":
        return A[:12], B[:12]
    return A, B


def targets_C(which):
    """[(seed, [(k, ply), ...]), ...] — first topout games, n_plies >= 60."""
    games = LC.bank_games()
    tops = [g for g in games if g["res"] == "topout" and g["n_plies"] >= 60]
    n_games = 4 if which == "pilot" else C_GAMES_CAMPAIGN
    out = []
    for g in tops[:n_games]:
        ks = [(k, g["n_plies"] - k) for k in C_KS]
        out.append((g["seed"], ks))
    if which == "pilot":
        flat = [(s, k) for s, ks in out for k, _ in ks]
        assert len(flat) == 12, len(flat)
    return out


# ------------------------------------------------------------------ workers
def _write_row(path_stem, row):
    tmp = os.path.join(LABELS, f".{path_stem}.tmp")
    dst = os.path.join(LABELS, f"{path_stem}.jsonl.gz")
    with gzip.open(tmp, "wt") as fh:
        fh.write(json.dumps(row) + "\n")
    os.replace(tmp, dst)


def work_import(src):
    """One stratum A/B save-state -> one label row (or a recorded void)."""
    sid = G.state_id(src)
    t0 = time.time()
    C, bmodel = LC.init_rig()
    try:
        st = G.read_state(src["path"])
        c, v, l = G.decode_planes(st["nes"])
        skey = G.source_key(src["stratum"], src["seed"], src["pre_idx"])
        env = G.build_env(c, v, l, st["cur"], st["nxt"], skey & 0xFFFF)
    except G.ImportVoid as ex:
        return {"id": sid, "void": ex.cls, "detail": repr(ex.detail),
                "stratum": src["stratum"], "cpu_s": round(time.time() - t0, 1)}
    vals, a = G.champ_pick(env, C)
    ents = G.label_import_state(env, C, bmodel, skey)
    row = {"id": sid, "stratum": src["stratum"], "source": src,
           "H": G.H, "N": G.N_SAMPLES, "level": G.LEVEL,
           "pills_placed": G.PILLS_PLACED_INIT, "fseed_base": skey,
           "v2": st["v2"], "cur": st["cur"], "nxt": st["nxt"],
           "nes": st["nes"], "champ_slot": a,
           "champ_vals": [LC._round3(vv) for vv in vals],
           "cands": ents}
    _write_row(sid, row)
    forks = sum(len(e["surv"]) for e in ents)
    return {"id": sid, "stratum": src["stratum"], "cands": len(ents),
            "forks": forks, "cpu_s": round(time.time() - t0, 1)}


def work_seed_C(seed, ks, stratum="C"):
    """One banked seed: gated replay + labels at each (k, ply)."""
    t0 = time.time()
    C, bmodel = LC.init_rig()
    rows, game = LC.load_bank_game(seed)
    want = {ply: k for k, ply in ks}
    got, forks = 0, 0
    gen = LC.replay_game(seed, C, bmodel, rows)
    try:
        while True:
            ply, env, vals, row = next(gen)
            k = want.get(ply)
            if k is None:
                continue
            ents = LC.label_state(env, C, bmodel, seed, ply, G.N_SAMPLES, G.H)
            forks += sum(len(e["surv"]) for e in ents)
            out = {"id": f"C_{seed}_k{k}", "stratum": stratum, "seed": seed,
                   "ply": ply, "k": k, "H": G.H, "N": G.N_SAMPLES,
                   "vir": row["vir"], "dsh": row["dsh"], "maxh": row["maxh"],
                   "a": row["a"], "vals": row["vals"], "champ_slot": row["a"],
                   "game_res": game["res"], "game_n_plies": game["n_plies"],
                   "cands": ents}
            _write_row(out["id"], out)
            got += 1
    except StopIteration as stop:
        res = stop.value
    assert res == game["res"], (seed, res, game["res"])
    assert got == len(ks), (seed, got, len(ks))
    return {"id": f"C_{seed}", "stratum": stratum, "rows": got, "forks": forks,
            "cpu_s": round(time.time() - t0, 1)}


CDEEP_KS = (8, 12, 16, 20)      # C-DEEP REGISTRATION
CDEEP_GAMES = 150               # per box, first-N in list order


def targets_cdeep(box, n_games=CDEEP_GAMES):
    """[(seed, [(k, ply)...])...] from this box's committed split list."""
    path = os.path.join(HERE, f"cdeep_split_{box}.txt")
    seeds = [int(x) for x in open(path).read().split()][:n_games]
    out = []
    for seed in seeds:
        _, game = LC.load_bank_game(seed)
        assert game["res"] == "topout" and game["n_plies"] >= 40, seed
        out.append((seed, [(k, game["n_plies"] - k) for k in CDEEP_KS]))
    return out


def main_cdeep(box, workers):
    os.makedirs(LABELS, exist_ok=True)
    ts = targets_cdeep(box)
    items = [(seed, ks) for seed, ks in ts
             if not all(os.path.exists(os.path.join(
                 LABELS, f"C_{seed}_k{k}.jsonl.gz")) for k, _ in ks)]
    reg = sum(len(ks) for _, ks in ts)
    print(f"[harvest:cdeep-{box}] games={len(ts)} states={reg} "
          f"todo={len(items)} workers={workers}", flush=True)
    from concurrent.futures import ProcessPoolExecutor, as_completed
    t0, aborts = time.time(), 0
    with ProcessPoolExecutor(max_workers=workers) as ex:
        futs = {ex.submit(work_seed_C, s, ks, "Cdeep"): s for s, ks in items}
        for i, f in enumerate(as_completed(futs), 1):
            try:
                r = f.result()
            except LC.ReplayMismatch as ex_:
                aborts += 1
                print(f"[harvest] {i}/{len(items)} seed={futs[f]} "
                      f"REPLAY_ABORT {ex_}", flush=True)
                continue
            print(f"[harvest] {i}/{len(items)} {r['id']} rows={r['rows']} "
                  f"forks={r['forks']} cpu_s={r['cpu_s']} "
                  f"wall={time.time()-t0:.0f}s", flush=True)
    have = sum(os.path.exists(os.path.join(LABELS, f"C_{s}_k{k}.jsonl.gz"))
               for s, ks in ts for k, _ in ks)
    print(f"[ledger] Cdeep-{box}: labeled {have}/{reg} "
          f"replay_aborts={aborts}/{len(ts)}", flush=True)
    if aborts > 0.10 * len(ts):
        print("HARVEST_STOP_RULE15 — replay-abort rate over threshold",
              flush=True)
    elif have == reg:
        print("HARVEST_OK", flush=True)
    else:
        print("HARVEST_INCOMPLETE", flush=True)


def _worker(item):
    kind, payload = item
    if kind == "import":
        return work_import(payload)
    return work_seed_C(*payload)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--set", dest="which",
                    choices=("pilot", "campaign", "d",
                             "cdeep-blackmage", "cdeep-redmage"),
                    required=True)
    ap.add_argument("--workers", type=int, default=8)
    args = ap.parse_args()

    if args.which == "d":
        return main_d(args.workers)
    if args.which.startswith("cdeep-"):
        return main_cdeep(args.which.split("-", 1)[1], args.workers)

    os.makedirs(LABELS, exist_ok=True)
    A, B = targets_AB(args.which)
    Cts = targets_C(args.which)

    items, skipped = [], 0
    for src in A + B:
        if os.path.exists(os.path.join(LABELS, G.state_id(src) + ".jsonl.gz")):
            skipped += 1
            continue
        items.append(("import", src))
    for seed, ks in Cts:
        if all(os.path.exists(os.path.join(LABELS, f"C_{seed}_k{k}.jsonl.gz"))
               for k, _ in ks):
            skipped += 1
            continue
        items.append(("C", (seed, ks)))

    reg = {"A": len(A), "B": len(B),
           "C": sum(len(ks) for _, ks in Cts)}
    print(f"[harvest:{args.which}] registered A={reg['A']} B={reg['B']} "
          f"C={reg['C']} | todo={len(items)} skipped={skipped} "
          f"workers={args.workers}", flush=True)

    from concurrent.futures import ProcessPoolExecutor, as_completed
    t0, results = time.time(), []
    with ProcessPoolExecutor(max_workers=args.workers) as ex:
        futs = [ex.submit(_worker, it) for it in items]
        for i, f in enumerate(as_completed(futs), 1):
            r = f.result()
            results.append(r)
            tag = (f"VOID:{r['void']}" if "void" in r else
                   f"cands={r.get('cands', r.get('rows'))} "
                   f"forks={r.get('forks')}")
            print(f"[harvest] {i}/{len(items)} {r['id']} {tag} "
                  f"cpu_s={r['cpu_s']} wall={time.time()-t0:.0f}s", flush=True)

    voids = [r for r in results if "void" in r]
    with open(os.path.join(OUT, "voids.jsonl"), "a") as fh:
        for r in voids:
            fh.write(json.dumps(r) + "\n")

    # ---------------- close-out ledger audit (registered vs on disk) -------
    have = {"A": 0, "B": 0, "C": 0}
    for src in A + B:
        if os.path.exists(os.path.join(LABELS, G.state_id(src) + ".jsonl.gz")):
            have[src["stratum"]] += 1
    for seed, ks in Cts:
        have["C"] += sum(os.path.exists(
            os.path.join(LABELS, f"C_{seed}_k{k}.jsonl.gz")) for k, _ in ks)
    all_voids = {}
    vpath = os.path.join(OUT, "voids.jsonl")
    if os.path.exists(vpath):
        for ln in open(vpath):
            r = json.loads(ln)
            all_voids[r["id"]] = r
    nvoid = {"A": sum(r["stratum"] == "A" for r in all_voids.values()),
             "B": sum(r["stratum"] == "B" for r in all_voids.values())}
    total_forks = sum(r.get("forks", 0) for r in results)
    total_cpu = sum(r["cpu_s"] for r in results)
    print("[ledger] stratum A: labeled "
          f"{have['A']}/{reg['A']} ({nvoid['A']} void all-time)", flush=True)
    print(f"[ledger] stratum B: labeled {have['B']}/{reg['B']} "
          f"({nvoid['B']} void all-time)", flush=True)
    print(f"[ledger] stratum C: labeled {have['C']}/{reg['C']}", flush=True)
    if total_forks:
        print(f"[ledger] forks={total_forks} cpu_s/fork="
              f"{total_cpu/total_forks:.3f} (prior 0.718)", flush=True)
    complete = all(have[s] + nvoid[s] >= reg[s] for s in "AB") \
        and have["C"] == reg["C"]
    print("HARVEST_OK" if complete else
          "HARVEST_INCOMPLETE — voids or missing segments; see ledger",
          flush=True)




# ------------------------------------------------------- stratum D (A3)
def work_import_d(path, rec):
    sid = G.d_state_id(rec)
    t0 = time.time()
    C, bmodel = LC.init_rig()
    try:
        st = G.read_d_row(rec)
        c, v, l = G.decode_planes(st["nes"])
        skey = G.d_source_key(rec)
        env = G.build_env(c, v, l, st["cur"], st["nxt"], skey & 0xFFFF)
    except G.ImportVoid as ex:
        return {"id": sid, "void": ex.cls, "detail": repr(ex.detail),
                "stratum": "D", "cpu_s": round(time.time() - t0, 1)}
    vals, a = G.champ_pick(env, C)
    ents = G.label_import_state(env, C, bmodel, skey)
    row = {"id": sid, "stratum": "D",
           "source": {"file": os.path.basename(path),
                      "game": rec["game"], "decision_idx": rec["decision_idx"],
                      "ts_video": rec.get("ts_video")},
           "H": G.H, "N": G.N_SAMPLES, "level": G.LEVEL,
           "pills_placed": G.PILLS_PLACED_INIT, "fseed_base": skey,
           "v2": st["v2"], "cur": st["cur"], "nxt": st["nxt"],
           "nes": st["nes"], "champ_slot": a,
           "played_slot": st["played_slot"],
           "champ_vals": [LC._round3(vv) for vv in vals],
           "cands": ents}
    _write_row(sid, row)
    forks = sum(len(e["surv"]) for e in ents)
    return {"id": sid, "stratum": "D", "cands": len(ents), "forks": forks,
            "cpu_s": round(time.time() - t0, 1)}


def main_d(workers):
    os.makedirs(LABELS, exist_ok=True)
    srcs = G.load_sources_D()
    items = [(p, r) for p, r in srcs
             if not os.path.exists(os.path.join(
                 LABELS, G.d_state_id(r) + ".jsonl.gz"))]
    print(f"[harvest:d] rows={len(srcs)} todo={len(items)} workers={workers}",
          flush=True)
    from concurrent.futures import ProcessPoolExecutor, as_completed
    t0, results = time.time(), []
    with ProcessPoolExecutor(max_workers=workers) as ex:
        futs = [ex.submit(work_import_d, p, r) for p, r in items]
        for i, f in enumerate(as_completed(futs), 1):
            r = f.result()
            results.append(r)
            tag = (f"VOID:{r['void']}" if "void" in r else
                   f"cands={r['cands']} forks={r['forks']}")
            print(f"[harvest] {i}/{len(items)} {r['id']} {tag} "
                  f"cpu_s={r['cpu_s']} wall={time.time()-t0:.0f}s", flush=True)
    voids = [r for r in results if "void" in r]
    with open(os.path.join(OUT, "voids.jsonl"), "a") as fh:
        for r in voids:
            fh.write(json.dumps(r) + "\n")
    have = sum(os.path.exists(os.path.join(LABELS,
               G.d_state_id(r) + ".jsonl.gz")) for _, r in srcs)
    print(f"[ledger] stratum D: labeled {have}/{len(srcs)} "
          f"({len(voids)} void this run)", flush=True)
    print("HARVEST_OK" if have + len(voids) >= len(srcs)
          else "HARVEST_INCOMPLETE", flush=True)


if __name__ == "__main__":
    main()
