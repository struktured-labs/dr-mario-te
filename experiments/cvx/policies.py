"""Adaptive (opponent-aware) policies for the VS arena: a policy is a callable(ctx)->(w,fl,swapped)."""
import fast_rtl_x as FX

def racer(ahead_variant="winholes80", behind_variant="wincross40", margin=3):
    """Race-aware mode switch: play safe when ahead, attack (combo credit) when behind.
    ctx deficit = own_vleft - opp_vleft (positive = losing the race)."""
    wa, fa = FX.variant(ahead_variant); wb, fb = FX.variant(behind_variant)
    state = {"last": None}
    def pol(ctx):
        behind = (ctx["own_vleft"] - ctx["opp_vleft"]) >= margin
        mode = "behind" if behind else "ahead"
        swapped = state["last"] is not None and mode != state["last"]
        state["last"] = mode
        return (wb, fb, swapped) if behind else (wa, fa, swapped)
    return pol

def closer(base="winholes80", kill="wincross40", opp_thresh=6):
    """Kill-mode: when the OPPONENT is close to clearing (about to win), switch to combo credit
    to crush them with garbage before they finish."""
    wa, fa = FX.variant(base); wb, fb = FX.variant(kill)
    state = {"last": None}
    def pol(ctx):
        kill_on = ctx["opp_vleft"] <= opp_thresh
        mode = "kill" if kill_on else "base"
        swapped = state["last"] is not None and mode != state["last"]
        state["last"] = mode
        return (wb, fb, swapped) if kill_on else (wa, fa, swapped)
    return pol
