"""ARGMAX-FLIP GATE, NEAR-DEATH STRATUM. The >60% fill stratum cannot be sampled
by stopping mid-game (transient states; the pressure-advance run got ZERO). But
125 REAL near-death boards exist: gate/death_hostdata.txt, harvested from actual
kill games, stack 13-16. Colour convention: hostdata is 0-based, champion wants
1-based Pills (the documented copro colour trap) -- crib transfer_check exactly."""
import sys, os, random
for v in ("OMP_NUM_THREADS","OPENBLAS_NUM_THREADS","MKL_NUM_THREADS","NUMEXPR_NUM_THREADS"):
    os.environ.setdefault(v, "1")
CF="/home/struktured/projects/dr-mario-cosimfarm-wt/experiments/cosim_farm"
Q="/home/struktured/projects/dr-mario-qa-wt/experiments"
for p in ("/home/struktured/projects/dr_mario_rl/.claude/worktrees/faithful-sim/src",
          CF, Q, Q+"/eval47", "/home/struktured/projects/dr_mario_rl/tmp/vs_aware",
          "/home/struktured/projects/dr_mario_rl/tmp/combo_term",
          "/home/struktured/projects/dr_mario_rl/tmp/pillrng"):
    if p not in sys.path: sys.path.insert(0, p)
import fast_rtl_x as FX
from cascade_stranded_x import StrandedChainD3Decider
import cascade_chain_x as C
from drmario.faithful_game import Pill
from transfer_check import nes_to_board, read_hostdata_full
from vs_harness import drop_garbage
FX.warmup_ship_eh(topk2=8); C.warmup_chain(topk2=8)
w, fl = FX.variant("winner")
champ = StrandedChainD3Decider(w, fl, topk2=8, maxpass=0, w_chain=180, ws=20)

cases = read_hostdata_full("/mnt/data/drmario_cosim/gate/death_hostdata.txt")
rng = random.Random(31)
flips = same = dead = err = 0
fills = []
for board, cA, cB, nA, nB in cases:
    b = nes_to_board(board)
    cur, nxt = Pill(cA+1, cB+1), Pill(nA+1, nB+1)
    try: pre = champ.choose(b, cur, nxt)
    except Exception: err += 1; continue
    if pre is None: err += 1; continue
    b2 = nes_to_board(board)
    drop_garbage(b2, rng.choice([2,3,4]), [1,2,3], rng.randrange(4))
    if b2.spawn_blocked(): dead += 1; continue   # instant death: no decision exists
    try: post = champ.choose(b2, cur, nxt)
    except Exception: err += 1; continue
    if post is None: err += 1; continue
    fills.append(sum(1 for r in range(b.rows) for c in range(b.cols) if b.color[r,c])/128)
    if pre != post: flips += 1
    else: same += 1
n = flips + same
import statistics
print(f"NEAR-DEATH FLIP GATE  (125 real kill-game boards, stack 13-16)")
print(f"  usable {n}   instant-death-on-drop {dead}   errors {err}")
if fills: print(f"  fill: median {statistics.median(fills)*100:.0f}%  min {min(fills)*100:.0f}%  max {max(fills)*100:.0f}%")
print(f"  flips {flips}/{n} = {flips/max(n,1)*100:.1f}%")
