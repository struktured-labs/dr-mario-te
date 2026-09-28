# PREREG (2026-09-27): STEER6 screen — "build toward a clear" leaf candidates on ANTIBODY

Written and committed BEFORE any screen game on the analysis block. The smoke runs used seeds 36734.. (4 games per
arm) and are not analysed.

## Why (phases 1–3)
- **Phase 2** (`RESULT_STEER6.md`): about 45% of gate-(b) tap-outs and about half of the slow race losses are
  endgame stalls. A stall is ≥ 20 pills with no clearing move, starting at ≤ 4 viruses left. Wins spend 25–37% of
  their pills stalled.
- **Phase 3:** a graded, gravity-aware, min-over-routes **clearing distance** D(v). Its definition is in
  `cascade_leaf6_x.py`. Horizontal windows charge each empty cell `1 + support gap`; vertical windows charge each
  empty cell above the virus 1; wrong-colour cells and cavities make a route infeasible.
  - **Regression cases** (`steer6_regress.py`, `steer6/regress_*.log`): couch boards, true pill sequence, replayed
    garbage, perfect execution.
    - **lulu G1 mid-stall (k120):** ANTIBODY takes **54 pills** to clear the sealed yellow (with garbage), or fails
      within 117 pills (without). The D-candidates take **4–10 pills**: dist_end60 4 / 7, dist_target60 4 / 7,
      dist_stall60 9 / 10, rowsup_end180 4 / 6.
    - **Match-1 G3** walled-in yellow (18 viruses left): ANTIBODY takes **54**. dist_hsv60 takes **15**,
      dist_hsv180 12, dist_stall60 31. The vk ≤ 4 gated arms are inactive there.
  - The "dig cost" variants (kdig 3) were neutral or worse and are dropped.
  - Two cases are anecdotes. The screen is the test.

## Arms (all = ANTIBODY + one `_x6` leaf extra; W = 0 is action-identical to ANTIBODY, selfcheck 311/311 × 5 modes)

| arm | mode | what | gate (root = firmware-side) | realisability |
|---|---|---|---|---|
| `s6_dist_end60` | (a) | −60 · Σ over all viruses of min(D, 16) | root viruses ≤ 4 | RTL: per-virus window scan on the column-top registers, ≤ 4 viruses when active; firmware sets W per decision |
| `s6_rowsup_end180` | (b) | +180 · Σ best-window (same-colour + support-ready cells) | root viruses ≤ 4 | RTL: as (a), cheaper (no gap arithmetic) |
| `s6_dist_stall60` | (c) | −60 · Σ min(D, 16) | ≥ 4 consecutive decisions with no ALLOWED root candidate clearing a virus | firmware counter on the search's own root `nv`; RTL as (a) but up to all viruses when active |
| `s6_dist_target60` | (d, own) | −60 · D(target); target = the root virus with the smallest D | root viruses ≤ 4 | **cheapest**: firmware picks the target once per decision; the leaf computes ONE virus's D (~12 comparators on column tops + 12 colour checks) |
| `s6_dist_hsv60` | (e, own) | −60 · Σ over HSV-region viruses (cols 3–5, rows < 9) of min(D, 16) | always (0 once no HSV virus remains) | RTL: region-gated per-virus scan; gives HSV512 a HOW |

## Instruments and seeds
- **Gate (b):** OWNER-0804, L11 MED, cap 600, unified DRTAPP=2 steering, run through `stuck_probe.py gb` (the
  probe does not change trajectories; identity-tested).
- **Race:** `stuck_probe.py race ARM 6.0` (vs_race lam 6, unified tap). Scored at M 177 δ 2.65 (the STEER5d
  instrument).
- **Seeds:** 37934–39132 even, **600 paired**, declared reuse (STEER5d / OPP1 / the phase-2 measurement). No
  STEER6 design choice used these sim seeds: the candidates were shaped on the couch boards only.
- **Baseline (banked):**
  - gate (b) = ANTIBODY STEER5d rows (== phase-2 probe rows, identity);
  - race lam 6 = STEER5d rows.

## Endpoints and bars (per arm vs the paired baseline, seed bootstrap 4,000, 95% CIs)
- **Primary:** tap≤100 and whole-game tap-out.
- **Race:** win at M 177 δ 2.65.
- **PASS** iff all three hold (the STEER5 bar):
  1. one primary CI lies entirely below 0;
  2. the other primary's upper CI ≤ +1 pp;
  3. race lower CI ≥ −2 pp.
- **Expected power:** tap-out SE ≈ 2.2 pp at n = 600, so a pass needs roughly ≥ 4.5 pp of tap-out reduction. The
  prize is ~10 pp. tap≤100 is not the mechanism's target (endgame), so the tap-out CI is the likely route.
- **Secondary (reported, no gate):**
  - Mechanism: pills spent in act-stalls ≥ 10, the endgame-stall death share (a terminal stall ≥ 20 from ≤ 4
    viruses), and active-decision share.
  - **Churn** on the baseline's failure seeds, fixed / new. The stall-breaker lesson: a flat net with big fixed and
    new counts is churn.
  - Race win at δ 2.0.
- **Multiplicity:** 5 arms, so a PASS here is a screen pass, not a ship. Any passer goes to:
  1. a powered confirmatory holdout on disjoint seeds (the STEER5d blocks minus 37934–39132, the OPP1b pattern),
     pre-registered separately;
  2. the **opponent suite**: OWNER-2026-09, lulu fit (gate b), STRIKER H6, and the LULU race (lam 4.7, M 140);
  3. an RTL cost estimate.
- A near-miss (point < 0 on both primaries, bar not met) may go to the holdout only if named in the result before
  any holdout game.

## Execution
- Hetzner (4 workers, systemd-run, exactness gate: code md5s + 2 seeds per arm, local == remote) plus local
  (nice 19, ≤ 4 workers).
- 5 arms × (600 gate-b + 600 race) = 6,000 games, ≈ 1.5 h.
- Rows: `steer6/screen/{local,remote}/`. Analyzer: `analyze_steer6.py`. Result: appended to `RESULT_STEER6.md`.
