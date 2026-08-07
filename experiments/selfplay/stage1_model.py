#!/usr/bin/env python3
"""STAGE 1g -- MODEL error: does the search mis-predicting its OWN move's physics cost value?

A third defect class, categorically different from eval error and horizon error and
never separated from them here. The depth-3 search expands children with
_expand_core, whose `_targeted_resolve` is a CAP-1 resolve: it settles the placed
pill's immediate clears but does not run the cascade to a fixpoint. The real sim
does. On ~10% of root actions the two disagree, so for those the search is scoring a
board the game will not actually produce -- it may be valuing a correctly-predicted
board wrongly (eval error) OR valuing the wrong board correctly (MODEL error), and
those have completely different fixes.

Test: split positions by whether the CHAMPION'S OWN chosen action is one whose
predicted board differs from the real one, and compare regret. If mis-predicted
moves carry more regret, a slice of the champion's suboptimality is physics, not
valuation.

Control for the obvious confound: cascades happen on busy boards, and busy boards
may simply be harder. So the comparison is also reported stratified by virus count.
"""
import json, sys, math, random, statistics as st
sys.path.insert(0, '.')
from stage1_depth import _split_regret, _v

def boot(xs, n=8000, seed=9):
    if len(xs) < 2: return (float('nan'), float('nan'))
    r = random.Random(seed); k = len(xs)
    reps = sorted(st.mean([xs[r.randrange(k)] for _ in range(k)]) for _ in range(n))
    return reps[int(.025*n)], reps[int(.975*n)]

lab = [json.loads(l) for l in open('out/labels_main.jsonl') if l.strip()]
dep = {r['idx']: r for r in (json.loads(l) for l in open('out/depth.jsonl') if l.strip())}
rng = random.Random(77)

mism, clean, mism_v, clean_v = [], [], [], []
rate_by_phase = {}
for L in lab:
    i = L['idx']
    acts = L['acts']
    if len(acts) < 3: continue
    vals = {int(a): _v(L['pills'][a], L['outcome'][a]) for a in L['pills']}
    if i in dep:
        for a, d in dep[i]['new_vals'].items():
            vals[int(a)] = _v(d['pills'], d['outcome'])
    M = min(len(v) for v in vals.values())
    if M < 4: continue
    ah = L['hand_act']
    if ah not in vals: continue
    reg = _split_regret(vals, sorted(vals), ah, rng, 100, M)
    dd = L['dyn_diff'].get(str(ah), 0)
    (mism if dd else clean).append(reg)
    (mism_v if dd else clean_v).append(L['nvir'])
    ph = 'early' if L['nvir'] >= 36 else ('mid' if L['nvir'] >= 12 else 'late')
    rate_by_phase.setdefault(ph, []).append(
        st.mean(L['dyn_diff'][str(a)] for a in acts))

print("MODEL ERROR: regret when the champion's OWN chosen move is mis-predicted")
print("="*74)
for tag, xs, vs in (("champ move MIS-PREDICTED", mism, mism_v),
                    ("champ move predicted OK ", clean, clean_v)):
    if xs:
        lo, hi = boot(xs)
        print(f"  {tag}  regret {st.mean(xs):+6.2f} [{lo:+.2f},{hi:+.2f}]  "
              f"n={len(xs):3d}   mean viruses {st.mean(vs):.1f}")
if mism and clean:
    d = st.mean(mism) - st.mean(clean)
    print(f"\n  difference: {d:+.2f} pills")
    print("  ^ confound to watch: cascades need material, so mis-predicted moves sit")
    print("    on busier boards. Compare the virus counts above before reading this")
    print("    as causal.")
print("\n  cap-1 vs full-cascade disagreement RATE by phase:")
for ph in ('early','mid','late'):
    if ph in rate_by_phase:
        print(f"    {ph:6s} {st.mean(rate_by_phase[ph]):.1%} of actions  n={len(rate_by_phase[ph])}")
