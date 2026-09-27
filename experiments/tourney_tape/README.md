# Nutmeg Regional tape analysis (DrMC broadcast, recorded 2026-09-13 23:46, 7h20m file)
Pipeline: 1fps frames; era classifier (HUD-box luminance probes); per-era grid fits; hue-based board
reader (`treader.py` — stream palette is far duller than our capture); HUD digit OCR by anchor-labeled
template matching (I read ~20 frames' values by eye at full res; templates propagate; tesseract FAILED
validation on this pixel font and was rejected).

## Eras found
- L1 "4-bottle prelims" (two matches at once, VIR+SPD per bottle): 9 segments, 1h22m, 0:03-2:21.
- L2 "Top 8 spotlight" (one 1v1, big bottles, names + round crowns): 4 segments, 1h01m, 1:17-3:14.
  Players seen: Leviticus, Parula, Ktizzle, Pangolin (name plates hash-clustered, labeled by eye).
- After 3:14: unrelated re-broadcast ("July Silver Speed Bracket") + hours of offline — not analyzed.

## Decode quality
L1: 82.7% clean per digit-cell; L2 after second-font anchors + header gating: 97.6% per counter.
Board occupancy validated against on-screen VIR (occupied >= HUD viruses on all 4 validation bottles).

## Status / caveats (honest)
- 27 L2 games segmented; 8 with a decisive VIR->0 winner (Ktizzle 3, Pangolin 3, Leviticus 1, Parula 1).
  Remaining games end without either counter reaching 0 (topout/forfeit/segment-truncation) — winner
  attribution for those needs the game-over graphic, not the counters.
- ⚠ OPEN QUESTION — FORMAT: left/right VIR starts frequently DIFFER (55/5, 59/12, 56/3...). In NES VS
  both bottles start equal. Either the splitter still misplaces some starts, or this event runs a
  race/handicap format. The crude send test (garbage-arrival within 4s of an opponent multi-clear:
  77/431 = 18%) does NOT yet confirm garbage VS. Discriminating test owed: 2-4fps re-scan of a few
  games -- NES VS garbage lands as 2-4 half-pills in distinct columns on one frame; unmistakable at 4fps.
- SPD counter rises during a game (26->63 observed) — consistent with the ROM speed ramp, recorded not interpreted.
Raw series in tmp/tourney/ (not committed: ~4GB frames); scripts here re-derive everything from the MKV.
