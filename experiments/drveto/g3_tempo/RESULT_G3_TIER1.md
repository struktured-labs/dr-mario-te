# G3 TIER-1 — driver-tempo measurements for the Sept-3 Fix-B GO/NO-GO
2026-08-30/31, branch drveto. Substrate: (a) real Rev-0 base ROM (`dr-mario-mods/drmario.nes`)
in nes_py, 2P VS mode, painted boards, per-frame traces; (b) real mapper RTL
(CoproDrMario+LeafEval+copro6502, the G1 rig's REBUILD_VSIM invocation) driving the SHIP hex
veto2fixa a2b2e4ac with a per-store clock-stamped observer; (c) driver constants read from
`patch_cartridge_copro.py` at the audited 2-hooks/frame cadence. No hardware touched.

## (b) The slide/lock window at spawn-rest — MEASURED, mechanism nailed
The ROM has NO lock delay: the capsule locks on the first BLOCKED gravity tick
(`fallingPill_checkYMove`: counter > table -> dec Y -> invalid -> confirmPlacement, same frame).
Lateral motion never touches the counter (E5) => the window is hard.

**W_slide = speedCounterTable[base + speedUps] + 1 frames** from pillFalling start.
Pinned-poke sweep E1p: **26/27 grid cells exact** (LOW/ups49 one frame high — immaterial regime).
⚠ This base ROM carries the disassembly's EU-block table (`ver_EU` values verified cell by cell;
LOW/MED/HI bases $0F/$19/$1F -> starting gravity 39/19/13 f/row + 1). The old US transcription in
scattered notes is wrong for THIS ROM.

| speed regime (MED) | ups | W_slide (fo=1 rest) |
|---|---|---|
| fresh game        | 0  | **20 f** |
| ~pill 50 (mid)    | 5  | **15 f** |
| ~pill 100         | 10 | **10 f** |
| ~pill 150         | 15 | **8 f**  |
| plateau (150-540) | 20-49 | **6 -> 2 f** |

speedUps = +1 per 10 pills (ROM), cap 49. HI starts at W=14 and reaches the same plateau ~5 ups
earlier. **fo=2 rest gets TWO gravity periods: W_eff = 2·W − 1 (measured 39/19 vs W 20/10)** —
G2-class boards (fo3=2) are twice as forgiving as fo=1 ledges.

Spawn anatomy: P2's fallingPillY is (re)written only **~1 frame** before the slide window opens
(E6, 3/3) — the 24-frame head start seen on P1 (throw animation) DOES NOT EXIST on the driver's
seat. The driver's Y-rise detector fires essentially at window open.

## (a) Answer latency — spawn to first VALID mailbox store
Driver pipeline (MEASURED from code, 2 hooks/frame): detect <=1 hook -> DELAY2=15 hooks settle
(:1578-80; the "~3 frames" comment is the stale 5-hooks/frame figure — it is **7.5 frames**) ->
board upload + GO in the expiry hook => **GO ~ 7.5±1 f after window open**. Firmware invalidates
the mailbox at search start (test_search_d3.py:518), sub-frame; first valid store measured on
RTL below; driver adopts <=0.5 f (hook poll); press->first lateral edge +1-2 f (E2/E3).

Copro cycles are the clock-domain invariant; frames quoted on the SILICON tap 54.669 MHz
(909652.11 clk/f, binding); the sim's 48x lockstep (1429469 clk/f) is the optimistic bound
([[dr-mario-cosim-farm-turnbased]] — the domain choice flips verdicts; both stored in margins.json).

| scenario class | n | first-pub (silicon) | DONE (silicon) | first-pub==final col |
|---|---|---|---|---|
| parent_s1A | 3 | 1.48-1.61 f | 34-36 f | 3/3 |
| parent_s1B | 3 | 1.52-1.60 f | 34-37 f | 2/3 |
| parent_s2A | 3 | 1.19-1.53 f | 27-37 f | 0/3 |
| parent_s3A | 3 | 1.39-1.49 f | 32-38 f | 2/3 |
| parent_s4A | 3 | 1.20-1.43 f | 28-34 f | 0/3 |
| g2 | 3 | 1.51-1.69 f | 28-32 f | 3/3 |
| g3 | 3 | 1.26-1.66 f | 25-33 f | 2/3 |
| PC4cap0 | 3 | 0.68-1.03 f | 3-6 f | 2/3 |
| synth_L4f1 | 2 | 1.25-1.31 f | 33-34 f | 0/2 |
| synth_L3f1 | 2 | 1.25-1.26 f | 33-34 f | 1/2 |
| synth_L4f2 | 2 | 1.32-1.38 f | 46-48 f | 0/2 |
| synth_L3f2 | 2 | 1.33-1.33 f | 47-47 f | 0/2 |
| synth_L4f1_gateblk | 2 | 1.02-1.09 f | 21-22 f | 0/2 |
| synth_B34f1 | 2 | 1.17-1.19 f | 28-28 f | 0/2 |
| synth_B34f2 | 2 | 1.32-1.34 f | 37-37 f | 0/2 |
| synth_L4f1_shallow | 2 | 1.28-1.34 f | 33-34 f | 1/2 |
| synth_none | 2 | 0.07-0.07 f | 0-0 f | 2/2 |

First VALID mailbox store (search-phase, Fix-A semantics: vetoed bests never stored): **1.0-1.7 f
after GO across every realistic board; DONE 21-48 f** — the converged answer NEVER beats even the
fresh 20 f window; everything the driver can do on this class rides the ANYTIME stream (the Fix-A
G2 gate class is confirmed load-bearing). first-pub==final column on 20/42: the prophylactic's
retarget path matters about half the time.  synth_none (no legal move) pubs in 0.07 f — degenerate
control behaves. Optimistic lockstep-domain numbers are stored alongside in margins.json (0.64x).

## (d) DAS mechanics + the one-edge premise
- **The ~16f "DAS engage cost" claim is WRONG for the first edge and RIGHT for the second.**
  A direction whose raw latch first appears during pillFalling produces a press edge -> the ROM
  moves the capsule the SAME/next frame (edges at t=1-2 measured), then +16 f (engage), then
  +6 f repeats. hor_accel=$10, hor_max=$06 confirmed as the mechanism (fallingPill_checkXMove).
- ⚠ **Edge-burn hazard (E7): a direction held from BEFORE pillFalling loses its press edge —
  first move then costs the full 16 f** (measured edges [16,22,28] vs [2,18,24]). Fix B must not
  hold the direction across the spawn boundary.
- **Press deadline = W_eff − 2** (E3: k<=18 escapes at W=20, k>=19 dies).
- **Geometry (rom_geometry.json, all MEASURED at W=20):** every one-sided ledge tested (fo=1 AND
  fo=2, both directions, incl. the vetog1 archetype fo=[14,12,13,12,1,1,2,2] and the g3 shape)
  is saved by ONE correctly-directed edge — capsule un-ledges, falls deep, throat free at lock.
  Both-sides plugs (B34) need the SECOND edge at +16 f => saved only when W_eff >= ~19 (E4:
  escapes at W=20, dies at W=10/14). Direction matters: toward a blocked gate the ROM refuses
  the move and the capsule dies in place; toward the open side it escapes (gateblk pair).

## (c) Margin table + the three fractions
```
regime (MED)          W    (i) answer-in-time   (ii) Fix-B win zone        (iii) nothing
                            [current driver]     [needs BOTH amendments]
fresh   ups0          20 f      42/42 100%            +0  (moot)                0
mid     ups5          15 f      42/42 100%            +0  (moot)                0
death   ups10         10 f      12/42  28.6%          +28  66.7% (pulse)        2/42  4.8%
late    ups15          8 f      12/42  28.6%          +28  66.7% (pulse)        2/42  4.8%
floor   ups20+         6 f       2/42   4.8%          +37  88.1% (pulse)        3/42  7.1%

Fix B AS SPECCED (press gated on PEND2==0, i.e. after GO at ~8.5 f): +0 in every death-regime
row -- the literal spec NEVER fires in time.  Held-DAS variant of the amended spec: +21 (50%).
```
**Decision input, death-regime band (W=8-10):** (i) **28.6%** — and every one of those is an
fo=2-rest board; **zero fo=1 ledges are steerable in time** (settle 7.5 f + pub 1.5 f + adopt/press
puts the first edge at ~11 f > deadline 6-8 f). (ii) **66.7%** — Fix B's win zone, BUT ONLY with
two spec amendments measured here: **(A) fire during the DELAY2 settle window** (from the first
hook after new-pill detect; the spec's PEND2==0 gate delays the press past the whole window), and
**(B) PULSE the direction (1 f on / 1 f off), don't hold it** — pulsed presses move 1 column per
2 frames (edges t=1,3,5 measured), which rescues the 2-edge classes (both-sides plug, the G2/G3
shapes) that held-DAS provably cannot reach in-regime (side-by-side: pulse escapes at ups10 where
hold dies, 3 board classes). (iii) **4.8%** — both-throat-cols walled; DISTGATE's conceded floor.
Population caveat (R63): the bank is the 5 vetog1 reconstructions + owner G2/G3 + PC4 + 9
synthetic classes x pill combos — class-coverage weighting, not a farm-frequency weighting; the
farm-frequency mix of these classes is a tier-2 question.

Secondary levers surfaced (not recommendations, sized only): DELAY2=15 hooks (7.5 f) is the
single largest tempo cost in the chain — a settle fast-path would ALSO restore the steer chain
at W=10 (chain would land ~4.5 f < deadline 8) but touches every pill's dispatch, not just the
trigger class.  ⚠ Same-Y consecutive-spawn detection gap (INFERRED from code, unmeasured): the
new-pill detector requires Y to RISE above LASTY2; a pill locking at Y=15 followed by a spawn at
Y=15 is invisible — no PEND2, no fresh search, stale-target steering.  G3 tier-2 should probe it.

## Tags
MEASURED: gravity law + table (E1p pinned), fo=2 double window, DAS 2/16/6 + edge-burn +
deadline W−2, geometry per class, P2 spawn anatomy, first-pub/DONE clocks per scenario (real
RTL, ship hex), driver constants+cadence (code, file:line). INFERRED: silicon-tap frame
conversion (54.669 MHz memory constant); mailbox-invalidate <1f; P1/P2 code symmetry of the
currentP loop. ASSUMED: expo regime = MED speed (qualifier settings); death-regime ups band
6-15 (pills 60-150) pending pills-at-death extraction from the corpora.
