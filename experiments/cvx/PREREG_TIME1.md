# PRE-REG run 19 (2026-09-17 AT LAUNCH): TIME-BASED pressure — does travel-time rescue the tall/lane arms?
Owner mechanism (9/13): "garbage takes FOREVER to fall in the endgame... good players account for that."
Runs 18/18b tested the SHAPES under PILL-indexed pressure and they failed (edge +4.33pp harm p=0.009;
tall/lane null-negative) — but pill-indexed pressure cannot price time at all: a slow placement costs
nothing. `pressure_rig_time.py` adds a wall-clock: dt = 0.6s + 0.35s/row of fall (MED ballpark; probe,
not certified physics), and TIME-DRIVEN volleys P(volley)=TRATE*dt (TRATE=0.04/s ≈ one 2-half volley
per 25 s), on top of the unchanged own-clear-conditioned owner model. Same rate for every arm — the
DIFFERENTIAL is the endpoint: a tall board shortens falls, spends less clock, eats fewer volleys.
Calibration (winholes80, TRATE=0): median 700 s / 180 pills = 3.9 s/pill (sane).
Arms: winholes80 / winh80_tall8_12 / winh80_tall8_24 / winh80_lane19w2. n=600 (declared reuse
36734..), L11, cap 600, PRIMARY = paired tap-out; SECONDARY = clear, elapsed_s, garbage_injected.
Decision: tall flips to a WIN p<0.05 => travel-time mechanism CONFIRMED as an objective feature — the
tuning target becomes time-under-pressure and a confirmation at n>=1500 follows. tall still harms =>
shape mimicry is dead even with time priced; the mechanism's value must live in the SEARCH/planner.
