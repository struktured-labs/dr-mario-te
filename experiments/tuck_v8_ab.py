#!/usr/bin/env python3
"""Paired-seed A/B: v8 (no tuck) vs v8+tuck, in the fast simulator, on the REAL NES stream.

WHAT THIS PRICES, STATED EXACTLY
--------------------------------
The cart flag DRTUCK switches on a 6502 EXECUTOR: while the capsule is high it steers to an
APPROACH column, and at/below a trigger row it steers to the FINAL column so the DAS slide
carries it under a lip. The DECISION (which tuck, and whether it is worth it -- the theta
gate, theta*=400) lives in the COPRO FIRMWARE, not on the cart. So there is no theta to set
here, and this rig cannot reproduce the firmware's theta curve.

What it CAN price is the thing the cart flag buys: access to the tuck vocabulary, restricted
to the placements THIS executor can actually perform. That is `DRTUCK_EXEC=1` in tuck_ab --
the one-horizontal-switch reachability model. Arm C (EXEC=0, full gravity-legal tuck space)
is carried as the UPPER BOUND, i.e. what a perfect executor would be worth; the cart is not
entitled to it.

Arms (identical seeds, identical everything else):
  A  tuck OFF                      = v8
  B  tuck ON, executor-reachable   = v8+tuck        <-- the ship question
  C  tuck ON, full tuck space      = upper bound (not shippable, for context only)

Outputs: clear rate per arm; median/mean pills; PAIRED pill delta on seeds where BOTH arms
cleared (censoring-free) with a percentile-bootstrap CI; fires/game.
"""
import os, sys, json, argparse, random, statistics as st
from concurrent.futures import ProcessPoolExecutor, as_completed

ROOT = "/home/struktured/projects/dr_mario_rl"
sys.path.insert(0, ROOT + "/tmp/champion")


def boot_ci(xs, stat=st.mean, n=10000, seed=12345):
    if not xs:
        return (float("nan"), float("nan"))
    rng = random.Random(seed)
    k = len(xs)
    reps = sorted(stat([xs[rng.randrange(k)] for _ in range(k)]) for _ in range(n))
    return reps[int(0.025 * n)], reps[int(0.975 * n)]


# ⚠ SEED SPACE. The NES pill LFSR gives seeds 2k and 2k+1 the SAME capsule stream (verified
# here: seq(2)==seq(3), seq(4)==seq(5), seq(100)==seq(101); 0 and 1 differ). The board layout
# still differs, so range(N) is N distinct GAMES -- but only N/2 distinct STREAMS, i.e. the
# rows come in correlated pairs and a naive bootstrap over them is too narrow. Use stride 2 so
# every game has its own stream AND its own board. Start at 2: seed 1 is the documented
# degenerate constant-(1,1) LFSR state.
def seed_list(n):
    return [2 * (i + 1) for i in range(n)]


def run_arm(name, tuck, execonly, seeds, level, workers, P, guard=False):
    os.environ["DRTUCK_EXEC"] = "1" if execonly else "0"
    os.environ["DRTUCK_GUARD"] = "1" if guard else "0"
    os.environ["DRTUCK_GATE"] = "0"
    os.environ["DRTUCK_V2"] = "0"
    import tuck_ab as TA          # imported AFTER env is set; workers inherit via fork
    rows = []
    with ProcessPoolExecutor(max_workers=workers, initializer=TA._init,
                             initargs=(level, tuck, 1, P)) as ex:      # nes=1: REAL stream
        futs = [ex.submit(TA.play, s) for s in seed_list(seeds)]
        for f in as_completed(futs):
            rows.append(f.result())
    rows.sort(key=lambda r: r["seed"])
    return name, rows


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--seeds", type=int, default=240)
    ap.add_argument("--level", type=int, default=11)
    ap.add_argument("--workers", type=int, default=4)
    ap.add_argument("--P", type=int, default=12)
    ap.add_argument("--out", default="/home/struktured/projects/dr-mario-v8-wt/tmp/tuck_v8_ab.json")
    a = ap.parse_args()

    # D = the ship question for task #102: executor-reachable tucks, with the CART-SIDE
    # fall-budget guard applied. A veto is not a different tuck, it is NO tuck -- the executor
    # reads TUCK_C2=$FF and steers straight to the final column -- so D can only ever lose
    # value relative to B, never gain it. That is exactly what we are pricing: how much of
    # B's -4.16 pills survives the safety.
    arms = [("A_v8_notuck", 0, False, False), ("B_v8tuck_exec", 1, True, False),
            ("D_v8tuck_guard", 1, True, True), ("C_upper_full", 1, False, False)]
    R = {}
    for name, tuck, execonly, guard in arms:
        _, rows = run_arm(name, tuck, execonly, a.seeds, a.level, a.workers, a.P, guard)
        R[name] = rows
        print(f"[done] {name}: n={len(rows)} clear={sum(r['won'] for r in rows)/len(rows):.1%} "
              f"medpills={st.median([r['pills'] for r in rows]):.1f} "
              f"fires/game={st.mean([r['fired'] for r in rows]):.2f} "
              f"vetoed/game={st.mean([r.get('vetoed',0) for r in rows]):.1f} "
              f"offered/game={st.mean([r.get('offered',0) for r in rows]):.1f}", flush=True)

    print(f"\n=== v8 vs v8+tuck, REAL NES capsules, L{a.level}, paired n={a.seeds} ===")
    print(f"{'arm':>16} {'clear':>8} {'medpills':>9} {'meanpills':>10} {'fires/g':>8}")
    for name, rows in R.items():
        print(f"{name:>16} {sum(r['won'] for r in rows)/len(rows):8.1%} "
              f"{st.median([r['pills'] for r in rows]):9.1f} "
              f"{st.mean([r['pills'] for r in rows]):10.1f} "
              f"{st.mean([r['fired'] for r in rows]):8.2f}")

    base = R["A_v8_notuck"]
    summary = {"seeds": a.seeds, "level": a.level, "arms": {}}
    for name, rows in R.items():
        summary["arms"][name] = {
            "clear": sum(r["won"] for r in rows) / len(rows),
            "med_pills": st.median([r["pills"] for r in rows]),
            "mean_pills": st.mean([r["pills"] for r in rows]),
            "fires_per_game": st.mean([r["fired"] for r in rows]),
        }
        if name == "A_v8_notuck":
            continue
        # PAIRED, both-clear only: censoring-free comparison of pills-to-clear
        d = [rows[i]["pills"] - base[i]["pills"]
             for i in range(len(rows)) if rows[i]["won"] and base[i]["won"]]
        lo, hi = boot_ci(d)
        wins = sum(1 for x in d if x < 0)
        losses = sum(1 for x in d if x > 0)
        # clear-rate delta, paired (McNemar-style discordant counts)
        b_only = sum(1 for i in range(len(rows)) if rows[i]["won"] and not base[i]["won"])
        a_only = sum(1 for i in range(len(rows)) if base[i]["won"] and not rows[i]["won"])
        print(f"\n  {name} vs A_v8_notuck")
        print(f"    paired pills (both cleared, n={len(d)}): mean {st.mean(d):+.2f} "
              f"[95% CI {lo:+.2f}, {hi:+.2f}]  median {st.median(d):+.1f}  W/L {wins}/{losses}")
        print(f"    clear-rate discordant: {name}-only {b_only}, A-only {a_only}")
        summary["arms"][name].update({
            "paired_n": len(d), "paired_mean": st.mean(d) if d else None,
            "paired_ci": [lo, hi], "paired_median": st.median(d) if d else None,
            "wins": wins, "losses": losses, "clear_only_B": b_only, "clear_only_A": a_only})

    with open(a.out, "w") as f:
        json.dump({"summary": summary,
                   "rows": {k: [{kk: vv for kk, vv in r.items() if kk != "seg"} for r in v]
                            for k, v in R.items()}}, f, indent=1)
    print(f"\nwrote {a.out}")


if __name__ == "__main__":
    main()
