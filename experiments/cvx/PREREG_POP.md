# PRE-REG (2026-09-20 AT LAUNCH): the self-improving loop, v1 (population.py / pop_driver.py)
Owner directive: "do both" (population loop + Hartford recalibration). Loop = iterated best response
over an opponent-aware policy family (base, attack, margin, kill_thresh) with FICTITIOUS-PLAY scoring
(every member scored vs the cumulative pool incl. all past members — blocks RPS cycling). Gen 0 = 8
members (fixed h80/cross40/winner + racer/closer variants); each gen keeps top-3, spawns 5 mutants;
n=100 CRN games per pairing. 3 generations tonight.
⚠ THIS IS A SEARCH, NOT A VERDICT: the loop's output champion is a CANDIDATE. Before any claim it
owes (a) head-to-head vs winholes80 at n>=600 on fresh-regime seeds, (b) solitaire transfer check under
the OWNER burst model (must not regress tap-out), (c) recalibrated-Hartford check. Arena v1
approximations (cells//3 send proxy, travel-time constants) carry into everything here.
