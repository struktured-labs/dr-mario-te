# P2 on-screen virus-counter decoder — instrument pre-registration

**Frozen before decoding the m1/m2 sequences.** This is an observation-instrument gate,
not a strength or player-behaviour arm.

## Why

The grid's dark/color sprite classifier is invalid for scalar virus count on this capture:
virus animation frames can be predominantly white/black and miss every color mask. At t=567 s
it reports 28 while the game's own P2 counter visibly reads 41. The game counter is the direct
ground truth and should be decoded rather than inferred from bottle sprites.

## Frozen method

- Source frames: the existing 1 fps full-frame capture, no re-encoding.
- P2 tens glyph: `[y=926:959, x=977:1015]`; ones: `[926:959, 1021:1059]`.
- Glyph mask: a pixel is ink when `max(R,G,B) < 100`.
- One m3 ones-glyph exemplar per digit, frozen as:
  `{0:568, 1:565, 2:604, 3:561, 4:628, 5:559, 6:616, 7:555, 8:613, 9:571}`.
- Decode each glyph by minimum normalized Hamming distance to those ten templates.
- Confidence requires best distance <=0.01 and second-best minus best >=0.12.

The template frames and labels were established from the m3 counter after the old grid-count
failure was known. m3 is training/continuity only. m1 and m2 are the validation windows.

## Frozen validation gates

- m1 seconds 45..260: P2 counter is monotone non-increasing, first=11, last=06.
- m2 seconds 265..549: monotone non-increasing, first=48, last=02.
- Every m1/m2 glyph clears both confidence margins.
- Continuity m3 seconds 555..738: first=47, t=567 is 41, last=06, monotone.

## Killed mutants

1. Swap the digit-1 and digit-7 template labels: at least one anchor/monotonicity gate fails.
2. Shift both digit boxes +8 px: at least one anchor or confidence gate fails.

No decoded sequence is accepted unless both deliberately wrong versions are rejected.

## Scope

Passing yields a trustworthy scalar virus-count timeline and clear-event timing. It does not
identify which grid cells are viruses and does not by itself support counterfactual legal-move
enumeration. Declined-clear analysis remains blocked until board identity also passes a control.
