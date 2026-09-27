# RESULT (2026-09-25): STEER2 — under real steering, BUILD the reach root; keep 540 (the dose no longer separates)

Pre-reg: `PREREG_STEER2.md` (committed `3f17a29` before any STEER2 arm ran). All cells run with the couch
steering model (`steer_model.Steer(proph="throat")`, STEER1 gates G0/G1/G2).

## Verdict
- **Bar PASSED for both doses → recommend building the reach-root firmware**, paired with **540**.
  - Survival: tap≤100 reach − no-reach **−19.0 [−22.7, −15.3]** at 540 and **−19.2 [−22.3, −15.8]** at 180.
    Both CIs are entirely below 0.
  - Race at δ 2.65: **+17.0 [+12.0, +22.3]** at 540 and **+10.0 [+4.7, +15.3]** at 180. Both lower bounds are far
    above −2 pp. The reach root does not cost race speed: it wins races because deaths are the dominant loss
    under steering.
  - L15: tap≤100 **−19.3 [−24.7, −14.0]**; whole-game −12.0 [−16.7, −7.3].
- **Dose:** once execution is real, 540 and 180 are statistically indistinguishable on both instruments. The
  pre-registered rule therefore keeps the incumbent 540.
  - Perfect execution, VS race: 540 was +7.3 pp over 180.
  - Under steering: race −4.0 [−10.3, +2.3] without reach, +3.0 [−3.7, +9.7] with reach.
  - Survival: tap≤100 +1.8 [−1.2, +5.0] with reach (540 − 180).
  - Point estimates lean 180 on survival (whole-game tap-out 540 − 180 with reach +4.3 [−1.0, +9.5]) and 540 on
    race. Neither is significant, and CHAIN540's earlier edge is not confirmed under real execution.

## A. Survival — gate (b), OWNER model, L11 MED, n=600 paired, steering on
| cell | tap≤100 | tap-out | win |
|---|---|---|---|
| fw540 | 28.83% | 60.17% | 39.8% |
| fw540 + reach | **9.83%** | 45.50% | 54.5% |
| fw180 | 27.17% | 58.00% | 42.0% |
| fw180 + reach | **8.00%** | 41.17% | 58.8% |

| contrast | tap≤100 | tap-out |
|---|---|---|
| 540+reach − 540 | −19.00 [−22.67, −15.33] | −14.67 [−18.50, −10.83] |
| 180+reach − 180 | −19.17 [−22.33, −15.83] | −16.83 [−20.83, −12.83] |
| 540 − 180 | +1.67 [−2.83, +6.50] | +2.17 [−2.83, +7.50] |
| 540+reach − 180+reach | +1.83 [−1.17, +5.00] | +4.33 [−1.00, +9.50] |

## B. Race — vs_race lam 6, n=300 paired, vs a 177-s human (σ 0.15)
| cell | WIN δ2.65 | WIN δ2.0 | clear% | med t_end | tiles sent |
|---|---|---|---|---|---|
| fw540 | 28.7% | 27.7% | 28.7% | 144 s | 35.2 |
| fw540 + reach | **45.7%** | 42.3% | 45.7% | 202 s | 55.1 |
| fw180 | 32.7% | 31.7% | 33.0% | 141 s | 26.3 |
| fw180 + reach | 42.7% | 37.0% | 46.0% | 187 s | 41.5 |
| fw540, perfect execution (vsrace2) | 95.3% | 84.0% | 97.7% | 215 s | 63.0 |
| fw180, perfect execution (vsrace2) | 88.0% | 77.7% | 96.0% | 201 s | 48.8 |

| contrast | δ 2.65 | δ 2.0 |
|---|---|---|
| 540+reach − 540 | +17.00 [+12.00, +22.33] | +14.67 [+9.67, +20.00] |
| 180+reach − 180 | +10.00 [+4.67, +15.33] | +5.33 [+0.67, +10.00] |
| 540 − 180 | −4.00 [−10.33, +2.33] | −4.00 [−10.33, +2.67] |
| 540+reach − 180+reach | +3.00 [−3.67, +9.67] | +5.33 [−1.33, +12.00] |
| 540 steered − 540 perfect | −66.7 [−72.0, −61.3] | −56.3 [−62.3, −50.7] |

**Break-even pace** is 900 s (the search ceiling) for every steered cell, because steered clear rates are
below 50%.

⚠ **Read the steered race win rates as a STRESS number, not a couch prediction.** The race model's human never
tops out, yet on the couch the owner topped out in 5 of CHAIN540's 6 wins, and the AI won by clearing once.
The AI side is consistent with the couch within noise:
- AI death hazard per placement: race 0.61%, gate b 0.48%, couch 0.21% (1 event, CI ≈ 0.005–1.2%).
- Garbage: the race's ghost sends 13.6 tiles/min; the owner sent 11.6/min in G2.
Contrasts between arms are the robust read.

## C. L15 — gate (b), n=300 paired, steering on
| cell | tap≤100 | tap-out | win |
|---|---|---|---|
| fw540 | 35.67% | 77.33% | 22.7% |
| fw540 + reach | 16.33% | 65.33% | 34.7% |
reach − no-reach: tap≤100 −19.33 [−24.67, −14.00]; tap-out −12.00 [−16.67, −7.33].

## D. Post-hoc (not pre-registered): the FIRMWARE RULE itself
The arms above used the frame-simulator mask (`ReachAwareDecider.mask`). That mask is slightly LENIENT: it counts
a tuck landing, under an overhang, as "reached". The firmware rule below is strict (the exact straight-drop
cells) and is **100% identical to the strict frame-sim mask**:
- 46,272 candidates on 1,446 boards (L11 + L15);
- per-candidate and argmax agreement 100%;
- `reach_fw_validate.py`.

Strict vs lenient choose different moves on 0.2–2.5% of boards. Results for the shipping rule, fw540 + reachFW,
steering on:

| cell (steering on) | tap≤100 | tap-out | VS win δ2.65 | VS win δ2.0 |
|---|---|---|---|---|
| fw540 | 28.83% | 60.17% | 28.7% | 27.7% |
| fw540 + reach (frame-sim mask, arms above) | 9.83% | 45.50% | 45.7% | 42.3% |
| **fw540 + reachFW (firmware rule)** | **10.33%** | **46.17%** | **44.0%** | **40.7%** |

| contrast | tap≤100 | tap-out | VS δ2.65 | VS δ2.0 |
|---|---|---|---|---|
| reachFW − fw540 | −18.50 [−22.17, −14.83] | −14.00 [−18.00, −10.00] | +15.33 [+10.33, +20.67] | +13.00 [+8.00, +18.00] |
| reachFW − reach (frame-sim) | +0.50 [−1.00, +2.00] | +0.67 [−1.83, +3.17] | −1.67 [−5.00, +2.00] | −1.67 [−5.00, +1.67] |

The shipping rule would pass the same bar on its own, and it is indistinguishable from the measured mask.
(n = 600 survival / 300 race; same paired seeds.)

## FIRMWARE SPEC — reach root (proposed flag `DRREACH`)
**What it does.** At the ROOT only, drop every candidate the couch driver cannot land exactly on its straight-drop
cells. It predicts where the capsule will be when the driver starts steering, and whether the driver can get it
there before gravity locks it.

**Inputs**
1. **Board**: the uploaded LIVE board ($0500 / LEV_BOARD, 128 B, 8 cols × 16 rows, row 0 = top).
   - Empty is `$FF` or `$00` (the DISTGATE/TUCKGUARD dual-encoding rule).
   - Derived: `top[c]` = first occupied row (16 if none), plus cell occupancy.
2. **Gravity threshold** `thr = speedCounterTable[baseSpeedSettingValue[speed] + speedUps]`.
   - NTSC `speedCounterTable` is the ROM's 81 B table; `baseSpeedSettingValue = [$0F, $19, $1F]` (LOW/MED/HI).
   - A row lasts `thr+1` frames. P2's `speed` is `$038B` and `speedUps` is `$038A` (the ROM's P1 struct + $80).
   - **Transport, no RTL change:** at GO the cart writes `nA |= (speedUps & $0F) << 4` and
     `nB |= (((speedUps >> 4) & 3) | (speed << 2)) << 4`. These are the free high nibbles.
   - Every firmware read of `S_NA`/`S_NB` already masks `AND #$0F` (tempo-wt `tests/test_search_d3.py`: the
     `_e_node` colour loads at ~L362-363/381-382, and L1124-1125, L1185-1186), so the search is byte-identical.
   - Both GO paths must write them: `handle()` (`wbase+$82/$83`) and DRPRESTART (`W2_BASE+$82/$83`).
   - The firmware keeps its own copy of the table (81 + 3 B) and computes `thr` once per search.
   - **Old cart + new firmware:** the nibbles are 0, so LOW speed and speedUps 0 give `thr = $27` (40 f/row), and
     the mask is nearly all-ones. That degrades safely to today's behaviour.
3. **Constants** (silicon-fitted; `steer_model.py`):
   - `T_LAT = 19` (frames from the new-pill edge to the driver's first answer action; silicon median, n=384);
   - `G0 = 8` (gravity counter starts; the driver's settle pin);
   - `F0 = 3` (first lateral frame);
   - DAS 16/6;
   - `NROT` by sim var `{0:0, 1:2, 2:1, 3:1}`, which by copro `o4` (var = [2,3,0,1][o4]) is `[1,1,0,2]`.
   - `T(n) = G0 + thr + n*(thr+1)` = the frame of gravity tick n (row n → n+1).
   - `row(t) = 0` if `t < G0+thr`, else `(t − G0 − thr) div (thr+1) + 1`.
   - No DIST_TABLE is needed: only DISTGATE's zero budget (y = 0) changes the outcome.

**Rule per legal root candidate** (`reach_fw.reachable`, Python reference):
- `fits(x,row,shape)` means the capsule's cells are empty: H covers `(row,x)` and `(row,x+1)`; V covers `(row−1,x)` and `(row,x)`.
- `rest(x,row)` means fall while the next row fits.
- `lock` = `T(rest)` of the current position.
```
x = 3 ; lock = T(rest(3, 0, H))
PROPH  if min(top3, top4) <= 2:                       # cart DRPROPH
         dir = deeper throat (ties L) if its gate cells (rows 0-1 of c2 / c5) are empty, else the other if empty, else none
         for f = 3,5,7,... < T_LAT and f < lock: if fits(x+dir, row(f), H): x += dir; lock = T(rest(x, row(f), H))
         if lock <= T_LAT: allowed = (var==0 && col==x && rest(x,·,H) == straight rest)   ; done
lock = T(rest(x, row(T_LAT-1), H))
ROTATE f = T_LAT; repeat NROT successful presses:     # blocked -> retry next frame
         if f >= lock: DENY
         press 1: fits(x,row(f),V) -> V ; press 2 (var1): fits H at x, else at x-1 (kick) -> H ; lock re-bases
         f++
         t1 = f
STEER  for i = 1..|col-x|:  t = t1 (i=1) or t1+16+6*(i-2)
         DENY if t >= lock                                             # locked first
         DENY if the row row(t-1)+1 is not ALL EMPTY across [min(x,col)..max(x,col)]   # DISTGATE budget 0
         DENY if !fits(x+step, row(t), shape)                           # blocked
         x += step ; lock = T(rest(x, row(t), shape))
ALLOW  iff rest(col, row, shape) == straight-drop rest row of (var,col)  # not tucked under an overhang
```

**Cost.** Per candidate: ≤ 7 steps, each a single-row span check plus a short downward rest scan. Compute the
32-bit mask ONCE per search, after the board upload and before Pass 0.

**Hook: a Pass-0 PRE-FILTER, not an `o_cand` penalty.**
- In the Pass-0 loop (`p0_c`), after `LEV_LEGAL != 0`, `jmp p0_next` when `mask[o4*8 + col] == 0`. The candidate
  then never enters `TK1`, is never replayed, and is never published by the anytime mailbox. No FIX-A-style
  publish suppression is needed.
- An `o_cand` penalty (DRVETO-style, −20000 saturating) is **not equivalent**. A masked candidate that clears the
  last virus gets +WIN (30000) at `o_cand`, so it still outranks unmasked non-winning candidates. Skip semantics
  is what was measured (`cascade_reach_x._choose_d3_chain_s_masked`: root `continue`).
- Side benefit: fewer root candidates to expand means a faster answer. `T_LAT` is the silicon latency of TODAY's
  search, so a faster answer only makes the mask conservative.

**All candidates masked.** If Pass 0 ends with `D_T1C == 0` (no legal candidate allowed), clear the filter and
rerun Pass 0 unfiltered. That is exactly the Python fallback (`if not allowed.any(): allowed[:] = 1`) and
today's behaviour.

**Gate suggestion.**
- **Gate 0 (transport is inert):** with DRREACH=0, the py65 golden corpus must give identical searches when
  nA/nB carry random high nibbles.
  - Audit on tempo-wt `drveto` @ `0140db3`: every S_NA/S_NB read, including the tuck modules, goes through
    `_e_node`/`_e_dnode` (`AND #$0F`), so this should hold by construction. The gate makes it a fact.
- Dump (board, speed, speedUps) → 32-bit mask vectors from `reach_fw.reach_mask_fw` over the validation boards.
  Require the 6502 mask (py65 golden) to match bit-exactly, like the DRVETO gate.
- Include killed mutants: T_LAT ± 1, the o_cand-penalty form, and the DISTGATE row check off.
- Then soak, and run a couch check with steering-model predictions.

## Files
- `vs_race.py` `steer=` hook plus arms `fw_winner_reach` / `fw540_reach` / `fw540_reachfw`.
- `steer_race.py`, `steer_run.py` (arms `w180`, `w180_reach`, `reachfw`, and a level arg).
- `analyze_steer2.py`.
- `reach_fw.py` (firmware rule) and `reach_fw_validate.py`.
- `cascade_reach_x.ReachFwDecider`.
- Rows: `steer2/{surv,race,l15,remote,fw}/`.
