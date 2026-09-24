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

## AMENDMENT 2026-09-20 (resume after Claude weekly-limit): confirmation + gen 3

Gens 0–2 scored; 5 gen-3 children spawned; `POP_DONE` fired before gen 3 was evaluated.
Search n=100 is underpowered ([[dr-mario-screen-n100-is-useless]]); the loop crown is a
CANDIDATE until (a) lands.

**Declared seed REUSE** (space exhausted; no free run of 600): even seeds **36934..38132**
(600 streams, step 2). This is the convex-height `valid` sub-block of 36734-40932, already
CONSUMED. Same stream both boards (NES VS convention). Not a fresh-regime claim.

**Confirm pairings, n=600 CRN each, L11, PRIMARY = A win rate vs 50% two-sided binomial:**
1. `winner|winner|mNone|kNone` vs `winholes80|winholes80|mNone|kNone` (loop crown, gen0–2 #1)
2. `winner|wincross40|mNone|kNone` vs holes80 (gen2 #2, winner-base + attack style)
3. `winholes80|wincross40|m3|kNone` vs holes80 (racer; run 24 was 58.0% n=300 — replicate at 2×)

Seat: A = candidate, B = holes80. Win>55% p<0.05 => candidate proceeds to gates (b)(c).
<=50% => n=100 ranking was noise.

Then score gen 3 (`pop_driver.py 3 100`) so the spawned children actually enter the ledger.

## AMENDMENT 2026-09-20b (code-path pin; gen 3 CANCELLED)

Import graph was a path soup: `nes_pills` bound the qa-wt lambda attach, search was
qa-wt tuck_v3 D3, `ws=20` always (cart `DRSTRAND` default 0), `wincross40` is
winner+cross with holes=20 not holes80. Gen 3 cancelled. In-flight n=600 A-first
confirm (ws=20, unpinned) is LOOP-INTERNAL only.

Pinned worker: `import_pin.py` asserts __file__ and forces `pillrng/nes_pills.py`.
`play_vs(..., ws=0)` matches the cart. New variant `winh80cross40` = holes80+R_CROSS=40
(one-change attack).

**Pinned follow-up (declared REUSE 38534-39732, scval sub-block, 600 even streams):**
seat-balanced n=300+300 (A-first and B-first) on the pinned arena, L11, cells send rule,
ws=0:
1. winner vs holes80
2. winh80cross40 vs holes80  (one-change style)
3. holes80|winh80cross40|m3 vs holes80  (one-change racer)
Plus a SMALL send-rule probe: winner vs holes80, `VS_SEND_RULE=lines`, n=100+100
(same 38534 block prefix). If the ranking flips vs cells, the v1 proxy is the story.

## AMENDMENT 2026-09-20c — cart-legal racer (the ship candidate)

Pinned winner-vs-holes80 is **63.8% seat-balanced n=580, p~3e-11** (A-first 64.7%,
B-first winner 62.9%). First-mover is not the story. `wincross40` is NOT cart-legal
(R_CROSS absent from LeafEval.sv; firmware hex is baked at Quartus — a mux still
costs a ~40 min resynthesis).

**Ship candidate:** `winholes80|winner|m3|kNone` — SAFE=holes80 when ahead, RACE=winner
when `own_vleft - opp_vleft >= 3`. One RTL register (R_HOLES 80↔20).

**Pinned follow-up of THAT pairing** (declared REUSE end_screen 40134-40732, 300 even
streams, n=300+300 seats, ws=0, cells rule). PRIMARY = seat-balanced win rate vs holes80.
>55% p<0.05 AND holes80-base (gate b inherited) => firmware mux is worth the Quartus.

Couch-test tonight without waiting: `RACE_WINNER.mgl` on bluemage is Childproof
(theta400 veto2fixa = winner-lineage holes=20) + TE study cart, **staged not loaded**
(holes80 soak stays). That is the RACE eval, not the mux. The mux is the racer.

## RESULT 2026-09-20c — cart-legal racer FAIL (keep always-on winner)

`winholes80|winner|m3|kNone` vs holes80, n=300+300, ws=0, cells, seeds 40134-40732:
A-first 166/300=55.3% p=0.065; B-first 151/300=50.3%; **seat-balanced 317/600=52.8% p=0.165**.
Does not clear >55% p<0.05. Switching to winner only when behind is not a VS gain.
Always-on winner remains 63.8% (n=600). Quartus for a holes mux is not justified.
The testable VS bot is `RACE_WINNER.mgl` (loaded on bluemage).


**Gate (b) citation, not a re-run of known arms:** run 16 bursty L11 already has winner
tap-out 19.1% vs holes80 13.0%. A winner-base candidate that wins (a) still FAILS (b)
unless a new solitaire number exists. A holes80-base switcher (racer) inherits the holes80
solitaire number for the base; switching is VS-only.

**Arena measurement note (banked, n=15300 pop games):** 99.0% end `clear`, 0.3% topout,
1.0% crushed; 100% of games deliver garbage (mean 40.7 halves/game). The VS objective is
a race. holes80's tap-out reduction is almost invisible here — that is why (b) is a
separate gate, not implied by (a).
