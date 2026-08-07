#!/usr/bin/env python3
"""GATE: are Stage 1's labels from the SAME policy that will produce the new ones?

team-lead's fifth condition on reusing Stage 1's 140 positions. Mixing labels from
two policy versions is exactly tonight's own finding -- label quality is set by the
rollout policy -- arriving through the back door as a compute saving. It is also the
code-skew trap: hash the code, not just the results.

A statistical comparison (does champion SE still read 3.31? does clear rate still read
99.5%?) would only bound the difference. This does better and costs less: REPLAY Stage
1's recorded rollouts with today's code and require the pill counts to match EXACTLY.
Bit-exact reproduction is a far stronger claim than distributional agreement, and it
fails loudly rather than within noise.

Non-vacuity: replays the labelled action sets with the MOST distinct pill counts. A
position where every rollout finished in the same number of pills would match even if
the policy had changed -- the same vacuous-pass trap the depth study's stream gate hit.
"""
import json, sys, numpy as np
sys.path.insert(0, '.')
import sp_engine as E
from stage1_depth import rebuild_stream_bases, ROLLOUT_CAP

d = np.load('out/corpus.npz')
col, vir, link, pills = d["col"], d["vir"], d["link"], d["pills"]
recs = [json.loads(l) for l in open('out/labels_main.jsonl') if l.strip()]
bases = rebuild_stream_bases(len(col), 140, 20260806)

# One action per POSITION, most-variable first, so the six replays span six
# different boards. Sorting purely by distinct-count let a single position supply
# every sample -- broad-looking coverage that is really one board six times.
best_per_pos = {}
for r in recs:
    for a in r["acts"]:
        pl = r["pills"][str(a)]
        k = len(set(pl))
        if r["idx"] not in best_per_pos or k > best_per_pos[r["idx"]][0]:
            best_per_pos[r["idx"]] = (k, r["idx"], a, pl)
cand = sorted(best_per_pos.values(), reverse=True)

champ = E.Champion()
env = E.new_env(level=E.LEVEL, seed=0, cap=ROLLOUT_CAP)
prov = E.provenance()
print(f"decide-tree rolled hash: {prov['rolled'][:16]}")
bad = 0
for k, (nd, i, a, want) in enumerate(cand[:6]):
    p = dict(col=col[i], vir=vir[i], link=link[i],
             ca=int(pills[i][0]), cb=int(pills[i][1]),
             na=int(pills[i][2]), nb=int(pills[i][3]))
    got = [E.rollout_value(p, a, bases[i] + m, champ, cap=ROLLOUT_CAP, env=env)[1]
           for m in range(len(want))]
    ok = got == want
    bad += (not ok)
    print(f"  idx={i:6d} act={a:2d} distinct={nd}  {'MATCH' if ok else 'MISMATCH'}")
    if not ok:
        print(f"    recorded {want}\n    replayed {got}")
print()
if bad == 0:
    print("POLICY IDENTITY: PASS -- today's champion reproduces Stage 1's recorded")
    print("rollouts bit-exactly, so the 140 reused labels come from the SAME generator")
    print("as the ~420 new ones. Reuse is sound.")
else:
    print(f"POLICY IDENTITY: FAIL ({bad}/6) -- the decider has MOVED since Stage 1.")
    print("Do NOT reuse: relabel all 560 positions.")
sys.exit(0 if bad == 0 else 1)
