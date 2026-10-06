#!/usr/bin/env python3
"""One VS match: cart-legal racer (holes80 when ahead, winner when behind) vs holes80.

Prints each pill: clock, virus counts, mode, action. Ends with sent/how.
Usage: python watch_racer.py [seed]
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import import_pin
import_pin.pin()
import vs_sim, population as POP, pressure_rig as PR

SEED = int(sys.argv[1]) if len(sys.argv) > 1 else 40134
PR._init(11, 0, 0)
racer = dict(base="winholes80", attack="winner", margin=3, kill=None)
h80 = dict(base="winholes80", attack="winholes80", margin=None, kill=None)
wA, fA = POP.make_policy(racer)
wB, fB = POP.make_policy(h80)

# wrap play_vs with a tracer by monkeypatching _choose_base? easier: replay via
# a thin copy of the loop that prints. Use play_vs then print result — for live
# mode we instrument vs_sim by wrapping make_policy's callable.
orig = wA
swaps = []

def traced(ctx):
    w, fl, swapped = orig(ctx)
    mode = "RACE" if (ctx["own_vleft"] - ctx["opp_vleft"]) >= 3 else "SAFE"
    if swapped or not swaps:
        swaps.append((ctx["own_t"], ctx["own_vleft"], ctx["opp_vleft"], mode))
        print(f"  t={ctx['own_t']:.1f}s  own_v={ctx['own_vleft']:2d} opp_v={ctx['opp_vleft']:2d}  {mode}")
    return w, fl, swapped

print(f"seed {SEED}  racer(h80↔winner m=3) vs holes80  ws=0 cells-rule")
r = vs_sim.play_vs(SEED, 11, traced, None, wB, fB, wt=0, ws=0, send_rule="cells")
print(f"winner={r['winner']} how={r['how']} pills={r['pills']} sent={r['sent']} swaps={r['swaps']}")
print(f"mode switches logged: {len(swaps)}")
