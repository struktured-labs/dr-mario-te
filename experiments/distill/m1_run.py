"""m1_run.py — M1 label campaign runner (REGISTRATION_M1_LABELS.md).

Stages
  smoke    2 seeds/stratum (block head), serial-ish, banked with smoke:true,
           then the launch gate battery (G-CRN, G-mutant-shuffle,
           G-pressure-live, G-activity) + cost projection vs tier.
  l20      campaign stratum L20  (seeds 17704..19098 step 2; head 2 = smoke).
  l11m     campaign stratum L11M (seeds 19104..19898 step 2; head 2 = smoke).
  analyze  registered endpoints E-M1a..d with pass/fail lines.

Wired gates (R43a/55): G-CRN recomputed every GATE_EVERY newly banked
adjudicated states IN-PROCESS; a BLOCK prints a greppable line, terminates the
pool and exits 3. Segments are per-seed atomic + resumable; META.json freezes
the runtime manifest and refuses resume under changed code.
R49: this runner prints game COUNTS while running, never endpoint numbers;
endpoints exist only in `analyze` over fully banked non-smoke segments.
"""
import argparse
import gzip
import hashlib
import importlib
import json
import os
import sys
import time

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import m1_harvest as MH  # noqa: E402  (wires h16/oracle/labels146 paths)

OUT = os.path.join(HERE, "out", "labels_m1")

BLOCK = {"L20": list(range(17700, 19100, 2)),     # 700 streams
         "L11M": list(range(19100, 19900, 2))}    # 400 streams
RESERVE = list(range(19900, 20900, 2))            # 500, untouched
# A2 (2026-08-26): smoke extended 2 -> 4 seeds/stratum after smoke #1 banked
# zero overrides in 4 games (no positive WHETHER record; R50's
# show-me-it-can-fire standard). Smoke seeds stay excluded from endpoints.
SMOKE = {s: BLOCK[s][:4] for s in BLOCK}
CAMPAIGN = {s: BLOCK[s][4:] for s in BLOCK}
assert not (set(BLOCK["L20"]) & set(BLOCK["L11M"]))
assert all(x % 2 == 0 for s in BLOCK for x in BLOCK[s])
LEVEL = {"L20": 20, "L11M": 11}
MAX_PILLS = 400
GATE_EVERY = 200
CRN_BAR = 0.18          # A4: 0.6 x known-good-bank same-form 0.300
TIER_EUR = 6.0
CPX62_EUR_H = 0.2452
CPX62_THREADS = 16

_W = {}


def _sha256(path):
    with open(path, "rb") as fh:
        return hashlib.sha256(fh.read()).hexdigest()


def runtime_manifest():
    names = ("m1_harvest", "h16_arm", "h12_arm", "oracle_arm", "labelcore",
             "pressure_rig", "bursty_model", "fast_rtl_x", "fast_sim_x",
             "root_search", "terms47", "fb", "nes_pills",
             "drmario.faithful_env", "drmario.faithful_game")
    files = {"m1_run": os.path.abspath(__file__)}
    for name in names:
        m = importlib.import_module(name)
        if getattr(m, "__file__", None):
            files[name] = os.path.abspath(m.__file__)
    per = {n: {"path": p, "sha256": _sha256(p)} for n, p in files.items()}
    rolled = hashlib.sha256("".join(
        f"{n}:{d['sha256']}" for n, d in sorted(per.items())).encode()
    ).hexdigest()
    return {"rolled": rolled, "files": per, "python": sys.version.split()[0]}


def freeze_meta(outdir, meta):
    path = os.path.join(outdir, "META.json")
    frozen = dict(meta)
    frozen["runtime_manifest"] = runtime_manifest()
    if os.path.exists(path):
        old = json.load(open(path))
        for d in (old, frozen):
            # run-scoped fields, not part of the code/settings freeze (the
            # smoke and campaign stages share an outdir but not a seed list —
            # comparing them killed both launch units, journal 23:19:23)
            for k in ("started", "workers", "seeds_lo", "seeds_hi",
                      "n_seeds", "hostname"):
                d.pop(k, None)
        if old != frozen:
            raise RuntimeError("refusing to resume under changed code")
        return
    os.makedirs(outdir, exist_ok=True)
    with open(path, "w") as fh:
        json.dump(frozen, fh, indent=1)


# ------------------------------------------------------------------ worker
def _winit(stratum):
    os.environ.update(OMP_NUM_THREADS="1", OPENBLAS_NUM_THREADS="1",
                      NUMBA_NUM_THREADS="1")
    import oracle_arm as OA
    C, bmodel = OA.init_rig("lulu", level=LEVEL[stratum])
    _W.update(C=C, bmodel=bmodel, stratum=stratum)


def _work(args):
    seed, smoke = args
    import oracle_arm as OA
    t0 = time.monotonic()
    arm = MH.M1HarvestArm(_W["stratum"], seed)
    row = OA.play_one(seed, arm, _W["C"], _W["bmodel"], max_pills=MAX_PILLS)
    rec = MH.game_record(seed, _W["stratum"], row, arm, smoke=smoke)
    rec["secs"] = round(time.monotonic() - t0, 2)
    return rec


def seg_path(stratum, seed):
    return os.path.join(OUT, stratum, f"seed_{seed:06d}.json.gz")


def bank(rec):
    p = seg_path(rec["stratum"], rec["seed"])
    os.makedirs(os.path.dirname(p), exist_ok=True)
    tmp = p + ".tmp"
    with gzip.open(tmp, "wt") as fh:
        json.dump(rec, fh)
    os.replace(tmp, p)


def load_segments(stratum, include_smoke=False):
    d = os.path.join(OUT, stratum)
    out = []
    if not os.path.isdir(d):
        return out
    for f in sorted(os.listdir(d)):
        if not f.endswith(".json.gz"):
            continue
        rec = json.load(gzip.open(os.path.join(d, f), "rt"))
        assert rec.get("schema") == MH.SCHEMA, \
            f"schema mismatch in {f}: {rec.get('schema')!r}"      # G-schema
        if rec["smoke"] and not include_smoke:
            continue
        out.append(rec)
    return out


# ------------------------------------------------------------------- G-CRN
def crn_rho(records, shuffle=False, rng=None):
    """A4 (2026-08-27) — FULL-WIDTH screen-half CRN calibration: Pearson of
    s1[0] vs s1[1] across ALL dedup'd candidates, weighted over non-degenerate
    states. REPLACES the shortlist confirm-half statistic, which was proven
    MIS-SCOPED on the known-good labels146 bank: the shortlist is pre-selected
    BY screen survival (range restriction) and the campaign population is
    saturation-heavy, so the old statistic read 0.222 on the very bank whose
    certified full-width 4v4 rho is 0.66-0.72, and ~0.1 in-campaign — it
    measured its own selection, not label quality (both strata BLOCKed on it,
    journals 00:18/00:44). Bar derived on the independent known-good bank:
    same-form (1v1 full-width) rho there = 0.300 (n=799; non-saturated 0.301)
    => CRN_BAR = 0.6 x 0.300 = 0.18. Campaign segments read 0.355 (L20) /
    0.435 (L11M) on this form — above the reference. The shuffle mutant
    permutes fork-1 values independently across candidates."""
    num = den = used = 0.0
    for rec in records:
        for adj in rec["adjudications"]:
            if adj["degenerate"]:
                continue
            cands = adj["cands"]
            if len(cands) < 3:
                continue
            a = np.array([c["s1"][0] for c in cands], float)
            b = np.array([c["s1"][1] for c in cands], float)
            if shuffle:
                idx = np.array(rng.sample(range(len(b)), len(b)))
                b = b[idx]
            if a.std() == 0 or b.std() == 0:
                continue
            r = float(np.corrcoef(a, b)[0, 1])
            w = len(cands) - 2
            num += r * w
            den += w
            used += 1
    return (num / den if den else float("nan")), int(used)


def gate_crn(records, tag):
    rho, n = crn_rho(records)
    verdict = "OK" if (n < 10 or (rho == rho and rho >= CRN_BAR)) else "BLOCK"
    if rho == rho and rho > 0.8 and n >= 10:
        verdict = "INVESTIGATE-HIGH"      # R53: implausibly good for 1-fork halves
    print(f"[m1-gate] G-CRN {tag} states={n} rho={rho:.3f} bar={CRN_BAR} "
          f"verdict={verdict}", flush=True)
    return verdict == "OK"


# ------------------------------------------------------------------ stages
def status(line):
    with open(os.path.join(HERE, "out", "STATUS"), "w") as fh:
        fh.write(line + "\n")
    print(line, flush=True)


def run_stratum(stratum, workers, seeds, smoke=False):
    import multiprocessing as mp
    outdir = os.path.join(OUT, stratum)
    freeze_meta(outdir, {"stratum": stratum, "level": LEVEL[stratum],
                         "max_pills": MAX_PILLS, "schema": MH.SCHEMA,
                         "trigger": ("dsh>=13" if stratum == "L20"
                                     else "wide12=max(H2..H5)>=12"),
                         "cap": MH.CAP, "seeds_lo": seeds[0],
                         "seeds_hi": seeds[-1], "n_seeds": len(seeds),
                         "hostname": os.uname().nodename})
    todo = [(s, smoke) for s in seeds if not os.path.exists(
        seg_path(stratum, s))]
    status(f"STATUS: RUNNING {os.getpid()} {outdir} todo={len(todo)}"
           f"/{len(seeds)}")
    if not todo:
        print(f"[m1] {stratum}: all {len(seeds)} banked")
        return True
    banked_states = 0
    next_gate = GATE_EVERY
    done = 0
    t0 = time.monotonic()
    with mp.Pool(workers, initializer=_winit, initargs=(stratum,)) as pool:
        for rec in pool.imap_unordered(_work, todo):
            bank(rec)
            done += 1
            banked_states += len(rec["adjudications"])
            if done % 10 == 0 or done == len(todo):
                rate = done / max(time.monotonic() - t0, 1)
                print(f"[m1] {stratum} games={done}/{len(todo)} "
                      f"states={banked_states} "
                      f"eta={((len(todo)-done)/max(rate,1e-9))/3600:.1f}h",
                      flush=True)
            if banked_states >= next_gate:
                next_gate += GATE_EVERY
                if not gate_crn(load_segments(stratum, include_smoke=True),
                                f"{stratum}@n{banked_states}"):
                    pool.terminate()
                    status(f"STATUS: BLOCKED G-CRN {stratum}")
                    sys.exit(3)
    status(f"STATUS: DONE {outdir} games={len(seeds)}")
    return True


def stage_smoke(workers):
    for stratum in ("L20", "L11M"):
        run_stratum(stratum, min(workers, 2), SMOKE[stratum], smoke=True)
    ok = True
    recs = {s: [r for r in load_segments(s, include_smoke=True) if r["smoke"]]
            for s in ("L20", "L11M")}
    # G-activity
    adj = {s: sum(len(r["adjudications"]) for r in recs[s]) for s in recs}
    ovr = sum(a["whether"] for s in recs for r in recs[s]
              for a in r["adjudications"])
    act_ok = all(adj[s] > 0 for s in adj)
    print(f"[m1-gate] G-activity adj={adj} overrides={ovr} "
          f"verdict={'OK' if act_ok else 'FAIL'}"
          + ("" if ovr > 0 else "  (WARN: 0 overrides in smoke — extend"
             " smoke before campaign; a WHETHER bank needs positives)"),
          flush=True)
    ok &= act_ok
    # G-CRN + shuffle mutant
    allrecs = recs["L20"] + recs["L11M"]
    ok &= gate_crn(allrecs, "smoke")
    import random as _r
    # R38a: a shuffled control is itself a random variable — 20 draws, not 1
    draws = [crn_rho(allrecs, shuffle=True, rng=_r.Random(1000 + i))
             for i in range(20)]
    n_s = draws[0][1]
    rhos = [d[0] for d in draws if d[0] == d[0]]
    mean_rho = float(np.mean(rhos)) if rhos else float("nan")
    sd_rho = float(np.std(rhos)) if rhos else float("nan")
    mut_ok = (n_s < 10) or (abs(mean_rho) < 0.2)
    print(f"[m1-gate] G-mutant-shuffle states={n_s} null-rho "
          f"mean={mean_rho:.3f} sd={sd_rho:.3f} (20 draws) "
          f"verdict={'OK' if mut_ok else 'FAIL'}", flush=True)
    ok &= mut_ok
    # G-pressure-live (gate_h16 S3 pattern: count injections for one seed)
    import oracle_arm as OA
    import bursty_model as BM
    real = BM.inject_bursty_garbage
    for stratum in ("L20", "L11M"):
        n = {"n": 0}

        def counting(board, model, s, pills, cs, rng=None, _n=n):
            _n["n"] += 1
            return real(board, model, s, pills, cs, rng=rng)
        BM.inject_bursty_garbage = counting
        try:
            C, bmodel = OA.init_rig("lulu", level=LEVEL[stratum])
            arm = MH.M1HarvestArm(stratum, SMOKE[stratum][0])
            OA.play_one(SMOKE[stratum][0], arm, C, bmodel, max_pills=60)
        finally:
            BM.inject_bursty_garbage = real
        pl_ok = n["n"] > 0
        print(f"[m1-gate] G-pressure-live {stratum} injections={n['n']} "
              f"verdict={'OK' if pl_ok else 'FAIL'}", flush=True)
        ok &= pl_ok
    # cost projection vs tier (R45: an over-tier projection STOPs for a
    # conversation; it never silently shrinks N)
    forks = sum(r["counters"]["tribunal_forks"] for r in allrecs)
    secs = sum(r["secs"] for r in allrecs)
    spf = secs / max(forks, 1)
    fpg = forks / max(len(allrecs), 1)
    n_campaign = sum(len(CAMPAIGN[s]) for s in CAMPAIGN)
    core_h = fpg * n_campaign * spf / 3600
    eur = core_h / CPX62_THREADS * CPX62_EUR_H
    tier_ok = eur <= TIER_EUR
    print(f"[m1-gate] G-cost forks/game={fpg:.0f} s/fork={spf:.2f} "
          f"projected core-h={core_h:.0f} cpx62-eur={eur:.2f} "
          f"tier={TIER_EUR} verdict={'OK' if tier_ok else 'STOP-OVER-TIER'}",
          flush=True)
    ok &= tier_ok
    print(f"[m1-smoke] verdict={'PASS' if ok else 'FAIL'}", flush=True)
    return 0 if ok else 3


# ----------------------------------------------------------------- analyze
def wilson(k, n, z=1.96):
    if n == 0:
        return (0.0, 1.0)
    p = k / n
    d = 1 + z * z / n
    c = p + z * z / (2 * n)
    h = z * ((p * (1 - p) / n + z * z / (4 * n * n)) ** 0.5)
    return ((c - h) / d, (c + h) / d)


def fire_wide12(H):
    return max(H[2:6]) >= 12


def fire_dsh13(H):
    return max(H[3], H[4]) >= 13


def stage_analyze():
    print(f"[m1-analyze] non-smoke banked: "
          f"L20={len(load_segments('L20'))}/{len(CAMPAIGN['L20'])} "
          f"L11M={len(load_segments('L11M'))}/{len(CAMPAIGN['L11M'])} "
          f"(count files, not prefixes)", flush=True)
    l11 = load_segments("L11M")
    # E-M1a: topout-game catch with >=5 plies lead
    topo = [r for r in l11 if r["game"]["res"] == "topout"]
    caught = sum(
        any(fire_wide12(H) for H in r["heights_trace"][:-5])
        for r in topo)
    caught_dsh = sum(
        any(fire_dsh13(H) for H in r["heights_trace"][:-5])
        for r in topo)
    frac = caught / max(len(topo), 1)
    lo, hi = wilson(caught, max(len(topo), 1))
    print(f"[m1-analyze] E-M1a wide12 topout-catch(lead>=5ply) "
          f"{caught}/{len(topo)} = {frac:.3f} CI[{lo:.3f},{hi:.3f}] "
          f"bar 0.70 {'PASS' if frac >= 0.70 else 'FAIL'} "
          f"(dsh13 comparator {caught_dsh}/{len(topo)})", flush=True)
    # E-M1b: false-fire on cleared-game plies
    clear_plies = [fire_wide12(H) for r in l11 if r["game"]["res"] == "clear"
                   for H in r["heights_trace"]]
    rate = (sum(clear_plies) / len(clear_plies)) if clear_plies else float("nan")
    verdict = ("PASS" if rate <= 0.15 else "FAIL")
    if rate < 0.01:
        verdict = "INVESTIGATE-LOW (defect signal per R53, not an auto-pass)"
    print(f"[m1-analyze] E-M1b wide12 cleared-ply fire "
          f"{sum(clear_plies)}/{len(clear_plies)} = {rate:.4f} "
          f"ceiling 0.15 {verdict}", flush=True)
    # E-M1c secondaries
    leads = []
    for r in topo:
        f = [i for i, H in enumerate(r["heights_trace"]) if fire_wide12(H)]
        if f:
            leads.append(len(r["heights_trace"]) - 1 - f[0])
    if leads:
        q = np.percentile(leads, [10, 50, 90])
        print(f"[m1-analyze] E-M1c lead-at-first-fire plies "
              f"p10/p50/p90={q[0]:.0f}/{q[1]:.0f}/{q[2]:.0f} "
              f"(~{q[1]*2.5:.0f}s at ~2.5 s/ply, approx)", flush=True)
    rand_danger = fired = 0
    for r in l11:
        for a in r["adjudications"]:
            if "random" in a["classes"] and a["champ_s2"] <= 3:
                rand_danger += 1
                if any(fire_wide12(H)
                       for H in r["heights_trace"][:a["ply"] + 1]):
                    fired += 1
    lo, hi = wilson(fired, max(rand_danger, 1))
    print(f"[m1-analyze] E-M1c random-quota danger recall "
          f"{fired}/{rand_danger} CI[{lo:.3f},{hi:.3f}] "
          f"(recorded; quoted only with its CI per R49)", flush=True)
    # E-M1d yields + L20 analog
    for stratum in ("L20", "L11M"):
        recs = load_segments(stratum)
        cnt = {}
        for r in recs:
            for k, v in r["counters"].items():
                cnt[k] = cnt.get(k, 0) + v
        states = sum(len(r["adjudications"]) for r in recs)
        danger = sum(a["champ_s2"] <= 3 for r in recs
                     for a in r["adjudications"])
        whether = sum(a["whether"] for r in recs for a in r["adjudications"])
        print(f"[m1-analyze] E-M1d {stratum} games={len(recs)} "
              f"states={states} danger={danger} overrides={whether} "
              f"counters={cnt}", flush=True)
    return 0


# -------------------------------------------------- A5 danger back-fill
BF_WINDOW = 30
BF_OUT = os.path.join(OUT, "L11M_backfill")


def _bf_work(item):
    seed, window_start, banked_trace = item
    import oracle_arm as OA
    t0 = time.monotonic()
    arm = MH.M1HarvestArm("L11M", seed, mode="backfill",
                          window_start=window_start)
    row = OA.play_one(seed, arm, _W["C"], _W["bmodel"], max_pills=MAX_PILLS)
    if arm.trace != banked_trace:
        return {"seed": seed, "replay_gate": "FAIL",
                "n_replay": len(arm.trace), "n_banked": len(banked_trace)}
    rec = MH.game_record(seed, "L11M", row, arm, smoke=False)
    rec["backfill"] = True
    rec["window_start"] = window_start
    rec["replay_gate"] = "PASS"
    rec["secs"] = round(time.monotonic() - t0, 2)
    return rec


def stage_backfill(workers):
    """A5 (approved 2026-08-28): adjudicate ALL trigger plies in the final
    BF_WINDOW plies of every banked L11M topout game. No thinning/cap.
    REPLAY GATE per game: the replayed height trace must equal the banked
    trace exactly, else nothing banks and the game is reported FAILED —
    champion-const determinism is asserted, not assumed. Segments land in a
    SEPARATE dir; the density rider travels in META."""
    import multiprocessing as mp
    base = load_segments("L11M")
    topo = [(r["seed"], max(0, r["game"]["n_plies"] - BF_WINDOW),
             r["heights_trace"])
            for r in base if r["game"]["res"] == "topout"]
    os.makedirs(BF_OUT, exist_ok=True)
    meta = {"stage": "A5_backfill", "window": BF_WINDOW, "schema": MH.SCHEMA,
            "density_rider": ("death-window oversampled BY DESIGN vs the "
                              "base bank; consumers stratify/weight, never "
                              "pool silently"),
            "n_games": len(topo), "hostname": os.uname().nodename}
    mpth = os.path.join(BF_OUT, "META.json")
    if not os.path.exists(mpth):
        json.dump(meta | {"runtime_manifest": runtime_manifest()},
                  open(mpth, "w"), indent=1)
    todo = [t for t in topo if not os.path.exists(
        os.path.join(BF_OUT, f"seed_{t[0]:06d}.json.gz"))]
    status(f"STATUS: RUNNING {os.getpid()} {BF_OUT} todo={len(todo)}"
           f"/{len(topo)}")
    fails = 0
    done = 0
    with mp.Pool(workers, initializer=_winit, initargs=("L11M",)) as pool:
        for rec in pool.imap_unordered(_bf_work, todo):
            done += 1
            if rec.get("replay_gate") != "PASS":
                fails += 1
                print(f"[m1-backfill] REPLAY GATE FAIL seed={rec['seed']} "
                      f"replay={rec.get('n_replay')} "
                      f"banked={rec.get('n_banked')} — NOT banked",
                      flush=True)
                continue
            p = os.path.join(BF_OUT, f"seed_{rec['seed']:06d}.json.gz")
            tmp = p + ".tmp"
            with gzip.open(tmp, "wt") as fh:
                json.dump(rec, fh)
            os.replace(tmp, p)
            if done % 10 == 0 or done == len(todo):
                print(f"[m1-backfill] {done}/{len(todo)} replay-fails={fails}",
                      flush=True)
    status(f"STATUS: DONE {BF_OUT} games={len(topo)-fails} fails={fails}")
    return 0 if fails == 0 else 3


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("stage", choices=("smoke", "l20", "l11m", "analyze",
                                      "backfill"))
    ap.add_argument("--workers", type=int, default=8)
    a = ap.parse_args()
    if a.stage == "smoke":
        sys.exit(stage_smoke(a.workers))
    if a.stage == "analyze":
        sys.exit(stage_analyze())
    if a.stage == "backfill":
        sys.exit(stage_backfill(a.workers))
    stratum = {"l20": "L20", "l11m": "L11M"}[a.stage]
    run_stratum(stratum, a.workers, CAMPAIGN[stratum])


if __name__ == "__main__":
    main()
