#!/usr/bin/env python3
"""PR #30 review: what the DRLATEGUARD census cut is worth, and what census.py charges an ABORTED phase hook.

  python tools/nmi126/census_lgcut_variants.py IR.json        (IR from capture_ir.py)

Prints, per DRPRESPIPE scenario, the hook bound WITH census.py's cuts and with the lg cut removed ("_nolg"), the
adjacent-phase admissible frames both ways (hook1 + hook2 + 12 + GAME_HEAD 2040 + eps 300), and an explicit
"pp_abort" class: pre_tick dispatched to pp_disp but an abort check fired, so NO phase ran and neither h2_cp nor
lg_live/lg_done may be cut (ARMED2/PEND2 can be set there). census.py lumps that hook into every pp_phK scenario
with both cuts applied ("pp_abort_cut"); the lumping is sound only while pp_abort <= every pp_phK bound
(tests/test_lateguard_census_cut.py asserts it).
"""
import sys
sys.path.insert(0, __import__("os").path.dirname(__import__("os").path.abspath(__file__)))
import census as C

ir = sys.argv[1]
meta, nodes = C.load(ir)
have = set()
for n in nodes.values():
    have.update(n.get("labels") or [])
so = C.detect_site_overrides(meta, nodes)
eb = C.detect_prespipe_bounds(meta)
wrap = meta["units"]["wrapper"]["base"]

def hook(cuts):
    cuts = [(k, l) for k, l in cuts if l in have]
    return C.Analyzer(nodes, cuts, site_overrides=so, extra_bounds=eb).worst(wrap)

pp_cuts, order = C.prespipe_scenarios(have)
phases = ["pp_ph1"] + sorted((l for l in have if l.startswith("pp_m") and l[4:].isdigit()), key=lambda l: int(l[4:]))
LG = [("into", "lg_live"), ("into", "lg_done")]

def strip_lg(c):
    return [x for x in c if x not in LG]

R = {}
for name, cuts in pp_cuts.items():
    R[name] = hook(cuts)
    R[name + "_nolg"] = hook(strip_lg(cuts))
# ABORTED-hook class: pre_tick dispatches to pp_disp (PP_PH != 0) but an abort check fires -> pt_bail.
# No phase entry is reached; ARMED2/PEND2 may be nonzero, so neither h2_cp nor lg_* may be cut.
abort_cuts = [("into", "ppd_skip")] + [("into", e) for e in phases] + [("into", "h1_start"), ("into", "do_init"), ("fallof", "p1n_nosearch")]
R["pp_abort"] = hook(abort_cuts)
# the same, with the PR's cuts wrongly applied (what the pp_phN scenario charges an aborted hook)
R["pp_abort_cut"] = hook(abort_cuts + LG + [("into", "h2_cp")])
for k in sorted(R):
    print(f"  {k:16s} {R[k] + 6:6d}")
HEAD = 2040 + 300 + 12
def frame(a, b):
    return R[a] + R[b] + HEAD
print("pairs (hook1+hook2+12+head2040+eps300):")
seqs = {
  "PR (lg cut)": [(order[i], order[i+1]) for i in range(len(order)-1)],
  "no lg cut": [(order[i] + ("_nolg" if order[i] != "pp_edge" else ""), order[i+1] + "_nolg") for i in range(len(order)-1)],
}
for nm, s in seqs.items():
    rows = sorted(((frame(a, b), a, b) for a, b in s), reverse=True)
    print(f"  [{nm}] worst = {rows[0][0]}  [{rows[0][1]} + {rows[0][2]}]  margin {29780 - rows[0][0]:+d}")
    for t, a, b in rows:
        print(f"      {a:12s} + {b:12s} = {t}")
extra = [("pp_edge", "pp_abort"), ("pp_ph1", "pp_abort"), ("pp_ph2", "pp_abort"), ("pp_ph3", "pp_abort"),
         ("pp_abort", "pp_idle"), ("pp_abort", "pp_edge"), ("pp_abort", "pp_spawn")]
print("  aborted-hook pairs (not in the census table):")
for a, b in extra:
    if a in R and b in R:
        print(f"      {a:12s} + {b:12s} = {frame(a, b)}  margin {29780 - frame(a, b):+d}")
