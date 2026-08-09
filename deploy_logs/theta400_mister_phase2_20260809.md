# theta400 MiSTer deploy — Phase 2 log (silicon fingerprints + the silicon tuck proof)

Date: 2026-08-09 (all times UTC). Operator: subagent under owner authorization recorded on
task #98 ("you can test on the mister while im gone fwiw", 2026-08-09).
MiSTer: 10.42.0.226 (mister_ip.sh, re-resolved 17:44Z), CORENAME NES, framework argv
`NES_theta400_20260809.rbf + theta400_tuck_demo.mgl` confirmed before starting.
Continues deploy_logs/theta400_mister_phase1_20260809.md (liveness PASS).

**VERDICT: STEP 3 + STEP 4 PASS. 7/7 like-for-like placement fingerprints match the
real-firmware co-sim across 3 distinct boards; board-29 replicate identical twice;
the first tuck ever executed on silicon is confirmed byte-exact. STOP rule NOT
triggered. No soak started (out of Phase 2 scope).**

Co-sim truth sources: Mesen QA decisions
(`staging/tuck_cart_theta400/mesen_qa/run2_inject_board18/decisions.jsonl` seq5-6,
`run3_inject_hz30_29/decisions.jsonl` seq5-6) + fresh farm_vsim runs (fw_md5
f78f1e9376405dc996404f68dfa9dfb8 asserted per run) for the pills whose colors Mesen's
stream did not share (see "pill-ring" below) and for the natural board.

## Rig

- Template: single live capture `template.ss` (md5 2e1abe32, 17:45:23Z) — fresh P2 spawn
  (y$0386=15, x=4, mode $04, MATCH_ACTIVE=1), doubles as the natural-play board
  (occ 44 / 40 viruses, cur=(1,1) next=(2,2)).
- Injection: `evidence_silicon_phase2/fp_tool.py` — board $0500 + pill $0381/82 + next
  $039A/9B (internal RAM), then the rig reset recipe (ARMED2/WDOG2/WDOGH2=0, PEND2=1,
  DELAY2=0, ROT_DONE2=0, STABLE_CT2=0, SLAM_ARM=0, LASTY2=cur $0386) + NEW tuck-latch
  invalidation TUCK_C2 $6179=$FF, TUCK_R2 $617A=$FF (addresses per
  patch_cartridge_copro.py on this branch).
- Every load: scp slot file -> menu.rbf interleave (12 s) -> mgl (15 s) -> bare
  `input combo f2`; no load_core was ever issued mid-invocation. Readback: `cap.sh`
  (leftalt f2, remote stat poll size==1327112 + mtime change, scp).
- Silicon pill cadence measured ~1.3-1.5 s/pill (search ~60-73M copro clocks); the
  runbook's 4.5 s single-save window catches 3 locked pills, so the clean one-pill
  readouts below use ~1.5-2.0 s captures. GUARD occ==injected+2 enforced on the
  pill-1 readouts.

## Board 18 (hostdata_l11_20, pill (1,0) next (0,0))

- `b18_run2.ss` (F2 17:52:29.842Z, save trigger +1.97 s, md5 a9ac90e7): diff vs injected =
  added EXACTLLY (4,4)=$61,(4,5)=$70, removed 0, changed 0 (occ==injected+2 GUARD PASS);
  viruses 48/48, ctr 40. Expected (Mesen seq5 / co-sim col=4 o4=2): cells 4,4,$61;4,5,$70
  -> **MATCH cell-for-cell**. Bonus: pill-2's live target already published TGT_C2=6
  TGT_O2=3 TUCK_C2=$FF = co-sim seq6 (col=6 o4=0 -> game 3).
- `b18_run1.ss` (F2 17:47:55.888Z, save +4.3 s, md5 791c239e): deep-trajectory readout.
  Net diff: added (5,5)=$80,(6,3)=$82; removed (5,3)=$62,(5,4)=$71,(6,4)=$d1,(7,6)=$d0,
  (8,6)=$d0; TGT_C2=4 TGT_O2=0 TUCK_C2=5 TUCK_R2=12; viruses 48->45, ctr 40->37.
  Decodes as pills 1-3 committed + both predicted clears:
  p1 (4,4),(4,5) [co-sim col4 o4=2]; p2 col6 vertical [co-sim col=6 o4=0] completing the
  4-yellow col-6 clear (removes (7,6),(8,6) = 2 yellow viruses); p3 = ring pill (1,1)
  (silicon draw, see pill-ring) -> fresh farm_vsim run on the exact post-p2 board with
  (1,1)/(1,0): **col=4 o4=2 tcol=5 trow=3** -> silicon latched TUCK_C2=5/TUCK_R2=12
  (15-3=12, exact) and produced the exact 4-red col-4 clear (removes (6,4) virus) +
  orphan pattern ((5,3)->(6,3) as $82; (4,5)->(5,5) as $80; the second orphan mid-fall
  at capture instant). **A SECOND silicon tuck, latch value exact.**

## Board 29 (hostdata_l11_hz30 — THE SILICON TUCK PROOF; pill (0,2) next (2,2))

Expected (Mesen run3 seq5 / co-sim): col=3 o4=2 TUCK tcol=2 trow=4 -> driver latch
TUCK_C2=2/TUCK_R2=11, approach col2, DAS right to col3 at row 11, lock (4,3)=$60
yellow,(4,4)=$72 blue under the (3,4) lip; the 4-blue column (4,4),(5,4),(6,4),(7,4)
clears 2 blue viruses.

- Run A (F2 17:54:14.440Z):
  - `b29_runA_t14.ss` (+1.48 s, md5 7d36da1a): **THE LOCK INSTANT.** added exactly
    (4,3)=$60,(4,4)=$72 (occ==injected+2), TUCK_C2=2 TUCK_R2=11, TGT_C2=3 TGT_O2=0,
    pill x=3 y$0386=11 orient=0, clear not yet run (48 viruses, ctr 40).
    **First tuck ever executed on silicon — cell-for-cell identical to the Mesen
    reference (run3 seq5: cells=4,3,60;4,4,72 tuckC=2 tuckR=11).**
  - `b29_runA_t2.ss` (+5.07 s, md5 65e84164): post-clear trajectory: (5,4)/(6,4)/(7,4)
    blues + the locked (4,4) removed = the predicted clear; viruses 48->46, ctr 40->38
    (**exactly 2 blue viruses cleared**); p2 (2,2) locked (3,2)=$42,(4,2)=$52 =
    co-sim seq6 col=2 o4=0 **MATCH**; p3 ring pill (1,1) -> fresh farm_vsim on the
    exact post-clear board with (1,1)/(1,0): **col=7 o4=0** -> silicon (4,7)=$41,
    (5,7)=$51 vertical col7 **MATCH**; settle cells ((4,3)->$80 orphan, (4,6)->(5,6),
    (6,5)=$80, lip fall (3,4)->(4,4)) all consistent with Mesen's own settle
    (run3 f=458 line).
- Run B / replicate (F2 17:59:35.136Z): `b29_runB_lock.ss` (+1.52 s, md5 0d899ef3)
  caught the CLEAR-ANIMATION frame: all four blue cells of the column as pop tiles
  ((4,4),(5,4),(6,4),(7,4)=$F2), orphan relabels (4,3)=$80,(5,5)=$80, ctr already 38,
  latch/commit identical (TUCK_C2=2 TUCK_R2=11 TGT_C2=3 TGT_O2=0). **Determinism
  replicate #1: same lock, same latch, ~2 frames later on the same trajectory.**
- Run C (F2 18:00:52.378Z): `b29_runC.ss` (+4.5 s, md5 6e86aecd): diff IDENTICAL
  cell-for-cell to runA_t2 (all 16 diff entries equal; WDOG2 37 vs 41 = capture 60 ms
  earlier in pill-4's search). **Determinism replicate #2 at trajectory depth.**
- Screenshots (misterclaw-send): `b29_lock_shot5/6.png` (18:04:59Z/18:05:30Z, VIRUS
  47/40) caught the tuck pill MID-MANEUVER — yellow/blue horizontal pill descending at
  the approach columns 2-3, board pristine (zooms: b29_shot5/6_zoomP2.png);
  `b29_lock_shot4.png` (18:03:51Z, VIRUS 47/38) shows the post-clear outcome. The shot
  service's ~3 s latency + ~1 s jitter cannot reliably hit the 0.5 s lock window
  (5 calibrated attempts; anticipated by DEPLOY.md), so the cell-for-cell lock/clear
  comparison vs evidence/tuck_lock_s05.png rides the byte-exact save-states
  (runA_t14 = lock frame, runB = clearing frame) rather than pixels. Screenshot #3
  attempt left the box at MENU harmlessly for ~30 s (a backgrounding quoting slip,
  recovered by direct mgl load; logged for completeness).

## Natural-play board (template board, pill (1,1) next (2,2), search-reset only)

Expectation computed BEFORE the run on farm_vsim (natural1_expect.json): col=7 o4=0
tcol=255 (clocks 70.4M).
- `nat_run1.ss` (F2 18:06:53.545Z, +1.97 s, md5 4fa84cd2): capture caught the clear
  animation: added (7,7)=$F1,(8,7)=$F1 (the pill, already popping), changed
  (9,7)=$81->$F1,(10,7)=$d1->$F1 — pill locked col7 vertical rows 7-8, completing the
  4-red column that clears 1 red virus (ctr 40->39). TGT_C2=7 **MATCH**; placed cells =
  co-sim placement **MATCH**.
- TGT_O2 adjudication (recorded raw): byte reads 1 where map(o4=0)=3. For a monochrome
  (1,1) pill, o4 0/1 are the same physical placement with equal eval; the driver's
  orient latches at MIN_THINK (~5f) from the copro's live-published running best
  (pair-latch behavior, driver comments + dr-mario-pair-latch-defect), so the
  equal-value o4=1 candidate wins the byte on silicon while Mesen's time-frozen bridge
  always lands the converged byte. DEPLOY.md's own comparison rule ("orient from PLACED
  CELLS — mailbox orient byte is copro-space") reads orient from the landed cells,
  which match exactly. Not a decision mismatch; noted as a latch-timing artifact.

## Pill-ring discovery (why Mesen's seq7+ decisions are not silicon expectations)

Silicon draws pills 3+ from the TEMPLATE's capsule ring $0780 (index $03A7 points one
past next; cur=ring[idx-2], next=ring[idx-1], id->(id%3,id//3) verified on 3 captures):
template idx 13 -> p3=(1,1), p4=(1,0), p5=(2,1). Mesen's runs drew (1,0),(0,0),(0,0)
from THEIR deterministic boot ring. So seq7+ of the Mesen decisions are answers to
different pills — silicon's p3 pills were instead verified with fresh farm_vsim runs on
the exact boards silicon faced (both matched, incl. the second tuck). No mismatch —
different inputs, both sides co-sim-verified.

## Fingerprint tally (all raw readouts above)

| # | board | pill | co-sim expectation | silicon committed | verdict |
|---|-------|------|--------------------|-------------------|---------|
| 1 | l11_20 #18 | (1,0)/(0,0) pinned | col4 o4=2 | (4,4)=$61,(4,5)=$70, occ+2 | MATCH |
| 2 | l11_20 #18 | (0,0) pinned | col6 o4=0 | col6 vertical + 4-yellow clear | MATCH |
| 3 | l11_20 #18 | (1,1) ring | col4 o4=2 tcol5 trow3 | TUCK latch (5,12) + 4-red clear | MATCH (tuck #2) |
| 4 | hz30 #29 | (0,2)/(2,2) pinned | col3 o4=2 TUCK (2,4) | latch (2,11), lock (4,3)=$60,(4,4)=$72, 2 viruses | MATCH (tuck #1, replicated 2x) |
| 5 | hz30 #29 | (2,2) pinned | col2 o4=0 | (3,2)=$42,(4,2)=$52 | MATCH |
| 6 | hz30 #29 | (1,1) ring | col7 o4=0 | (4,7)=$41,(5,7)=$51 | MATCH |
| 7 | natural | (1,1)/(2,2) | col7 o4=0 | (7,7),(8,7) red vertical + 4-red clear | MATCH (TGT_O2 byte = pair-latch artifact, cells exact) |

## End state (18:08-18:09Z)

- CORENAME NES, theta400 running, match active, rounds cycling: NAV_T $26->$68 over
  22 s, P2 viruses 27->21, BUSY=$00/BUSYSKP=$00, ctr==popcount both boards, wram/iram
  bases signature-stable in every capture this phase (15 captures total).
- Prior champion + rollback chain untouched (nothing deleted/overwritten anywhere).
- NO soak units started; next = DEPLOY.md step 5 (soak + alarms) under its own scope.
- Evidence archive: staging `evidence_silicon_phase2/` (24 files + MD5SUMS): all .ss
  captures, injected states, template, screenshots+zooms, fp_tool.py/cap.sh,
  natural_expect.py + natural1_expect.json, board hexes. Session copies in scratchpad
  `theta400_fp/`.
