#!/usr/bin/env python3
"""Stage 2: re-score screen survivors at high n on a DISJOINT seed block.

The screen tested ~38 candidates at a 95% CI on seeds 400-559. Under a true null that
yields ~2 apparent winners by luck, and this project has already retracted two results that
were exactly that. Nothing from the screen is a finding until it survives here.

Every spawn value tested came out slightly ABOVE 50% on the tuning block (100/200/250/300 ->
50.6/50.9/51.2/51.2%). Both directions beating the centre is not what a real gradient looks
like; it is what a seed-block artefact looks like. That is the specific thing this checks.

Reports the SAME candidate on the tuning block and on the holdout block, so the comparison
is like-for-like and any shrinkage is visible.
"""
from __future__ import annotations
import sys, os, json, argparse

ROOT = "/home/struktured/projects/dr_mario_rl"
HERE = os.path.dirname(os.path.abspath(__file__))
for p in (HERE, ROOT + "/tmp/combo_term", ROOT + "/tmp/pillrng",
          ROOT + "/.claude/worktrees/faithful-sim/src"):
    if p not in sys.path:
        sys.path.insert(0, p)

from h2h_vs import WINNER, run, fmt

CANDS = {
    "spawn=250":  {"spawn": 250},
    "spawn=300":  {"spawn": 300},
    "spawn=200":  {"spawn": 200},
    "spawn=100":  {"spawn": 100},
    "toprisk=45": {"toprisk": 45},
    "vbonus=100": {"vbonus": 100},
    # L20 candidates. vbonus=400 nominally cleared the bar at L20 (57.5% [51.2,63.7]) but
    # the dose-response ZIGZAGS (100/200/400/800 -> 55.0/49.6/57.5/52.1) and its MARGIN is
    # NEGATIVE (-0.66) while its win rate is positive -- i.e. it would be winning more
    # matches while finishing further behind on viruses. Both are noise signatures.
    "vbonus=400": {"vbonus": 400},
    "vbonus=200": {"vbonus": 200},
    # ★ THE ONE REAL LEAD. Under the ROM-true rule (cascades sum, 85% of attacks) `cross`
    # -- combo credit, the only term rewarding cascade STRUCTURE -- flips from monotonically
    # harmful to a clean monotone dose-response peaking low: 4/8/16/32 -> 54.1/51.2/49.4/38.8%,
    # margin +0.53/+0.02/-0.52/-2.04. Win rate and margin AGREE in sign at every point, which
    # is exactly what the L20 vbonus artefact did NOT do. Mechanistically motivated, so it
    # gets the holdout the artefacts failed.
    "cross=4":    {"cross": 4},
    "cross=2":    {"cross": 2},
    # ★★ cascade-search's LINK-FAITHFUL cap-1 arm. This is the first candidate that moves
    # the CASCADE channel (~90% of ROM attacks) rather than the simultaneity channel my
    # vbonus/cross sweeps could only reach. Their solo data: attack rate +7%, doubles +37%,
    # and clear rate 96.7% -> 100.0% over 360 games (12 discordant pairs, ALL one way).
    # Their paired-pills headline did NOT replicate, so speed is not the claim -- robustness
    # and attack rate are. Scored here as a VS arm for the first time.
    "lnk1":       {"arm": "lnk1"},
    # the fixpoint arm, scored only as a NEGATIVE control: it should send LESS garbage
    # (-18 to -23% on their instrument) because seeing chains makes the search avoid them.
    "lnkfix":     {"arm": "lnkfix"},
    # cascade-search's chain-depth reward, built on the FIXPOINT leaf. Their intent sweep
    # showed the knob has real authority: intent 3.3x and ATTACK RATE 2.8x across
    # w_chain 0->720, with INTEND==REALIZE at every dose (correct physics, no phantoms).
    # So this is the first lever that moves the attack channel by MULTIPLES. Whether that
    # buys wins is exactly what my lnk1/lnkfix result predicts it will NOT.
    "chain180":   {"arm": "chain180"},
    "chain360":   {"arm": "chain360"},
}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--seeds", type=int, default=400)
    ap.add_argument("--tune0", type=int, default=400)
    ap.add_argument("--tune-n", type=int, default=160)
    ap.add_argument("--hold0", type=int, default=8000)
    ap.add_argument("--workers", type=int, default=12)
    ap.add_argument("--level", type=int, default=11)
    ap.add_argument("--rule", default="rom", choices=("rom", "exact"))
    ap.add_argument("--only", default=None)
    ap.add_argument("--out", default="/home/struktured/projects/dr-mario-qa-wt/tmp/selfplay/holdout.jsonl")
    a = ap.parse_args()

    names = a.only.split(",") if a.only else list(CANDS)
    tune = list(range(a.tune0, a.tune0 + a.tune_n))
    hold = list(range(a.hold0, a.hold0 + a.seeds))
    print(f"HOLDOUT CONFIRMATION  L{a.level}  REAL NES capsules")
    print(f"  tuning block  seeds {tune[0]}..{tune[-1]}  (n={len(tune)})")
    print(f"  HELD-OUT block seeds {hold[0]}..{hold[-1]}  (n={len(hold)})  <- never used to select\n",
          flush=True)

    with open(a.out, "w") as fh:
        for name in names:
            cand = dict(WINNER); cand.update(CANDS[name])
            rt = run(cand, dict(WINNER), tune, workers=a.workers, level=a.level, rule=a.rule)
            rh = run(cand, dict(WINNER), hold, workers=a.workers, level=a.level, rule=a.rule)
            print(fmt(f"{name} TUNE", rt), flush=True)
            print(fmt(f"{name} HOLD", rh), flush=True)
            verdict = ("CONFIRMED" if rh["wr_lo"] > 0.5 else
                       "NOT CONFIRMED (holdout CI includes 50%)")
            print(f"    => {verdict}\n", flush=True)
            fh.write(json.dumps({"name": name, "cand": cand,
                                 "tune": {k: v for k, v in rt.items()
                                          if k not in ("wr_seed", "mg_seed")},
                                 "hold": {k: v for k, v in rh.items()
                                          if k not in ("wr_seed", "mg_seed")},
                                 "confirmed": rh["wr_lo"] > 0.5}) + "\n")
            fh.flush()


if __name__ == "__main__":
    main()
