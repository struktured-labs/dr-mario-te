#!/usr/bin/env python3
"""Head-to-head VS win rate between two eval-constant sets, with an honest paired CI.

WHY THE STATS ARE SHAPED THIS WAY
---------------------------------
The two players share the seed's capsule stream but get different virus layouts, so BOARD
LUCK dominates the variance. Two devices control it:

  * SIDE SWAP. Every seed is played twice, candidate as P0 and as P1. With identical arms
    those two matches are the SAME match, so exactly one side wins and the pair scores 0.5
    by construction -- the self-vs-self "sanity check" in the old `selfplay.py` was therefore
    vacuous, it could not fail. With different arms the swap cancels the layout advantage.

  * SEED-LEVEL PAIRING. The two matches of a seed are NOT independent, so a CI over
    2*n_seeds matches understates variance. The unit of analysis is the SEED, scoring
    s = (win_as_P0 + win_as_P1) / 2 in {0, 0.5, 1}. The CI is a bootstrap over seeds.

REPORTED: win rate (primary, the objective) and virus margin (secondary, lower variance,
used to steer the search). Margin is only a legitimate search signal if it agrees with win
rate; `--check-margin` measures that agreement instead of assuming it.

Draws (both stall at the pill cap) score 0.5 and are reported separately -- a candidate that
wins by turning losses into stalls is not winning.
"""
from __future__ import annotations
import sys, os, json, time, argparse, random
import statistics as st
from concurrent.futures import ProcessPoolExecutor

ROOT = "/home/struktured/projects/dr_mario_rl"
HERE = os.path.dirname(os.path.abspath(__file__))
for p in (HERE, ROOT + "/tmp/combo_term", ROOT + "/tmp/pillrng",
          ROOT + "/.claude/worktrees/faithful-sim/src"):
    if p not in sys.path:
        sys.path.insert(0, p)

from vs_env_exact import play_match as _play_exact
# ★ The ROM-rule path is the ONE sanctioned harness, imported directly. `vs_env_rom` was a
# second match loop (opening-book's); it had the floating-garbage bug and was deleted --
# two rigs for one rule is the fragmentation that let five mechanics bugs coexist.
import sys as _sys
_sys.path.insert(0, "/home/struktured/projects/dr_mario_rl/tmp/vs_aware")
import vs_harness as _H


def _play_rom(seed, f0, f1, level=11, max_pills=300, nes_pills=True, garbage=True):
    """vs_harness deciders take (board, cur, nxt, opp_board) and `blind()` wants an object
    with `.choose`; this module passes plain 3-arg callables, so adapt at the boundary."""
    class _B:
        def __init__(self, fn): self._fn = fn
        def choose(self, b, c, n): return self._fn(b, c, n)
    return _H.play_match(seed, _H.blind(_B(f0)), _H.blind(_B(f1)), level=level,
                         max_pills=max_pills, nes_pills=nes_pills, garbage=garbage)


def _play(cfg, seed, f0, f1):
    """Dispatch to the harness rev named by cfg['rule'].

    ★ 'rom' IS THE CORRECT ONE. The 'exact' rev (mine, 2026-07-31) counted only lines
    cleared in the SAME step. The ROM's comboCounter SUMS ACROSS CASCADE STEPS and is never
    reset inside the cascade, so a cascade of two SINGLE lines attacks -- and that case is
    85% of all real attacks. Mesen-confirmed on the real ROM. 'exact' therefore fires ~6.7x
    too rarely and every number taken through it is provisional.
    See memory dr-mario-rom-attack-rule / tmp/vs_aware/rom_attack_rule.py.
    """
    if cfg.get("rule", "rom") == "rom":
        return _play_rom(seed, f0, f1, level=cfg["level"], max_pills=cfg["max_pills"],
                         nes_pills=cfg["nes_pills"], garbage=cfg.get("garbage", True))
    return _play_exact(seed, f0, f1, level=cfg["level"], max_pills=cfg["max_pills"],
                       nes_pills=cfg["nes_pills"], chain_mode=cfg["chain_mode"],
                       garbage=cfg.get("garbage", True))

# The two reference arms, pinned BY VALUE. Memory `dr-mario-eval-h2h-threeway` records a
# naming hazard: "winner" has meant two different arms. These dicts are the contract.
R47    = {"vrdy": 24, "buried": 30, "rdyext": 12, "setup": 60, "matched": 60, "poll": 6,
          "maxh": 12, "holes": 20, "toprisk": 90, "spawn": 150}
WINNER = {"vrdy": 8,  "buried": 48, "rdyext": 8,  "setup": 32, "matched": 48, "poll": 6,
          "maxh": 12, "holes": 20, "toprisk": 90, "spawn": 150}
LNK1   = dict(WINNER, arm="lnk1")     # winner weights, link-faithful cap-1 physics
LNKFIX = dict(WINNER, arm="lnkfix")   # winner weights, fixpoint cascade resolution
CHAIN180 = dict(WINNER, arm="chain180")   # fixpoint + chain-depth reward w_chain=180
CHAIN360 = dict(WINNER, arm="chain360")
ARMS = {"r47": R47, "winner": WINNER, "lnk1": LNK1, "lnkfix": LNKFIX,
        "chain180": CHAIN180, "chain360": CHAIN360}

_CFG = {}


def _init(cfg):
    global _CFG
    import fast_rtl_x as F
    F.warmup_delta(topk2=cfg.get("topk2", 8))
    # link-physics arms need their own numba warmup, once per worker process
    arms = [c.get("arm", "ship") for c in (cfg.get("cand") or {}, cfg.get("ref") or {})]
    if any(a in ("lnk1", "lnkfix") for a in arms):
        import cascade_link_x as L
        L.warmup_linked(topk2=cfg.get("topk2", 8))
    if any(a.startswith("chain") for a in arms):
        import cascade_chain_x as C
        C.warmup_chain(topk2=cfg.get("topk2", 8))
    _CFG = cfg


def idx_map():
    """name -> weight-vector index. THE SINGLE SOURCE OF TRUTH for this mapping.

    ⚠ THIS EXISTED IN TWO COPIES AND THEY SILENTLY DIVERGED (2026-07-31). `sweep_knobs`
    grew vbonus/cross/wvir; this one did not. The L20 vbonus holdout therefore applied NO
    weight change at all and returned a completely plausible "NOT CONFIRMED" for a
    candidate it had never actually tested. Nothing raised an error -- a candidate key that
    is not in the map is simply ignored.

    Caught by the `decisive` diagnostic: "moved 0% of seeds" with attack rates identical to
    four significant figures is impossible for a real weight change. Keep ONE copy, and
    keep that diagnostic in the output.
    """
    import fast_rtl_x as F
    return {"vrdy": F.R_VRDY, "buried": F.R_BURIED, "rdyext": F.R_RDYEXT,
            "setup": F.R_SETUP, "matched": F.R_MATCHED, "poll": F.R_POLL,
            "maxh": F.R_MAXH, "holes": F.R_HOLES, "toprisk": F.R_TOPRISK,
            "spawn": F.R_SPAWN, "vbonus": F.R_VBONUS, "cross": F.R_CROSS,
            "wvir": F.R_WVIR}


def _mk(cand, topk2=8):
    """Build a decider from a constant dict.

    `arm` selects the SEARCH PHYSICS and is not a weight (it is popped before the idx_map
    check, so the unknown-key guard still catches typo'd constants):
      "ship"   (default) delta-backed shipped leaf, compact gravity, cap-1.
      "lnk1"   cascade-search's LINK-FAITHFUL gravity, still cap-1 (maxpass=1).
      "lnkfix" link-faithful + FIXPOINT cascade resolution (maxpass=0).

    ★ Score lnk1, not lnkfix, per cascade-search: making the search SEE chains makes it
    AVOID them, and chains are ~90% of ROM attacks, so lnkfix sends 18-23% LESS garbage.
    lnk1 goes the other way (+7% attacks, +37% doubles) and took clear rate 96.7% -> 100%
    over 360 games. Their pills claim did NOT replicate; robustness + attack rate did.
    """
    import fast_rtl_x as F
    cand = dict(cand)
    arm = cand.pop("arm", "ship")
    w, fl = F.variant("winner")
    m = idx_map()
    unknown = set(cand) - set(m)
    if unknown:                     # fail loud rather than silently ignoring a knob
        raise KeyError(f"candidate has constants not in idx_map(): {sorted(unknown)}")
    for k, idx in m.items():
        if k in cand:
            w[idx] = float(cand[k])
    if arm.startswith("chain"):
        # cascade-search's explicit chain-depth reward, `imm += w_chain * (chain - 1)`.
        # ★ Built on the FIXPOINT leaf (maxpass=0) BY DESIGN, so a chain term cannot buy
        # phantom chains. Its correct internal baseline is therefore LNKFIX, not lnk1 --
        # scoring it against lnk1 confounds the chain term with the cap-1-vs-fixpoint
        # difference, which my own direct run measured at ~7 points.
        import cascade_chain_x as C
        return C.ChainRewardD3Decider(w, fl, topk2=topk2, maxpass=0,
                                      w_chain=int(arm[5:]))
    if arm != "ship":
        import cascade_link_x as L
        if arm not in ("lnk1", "lnkfix"):
            raise KeyError(f"unknown arm {arm!r}; want ship|lnk1|lnkfix|chain<N>")
        return L.LinkedD3Decider(w, fl, topk2=topk2,
                                 maxpass=1 if arm == "lnk1" else 0)
    return F.FastShipD3DeciderEHDelta(w, fl, topk2=topk2)


def _one(job):
    """Play one match. `job` = (seed, swap). Returns the CANDIDATE's outcome."""
    seed, swap = job
    cfg = _CFG
    cand = _mk(cfg["cand"], cfg["topk2"])
    ref = _mk(cfg["ref"], cfg["topk2"])
    f = lambda d: (lambda b, c, n: d.choose(b, c, n))
    a, b = (cand, ref) if not swap else (ref, cand)
    r = _play(cfg, seed, f(a), f(b))
    side = 0 if not swap else 1
    win = 1.0 if r["winner"] == side else (0.0 if r["winner"] >= 0 else 0.5)
    margin = r["margin"] if side == 0 else -r["margin"]
    sent_c, sent_r = attacks_sent(r, side), attacks_sent(r, 1 - side)
    return {"seed": seed, "swap": swap, "win": win, "margin": margin,
            "reason": r["reason"], "draw": r["winner"] < 0,
            "atk_cand": sent_c, "atk_ref": sent_r,
            "pills_cand": r["pills"][side]}


def attacks_sent(r, side):
    """Attacks SENT by `side`, normalising over harness revs. ONE definition, on purpose.

    ⚠ THE SCHEMAS DISAGREE AND THE INDEX FLIPS. `vs_harness` returns `attacks` = releases
    LANDED ON each player (RECEIVED), so what a side SENT is the OPPONENT's entry, [1-side].
    `vs_env_exact` returns `attacks_sent`, already sender-indexed, [side]. Reading the wrong
    one silently INVERTS every attack-rate number without raising anything -- and I had
    already written the two-copies lesson down before making the same mistake again here in
    sweep_knobs. Both callers now use this.
    """
    if "attacks_sent" in r:
        return r["attacks_sent"][side]
    return r["attacks"][1 - side]


def boot_ci(vals, iters=10000, alpha=0.05, seed=12345):
    """Percentile bootstrap over the SEED-level scores."""
    if not vals:
        return (float("nan"), float("nan"))
    rng = random.Random(seed)
    n = len(vals)
    means = []
    for _ in range(iters):
        means.append(sum(vals[rng.randrange(n)] for _ in range(n)) / n)
    means.sort()
    lo = means[int(alpha / 2 * iters)]
    hi = means[min(iters - 1, int((1 - alpha / 2) * iters))]
    return lo, hi


def run(cand, ref, seeds, workers=8, level=11, max_pills=300, nes_pills=True,
        chain_mode="first", topk2=8, per_match=None, garbage=True, rule="rom"):
    """Play `seeds` from both sides. Returns a summary dict with seed-paired stats."""
    cfg = {"cand": cand, "ref": ref, "level": level, "max_pills": max_pills,
           "nes_pills": nes_pills, "chain_mode": chain_mode, "topk2": topk2,
           "garbage": garbage, "rule": rule}
    jobs = [(s, sw) for s in seeds for sw in (0, 1)]
    t0 = time.time()
    with ProcessPoolExecutor(max_workers=workers, initializer=_init, initargs=(cfg,)) as ex:
        rows = list(ex.map(_one, jobs, chunksize=1))
    dt = time.time() - t0

    by_seed = {}
    for r in rows:
        by_seed.setdefault(r["seed"], []).append(r)
    wr_seed, mg_seed = [], []
    for s, rs in by_seed.items():
        wr_seed.append(sum(x["win"] for x in rs) / len(rs))
        mg_seed.append(sum(x["margin"] for x in rs) / len(rs))

    lo, hi = boot_ci(wr_seed)
    mlo, mhi = boot_ci(mg_seed)

    # ★ HOW OFTEN DID THE KNOB MATTER AT ALL? With identical arms every seed scores exactly
    # 0.5 (each side wins once under the swap), so a seed scoring 0 or 1 is one where the
    # constant actually changed the outcome. This separates two very different 51%s: a knob
    # that moves 8% of seeds and wins 63% of those, versus one that moves 90% and wins 51%.
    # It also explains the CI widths -- inert knobs give tight CIs because most paired
    # differences are exactly zero, which is NOT the same as being precisely measured as good.
    dec = [w for w in wr_seed if w != 0.5]
    decisive = len(dec) / len(wr_seed)
    wr_dec = (sum(dec) / len(dec)) if dec else float("nan")
    dlo, dhi = boot_ci(dec) if dec else (float("nan"), float("nan"))
    if per_match:
        with open(per_match, "w") as fh:
            for r in rows:
                fh.write(json.dumps(r) + "\n")
    return {
        "n_seeds": len(by_seed), "n_matches": len(rows),
        "winrate": sum(wr_seed) / len(wr_seed), "wr_lo": lo, "wr_hi": hi,
        "margin": st.mean(mg_seed), "mg_lo": mlo, "mg_hi": mhi,
        "draws": sum(1 for r in rows if r["draw"]),
        "atk_cand": sum(r["atk_cand"] for r in rows) / len(rows),
        "atk_ref": sum(r["atk_ref"] for r in rows) / len(rows),
        "pills_cand": st.mean([r["pills_cand"] for r in rows]),
        "sec_per_match": dt / len(rows) * workers, "wall_s": dt,
        "decisive": decisive, "wr_decisive": wr_dec,
        "wr_dec_lo": dlo, "wr_dec_hi": dhi,
        "wr_seed": wr_seed, "mg_seed": mg_seed,
    }


def fmt(tag, r):
    return (f"{tag:<26} winrate {r['winrate']:6.1%}  95% CI [{r['wr_lo']:.1%}, {r['wr_hi']:.1%}]"
            f"   margin {r['margin']:+6.2f} [{r['mg_lo']:+.2f}, {r['mg_hi']:+.2f}]"
            f"   n={r['n_seeds']} seeds / {r['n_matches']} matches"
            f"   draws {r['draws']}  atk {r['atk_cand']:.2f}v{r['atk_ref']:.2f}"
            + (f"   moved {r['decisive']:.0%} of seeds, won {r['wr_decisive']:.1%} of those"
               f" [{r['wr_dec_lo']:.1%},{r['wr_dec_hi']:.1%}]" if "decisive" in r else ""))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--cand", default="winner")
    ap.add_argument("--ref", default="r47")
    ap.add_argument("--seed0", type=int, default=400)
    ap.add_argument("--seeds", type=int, default=60)
    ap.add_argument("--workers", type=int, default=8)
    ap.add_argument("--level", type=int, default=11)
    ap.add_argument("--max-pills", type=int, default=300)
    ap.add_argument("--uniform", action="store_true", help="uniform capsules (CONTRAST ONLY)")
    ap.add_argument("--chain-mode", default="first", choices=("first", "all"))
    ap.add_argument("--rule", default="rom", choices=("rom", "exact"),
                    help="rom = ROM-true cascade-summing rule (CORRECT); exact = the "
                         "superseded simultaneous-only rev, kept only for comparison")
    ap.add_argument("--no-garbage", action="store_true",
                    help="count attacks but never deliver them -- the solo-race control")
    ap.add_argument("--out", default=None)
    a = ap.parse_args()

    cand = ARMS[a.cand] if a.cand in ARMS else json.loads(a.cand)
    ref = ARMS[a.ref] if a.ref in ARMS else json.loads(a.ref)
    seeds = list(range(a.seed0, a.seed0 + a.seeds))
    r = run(cand, ref, seeds, workers=a.workers, level=a.level, max_pills=a.max_pills,
            nes_pills=not a.uniform, chain_mode=a.chain_mode, per_match=a.out,
            garbage=not a.no_garbage, rule=a.rule)
    cap = "UNIFORM (contrast only)" if a.uniform else "REAL NES capsules"
    gb = "garbage OFF (solo-race control)" if a.no_garbage else "garbage ON"
    print(f"L{a.level}  {cap}  {gb}  rule={a.rule}  "
          f"seeds {a.seed0}..{a.seed0+a.seeds-1}")
    print(fmt(f"{a.cand} vs {a.ref}", r))
    print(f"  {r['sec_per_match']:.2f} s/match/core, {r['wall_s']:.0f}s wall at {a.workers} workers")
    if a.out:
        json.dump({k: v for k, v in r.items() if k not in ("wr_seed", "mg_seed")},
                  open(a.out + ".summary.json", "w"), indent=2)


if __name__ == "__main__":
    main()
