#!/usr/bin/env python3
"""a16mt lane: does the cart EXECUTE A16's changed answers? For every pill whose A16 co-sim final differs from the V11
final, where the cart landed on the A16 timeline replay (the A16 final, V11's final, or something else), and when the A16
final first became visible. Plus every pill whose landing-on-final status differs between the V11 and A16 replays of
the same cart.
Usage: fw_effect.py RUNS A16_TL_DIR CART GAME=V11_TIMELINE [GAME=V11_TIMELINE ...]"""
import json, os, statistics, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "lateflip"))
import parse_lateflip as PL


def run(runs, tag):
    return PL.load(os.path.join(runs, tag, f"lateflip_{tag}.log"))


def main():
    runs, tl, cart = sys.argv[1:4]
    tot = land_a = land_v = other = 0
    vis, flips = [], []
    for arg in sys.argv[4:]:
        g, pv = arg.split("=", 1)
        PV = {r["p"]: r for r in map(json.loads, open(pv))}
        PA = {r["p"]: r for r in map(json.loads, open(os.path.join(tl, f"pubtrace_{g}_a16.jsonl")))}
        LV, LA = run(runs, f"{g}_{cart}_v11_chain_garb"), run(runs, f"{g}_{cart}_a16_chain_garb")
        for p in sorted(PA):
            if p not in LA or not LA[p]["land"]:
                continue
            a = LA[p]["land"]["act"]
            if PA[p]["final"] != PV[p]["final"]:
                fa = PA[p]["final"][2]
                vis.append(next((x[0] for x in PA[p]["pubs"] if x[3] == fa), PA[p]["done_f"]))
                tot += 1; land_a += a == fa; land_v += a == PV[p]["final"][2]
                other += a not in (fa, PV[p]["final"][2])
            if p in LV and LV[p]["land"]:
                fv = LV[p]["land"]["act"] == PV[p]["final"][2]; fa_ = a == PA[p]["final"][2]
                if fv != fa_:
                    flips.append(f"  {g} p{p}: vc {PA[p]['vc']} | V11 final a{PV[p]['final'][2]} landed a{LV[p]['land']['act']}"
                                 f"{' (frozen)' if LV[p]['frozen'] else ''} | A16 final a{PA[p]['final'][2]} landed a{a}"
                                 f"{' (frozen)' if LA[p]['frozen'] else ''} | A16 publishes "
                                 + " ".join(f"a{x[3]}@{x[0]}" for x in PA[p]["pubs"]))
    print(f"{cart}: pills whose A16 final != V11 final: {tot}; the cart landed on the A16 final {land_a}, on the V11 final "
          f"{land_v}, elsewhere {other}; A16 final first visible: median {statistics.median(vis):.1f} f, <= 6 f on "
          f"{sum(x <= 6 for x in vis)}")
    print(f"{cart}: landing-on-final status differs V11 replay vs A16 replay on {len(flips)} pills:")
    print("\n".join(flips))


if __name__ == "__main__":
    main()
