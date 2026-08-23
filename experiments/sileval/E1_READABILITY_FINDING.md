# FINDING — E1's match winner is not adjudicable from the sampled artifacts

**2026-08-23, swap lane, written BEFORE any population-B row exists.**
Scope: this is an INSTRUMENT finding about what the artifacts contain. It is not
an endpoint reading, and no endpoint number was computed to reach it.

## What was checked

All of population A: **255 OK rows, 4,589 sampled save-states.**

| observation | value |
|---|---|
| samples where a side is at 0 viruses (a match ENDING) | **18 / 4,589 = 0.4%** |
| modes ever seen | `$04` play ×3,727, `$08` ×143, `$00` ×18 |
| a results / game-over mode | **never observed** |
| samples undecodable (counters disagree with board mid-clear) | 701 = 15.3% |
| LEVEL ($0316/$0396) across a whole cycle | **pinned 11/11**, every rollover |

Matches last ~3 samples (~60 s) against a 20 s sampling cadence, so the sampler
steps over the moment a match ends.

## Routes tried and refuted (each tested, none assumed)

1. **Virus counters reaching 0** — 0.4% of samples. The adjudicator returns
   `UNREADABLE:rollover-without-zero` on every cycle tried.
2. **Mode timeline** — `$08` and `$00` were opened and looked at directly. Both
   are the LEVEL-START screen (bottles refilling, "LEVEL 11 11"). Neither is a
   results screen and neither carries a win tally.
3. **Level deltas** (the winner's level advancing) — located LEVEL at
   `$0316`/`$0396` by matching the on-screen "11 11", then traced it: pinned at
   11/11 through every rollover. **Hypothesis refuted, not assumed.**
4. **A win counter in internal RAM** — scanned all $0000-$07FF for a monotone,
   small-valued byte incrementing once per match. One candidate (`$06D9`), and
   it does not track wins.
5. **A win counter in cart WRAM** — scanned the 8K. The hits are an append-only
   driver EVENT LOG at `$6210`: 3-byte records `02 01 XX` with XX cycling
   04,05,07,03,08. It grows several records per match, not one, and encodes no
   result.

## Consequence

E1 is the pre-registered PRIMARY. The prereg's own reading rule says >10%
UNREADABLE voids the endpoint and the instrument gets fixed. On this evidence
E1-by-these-artifacts is ~99% unreadable, and that applies to population A's
banked 126 pairs exactly as much as to anything population B would collect.

It also **invalidates the repeatability tripwire registered in AMENDMENT 1**,
whose measurand is the match-1 winner. Recorded here rather than quietly
re-specced.

## What this does NOT establish

That no adjudication is possible. The cart was not exhaustively reverse
engineered, and the prereg's reading rule also names the end-of-cycle
screenshot. A dedicated scoring pass may find a route — and if it does, it
works on the ALREADY-BANKED population A, which is why proving it there is the
cheap prerequisite to spending ~53 h of box time on B.

E1b (near-death survival) is keyed on `occ_top3`, which IS readable from these
artifacts; E2 (wedge monitor) and E3 (descriptive tallies) are readable too.

## Instrument probe

`probe_cadence.sh` re-runs the identical code path at a 5 s cadence to measure
how often a faster sampler actually catches an ending. Not a prereg row; never
written to `rows/`.
