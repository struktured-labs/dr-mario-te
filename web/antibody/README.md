# Play ANTIBODY in the browser

`index.html` is a Dr. Mario VS game: you (P1) against ANTIBODY (P2), the canon Rx champion of
2026-09-27 (`experiments/cvx/SOTA_20260927.md`). Serve the folder and open it:

    python3 -m http.server -d web/antibody 8000   # then http://localhost:8000/

- `antibody_brain.js`: JS port of the ANTIBODY decider, `cascade_leaf5b_x._choose_d3_chain_s_leaf5`
  with the `s5b_hsv512` arm (winner leaf, depth 3, top-8, fixpoint cascades, chain 540, strand 20,
  HSV 512) and the `reach_fw_tap` REACH mask at tap=2.
- `antibody_worker.js`: runs the search in a Web Worker. The page falls back to the main thread.
- `test/check_parity.js`: `node web/antibody/test/check_parity.js` checks the JS brain against
  200 Python golden decisions (action and REACH mask). Regenerate with `test/gen_golden.py`
  (needs numba).

Controllers: any pad the browser's Gamepad API sees (USB or Bluetooth) drives P1. Standard-mapping
pads use the d-pad/left stick, right face button = A, left = B, Start, Select. Generic USB NES/SNES
pads (non-standard mapping) are read from axes 0/1 or the POV hat on axis 9; a "Swap A and B"
checkbox fixes pads that report the face buttons the other way round. Browsers expose a pad only
after a button press on the page.

The brain is exact. The game around it is an approximation of the NES: gravity uses the ROM speed
table and the bot's driver uses the silicon timings (19-frame answer, gravity pinned for 8 frames,
one tap every 2 frames, soft drop once aligned), but clear/cascade animation lengths, virus layout
and garbage colours are not frame-exact. No ROM data is included.
