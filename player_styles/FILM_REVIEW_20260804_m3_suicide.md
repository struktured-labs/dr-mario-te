# Film review — 2026-08-04 recorded set, match 3 Stomper suicide autopsy

Source: `~/Videos/drmario_sessions/20260804_1955_pocket_dock.mkv` (25 min, 1080p60).
Method: 1 fps frame extraction → color-grid classifier over the P2 bottle (8×16 cell
map per second) → cell-level add/remove ledger. **No RAM taps, no emulator — pure video.**
Blind-first: everything below was concluded before re-reading the player's commentary.

## Set segmentation (verified by the crown tally in the center window)

| match | video time | result | how |
|---|---|---|---|
| m1 | ~2:00–6:25 | Stomper W | **full clear**, P1 stuck at 5 viruses |
| m2 | ~13:25–14:50 | Stomper W | P1 topout at 34–29 (behind); short, fast game |
| m3 | ~15:55–18:40 | **P1 W** | **Stomper suicide** — X at 28–26, ahead by 2 |
| m4 | ~19:25–24:50 | Stomper W | full clear, **P1 at 01** — one virus from winning |

Sides confirmed from tape alone: the m3 topout happens to the bottle that is AHEAD
(26 vs 28) ⇒ that bottle is the AI ⇒ **Stomper = P2 (right), player = P1 (left)**.

## m3 autopsy — the mechanism, second by second

Column-height trajectory of P2 (cols 0–7), from the ledger:

- **t≈984**: a 4-wide garbage volley lands on P2 (four singles appear at row 0 over
  cols 0/2/4/6 and fall together — classic attack pattern). P1's attack channel was
  live; this seeds mid-board congestion but does NOT directly kill.
- **t≈1042–1096**: col 5 churns (0→16→cleared→refilled) while cols 3–4 ratchet up
  from ~11 to ~13. The AI keeps clearing (33→26, it is WINNING the race) but its
  placements increasingly land in the spawn-adjacent columns.
- **t≈1099**: col 5 reaches 16 (full) and **never comes down again**.
- **t≈1099–1118 (the death spiral)**: every spawned capsule appears at (row 0, cols
  3–4) and is committed essentially in place — including a **vertical drop onto a
  height-13 column at t≈1103** — while cols 0, 1, 6, 7 sit at heights 2–9, open sky,
  physically reachable (rows 0–2 clear across the whole left side). Navigation was
  possible; it simply was not taken.
- **t≈1119**: spawn blocked by its own three full columns (3/4/5 at 16/16/16). X.
  Four columns were ≤9 at the moment of death.

## Verdict (blind)

The suicide is NOT an eval-style failure of the strand20 term and NOT primarily a
garbage burial — the board had abundant open space. The signature — placements
defaulting into the spawn columns exactly when the stack under spawn gets tall
(= exactly when the fall window gets short) — is the known **search-vs-fall-time /
pair-latch COLUMN@DONE family**: stack rises → shorter fall → search overruns →
driver commits the latched/near-spawn column → stack rises further. A ratchet.

Supporting known priors: pair-latch defect is "champion item, WORST IN ENDGAME
(23.2% L11 / 39.1% endgame)"; fix deployed but untested on this Pocket lineage;
Pocket has its own timing history (#43 slam-gate regression).

## Decisive next test (queued)

Reconstruct the t=1110 board from the video grid, feed it to `decide_ship_d3`
(the chip proxy, 3/3 on committed-placement prediction) and compare the proxy's
chosen column against the tape's actual placement (col 4 vertical). Proxy says
"go left" + tape says "dropped in place" ⇒ commit-path defect confirmed, entirely
from footage. Proxy agrees with the tape ⇒ eval defect, reopen strand accounting.

## Still open (human-side blind pass, needs 60 fps clips)

Rotation-slip count, placement-latency distribution, endgame speed-panic curve,
over-setup check, m1 earned-vs-gifted verdict. The player's four self-reports
remain untested hypotheses until that pass is done.
