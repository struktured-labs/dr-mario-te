"""Worst admissible NMI frame-pair bound, WITH A PAIRING-MODE GUARD.

⚠ WHY THIS MODULE EXISTS. Two different pair constructions are correct for two different
cart shapes, and applying the wrong one is silent:

  * NON-pipelined image (DRPRESPIPE=0): every ordered pair of scenarios is admissible,
    so the bound is the max over the full CROSS PRODUCT.
  * PIPELINED image (DRPRESPIPE=1): `steady_play` / `spawn_edge_p2` cut only `pt_edge`, so
    pairing one with a PHASE hook double-counts the pipeline. The admissible set is
    consecutive phases + (phase, pp_idle) + two named pairs.

Measured 2026-09-01: a cross-product harness applied to the PIPELINED Childproof cart
reported the UNMODIFIED CHAMPION as 30,816/29,780 -- OVER by 1,036 -- when the true bound is
25,464 (+4,316). It was caught only because a banked figure existed to compare against.

★ THE ERROR IS ONE-WAY, established rather than hoped: the pipelined pair set is a strict
SUBSET of the cross product, so max(superset) >= max(subset) -- the mismatch is always
PESSIMISTIC and fails safe. The reverse cannot mis-score silently: on a non-pipelined image
prespipe_scenarios() returns {}, the pair list is empty and max() raises. **No gate can have
PASSED that should have FAILED.**

The guard below refuses rather than guessing -- the same principle as the census's own
undeclared-loop refusal.
"""
import census

GAME_HEAD, EPS, FRAME = 2040, 300, 29780


def worst_pair(meta, expect_pipelined=None):
    nodes = census.load_from_meta(meta)
    so = census.detect_site_overrides(meta, nodes)
    eb = census.detect_prespipe_bounds(meta)
    have = set()
    for n in nodes.values():
        have.update(n.get("labels") or [])
    pp = census.prespipe_scenarios(have)
    pp_cuts, pp_order = pp if isinstance(pp, tuple) else ({}, [])
    pipelined = bool(pp_order)

    # ---- PAIRING-MODE GUARD: refuse, do not guess ----
    if expect_pipelined is not None and bool(expect_pipelined) != pipelined:
        raise AssertionError(
            "PAIRING-MODE MISMATCH: caller expected pipelined=%s but the IR says pipelined=%s. "
            "A cross-product pairing on a pipelined image double-counts the pipeline (measured: "
            "it scored the unmodified champion OVER by 1,036 cyc). Fix the caller; do not "
            "override." % (expect_pipelined, pipelined))

    scen = dict(census.SCENARIO_CUTS); scen.update(pp_cuts)
    res = {}
    for name, cuts in scen.items():
        ch = [(k, l) for k, l in cuts if l in have]
        res[name] = census.Analyzer(nodes, ch, site_overrides=so,
                                    extra_bounds=eb).worst(meta["units"]["wrapper"]["base"])
    if pipelined:
        pairs = [(pp_order[i], pp_order[i + 1]) for i in range(len(pp_order) - 1)]
        pairs += [(a, "pp_idle") for a in pp_order]
        pairs += [("pp_spawn", "pp_edge"), ("pp_idle", "pp_edge")]
        pairs = [(a, b) for a, b in pairs if a in res and b in res]
    else:
        import itertools
        pairs = list(itertools.product(res, repeat=2))
    worst = max(res[a] + res[b] + 12 + GAME_HEAD + EPS for a, b in pairs)
    # ⚠ `worst` INCLUDES the p1_search scenario. On DRP1NATIVE CvC carts that hook overruns
    # the frame BY DESIGN (~94.8k cyc, unsliced d1 search, absorbed by DRRTIVEC/DRMMC1RST), so
    # a raw CvC number reads OVER and means nothing. For those carts report the worst
    # NON-search pair, from `scenarios` with "p1_search" removed -- a documented exclusion,
    # not a fudge. Pipelined human carts have no p1_search and need no exclusion.
    return dict(worst=worst, frame=FRAME, margin=FRAME - worst,
                fits=worst <= FRAME, pipelined=pipelined, scenarios=res)
