# RESULT TAPOUT (INTERIM, 2026-10-13): what kills the AI vs dr. lulu, and DANGER root penalties

**Status: stage 0 (characterisation) COMPLETE; stage 1 screen and the main phase RUNNING** (systemd user units
`tapout-screen`, then `tapout-auto` runs the pre-registered selection, main and Q2 phases and writes
`tapout/analysis.txt`). The numbers in sec. 2 will be filled from that file. Design: `PREREG_TAPOUT.md` (f7e5bd00,
arms eaed99cd), committed before any danger-arm game.

## 1. Stage 0: what the tap-outs are (sim, STEER14 harness, `tapout/characterisation.txt`)
Every tap-out of both baselines on the STEER14 main block (5,100 seeds) was replayed under the trace wrapper, plus 200
random clears of each. **Identity: 1,455 / 1,455 replays reproduce the banked STEER14 rows** (t_end, how, pills).

| | A16 + u8 | FAIR2PLUS-equiv (d4 k32) |
|---|---|---|
| Kill losses (tap-out before her finish) | 356 / 5,100 (7.0 %) | 307 / 5,100 (6.0 %) |
| Tap-outs at any time | 478 | 577 |
| Kill: pills at death p10/50/90 | 52 / 124 / 202 | 50 / 110 / 178 |
| Kill: time at death (s) p10/50/90 | 70 / 183 / 294 | 74 / 163 / 294 |
| Kill: viruses left at death p10/50/90 | 5 / 11 / 28 | 5 / 14 / 30 |
| Kill: died with >= 10 viruses left | 58 % | 65 % |
| Kill: pills spent with the spawn throat (cols 2-5) at height >= 14 before death, median | 49 | 43 |
| Kill: viruses left when the throat first reached 14, median | 22 | 24 |
| Clears that ever reach throat 14 | 18 % | 20 % |
| Kill: garbage tiles in the last 8 pills, median (p90) | 0 (4) | 2 (5) |
| Class (pre-registered rule, last 8 pills): THROAT / GARBAGE / other | 281 / 74 / 1 | 228 / 77 / 2 |

**Dominant cause: a slow THROAT CREEP, not a sudden garbage kill and not the slam gate.**
- About 79 % (A16 + u8) and 74 % (FAIR2PLUS) of kills are THROAT. The centre columns reach within 2 rows of the top
  mid-game: the median kill game has about 22 viruses left at that point. The AI then lives up there for about 45-50
  pills before a spawn is blocked.
- Garbage is the proximate trigger in only about 21-25 % of kills.
- **Execution degrades up there.** In kill games the landing differs from the chip's final answer on 4.2 % of pills
  while the throat is at 14 or higher, against 1.8 % below it (A16 + u8). In the last 8 pills it is 12.5 %, against
  0.6 % in clears. Reach to the target is lost on a tall board.
- **Search cut short is NOT a cause.** Stability locks (before DONE) are rarer in the last 8 pills of kills (45 %)
  than across clears (80 %) on A16 + u8. A16 + u8 has more kills than FAIR2PLUS (356 vs 307), but that comes from
  playing longer under the same creep, not from u8 cutting searches.
- In 107 of 356 A16 + u8 kills the throat came back down to 12 or below after first reaching 14 and then went up again.
  These are recoverable boards the brain did not keep low.

## 2. Stage 1 screen / main (PENDING; filled from `tapout/screen_select.txt` and `tapout/analysis.txt`)
Arms (all A16 + u8, root-side penalty on the soft b1 of each root, cols 2-5 throat height Hs):
D1 P 60 h0 11 | D2 P 200 h0 11 | D3 P 200 h0 13 | D4 quadratic P 40 h0 10 | D5 P 500 h0 12, only when root Hs >= 11.

## 3. What a winning arm would need outside the sim
- **Firmware only (6502 root side), no RTL.** The penalty is applied per root after DRVETO, on the soft b1 board that
  the firmware already builds for STEER10's `ereach`/`edig` rules (`rules_steer10._reach_pen` is the closest
  precedent). That covers a column-height scan of 4 columns per root (32 roots), a compare and a multiply-subtract
  with 16-bit saturation.
- **Size:** comparable to ereach, estimated at about 60-120 bytes of 6502 plus a cycle check against the NMI budget
  (the worst frame is currently 28,001 / 29,780).
- **Then needed:**
  - a co-sim gate: Verilator copro plus firmware against `tapout_run`'s choices on fixed boards;
  - a cart build, the existing cart gates and Mesen chained replays;
  - a bluemage soak and a couch test (owner).
- The META-with-penalty publish timeline is a model assumption. The firmware would need to apply pen inside the
  anytime publish loop so that intermediate publishes see it; `meta_pen_mismatch` counts where the model had to force
  this.
