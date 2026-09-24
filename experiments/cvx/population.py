"""population — the self-improving loop, v1: iterated best response with FICTITIOUS-PLAY scoring.

Policy family (parametric, opponent-aware): every member is (base, attack, margin, kill_thresh):
  play `base` weights; switch to `attack` when behind in the race by >= margin viruses OR when the
  opponent has <= kill_thresh viruses left (margin=None / kill_thresh=None disable that trigger).
Fixed styles are members with both triggers disabled.
Scoring: each member's fitness = mean win rate over ALL other members of the cumulative population
(every generation's members stay in the pool — the fictitious-play average — so a new champion must
beat history, not just the current crop; this blocks rock-paper-scissors cycling).
Generation step: keep top-K, spawn children by single-parameter mutation, add to pool, score only
the NEW pairings (old pairings are banked). Deterministic CRN seeds per pairing.
"""
import json, os, itertools, random
import fast_rtl_x as FX

BASES   = ["winholes80", "winner", "wincross40"]
ATTACKS = ["wincross40", "wincross80", "winholes80"]
MARGINS = [None, 2, 3, 5, 8]
KILLS   = [None, 4, 6, 10]

def name(m): return f"{m['base']}|{m['attack']}|m{m['margin']}|k{m['kill']}"

def make_policy(m):
    wa, fa = FX.variant(m["base"]); wb, fb = FX.variant(m["attack"])
    # Both triggers off => FIXED base style. The attack field is unused.
    # So winner|wincross40|mNone|kNone == winner|winner|mNone|kNone.
    if m["margin"] is None and m["kill"] is None:
        return (wa, fa)
    state = {"last": None}
    def pol(ctx):
        behind = m["margin"] is not None and (ctx["own_vleft"] - ctx["opp_vleft"]) >= m["margin"]
        kill = m["kill"] is not None and ctx["opp_vleft"] <= m["kill"]
        mode = "attack" if (behind or kill) else "base"
        swapped = state["last"] is not None and mode != state["last"]; state["last"] = mode
        return (wb, fb, swapped) if mode == "attack" else (wa, fa, swapped)
    return (pol, None)

def gen0():
    G = [dict(base="winholes80", attack="winholes80", margin=None, kill=None),   # fixed h80
         dict(base="wincross40", attack="wincross40", margin=None, kill=None),   # fixed cross40
         dict(base="winner",     attack="winner",     margin=None, kill=None),   # old champion
         dict(base="winholes80", attack="wincross40", margin=3, kill=None),      # racer (run 24 winner)
         dict(base="winholes80", attack="wincross40", margin=None, kill=6),      # closer
         dict(base="winholes80", attack="wincross40", margin=3, kill=6),         # both triggers
         dict(base="winholes80", attack="wincross80", margin=5, kill=None),      # harder attack, later
         dict(base="winholes80", attack="wincross40", margin=2, kill=10)]        # hair-trigger
    return G

def mutate(m, rng):
    c = dict(m); k = rng.choice(["base", "attack", "margin", "kill"])
    pool = {"base": BASES, "attack": ATTACKS, "margin": MARGINS, "kill": KILLS}[k]
    c[k] = rng.choice([x for x in pool if x != m[k]])
    return c
