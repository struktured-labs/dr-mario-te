# Level-select garble: now ASSERTED, not screenshot-corroborated

Closing the gap recorded in `dr-mario-te-v9-standalone` ("level-select garble is only
screenshot-corroborated, not asserted"). Measured 2026-08-01 with
`dr-mario-qa-wt/tools/standalone_study_qa.lua`, which hashes the level-select nametable
and counts non-blank tiles. All runs `DRQA_MODE=1p` so the comparison is like-for-like.

| cart | md5 | `$BE56` (old study part3b) | NT hash | non-blank |
|---|---|---|---|---|
| v8.0 `drmario_te_v8.nes` | `be75fc4752560d9d76d025fb17a9352f` | **part3b present** | **977865308** | 949 |
| v8.2 `before_v82.nes` | `38cc2308d3a26b95c4058090a01f9f24` | vanilla | 3195770790 | 958 |
| v9 `drmario_te_v9_standalone.nes` | `2bed63a20b74482329b11735b8ab840f` | vanilla | 3195770790 | 958 |
| **v9d `drmario_te_v9d_bcdfix.nes`** | `0f8f5d89dcf938144d24977d4faf2628` | vanilla | **3195770790** | 958 |

**The assertion is two-sided, which is what makes it evidence rather than a coincidence:**

- **Negative control** — v8.0, which still has study part3b sitting inside the print table
  at `$BE56`, produces a DIFFERENT nametable: a different hash and **9 fewer non-blank
  tiles**. That is the garble, measured rather than eyeballed.
- **Positive controls (x2)** — v8.2 and v9, both of which restored `$BE56` to vanilla,
  hash identically to each other.
- **The release candidate matches the clean group exactly**, byte-for-byte on the hash.

A one-sided check ("v9d looks fine") could not have distinguished "the garble is fixed"
from "the harness cannot see the garble". The 9-tile delta proves the instrument responds
to the defect it is being used to rule out.

## Reproduce

    cd /home/struktured/projects/dr-mario-mods
    DRQA_OUT=<dir> DRQA_MODE=1p timeout 95 ./run_mesen.sh <cart.nes> \
      /home/struktured/projects/dr-mario-qa-wt/tools/standalone_study_qa.lua \
      --donotsavesettings
    grep LEVELSEL_NT <dir>/standalone_study_qa.log

★ Mesen2 does not exit on `emu.stop(0)` from this probe — run under `timeout` and reap the
process (`pgrep -x Mesen`). The log lands well inside 95 s. Mesen2 is single-instance, so
one run at a time.

## Logs

`qa_v9d/` (2P, 13/13), `qa_v9d_1p/` (1P, 11/11), `qa_v80_1p_hash/` (negative control),
alongside the pre-existing `qa_v9/`, `qa_v9_1p/`, `qa_v82_1p/`.

---

# Addendum: are BOTH virus counters proven at a TWO-DIGIT value?

Raised 2026-08-01, because below 10 **BCD and binary are identical** — so any observation at
a count of 4 structurally cannot distinguish a BCD-correct render from the 48→"72" failure
class that v9d exists to fix. Three separate questions, answered separately.

**1. Does the digit truth table exercise two digits?  YES — it injects.**
`prove_v9d_digits.py` feeds every value 0..99 to each counter, plus a boundary
cross-product including 48, 84 and 99. Level 0 is irrelevant to it. Its docstring also
records *why* the premise is stated explicitly: the v9b/v9c truth tables fed BINARY to the
virus counters, self-consistent with the code's wrong assumption, so 656 passing runs
proved nothing about the real format. A truth table that supplies its own input can never
validate the source format — only the routine.

**2. Is P1's source format confirmed at two digits?  YES, twice.**
`qa_format/pause_digits.log` — 84 viruses at level 20, correct in play AND after the STUDY
pause. Re-confirmed independently on 2026-08-01 against the ROM produced by applying the
shipping BPS to a clean base: **P1 byte `$68`, BCD-decode 68, rendered 68, in study pause**
(`qa_v9d_2digit/`).

**3. Is P2's source format confirmed at two digits?  NOT DYNAMICALLY — and
`format_probe.log` said so itself: `VC_P2: AMBIGUOUS (<10, rerun higher)`.** That rerun was
never done; every observation of `$03A4` has been below 10. An attempt on 2026-08-01 to
drive both players to a high level got P1 to 68 but could not move P2's level-select cursor
via port-1 input under this Mesen build.

**It is instead settled STATICALLY, which is the stronger argument.** Both players' counters
are *the same variable*, maintained by *the same code*, with explicit decimal-adjust
arithmetic (`prg/drmario_prg_game_logic.asm`):

    decrement (:1524)   dec currentP_virusLeft / and #$0F / cmp #$0F
                        bne .. / lda / sec / sbc #$06      <- BCD borrow fixup
    increment (:3268)   inc currentP_virusLeft / and #$0F / cmp #$0A
                        bne .. / lda / clc / adc #$06      <- BCD carry fixup

`currentP_virusLeft` is swapped in and out of the per-player blocks by `p1RAM_toCurrentP` /
`p2RAM_toCurrentP`, the same $30-byte copy used for the controller state. There is no
P1-specific or P2-specific counter path. **So if P1's counter is BCD, P2's is BCD by
construction** — for every value, not merely for the ones a probe happened to reach. The
game's own arithmetic is the authority, exactly as it was for the original BCD discovery.
