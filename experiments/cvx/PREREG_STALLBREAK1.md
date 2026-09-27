# PRE-REG (2026-09-25 AT LAUNCH, Claude solo): STALL BREAKER on the fw540 brain — SCREEN
Couch 2026-09-25 G2 (recorded): the AI died after ~36 s with no virus cleared while a spawn-lane tower stood.
Mechanism under test (cascade_dig_x): DIG mode per pill when >= S placements w/o a virus cleared AND spawn
lane >= H rows. Levers are FIRMWARE-side only (ROM-only rebuild if it wins): chain dose, root spawn-height
penalty, root virus-clear bonus. selfcheck: dig off == stranded decider 150/150; dig on moves 50/150.
Arms vs fw540: sb_chain0 (dose 0 in dig) · sb_spawn (300/row above 10) · sb_virus (+400/virus) · sb_all ·
sb_all_early (S=5,H=10). Instruments, paired on seeds 36734..: gate (b) owner model n=600 (PRIMARY: tap-out),
VS-race lam 6 n=300 vs a 177-s human (delta 2.65) (SECONDARY: must not drop > 2pp).
Advance to a Hetzner holdout only if tap-out paired diff vs fw540 < 0 with CI excluding 0. Doses are a first
guess (screen); a pass is re-tuned, never shipped from the screen.
