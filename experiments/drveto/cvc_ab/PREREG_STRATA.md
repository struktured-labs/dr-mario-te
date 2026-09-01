# PRE-REGISTRATION: champion-death strata for the DRPROPH CvC A/B

Registered 2026-09-01, on the team lead's ruling, **BEFORE any death was scored under
it**. At registration time the corpus was 5 champion topouts (L20 proph arm), none of
which had been evaluated against this condition.

## Why not the viruses-left proxy

Viruses-left-at-death was my quick index and it did its job -- it is what caught that
the L20 CvC deaths (82-83 left of 84) are a different population from the banked L20
farm (median 41 left). But it is a *correlate* of "the board was too full for an escape
to exist", and this program has been burned repeatedly by proxies that return the same
value under two different worlds (R93). The direct measurement is available: frame-
accurate video plus a validated board decoder. So the stratifier is the mechanism's own
eligibility condition, **computed the way the firmware computes it**, not a stand-in for it.

## The condition, transcribed from the emitted code

Source: `patch_cartridge_copro.py`, `proph_trigger` (read from the emitter, not from its
comment). Board is 16 rows x 8 cols at `$0500`; index = `row*8 + col`. A cell is EMPTY
iff its byte is `$00` **or** `$FF` (the DISTGATE/TUCKGUARD dual-encoding rule).

```
fo(col) = first row 0..15 whose cell is occupied; 16 if the column is empty
TRIGGER  : fires iff fo(3) <= 2 OR fo(4) <= 2          # spawn-rest throat ledge
DIRECTION: fo(4) >  fo(3) -> prefer RIGHT              # toward the DEEPER side
           otherwise      -> prefer LEFT               # (ties -> LEFT)
GATE(LEFT ) = cells (0,2) and (1,2) both empty         # $0502, $050A
GATE(RIGHT) = cells (0,5) and (1,5) both empty         # $0505, $050D
ELIGIBLE : preferred side's gate free, ELSE the other side's gate free
           both blocked -> PROPH_DIR = 0, stand aside
```

## The board it is evaluated on

The trigger runs at the **new-P2-pill edge**, so the board of record is the PARENT board
-- before the fatal capsule locks. On video: walk back from the start of the death hold
to the last frame where P2's throat cells (0,3) and (0,4) are both unoccupied, and use
that frame. At L20 gravity is fast (the lock window is ~8-10 frames), so at 10 fps this
frame is within ~0.1 s of the spawn.

⚠ Known limitation, stated up front: this is the board as the VIDEO sees it, not the
`$0500` bytes. It cannot distinguish `$00` from `$FF` (both render as empty, which is
what the firmware treats them as anyway), and a capsule mid-fall above the stack is
indistinguishable from a locked cell. The walk-back to a clear-throat frame is what
bounds that error.

## Strata (fixed now; counts published with every result)

- **ADDRESSABLE** -- trigger fires AND an eligible escape side exists.
  **The A/B contrast is read HERE and only here.**
- **UNADDRESSABLE** -- trigger fires, both gates blocked. Reported as a RATE, never
  pooled into the contrast. DRPROPH standing aside here is *correct behaviour*, not
  failure.
- **OTHER** -- no spawn-rest geometry at the parent (`min(fo3,fo4) > 2`): garbage plugs
  and anything else. Reported, excluded from the contrast.

## Exposure statement, required in the headline sentence of any result

If ADDRESSABLE is a small minority at L20, the correct conclusion is
**"L20 is the wrong amplifier for this mechanism"**, NOT "the prophylactic does not
work." Those are different findings and only one of them is about DRPROPH. A reader must
be able to see how much of the death population the mechanism could ever have touched,
so all three counts are published together, with the regime label attached.

If ADDRESSABLE stays rare after a reasonable N, the counts go to the team lead and an
intermediate level (the ROM clamp is 20, so 15/16 are reachable) is considered -- chosen
for the MECHANICAL reason that boards must be playable enough for an escape to exist,
never because a level produced a nicer number. That distinction goes in the record if
the move is made.
