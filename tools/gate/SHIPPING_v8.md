# v8 rematch cart — read this before you sit down

**PLAY `v8 REMATCH (hardened).nes`, md5 `c0082cb34259007854120d3d4ab9fa27` (98,320 bytes).**
**Evidence: 3.1 hours of emulated play. Zero crashes — bound at 1 per 40 min of live play. But the
soak also hit ONE unexplained freeze whose cause I never found, so: ~2.5% chance (95% upper bound
11%) that one match in a 20-match evening locks up. Keep the reset button in reach.**

That freeze is the headline, not a footnote. Everything else came back clean.

> **The cart named in the earlier version of this document is withdrawn.** `c-v8ship`
> (`087ff959…`) had a real defect: its NMI shield does `LDA $A02E` with no `PHA`, corrupting the
> accumulator on every NMI it handles. The cart above (`v6e`) is the *same 57 flags*, byte-for-byte
> identical snapshot, with a 15-byte A-preserving shield in place of the broken one. The two carts
> differ in exactly 31 bytes. If you have `087ff959` on the card already, do not play it.

---

## 1. Verdict

| | |
|---|---|
| **Cart** | `v8 REMATCH (hardened).nes` |
| **md5** | `c0082cb34259007854120d3d4ab9fa27` |
| **size** | 98,320 bytes |
| **base ROM** | `drmario_v28cs.nes`, md5 `7d307c3051ebc0f8a10e259e3c270acb` |
| **emitter** | `patch_cartridge_copro.py` md5 `22360d986715ce3161fd3bead8eed6ff` |
| **manifest** | `release/v8_20260810/v6e.json` (all 57 flags recorded) |
| **key flags** | `DRMMC1RST=1` `DRRTIVEC=1` `DRDISTGATE=1` `DRRELATCH=1` `DRPRESTART=1` `DRFCGATE=1` `DRPOCKET=1` `DRHUMAN=1` `DRLEVEL=11` `DRHOLDBOARD=0` **`DRTUCK=0`** |

**How strong is the evidence, in the unit you care about:**

| class of failure | what was seen | 95% upper bound |
|---|---|---|
| Crash (MMC1 interleave, RAM wipe, bank-0, BRK, stuck-BUSY) | **0 events** in 2.00 h of live play | ≤ 1 per **40.1 min of live play** |
| Match-boundary abort / title drop | **0 events** in 751 match-ends | ≤ 1 per **251 match-ends** |
| **Hang (mode-4 freeze)** | **1 event** in ~795 matches | ≤ 1 per **41.6 min** of emulated play |

The first two rows are the ones that got fixed and stayed fixed. The third row is new, and it is
the reason this document does not say "safe".

---

## 2. Tucks: NO. This cart does not carry them.

**One sentence: tucks were rejected on provenance, not safety — θ is not a cart flag, it is copro
firmware, so `DRTUCK=1` would ship a strength upgrade whose dose depends on which of eight NES
cores happens to be loaded on the night.**

The longer version, because this was the closest call of the day:

- The safety question came back **clean**. `v8+tuck` was built (`4c1e7fdb…`, `DRTUCK=1` as the only
  delta) and gated. The MMC1 hardening held with the tuck path executing on every hook — the
  composition that had never been tested before — and the functional numbers were
  indistinguishable from plain v8. Tucks cost nothing measurable.
- The executor is **real**, not inert descriptors: 23 tucks actually executed over 131 pills, and
  `fail_land = 0` (whenever the steering window was open, the capsule landed exactly where asked).
  That is a genuine improvement over the historical state where descriptors were published to a
  cart that could not perform them.
- **What killed it**: the validated dose is θ=400. θ lives in `fpga/copro/tuck_v3.py`, not in the
  emitter's 57 flags, and its **default is 150** — the arm that measured 5.8% dies-ahead against
  dr. lulu's 0.8% floor. Worse, the shipped Combo Stomper core records `DRCOPRO_TUCK=1`, which is
  tuck **v1** — a variant with no θ mechanism at all that never writes the descriptor fields. On
  that core, `DRTUCK=1` converts a documented no-op into live, never-measured behaviour. The cart
  cannot detect or verify which core it is running on.
- The measured value was also **~38% of the claim**: −4.16 pills/game (95% CI [−7.61, −0.67]), not
  the −11.0 the co-sim priced, because this 6502 executor completes about three tucks in five.

Real but smaller than advertised, and conditional on a core the cart can't check. Not worth it
tonight. **What would flip this**: pin one core for the match (`NES_theta400_20260809.rbf`, md5
`de7dea35…`) and silicon-gate that exact core+cart pair.

---

## 3. The gate table

### 3a. Mechanism — both directions

The zeros below only mean something because **the same detector, on the same rig, with the fix
turned off, still reports the defect**. 3,000 frames per arm, trigger deliberately present
(`DRHOLDBOARD=1`).

| arm | hardening | mixed→PRG loads | RAM wipes | bank-0 entries | 4→0 aborts | sr_resets |
|---|---|---|---|---|---|---|
| `s-val-mech` (**defect must fire**) | **OFF** | **14** | **15** | **16** | **1** | 2 |
| v8 plain | OFF | 14 | 15 | 16 | 1 | 2 |
| v8 + tuck | OFF | **21** | 21 | 23 | 1 | 2 |
| v8 plain | **ON** | **0** | 0 | 1 *(boot)* | 0 | 11,988 |
| v8 + tuck | **ON** | **0** | 0 | 1 *(boot)* | 0 | 11,988 |

*The wrong input this catches*: a build with the hardening compiled out, or a detector keyed to the
wrong shape. Both fix-off arms reproduce the defect at full strength; corroborated independently by
another lane's `t6-mech-off` (20 / 20 / 22 / 1), each log carrying its own tag.

⚠ An earlier detector (`probe2`) keyed on "a run of writes not a multiple of 5" and **would have
scored the fix as the defect**, because the fix prepends a reset making the run six long. `probe3`+
model the actual shift register instead. If you build a new instrument, check it for that inversion.

### 3b. Functional — 18,000 frames, matches allowed to END

| arm | started | clean ends | catastrophic aborts | searches / completions |
|---|---|---|---|---|
| v8 plain | 20 | 19 | **0** | 153 / 142 |
| v8 + tuck | 19 | 19 | **0** | 149 / 141 |

A crash-clean cart that cannot play is not a pass; this is the other half. Numerically
indistinguishable between arms.

### 3c. Execution — did tucks actually happen?

23 executed tucks / 131 pills / 19 matches = **60.5% conversion** of published descriptors.
Failures: 10 descriptors arrived after the capsule passed the trigger row, 5 never switched to the
final column, **`fail_land = 0`**. Recorded for the file — this cart ships with tucks off.

### 3d. Long soak — the main event

**674,487 frames = 3.12 h emulated, 2.00 h of live play, 751 match-ends, 3 independent seeds.**
That is 37× the previous gate, which covered ~5 minutes and bounded the crash rate at only
1 per 100 s.

Every cart canary **zero**: mixed PRG loads · RAM wipes beyond baseline · bank-0 beyond power-on ·
BRK-loop hits · stuck-BUSY · unrequested title returns · 4→0 aborts · tuck-executor writes (this
also proves the cart under test really is `DRTUCK=0`) · mode stalls · boundary stalls · search stalls.

> **Two counters have non-zero *healthy* baselines and are reported baseline-corrected.** `wipes`
> fires on any `$0324` →0 transition and the end of every match legitimately does that: 751
> zeroings against 751 match-ends, exactly 1:1. Printed raw, a clean cart looks like 751 failures.
> The real canary is `wipes_anom = 0`.

**Killed-mutant validation: 9 of 12 detectors were made to fire on purpose.** `s-val-mech` drove
mixedPRG=14, wipes=15, soft8036=16, title0=14, abort=1. `s-val-busy` drove busyEp=1. `s-val-title`
drove modeStall=1, gapStall=2, title0=1. `s-val-tuckwr` drove tuckwr=1750 against 0 everywhere else.

**Rule of three**: zero events over 2.00 h of live play → λ = −ln(0.05) = 2.996 → **≤ 1 crash per
40.1 minutes of live play** at 95% confidence. Against wall-clock emulated time, 62.4 min. Against
match boundaries, 1 per 251.

I lead with the live-play figure because it is the conservative one. Only 64% of the run is mode 4,
and every driver hook — hence every MMC1 bank switch, which is the hazard's actual exposure —
happens there. **This clears a 20-match evening comfortably, but it is ~40 minutes of live play,
not a whole evening. Do not round it up.**

### 3e. The event the soak found

A fourth segment (seed 30011) ran 43 matches cleanly, then **match #44 started at f=37,471 and
never ended** — mode 4 held for 82,529+ frames.

- It is a **freeze, not a slow match**: the framebuffer was byte-identical across 7 minutes while
  Mesen ran at 60.1 fps and its own counter advanced 30,000 frames. A stall still animates.
- The board is frozen **mid-game** at 48/48 viruses with low stacks — nowhere near a natural end.
- It is **deterministic**: a re-run froze at the same frame.
- **Every crash canary stayed zero through it** (mixedPRG=0, wipes=43, aborts=0). So this is *not*
  the MMC1 fault we fixed. It is a different, unidentified fault.
- **Two causes were raised and both killed.** Silicon START-injection: the trigger byte sequence
  `A9 10 85 F5` is *absent* from this cart (compiled out under `DRHUMAN=1`). Harness START leak: a
  stale one-frame mode cache meant a START press could land across the 8→4 transition, and pressing
  START there **reproduces the signature exactly** — but fixing the guard **did not prevent the
  freeze**. Sufficiency proven, necessity failed, hypothesis refuted.

⚠ **This segment is EXCLUDED from the 40.1-minute headline above**, which pools only the three
clean segments. That exclusion is legitimate for the *crash* class (this was not a crash) but you
should see the number it produces for the *hang* class: 1 event in ~712k frames of exposure →
**≤ 1 per 41.6 min of emulated play**, point estimate 1 per ~3.3 h.

In the unit that matters: **1 freeze in ~795 matches.**

| evening | point estimate | 95% upper bound |
|---|---|---|
| 10 matches | 1.3% | 5.8% |
| **20 matches** | **2.5%** | **11.3%** |
| 30 matches | 3.7% | 16.4% |

A freeze costs you a match and a reset, not the evening or the cart.

⚠ **Instrument limitations found in my own work, which bound how much the above is worth**:
`srchGapMax` hit 1,199 in the real freeze, in the deliberate-pause arm, *and* in the guard-fixed
arm — that signature **cannot discriminate "paused" from "wedged for another reason"**. And the
GAP-STALL detector never resets its reference on match start, so it measures time since the last
match *ended* and fires on any long match; **its f=40,777 firing carries no information.**
MODE-STALL is the valid signal.

---

## 4. Silicon

**Status: the cart you are about to play has never been run on silicon. Not once.**

What was actually run, on MiSTer:

| | |
|---|---|
| ran | `m-v8auto` — an **auto-nav sibling**, not this cart |
| result | 15 match segments / **14 boundaries clean** in ~18 min at L11, virus counts advancing, zero frozen intervals through every boundary |
| field symptoms | **no** corrupt title, **no** blue bars, **no** garbled tiles across all 107 verified screenshots |
| then | a ~12-min unrecovered **pause-wedge** — the DRSTUDY pause overlay over an intact board |

Two structural blockers stopped the real cart from running there, neither of them a cart defect:

1. **Wrong mailbox window.** This cart is `DRPOCKET=1`; the MiSTer core has its single copro at
   `$5200`. The ship cart would poll `$5000` = open bus and never see DONE.
2. **No input path.** With `DRHUMAN=1` the autonav is *deliberately* inert — the human is P1 and
   navigates for themselves. With no human, and MiSTer's input bridge a silent no-op, it sits on
   the title forever. (Confirmed on the unhardened control too, which is what stopped this being
   reported as a hardening defect.)

The wedge was traced to a START-injection path with **2 sites in the sibling and 0 in this cart** —
a check that could have failed and didn't.

> ### ⚠ Correction to the "Pocket-tuned constants" framing
> **`DRPOCKET` is not a set of Pocket-tuned timing constants.** It has exactly one effect anywhere
> in the emitter: it moves the copro mailbox window base from `$5200` to `$5000`. That is all.
>
> The consequence is what matters: **this MiSTer run exercised neither the `$5000` mailbox window
> nor Pocket DONE latency — and both of those are what actually ships.** "Played 14 boundaries
> clean on MiSTer" is evidence about the P2 driver and the crash hardening in general; it is
> **not** evidence about the configuration on your card.

---

## 5. What this gate CANNOT see

Stated plainly, because the last cart shipped on a harness that could not reach the state where its
bug lived, and the one before that on numbers that were true and irrelevant.

1. **The accumulator check was OFF for the entire soak.** The canary table prints
   `MISMATCH 0 ≤ 1 per 40.1 min` — and that row is worthless. The accessor never resolved the
   accumulator (`on=false, tried=0, ok=0`): it sampled A **zero times in 674,487 frames**. A check
   that cannot fail is not a check. **This is the exact defect class that withdrew the previous
   cart**, and the reason to believe it is fixed here is that I read the bytes — v6e carries the
   15-byte A-preserving form `48 AD 2E A0 … 68 40` at both shield mirrors, and the broken
   `AD 2E A0` sequence appears nowhere in the file — **not** because anything measured it running.
2. **P1 is an idle seat in every single frame of this evidence.** No human ever pressed a button.
   dr. lulu will. Every match in the soak is the AI against a player who tops out fast — median
   match ~570 frames, versus minutes for a real one. Whole classes of state (a contested board, a
   long endgame, garbage arriving under pressure) are **unreached**, and "unreached" is precisely
   how the last bug survived its gate.
3. **Zero minutes on an Analogue Pocket.** Emulation and one MiSTer run on a different sibling
   cart, with a different mailbox window.
4. **The freeze cause is unknown.** Not attributed to this cart and not exonerating it. The
   cross-cart control followed an identical trajectory to match #43 but timed out before resolving
   #44 — that leans against a regression without proving it.
5. **Three detectors were never validated**, so their zeros are not evidence: `srchStall`,
   `brk_a02e`, and the A-integrity check above.
6. **Two stall detectors passed validation only at lowered thresholds** (600) and would have read 0
   at the shipping 7,200 / 3,600.
7. **No strength upgrade.** This cart plays exactly as well as the build she has already been
   beating. The gate says it will not crash on her; it does not say it will win.

---

## 6. Installing it

Once the SD card is back in the reader:

```bash
cd /home/struktured/projects/dr-mario-v8-wt/release/v8_20260810
./install_to_pocket.sh
```

It verifies the md5 **before** touching the card, refuses to overwrite an existing file of that
name, refuses to guess if two cards are labelled `POCKET-SD`, and aborts if the card is absent.
Verified just now with the card out — it stops at:

```
== verifying the artifact before touching the card ==
ok: c0082cb34259007854120d3d4ab9fa27
== locating the Pocket SD card ==
ABORT: no mounted volume labelled POCKET-SD.
```

The copy is staged through a `.part` and only renamed into place after the staged bytes verify, so
a truncated write can never leave a corrupt cart at the real filename. **Do not "simplify" that
into a direct copy with an md5 check afterwards** — that reintroduces the original bug while
leaving a verify step visible in the code. Destination is `Assets/nes/common`; v4 and everything
else already on the card are untouched.

Optional second cart, `v8 REMATCH + board hold (optional).nes` (`c9364b26…`, via
`./install_boardhold.sh`): identical but the end-of-match board stays visible. It differs by one
flag and measured clean, but it has **one** 18,000-frame gate and **no soak**. See `WHICH_CART.md`.

---

### If something goes wrong tonight

- **Frozen mid-match, board visible, nothing moving** — that is the known event. Reset and carry
  on; it did not corrupt anything in 795 matches.
- **Drop to a corrupt title, blue bars, garbled tiles** — that is the *old* crash, the one this
  cart is supposed to have fixed. If you see it, stop using this cart and note the level and
  roughly how long you had been playing.
