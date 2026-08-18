"""ARGMAX-FLIP GATE, HIGH-FILL STRATUM. The first run's advance left every board
below 45% fill -- zero coverage of the states where dies-ahead happens and where
the compute window is shortest. This advance injects drip garbage DURING play
(how high-fill states actually arise) and reports per-stratum."""
import sys, os, random
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
from vs_harness import drop_garbage

rng = random.Random(23)
byfill = {}
skipped = 0
for seed in range(300, 700):
    env = FaithfulDrMarioEnv(level=11, seed=seed, max_pills=300); env.reset()
    # advance UNDER PRESSURE: drip garbage every 3-6 pills so the board fills
    npills = rng.randint(24, 60); since = 0; gap = rng.randint(3, 6)
    dead = False
    for _ in range(npills):
        b = env.board
        if b.spawn_blocked() or b.virus_count() == 0: dead = True; break
        try: mv = champ.choose(b, env.cur, env.nxt)
        except Exception: dead = True; break
        if mv is None: dead = True; break
        try: env.step(mv)
        except Exception: dead = True; break
        since += 1
        if since >= gap:
            drop_garbage(env.board, rng.choice([2,3,4]), [1,2,3], rng.randrange(4))
            since = 0; gap = rng.randint(3, 6)
            if env.board.spawn_blocked(): dead = True; break
    if dead: skipped += 1; continue
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
    if pre != post: d[0]+=1
    else: d[1]+=1
    # stop early once the thin strata are covered
    hi = byfill.get("high(>60%)",[0,0]); mid = byfill.get("mid(45-60%)",[0,0])
    if hi[0]+hi[1] >= 60 and mid[0]+mid[1] >= 60: break
print(f"HIGH-FILL FLIP GATE  (skipped {skipped})")
tot_f = tot_n = 0
for k in ("low(<45%)","mid(45-60%)","high(>60%)"):
    if k in byfill:
        f,s = byfill[k]; t=f+s; tot_f+=f; tot_n+=t
        print(f"  {k:12s} flips {f:3d}/{t:3d} = {f/max(t,1)*100:5.1f}%")
print(f"  {'ALL':12s} flips {tot_f:3d}/{tot_n:3d} = {tot_f/max(tot_n,1)*100:5.1f}%")
