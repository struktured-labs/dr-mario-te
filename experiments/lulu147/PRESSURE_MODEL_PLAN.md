# Lulu Pressure Model — footage inventory and fit plan

Lane: lulu-147. Date: 2026-08-21 EDT. **Inventory only; no footage was decoded and no fit was run.**
Footage was treated as READ-ONLY throughout (`stat` and `ffprobe` only).

---

## 1. ★ Footage inventory — the corpus is much thinner than assumed

`~/Videos/drmario_sessions/`, all 11 files, with age at 2026-08-21 22:28 EDT:

| file | duration | size | age | player |
|---|---|---|---|---|
| `20260804_1955_pocket_dock.mp4` | 24:57 | 222 MB | 17 d | struktured (v1/v1.1 source) |
| **`20260808_162125_dr_lulu.mkv`** | **2:50** | 20 MB | 13 d | **dr. lulu** |
| **`20260808_162820_dr_lulu.mkv`** | **12:38** | 152 MB | 13 d | **dr. lulu** — the 3-match set |
| **`20260808_164104_dr_lulu.mkv`** | **0:08** | 1 MB | 13 d | **dr. lulu** (fragment, unusable) |
| `20260809_202915_struktured_v6c.mkv` | — | 17 MB | 12 d | struktured |
| `20260809_2032*_part2.mkv` ×2 | — | 8 MB | 12 d | struktured |
| `20260815_130848_struktured_v6c_part2.mkv` | — | 16.6 GB | 5.6 d | struktured |
| `20260816_161508_struktured_v6c_part2.mkv` | — | 11.6 GB | 4.7 d | struktured |
| `20260818_192820_struktured_v6c_part2.mkv` | — | 2.8 GB | 2.1 d | struktured |
| `20260821_194835_struktured_v6c_part2.mkv` | — | **71 GB** | **0 min — OBS IS WRITING IT NOW** | struktured |

### ★★ Two findings the lane brief needs corrected

1. **The entire dr. lulu corpus is 15 min 36 s, from one session on 2026-08-08.** Discounting
   the 8-second fragment: **15 min 28 s**, of which the usable 3-match set is **12 min 38 s**.
   That is the whole basis of her model. There is no second session.
2. **Tonight's recording is NOT lulu footage.** `20260821_194835_struktured_v6c_part2.mkv` is
   labelled `struktured_v6c`, matching the last four sessions. It was **being written at the
   moment of this inventory** (mtime = now) — untouched, per the 10-minute rule. If the owner
   in fact played lulu tonight under a struktured-named OBS profile, that is a filename/profile
   issue worth a one-line confirmation before anyone budgets a refit against it.

**⇒ There is no new lulu data to fit.** Any improvement to her model in the near term must come
from **re-processing the existing 12:38**, not from new footage. The single highest-leverage
non-code action available to this program is **recording another lulu set** — see §5.

### Derived data already on disk

Under `dr-mario-qa-wt/experiments/eval47/tmp/dr_lulu_20260808/` (gitignored):
frames 758 @1fps · `p1_60fps/m3` 11,040 jpgs · `p2_60fps/{m1,m2,m3}` 12,900 / 17,040 / 11,040 ·
`events/p1_m3.csv` 75 rows · `events/p2_m3.csv` 94 rows.
Promoted to VC: `experiments/eval47/results/latency_events/film_20260808/p1_m3.csv` (75 rows).

**Processing reached m3 only, and the P2 (AI) side failed its own control** — 19.4% (18/93) of
tracked P2 pills false-lock at the spawn cell, and the classifier reads 28 virus cells where the
on-screen counter reads 41 (~30% undercount). Her declined-clear rate and pills-per-clear are
therefore **correctly unpublished**. m1 and m2 have **no P1 tracking at all**.

---

## 2. How much lulu-specific data exists for fitting

| quantity | lulu | struktured (for scale) |
|---|---|---|
| sessions | **1** | 5 |
| usable footage | **12:38** | 24:57 (fitted) + ~31 GB unfitted |
| matches | 3 | 4 |
| clears observed | 175 (pooled) | 188 pooled / 89 sending |
| **volleys observed** | **59 (POOLED — both sides)** | 61 pooled / **28 sending** |
| separated sending fit | **DOES NOT EXIST** | exists (v1.1) |
| tracked pills | 75 (m3 only) | 331 (m1-m4) |

**Expected size of her separated stream:** struktured's split ran 61 → 28 (46% his). Under the
same rough split her 59 pooled volleys yield an estimated **~27 sending volleys** — landing her
in the notebook's **FITTED (n≥20)** tier, but only just. Two conditioning bins will survive
(4-6 cell and 7-10 cell); the 11+ bin already has n=2 and will not.

⇒ **Her model can be de-contaminated, but it cannot be enriched, on current data.** Aim and
phase are *not* fittable from 12:38 at any acceptable confidence; they are (b)/(c) below and
they need a second session.

---

## 3. The fit plan

### (a) `dr_lulu_20260808_P1_sending_fit.json` — DO THIS FIRST. Cheap, tooled, removes a known bias.

Re-fit her raw events through `fit_ensemble_source.fit_per_player(all_volleys, all_clears,
n_matches, "P1", opponent_of)` — the same call `run_bursty_v1_1_validity.build_v1_1()` uses for
struktured. Her `raw_events` are in the existing fit's `meta`; **no video decode is required.**

Emit `meta.profile_kind = "sending"` and `meta.sender_side = "P1"` so the notebook's `fit scope`
column can never put her in a column with a pooled number again.

**Pre-registered expectation, written before running** ([[dr-mario-measurement-rules]]):
her separated p(volley | 4-6 clear) will come in **at or below the pooled 40.8%**, because
pooling drags a human toward the copro's near-deterministic cadence. If it comes in *above*
40.8%, the split is suspect, not the finding.

**Validation (all three required before the fit is used anywhere):**
- **V1 identity** — re-running the pipeline on struktured's 20260804 events must reproduce
  `struktured_20260804_P1_sending_fit.json` exactly (28/89/4). If it does not, the tooling
  drifted and nothing downstream is trustworthy.
- **V2 conservation** — lulu_sending + copro_sending volley counts must sum to 59.
- **V3 side check** — the copro side of her split must land near the copro's own known
  near-deterministic cadence. If lulu's separated stream looks *more* mechanical than the
  copro's, `--human-side` is inverted.

### (b) AIM — spec now, fit only after a second session

`bursty_model.extract_volleys()` already recovers the column pair `(c, c+4)` for every detected
volley; `sample()` discards it. The ROM's own rule
([[dr-mario-attack-buffer-is-attacker-side]], [[dr-mario-garbage-window-mechanics]]) is
size2 `{c,c+4}` c=frameCounter&3 · size3 `{c,c+2,c+4}` c=&3 · size4 `{c,c+2,c+4,c+6}` c=&1.

★ **This is the load-bearing question about aim, and it should be asked before any fitting:
on the NES, can a human aim at all?** The columns are a deterministic function of the frame
counter at release. If she is aiming, she is doing it by **choosing when to clear**, not where to
send — which makes "aim" a *timing* phenomenon and folds it back into the striker's release
model rather than requiring a new column distribution.

**Test (cheap, and it is the right first move):** take her 59 detected volleys, compute the
implied `c` for each, and test the histogram against uniform over 4 phases. **Uniform ⇒ aim is
not a channel for her and we stop.** Non-uniform ⇒ the deviation is her *release-timing*
signature and belongs in the striker, not in a column sampler. n=59 gives a chi-square over 4
bins adequate power for a gross deviation only; a subtle one needs the second session.

### (c) PHASE — needs the second session. Specced, not scheduled.

Does her volley rate change with viruses-left on either board? Her dossier says she "keeps her
stack ≤ ~4 rows through the midgame", and the damage instrument found damage tracks **game
phase** rather than height. n=59 across 3 matches cannot support a phase-conditioned rate.

### (d) Population mutants (rule 7) — required for every arm above

Each fit ships with mutants that the gate must **kill**, following
`lulu_proxy/striker_model.py`'s `check_release_log` / `check_pairing` / `check_matched_volume`:
- **M1 shuffled-labels** — permute the sender label across volleys. Must destroy the
  sending/pooled distinction. If M1 survives, the split is not doing anything.
- **M2 volume-matched blind** — `build_blind_schedule` at her exact volley volume, random times.
  Any claim that *her timing* matters must beat this, not merely beat no-pressure.
- **M3 struktured-substituted** — run the rig with struktured's sending fit under lulu's label.
  Any claim that the difference is *lulu-specific* must separate from this.
- **M4 uniform-column** vs her fitted columns, for the aim arm only.

---

## 4. What this does and does not buy

Even executed perfectly, (a)-(d) produce a **better garbage generator**. They do **not** produce
an opponent. Her model still has no clock, no board, and cannot lose — so it still cannot
produce a win rate. That is `VS_RACE_ENDPOINT.md`'s job, and it is the higher-value of the two.

**Honest ordering:** if only one thing gets built this week, build the **race endpoint** with her
*existing pooled* fit and a loud scope label, not a perfect fit with no race.

---

## 5. ★ The one ask for the owner

**Record a second dr. lulu set**, ideally 25-30 minutes (≈ the 20260804 length), with the OBS
filename template set to `dr_lulu` rather than `struktured_v6c`. Rationale, in one line:

> her entire model rests on 12 min 38 s from a single night, it is pooled, and aim and phase are
> unfittable below roughly double the current data.

A second session roughly doubles her volley count (~59 → ~120 pooled, ~27 → ~55 sending), which
is the difference between "her cadence is fitted" and "her *style* is fitted." It is also the
only input to this lane that no amount of compute can substitute for.
