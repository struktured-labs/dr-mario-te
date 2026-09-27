"""run_h16.py — H16 registered evaluation runner (REGISTRATION_H16.md sec 6).

Stages
  e1      PRIMARY true arm: 600 L20 honest-lulu pairs, A=H12Arm certified,
          B=H16Arm registered config.  RUNNER-LEVEL futility at n=200/400 on
          ascending-seed prefixes (in-process; STOP halts this run AND stops
          the guard unit drm-h16-guard).
  e2      dose-matched null: B=H16Arm with h16_label_mode='shuffle'
          (+ --null-keep-num/den auto-thin), same seeds as e1.
  guard   1,000 clean L11 pairs (no in-game injection), same arms.
  analyze registered readout: primary McNemar+CI (never before n=600),
          guard trip rule, mutant dose anchor on realized override RATES.

Seeds (sec 6.2): primary = first 600 eligible ascending from 53701 within
53100-59999 minus SILEVAL_EXCL; guard = the next 1,000 eligible.
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

import numpy as np

import h16_arm  # noqa: E402  (also wires oracle + labels146 sys.path)

BLOCK_LO, BLOCK_HI = 53100, 59999
H14_CONSUMED_MAX = 53700          # on-disk audit, REGISTRATION sec 6.2
SILEVAL_EXCL = {53239, 54149, 54311, 54593, 55511, 55789, 56331, 56561,
                56585, 57129, 57245, 57431, 57773, 58007, 58253, 58403,
                58427, 58957, 59115, 59937}


def eligible_seeds():
    out = []
    for s in range(H14_CONSUMED_MAX + 1, BLOCK_HI + 1):
        if s not in SILEVAL_EXCL:
            out.append(s)
    return out


ELIG = eligible_seeds()
PRIMARY_SEEDS = ELIG[:600]
GUARD_SEEDS = ELIG[600:1600]
FUTILITY_NS = (200, 400)
FUTILITY_BOUND = -0.01
OUT = os.path.join(HERE, "out")
MAX_FLIPLOG = 400

_W = {}


# ---------------------------------------------------------------- manifest
def _sha256(path):
    with open(path, "rb") as fh:
        return hashlib.sha256(fh.read()).hexdigest()


def runtime_manifest():
    names = ("h16_arm", "h12_arm", "oracle_arm", "labelcore", "pressure_rig",
             "p0_ab", "bursty_model", "fast_rtl_x", "fast_sim_x",
             "root_search", "terms47", "fb", "nes_pills",
             "drmario.faithful_env", "drmario.faithful_game")
    files = {"run_h16": os.path.abspath(__file__)}
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
            d.pop("started", None)
            d.pop("workers", None)
        if old != frozen:
            raise RuntimeError("refusing to resume under changed code/settings")
        return
    os.makedirs(outdir, exist_ok=True)
    with open(path, "w") as fh:
        json.dump(frozen, fh, indent=1)


# ------------------------------------------------------------------ arms
def make_base():
    from h12_arm import H12Arm
    return H12Arm(label_mode="true", topk=4, horizon=15, fork_samples=5,
                  tie_margin=0.5, future_mode="dist", provenance=True)


def make_trt(label_mode="true", null_num=1, null_den=1):
    return h16_arm.H16Arm(h16_label_mode=label_mode,
                          h16_null_keep_num=null_num,
                          h16_null_keep_den=null_den,
                          topk=4, horizon=15, fork_samples=5, tie_margin=0.5,
                          future_mode="dist", provenance=True)


def _row(r, arm):
    r.pop("_actions", None)
    for k in ("h16_trigger_plies", "h16_adjudications", "h16_overrides",
              "h16_null_rejected", "h16_screen_forks", "h16_confirm_forks",
              "h16_cand_width"):
        r[k] = arm.stats.get(k, 0)
    r["flip_log"] = arm.flip_log[:MAX_FLIPLOG]
    return r


def _winit(stage, null_num, null_den):
    import oracle_arm as OA
    if stage in ("e1", "e2"):
        C, bmodel = OA.init_rig("lulu", level=20)
        _W.update(C=C, bmodel=bmodel, level=20, max_pills=400)
    else:
        C, bmodel = OA.init_rig("lulu", level=11)
        _W.update(C=C, bmodel=bmodel, level=11, max_pills=300)
    _W.update(stage=stage, null_num=null_num, null_den=null_den)


def play_clean_l11(seed, arm, C, bmodel, max_pills=300):
    """Clean guard game: arm decides, NO in-game injection (sec 6.4)."""
    import oracle_arm as OA
    env = OA.make_env(seed, 11, max_pills=max_pills)
    res = "stall"
    n = 0
    for ply in range(max_pills):
        if env.board.virus_count() == 0:
            res = "clear"
            break
        a, _b = arm.choose(env, seed, C, bmodel, C["w"], C["fl"],
                           C["wt"], C["ws"], ply)
        if a is None:
            res = "topout"
            break
        n += 1
        _obs, _r, term, trunc, info = env.step(int(a))
        if term:
            res = "clear" if info["won"] else "topout"
            break
        if trunc:
            res = "stall"
            break
    return {"seed": seed, "res": res, "won": int(res == "clear"),
            "topout": int(res == "topout"), "stall": int(res == "stall"),
            "pills": int(env.pills_placed), "n_plies": n,
            "flips": arm.stats["flips"], "forks": arm.stats["forks"]}


def _work(seed):
    import oracle_arm as OA
    t0 = time.monotonic()
    stage = _W["stage"]
    ab = make_base()
    at = make_trt("true" if stage != "e2" else "shuffle",
                  _W["null_num"], _W["null_den"])
    if stage == "guard":
        rb = play_clean_l11(seed, ab, _W["C"], _W["bmodel"],
                            _W["max_pills"])
        rt = play_clean_l11(seed, at, _W["C"], _W["bmodel"],
                            _W["max_pills"])
    else:
        rb = OA.play_one(seed, ab, _W["C"], _W["bmodel"],
                         max_pills=_W["max_pills"])
        rt = OA.play_one(seed, at, _W["C"], _W["bmodel"],
                         max_pills=_W["max_pills"])
    rb, rt = _row(rb, ab), _row(rt, at)
    rb["arm"], rt["arm"] = "base", "trt"
    return {"seed": seed, "base": rb, "trt": rt,
            "secs": round(time.monotonic() - t0, 2)}


# -------------------------------------------------------------- run stage
def seg_path(outdir, seed):
    return os.path.join(outdir, f"pair_{seed:06d}.json")


def fail_of(r):
    return int(r["won"] == 0)


def score_pairs(pairs):
    n = len(pairs)
    fa = np.array([fail_of(p["base"]) for p in pairs])
    fb = np.array([fail_of(p["trt"]) for p in pairs])
    d = float(fb.mean() - fa.mean()) if n else 0.0
    b01 = int(((~fa.astype(bool)) & fb.astype(bool)).sum())   # trt-only fail
    b10 = int((fa.astype(bool) & (~fb.astype(bool))).sum())   # trt rescues
    diffs = fb.astype(int) - fa.astype(int)
    rng = np.random.default_rng(16)
    boots = (np.array([diffs[rng.integers(0, n, n)].mean()
                       for _ in range(10000)]) if n else np.array([0.0]))
    lo, hi = np.percentile(boots, [2.5, 97.5])
    from scipy.stats import binomtest
    p = (binomtest(b10, b01 + b10, 0.5, alternative="greater").pvalue
         if (b01 + b10) else 1.0)
    return {"n": n, "d": d, "ci": (float(lo), float(hi)),
            "good": b10, "bad": b01, "mcnemar_p_onesided": float(p),
            "failA": float(fa.mean()) if n else 0.0,
            "failB": float(fb.mean()) if n else 0.0}


def _prefix_pairs(outdir, seeds, n):
    out = []
    for s in seeds:
        p = seg_path(outdir, s)
        if not os.path.exists(p):
            break                     # ascending-seed PREFIX only
        out.append(json.load(open(p)))
        if len(out) == n:
            break
    return out


def run_stage(stage, workers, null_num, null_den):
    outdir = os.path.join(OUT, stage)
    seeds = GUARD_SEEDS if stage == "guard" else PRIMARY_SEEDS
    freeze_meta(outdir, {
        "stage": stage, "seeds": [seeds[0], seeds[-1], len(seeds)],
        "arm": "H16Arm registered" if stage != "e2" else "H16Arm shuffle",
        "null_keep": [null_num, null_den],
        "config": {"trigger_dsh": h16_arm.TRIGGER_DSH,
                   "cooldown": h16_arm.COOLDOWN,
                   "screen_forks": h16_arm.SCREEN_FORKS,
                   "keep": h16_arm.KEEP,
                   "confirm_forks": h16_arm.CONFIRM_FORKS,
                   "rollout_horizon": h16_arm.ROLLOUT_H,
                   "ovr": [h16_arm.OVR_CHAMP_MAX, h16_arm.OVR_DELTA_MIN]}})
    todo = [s for s in seeds if not os.path.exists(seg_path(outdir, s))]
    print(f"[h16:{stage}] pairs={len(seeds)} todo={len(todo)} "
          f"workers={workers}", flush=True)
    from concurrent.futures import ProcessPoolExecutor, as_completed
    t0, checked = time.time(), set()
    with ProcessPoolExecutor(
            max_workers=workers, initializer=_winit,
            initargs=(stage, null_num, null_den)) as ex:
        futs = {ex.submit(_work, s): s for s in todo}
        for i, f in enumerate(as_completed(futs), 1):
            r = f.result()
            tmp = seg_path(outdir, r["seed"]) + ".tmp"
            with open(tmp, "w") as fh:
                json.dump(r, fh)
            os.replace(tmp, seg_path(outdir, r["seed"]))
            print(f"[h16:{stage}] {i}/{len(todo)} seed={r['seed']} "
                  f"A={r['base']['res']} B={r['trt']['res']} "
                  f"adj={r['trt'].get('h16_adjudications', 0)} "
                  f"ovr={r['trt'].get('h16_overrides', 0)} "
                  f"secs={r['secs']} wall={time.time()-t0:.0f}s", flush=True)
            if stage == "e1":
                for th in FUTILITY_NS:
                    if th in checked:
                        continue
                    pre = _prefix_pairs(outdir, seeds, th)
                    if len(pre) < th:
                        continue
                    checked.add(th)
                    sc = score_pairs(pre)
                    stop = sc["ci"][0] > FUTILITY_BOUND
                    print(f"[h16:INTERIM] n={th} d={sc['d']:+.4f} "
                          f"CI[{sc['ci'][0]:+.4f},{sc['ci'][1]:+.4f}] "
                          f"futility={'STOP' if stop else 'CONTINUE'}",
                          flush=True)
                    if stop:
                        print("FUTILITY_STOP — halting primary and guard",
                              flush=True)
                        os.system("systemctl --user stop drm-h16-guard "
                                  "2>/dev/null")
                        ex.shutdown(wait=False, cancel_futures=True)
                        sys.exit(3)     # FUTILITY_STOP: chain must not run e2
    done = sum(os.path.exists(seg_path(outdir, s)) for s in seeds)
    print(f"[h16:{stage}] ledger {done}/{len(seeds)}", flush=True)
    print(f"{stage.upper()}_OK" if done == len(seeds)
          else f"{stage.upper()}_INCOMPLETE", flush=True)
    if done != len(seeds):
        sys.exit(4)                     # incomplete: chain must not advance


# ---------------------------------------------------------------- analyze
def _override_rate(pairs):
    ov = sum(p["trt"]["h16_overrides"] for p in pairs)
    pl = sum(p["trt"]["n_plies"] for p in pairs)
    return ov / max(1, pl), ov, pl


def analyze():
    e1 = _prefix_pairs(os.path.join(OUT, "e1"), PRIMARY_SEEDS, 600)
    if len(e1) < 600:
        print(f"[analyze] e1 {len(e1)}/600 — FUTILITY_STOP or incomplete; "
              f"no efficacy readout before the registered n", flush=True)
    else:
        sc = score_pairs(e1)
        go = sc["mcnemar_p_onesided"] < 0.05 and sc["d"] < 0
        tr, ov, pl = _override_rate(e1)
        print(f"PRIMARY n=600: failA={sc['failA']:.4f} "
              f"failB={sc['failB']:.4f} d={sc['d']:+.4f} "
              f"CI[{sc['ci'][0]:+.4f},{sc['ci'][1]:+.4f}] good={sc['good']} "
              f"bad={sc['bad']} p={sc['mcnemar_p_onesided']:.4g} "
              f"ovr_rate={tr:.5f} ({ov}/{pl}) -> "
              f"{'GO' if go else 'NO_GO'}", flush=True)
        # achieved MDE from realized discordance (sec 6.6)
        disc = sc["good"] + sc["bad"]
        if disc:
            mde = 2.8 * np.sqrt(disc) / 600
            print(f"ACHIEVED-MDE (~80% power scale): +/-{100*mde:.2f}pp "
                  f"from {disc} discordant pairs — travels with the verdict",
                  flush=True)
        e2 = _prefix_pairs(os.path.join(OUT, "e2"), PRIMARY_SEEDS, 600)
        if len(e2) == 600:
            m = score_pairs(e2)
            mr, mov, mpl = _override_rate(e2)
            ratio = (mr / tr) if tr else float("inf")
            band = 0.9 <= ratio <= 1.1
            mgo = m["mcnemar_p_onesided"] < 0.05 and m["d"] < 0
            print(f"MUTANT n=600: d={m['d']:+.4f} "
                  f"p={m['mcnemar_p_onesided']:.4g} ovr_rate={mr:.5f} "
                  f"ratio={ratio:.3f} band={'OK' if band else 'OUT_OF_BAND'} "
                  f"mutant_reads_GO={'YES (VOID)' if mgo else 'no'}",
                  flush=True)
            if not band:
                keep = max(1, min(1000, round(1000 * tr / mr))) if mr else 1000
                print(f"AUTO-THIN: re-run e2 with --null-keep-num {keep} "
                      f"--null-keep-den 1000", flush=True)
        else:
            print(f"MUTANT: {len(e2)}/600 banked", flush=True)
    g = _prefix_pairs(os.path.join(OUT, "guard"), GUARD_SEEDS, 1000)
    if len(g) == 1000:
        gs = score_pairs(g)
        se = float(np.std([fail_of(p["trt"]) - fail_of(p["base"])
                           for p in g]) / np.sqrt(len(g)))
        lb1 = gs["d"] - 1.645 * se
        trip = gs["d"] > 0.010 or lb1 > 0
        tr, ov, pl = _override_rate(g)
        print(f"GUARD n=1000: failA={gs['failA']:.4f} "
              f"failB={gs['failB']:.4f} d={gs['d']:+.4f} "
              f"onesided95LB={lb1:+.4f} ovr_rate={tr:.5f} -> "
              f"{'TRIP (NO-PROMOTION)' if trip else 'PASS'}", flush=True)
    else:
        print(f"GUARD: {len(g)}/1000 banked", flush=True)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("stage", choices=("e1", "e2", "guard", "analyze",
                                      "seeds"))
    ap.add_argument("--workers", type=int, default=14)
    ap.add_argument("--null-keep-num", type=int, default=1)
    ap.add_argument("--null-keep-den", type=int, default=1)
    args = ap.parse_args()
    if args.stage == "seeds":
        print(f"primary: {PRIMARY_SEEDS[0]}..{PRIMARY_SEEDS[-1]} "
              f"n={len(PRIMARY_SEEDS)}")
        print(f"guard:   {GUARD_SEEDS[0]}..{GUARD_SEEDS[-1]} "
              f"n={len(GUARD_SEEDS)}")
        return
    if args.stage == "analyze":
        analyze()
        return
    run_stage(args.stage, args.workers, args.null_keep_num,
              args.null_keep_den)


if __name__ == "__main__":
    main()
