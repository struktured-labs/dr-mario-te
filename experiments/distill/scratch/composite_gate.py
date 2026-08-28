"""M3 rider (b): is the composite trigger x g catch gate reachable?
All inputs measured: M0 corpus counts, and the TEACHER's own action rate on
danger states from the M1 bank."""
import math
TRIG_CATCH   = 21/31      # wide12 per-loss any-fire, M0 corpus
BOARD_FIRE   = 32/69      # per-board fire
FIRED_BOARDS, CAUGHT_LOSSES = 32, 21
M0_BAR       = 2/3
TEACHER_P    = 153/353    # H16 overrides / danger states, L20 M1 bank
k = FIRED_BOARDS/CAUGHT_LOSSES     # fired samples per caught loss, on the corpus
print(f"trigger per-loss catch     = {TRIG_CATCH:.3f} (21/31), M0 bar {M0_BAR:.3f}")
print(f"fired boards per caught loss (corpus) k = {k:.2f}")
print(f"TEACHER action rate on danger states    = {TEACHER_P:.3f} (153/353)\n")
def any_action(p, k): return 1 - (1-p)**k
print("=== if g PERFECTLY reproduces the teacher (p = 0.433) ===")
pa = any_action(TEACHER_P, k)
print(f"  P(g acts >=once per caught loss, corpus cadence) = {pa:.3f}")
print(f"  composite corpus catch = {TRIG_CATCH:.3f} x {pa:.3f} = {TRIG_CATCH*pa:.3f}")
print(f"  vs the M0 bar {M0_BAR:.3f}  ->  "
      f"{'PASSES' if TRIG_CATCH*pa>=M0_BAR else '*** FAILS ***'}\n")
need_any = M0_BAR/TRIG_CATCH
need_p   = 1 - (1-need_any)**(1/k)
print(f"=== what the gate as written would REQUIRE of g ===")
print(f"  per-loss any-action >= {need_any:.4f} ({need_any*100:.1f}%)")
print(f"  => per-state action rate >= {need_p:.4f} ({need_p*100:.1f}%)")
print(f"  the teacher itself is at {TEACHER_P:.3f} -> g must be "
      f"{need_p/TEACHER_P:.1f}x MORE aggressive than what it distills\n")
print("=== the cadence artifact: corpus vs deployment ===")
for lab,kk in (("corpus (20.4 s samples, last 40-80 s banked)",k),
               ("deployment (every ply; ~20 fired plies in the same window)",20),
               ("deployment, conservative (~8 fired plies)",8)):
    print(f"  k={kk:5.2f}  P(any action | teacher-perfect g) = "
          f"{any_action(TEACHER_P,kk):.3f}  composite = "
          f"{TRIG_CATCH*any_action(TEACHER_P,kk):.3f}  {lab}")
print(f"\n=> the corpus-measured composite is set by SAMPLING CADENCE, not by g.")
