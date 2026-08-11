# On-screen virus-counter decoder result

The scalar counter is the right observation target for remaining-virus timing: the older
grid classifier can miss viruses during pale animation frames. Neither registered decoder
version passed its complete instrument gate, so no decoded timeline is authorized yet.

## V1: NO_GO

The P2-only decoder got all anchors and the m2/m3 monotonicity checks right. It failed because:

- m1 contains a real visible new-board reset from 11 to 48 at seconds 45--46, while the
  preregistration incorrectly required monotonicity across it;
- the frozen absolute Hamming cutoff was 0.010, but valid JPEG variation reached 0.01196.

The relative nearest-glyph margin remained large (minimum about 0.161), but thresholds were
not changed after seeing the result.

## V2: NO_GO

V2 was frozen at commit `9468a84` before decoding the P1/Lulu sequence. P1 used mirror boxes
and no P1 frame supplied a template. All m1/m2 anchors, all P2 anchors, and all monotonicity
checks passed. The held-out P1 images exposed a style/domain shift:

- valid P1 glyphs reached Hamming distance 0.05024 versus the frozen 0.020 ceiling;
- the final m3 P1 anchor decoded `00` rather than the expected visible `02`;
- consequently the confidence and endpoint gates failed.

This is a decisive instrument failure, not permission to widen the cutoff again. A future
attempt needs a new representation and a validation source independent of its templates,
not a V3 threshold adjustment. Until then, use hand-verified endpoint counters only and do
not derive behavior claims from automatic clear timing.

