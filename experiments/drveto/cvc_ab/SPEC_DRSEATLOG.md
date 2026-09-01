# SPEC (decision document, NOT a change): cart-side "which seat topped out" log

**For the owner's ruling. Nothing has been built. No cart, core, or box has been touched.**

## Why this exists

The DRPROPH A/B could not be measured because **both instruments are pixel-based** — the
MiSTer framebuffer poll and the OBS video — so they share a failure mode and neither can
arbitrate the other. Measured on the run: they disagree in **both** directions at
**arm-dependent** rates (poll over-flags 45% control / 20% treated; poll MISSES 53% / 87%).
There is currently **no ground truth** in this measurement system.

**The game knows who died.** A cart-side log is independent of both pixel instruments by
construction, and it is the durable fix — the emulator route can at best characterise a
detector defect, not supply truth on silicon.

## 1. WHAT TO LOG, and where the information already is

The driver's hook already reads everything needed:

| datum | address | note |
|---|---|---|
| game mode | `$0046` | `==4` is live play; the go_ai gate |
| P1 board | `$0400` | 16x8, `$00`/`$FF` empty |
| P2 board | `$0500` | same |
| P1 viruses | `$0324` | **BCD**; `0` = that seat CLEARED |
| P2 viruses | `$03A4` | same |
| match latch | `MATCH_ACTIVE $6164` | set once play is dispatched |

**Proposed record (4 bytes per match end):**
`[ throat_p1 | throat_p2 | vcount_p1 | vcount_p2 ]`
where `throat_pN` = were cells (0,3)/(0,4) of that seat's board occupied — **the ROM's one
and only loss condition**. A seat with `vcount==0` cleared and won; otherwise the seat whose
throat is occupied is the one that plugged. That is the exact arbitration the pixel
instruments are guessing at.

## 2. ⚠⚠ THE TRAP THAT MAKES THE NAIVE DESIGN FAIL

**The boards are DESTROYED SYNCHRONOUSLY at match end.** The emitter's own comment:
*"RB337_STAGE_CLEAR/TOP_7 destroy `$0400`/`$0500` synchronously, before this hook can react
to the SAME frame's transition"* — this is precisely why `DRHOLDBOARD` exists.

⇒ **Sampling at the play→not-play transition reads WIPED boards and would log garbage that
looks plausible.** (`DRHOLDBOARD=0` in the shipped snapshot, so its mirror is not available
either.)

**Therefore: latch continuously during play, do not sample at the end.** Each go_ai hook,
write the 4 bytes above into a fixed 4-byte latch (not a ring). At match end the latch
already holds the last live values. Cost is one write per hook of data already in registers.

## 3. WHERE IT GOES, AND HOW IT IS READ BACK

**Storage:** 4 bytes from the documented free run **`$61C7-$61FF` (57 B)** — clear of
`PROPH_DIR $61C6` and of the `$6186+` DRPROBE ring header. A 16-entry ring (64 B) does not
fit that run; a 4-byte latch plus an 8-entry ring (32 B) does, if history is wanted.

**⚠ READBACK IS THE OPEN PROBLEM, AND IT IS THE REASON DRPROBE IS NOT ALREADY THE ANSWER.**
`DRPROBE` logs `($0046,$0727,$04)` — mode transitions, **not which seat died** — and is read
**via save-state**. This run's own freeze dossier recorded **`savestate trigger did not
produce a new file`**, so the save-state path is suspect on this rig.

Options, none yet validated:
* **(a) render it on screen** — draw the 4 bytes into an unused HUD region and let the
  EXISTING video decoder read them. Ironic but sound: the pixels would then carry a
  cart-computed *fact* rather than a pixel *inference*, and the decoder's job drops from
  "infer a death" to "read 4 digits", which it already does reliably for the virus counters.
  **This is the recommended option** — it needs no new channel and reuses a validated reader.
* (b) fix/verify the save-state path — unknown cost, currently failing.
* (c) a new UART/BoardTap channel — heavier, and there is a banked UART collision hazard.

## 4. BYTE COST

Latch-only, ~20-30 B of 6502 in the go_ai path (4 loads + 4 stores + the throat test on two
boards). Option (a) rendering adds a small HUD draw. Well inside the free run and well
inside the ~4.6 kB of free PRG-ROM measured on this lineage.

## 5. GATE PLAN

* **`DRSEATLOG=0` must rebuild BYTE-IDENTICAL** to the current arm (md5 + cmp), the standard
  this program already applies to every flag.
  ⚠ Expect the **emitter-lineage trap**: a byte-identity gate on this program can fail on
  the lineage rather than the flag (the `FC_STAB $61BB→$61C4` relocation). **Build the
  old-emitter control before concluding the flags differ.**
* **Mutant that must FAIL:** a variant that samples at the play→not-play transition instead
  of latching during play. It must produce demonstrably wrong seat attribution — that is the
  §2 trap, and a gate that cannot catch it is not testing the thing that matters.
* **Cross-check against the pixel instruments** on the same rounds: the log's disagreement
  rate with each instrument *is* the calibration we currently lack.
* PRG-RAM deriver `--check` green with a new config covering the flag.

## 6. ⚠ THE RISK, STATED PLAINLY

**It touches the driver, which is the freeze-prone layer.** This lineage has a documented
freeze history (5 reloads in the watcher's life, one inside this very A/B) and the
`#133`-class OAM tell has now appeared on a second cart, so the freeze mechanism is **not**
closed.

What could destabilise:
* **added hook cycles** — the driver already overruns the frame by design on the
  `p1_search` hook (94,791 cyc, absorbed by DRRTIVEC). More per-hook work narrows an already
  strained budget. **Mitigation:** run the `#126` frame census on the new image and require
  the worst non-search hook pair to stay inside 29,780 cycles.
* **a new PRG-RAM writer** — the collision class this program has been bitten by twice.
  **Mitigation:** the deriver's `--check`, which already catches exactly this.
* **the latch runs every hook**, so a bug is continuous rather than rare — which cuts both
  ways: it would show up immediately in a soak rather than hiding.

**How it would be caught:** the existing pre-push hazard suite (`test_rtivec`, `test_mmc1rst`,
`test_rtivec_aclobber`, `test_prg_ram_map`, `test_combo_cart`) plus a soak on the CvC pairing
watched by `freeze_watch`, compared against the banked freeze rate rather than against zero.

## RECOMMENDATION

Approve the **latch + on-screen readback (option a)** variant. It avoids the save-state
dependency, reuses a validated reader, and its failure mode is loud. The measurement lane
stays blocked until something arbitrates, and this is the only candidate that supplies truth
on silicon rather than characterising an instrument.
