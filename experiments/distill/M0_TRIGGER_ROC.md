# M0(a) — In-regime trigger re-ROC on the silicon death class
distill-coproc lane · 2026-08-26 · tier €0 (banked data + OBS video reads only)
Instrument: `m0_sampler.py` (this dir; both banked JSONs in `out/` are its
exact output, re-run after consolidation). DESIGN.md §E/M0.

## Verdict
- **The registered L20 trigger `dsh>=13` FAILS the M0 catch gate on the
  silicon death class**: 9/31 (29%) per-loss any-fire on the banked corpus;
  on the owner-match suicides it fires NEVER in G3 (0/27 samples) and only AT
  the death sample in G2 (1/48) — zero prophylactic lead on both named
  must-catch cases. DESIGN.md risk #1 (regime transfer) is confirmed, cheaply.
- **The variant `wide12 = max(H[2..5]) >= 12` PASSES**: corpus 21/31 = 67.7%
  per-loss any-fire; both owner-match suicides caught with sustained pre-death
  fire (G2 20/48, G3 15/27 samples ≈ 75-100 s of lead) at 4/101 (4.0%)
  false-fire on healthy match samples. Proceeding requires registering this
  variant (team-lead: "a new registration, not a patch") — requested.

## Mechanism (the legible part)
The fatal towers do not live in the two spawn columns. Owner match: the killer
column is **c5** both times (G2 death heights [6,9,14,12,11,16,16,14] — a
c5-c7 wall with the spawn lane at 11-12; G3: c5 pinned at 13 for the final
~40 s). Corpus: tallest(>=12) columns at the last pre-death sample spread over
**c1-c5** (histogram c0..c7 = [3,7,4,7,8,6,4,0]; c4 most common, c7 never).
`max(H[3],H[4])` structurally underreads the class; the danger signature
in-regime is a TALL NEAR-CENTER TOWER (c2-c5). This also feeds §C's guard
features: throat/neighborhood shape, not just the two spawn columns.

## Data
### Owner match (OBS video, 5 s cadence, AI = 2P; windows per MATCH_REPORT)
| variant | G2 suicide fire | G3 suicide fire | wins false-fire (3 games) |
|---|---|---|---|
| dsh13 (registered) | 1/48 (death sample only) | **0/27 MISS** | 2/101 = 2.0% |
| dsh12 | 4/48 | 6/27 | 3.0% |
| dsh11 | 7/48 | 12/27 | 8.9% |
| core12 = max(H3..H5)>=12 | 17/48 | 15/27 | 4.0% |
| **wide12 = max(H2..H5)>=12** | **20/48** | **15/27** | **4.0%** |
| wide13 | 16/48 | 10/27 | 2.0% |
| maxh13 | 28/48 | 12/27 | 3.0% |
| maxh14 | 16/48 | 1/27 | 0.0% |

### Silicon corpus (banked labels-146 A/B imports: 69 settled pre-death boards,
31 competitive losses — pop-A grinds + boundary/order-clean fresh corpus)
| variant | per-board fire | per-loss ANY-fire (catch) |
|---|---|---|
| dsh13 | 10/69 | **9/31 = 29%** |
| dsh12 | 18/69 | 15/31 = 48% |
| dsh11 | 33/69 | 21/31 = 68% (match false-fire 8.9% though) |
| core12 | 23/69 | 18/31 = 58% |
| **wide12** | **32/69** | **21/31 = 67.7%** |
| maxh13 | 23/69 | 16/31 = 52% |

## Instrument notes (what it is and is not)
- Video sampler: calibrated sprite lattice on the 2P crop (overlay-verified);
  virus classification by sprite texture (viruses float legitimately, kept);
  **falling-capsule removal** — unsupported pill components (<=2 cells) deleted
  to fixpoint. Without this filter ~25% of raw samples spiked dsh=16 (capsule
  passing through the spawn lane), in wins and suicides alike — the
  plausible-wrong failure R61 warns about. Validation: timelines physical
  after filtering; virus counts decline across each game; the G2 t=472 frame
  cross-checks against the independently-saved suicide1_final.png.
- Scope: 5 s samples (match) / 20.4 s (corpus), NOT plies. Fire rates are
  per-sample; per-ply false-fire pricing comes free in M1's label games.
- Corpus catch window = the banked last ~40-80 s only; a deployed trigger is
  live for the whole approach, so any-fire-in-window UNDERSTATES catch
  (conservative direction for the gate).

## Caveats that travel with wide12
1. **Multiplicity (R35/R58)**: 9 pre-stated variants, scored in-sample on the
   same acceptance sets; wide12 is selected PROVISIONALLY. M1 validates it on
   fresh data (trigger recall on states where the tribunal itself finds
   champ_surv low) before it becomes the registered deployed trigger.
2. **Knife-edge**: 21/31 clears the 2/3 bar by one loss; binomial 95% CI
   [50%, 81%] spans the bar. Honest statement: CONSISTENT with >=2/3, not
   established — offset by the conservative window note above, and by 2/2
   sustained catch on the match class the program is actually named after.
3. Catch != save. Firing in time says nothing about whether a distilled g can
   refuse the fatal placement — that is M2/M3's question, unchanged.

# M0(b) — Firmware audit (canonical copro tree)
- fw ROM $8000-$BFFF (16 KB): code region $8000-$AFFF **86% used, 1,756 bytes
  free**; table region $B000-$BFFF 98% used (80 B free). Guard budget must fit
  ~1.7 KB in this build. ⚠ Measured on the CANONICAL delta build; the shipped
  dblcanon fw (b03a586e) is a different build — re-measure there before M4
  (copro-build-provenance trap).
- Live board mirrored at $0500 in copro space; the search materializes
  per-candidate placements (tuck/land emitters) — a ply-1 guard hook point
  exists in firmware. Guard features (neighborhood heights, throat occupancy)
  are recomputable from $0500 + placement in a few hundred cycles/candidate;
  at gated dose this is non-binding against the 0.15-0.35 s/pill envelope.
- Conclusion: FIRMWARE-ONLY remains feasible; binding constraint is ROM bytes
  (~1.7 KB), not cycles, not ALM.

# M0(c) — Status
DESIGN signed off (team-lead 2026-08-26). Seed block 17700..20898 step 2
approved; registered at M1 launch. **M1 unlock request pending team-lead
blessing of the wide12 variant registration** (to be written into M1's
registration: stratum definition + trigger-recall validation endpoint).
