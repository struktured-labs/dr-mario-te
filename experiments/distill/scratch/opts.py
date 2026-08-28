import math, sys
sys.path.insert(0,'.')
A,B = 0.05245,0.07124; CAL=0.650
def se(ng,s): return CAL*math.sqrt((A+B/s)/ng)
def power(x,cap=0.0645):
    z=(0.099-cap)/x-1.96; return 0.5*(1+math.erf(z/math.sqrt(2)))
# per-game costs, from the fitted model: 369 + 0.869*forks - 0.368*plies
TRIG_PER_GAME = 20194/696          # measured un-thinned trigger plies/game
FPA, PLIES = 89.8, 243
def cost_unthinned(): return (369+0.869*TRIG_PER_GAME*FPA-0.368*PLIES)/3600
def cost_thinned():   return 860.8/3600
DANG_PER_UNTHINNED_HELD = 785/164  # measured yield per held-out game
P_CONTRIB = 119/164                # P(un-thinned game yields >=1 danger state)
print(f"per-game: un-thinned {cost_unthinned():.2f} core-h "
      f"(~{TRIG_PER_GAME:.0f} trigger plies), campaign-thinned {cost_thinned():.2f}")
print(f"\n{'option':<46} {'core-h':>7} {'games':>6} {'dang':>6} {'SE':>7} {'pow':>5} {'seeds':>6}")
def row(lab,ch,ng,dang,seeds):
    s=dang/max(ng,1); x=se(ng,s)
    print(f"{lab:<46} {ch:7.0f} {ng:6.0f} {dang:6.0f} {x:7.4f} {power(x):5.0%} {seeds:>6}")
row("0. do nothing (pre-A5)",0,38,93,"0")
row("1. A5 as approved (W=30, topout-only)",120,54,383,"0")
row("2. PHASE 1 un-thin all held-out games",114,119,785,"0")
row("2b. + phase 2 (un-thin train too)",492,119,785,"0")
for extra in (100,175,251,400):
    ng=119+extra*P_CONTRIB; dang=785+extra*DANG_PER_UNTHINNED_HELD
    row(f"3. PHASE 1 + {extra} FRESH held-hashed games",
        114+extra*cost_unthinned(), ng, dang, str(extra))
print(f"\nsensitivity — power depends on the TRUE capture, not just n:")
for cap in (0.00,0.0323,0.0645,0.069):
    print(f"  if true capture={cap:.4f}: phase1 pow={power(se(119,785/119),cap):3.0%}"
          f"  phase1+251 pow={power(se(119+251*P_CONTRIB,(785+251*DANG_PER_UNTHINNED_HELD)/(119+251*P_CONTRIB)),cap):3.0%}")
