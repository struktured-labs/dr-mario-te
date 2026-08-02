# Freeze #4 root-cause analysis — mid-PLAY P2 pill stall (task #40)

Cart: `latch-converged-native` 016d84ea = `DRCOLDINIT=1 DRNAVDWELL=0 DRNOFREEZE=1 DRP1NATIVE=1
DRRECOMMIT_NOFREEZE=1 DRNAVESC=1`. Capture: `experiments/freeze_20260801/freeze4_playstall_20260802.ss`,
2026-08-02 ~09:15. Source read: `driver-nav/patch_cartridge_copro.py` (1747 lines). Flag decode for
this exact env combination was re-derived and confirmed by re-importing the emitter (`MATURE=True
SLAM=True ROTFIX=True PENDBOUND=False RECOMMIT=True NO_FREEZE=True P1NATIVE=True P1_OWNED=True
NAVESC=True WRETRY_FIX=False COLDINIT=True`).

## 0. Headline finding

**The decoded register combination (PEND2=0, ARMED2=0, WDOG2=0, WDOGH2=0, DELAY2=$0F) is
unreachable through any single linear execution trace of the emitted 6502 code.** This was
established two ways: (a) exhaustive enumeration of every instruction that writes PEND2 or DELAY2
(three sites total, listed below — each pair is written atomically together, and every write that
sets PEND2=0 also sets DELAY2=0 in the same instruction sequence, never leaving DELAY2 at 15), and
(b) empirically, with a py65 reproduction driving the real emitted bytes for this exact flag set
through 8 full pill placements under normal search timing: `PEND2==0 & DELAY2!=0` was observed on
**0 of ~1700 hooks**. That is strong enough that I do not believe this is a coding-logic bug I've
mis-traced; see §2 for what I now think it is.

This matters for the investigation: it means the two "smoking gun" bytes the capture highlights
(DELAY2=$0F, STABLE_CT2=$07 — both flagged `(!)` in the request) are more likely **artifacts of how
the save-state was assembled** than a state the CPU was actually in. Sections 1–3 lay out why, what
mechanism I *can* confirm is real and freeze-shaped (the P0.2 "opening-stall" family, now proven to
recur indefinitely under this cart's flags — a new finding), and what a second capture needs to look
like to tell them apart.

## 1. The state-space argument (why DELAY2=$0F + PEND2=0 doesn't fit)

PEND2 (`$614F`) has exactly three writers in the whole 1747-line emitter, and DELAY2 (`$615F`) has
exactly three, always co-occurring with a PEND2 write in the same unconditional instruction run
(no branch separates them):

| Site | Line(s) | PEND2 ← | DELAY2 ← | Also touches |
|---|---|---|---|---|
| power-on init (`inited`, once-ever via `NAV_MAGIC`) | 755–756 | 0 | 0 | PEND1, DELAY1 |
| COLDINIT match-start reset, gated `MATCH_ACTIVE==0` | 945–946 | 0 | 0 | PEND1, DELAY1, LASTY1/2, and (COLDINIT) ARMED2/WDOG2/WDOGH2/WRETRY2 |
| P2 new-spawn edge (`$0386 > LASTY2`, i.e. Y jumps back to 15 at next spawn — **not** a per-row event; see §1a) | 1186–1193 | 1 | 15 | WRETRY2→0, ROT_DONE2→0, STABLE_CT2→0 |
| `handle(2,…)`'s `_start` (search launch) | 1302–1332 | 0 (paired with ARMED2→1) | *unwritten* — only reachable once DELAY2 already reads 0 (its own gate: `LDA delay; BEQ st2; JMP done`) | ARMED2→1, WDOG2/WDOGH2→0, WRETRY2→0 (bug A, §3) |

Given this table: every path that clears PEND2 to 0 either clears DELAY2 to 0 in the *same* store
sequence (init/COLDINIT), or *requires* DELAY2 to already be 0 as its own precondition (`_start`).
There is no code path that produces PEND2=0 with DELAY2=15. I confirmed this isn't a branch-sense
mistake on my part by running the actual emitted bytes (see §5) through ~1700 hooks of normal
search/placement cycling: the pairing held every time.

**§1a — resolving an apparent second contradiction.** I first misread `$0306`/`$0386` as increasing
during descent, which would make the "new-spawn edge" fire on *every row* of a normal fall (a very
different, much scarier bug). `driver-nav/rl-training-new/LIVE_CONTROL_NOTES.md` and
`memory_map.py` are unambiguous: **Y=15 is spawn (top) and decreases as the pill falls.** Given that,
`CMP LASTY2; BCC/BEQ → skip` only fires when Y *increases*, which during a real fall never happens
except at the instant a new pill spawns (Y snaps from ~0 back up to 15). So the edge really is
"once per pill," as the comment claims — good, no separate row-level re-arm bug. I flag this
correction explicitly because it's the kind of thing that would send a second investigator down the
same dead end.

**§1b — STABLE_CT2=$07 independently corroborates "not a steady 0/0/0 state for 10 minutes."**
`act_p2_go`'s SLAM-stability tracker runs *unconditionally* once PEND2==0 (no gate besides that),
incrementing STABLE_CT2 up to a saturating cap of 0xFE (254) every hook the published (col,orient)
target is unchanged. If PEND2 had genuinely read 0 continuously for the observed ~10-minute stall,
STABLE_CT2 would have pegged at 254 within ~2 seconds and stayed there — not sit at 7. A value of 7
is exactly what you'd see a few hooks (~3.5 frames) after a search's DONE-publish. This is the same
"looks like an early, fresh moment, not a 10-minute-stale one" signature as DELAY2=15 — both bytes
read like a **snapshot taken very close to a state transition**, not the terminal frozen state the
task's framing (pose static across the whole capture) implies.

## 2. Leading explanation: the capture straddles two non-atomic memory regions

The decode notes CPU WRAM at file offset `0x102B08` and cart PRG-RAM `$6000` at file offset
`0x103308` — **two physically separate memories** on a mapper-100 board (console-internal WRAM vs.
the cartridge's own PRG-RAM chip, on a different bus/timing domain of the FPGA core). All of the
driver's search-state scratch (PEND2/ARMED2/DELAY2/…) lives in PRG-RAM; all of the pose/mode state
($0385/$0386/$03A5/$0392/$0046/$0727/$04) lives in WRAM. If the MiSTer save-state serializer dumps
these two regions via separate passes rather than a single bus-frozen instant (plausible for an
FPGA core where PRG-RAM sits behind the cartridge mapper's own read logic), then "the pose is static
across the *whole* capture" and "PRG-RAM reads a fresh-transition combination" can both be true
simultaneously without any contradiction: the PRG-RAM dump could be lagging or leading the WRAM dump
by the low hundreds of hooks needed to explain DELAY2/STABLE_CT2, while the pose genuinely hadn't
moved yet (or had already re-frozen) at whichever instant WRAM was actually latched.

**Confidence: medium.** I can't verify the save-state serializer's atomicity from the .ss file
alone — that needs either the MiSTer core source for this specific save-state feature, or (cleaner)
a second capture designed to catch the *transition*, not just one still frame (§4 makes this
concrete: log PEND2/ARMED2/DELAY2/pose into the existing DRPROBE ring every hook for a few seconds
around a stall, rather than trusting one save-state snapshot).

**Alternative I can't rule out:** stray corruption of the single byte at `$615F` from unrelated
code. I weigh against this because the observed value (`$0F` = 15 decimal) is *exactly* the
literal immediate the pill-lock edge uses (line 1187: `LDA #15; STA DELAY2`) — a coincidence corruption
would have to hit by chance, whereas a **genuinely-fresh, not-yet-reconciled delay write** producing
that exact value is the natural reading. This argues for "captured mid-transition," not "corrupted,"
but I list it for completeness.

## 3. A confirmed, freeze-shaped mechanism: the P0.2/bug-A stale-ARMED retry loop recurs *indefinitely*

Whatever the exact snapshot means, I wanted a mechanism that actually produces the *qualitative*
symptom (P2 motionless for extended periods, NAVESC ineffective) so I built and ran a py65 repro
(§5) of the documented-but-previously-uncharacterized P0.2 "lock-while-armed" bug, combined with the
also-documented, also-unfixed DRWRETRY bug (A). This cart runs with `DRWRETRY` unset (`WRETRY_FIX=
False`), so **both** bugs are live:

- **Lock-while-armed (P0.2, PENDBOUND=0 default on this cart):** if a pill's own search hasn't
  DONE'd by the time the pill naturally falls and locks (real on this cart — `NO_FREEZE=1` never
  pins gravity for fairness, so a slow search and a fast fall can race), the new-spawn edge fires
  fine (PEND2=1, DELAY2=15) but `ARMED2` is still 1 from the stale search, so `handle(2)`'s top-level
  `LDA armed; B(NE) → still-searching path` never reaches `_start` — the fresh PEND2 is never
  consumed. Meanwhile `freeze_pending` pins `GRAV_P2=0` unconditionally whenever PEND2≠0 (no
  `PENDBOUND` gate on this cart), so the *next* capsule is pinned motionless. This is exactly
  `dr-mario-mister-vrdy-provenance`/task-#56's documented mechanism — I didn't rediscover it, I
  confirmed it's live on this specific flag combination.
- **New finding — bug (A) makes the above recur forever instead of self-healing once.** The
  `WDOG_HI_LIM` watchdog (56×256 = 14,336 hooks ≈ 4 min at 2 hooks/frame) eventually times out the
  stale search, and since `WRETRY2` reads 0 the first time, it re-queues once (P0.2's documented
  "stale search DONEs or the watchdog fires (~minutes)" recovery). **But** `_start`'s epilogue
  unconditionally clears `wretry` on every launch when `DRWRETRY` is off (line 1330–1331, "FIX(A):
  dropping this keeps the re-queue-once latch") — including the *retried* launch. So the very next
  time that retried search also fails to keep pace with a fall (same root cause: search latency vs.
  fall time), `WRETRY2` reads 0 again, and it re-queues *again*. In my py65 repro (§5) with a search
  that never DONEs, this produces a stable ~7190-frame (~2 min at my sim's hook rate; realistically
  closer to the documented ~4 min per the WDOG_HI_LIM comment) **periodic stick-then-recover cycle,
  indefinitely** — never a genuine escape, contradicting the "$620s: DONEs or watchdog fires" framing
  in the P0.2 comment, which describes a one-shot recovery, not a steady-state oscillation.

This mechanism is consistent with "NAVESC fired 238 times with no effect": NAVESC's own START
injections toggle pause, which (per the DRSTUDY2P probe notes) does **not** change `$0046` — so the
driver's play dispatch, including `handle(2)`'s watchdog ticking, keeps running underneath the pause
just as before, meaning NAVESC's remediation is orthogonal to (and can't interrupt) this cycle.

**Gap:** my repro predicts *periodic* forward progress (a lock event) roughly every watchdog period,
not permanent stasis for the full observed ~10 minutes. Two ways to reconcile: (1) the capture may
simply have landed within the first such period (the operator's "10 minutes of no effect" describes
watching NAVESC fire repeatedly with no resolution, which is consistent with catching *part* of one
cycle, not necessarily multiple); or (2) on real silicon, with a real dense board (not my sim's empty
one), the search latency itself may consistently exceed one whole `WDOG_HI_LIM` period at this
board's virus density, in which case the "recovery" GO never gets a chance to actually finish either
— i.e. it isn't cycling, it's stuck at the *first* timeout, forever, because the retried search is
just as slow as the one that caused the timeout. I can't distinguish these without knowing the real
board's density at the time of the freeze (not in the decode).

## 4. Root cause, ranked

1. **(Highest confidence, mechanism-level)** The P0.2 lock-while-armed pin, compounded by
   unfixed bug (A) (`DRWRETRY=0` on this cart) turning what should be a one-shot recovery into an
   indefinitely-recurring stall. This is a *real*, silicon-relevant defect on this exact flag
   combination, independently of whether it's precisely what the capture shows.
2. **(Medium confidence, capture-level)** The specific captured register combination is most
   plausibly a non-atomic WRAM/PRG-RAM save-state artifact (§2), not a distinct state the CPU was
   ever actually in. If true, the "true" live state at the moment of the freeze was very likely
   PEND2=1 (stuck, per mechanism #1) rather than PEND2=0 as decoded.
3. **(Low confidence, needs the second capture to even evaluate)** A genuine third mechanism I
   haven't found that legitimately produces PEND2=0/ARMED2=0/DELAY2=15. I could not construct one
   from the code as read, including deliberately trying a spurious `MATCH_ACTIVE`/mode-8 mid-fall
   dip in the py65 repro (Scenario C, §5) — it reproduces `PEND2=0,DELAY2=0` (COLDINIT's own zeroing
   wins), not `DELAY2=15`.

**PEND1=1 "orphaned":** confirmed harmless *for this specific freeze*. Under `P1NATIVE`, `P1_OWNED`
is true, which at Python-build-time (not runtime) drops the entire `freeze_pending` P1 block from
the emitted code (line 1345: `if not HUMAN_P1 and not P1_OWNED:`) — PEND1's stale value is simply
never read by anything downstream on this cart. It's real latent debt (a future rebuild that
re-enables P1's copro path without re-adding `handle(1)` would revive the P0.3-class pin bug) but it
is not part of this freeze's causal chain.

## 5. py65 reproduction

Script: `/tmp/claude-1000/.../scratchpad/freeze4_repro.py` (built against `tests/py65_harness.py`'s
MPU pattern and `tests/test_p1_wiggle.py`'s driver-hook-stepping model; not committed to the repo —
scratch only, per the read-only brief). It builds the **real emitted bytes** via
`patch_cartridge_copro.build_main(11, 1)` under the freeze cart's exact env, and drives P2 through a
transcribed gravity/DAS model (same physics constants `test_p1_wiggle.py` validates against, mirrored
onto `$0385/$0386/$03A5/$0392/$F6/$F8`).

Three scenarios run:
- **A (normal timing):** 8 pills, DONE after 25 hooks each. `PEND2==0 & DELAY2!=0` observed 0/1700
  hooks — confirms §1's static claim empirically, not just by inspection.
- **B (search that never DONEs):** reproduces the lock-while-armed pin (PEND2 stuck at 1, pose stuck
  at spawn, `GRAV_P2` pinned via `freeze_pending`) and, extended to 30,000 frames, the periodic
  timeout→bug-A-retry→re-stick cycle at ~7190-frame intervals (§3).
- **C (forced spurious `MATCH_ACTIVE`=0 mid-fall, i.e. simulating an errant mode-8 hook):** produces
  `PEND2=0, DELAY2=0` (COLDINIT wins outright) — does **not** reproduce `DELAY2=15`, which is why
  it's ranked low in §4.

None of the three hits the exact target tuple (`PEND2=0,ARMED2=0,WDOG2=0,WDOGH2=0,DELAY2=15,
STABLE_CT2=7`) — consistent with §1's unreachability argument. Scenario B is the one to extend for
future work if a second capture points back at mechanism #1: run it to several watchdog periods and
sample the register tuple every hook to build the *reachable-state histogram*, which is a more
rigorous way to ask "how rare would this snapshot need to be" than my hand enumeration.

## 6. Minimal fix (emitter-level)

Two independent layers, in priority order:

1. **Enable + actually fix `DRWRETRY` (bug A specifically) on P2 carts.** Setting `DRWRETRY=1` flips
   `WRETRY_FIX=True`, which (a) drops the `_start` epilogue's unconditional `wretry` clear (line
   1330: `if not WRETRY_FIX: STA wretry` — becomes a no-op), so a retried search's *own* timeout
   correctly finds `WRETRY2` already latched at 1 and does **not** re-queue a second time — turning
   the current infinite recur (§3) back into the one-shot "self-heals within a `WDOG_HI_LIM` period"
   behavior the P0.2 comment originally described; and (b) fixes the P1/P2 latch copy-paste (bug B:
   the pill-lock edge writes `WRETRY` instead of `WRETRY2` when off), which is orthogonal to this
   freeze (P1's search is dropped entirely under `P1NATIVE`) but should be enabled together since
   they're gated by the same flag and (b) is strictly a correctness improvement with no downside on
   this cart. **This does not eliminate the underlying lock-while-armed pin** — it only stops the
   *retry* from spinning forever. The pill can still stick for one full `WDOG_HI_LIM` period
   (~4 min) before the one-shot recovery fires. That's still a multi-minute freeze from a spectator's
   perspective, just bounded instead of unbounded.
2. **Enable `DRPENDBOUND=1`.** This is the fix the P0.2 comment names directly ("bound the
   `freeze_pending` gravity pin to the settle window (PEND && DELAY!=0)") — it stops
   `freeze_pending` from pinning `GRAV_P2` for the **entire** duration a stale search is stuck (which
   is what makes the *next* pill visibly freeze), limiting the pin to the ~15-tick settle window a
   pill-lock edge is actually supposed to cover. Combined with (1), this should convert "P2 visibly
   frozen for up to 4 minutes" into "P2's *search* occasionally falls behind and free-falls the
   capsule under live gravity without AI guidance for a few seconds" — a quality regression, not a
   freeze. Neither flag is enabled on the deployed `016d84ea` cart; both default OFF specifically to
   keep byte-exact goldens, so this requires an opt-in rebuild, not a hotfix to the shipped binary.

I did not find a fix for scenario in §4/rank-3 (the state I couldn't reach) because I couldn't
construct the bug to fix — if the second capture (§4 below) shows this is real, it needs its own
follow-up.

## 7. Driver-level play-stall watchdog design

Given §1–2, I recommend the watchdog **not** key off the internal PEND2/ARMED2/DELAY2 registers at
all — those are exactly the bytes in question, and (per §2) may not even be reliably observable in a
single-frame snapshot. Key it off **externally observable, WRAM-resident, game-owned truth** instead:

- **Trigger:** `$0046==4` (play) AND P2 virus count (`$03A4`) > 0 AND the tuple
  `($0385,$0386,$03A5)` unchanged for **M** consecutive hooks. Suggested M: something below
  `WDOG_HI_LIM` (14,336 hooks) so it fires *before* the existing watchdog would eventually try to
  self-heal — e.g. M ≈ 2,400 hooks (~20s at 2 hooks/frame), comfortably above any legitimate
  in-air hover (min-think gate tops out around `MIN_THINK`=25 hooks, and even a stalled-DONE endgame
  wait under `K_END=255` is bounded by the fall time, which is always < `WDOG_HI_LIM`).
- **Remediation (safe reset, not a fake pill-lock):** do **not** replay the full new-spawn edge
  (that resets `ROT_DONE2`/`STABLE_CT2`, discarding a possibly-good orientation commit, and would
  misfire `TUCK_C2` invalidation if `DRTUCK` is ever enabled alongside this). Instead, synthesize
  exactly what a *fresh* `_start` needs, i.e. force the search-state quintet back to the "ready to
  launch a fresh search against the CURRENT board" state without touching pose-derived state:
  `ARMED2=0, WDOG2=0, WDOGH2=0, PEND2=1, DELAY2=0` (skip the 15-tick settle — the board hasn't
  changed, there's nothing to wait for), leaving `ROT_DONE2`/`STABLE_CT2`/`TGT_C2`/`TGT_O2` alone so
  a still-good running target isn't discarded. On the very next hook, `handle(2)`'s `_start` gate
  (`pend!=0 && delay==0`) fires immediately and re-GOes the copro against the live board. This is
  the minimal reset that unwedges the specific state class in §3 (stale ARMED2) without being a
  bigger hammer than needed.
- **Why this is safe:** it only fires when the pose genuinely hasn't moved for M hooks with viruses
  still on P2's board — the same "structurally cannot trip during real play" argument NAVESC's own
  comment makes for its own trigger (real play advances `$0386` every fall step). Unlike NAVESC's
  START injection, this remediation never touches `$F5`/pause state, so it can't produce the
  toggle-and-do-nothing behavior observed in this freeze, and unlike a full re-arm it doesn't discard
  `ROT_DONE2`/`STABLE_CT2` progress that might be fine.
- **Layering:** this should run **before** NAVESC's own check in `main` (NAVESC's mode-8 exclusion
  and 4-hook frame-owning RTS would otherwise race a stall-watchdog reset the same way it currently
  races the underlying bug) — or, more simply, NAVESC's own stall detector could be extended to
  branch to this remediation instead of a blind START when `$0046==4` specifically (title/menu stalls
  still get START; play-mode stalls get the search-state reset). That reuses the existing
  `ESC_S0/S1/S2`/`ESC_CTL/CTH` infrastructure rather than adding a fourth watchdog.

## 8. What the py65 gate for the fix must simulate

To prove the fix (§6) and not just the watchdog (§7), the test needs to **synthesize the defect**,
not just check normal-path behavior (which `test_p1_wiggle.py`/`test_pocket_wretry.py`-style tests
already do implicitly by never wedging). Concretely:

1. A P2 game model (as in `freeze4_repro.py` §5) with a **mock copro that can be told to never
   assert DONE** for a controlled number of hooks (my `never_done` flag) — this is the load-bearing
   piece; without a controllable-latency mock there's no way to force the fall-faster-than-search
   race that triggers lock-while-armed.
2. Drive it through **at least two** watchdog periods (`WDOG_HI_LIM * 256` hooks ≈ 28,672 hooks) so
   the test can assert: *with `DRWRETRY=0`* the stick-recover cycle repeats (fails the "eventually
   converges" property — this is the regression test for bug A), and *with `DRWRETRY=1`* it does
   **not** repeat a second time (WRETRY2 stays latched through the retried search's own possible
   timeout).
3. Assert `freeze_pending`'s `GRAV_P2` pin duration directly: count hooks where `$0392` is forced to
   0 while `PEND2!=0`, with and without `DRPENDBOUND=1` — the fix should bound it to ≤ the settle
   window (15 ticks) rather than the full stale-search lifetime.
4. For the watchdog design in §7 specifically: force the mock into the stuck state, run the new
   watchdog logic for < M hooks (assert no reset fires — no false positive during a legitimately
   slow search) and then for ≥ M hooks (assert the reset fires and a subsequent hook's `_start` gate
   opens, i.e. `ARMED2` transitions back to 1 against the live board within a few hooks of the
   reset).

**Honest unknown I can't close without more silicon data:** whether the real freeze's underlying
board was dense enough that the *retried* search is itself doomed to time out too (permanent stick,
matching the observed static 10 minutes) or whether it would have recovered on its own moments after
the capture (periodic stick, per my repro). The fix in §6 helps either way, but distinguishing them
matters for deciding whether §7's watchdog is a nice-to-have or load-bearing. **Recommended second
capture:** don't take another single `.ss` snapshot — instead repurpose the existing `DRPROBE` ring
(`$6200`, currently logs `$0046/$0727/$04` on change) to also log `PEND2/ARMED2/WDOG2/WDOGH2/DELAY2/
STABLE_CT2/$0385/$0386` on change, for a build that reproduces this stall, and read the ring instead
of a single frozen frame — that turns this whole analysis from single-snapshot archaeology into an
actual timeline.
