"""DERIVATION INPUTS for the v2 RAND threshold — board structure only.

Uses NO refork output. Both quantities are facts about champion-value structure
at plies in the SPENT block, and both predate the run-1 look.
"""
import sys, statistics as st, random
sys.path.insert(0, '.')
import numpy as np
import screen_gw as S
S._boot()
import oracle_arm as O
from oracle_arm import make_env, _champ_action, CHAMP_ORDER

C, bm = O.init_rig('lulu')
w, fl, wt, ws = C['w'], C['fl'], C['wt'], C['ws']
tie_gap, gen_gap = [], []
rng = random.Random(20260818)

for seed in range(50100, 50250):
    env = make_env(seed, C['level']); pend = None
    for ply in range(300):
        if env.board.virus_count() == 0:
            break
        vals = S.champ_values_of(env.board, env.cur.a, env.cur.b,
                                 env.nxt.a, env.nxt.b, w, fl, wt, ws)
        a = _champ_action(vals, CHAMP_ORDER)
        if a is None:
            break
        if pend is not None:
            legal = [int(s) for s in CHAMP_ORDER if np.isfinite(vals[int(s)])]
            if len(legal) >= 3:
                reps, _d = S.representatives(env, legal, vals, dedup=True)
                if len(reps) >= 2:
                    top = float(vals[reps[0]])
                    pool = [c for c in legal if c not in reps[:2]]
                    if pool:
                        g = top - float(vals[rng.choice(pool)])
                        gen_gap.append(g)
                        if float(vals[reps[0]]) == float(vals[reps[1]]):
                            tie_gap.append(g)
            pend = None
        r, v, pend = S.advance_split(env, a, C, seed, bm)
        if r is not None:
            break

mt, mg = st.mean(tie_gap), st.mean(gen_gap)
r = mt / mg
print("DERIVATION INPUTS (spent seeds 50100-50249, board structure only)")
print("  champion-value gap, top vs uniform non-top-2 candidate")
print("    at TIE plies       : mean %.1f   n=%d" % (mt, len(tie_gap)))
print("    at ALL post-garbage: mean %.1f   n=%d" % (mg, len(gen_gap)))
print("  STRUCTURAL RATIO r = tie/general = %.3f" % r)
print("  h13 RAND on their population     = -0.559")
print("  DERIVED expectation for MY RAND  = %.3f" % (-0.559 * r))
print("  VOID bar = CI upper must be < 50%% of that = %.3f" % (-0.559 * r * 0.5))
