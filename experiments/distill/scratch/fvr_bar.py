"""M3 rider (a): the false-veto ceiling, COMPUTED from reference quantities.
Nothing here uses a fitted guard — every input is either a signed-off bar or a
measurement on the banked labels."""
# --- reference measurements (fvr_ref.py, base M1 bank, L20, non-degenerate)
N_TOT, N_DANGER, N_NONDANGER = 3587, 353, 2914
HARM_PER_VETO = 0.0491      # eval-half surv pts lost by a forced veto at a
                            # non-danger state (mean; 89.4% cost exactly 0)
# --- already-signed M2 bars (not re-derived here)
GO, KILL_LB = 0.129, 0.099
d, nd = N_DANGER/N_TOT, N_NONDANGER/N_TOT
print(f"population: danger {d:.4f}  non-danger {nd:.4f}  "
      f"harm/false-veto {HARM_PER_VETO:.4f} surv-pts")
print(f"\nnet per-ply survival effect = d*capture - nd*FVR*harm")
for lab, cap in (("at the GO bar", GO), ("at the KILL line", KILL_LB),
                 ("at today's point estimate", 0.0645)):
    be = (d*cap)/(nd*HARM_PER_VETO)
    print(f"  {lab:26s} capture={cap:.4f} -> BREAK-EVEN FVR = {be:.3f} "
          f"({be*100:.1f}%)")
be_go = (d*GO)/(nd*HARM_PER_VETO)
for keep, lab in ((2/3, "keep >=2/3 of the gain (RECOMMENDED)"),
                  (1/2, "keep >=1/2 of the gain")):
    print(f"\nCEILING at '{lab}': FVR <= {(1-keep)*be_go:.4f} "
          f"= {(1-keep)*be_go*100:.2f}%")
print(f"\n--- rider (b): composite trigger x g silicon catch ---")
TRIG_CATCH, M0_BAR = 21/31, 2/3
print(f"wide12 raw catch on the M0 silicon corpus = {TRIG_CATCH:.3f} "
      f"(21/31); M0's gate = {M0_BAR:.3f}")
print(f"composite catch = trig_catch * P(g fires | death state)")
print(f"=> g must fire on >= {M0_BAR/TRIG_CATCH:.4f} "
      f"({M0_BAR/TRIG_CATCH*100:.1f}%) of the death states the trigger catches")
print(f"   headroom for g to miss ANY death state: "
      f"{(TRIG_CATCH-M0_BAR)*31:.2f} of 31 corpus deaths "
      f"-> the composite gate is ESSENTIALLY BINDING ALREADY")
