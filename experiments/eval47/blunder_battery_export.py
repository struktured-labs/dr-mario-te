"""Run every blunder tier once and cache the numbers for the notebook.

The notebook is deliberately I/O-light -- stdlib json only, no numpy, no PIL -- because
this box carries live jobs and the tiers decode thousands of video frames between them.
So the tiers run here, out of band, exactly like `repro_struktured_fit.py` does for the
pressure fit, and the notebook reads the cache.

Every tier's own gate runs first. If any gate fails this writes nothing: a cache is the
one place a broken number would outlive the run that produced it.
"""
import collections
import json
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "results", "blunder_battery.json")
PY = sys.executable

GATED_SCRIPTS = ("blunder_tiers.py", "blunder_tier_d.py", "blunder_tier_f2.py",
                 "blunder_tier_d2.py", "blunder_tier_o.py", "battery4_metric4.py")


def gates():
    """Each tier script exits nonzero when its own control or mutant gate fails."""
    ok = True
    for s in GATED_SCRIPTS:
        r = subprocess.run([PY, os.path.join(HERE, s)], capture_output=True, text=True)
        print(f"  {s:26s} exit {r.returncode}  {'PASS' if r.returncode == 0 else 'FAIL'}")
        if r.returncode:
            print(r.stdout[-2000:])
            print(r.stderr[-2000:])
        ok &= r.returncode == 0
    return ok


def collect():
    import blunder_tiers as M
    import blunder_tier_d as D
    import blunder_tier_f2 as F2
    import blunder_tier_d2 as D2
    import blunder_tier_o as O
    import battery4_metric4 as M4
    import blunder_boards as BB

    out = {"players": {}}

    # ---- tier M (rotation corrections), the adjudicated tier
    srcs = {"struktured": [os.path.join(M.LE, "film_20260804", f"{m}.csv")
                           for m in ("m1", "m2", "m3", "m4")],
            "dr. lulu": [os.path.join(M.LE, "film_20260808", "p1_m3.csv")]}
    for p, paths in srcs.items():
        t = M.tally([r for q in paths for r in M.load(q)])
        out["players"].setdefault(p, {})["tier_M"] = dict(
            n=t["pills"], any=t["any"], reversal=t["reversal"],
            overshoot=t["overshoot"], late=t["late-flurry"],
            per100=100 * t["any"] / t["pills"], evidence="adjudicated")

    # ---- tier D (wrong colour phase)
    dtot, _dfl = D.run()
    for p, a in dtot.items():
        out["players"].setdefault(p, {})["tier_D"] = dict(
            n=a["scored"], ungated=a["ungated"], flagged=a["gated"],
            per100=100 * a["gated"] / a["scored"] if a["scored"] else None,
            evidence="controlled")

    data = BB.load_all()
    # ---- tier F2 (last-access seal), endgame-gated
    for p, ms in data.items():
        agg, fl = F2.run(ms)
        ug, _ = F2.run(ms, endgame_vc=None)
        reop = sum(F2.later_reopened(m, [f for f in fl if f["match"] == m.name]) for m in ms)
        out["players"][p]["tier_F2"] = dict(
            n=agg["scored"], ungated=agg["ungated"], flagged=agg["gated"],
            narrow=agg["narrow"], reopen_suppressed=agg["excl_reopenable"],
            later_reopened=reop,
            per100=100 * agg["gated"] / agg["scored"] if agg["scored"] else None,
            whole_match_n=ug["scored"], whole_match_flagged=ug["gated"],
            evidence="controlled")

    # ---- tier D2 (hard burial) -- NOT QUOTABLE, see blunder_tier_d2.py's limitation block.
    # The cache carries the marker so the number cannot outlive the caveat: `quotable` is
    # False, `fp_estimate` sits next to every figure, and `tightening` records what the
    # matched-reopen gate and the last-straw rule actually achieved (volume, not precision).
    def d2_variant(ms, **kw):
        agg, evs = D2.run(ms, **kw)
        nb, reop, clr = D2.survival(ms, evs)
        return agg, dict(flagged=agg["gated"], viruses_buried=nb, later_reopened=reop,
                         later_cleared=clr,
                         fp_estimate=100 * reop / nb if nb else None,
                         per100=100 * agg["gated"] / agg["scored"] if agg["scored"] else None)

    for p, ms in data.items():
        agg, head = d2_variant(ms)
        _a1, v_reopen = d2_variant(ms, reopen_gate=True)
        _a2, v_straw = d2_variant(ms, last_straw=True)
        out["players"][p]["tier_D2"] = dict(
            n=agg["scored"], ungated=agg["ungated"], forced=agg["excl_forced"],
            bins={b: agg["bin_" + b] for b, _lo, _hi in D2.BINS},
            control_pass=100 * agg["scored"] / (agg["scored"] + agg["control_fail_landing"]),
            quotable=False, not_quotable=D2.NOT_QUOTABLE,
            tightening=dict(matched_reopen_gate=v_reopen, last_straw=v_straw),
            evidence="not quotable", **head)

    # ---- tier O (evaporated opportunity) + metric 4 (cascade share)
    corpus, _dropped = O.load_corpus()
    t_dec, sizes = O.size_threshold(corpus, 0, O.TOP_DECILE)
    dec, _fd = O.analyse(corpus, t_dec)
    any_, _fa = O.analyse(corpus, O.ANY_CLEAR)
    for p in out["players"]:
        f, g = dec.get(p), any_.get(p)
        if not f:
            continue
        out["players"][p]["tier_O"] = dict(
            n=f["scored"], threshold_cells=float(t_dec),
            opportunity=f["opportunity"], declined=f["declined"],
            destroyed_uncashed=f["destroyed_uncashed"], flagged=f["flagged"],
            per100=100 * f["flagged"] / f["scored"] if f["scored"] else None,
            any_opportunity=g["opportunity"], any_declined=g["declined"],
            any_flagged=g["flagged"],
            any_per100=100 * g["flagged"] / g["scored"] if g["scored"] else None,
            evidence="controlled")

    bylock = M4.build(corpus)
    for p, locks in bylock.items():
        c, _v = M4.classify(locks)
        cl = [L for L in locks if L.eng_clear]
        eng = sum(1 for L in cl if L.eng_total > L.eng_first)
        out["players"][p]["metric4"] = dict(
            frame_events=c["events"], frame_cascade=c["cascade"],
            frame_cascade_pct=100 * c["cascade"] / c["events"] if c["events"] else None,
            engine_clears=len(cl), engine_cascade=eng,
            engine_cascade_pct=100 * eng / len(cl) if cl else None,
            evidence="bracketed")

    ai_path = os.path.join(HERE, "results", "blunder_ai_rows.json")
    if os.path.exists(ai_path):
        out["ai"] = json.load(open(ai_path))
    return out


def main():
    print("TIER GATES (each script re-runs its own control + killed mutants)")
    if not gates():
        print("\nA TIER GATE FAILED -- cache NOT written")
        return 1
    print("  ALL GATES PASS\n")
    res = collect()
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w") as fh:
        json.dump(res, fh, indent=1, sort_keys=True)
    print(f"wrote {OUT}")
    for p, tiers in res["players"].items():
        for t, d in sorted(tiers.items()):
            print(f"  {p:12s} {t:9s} n={d.get('n')} per100="
                  f"{d.get('per100') if d.get('per100') is None else round(d['per100'], 2)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
