"""gate_h16.py — H16 killed-mutant sheet (REGISTRATION_H16.md sec 6.5).

Runs on the house gate seeds 40000..40011 (reserved for gates, never scored
— PREREG_ORACLE sec 'gate seeds').  All suites must pass before E1.

  S1 m-neverfire   H16Arm(never_fire) action-trace bit-identity with H12Arm,
                   12/12 (the load-bearing one: H16 IS H12 when quiet).
  S2 not-inert     true H16Arm produces adjudications>0 AND overrides>0
                   across the gate seeds (an arm that never binds tests
                   nothing) + liveness for S1.
  S3 pressure-live injections counted in game path AND fork path
                   (bursty counter: H16 count > H12 count > 0, same seed).
  S4 m-swap        scorer negation: score_pairs(d) == -score_pairs(swapped).
  S5 m-nodedup     population mutant: dedup width < raw width on a real
                   fired double-capsule state; board_key collision must trip
                   the never-same-board assert.
  S6 m-cooldown    no_cooldown adjudications grow (bank prediction ~3.5x);
                   require pooled ratio > 1.8 and report the measured value.
  S7 verdict-gate  score_pairs + trip rule driven with synthetic tables
                   (GO-shaped, null, guard-trip) — the analysis code is
                   itself shown to discriminate.
"""
import copy
import json
import os
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import numpy as np

import h16_arm as HA
import run_h16 as R

GATE_SEEDS = list(range(40000, 40012))
OUT = os.path.join(HERE, "out")


def _play(kind, seed):
    import oracle_arm as OA
    C, bmodel = OA.init_rig("lulu", level=20)
    if kind == "base":
        arm = R.make_base()
    elif kind == "nf":
        arm = HA.H16Arm(never_fire=True, topk=4, horizon=15, fork_samples=5,
                        tie_margin=0.5, future_mode="dist", provenance=True)
    elif kind == "true":
        arm = R.make_trt("true")
    elif kind == "nocool":
        arm = HA.H16Arm(no_cooldown=True, topk=4, horizon=15, fork_samples=5,
                        tie_margin=0.5, future_mode="dist", provenance=True)
    else:
        raise ValueError(kind)
    t0 = time.monotonic()
    r = OA.play_one(seed, arm, C, bmodel, max_pills=400)
    r["kind"], r["secs"] = kind, round(time.monotonic() - t0, 1)
    for k in ("h16_trigger_plies", "h16_adjudications", "h16_overrides"):
        r[k] = arm.stats.get(k, 0)
    return r


def _play_star(args):
    return _play(*args)


def s1_s2_s6(workers):
    """One parallel pass: base/nf/true/nocool on every gate seed."""
    from concurrent.futures import ProcessPoolExecutor
    tasks = [(k, s) for s in GATE_SEEDS
             for k in ("base", "nf", "true", "nocool")]
    res = {}
    with ProcessPoolExecutor(max_workers=workers) as ex:
        for r in ex.map(_play_star, tasks):
            res[(r["kind"], r["seed"])] = r
            print(f"  [{r['kind']}] seed={r['seed']} res={r['res']} "
                  f"plies={r['n_plies']} adj={r['h16_adjudications']} "
                  f"ovr={r['h16_overrides']} secs={r['secs']}", flush=True)
    ok = True

    ident = all(res[("base", s)]["_actions"] == res[("nf", s)]["_actions"]
                and res[("base", s)]["res"] == res[("nf", s)]["res"]
                for s in GATE_SEEDS)
    ok &= ident
    print(f"[S1 m-neverfire] bit-identity {sum(1 for s in GATE_SEEDS)}"
          f" seeds: {'PASS' if ident else 'FAIL'}", flush=True)

    adj = sum(res[("true", s)]["h16_adjudications"] for s in GATE_SEEDS)
    ovr = sum(res[("true", s)]["h16_overrides"] for s in GATE_SEEDS)
    live = adj > 0 and ovr > 0
    ok &= live
    print(f"[S2 not-inert] adjudications={adj} overrides={ovr}: "
          f"{'PASS' if live else 'FAIL'}", flush=True)

    a_cool = sum(res[("true", s)]["h16_adjudications"] for s in GATE_SEEDS)
    a_nc = sum(res[("nocool", s)]["h16_adjudications"] for s in GATE_SEEDS)
    ratio = a_nc / max(1, a_cool)
    grow = ratio > 1.8
    ok &= grow
    print(f"[S6 m-cooldown] adjudications {a_cool} -> {a_nc} "
          f"(ratio {ratio:.2f}; bank predicted ~3.5): "
          f"{'PASS' if grow else 'FAIL'}", flush=True)
    return ok, res


def s3_pressure_live():
    import oracle_arm as OA
    import bursty_model as BM
    C, bmodel = OA.init_rig("lulu", level=20)
    real = BM.inject_bursty_garbage
    counts = {}
    try:
        for kind in ("base", "true"):
            n = {"n": 0}

            def counting(board, model, s, pills, cs, _n=n):
                _n["n"] += 1
                return real(board, model, s, pills, cs)

            BM.inject_bursty_garbage = counting
            arm = R.make_base() if kind == "base" else R.make_trt("true")
            OA.play_one(GATE_SEEDS[0], arm, C, bmodel, max_pills=400)
            counts[kind] = n["n"]
    finally:
        BM.inject_bursty_garbage = real
    ok = counts["base"] > 0 and counts["true"] > counts["base"]
    print(f"[S3 pressure-live] injections base={counts['base']} "
          f"h16={counts['true']} (game path >0, fork path adds): "
          f"{'PASS' if ok else 'FAIL'}", flush=True)
    return ok


def s4_swap():
    fake = ([{"base": {"won": 0}, "trt": {"won": 1}}] * 7
            + [{"base": {"won": 1}, "trt": {"won": 0}}] * 3
            + [{"base": {"won": 1}, "trt": {"won": 1}}] * 10)
    d1 = R.score_pairs(fake)["d"]
    sw = [{"base": p["trt"], "trt": p["base"]} for p in fake]
    d2 = R.score_pairs(sw)["d"]
    ok = abs(d1 + d2) < 1e-12 and d1 != 0
    print(f"[S4 m-swap] d={d1:+.4f} swapped={d2:+.4f}: "
          f"{'PASS' if ok else 'FAIL'}", flush=True)
    return ok


def s5_nodedup():
    import oracle_arm as OA
    import labelcore as LC
    C, bmodel = OA.init_rig("lulu", level=20)
    hit = tripped = False
    grew = 0
    for seed in GATE_SEEDS[:6]:
        env = OA.make_env(seed, 20, max_pills=400)
        for ply in range(400):
            if env.board.virus_count() == 0:
                break
            H = OA.heights(env.board.color)
            dsh = int(max(H[3], H[4]))
            if dsh >= HA.TRIGGER_DSH and int(env.cur.a) == int(env.cur.b):
                hit = True
                dd = LC.enumerate_candidates(env, dedup=True)
                raw = LC.enumerate_candidates(env, dedup=False)
                if len(raw) > len(dd):
                    grew += 1
                # board_key collision must trip the never-same-board assert
                orig = LC.board_key
                try:
                    LC.board_key = lambda c1, v1, n: "collide"
                    try:
                        LC.enumerate_candidates(env, dedup=True)
                    except AssertionError:
                        tripped = True
                finally:
                    LC.board_key = orig
                break
            vals = LC.compute_vals(env, C["w"], C["fl"], C["wt"], C["ws"])
            a = OA._champ_action(vals, OA.CHAMP_ORDER)
            if a is None:
                break
            r, _v = OA._advance(env, a, C, seed, bmodel)
            if r is not None:
                break
        if hit and grew and tripped:
            break
    ok = hit and grew > 0 and tripped
    print(f"[S5 m-nodedup] fired double-capsule state found={hit} "
          f"raw>dedup on {grew} state(s), collision-assert tripped={tripped}: "
          f"{'PASS' if ok else 'FAIL'}", flush=True)
    return ok


def s7_verdict():
    def mk(nf_a, nf_b, n):
        """n pairs with nf_a base-only fails, nf_b trt-only fails."""
        out = []
        out += [{"base": {"won": 0}, "trt": {"won": 1}}] * nf_a
        out += [{"base": {"won": 1}, "trt": {"won": 0}}] * nf_b
        out += [{"base": {"won": 1}, "trt": {"won": 1}}] * (n - nf_a - nf_b)
        return out

    go = R.score_pairs(mk(60, 20, 600))
    null = R.score_pairs(mk(30, 30, 600))
    ok = (go["mcnemar_p_onesided"] < 0.05 and go["d"] < 0)
    ok &= not (null["mcnemar_p_onesided"] < 0.05 and null["d"] < 0)
    trip_tbl = mk(2, 30, 1000)
    ts = R.score_pairs(trip_tbl)
    se = float(np.std([(1 - p["trt"]["won"]) - (1 - p["base"]["won"])
                       for p in trip_tbl]) / np.sqrt(len(trip_tbl)))
    trip = ts["d"] > 0.010 or (ts["d"] - 1.645 * se) > 0
    ok &= trip
    print(f"[S7 verdict-gate] GO-table p={go['mcnemar_p_onesided']:.2g} "
          f"null-table p={null['mcnemar_p_onesided']:.2g} "
          f"trip-table trips={trip}: {'PASS' if ok else 'FAIL'}", flush=True)
    return ok


def main():
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--workers", type=int, default=12)
    args = ap.parse_args()
    os.makedirs(OUT, exist_ok=True)
    ok = True
    ok &= s4_swap()
    ok &= s7_verdict()
    ok &= s5_nodedup()
    ok &= s3_pressure_live()
    g, res = s1_s2_s6(args.workers)
    ok &= g
    with open(os.path.join(OUT, "gate_sheet.json"), "w") as fh:
        json.dump({k[0] + "_" + str(k[1]): {
            "res": v["res"], "plies": v["n_plies"],
            "adj": v["h16_adjudications"], "ovr": v["h16_overrides"],
            "secs": v["secs"]} for k, v in res.items()}, fh, indent=1)
    print("SHEET_OK" if ok else "SHEET_FAIL", flush=True)
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
