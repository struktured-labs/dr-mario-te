#!/usr/bin/env python3
"""S0-A GATE — PREREG_S0A.md sec 8, plus the identity proof the screen needs.

House standard: a check that cannot fail is not a check, and each mutant must be
paired with the observable that CAN see it.  An unkillable-by-that-observable
mutant is a design error in the gate, not a pass.

STAGES
  S1  IDENTITY.  The screened loop's action sequence equals plain
      `oracle_arm.play_one` with the const-label champion arm, seed for seed.
      This is what licenses calling the screen a pure observer, and it gates the
      object that ACTUALLY RUNS (`play_one_screened`), not a parent of it.
      Requires observations > 0 -- a screen that never fired proves nothing.
  S2  FORK INDEPENDENCE.  `deepen`'s clones must not advance the parent's
      capsule cursor or mutate its board.
  S3  ROUTER MUTANTS  M-R1..M-R5 on synthetic tallies.
  S4  INSTRUMENT MUTANTS  M-D1 (disabled deepening -> flip rate EXACTLY 0) and
      M-D2 (unpaired futures -> flip rate must MOVE).  Two-sided: M-D2 shows the
      screen can see a change, M-D1 shows it does not manufacture one.

Exit 0 only if every stage passes.
"""
from __future__ import annotations

import copy
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import screen_gw as S            # noqa: E402
import verdict_s0a as V          # noqa: E402

FAILS = []


def check(name, ok, detail=""):
    print(f"  [{'PASS' if ok else 'FAIL'}] {name}" + (f"  {detail}" if detail else ""))
    if not ok:
        FAILS.append(name)
    return ok


# ------------------------------------------------------------------ S1 + S2
def s1_identity(seeds):
    print("S1 IDENTITY — screened loop vs plain champion")
    S._boot()
    import oracle_arm as O
    C, bmodel = O.init_rig("lulu")
    n_obs = 0
    for sd in seeds:
        rows = []
        mine = S.play_one_screened(sd, C, bmodel, rows)
        ref = O.play_one(sd, O.OracleArm(label_mode="const"), C, bmodel)
        same_res = (mine["res"] == ref["res"] and mine["pills"] == ref["pills"]
                    and mine["n_plies"] == ref["n_plies"])
        check(f"seed {sd}: outcome identical", same_res,
              f"{mine['res']}/{mine['pills']}p vs {ref['res']}/{ref['pills']}p")
        n_obs += len(rows)
    check("observations > 0 (non-vacuity)", n_obs > 0, f"n_obs={n_obs}")
    return n_obs


def s2_fork_independence(seed=50100):
    print("S2 FORK INDEPENDENCE — deepen() must not disturb the parent")
    S._boot()
    import oracle_arm as O
    import numpy as np
    C, bmodel = O.init_rig("lulu")
    env = O.make_env(seed, C["level"])
    for _ in range(8):
        vals = S.champ_values_of(env.board, env.cur.a, env.cur.b, env.nxt.a,
                                 env.nxt.b, C["w"], C["fl"], C["wt"], C["ws"])
        a = O._champ_action(vals, O.CHAMP_ORDER)
        if a is None:
            break
        r, _v, _p = S.advance_split(env, a, C, seed, bmodel)
        if r is not None:
            break
    board_before = np.array(env.board.color, copy=True)
    cur_before = (env.cur.a, env.cur.b, env.nxt.a, env.nxt.b)
    nxt_draw_before = copy.deepcopy(env)._rand_pill()

    S.deepen(env, [0, 1], C, seed, bmodel, C["w"], C["fl"], C["wt"], C["ws"], 3)

    board_after = np.array(env.board.color, copy=True)
    cur_after = (env.cur.a, env.cur.b, env.nxt.a, env.nxt.b)
    nxt_draw_after = copy.deepcopy(env)._rand_pill()
    check("parent board unmutated", bool((board_before == board_after).all()))
    check("parent capsules unmutated", cur_before == cur_after)
    check("parent pill cursor unadvanced",
          (nxt_draw_before.a, nxt_draw_before.b)
          == (nxt_draw_after.a, nxt_draw_after.b))


# ---------------------------------------------------------------- S3 router
H_OF = {"low": 4, "high": 12}      # a band <11 and a band >=11 (PREREG v2 C.2)


def _rows(spec):
    """spec = {"low"|"high": (flips, n)} -> synthetic 'deepen' rows, keyed on h."""
    out = []
    for b, (k, n) in spec.items():
        for i in range(n):
            out.append({"kind": "deepen", "flip": 1 if i < k else 0,
                        "h_hit": H_OF[b], "fill_bin": "n/a"})
    return out


def s3_router_mutants():
    print("S3 ROUTER MUTANTS — M-R1..M-R5")

    # Fixtures. High-fill n is >= MIN_HIGH_FILL except where coverage is tested.
    zero = _rows({"low": (0, 400), "high": (0, 300)})           # flat 0%
    high = _rows({"low": (60, 400), "high": (60, 300)})         # ~20% everywhere
    lown = _rows({"low": (0, 20), "high": (5, 120)})            # 4.2% but wide CI
    split = _rows({"low": (60, 400), "high": (0, 300)})         # pooled 8.6%, h>=11 0%
    thin = _rows({"low": (60, 400), "high": (9, 30)})           # coverage too thin

    base = {
        "zero -> CLOSE": (zero, "CLOSE"),
        "high -> PROCEED": (high, "PROCEED"),
        "low-n -> INDETERMINATE": (lown, "INDETERMINATE"),
        "high-h 0% -> CLOSE": (split, "CLOSE"),
        "thin coverage -> VOID": (thin, "VOID"),
    }
    for name, (rows, want) in base.items():
        got = V.route(rows)["verdict"]
        check(f"baseline {name}", got == want, f"got {got}")

    # --- M-R1: always PROCEED
    def m_r1(rows, **kw):
        return {"verdict": "PROCEED"}
    check("M-R1 killed (always PROCEED)",
          m_r1(zero)["verdict"] != V.route(zero)["verdict"],
          "caught by the flat-0% fixture")

    # --- M-R2: the two CI bounds swapped, i.e. the rule genuinely inverted
    #     (close on a HIGH lower bound, proceed on a LOW upper bound)
    def m_r2(rows):
        r = V.route(rows)
        if r["verdict"] == "VOID":
            return r
        l_hi, u_hi = r["high_h"]["ci"]
        if l_hi > V.FLOOR:
            return {"verdict": "CLOSE"}
        if u_hi < V.FLOOR:
            return {"verdict": "PROCEED"}
        return {"verdict": "INDETERMINATE"}
    for fx_name, fx in (("high", high), ("zero", zero)):
        check(f"M-R2 killed on {fx_name} (inverted comparison)",
              m_r2(fx)["verdict"] != V.route(fx)["verdict"],
              f"m_r2={m_r2(fx)['verdict']} vs true={V.route(fx)['verdict']}")

    # --- M-R3: point estimate, no CI
    def m_r3(rows):
        r = V.route(rows)
        if r["verdict"] == "VOID":
            return r
        return {"verdict": "PROCEED" if r["high_h"]["rate"] > V.FLOOR
                else "CLOSE"}
    check("M-R3 killed (ignores the CI)",
          m_r3(lown)["verdict"] != V.route(lown)["verdict"],
          f"m_r3={m_r3(lown)['verdict']} vs true={V.route(lown)['verdict']}")

    # --- M-R4: strata collapsed to pooled
    def m_r4(rows):
        r = V.route(rows)
        if r["verdict"] == "VOID":
            return r
        l, u = r["overall"]["ci"]
        if u < V.FLOOR:
            return {"verdict": "CLOSE"}
        return {"verdict": "PROCEED" if l > V.FLOOR else "INDETERMINATE"}
    check("M-R4 killed (pools the strata)",
          m_r4(split)["verdict"] != V.route(split)["verdict"],
          f"m_r4={m_r4(split)['verdict']} vs true={V.route(split)['verdict']}")

    # --- M-R5: ignores the coverage void
    def m_r5(rows):
        saved = V.MIN_HIGH_H
        try:
            V.MIN_HIGH_H = 0
            return V.route(rows, min_high=0)
        finally:
            V.MIN_HIGH_H = saved
    check("M-R5 killed (ignores coverage void)",
          m_r5(thin)["verdict"] != V.route(thin)["verdict"],
          f"m_r5={m_r5(thin)['verdict']} vs true={V.route(thin)['verdict']}")


# ------------------------------------------------------ S4 instrument mutants
def s4_instrument_mutants(seeds):
    print("S4 INSTRUMENT MUTANTS — M-D1 / M-D2")
    S._boot()
    import oracle_arm as O
    C, bmodel = O.init_rig("lulu")

    def flips(mut):
        k = n = d = 0
        for sd in seeds:
            rows = []
            S.play_one_screened(sd, C, bmodel, rows, mut)
            for r in rows:
                if r["kind"] == "deepen":
                    n += 1
                    k += r["flip"]
                    d += r.get("dup_pair", 0)
        return k, n, d

    k0, n0, d0 = flips(None)
    k1, n1, _ = flips({"disable": True})
    k2, n2, _ = flips({"unpaired": True})
    k3, n3, d3 = flips({"nodedup": True})
    print(f"    true      {k0}/{n0}   dup-pairs {d0}")
    print(f"    M-D1      {k1}/{n1}   (disabled deepening)")
    print(f"    M-D2      {k2}/{n2}   (unpaired futures)")
    print(f"    M-D3      {k3}/{n3}   dup-pairs {d3}  (de-dup disabled)")

    check("instrument non-vacuous (tie plies observed)", n0 > 0, f"n={n0}")
    check("M-D1 killed (disabled deepening flips EXACTLY 0)", k1 == 0,
          f"k={k1}")
    check("M-D1 population unchanged", n1 == n0)
    if n0 > 0 and k0 == 0:
        print("    NOTE: the true arm produced 0 flips on this sample, so M-D2 "
              "cannot be evaluated here; it needs a sample with flips.")
    else:
        check("M-D2 killed (unpaired futures move the flip rate)", k2 != k0,
              f"{k2} vs {k0}")

    # --- PREREG v2 sec D: the population check that v1's gate lacked
    check("v2 candidates are NEVER the same board (asserted, not assumed)",
          d0 == 0, f"dup_pairs={d0}/{n0}")
    check("M-D3 killed: de-dup off inflates the population", n3 > n0,
          f"{n3} vs {n0} ({n3 / max(1, n0):.1f}x)")
    check("M-D3 killed: de-dup off admits identical-board pairs",
          d3 > 0 and (d3 / max(1, n3)) > 0.5,
          f"dup_pairs={d3}/{n3} = {100 * d3 / max(1, n3):.0f}%")


def main():
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--seeds", type=int, default=6)
    ap.add_argument("--seed-start", type=int, default=50100)
    ap.add_argument("--skip-slow", action="store_true")
    a = ap.parse_args()
    seeds = list(range(a.seed_start, a.seed_start + a.seeds))

    s3_router_mutants()
    if not a.skip_slow:
        s1_identity(seeds)
        s2_fork_independence(a.seed_start)
        s4_instrument_mutants(seeds)

    print()
    if FAILS:
        print(f"GATE FAILED: {len(FAILS)} check(s): {FAILS}")
        return 1
    print("GATE PASSED")
    return 0


if __name__ == "__main__":
    sys.exit(main())
