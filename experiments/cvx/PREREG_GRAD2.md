# PRE-REG run 20 (2026-09-18 AT LAUNCH): FULL constant gradient under the CALIBRATED regime
Premise (verified in the ledger): coef-opt2 and run 11 tuned/screened these constants under DRIP-L20
with a censoring cap and clear-rate primary. The calibrated objective is BURSTY-L11 with TAP-OUT
primary (run 16). Only HOLES has ever been re-checked there. Method = run-11's gradient rule (this is
an INCLUSION screen, not a max-of-N pick): per axis, if the better direction beats baseline by
>1.0*SE(from its own discordance), that axis moves into the combined point `winh80grad`, which then
gets its OWN pre-registered validation at n>=1500. Screen numbers are never the estimate.
Base/baseline = winholes80 (n=600 CRN baseline reused from run 18, same seeds/regime/worker).
Axes (popcount-neutral x2 and /2): maxh 6/24 · toprisk 45/180 · spawn 75/300 · poll 3/12 ·
buried 24/96 · setup 16/64 · matched 24/96 · rdyext 4/16 · vrdy 4/16 · wvir 90/360 · holes 40/160
(holes arms = consistency check; 22 arms x 600 games; seeds 36734.. declared reuse).
