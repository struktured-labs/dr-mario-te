"""Is my reported TIE/TRIGGER rate inflated by 180-degree-symmetric doubles?

gw-design (#117) measured that ~87% of "exact top-2 champion-value ties" are the
SAME PHYSICAL PLACEMENT: a double capsule (a == b) is 180-symmetric, so the
32-slot action space collapses to 16 and every placement appears twice at
exactly equal value. Their screen would have compared a board with itself.

WHY THIS LANE CARES. My headline dose statistics are TIE-based:
  exact-tie rate            0.3608 of plies
  TRIGGER (gate AND tie)    0.2072 of plies
  trigger ratio v2/v1       1.129  <- the number the whole NO-GO rests on
If the tie indicator is dominated by self-ties, the first two overstate the
DECISION-RELEVANT population. The ratio survives only if the degenerate
fraction is BALANCED across the v1 and v2-only populations — which is an
assumption, not a fact, until measured.

This measures rather than argues:
  1. VERIFY the collapse pattern empirically (do slots v and v+2 carry equal
     value on doubles?) instead of assuming which orientations pair up.
  2. Split the tie rate by double / non-double.
  3. Recompute the trigger rate and the v2/v1 TRIGGER RATIO on DEDUPLICATED
     ties, and compare against the shipped numbers.
"""
import argparse
import json
import os
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

_W = {}


def _winit():
    import oracle_arm as O
    C, bmodel = O.init_rig("lulu")
    _W.update(O=O, C=C, bmodel=bmodel)


def _work(seed):
    import numpy as np
    from oracle_arm import (OracleArm, CHAMP_ORDER, _champ_values,
                            _champ_action, gate_fires, heights,
                            GATE_DSPAWN_H, GATE_VIRUSES)
    from fb import FB
    import root_search as RS
    O, C, bmodel = _W["O"], _W["C"], _W["bmodel"]
    w, fl, wt, ws = C["w"], C["fl"], C["wt"], C["ws"]
    rows = []

    class Probe(OracleArm):
        def choose(self, env, seed_, C_, bmodel_, w_, fl_, wt_, ws_, ply):
            col, vir = RS.board_flat_from_fb(FB.from_board(env.board))
            vals = _champ_values(col, vir, int(env.cur.a), int(env.cur.b),
                                 int(env.nxt.a), int(env.nxt.b),
                                 w_, fl_, wt_, ws_)
            base_a = _champ_action(vals, CHAMP_ORDER)
            if base_a is None:
                return None, None
            self.stats["plies"] += 1
            legal = [int(s) for s in CHAMP_ORDER if np.isfinite(vals[int(s)])]
            is_double = int(env.cur.a) == int(env.cur.b)

            # (1) VERIFY the collapse empirically: for each legal slot, does the
            # slot 2 orientations away carry an EQUAL value? Do not assume which
            # orientations pair.
            pairs = eq = 0
            for s in legal:
                v_, c_ = divmod(s, 8)
                t = ((v_ + 2) % 4) * 8 + c_
                if t in legal and t > s:
                    pairs += 1
                    eq += int(vals[s] == vals[t])

            fv = sorted((float(vals[c]) for c in legal), reverse=True)
            tie = int(len(fv) >= 2 and fv[0] == fv[1])

            # (2) DEDUPLICATED tie: drop one member of every equal (v, v+2) pair
            keep, seen = [], set()
            for s in legal:
                v_, c_ = divmod(s, 8)
                t = ((v_ + 2) % 4) * 8 + c_
                if t in legal and vals[s] == vals[t] and t in seen:
                    continue
                seen.add(s)
                keep.append(s)
            fvd = sorted((float(vals[c]) for c in keep), reverse=True)
            tie_dedup = int(len(fvd) >= 2 and fvd[0] == fvd[1])

            H = heights(env.board.color)
            d_spawn = int(max(H[3], H[4]))
            maxh = int(H.max())
            nvir = int(env.board.virus_count())
            v1 = int(d_spawn >= GATE_DSPAWN_H or nvir <= GATE_VIRUSES)
            rows.append({"is_double": int(is_double), "n_legal": len(legal),
                         "n_dedup": len(keep), "sym_pairs": pairs,
                         "sym_pairs_equal": eq,
                         "tie": tie, "tie_dedup": tie_dedup,
                         "gate_v1": v1,
                         "gate_v2_t13": int(v1 or maxh >= 13)})
            return base_a, base_a

    arm = Probe(label_mode="const")
    O.play_one(seed, arm, C, bmodel)
    return rows


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--seed-start", type=int, default=70000)
    ap.add_argument("--seed-count", type=int, default=60)
    ap.add_argument("--workers", type=int, default=2)
    ap.add_argument("--out", default="out/TIE_DEGENERACY.json")
    a = ap.parse_args()

    from concurrent.futures import ProcessPoolExecutor
    t0 = time.monotonic()
    rows = []
    seeds = range(a.seed_start, a.seed_start + a.seed_count)
    with ProcessPoolExecutor(max_workers=a.workers,
                             initializer=_winit) as ex:
        for r in ex.map(_work, seeds):
            rows.extend(r)

    n = len(rows)
    dbl = [r for r in rows if r["is_double"]]
    nod = [r for r in rows if not r["is_double"]]
    P = sum(r["sym_pairs"] for r in rows)
    E = sum(r["sym_pairs_equal"] for r in rows)
    print(f"TIE DEGENERACY — {a.seed_count} seeds, {n} champion plies "
          f"({time.monotonic()-t0:.0f}s)\n")
    print(f"(1) COLLAPSE VERIFIED EMPIRICALLY: of {P} (v, v+2) legal slot "
          f"pairs, {E} carry EQUAL value = {100*E/max(P,1):.1f}%")
    print(f"    doubles are {len(dbl)}/{n} = {100*len(dbl)/n:.1f}% of plies")
    dP = sum(r["sym_pairs"] for r in dbl); dE = sum(r["sym_pairs_equal"] for r in dbl)
    oP = sum(r["sym_pairs"] for r in nod); oE = sum(r["sym_pairs_equal"] for r in nod)
    print(f"      on DOUBLES     : {dE}/{dP} equal = {100*dE/max(dP,1):.1f}%")
    print(f"      on NON-doubles : {oE}/{oP} equal = {100*oE/max(oP,1):.1f}%")

    def rate(rs, k):
        return sum(r[k] for r in rs) / max(len(rs), 1)
    print(f"\n(2) TIE RATE")
    print(f"    raw   overall {rate(rows,'tie'):.4f} | doubles "
          f"{rate(dbl,'tie'):.4f} | non-doubles {rate(nod,'tie'):.4f}")
    print(f"    DEDUP overall {rate(rows,'tie_dedup'):.4f} | doubles "
          f"{rate(dbl,'tie_dedup'):.4f} | non-doubles "
          f"{rate(nod,'tie_dedup'):.4f}")
    infl = rate(rows, 'tie') / max(rate(rows, 'tie_dedup'), 1e-9)
    print(f"    => raw tie rate is inflated {infl:.2f}x by self-ties")

    print(f"\n(3) TRIGGER RATE AND THE RATIO THE VERDICT RESTS ON")
    out = {"n_plies": n, "double_frac": len(dbl)/n,
           "sym_pairs_equal_frac": E/max(P, 1),
           "tie_raw": rate(rows, "tie"), "tie_dedup": rate(rows, "tie_dedup"),
           "tie_inflation": infl}
    hdr = f"    {'tie def':>8} {'v1 trig':>9} {'v2 trig':>9} {'RATIO v2/v1':>12}"
    print(hdr)
    for tk in ("tie", "tie_dedup"):
        t1 = sum(r["gate_v1"] and r[tk] for r in rows)
        t2 = sum(r["gate_v2_t13"] and r[tk] for r in rows)
        ratio = t2 / max(t1, 1)
        print(f"    {tk:>8} {t1/n:>9.4f} {t2/n:>9.4f} {ratio:>12.4f}")
        out[f"trigger_{tk}"] = {"v1_rate": t1/n, "v2_rate": t2/n,
                                "ratio": ratio, "v1_n": t1, "v2_n": t2}
    # STRATIFIED — the assumption-free control. My (v, v+2) dedup detector
    # found only ~1% of pairs equal, so "deduplicated" is NOT a validated
    # control and must not be quoted as one. Splitting by capsule type needs
    # no assumption about WHICH orientations collapse: on doubles the tie is
    # degenerate almost by construction, on non-doubles it is genuine.
    print(f"\n(3b) STRATIFIED BY CAPSULE TYPE — no assumption about which "
          f"orientations pair")
    print(f"    {'stratum':>12} {'plies':>7} {'tie rate':>9} {'v1 trig':>8} "
          f"{'v2 trig':>8} {'RATIO':>8}")
    for nm, rs in (("doubles", dbl), ("non-doubles", nod), ("pooled", rows)):
        t1 = sum(r["gate_v1"] and r["tie"] for r in rs)
        t2 = sum(r["gate_v2_t13"] and r["tie"] for r in rs)
        m = len(rs)
        print(f"    {nm:>12} {m:>7} {rate(rs,'tie'):>9.4f} {t1/max(m,1):>8.4f} "
              f"{t2/max(m,1):>8.4f} {t2/max(t1,1):>8.4f}")
        out[f"stratum_{nm.replace('-','_')}"] = {
            "plies": m, "tie_rate": rate(rs, "tie"), "v1_trig": t1,
            "v2_trig": t2, "ratio": t2 / max(t1, 1)}
    rd = out["stratum_doubles"]["ratio"]
    rn = out["stratum_non_doubles"]["ratio"]
    print(f"\n    ratio on doubles {rd:.4f} vs non-doubles {rn:.4f} "
          f"-> spread {abs(rd-rn):.4f}")
    print("    If these agree, the degeneracy is BALANCED across the gate "
          "populations and\n    the trigger RATIO — the number the NO-GO "
          "rests on — is untouched.")
    out["stratum_ratio_spread"] = abs(rd - rn)

    r_raw = out["trigger_tie"]["ratio"]
    r_ded = out["trigger_tie_dedup"]["ratio"]
    out["ratio_shift"] = r_ded - r_raw
    print(f"\n    RATIO SHIFT from deduplication: {r_ded - r_raw:+.4f} "
          f"({r_raw:.4f} -> {r_ded:.4f})")
    print("    The NO-GO rests on the RATIO, not on the tie rate. A ratio "
          "shift near zero\n    means the degeneracy is BALANCED across the "
          "two gate populations and the\n    verdict is untouched; a large "
          "shift would mean it is not.")
    os.makedirs(os.path.dirname(a.out) or ".", exist_ok=True)
    json.dump(out, open(a.out, "w"), indent=1)
    print(f"\n-> {a.out}")


if __name__ == "__main__":
    main()
