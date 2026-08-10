# Which cart to play

Two carts here. They differ by **one flag**. Both carry the corrected NMI shield.

| | **`v8 REMATCH (hardened).nes`** | `v8 REMATCH + board hold (optional).nes` |
|---|---|---|
| md5 | `c0082cb34259007854120d3d4ab9fa27` | `c9364b2670a7a0e0292e56264d9f231b` |
| board hold | off | **on** — end-of-match board stays visible |
| install | `./install_to_pocket.sh` | `./install_boardhold.sh` |
| evidence | 18,000-frame gate **+ a ~900k-frame, 4-seed soak** | 18,000-frame gate only |

## Recommendation: play the first one

Not because the second is suspect — it measured clean — but because the **soak is running on the
first one**, and a bound you can quote is worth more than a feature you can see. If the soak comes
back clean, the hardened cart is the only artifact with a play-length number behind it.

## Why board hold is back at all

It was pulled because `DRHOLDBOARD=1` soft-bricked the cart after a match. That turned out to be
the MMC1 shift-register interleave, which `DRMMC1RST` + `DRRTIVEC` now block outright.

Then a *second* problem appeared: the end-of-match hold re-armed every hook and thrashed during
live play — 23 of 25 arms firing in mode 4 at a full clear. It was reported as an independent
defect, and a latch (`DRHOLDONCE`) was built to fix it.

**That was wrong, and the correction is the good news.** Same flags, same harness, same seed,
same 18,000 frames — the only delta being the 15-byte accumulator fix:

| build | holdARM by mode | matches | clean ends | aborts | arm/release |
|---|---|---|---|---|---|
| pre-fix (A clobbered) | **23 in mode 4**, 2 in mode 7 | 3 | 2 | 0 | 25 / 25 |
| v6e (A preserved), no latch | **0 in mode 4**, 17 in mode 7, 1 in mode 5 | 19 | 18 | **0** | 18 / 18 |

With the accumulator preserved, the hold arms **exactly once per match end, in the right mode**,
and releases every time. `patho_frames = 0`. So the thrash was a *third* symptom of the
accumulator clobber, not a defect of its own.

`DRHOLDONCE` remains in the tree, **default OFF and byte-inert** (`DRHOLDONCE=0` rebuilds
`c0082cb3` exactly). It is deliberately **not enabled**: it would fix a defect that no longer
exists, at the cost of a RAM byte and two code sites.

## What neither cart has

- **Tucks.** Not deliverable to the Pocket: that core has no θ mechanism at all, and the
  descriptors it does publish stranded the capsule 4 times out of 4. See task #101/#102.
- **A silicon bound.** Both are gated in emulation only.
