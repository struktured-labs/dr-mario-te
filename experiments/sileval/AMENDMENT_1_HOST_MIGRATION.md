# AMENDMENT 1 to PREREG_SLICE_SILICON — host migration (NEW box → OLD box)

**Status: REGISTERED 2026-08-23 (UTC), BEFORE any old-box row exists and
BEFORE any row of either population has been scored.**

Timing proof (the datable-preregistration standard):
- `out_oldbox/` does not exist at the registering commit; the old box holds no
  sileval cart, no sileval MGL, and no box sentinel (verified over ssh
  2026-08-23 01:1x UTC, inventory in this commit's message).
- No scorer output exists anywhere in the tree, on disk, or in git history
  (`out/` holds only `ARMED` at top level; nothing scorer-shaped was ever
  committed), and `score_rows.py` is unmodified since it was authored
  2026-08-20 18:53 EDT — before row 1. No interim reading is recorded, though
  the prereg permits one at n=120.
  **Limit of this evidence, stated rather than glossed:** it cannot exclude
  someone having run the scorer and read stdout without saving it. What is
  positively established is that no endpoint number exists in any artifact
  this lane can find, and that no such number informed this amendment — the
  decision below was reached from row *status* and *provenance* fields only,
  never from an outcome.

## 1. What happened (the population change)

The prereg fixes the hardware: *"Hardware: the NEW MiSTer only."* The owner has
reallocated the machines — the NEW box (`10.42.0.233`, MAC `02:53:49:4c:45:56`,
`SILEVAL_BOX_ID` present) becomes their TV/play box and is out of bounds for
this lane in every direction; experiments move to the OLD box (`10.42.0.225`,
stock MAC `02:03:04:05:06:07`, no sentinel).

A host change is a **population change**, not a continuation. This amendment
records how the two populations are treated, decided before any old-box byte
was written.

## 2. State of the NEW-box population at freeze

410 rows on disk, and the honest count is **not** 205 usable pairs:

| | count |
|---|---|
| rows written | 410 |
| rows `status: OK` | 255 |
| rows `status: VOID` | 155 |
| distinct seeds attempted | 205 (an exact prefix of the registered order — no cherry-picking) |
| **seeds with BOTH arms OK — the analysable n** | **126** |
| seeds with ≥1 VOID (retriable, but only on a box we may no longer touch) | 79 |
| seeds never attempted | 35 |

VOID causes: 154 × `boot_motion_shots_failed`, 1 × `cart_hash_mismatch` whose
`got=` field is **empty** — an ssh hash that returned nothing, i.e. an
instrument fault recorded under VOID rule 1, not a substituted cart.

The VOIDs are one contiguous outage, not a background rate: zero VOIDs in every
hour except 2026-08-21 20:00–22:xx EDT (9/103/42), which coincides with the
owner's SNAC bring-up and power-cycling recorded in `REPORT.md`. On both sides
of that window the instrument runs at a steady 9 rows/hour (≈4.5 pairs/h,
≈13 min/pair, matching the ~12.5 min/pair design). The harness retries VOID
rows on resume (`sileval_ab.sh:110` skips only on `"status": "OK"`), so those
79 seeds were recoverable — **on that box**. They are not recoverable now.

**The NEW-box population is therefore FROZEN at n=126 complete pairs**, versus
a planned 240. Per the prereg's own power table this is materially
under-powered: n=240 was sized for "discordance ≥4% with an ~80/20 split", and
n=126 needs a substantially larger effect than that. Stated up front, not
discovered at write-up.

The stop was **data-blind**: an external hardware reallocation plus the owner's
21:02 cable pull, with no endpoint ever computed. It is not an efficacy stop
and carries no optional-stopping penalty.

## 3. The decision: option (c) — two populations, and the second run is a REPLICATION

Rejecting the two offered options, with reasons:

### (b) "cross-box equivalence gate, pool if rows are byte-identical" is REJECTED — the gate is not runnable

This was tested, not argued. Seed 27875/ship was run **twice on the NEW box**
(the quarantined accidental cycle `_accidental_27875_ship_20260821_holdviolation`
and the banked row), giving a free same-box, same-seed, same-arm repeat:

- `patched.ss` md5 identical (`67fc43ee…`) — **seed injection is deterministic**.
- Sampled save-states: **0 of 16 cross-pairings byte-identical.** Not one.
- Decoded, the two runs track the same trajectory but not the same instant:
  evolved LFSR identical at every sample index (`$14e3`, rolling to `$c256` at
  s004), P1 virus counts identical (46/44/44/48), P2 counts differing
  (39/26/21/47 vs 35/24/21/48).

A byte-identity gate would therefore **fail on the new box against itself**.
A gate that a true null cannot pass measures nothing, so it cannot license
pooling. (Caveat recorded on the evidence, not just near it: the accidental
cycle ran 2026-08-21 02:44 UTC, ~15 min before the 03:00 UTC `update_all` that
replaced Main — so this is a same-box repeat across a firmware change, which
weakens it as a *noise-floor* estimate while strengthening the point that byte
identity is unavailable. It also means **no same-box noise floor was ever
measured on the new box, and can no longer be** — hands off.)

The P1-identical/P2-differing pattern is what a small wall-clock sample-phase
offset produces on the fast-clearing side. But it is also what a genuinely
divergent trajectory produces, and 4 samples of one cell cannot separate them —
the same after-the-fact indistinguishability recorded in
`dr-mario-stall-determinism-node-disagreement`. We do not claim to know which.

### (a) "park it and restart clean" is INCOMPLETE

Correct about populations, but it throws away something free: run the old box
on the **same registered seed list in the same registered order** and the
restart *is* a replication, at zero extra cost, with 205 seeds overlapping the
new-box attempts.

### (c) ADOPTED

1. **Two populations, never silently merged.** NEW-box = population A, frozen
   at n=126. OLD-box = population B. Separate `out_oldbox/` tree, separate box
   sentinel string, separate validity gates captured on the old box. The
   separation is structural, not a convention: a shared `out/` would let
   resume skip B's seeds against A's rows.
2. **B is a full replication**, same 240 seeds, same order, same ABBA parity,
   same driver code path.
3. **Primary reads are reported SEPARATELY.** B (larger, complete) is the
   lane's primary; A is reported as a prior independent run asking the same
   directional question at n=126.
4. **Cross-box concordance is an OUTPUT, not a gate.** On the seeds present in
   both, report the per-seed outcome agreement rate with a CI — a measured
   property of the rig, reported whatever it says. It never silently licenses
   addition.
5. **Pooling is permitted only as an explicitly-labelled SECONDARY**, only if
   B's direction agrees with A's, and always printed *beside* the two separate
   reads, never in place of them. `dr-mario-stall-determinism-node-disagreement`
   rule 1 — never pool two machines' rows into one population — is the standing
   default; this amendment does not overturn it, it fences an exception that
   must be shown, labelled, and never load-bearing alone.

### Why the boxes are not interchangeable (the concrete list)

Measured on the old box 2026-08-23, these differ and would have been assumed
away by a pooling gate:

| | NEW (.233) | OLD (.225) |
|---|---|---|
| MiSTer Main | 260707 (MGL needs `index="0"` + absolute path) | **2024-05-07** (old MGL format) |
| input channel | uinput FIFO daemon (built because hotkeys were refused) | **misterclaw** present since April |
| θ400 core `de7dea35` | copied in the bundle | **already native**, md5 verified exact |
| seedjit lineage | template imported | **template's native host** (`seedjit_d1.mgl`, Aug 16) |

The A/B core hash is identical on both, which is the one thing that *is*
shared. The template being native to the OLD box is worth stating plainly: the
pinned template `0d9e7b2f` was captured in the old box's live-soak era, so
population B restores it to its own host rather than reusing it across one.

## 4. Added control: the winner-endpoint repeatability tripwire

E1's McNemar attributes **all** discordance to the arm. The evidence above
shows the rig is not sample-reproducible; whether it is *winner*-reproducible
is unmeasured, and E1 depends entirely on that. If a same-arm rerun can flip a
match winner at rate δ, then arm-discordance d must beat δ, and the prereg has
no way to represent that (rule 29 — can the model represent the fault?).

Registered now, run FIRST on the old box, before the main replication:
- **30 seeds** (registered choice: every 8th seed in registered order, indices
  8,16,…,240), **ship arm only**, run **twice**, cycles otherwise identical.
- Statistic: number of the 30 whose match-1 winner differs between the two runs.
- Honest sizing, stated in advance: this is a **tripwire, not an estimate**.
  0/30 gives a 95% upper bound of ≈10% on δ — which does *not* clear the 4%
  discordance the prereg hopes to detect. It cannot certify E1; it can only
  catch a δ large enough to wreck it, cheaply (~3 h of box time) and before two
  days are spent.
- Reading rule, fixed now: **0/30 → proceed**, and report the ≤10% bound
  wherever E1 is reported. **≥1/30 → HALT the replication and report**; a
  nonzero winner-level noise floor means E1 as registered cannot be read, and
  that is a finding, not a setback.

## 5. What this costs (stated, not buried)

- The 35 unattempted + 79 VOID seeds of population A are **gone**. A is
  permanently n=126 and under-powered on its own.
- B costs ~53 h of box time for 240 pairs at the measured 4.5 pairs/h, plus
  ~3 h for the tripwire.
- The lane does **not** get a single n=366 result. It gets n=126 and n≤240,
  reported separately, with a concordance number between them.
- If B's direction disagrees with A's, this amendment has bought a genuine
  replication failure rather than a pooled number that hid it. That is the
  point.

## 6. Unchanged

Arms, carts, core, endpoints (E1/E1b/E2/E3), seed list and its order, cycle and
sampling parameters, the reading rule, and all seven VOID conditions carry over
verbatim. VOID condition 4 (box identity) is re-pointed: for population B the
sentinel is the OLD box's own `SILEVAL_BOX_ID` string, and the driver's guard
must refuse the NEW box's IP and MAC — the direction of the guard is inverted
by this amendment, and inverting it is part of the amendment, not a later fix.
