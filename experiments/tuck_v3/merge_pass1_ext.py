#!/usr/bin/env python3
"""Merges pass-1's L11 n=120 (seeds 0-119) with the theta=150 seed extension's n=120
(seeds 120-239) into a combined n=240 statistic -- the power-question decisive test
(team-lead directive): does the pooled CI exclude 0 in the tuck-favourable direction,
even though pass-1 alone (n=120) washed?

Re-derives the statistics from the MERGED RAW per-seed results (never combines two
summary dicts directly -- the bootstrap CI and sign test are not simply additive
across sub-batches), the same approach ab_root_firmware.run_pass1 already uses for
its own L20 0-79 + 80-239 merge.
"""
import sys
import os
import json
import statistics as st

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import ab_root_firmware as AF

PASS1_JSON = ("/tmp/claude-1000/-home-struktured-projects-dr-mario-rl/"
              "02493363-c6af-4da9-9c47-58ceef8174b6/scratchpad/tuck_repro/pass1_out/pass1_L11.json")
EXT_JSON = ("/tmp/claude-1000/-home-struktured-projects-dr-mario-rl/"
            "02493363-c6af-4da9-9c47-58ceef8174b6/scratchpad/tuck_repro/pass1_ext_out/ext_L11.json")


def _load(path):
    with open(path) as fh:
        d = json.load(fh)
    off = {r["seed"]: r for r in d["off"]}
    on = {r["seed"]: r for r in d["on"]}
    return off, on


def main():
    off_a, on_a = _load(PASS1_JSON)
    off_b, on_b = _load(EXT_JSON)
    assert not (set(off_a) & set(off_b)), "seed ranges overlap -- not a clean extension"
    off = {**off_a, **off_b}
    on = {**on_a, **on_b}

    all_seeds = sorted(set(off) & set(on))
    both = [s for s in all_seeds if off[s]["won"] and on[s]["won"]]
    d = [on[s]["pills"] - off[s]["pills"] for s in both]
    lo, hi = AF.boot_ci(d)
    better = sum(1 for x in d if x < 0)
    worse = sum(1 for x in d if x > 0)
    c_off = sum(off[s]["won"] for s in all_seeds) / len(all_seeds)
    c_on = sum(on[s]["won"] for s in all_seeds) / len(all_seeds)
    disc = [(off[s]["won"], on[s]["won"]) for s in all_seeds if off[s]["won"] != on[s]["won"]]
    won_only_on = sum(1 for o, n in disc if n)
    won_only_off = len(disc) - won_only_on
    p_clear = AF.sign_test_p(won_only_on, won_only_off)
    fires = [on[s]["fired"] for s in all_seeds]

    verdict = "REAL (CI excludes 0)" if (hi < 0 or lo > 0) else "WASH (CI spans 0)"
    print(f"=== POOLED n={len(all_seeds)} (pass-1 seeds 0-119 + extension seeds 120-239) ===")
    print(f"1. PAIRED PILLS (both cleared, n={len(both)}/{len(all_seeds)})")
    print(f"   mean delta {st.mean(d) if d else float('nan'):+.2f}   95% CI [{lo:+.2f}, {hi:+.2f}]")
    print(f"   better {better} / worse {worse} / tie {len(d) - better - worse}   => {verdict}")
    print(f"2. CLEAR RATE  off {c_off:.1%} -> on {c_on:.1%}   discordant {len(disc)} "
          f"(tuck-only wins {won_only_on}, tuck-only losses {won_only_off}, sign-test p={p_clear:.4f})")
    print(f"3. FIRES/GAME  {st.mean(fires) if fires else 0.0:.2f}")
    print()
    if hi < 0 or lo > 0:
        print("VERDICT: firmware transfer CONFIRMED at n=240 -- the mirror predicted it, "
              "power found it. Proceed to the L20 check and stage 3.")
    else:
        print("VERDICT: pooled n=240 STILL washes. A genuine mirror-vs-firmware behavioral "
              "gap, not just a power issue -- worth dissecting (trajectory compounding from "
              "the 2/20 decision-level flips is the lead theory).")


if __name__ == "__main__":
    main()
