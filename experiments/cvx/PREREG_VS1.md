# PRE-REG run 23 (2026-09-19 AT LAUNCH): first competitive round-robin in the two-board VS arena
Arena: vs_sim.py (event-driven race on the travel-time clock; garbage transfer on combos, halves =
min(4, cleared_cells//3) when >=6 cells clear, landing in the garbage-legal columns {1,2,3,5,6,7}).
⚠ Declared v1 approximations: cell-count proxy for the ROM's "2+ lines" send rule; travel-time
constants (0.6s + 0.35s/row); both flagged for refinement against the disassembly before any
ship-adjacent claim. Seeds 36734.. declared reuse; same stream both boards (NES VS convention).
QUESTION: does combo credit — DEAD as a solitaire candidate — win head-to-head where combos ATTACK?
Arms vs winholes80: wincross40, wincross80, winvbonus? (use existing variants wincross40/wincross80);
n=300 CRN seeds per pairing, L11. PRIMARY = head-to-head win rate (binomial vs 50%, two-sided).
Win>55% p<0.05 => the competitive objective genuinely inverts the solitaire verdict; next step is a
population round-robin + fictitious-play averaging. <=50% => the smoke was noise.
