# RESULT (silicon-fidelity lane, 2026-10-06): what the 10/05 silicon-only misses are, and are not

**Question.** Which mechanism is behind the 10/05 silicon-only misses?
- **Setup:** the 10/05 dr. lulu match, cart dbbb5007 + rbf 318607aa, fw 1488e158.
- **The misses:** 102 of the 158 AI misses in the 5 replayed games are SILICON-ONLY. The Mesen replay of the same cart,
  fed Verilator co-sim timelines and her garbage, lands elsewhere (forensics RESULT_LULU_20261005 section 7).

**Short answer.**
- **Emulation explains 25 of the 102:**

  | cause | pills |
  |---|---|
  | the known PREV-TARGET defect | 10 |
  | the tie-break seed (new) | 14 |
  | frame phase | ≤ 6 |
  | a speedUps offset (new) | 2 |

  The tags overlap.
- **The other 77 are COPRO-SIDE on silicon.** The silicon copro published something the Verilator copro does not publish
  on the reconstructed input.
- **Ruled out:** the reset gap, frame phase as the main cause, torn reads, tracker misreads.
- **Two real replay infidelities found:**
  - the tie-break SEED: every instrument runs 0; silicon never does. It comes with a firmware leak of the seed into the
    tuck extension;
  - the speedUps index.
- **The seed is now fixable** with default-off flags (dr-mario-te PR #37, section 7).
- **Silicon trace RUN (section 9; bluemage, fair CvC cart 4dfa9c79 + rbf 318607aa, 113 save-states):**
  - **32/32 unambiguous samples MATCH, 0 mismatches.** On identical input (the real seed $A5 included), the silicon copro
    publishes exactly what Verilator publishes, at the same time.
  - **But it covered the wrong regime.** All 34 usable samples are EARLY-game L20 boards (59–84 viruses), and none is
    seed- or tuck-sensitive (0/34 timelines change at seed 0 or with the tuck mask).
  - The couch residual lives in the ENDGAME: 56 of the 77 are at ≤20 viruses, on boards of height 14–16.
  - **Verdict:** a general copro/bitstream divergence is rejected. An endgame / tuck-path divergence is untested.
  - Next steps (bluemage only) are in section 9.

## 0. Method and controls
- Lane tools: this folder. Run data (ignored): `~/projects/dr_mario_rl/tmp/silfid/`.
  - PAUSE switch: `tmp/silfid/PAUSE` + `tmp/PAUSE_ALL` (unit `silfid-throttle`, cap 6).
- **Replays:**
  - execfid's chained + garbage Mesen probe on the FAIR cart dbbb5007;
  - plus GO logging (`tools/silfid_probe.lua`: kind case / prefetch / FILLER, and whether the GO preempted a running
    search).
- **Control:** re-running the banked seed-0 timelines reproduces the banked FAIR replays EXACTLY.
  - landing == silicon: 184/182/122/110/115;
  - == copro final: 173/201/116/118/120 (M1 G1/G2/G4, M2 G2/G3).
- 842 pills: silicon ≠ Mesen on 131. That is 116 where neither lands the final, and 15 where SILICON hits the final while
  Mesen misses. Silicon-only = the banked 102.

## 1. Per-hypothesis verdict (counts of the 102; a pill can carry more than one tag; `summary_silfid_20261006.json`)

| hypothesis | test | explains |
|---|---|---|
| **H1, LeafEval `dphase` reset gap** (needs a GO that preempts a running search) | GO log of the FAIR chained replays, all 5 games | **0**. 0 preempting GOs in 842 pills (783 case + 59 prestart GOs; FILLER only at warm-up). Cart D's next GO waits for DONE. |
| | the only silicon-side preempt path (a 2nd volley inside a garbage window → DRPRESTART invalidate → new GO) | 0 pill intervals with 2 receptions in these games (volleys file) |
| | CHAINED co-sim of M1 G4 in one copro process on the FAIR-cart GO schedule (`chain_run.py` + abortstale's `vsim_chain`, wgap 18) | **146/146 identical to the fresh per-pill timelines** (same publishes, times, finals, all DONE) |
| **H2, frame phase** | every publish + DONE shifted +1 f / −1 f; STALE GO-hook read | **≤ 6.** +1 f: 4; −1 f: 3; stale: 1. Union: M1 G2 p93/p195, M1 G4 p92/p127/p129, M2 G3 p126. 3 of these are PREV-TARGET pills. Overall landing == silicon moves by only −1…+3 per game. |
| **H3, torn mailbox read** | code: the firmware stores col then orient 7 copro clocks apart; the cart reads orient, col, orient and keeps the old target unless both orient reads agree; the DONE stub writes col, orient, THEN DONE | **0 by construction.** An undetected tear needs two running-best updates within ~20 CPU cycles (~960 copro clocks); one root evaluation is far longer. |
| **H4, tracker misreads** | 6 silicon-only landings checked by eye on 1080p frame pairs (`tmp/silfid/frames/`): M1 G1 p95/p133/p146, M1 G2 p171, M1 G4 p129, + p135 | **0**. Every checked landing is read correctly. |
| **H5 (new), tie-break SEED** | co-sim of all 129 disagreeing pills under 12 seed variants: all 8 jitter classes (seed bits 0/1/3/4; bit 0 is always 1 on silicon) + 4 with the tuck-leak half B = $D; then Mesen replays with each variant substituted | **14** (best variant per game; union over the 12 variants = 19). Section 4. |
| **H6 (new), speedUps offset** | silicon falls one gravity step faster at p % 10 ∈ {8, 9}; Mesen replay with spu = (p+2)//10 | **2** (M1 G2 p93, p179). Section 5. |
| **known PREV-TARGET defect** (LATEGUARD × PRESTART) | silicon's signature is exact (it executed the previous pill's target after a garbage window); the replay's synthetic garbage (fake colours) did not trigger it on these pills | **10.** FAIRPLUS lands the copro final on 9/10 (13/14 of all post-garbage silicon-only pills) |
| **union explained** | | **25 / 102** |

## 2. The residual 77 is copro-side

Residual by label: EARLIER-PUB 30, HYBRID 27, LATE-FLIP 11, SHORT-LANDING 9.

Four independent signs:
1. **Silicon lands outside every timeline.** 48 of the 102 silicon landings appear in NO co-sim timeline, under seed 0 or
   any of the seed variants. Some are cart compositions (hybrid / short).
2. **Silicon misses improvements the cart could not have refused.** On 11 EARLIER-PUB pills, the co-sim's improvement
   arrives BEFORE the 6 f commit gate, where every build retargets freely. Silicon never moved toward it, so the silicon
   copro had not published it by about f6.
   - M1 G2 p105: a22 at 1.13 f, a5 at 2.14 f.
   - M2 G2 p64: a23 at 1.13, a18 at 3.18.
   - Also M2 G2 p62/p86/p90, M2 G3 p54/p107, M1 G4 p99, M1 G2 p130/p190, M2 G3 p80 (seed-explained).
3. **Silicon pursues targets no timeline has.** On M1 G1 p133, silicon makes a 4th rotation to H at about GO+9 f, then
   one step to col 2. No timeline under any seed ever publishes an H placement for that pill.
4. **Silicon's DONE time differs on these pills.**
   - Slam onset (the cart slams at DONE): Δ = 0 on 368/630 agreeing pills, with ±1–2 detector noise.
   - On silicon-only pills it is spread −15…+14 f.
   - So silicon ran a different search on those pills, not the same search with a different cart reaction.

**Two further checks:**
- **The tracker boards are self-consistent:** on M1 G1, every agreeing pill's post-landing board (Mesen) continues into
  the next case's board. The only added cells are cascade falls.
- **The preview is consistent:** nxt(p) == cur(p+1) on 835/835 pills.

**What remains unknown:**
- whether the silicon copro computes differently on IDENTICAL input (an RTL / bitstream-vs-Verilator divergence);
- or whether its live input differs from the tracker's reconstruction in a way the checks above cannot see.

Only silicon separates the two (section 8).

## 3. Mechanism notes
- **H1 is structurally excluded on cart D:**
  - The chained, the fresh and the Mesen schedules agree.
  - The settle lane's dead-pill re-upload would appear as FILLER GOs during play. There are none.
  - **DRLEFLUSH (V11) therefore cannot change these misses on FAIR.** It matters for DRABORTSTALE carts, which preempt by
    design.
- **H3 code:**
  - Firmware: `LDA D_BC; STA S_BEST_C; LDA D_BO; STA S_BEST_O`, plus the DONE stub (col, orient, then DONE=1).
  - Cart `act`: `LDA $5286; CMP #$FF; ...; STA $616C; LDA $5285; STA $616D; LDA $5286; CMP $616C`. On a disagreement it
    keeps the old TGT.

## 4. The tie-break seed (H5): jitter + a firmware leak

**The cart side:**
- `SEED2 = (NAV_T|1) ^ $A4`, re-derived on the first play frame of each match (per game: DRCOLDINIT clears MATCH_ACTIVE
  on menu hooks).
- It rides the colour uploads' high nibbles.

**The firmware side:**
1. **Jitter** `+(t ^ t>>3) & 3` per root (by design).
2. **A LEAK:**
   - `tuck_v3.emit_tuck_cell_prep` loads S_CA/S_CB RAW, so the tuck extension's own placed cells become
     `(nibble|4)<<4 | colour` (= `$5x/$7x/$Dx(VIRUS)/$Fx`).
   - **Measured** (Verilator, seed $99, the 61 pills with a seed-0 tuck final): shipped fw vs the same fw with the colour
     loads masked differ on **38/61**.
     - The leaky image mostly drops the tuck: 14 have fewer publishes and 22 finals change.
     - The masked image == seed 0 on 52/61; the rest is the jitter.
   - **The tuck extension silicon runs has therefore never been the one every sim measured.**

**Every replay instrument runs seed 0.** The DBLCANON report had flagged this for double capsules.

**Per-variant Mesen replays** (each variant's timelines substituted on the 129 disagreeing pills; landing == silicon /
pills, and silicon-only reproduced / total):

```
seed              m1g1              m1g2              m1g4              m2g2              m2g3
s0    184/212 so 0/20  182/217 so 0/32  122/146 so 0/20  110/133 so 0/16  115/134 so 0/14
s1    185/212 so 1/20  190/217 so 8/32  122/146 so 0/20  110/133 so 0/16  117/134 so 2/14
s25   187/212 so 2/20  182/217 so 0/32  122/146 so 0/20  111/133 so 1/16  117/134 so 2/14
s11   185/212 so 1/20  182/217 so 0/32  122/146 so 0/20  110/133 so 0/16  117/134 so 2/14
s9    187/212 so 2/20  186/217 so 4/32  123/146 so 1/20  111/133 so 1/16  116/134 so 2/14
s3    185/212 so 1/20  185/217 so 3/32  122/146 so 0/20  110/133 so 0/16  118/134 so 2/14
s17   185/212 so 1/20  185/217 so 3/32  122/146 so 0/20  110/133 so 0/16  118/134 so 2/14
s19   185/212 so 1/20  190/217 so 8/32  122/146 so 0/20  110/133 so 0/16  117/134 so 2/14
s27   185/212 so 1/20  186/217 so 4/32  123/146 so 1/20  110/133 so 0/16  116/134 so 2/14
s153  186/212 so 2/20  182/217 so 0/32  122/146 so 0/20  111/133 so 1/16  116/134 so 1/14
s145  186/212 so 1/20  185/217 so 3/32  122/146 so 0/20  111/133 so 1/16  116/134 so 1/14
s155  187/212 so 2/20  186/217 so 4/32  123/146 so 1/20  111/133 so 1/16  115/134 so 1/14
s147  186/212 so 1/20  190/217 so 8/32  122/146 so 0/20  111/133 so 1/16  115/134 so 1/14
union over seeds: {'m1g1': 3, 'm1g2': 11, 'm1g4': 1, 'm2g2': 1, 'm2g3': 3} 19
```

**The mechanism is proven on individual pills:**
- M1 G2, class 1: the copro FINAL itself flips to silicon's landing on near-ties: p52 a3→a22, p73 a28→a29, p87 a20→a13,
  p132 a11→a31, p140 a10→a27, p171 a28→a29.
  - These are not execution misses. Silicon executed its own seeded copro's answer.
- M2 G3 p73: the leaky image at $99 makes the final a29 = silicon (seed 0: a10).

**The scale is modest.**
- The best variant per game reproduces 14; the union is 19.
- The jitter only moves near-ties. The leak changes tuck boards, but the $D-coded variants do not reproduce more of the
  102 than the jitter-only ones.
- **Caveat:** the true per-game seeds are unknown. 12 of the 128 odd seeds were sampled, covering every jitter class and
  both leak codes that matter most. The silicon trace reads the exact seed (`$6168`).

## 5. The speedUps offset (H6)
- **What silicon shows:** in the video gravity, silicon is one speed step faster at p % 10 ∈ {8, 9} (frames/row 12/11,
  11/10, 10/9, 9/8, 7/6 at p 88/89, 99, 118/119, 138/139, 158/159, 178/179).
- **Cause:** the ROM speed counter runs 2 capsules ahead of the tracker's pill index.
- **The bug it creates:** the co-sim's REACHTX nibble and the Mesen injection both use p//10.
- **Effect:** small. The Mesen-side correction reproduces 2/102, and silicon-only misses are not concentrated there (15 vs
  20 expected).
- **Tooling fix owed** (forensics pubtrace / gen_cases): `spu = min(49, (p+2)//10)`.

## 6. Fix status

| class | count | fixed by |
|---|---|---|
| PREV-TARGET (LATEGUARD × PRESTART) | 10 | **existing FAIRPLUS / FAIR2PLUS** (DRLGPRESTART), as the forensics found |
| tie-break seed (jitter + tuck leak) | 14 (≤ 19) | **new:** DRSEEDZERO (cart only, couch) or DRCOPRO_TUCKV3_SEEDMASK (fw, for seeded CvC; needs an rbf). No existing build removes it. |
| frame phase / spu | ≤ 6 / 2 | instrument-side, no cart change |
| residual, copro-side | 77 | **unknown until the silicon trace (section 8)** |

## 7. The fix PR: dr-mario-te #37 (`claude/silfid-seedzero` → `claude/execfid`; not merged)

Details in `experiments/silfid/RESULT_SILFID.md` there.

**DRSEEDZERO=1 (default 0, byte-identical):**
- Sets SEED1/SEED2 := 0 on the first play frame of every match.
- **Why a store and not DRSEED=0:** DRSEED=0 keeps a STALE seed, because MiSTer PRG-RAM is sticky across load_core. The
  new defect gate shows it: 93/93 GOs upload the stale seed.
- **Carts:** FAIRPLUS+SZ **607e819c**, FAIR2PLUS+SZ **f954774d**, FAIR+SZ 90b442c7.

**DRCOPRO_TUCKV3_SEEDMASK=1 (default 0):**
- Unset/0 → fw **1488e158** byte-identical; 1 → **4c005042**.
- The rbf build is not done.

**Gates, all pass:**
- negative controls on 5 carts;
- run_cart_gates (8 suites), incl. gravity fidelity;
- the new two-sided test_seedzero and test_tuck_seedmask;
- lgcut;
- NMI census (margin slightly better);
- TAP, plus the TAP mutant KILLED.

**Why ship DRSEEDZERO although the seed explains a minority:**
- it makes silicon the SAME decider as every replay and brain tool, so fidelity work stops measuring a known confound;
- it removes the tuck-colour leak on the couch at no rbf cost;
- it costs nothing.

## 8. Silicon trace design (run on 2026-10-06 by the main session on the owner's OK; results in section 9)

**Save-state sampling on the EXISTING cart + rbf. No new cart, no new rbf.**

A MiSTer NES save-state (1,327,112 B) carries everything needed for one exact silicon-vs-Verilator comparison:
- **the input:**
  - P2's board `$0500`, valid while the capsule is falling with its search ARMED;
  - the colours, speedUps / speed;
  - the game's seed `$6168`;
- **silicon's own copro publish:** `$616C/$616D` (the cart's last untorn live read, before LATEGUARD);
- **the time since GO:** `$6166:$6162` hooks.

**The tool:** `dr-mario-te tools/silfid/ss_cosim.py` rebuilds the upload byte-exactly and co-sims it.
- **Validated in emulation:**
  - 140 synthetic save-states from a Mesen FAIR replay give **117/117 non-ambiguous MATCH** (6 AMBIGUOUS, 17 unusable);
  - 2/2 mutants are KILLED;
  - the seeded upload rebuild is 246/246 exact.

**Protocol:**
1. Load the fair CvC cart `couch_kit/fair_20261003/drmario_cvc_fair_4dfa9c79.nes` on rbf 318607aa. It is unattended and
   needs no human. Or use the FAIR couch cart with anyone playing P1.
2. Run `tools/livecatch/ring_capture.sh --interval 8` (Alt+F1 save, size-stable wait, scp) for about 20 min. That gives
   about 150 states. About 40% are mid-search with the capsule falling, so about 60 usable samples.
3. Run `ss_cosim.py *.ss` (about 10 min offline).

**Decision rule:**
- **Any MISMATCH:** the silicon copro diverges from Verilator on identical input. Each mismatch is a complete repro case
  (exact upload bytes) for RTL / bitstream debugging. If the copro diverges at the rate the residual implies, expect about
  5–10% of usable samples to mismatch.
- **All MATCH / AMBIGUOUS:** silicon's copro equals Verilator, so the residual is in the live input or the cart.
  - Next: the same sampling on the couch cart during HDMI capture.
  - Compare the RAM board, colours and seed with the tracker's reconstruction at the same moment.

**Hardware time:**
- about 10 min of setup: install a CvC MGL, load it, confirm by screenshot;
- about 20 min of capture.

That is about 30–40 MiSTer-minutes, with no human at the controls for CvC. Each save flashes the OSD.

**Known risk:** the CvC autonav wedge on long soaks. 20 min is short; check by screenshot timeout.

## 9. The silicon trace: results (bluemage, 2026-10-06)

**Capture (main session, owner's OK):**
- bluemage loaded `FAIR_CVC.mgl` (cart 4dfa9c79 + rbf 318607aa); the screenshot
  `20261006_213507-drmario_cvc_fair_4dfa9c79.png` confirms the cart.
- `ring_capture.sh --host 192.168.1.156 --interval 8 --keep 400` ran for 20 min.
- Result: **113 save-states, 0 capture errors**, each md5-verified (`ss_trace_files_20261006.txt`).

**Offline:** `ss_cosim.py` on all 113, under the silfid PAUSE switch.

| class | n |
|---|---|
| not in a match (between games; ss_decode refuses them) | 27 |
| in a match but unusable (no search ARMED: 37; capsule locked while ARMED: 11; new-pill edge pending: 3; game-over screen: 1) | 52 |
| **usable** (mid-search, capsule falling, an answer published) | **34** |
| ↳ MATCH | **32** |
| ↳ AMBIGUOUS | 2: 173643 shows the 1st publish 0.06 f after the co-sim's 2nd; 174902 is at t = 0.5 f, before the 1st publish, so it holds the previous pill's last read |
| ↳ **MISMATCH** | **0**: no repro case to bank |

**What the matches cover:**
- **Exact input, including the REAL seed.**
  - Every readable state carries SEED2 = **$A5**: jitter class "1", tuck-leak nibbles $5x / $Ex.
  - It is the SAME value in every match of the 20 min. Under autonav, NAV_T at the first play frame is deterministic, so
    the CvC seed is effectively a constant.
  - The co-sim ran with $A5, i.e. the jitter and the leak were both modelled.
- **Timing.**
  - Silicon's live value equals the co-sim publish valid at hooks/2 frames in every match.
  - That includes 8 samples where silicon already shows a LATER running best (pub 2 of 2 ×7, 4 of 4 ×1).
  - Gaps to the nearest publish change run 0.0–24 f, with 8 samples within 1.4 f. So silicon's publish times agree with
    Verilator to within a hook.
- **Statistical reach.** A copro divergence affecting a random ~10% of searches would give P(0/32) ≈ 0.03. **A general
  copro / bitstream / timing divergence is rejected.**

**What the matches do NOT cover:**
- **The game phase.** All 34 boards are early-game L20: 59–84 viruses, height 13–16 made of virus stacks. 20/34 searches
  have a single publish.
- **The seed and the tuck.** `ss_seedcheck.py` re-ran each sample with the seed nibbles at 0 and on the masked tuck fw
  4c005042. **0/34 timelines change** (`ss_trace_seedcheck_20261006.*`). None of these searches touched a near-tie or a
  tuck.
- **Where the couch residual sits:** 56 of the 77 are at ≤20 viruses (all 842 pills: 530/842), 55 on boards of height
  14–16. That is the regime with sparse tall stacks, tucks and late running bests.
- **Prestart and garbage.** CvC carts have DRPRESTART=0, so no prestart / garbage-window search was sampled.
- ⇒ **Clustering of mismatches:** none to cluster (0). The coverage table above IS the result. Every dimension the
  coordinator asked about is either uncovered (prestart / garbage, tuck boards, the seed leak) or covered only in the
  early-game regime (board height, LeafEval paths).

**Verdict:**
- **(a) "silicon copro ≠ Verilator on identical input" is REJECTED for the regime sampled.** On dense early-game boards,
  silicon publishes the same answers at the same times, with the real seed.
- It is **NOT tested** for the endgame / tuck regime where the couch residual lives.
- So this is neither a clean (a) nor a clean (b):
  - a regime-specific copro divergence (tuck extension, late LeafEval paths) remains possible;
  - so does a live-input difference (the couch seed, prestart projections).

**Next steps (bluemage only; rivalmage is off-limits). Cheapest first:**
1. **Zero hardware: finish the seed sweep.**
   - Silicon behaviour depends on seed bits {0,1,3,4,5,7} (jitter + both leak nibbles): 32 classes, 12 tested.
   - The couch seed is the one live input the tracker cannot see. On the couch (human START), NAV_T at the first play
     frame is not deterministic.
   - Co-sim the 129 disagreeing 10/05 pills for the remaining 20 classes and score per game: about 4–5 h CPU under the
     PAUSE switch.
   - If a single class explains most of a game's residual, the couch residual IS the seed, and DRSEEDZERO fixes it.
2. **Endgame coverage, same method, about 40 MiSTer-min.**
   - A fair CvC cart at **L11**: the couch level, longer games that reach the endgame. It is a cart-only build of the fair
     CvC flags + DRLEVEL=11, with negative controls.
   - Sample it 30–40 min with `ring_capture.sh`, then `ss_cosim.py` + `ss_seedcheck.py`; post-filter to ≤20-virus states.
   - Owner OK needed for the second session.
3. **Strongest instrument: a PRG-RAM publish-ring debug cart.** It is cart-only, needs no rbf, and fits in the free
   $6600-$7FFF.
   - At every GO it tees the 132 upload bytes. Every hook it logs live-read CHANGES with the hook count, plus DONE.
   - That is about 48 pills of history. Save-states every ~60 s then give an exact silicon-vs-Verilator comparison of
     EVERY pill, endgame and tucks included, instead of one sample per state.
   - Use it on the L11 CvC flags; add DRPRESTART on a couch-flag CvC variant (P1 native AI sends the garbage), so the
     garbage-window prestart searches are covered too.
   - Needs the NMI census: the upload tee is about 600 cycles at the GO hook.
   - It would also close (b) without HDMI: if every pill matches, the copro is cleared in every regime.
4. **Live input proper (needs the couch cart on bluemage):**
   - The FAIR couch cart without DRSTUDYEND (a5107dca) on bluemage, with P1 driven through the proven keyboard-class game
     driver (`input raw`; never `dpad` / `button`).
   - Save-states + MiSTer screenshots at the same instants. The board reader runs on the native-resolution screenshot
     against the RAM board and seed, which tests the tracker's board / link reconstruction directly.
   - Needs a P1 that sends garbage (scripted) to reach the couch's garbage windows.
   - Recommended only after 1–3.

**Files:**
- `ss_trace_cosim_20261006.{json,log}`: every state, its status, upload bytes and co-sim timeline.
- `ss_trace_seedcheck_20261006.{json,log}`.
- `ss_trace_files_20261006.txt`: the .ss paths, under `~/projects/dr_mario_rl/tmp/silfid/ss_20261006/`.
- `tools/ss_seedcheck.py`.

## Files (this folder)
- **Analysis:**
  - `load.py` (silicon trajectories + Mesen T-traces), `score.py`, `summary.py`, `diverge.py`, `firstact.py`, `slam.py`;
  - `gravity.py`, `gravity2.py`;
  - `seedan.py`, `seedtab.py`, `mkpub.py` (seed variants / ±1 f shift / spu);
  - `cosim.py` (vsim_pub2 with SEED / SPU_OFF / FWDIR), `chain_run.py`, `allpills.py`, `side.py`.
- **Tools:**
  - `tools/silfid_probe.lua` (execfid probe + GO log), `tools/silfid_dump_probe.lua` (+ RAM dumps for the save-state
    validation);
  - `tools/*.sh` (every job ran in a `silfid-*` unit under the PAUSE switch);
  - `tools/build_fw_tuckmask.py` (the fw rebuild: control 1488e158 PASS, + the masked variant 4c005042).
- **Data:**
  - `seedcls_20261006.jsonl`: co-sim timelines of the 129 disagreeing pills × 12 seed variants;
  - `chain_wait_m1g4_20261006.jsonl`;
  - `summary_silfid_20261006.json`.
