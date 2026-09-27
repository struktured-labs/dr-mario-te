#!/usr/bin/env python3
"""analyze_soak.py -- turn a probe_soak log into a BOUND, and check the killed-mutant arms.

Two jobs:

  soak <dir/probe_soak.log> ...
      For each canary, report the event count and a 95% one-sided UPPER BOUND on its rate,
      expressed in MINUTES OF PLAY, because that is the unit the owner cares about. Zero events
      is not a result on its own -- "0 in N frames" only means something once N is attached.

  val <dir/probe_soak.log> ...
      Check each killed-mutant arm actually fired. An arm that was supposed to reproduce a fault
      and did not means the DETECTOR is void, not that the cart is clean.

The bound is the exact Poisson one-sided upper limit, found by solving P(X <= k | lambda) = alpha
by bisection -- no scipy dependency. For k = 0 it reduces to -ln(0.05) = 2.996, i.e. the familiar
rule of three. Reported as: rate_UB = lambda_UB / N, so mean frames between events >= N/lambda_UB.
"""
import argparse
import math
import re
import sys

NTSC_FPS = 60.0988


def poisson_cdf(k: int, lam: float) -> float:
    """P(X <= k) for X ~ Poisson(lam), stable for the small k we see."""
    if lam <= 0:
        return 1.0
    term = math.exp(-lam)
    total = term
    for i in range(1, k + 1):
        term *= lam / i
        total += term
    return total


def poisson_upper(k: int, alpha: float = 0.05) -> float:
    """Largest lambda whose P(X <= k) is still alpha -- the 95% one-sided upper limit."""
    lo, hi = 0.0, max(10.0, 4.0 * (k + 1))
    while poisson_cdf(k, hi) > alpha:
        hi *= 2
    for _ in range(200):
        mid = (lo + hi) / 2
        if poisson_cdf(k, mid) > alpha:
            lo = mid
        else:
            hi = mid
    return (lo + hi) / 2


def kv(line: str) -> dict:
    return dict(re.findall(r"(\w+)=(-?[\w.]+)", line))


def read(path: str):
    txt = open(path, "r", errors="replace").read().splitlines()
    out = {"lines": txt, "summary": None, "soak": None, "soak2": None,
           "ckpts": [], "matches": [], "quart": [], "start": None, "events": []}
    for ln in txt:
        if ln.startswith("probe_soak start"):
            out["start"] = kv(ln)
        elif ln.startswith("SUMMARY "):
            out["summary"] = kv(ln)
        elif ln.startswith("SOAK2 "):
            out["soak2"] = kv(ln)
        elif ln.startswith("SOAK "):
            out["soak"] = kv(ln)
        elif ln.startswith("CKPT "):
            out["ckpts"].append(kv(ln))
        elif ln.startswith("MATCH "):
            out["matches"].append(kv(ln))
        elif ln.startswith("QUART "):
            out["quart"].append(kv(ln))
        elif "!!!" in ln or "***" in ln or ln.startswith("ERR "):
            out["events"].append(ln)
    return out


# canary key -> (human name, source dict)
CANARIES = [
    ("MIXED_PRG_nonboot", "mixed shift-reg load into PRG reg"),
    ("wipes", "RAM wipe (VC1 -> 0)"),
    ("ABORT_4to0", "mid-match abort to title (4->0)"),
    ("brk_a02e", "BRK-loop hits"),
    ("busyEp", "stuck-BUSY episodes"),
    ("modeStall", "mode stalls"),
    ("gapStall", "match-boundary stalls"),
    ("srchStall", "search stalls"),
    ("title0", "unrequested title returns"),
    ("tuckwr", "tuck-executor writes (identity: MUST be 0)"),
]


def do_soak(paths, tags):
    tot_frames = tot_play = tot_matches = tot_sr = 0
    agg = {k: 0 for k, _ in CANARIES}
    partial = []
    for p in paths:
        d = read(p)
        st = d["start"] or {}
        tag = st.get("tag", "?")
        if tags and tag not in tags:
            print(f"!! {p}: tag={tag} is not one of {tags} -- REFUSING (untagged/mismatched log)")
            return 2
        s, k = d["summary"], d["soak"]
        if s is None or k is None:
            c = d["ckpts"][-1] if d["ckpts"] else None
            if c is None:
                print(f"!! {p}: tag={tag} has NO summary and NO checkpoint -- contributes NOTHING")
                continue
            partial.append(tag)
            f = int(c["f"])
            print(f"~~ {p}: tag={tag} PARTIAL, using last checkpoint f={f}")
            tot_frames += f
            tot_matches += int(c.get("ended", 0))
            for key, _ in CANARIES:
                agg[key] += int(c.get(_ck(key), 0) or 0)
            continue
        f = int(s["frames"])
        tot_frames += f
        tot_play += int(k.get("play4_frames", 0))
        tot_sr += int(k.get("sr_loads", s.get("sr_loads", 0)))
        tot_matches += int(s["matches_ended"])
        merged = {**s, **k}
        for key, _ in CANARIES:
            agg[key] += int(merged.get(key, merged.get(_ck(key), 0)) or 0)
        print(f"== {p}")
        print(f"   tag={tag} frames={f} play4={k.get('play4_frames')} "
              f"matches started={s['matches_started']} ended={s['matches_ended']} "
              f"clean={s['clean_ends']} aborts={s['ABORT_4to0']}")
        print(f"   fps={k.get('fps')} wall={k.get('wall')}")
        if d["soak2"]:
            print(f"   {' '.join(f'{a}={b}' for a, b in d['soak2'].items() if a != 'tag')}")
        for q in d["quart"]:
            print(f"   QUART q={q['q']} matches={q['matches']} mixedPRG={q['mixedPRG']} "
                  f"wipes={q['wipes']} soft8036={q['soft8036']} abort={q['abort']}")

    print()
    print("=" * 78)
    print(f"TOTAL frames {tot_frames}   live-play (mode 4) frames {tot_play}   "
          f"matches ended {tot_matches}   MMC1 sr_loads {tot_sr}")
    print(f"      = {tot_frames / NTSC_FPS / 60:.1f} min of emulated wall time "
          f"({tot_play / NTSC_FPS / 60:.1f} min of it LIVE PLAY) at {NTSC_FPS} Hz")
    if partial:
        print(f"      ⚠ PARTIAL arms folded in at their last checkpoint: {partial}")
    print("=" * 78)
    print(f"{'canary':<44}{'events':>7}{'95% UB rate':>14}{'min between':>14}")
    worst = None
    for key, name in CANARIES:
        k_ev = agg[key]
        lam = poisson_upper(k_ev)
        per_frame = lam / tot_frames if tot_frames else float("inf")
        mins = (1 / per_frame) / NTSC_FPS / 60 if per_frame > 0 else float("inf")
        print(f"{name:<44}{k_ev:>7}{per_frame:>14.2e}{mins:>14.1f}")
        if worst is None or mins < worst[1]:
            worst = (name, mins)
    print("=" * 78)
    lam0 = poisson_upper(0)
    if tot_frames:
        mins0 = (tot_frames / lam0) / NTSC_FPS / 60
        play0 = (tot_play / lam0) / NTSC_FPS / 60 if tot_play else 0
        print(f"HEADLINE (any single canary at 0 events in {tot_frames} frames):")
        print(f"  95% upper bound = 1 event per {tot_frames / lam0:,.0f} frames "
              f"= 1 per {mins0:.1f} MINUTES of play")
        if tot_play:
            print(f"  against LIVE-PLAY frames only: 1 per {play0:.1f} minutes of live play")
    if worst:
        print(f"WORST canary bound: {worst[0]} at 1 per {worst[1]:.1f} min")
    print()
    print("UNVALIDATED DETECTORS -- their zeros are NOT evidence:")
    for k, why in UNVALIDATED.items():
        print(f"  {k}: {why}")
    return 0


def _ck(key):
    """checkpoint lines use the statline() spellings"""
    return {"MIXED_PRG_nonboot": "mixedPRG", "ABORT_4to0": "abort",
            "brk_a02e": "brk", "busyEp": "busyEp"}.get(key, key)


# Each entry is the fault the arm injects and the counter that MUST move because of it. An arm
# that does not fire means the DETECTOR is void, not that the cart is clean.
VAL_EXPECT = {
    "s-val-busy":   [("busyEp", ">", 0)],
    # thresholds are lowered to 600 for this arm only so the 900-frame frozen-title injection can
    # actually cross them; the soak keeps 7200/3600
    "s-val-title":  [("title0", ">", 0), ("modeStall", ">", 0), ("gapStall", ">", 0)],
    "s-val-mech":   [("MIXED_PRG_nonboot", ">", 0), ("wipes", ">", 0), ("soft8036", ">", 0)],
    "s-val-tuckwr": [("tuckwr", ">", 0)],
}

# The A-integrity pair is checked on the ACHK verdict string, not a counter. VOID is a THIRD
# outcome, distinct from PASS -- a dead callback or an unreadable accumulator means the check did
# not run, and must never be read as a clean cart.
ACHK_EXPECT = {
    "s-val-aclob": "FAIL_A_CORRUPTED",   # the HELD cart 087ff959 -- must be caught
    "s-val-aok":   "PASS",               # v6e -- must come back clean
}

# Detectors with no killed-mutant test. Reported as UNVALIDATED so the reader can tell which of
# the soak's zeros carry weight. search_stall keys on the cart having stopped issuing GO while
# still in mode 4; no instrument-side injection produces that without forging the detector's own
# input, and a detector validated against a forged version of its own input is validated against
# nothing. The honest route is a cart-side fault build that deliberately stops issuing GO.
UNVALIDATED = {
    "srchStall": "no injection can produce 'stopped issuing GO while in mode 4' without forging "
                 "the detector's own input; needs a cart-side fault build",
    "brk_a02e":  "no BRK-loop mutant was run in this soak; the detector is inherited from the "
                 "M3-era gate where it did fire",
}


def do_val(paths):
    ok = True
    for p in paths:
        d = read(p)
        st = d["start"] or {}
        tag = st.get("tag", "?")
        s, k = d["summary"], d["soak"]
        if s is None or k is None:
            print(f"{tag:<14} NO SUMMARY -- arm did not complete; detector NOT validated")
            ok = False
            continue
        merged = {**s, **k}
        exp = VAL_EXPECT.get(tag)
        if not exp and tag not in ACHK_EXPECT:
            print(f"{tag:<14} (no expectation registered)")
            continue
        exp = exp or []
        av = None
        for ln in d["lines"]:
            if ln.startswith("ACHK "):
                av = kv(ln).get("verdict")
        if tag in ACHK_EXPECT:
            want = ACHK_EXPECT[tag]
            good = (av == want)
            print(f"{tag:<14} {'ACHK verdict':<22} = {str(av):<26} expected {want:<20} "
                  f"{'OK' if good else 'MISMATCH -- A-CHECK IS NOT USABLE'}")
            ok = ok and good
        for key, op, want in exp:
            got = int(merged.get(key, merged.get(_ck(key), 0)) or 0)
            good = got > want if op == ">" else got == want
            print(f"{tag:<14} {key:<22} = {got:<6} expected {op}{want}   "
                  f"{'FIRED (detector valid)' if good else 'DID NOT FIRE -- DETECTOR VOID'}")
            ok = ok and good
    print("VALIDATION " + ("PASS -- every new detector fired on its own fault" if ok
                           else "FAIL -- at least one detector could not be shown to fail"))
    return 0 if ok else 1


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("mode", choices=["soak", "val"])
    ap.add_argument("logs", nargs="+")
    ap.add_argument("--tag", action="append", default=[])
    a = ap.parse_args()
    return do_soak(a.logs, a.tag) if a.mode == "soak" else do_val(a.logs)


if __name__ == "__main__":
    sys.exit(main())
