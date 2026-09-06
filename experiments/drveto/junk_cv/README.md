# junk_cv — read Dr. Mario board junk from clean HDMI video

Validated 2026-09-06. Reads **per-seat junk** (non-virus occupied cells) directly
from 4K OBS HDMI frames of a MiSTer NES Dr. Mario CvC game — no on-cart counter, no
OCR. Supersedes the on-cart `DRJUNKCOUNT` counter (which does not render on silicon).

## Method
- Detect the two bottle interiors from the cyan bottle walls (fixed geometry per
  video mode; calibrated to bluemage's 3840×2160 output — 88 px/col × 8, 16 rows).
- Per cell: **occupied** = bright, not cyan-wall, not purple-checkerboard bg.
- **virus vs pill** = interior **dark-fraction** (virus eyes/mouth are dark; pills
  solid). Clean bimodal split: pills 0.00–0.01, viruses 0.22–0.39; threshold 0.10.
- `junk = # pill cells`. The **virus** count this yields matches the game's own
  on-screen VIRUS counter EXACTLY (validated on 3 independent live frames).

## Files
- `read_board.py` — the reader. `python3 read_board.py 'frames/*.png'`
- `obs_shot.py` — grab one 4K frame via obs-websocket. `OBS_WS_PASSWORD=… python3 obs_shot.py out.png`

## Result it produced (unbiased silicon, CvC L11, ~750 frames)
Champion (P2) junk by viruses-remaining: median rises to a ~14 plateau at 6–19
viruses, then eases to ~9 at 1–5 (survivorship), p90 tail ~22. The old
disagreement-corpus claim of "junk → 51 at the last virus, never sheds" is a
selection artifact — real median endgame junk is ~10–14, worst-decile ~22.

## Limits
- **CLEAN HDMI ONLY.** Does NOT port to phone-recorded VODs: virus faces don't
  resolve at ~33 px cells (phone moire/glare), which is exactly the dark-fraction
  signal this depends on. The north-star human/lulu matches need HDMI capture.
- Geometry is per video-mode; re-detect the cyan walls if it changes.
- A falling capsule (transient, top rows) reads as ~2 junk while airborne.

See the memory notes `dr-mario-cv-junk-reader` and `dr-mario-endgame-junk-accumulation`
for the full method, validation, and the corrected endgame finding.
