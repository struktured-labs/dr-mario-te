# Ready-to-land: volley timeline in `pressure_rig` (unblocks P3)

Lane: lulu-147. Date: 2026-08-21 EDT.
Patch: `experiments/lulu147/volley_timeline.patch` — **verified to apply cleanly**
(`git apply --check`, exit 0). **Deliberately NOT landed.** See §4.

## 1. The defect

`pressure_rig` rows are per-GAME aggregates. `garbage_injected` is a **total**; the placement
index of each volley is never serialized. So the question

> is failure clustered in the placements right after a volley lands, or is it uniform?

— the one that separates an **attack-response** defect from plain **cumulative height** — is
not answerable from any artifact this rig has ever written. L1a(3)/P3 is blocked on this.

**★ It reaches further than L1.** `lulu_proxy/striker_model.py` is entirely a height-gated
*release* model: it banks volleys and fires them when the defender's scaffold height crosses
`H_RELEASE`. That design presumes the clustering. **Nothing on disk confirms it.** Until this
lands, every timed-pressure result rests on an unmeasured premise.

## 2. The patch — 3 hunks, purely additive

1. `volley_pills = []` initialised beside `garbage_injected` (~:172).
2. One append inside the **existing** `if landed:` branch (~:246), alongside the
   `last_garbage_landed_pill` assignment that is already there.
3. Two keys in the returned row: `volley_pills` and `row_schema: 2`.

```python
volley_pills.append([int(env.pills_placed), int(landed)])
```

**Provenance stamp — the requirement that old rows stay distinguishable.** `row_schema: 2` is
the discriminator, and it is load-bearing rather than decorative:

| row | means |
|---|---|
| no `row_schema` key | **pre-timeline row. The volley timeline is UNKNOWN.** |
| `row_schema: 2`, `volley_pills: []` | **genuinely zero volleys landed.** |

Without the stamp those two collapse into the same empty list, and a v1 row would silently
read as "this game was never attacked" — a false zero of exactly the shape this project keeps
getting caught by. **Any analysis must refuse to run on rows lacking `row_schema`.**

## 3. Why it cannot change the measurement

No new RNG draws, no new branches, no reordering. `_inject_garbage`'s
`random.Random(seed * 1000 + pills_placed)` is untouched, `inject_bursty_garbage` is untouched,
and the append sits inside a branch that already exists and already executes on exactly the
same condition. Control flow is unchanged; only the returned dict grows.

**★ That argument is a hypothesis, not a result** (rule 6: reproducibility is not validity).
It must be *demonstrated*, and §4 is how.

## 4. Verification protocol — REQUIRED BEFORE LANDING. Needs compute; do not skip.

The patch is not landed precisely because this cannot run under the spend cap, and **landing
an unverified rig change is how a silent measurement shift enters the record.**

- **V1 — byte-identical outcomes.** Re-run ≥40 seeds pre- and post-patch. Every field that
  existed in v1 must match **exactly**, row for row: `pills`, `won`, `topout`, `stall`,
  `garbage_injected`, `viruses_left_at_end`, `dies_ahead`, `funnel*`, `mm_vert`,
  `stranded_final`, `tower_final`. **Any single difference blocks the landing** — it would
  mean the instrument moved the thing it measures.
- **V2 — conservation.** `sum(halves for _, halves in volley_pills) == garbage_injected`, on
  every row. This is the outcome-plausibility assertion (rule 7) that a structural diff cannot
  give you.
- **V3 — ordering and bounds.** `volley_pills` is strictly increasing in placement index, and
  every index is `>= GARBAGE_MIN_PILLS` and `<= pills`.
- **V4 — non-vacuity.** Under the lulu/bursty stream, a substantial majority of rows must have
  a non-empty `volley_pills`. An all-empty result means the append is on a dead branch.
- **V5 — one kernel, many call sites (rule 3).** `pressure_rig.py` currently exists in **44
  worktrees, all byte-identical** (single md5 `9ee56938…`, verified 2026-08-21). It is a
  tracked file, so a commit propagates by checkout and needs **no manual fan-out** — but
  re-verify the md5 group after landing. A hand-edit in one worktree is how the four-copies
  defect started.

## 5. The analysis this unblocks — write it once V1-V5 pass

Pre-registered per PREREG_L1 §3/P3, with the interpretability floor (rule 5) enforced.

```python
def volley_hazard(rows, strata=((0, 2), (3, 5), (6, 9), (10, 10**9))):
    """Bad-end hazard per placement, stratified by placements-since-last-volley.

    Refuses pre-timeline rows: an absent row_schema means the timeline is UNKNOWN,
    not empty, and silently treating it as empty manufactures a false zero."""
    bad = [0] * len(strata)
    exposure = [0] * len(strata)
    for r in rows:
        if "row_schema" not in r:
            raise ValueError("pre-timeline row (no row_schema): timeline UNKNOWN, refusing")
        vp = [p for p, _ in r["volley_pills"]]
        died = not r["won"]
        for pill in range(1, r["pills"] + 1):
            prior = [p for p in vp if p <= pill]
            if not prior:
                continue                      # never yet attacked: not at risk
            gap = pill - prior[-1]
            for i, (lo, hi) in enumerate(strata):
                if lo <= gap <= hi:
                    exposure[i] += 1
                    if died and pill == r["pills"]:
                        bad[i] += 1
                    break
    return [(s, b, e, (b / e if e else float("nan")))
            for s, b, e in zip(strata, bad, exposure)]
```

**Reporting rules, fixed now:**
- **Unit of analysis is the SEED.** Per-placement counts must be seed-clustered before any CI
  — per-row counts have impersonated independent samples three times in this project.
- **Interpretability floor (rule 5):** report only if every stratum holds ≥100 placements
  **and** the strata differ on ≥2-3% of the outcome. Otherwise publish
  **"not testable at this stratification"** — never as a null.
- **P3 decision rule (unchanged from PREREG_L1 §7):** hazard elevated in the 0-2 stratum vs
  10+ ⇒ attack-response defect confirmed, the striker's height-gated release model is the
  right shape. Uniform ⇒ it is a **height** story, and the striker's release predicate must be
  re-examined **before any timed-pressure result is trusted**.

## 6. Landing order

1. Restore compute → apply the patch → run **V1-V5**.
2. V1 fails ⇒ **stop**; the instrument moved the measurement and that is the finding.
3. V1-V5 pass ⇒ land, re-verify the 44-copy md5 group, re-run the lulu arm at n=120 to
   generate v2 rows, then run `volley_hazard` and settle P3.
