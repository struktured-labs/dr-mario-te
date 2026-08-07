#!/usr/bin/env python3
"""PRICE THE GATED-d4 PROPOSAL — and check the premise before pricing it.

The lead's proposal: fire depth-4 only when #78's gate is open
(`since_garbage <= k`, k=6), so d4's measured 22.9x cost is paid on the ~48% of
decisions where the spawn lane is loaded rather than everywhere.

BEFORE PRICING IT, THE PREMISE HAS TO SURVIVE ONE QUESTION.
I described E=1 as "the horizon ends one placement before the column closes".
That framing assumes the fatal event is a PLACEMENT. But the champion's search
has NO GARBAGE MODEL AT ALL -- `champion_move(col, vir, ca, cb, na, nb)` sees
two capsules and a board, and nothing about incoming tiles. So if a death is
caused by GARBAGE ARRIVING, then:

    the missing ply is not a placement the search failed to reach,
    it is an EVENT NO SEARCH DEPTH CAN SEE.

Depth-4, depth-8, depth-40 would all miss it identically. Only a term or gate
that ANTICIPATES garbage helps. That makes the discriminator decisive, and it is
already in the recorded data:

    died_on_delivery == True   -> garbage killed it; DEPTH CANNOT HELP
    died_on_delivery == False  -> the champion's own placement killed it;
                                  depth is at least the right KIND of fix

This script measures that split first, then prices only the part that survives.

OUTPUTS
  1 premise check   -- of the E=1 deaths, how many are delivery deaths?
  2 coverage        -- of the depth-addressable ones, how often is #78's gate
                       actually OPEN at the escape ply? (gate shut = no cover)
  3 cost            -- gate-open rate over ALL decisions in the corpus, and the
                       amortised multiplier 1 + rate*(22.9 - 1)
"""
from __future__ import annotations
import sys, os, json, argparse
from collections import Counter

HERE = os.path.dirname(os.path.abspath(__file__))
for _p in (HERE, "/home/struktured/projects/dr-mario-qa-wt/experiments"):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import champion as CH        # noqa: E402
import pressure_escape as PE  # noqa: E402

D4_COST = 22.9      # dr-mario-depth4-memo, measured
GATE_K = 6          # #78 authorised parameters
GATE_H = 4


def gate_trace(seed, level, k, period, after, max_pills=300):
    """Replay a game and record, per ply: gate_open (#78 semantics) and whether
    that ply's death (if any) was a delivery death.

    #78 gate: since_garbage = ply - (ply garbage last landed); open iff <= GATE_K.
    """
    res, plies, trace, v0 = PE.play(seed, level, k, period, after, max_pills)
    last_g = None
    out = []
    for t in trace:
        ply = t["ply"]
        if t.get("garbage_in", 0) > 0:
            last_g = ply
        since = (ply - last_g) if last_g is not None else 10 ** 6
        out.append({"ply": ply, "gate_open": since <= GATE_K,
                    "since_garbage": since,
                    "died_on_delivery": bool(t.get("died_on_delivery")),
                    "spawn_top": t.get("spawn_top")})
    return res, plies, out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--files", nargs="+", default=[
        "results/pressure_escape.json",
        "results/pressure_escape_p8.json",
        "results/pressure_escape_L17.json"])
    ap.add_argument("--out", type=str, default="results/gated_d4_pricing.json")
    a = ap.parse_args()
    CH.init_champion()

    deaths = []
    for f in a.files:
        p = os.path.join(HERE, f)
        if not os.path.exists(p):
            continue
        for r in json.load(open(p)):
            if r["result"] in ("topout", "nomove"):
                r["_src"] = os.path.basename(f)
                deaths.append(r)
    print(f"=== GATED-d4 PRICING over {len(deaths)} replay-verified deaths ===\n")

    # ---------------------------------------------------- 1. PREMISE CHECK
    print("--- 1. PREMISE: is the fatal event a PLACEMENT or a DELIVERY? ---")
    print("    (the champion's search has no garbage model, so a delivery death")
    print("     is invisible at ANY depth -- depth-4 cannot address it)")
    cfg_of = {"pressure_escape.json": (11, 2, 5, 20),
              "pressure_escape_p8.json": (11, 2, 8, 25),
              "pressure_escape_L17.json": (17, 2, 5, 20)}
    rows = []
    for r in deaths:
        lvl, k, per, aft = cfg_of[r["_src"]]
        res, plies, gt = gate_trace(r["seed"], lvl, k, per, aft)
        if res != r["result"] or plies != r["plies"]:
            print(f"    !! seed {r['seed']} did not replay -- skipped")
            continue
        delivery = gt[-1]["died_on_delivery"] if gt else False
        esc_ply = r.get("escape_ply")
        gate_at_escape = None
        if esc_ply is not None:
            m = [g for g in gt if g["ply"] == esc_ply]
            gate_at_escape = m[0]["gate_open"] if m else None
        sg_escape = None
        if esc_ply is not None:
            m = [g for g in gt if g["ply"] == esc_ply]
            sg_escape = m[0]["since_garbage"] if m else None
        rows.append({"seed": r["seed"], "src": r["_src"], "E": r.get("E"),
                     "K": r["plies"], "delivery_death": delivery,
                     "escape_ply": esc_ply, "gate_open_at_escape": gate_at_escape,
                     "gate_open_rate": (sum(g["gate_open"] for g in gt) / len(gt)) if gt else 0.0,
                     "n_decisions": len(gt),
                     "since_garbage_at_escape": sg_escape,
                     # full distribution so the gate parameter k can be swept
                     # WITHOUT re-replaying every game
                     "since_hist": dict(__import__("collections").Counter(
                         min(g["since_garbage"], 99) for g in gt))})

    e1 = [x for x in rows if x["E"] == 1]
    le3 = [x for x in rows if x["E"] is not None and x["E"] <= 3]
    print(f"\n    ALL deaths ({len(rows)}): delivery={sum(x['delivery_death'] for x in rows)}"
          f"  placement={sum(not x['delivery_death'] for x in rows)}")
    print(f"    E=1  deaths ({len(e1)}): delivery={sum(x['delivery_death'] for x in e1)}"
          f"  placement={sum(not x['delivery_death'] for x in e1)}")
    print(f"    E<=3 deaths ({len(le3)}): delivery={sum(x['delivery_death'] for x in le3)}"
          f"  placement={sum(not x['delivery_death'] for x in le3)}")

    addressable = [x for x in e1 if not x["delivery_death"]]
    print(f"\n    ==> DEPTH-ADDRESSABLE E=1 deaths: {len(addressable)}/{len(e1)}")

    # ---------------------------------------------------- 2. COVERAGE
    print("\n--- 2. COVERAGE: is #78's gate OPEN at the escape ply? ---")
    print("    (gate shut at the critical moment => gated-d4 cannot fire there)")
    for grp, name in ((e1, "E=1"), (le3, "E<=3")):
        opn = sum(1 for x in grp if x["gate_open_at_escape"])
        shut = sum(1 for x in grp if x["gate_open_at_escape"] is False)
        print(f"    {name:5s}: gate OPEN at escape ply {opn}/{len(grp)}, shut {shut}")
    cov = [x for x in addressable if x["gate_open_at_escape"]]
    print(f"\n    ==> COVERED (depth-addressable AND gate open): {len(cov)}/{len(e1)} "
          f"of the E=1 deaths, {len(cov)}/{len(rows)} of all deaths")

    # ---------------------------------------------------- 3. COST
    print("\n--- 3. COST: gate-open rate over ALL decisions ---")
    tot_dec = sum(x["n_decisions"] for x in rows)
    tot_open = sum(x["gate_open_rate"] * x["n_decisions"] for x in rows)
    rate = tot_open / tot_dec if tot_dec else 0.0
    amort = 1 + rate * (D4_COST - 1)
    print(f"    decisions sampled       : {tot_dec}")
    print(f"    gate-open rate (k={GATE_K})   : {rate:.1%}")
    print(f"    d4 cost when it fires   : {D4_COST}x")
    print(f"    AMORTISED multiplier    : 1 + {rate:.3f}*({D4_COST}-1) = {amort:.2f}x")
    print(f"    (vs {D4_COST}x for always-on d4 -- a {D4_COST/amort:.1f}x saving)")

    out = {"deaths": len(rows), "e1": len(e1),
           "e1_delivery": sum(x["delivery_death"] for x in e1),
           "e1_depth_addressable": len(addressable),
           "covered": len(cov), "gate_open_rate": rate,
           "amortised_multiplier": amort, "rows": rows}
    with open(os.path.join(HERE, a.out), "w") as fh:
        json.dump(out, fh, indent=1, default=str)
    # ------------------------------------------------- 4. SWEEP THE GATE
    print("\n--- 4. k-SWEEP: where do the economics actually work? ---")
    print("    coverage = depth-addressable E=1 deaths whose escape ply is gated in")
    print(f"    {'k':>3s} {'gate rate':>10s} {'amortised':>10s} {'E=1 covered':>12s}")
    for kk in (0, 1, 2, 3, 4, 6, 8, 12):
        opn = tot = 0
        for x in rows:
            for sg, n in x["since_hist"].items():
                tot += n
                if int(sg) <= kk:
                    opn += n
        rr = opn / tot if tot else 0.0
        am = 1 + rr * (D4_COST - 1)
        covk = sum(1 for x in addressable
                   if x["since_garbage_at_escape"] is not None
                   and x["since_garbage_at_escape"] <= kk)
        print(f"    {kk:>3d} {rr:>9.1%} {am:>9.2f}x {covk:>7d}/{len(e1):<4d}")
    print("\nwrote " + a.out)


if __name__ == "__main__":
    main()
