# sileval — DRP1SLICE silicon evaluation lane (task #139)

> ## ⛔ WHAT THIS RIG CAN EVER MEASURE — read this before proposing an endpoint
>
> **Only the quantities that `L9532_TOP_5` ($9532) writes BEFORE it changes the game
> mode, and that survive into the next match, are readable at ~100% capture.**
> That set is exactly:
>
> * `$031E` / `$039E` — per-player VS win counters
> * `$0309` / `$0389` — per-player topped-out flags
>
> **Everything else about a match is a WITHIN-MATCH quantity.** It resets at the match
> boundary, so it can only be read by LANDING on the ~2.5 s end-of-match window — which
> at the 20 s sample period happens **12.5%** of the time (124 of 989 endings in
> population A). That applies to virus count at death, pills placed, viruses cleared,
> and every other "how much game did P1 survive" measure anyone will propose. They are
> all structurally in the 12.5% class, and no amount of faster sampling fixes it
> (see hazard 2 below — the sampler floors at ~2.8 s and tier-2 capture costs 3.78 s).
>
> Censored substitutes are usually worse than they look: a "value at the last sample
> before death" proxy is stale by up to one full sample period, which for a ~54-unit
> per-match count is ~24% of the quantity.
>
> **Corollary: duration endpoints are not available either** — and not merely because
> the prereg excludes them (it does, deliberately: DRP1SLICE has documented tempo
> PHASE DIALS, so seconds-to-death can be the dial moving rather than P1 surviving).
> A sweep of all 8 KB of cart WRAM and all 2 KB of internal RAM found **zero** bytes
> advancing by a small constant per sample — there is **no usable in-game clock**
> (`NAV_T` $6147 is 8-bit ticking ~5x/frame, wrapping every ~0.85 s). So every duration
> we can measure is WALL-CLOCK, and we cannot separate "the core ran slower" from
> "P1 survived longer." That confound is irrecoverable on this rig, not just contestable.

Staged, plug-and-play the moment the NEW MiSTer is on the network. Nothing here
touches the live soak box.

| file | what |
|---|---|
| `PREREG_SLICE_SILICON.md` | pre-registration (DRAFT until team-lead endpoint review) |
| `NEWMISTER_RUNBOOK.md` | new-box day-one: network, fingerprint gate, templates, shakedown |
| `OWNER_SETUP.md` | the owner's ~15 min of hands-on vs what is automated |
| `stage_bundle.sh` | assembles + md5-verifies the SD bundle at `out/newmister_bundle/` |
| `sileval_ab.sh` | the paired-seed ABBA A/B driver (systemd unit `drm-sileval-ab`) |
| `sileval_watchdog.sh` | 2h reload+seedjit soak loop for the new box (`drm-sileval-watchdog`) |
| `score_rows.py` | offline scorer: save-state → timeline CSV (mode, BCD virus, top-3-row occupancy) |
| `e1_winner.py` | **E1 PRIMARY reader** — per-match winners from `$031E`/`$039E`. Use this one. |
| `endframe_scorer.py` | adjudicate one END-FRAME capture (`$0309`/`$0389` primary, `occ_top3` corroborating) |
| `tier1_endframe.py` | cheap screenshot boundary classifier + its gate self-test (`--gate`) |
| `margin_reader.py` | ⛔ NOT an endpoint — duration is prereg-EXCLUDED (tempo phase dials). Diagnostics only. |
| `sealed/` | sealed pre-ruling computations. Do not extend, act on, or delete. |
| `match1_winner.py` | DEPRECATED — virus-counter rule, ~100% UNREADABLE at any usable cadence |
| `seeds_sileval.txt` | 240 pre-registered seeds (recipe in the prereg; alias-deduped, seed 1 excluded) |
| `sileval.env.example` | the only place the new box's IP + pinned template md5s live |
| `mgl/` | loaders for both arms (both reference the proven θ400 core `de7dea35`) |
| `vendor/seedjit_ss.py` | vendored seed-injection tool (`a26a0d5f`), no gitignored-path dependency |

Refusal-gate verification (2026-08-20, offline, no network): 5/5 mutants refused
with exit 2 — placeholder IP, live-box IP (driver + watchdog), unpinned
templates, wrong template md5. Positive control: vendored seedjit patched seed
27875 into a real pre-generation template and read it back (0x6ce3, mode $00).


## ⚠ Two properties of the sample loop that will mislead you

Both are measured on population A (255 rows / 4,593 samples) and both have already
cost a lane a wrong conclusion. Read them before using `out/artifacts/`.

**1. The screenshots LAG the save-states — they are not a synchronous pair.**
The loop in `sileval_ab.sh` is `send_combo leftalt f2` → `pull_state` (which polls up
to 12 s) → `take_shot`. The PNG is therefore captured seconds AFTER the `.ss` beside
it. Consequence: for all 128 samples whose save-state is in the end-of-match window
(mode `$03`/`$05`/`$07`), the PNG shows the **next match's virus-fill animation**
(VIRUS 02/02, 17/17, 35/35, 48/48 — both bottles symmetric), not the ending.
**No game-over frame exists in any of the 4,593 banked screenshots.** Do not use these
PNGs as visual ground truth for a match ending; you will be looking at the wrong moment
and nothing will flag it. Any (input, label) pair drawn across these two transports
needs the skew measured first.

**2. The sampler floors at ~2.8 s, and "just sample faster" cannot fix an endpoint.**
Recovered from local file mtimes (scp does not preserve mtime, so local mtime = write
completion), medians over population A:

| step | cost | note |
|---|---|---|
| `take_shot` (.ss → .png) | **2.70 s** | p10 2.68 / p90 2.71 — a hardcoded `sleep 2` plus ~0.7 s of 4 sequential ssh round-trips. A floor, not load-dependent. |
| `pull_state` (save-state + scp) | **3.78 s** | old box |
| full cycle @ `SAMPLE_SECS=20` | 20.37 s | |
| full cycle @ `SAMPLE_SECS=5` | 6.50 s | asking for 5 s gets 6.5 s |

Save-state is **1,296 KB** vs **7.0 KB** for a PNG — a **184x** ratio. The end-of-match
window is ~2.5 s (capture ≈ min(1, W/T); observed 128/989 = 12.9% at T=20.37 s ⇒ W=2.64 s).
So a trigger-then-capture detector is structurally impossible here: tier 2 costs 3.78 s,
longer than the window it is trying to catch, and lands after mode `$07` has passed.

**3. `out_oldbox/probe5s/` IS NOT A CADENCE CONTROL — cadence is confounded with BOX.**
The 5 s probe ran on the OLD box (10.42.0.225); population A ran on the NEW box
(10.42.0.233). Cadence and machine vary together, so that comparison cannot settle
"does sampling faster perturb the run?" at ANY n — collecting more probe rows would
just be more of the same unusable contrast. A real test has to be same-box with
interleaved cadence. Note also that the two runs used different `CYCLE_SECS` (360 vs
240), so raw matches-per-CYCLE is not comparable between them either: normalise to
matches per unit TIME (10.73 vs 11.11 per 1000 s; the apparent 3.87-vs-2.67 gap is
entirely the 360/240 = 1.50 cycle-length ratio).

**The resolution was not a faster sampler.** `L9532_TOP_5` (`$9532`) increments the VS win
counters `$031E`/`$039E` *before* it writes mode 7 at `$9585`, and those counters persist
into the next match. `e1_winner.py` reads them and scores the banked corpus at
**987/988 = 0.10% unreadable at the unchanged 20 s cadence**. When an endpoint looks
cadence-bound, check whether the machine already writes the answer down.

## CLOSE-OUT — what E1 could and could not measure, and why B was declined (2026-08-23)

### What it CAN measure
**The per-match winner, at 100% capture and independent of sampling cadence.**
`e1_winner.py` reads `$031E`/`$039E`, cross-checked against `$0309`/`$0389` and gated on
the `$6200` ring's match-end count. On the banked population A: **988 endings, 987
adjudicated, 1 UNREADABLE = 0.10%** against a registered 10% void rule, at the unchanged
20 s cadence, with 0.00% undecodable samples (4,589/4,589).

Gate evidence: two independent RAM routes agree 122/0; 29 real P1 wins across 28 rows, so
it is not stuck on one answer; mutants — swap the two players' counters and flags → the
verdict FLIPS (live 8/8, banked 4/4); swap the flags ONLY → 110/128 self-report
`flag_occ_conflict` rather than guessing; wipe the evidence → 100% UNREADABLE with zero
fabricated verdicts; clobber the virus counters → answer UNCHANGED.

### What it CANNOT measure
Anything within-match — see the scope box at the top. Pills-to-top-out was gated and
rejected on two grounds: no trustworthy per-player capsule counter exists (`$0327` fails a
hard physical test at 13.2% impossible residues, `$0310` at 2.5%; `$0090`/`$00a7` pass only
vacuously because the test catches under-counting and they over-count ~2x), and even a
perfect one would be a within-match quantity at 12.5% capture. Duration is excluded by the
prereg and, per the no-clock sweep, irrecoverably confounded here. **There is therefore no
secondary endpoint. The binary winner ships alone.**

### Why population B was declined
Measured paired discordance, pooled and arm-blind: **12 of 445 aligned match-slots = 2.70%,
Wilson 95% CI [1.55%, 4.65%]** — 0.47x the `2p(1-p)` = 5.70% independence bound, because the
arms are strongly correlated (same seed, same board). At the registered 240 pairs that is
~848 slots ⇒ **~23 discordant pairs**, which powers detection of **OR ≈ 4** among discordants
and nothing subtler (70/30 needs 47 pairs, 75/25 needs 29, 80/20 needs 19).

DRP1SLICE removes an NMI tail. Nothing in the model of that change predicts a 4x odds swing,
and per the scope box no cheaper endpoint could catch a smaller one. So B would have spent
~53 h of box time on an instrument that can only see an effect we have no reason to expect.
**Declined — not deferred.**

**Disclosure, recorded rather than omitted.** The team-lead making this call was **not blind**
to population A's arm splits (E1b ship 12.99 vs slice 14.00; E4a 42.429 vs 42.484, both
nulls), reported under authorizations they gave. The decision rests on an **arm-blind design
parameter** — the discordance rate and the resulting OR >= 4 detection floor — **and would have
been identical had A's exploratory reads pointed the other way, because the instrument's
resolution does not depend on the effect's direction.** That claim is checkable: the
discordance computation reads no arm labels. Separately, this lane computed and transmitted
per-arm rates for A BEFORE the arm-blind ruling existed; those are sealed, undeleted, in
`sealed/` with their provenance stated.

**What would reopen B:** a specific mechanism predicting an effect of OR >= 4, or a cheaper
endpoint that clears the structural limit in the scope box.

### The root cause that recurred five times tonight
Every reversal in this investigation had one shape: **a criterion encoding an assumption the
phenomenon violates.** `find_base` required the virus counters to agree with the board, which
is false exactly during the end-of-match animation, so it deleted the evidence. A one-anchor
`$6149` base search admitted a decoy at +0x1F that decoded to all zeros. A win-counter scan
required monotonicity, which the best-of-3 reset violates. A delta-based reader required wins
to appear as positive increments, which the same reset violates. And an estimator was polished
to three decimals on a quantity the prereg excludes. When a check returns "absent", ask what
that check would do if the thing were present but malformed.
