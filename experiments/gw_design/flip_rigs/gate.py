"""ARGMAX-FLIP GATE for garbage-window compute: does searching the POST-garbage
board pick a different move than searching the pre-garbage board?
Below ~2% the arm is untestable and a null would mean nothing."""
import sys, os, random, statistics
for v in ("OMP_NUM_THREADS","OPENBLAS_NUM_THREADS","MKL_NUM_THREADS","NUMEXPR_NUM_THREADS"):
    os.environ.setdefault(v, "1")
Q="/home/struktured/projects/dr-mario-qa-wt/experiments"
for p in ("/home/struktured/projects/dr_mario_rl/.claude/worktrees/faithful-sim/src",
          Q, Q+"/eval47", Q+"/adversary", "/home/struktured/projects/dr_mario_rl/tmp/vs_aware",
          "/home/struktured/projects/dr_mario_rl/tmp/combo_term",
          "/home/struktured/projects/dr_mario_rl/tmp/pillrng"):
    if p not in sys.path: sys.path.insert(0, p)
from drmario.faithful_env import FaithfulDrMarioEnv
import fast_rtl_x as FX
from cascade_stranded_x import StrandedChainD3Decider
import cascade_chain_x as C
FX.warmup_ship_eh(topk2=8); C.warmup_chain(topk2=8)
w, fl = FX.variant("winner")
champ = StrandedChainD3Decider(w, fl, topk2=8, maxpass=0, w_chain=180, ws=20)
from vs_harness import drop_garbage           # gravity-correct (fix 5)

rng = random.Random(11)
flips = same = skipped = 0
byfill = {}
for seed in range(0, 200):
    env = FaithfulDrMarioEnv(level=11, seed=seed, max_pills=300); env.reset()
    for _ in range(rng.randint(18, 46)):
        try: mv = champ.choose(env.board, env.cur, env.nxt)
        except Exception: mv = None
        if mv is None: break
        try: env.step(mv)
        except Exception: break
        if env.board.virus_count() == 0: break
    b = env.board
    if b.virus_count() == 0 or b.spawn_blocked(): skipped += 1; continue
    try: pre = champ.choose(b, env.cur, env.nxt)
    except Exception: pre = None
    if pre is None: skipped += 1; continue
    b2 = b.clone()
    drop_garbage(b2, rng.choice([2,3,4]), [1,2,3], rng.randrange(4))
    if b2.spawn_blocked(): skipped += 1; continue
    try: post = champ.choose(b2, env.cur, env.nxt)
    except Exception: post = None
    if post is None: skipped += 1; continue
    fill = sum(1 for r in range(b.rows) for c in range(b.cols) if b.color[r,c])/(b.rows*b.cols)
    k = "low(<45%)" if fill<.45 else ("mid(45-60%)" if fill<.60 else "high(>60%)")
    d = byfill.setdefault(k,[0,0])
    if pre != post: flips += 1; d[0]+=1
    else: same += 1; d[1]+=1
n = flips+same
print(f"ARGMAX FLIP: pre-garbage vs post-garbage board   n={n}  (skipped {skipped})")
print(f"  flipped {flips}/{n} = {flips/max(n,1)*100:.1f}%      gate floor ~2%")
print(f"  => {'PASSES' if flips/max(n,1)>.02 else 'FAILS'} the testability gate")
print("\n  by board fill (the compute window is SHORTEST when fill is HIGHEST):")
for k in ("low(<45%)","mid(45-60%)","high(>60%)"):
    if k in byfill:
        f,s = byfill[k]; t=f+s
        print(f"    {k:12s} flips {f:3d}/{t:3d} = {f/max(t,1)*100:5.1f}%")
