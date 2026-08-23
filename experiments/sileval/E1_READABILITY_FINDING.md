# FINDING — E1's match winner is not adjudicable from the sampled artifacts

**2026-08-23, swap lane, written BEFORE any population-B row exists.**
Scope: this is an INSTRUMENT finding about what the artifacts contain. It is not
an endpoint reading, and no endpoint number was computed to reach it.

## What was checked

All of population A: **255 OK rows, 4,589 sampled save-states.**

| observation | value |
|---|---|
| samples with a side at 0 viruses | 18 / 4,589 = 0.4% |
| **of those, samples with ONE side at 0 and the other above it (a readable WIN)** | **0** |
| modes ever seen | `$04` play ×3,727, `$08` ×143, `$00` ×18 |
| a results / game-over mode | **never observed** |
| samples undecodable (counters disagree with board mid-clear) | 701 = 15.3% |
| LEVEL ($0316/$0396) across a whole cycle | **pinned 11/11**, every rollover |

Matches last ~3 samples (~60 s) against a 20 s sampling cadence, so the sampler
steps over the moment a match ends.

## Routes tried and refuted (each tested, none assumed)

1. **Virus counters reaching 0** — **zero readable wins in all 4,589 samples.**
   18 samples show a 0, but every one is BOTH sides at 0 simultaneously, which
   is the counter-reset transition, not a result. There is therefore no
   ground-truth match ending anywhere in population A — and so nothing to
   calibrate an inferential rule against either. The adjudicator returns
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

## Instrument probe — A FASTER CADENCE DOES NOT FIX THIS

`probe_cadence.sh` re-ran the identical code path at a requested 5 s cadence on
the old box (3 cycles x 240 s, ship arm). Result:

| | population A | 5 s probe |
|---|---|---|
| achieved cadence | 20 s | **6.86 s** (2.9x faster) |
| samples | 4,589 | 105 |
| match boundaries crossed | many | 7 |
| mode `$08` captured | 143 | 4 |
| **samples with ONE side at 0 (a readable WIN)** | **0** | **0** |
| undecodable | 15.3% | 11.4% |

**Tripling the sampling rate captured zero match endings across 7 boundaries.**
Observed directly in probe cycle 1: P2 went from 20 viruses at s011 straight to
the level-start screen at s012 — 20 to 0 inside one ~7 s gap, because a single
large combo clears many viruses at once.

The sampling channel cannot go much faster either: each sample costs a
save-state plus a 1.3 MB scp, which is why a requested 5 s lands at 6.9 s.

⇒ **E1 is not fixable by cadence.** It needs a different channel — the winner
recorded at the moment it happens (copro-side result byte, a mode-change
trigger, or screenshot detection of the win animation) rather than sampled and
hoped for. That is a design decision for the scoring owner, not a knob this
lane should turn post hoc.

Neither the probe nor the gates write to `rows/`; nothing here is a prereg row.
