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
