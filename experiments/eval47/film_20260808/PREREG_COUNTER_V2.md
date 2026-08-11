# Dual-side on-screen counter decoder v2 — pre-registration

**Frozen after V1 failed and before any P1 sequence was decoded.** V1 remains a registered
failure: its absolute-distance cutoff 0.01 was 0.00196 tighter than real JPEG variation, and it
incorrectly required m1 to be monotone across a visible new-board reset at seconds 45→46.

## Unchanged decoder

Digit templates, threshold, and nearest-Hamming classifier are byte-for-byte V1. P2 boxes are
unchanged. P1 uses the mirror counter boxes `(861:899, 926:959)` and
`(905:943, 926:959)`, the same 38x33 glyph size. No P1 frame supplies a template.

V2 confidence is frozen at best distance <=0.02 and second-best margin >=0.12. The 0.02 limit
is above V1's observed JPEG maximum 0.01196 while still eight times below the observed nearest
wrong-glyph separation (>=0.161). The relative margin remains the load-bearing discriminator.

## Held-out P1 gates

- m1: second 45 is 11, second 46 resets to 48, then 46..260 is non-increasing and ends 14.
- m2: 265..549 is non-increasing, 48→05.
- m3: 555..738 is non-increasing, 48→02.
- Every P1 glyph clears both confidence limits.

These anchors are the game's own visible digits and match the already-recorded film endpoint
table. The complete intervening P1 timelines have not been decoded or tuned against.

## Continuity P2 gates

- m1: 45=11, 46=48 reset, then non-increasing to 06.
- m2: 48→02, non-increasing.
- m3: 47→06, t=567 is 41, non-increasing.
- Every glyph clears both V2 confidence limits.

## Killed mutants

- Swapping digit-1 and digit-7 labels must fail anchors/monotonicity.
- Shifting both P1 boxes +8 pixels must fail anchors or confidence.

Passing validates scalar count and clear timing only, not per-cell virus identity.
