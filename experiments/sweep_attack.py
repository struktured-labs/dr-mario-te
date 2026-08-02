#!/usr/bin/env python3
"""The one search that is genuinely VS-specific: does BUYING ATTACKS pay under VS scoring?

WHY THIS AND NOT MORE COORDINATE DESCENT ON THE SHAPE TERMS. Every constant in the main
screen (vrdy/buried/setup/maxh/holes/toprisk/spawn/...) was already optimised against a solo
objective, and a VS objective in which garbage is rare will just rediscover that optimum --
so those knobs cannot tell us whether solo was a leaky proxy. Two constants CAN:

  R_VBONUS  flat extra immediate reward when a placement clears >= 2 viruses at once
  R_CROSS   per-virus min(hq,vq) -- combo credit, the axis rdy_ext discards

These make the search actively PREFER simultaneity. Under a SOLO objective simultaneity is
worth only the viruses it removes, so solo tuning had every reason to push them to zero
(both sit at 0 in the winner). Under a VS objective a double ALSO SENDS GARBAGE, so their
optimum genuinely should move. If VS is a different objective from solo, this is where the
difference lives; if these come back flat too, the "leaky proxy" story is dead.

Reports ATTACK RATE alongside win rate, because there are two distinct failure modes and
they demand different conclusions:
  * attacks DON'T rise  -> the constant is inert / the search cannot buy doubles at any price
  * attacks DO rise but win rate doesn't -> attacking is real but DOESN'T PAY at this rate
"""
from __future__ import annotations
import sys, os, json, time, argparse
from concurrent.futures import ProcessPoolExecutor

ROOT = "/home/struktured/projects/dr_mario_rl"
HERE = os.path.dirname(os.path.abspath(__file__))
for p in (HERE, ROOT + "/tmp/combo_term", ROOT + "/tmp/pillrng",
          ROOT + "/.claude/worktrees/faithful-sim/src"):
    if p not in sys.path:
        sys.path.insert(0, p)

from h2h_vs import WINNER
from sweep_knobs import evaluate, _warm

# winner has vbonus=0 and cross=0. wvir=180 is the shipped per-virus immediate reward;
# raising it is the "clear density" lever from memory `dr-mario-combo-gap`.
GRID = {
    "vbonus": [100, 200, 400, 800],
    "cross":  [4, 8, 16, 32],
    "wvir":   [240, 300],
}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--seeds", type=int, default=160)
    ap.add_argument("--seed0", type=int, default=400)
    ap.add_argument("--workers", type=int, default=12)
    ap.add_argument("--level", type=int, default=11)
    ap.add_argument("--no-garbage", action="store_true",
                    help="the control: same sweep with garbage never delivered")
    ap.add_argument("--uniform", action="store_true",
                    help="CONTRAST ONLY -- uniform capsules, to show what they would have said")
    ap.add_argument("--only", default=None)
    ap.add_argument("--rule", default="rom", choices=("rom", "exact"))
    ap.add_argument("--out", default="../tmp/selfplay/attack_real.jsonl")
    a = ap.parse_args()

    cfg = {"level": a.level, "max_pills": 300, "nes_pills": not a.uniform,
           "chain_mode": "first", "topk2": 8, "garbage": not a.no_garbage,
           "rule": a.rule}
    seeds = list(range(a.seed0, a.seed0 + a.seeds))
    ref = dict(WINNER)
    out = os.path.abspath(os.path.join(HERE, a.out)) if not os.path.isabs(a.out) else a.out
    os.makedirs(os.path.dirname(out), exist_ok=True)

    cap = "UNIFORM (contrast only)" if a.uniform else "REAL NES"
    print(f"ATTACK-SHAPING SWEEP vs WINNER   L{a.level}  {cap} capsules  "
          f"garbage {'OFF (control)' if a.no_garbage else 'ON'}  rule={a.rule}  "
          f"{a.seeds} seeds = {2*a.seeds} matches/eval", flush=True)
    print(f"  winner baseline: vbonus=0 cross=0 wvir=180\n", flush=True)

    grid = {k: v for k, v in GRID.items() if not a.only or k in a.only.split(",")}
    t0 = time.time()
    with ProcessPoolExecutor(max_workers=a.workers, initializer=_warm, initargs=(8,)) as ex:
        with open(out, "w") as fh:
            for knob, vals in grid.items():
                for v in vals:
                    cand = dict(ref); cand[knob] = v
                    r = evaluate(ex, cand, ref, seeds, cfg)
                    r["knob"] = knob; r["value"] = v
                    fh.write(json.dumps(r) + "\n"); fh.flush()
                    sig = "  <-- CI EXCLUDES 50%" if r["wr_lo"] > 0.5 else (
                          "  (worse)" if r["wr_hi"] < 0.5 else "")
                    ratio = r["atk_cand"] / r["atk_ref"] if r["atk_ref"] else float("nan")
                    print(f"  {knob:>7}={v:<5} winrate {r['winrate']:6.1%} "
                          f"[{r['wr_lo']:.1%},{r['wr_hi']:.1%}]  margin {r['margin']:+6.2f}"
                          f"  attacks {r['atk_cand']:.2f} vs {r['atk_ref']:.2f}"
                          f"  ({ratio:.2f}x){sig}", flush=True)
    print(f"\ndone in {(time.time()-t0)/60:.1f} min -> {out}", flush=True)


if __name__ == "__main__":
    main()
