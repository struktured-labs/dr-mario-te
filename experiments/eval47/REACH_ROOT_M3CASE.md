# M3 DEATH-BOARD case study: base32 vs reach32 vs reachfull on the 6 tape commits

Source boards: `/home/struktured/projects/dr_mario_rl/tmp/film_review_20260804/recon/boards.json`
(schema/config: `.../recon/proxy_results.json`). Decider: `eval47/reach_root.py`
(`choose_base32` / `choose_reach32` / `choose_reachfull`, strand20 weights,
`ws=20`, `theta=250`). Board index 0 is the healthy control frame (no pill
commit) and is excluded — 6 real capsule commits remain, indices 1-6.

Runner: `eval47/tmp_logs/m3case.py`. Raw per-commit JSON:
`eval47/tmp_logs/m3case_raw.json`.

**Sanity check (passed):** `base32`'s value for every one of the 6 commits
reproduced `proxy_results.json`'s `shipped_strand20.chosen.val` bit-for-bit
(4191.0 / 4203.0 / 3728.0 / 3698.0 / 3212.0 / 2963.0) — confirms this run is
exercising the same shipped strand20 arithmetic the earlier film-review pass
used, not a re-derivation that could have drifted.

**Hooks-needed convention:** `hooks_needed = 32 * edges`, `edges =
min(|col-3|, |col-4|)` (nearest spawn half, `SPAWN_COLS=(3,4)`), per the
driver's own DAS-cadence constant (`patch_cartridge_copro.py:1554-1556`,
"NAV_T=5*/frame ... 32-hook cycles = 6.4 frames per edge"). `exceeds40` flags
`hooks_needed > 40`, the PAIR_LATCH_AUDIT.md §7 historical window ("a
commit-6-shaped ~40-hook window reaches 1-column-distant targets, cannot
reach 3-column-distant ones (~96 hooks needed)"). Human-family reference =
`{0, 6, 7}` per task instruction (also the argmax column in
`shipped_strand20.column_family_margin.family_values` on 5 of 6 boards).

## Per-commit table

| # | t_video | pill/next | tape actual (col,orient,frames-to-lock) | base32 pick | base32 BFS-reachable? | reach32 pick | reach32 hooks (edges) | reachfull pick | reachfull kind |
|---|---|---|---|---|---|---|---|---|---|
| 1 | 1109.9 | BB/BY | col4 V, 50f | col6 V, val 4191.0 | **NO** | col4 V, val 4093.0 | 0 (0 edges) | col6 V, val 4191.0 (=base32) | base |
| 2 | 1111.5 | BY/YR | col4 V, 95f | col7 V, val 4203.0 | **NO** | col3 H, val 4051.0 | 0 (0 edges) | col7 V, val 4203.0 (=base32) | base |
| 3 | 1113.6 | YR/BB | col3 V, 33f | col3 H, val 3728.0 | **YES** | col3 H, val 3728.0 (=base32) | 0 (0 edges) | col3 H, val 3728.0 (=base32) | base |
| 4 | 1114.5 | BB/YR | col4 V, 65f | col7 V, val 3698.0 | **NO** | col1 V, val 3524.0 | 64 (2 edges) — **exceeds 40** | col7 V, val 3698.0 (=base32) | base |
| 5 | 1116.0 | YR/RB | col3 H, 42f | col0 V, val 3212.0 | **YES** | col0 V, val 3212.0 (=base32) | 96 (3 edges) — **exceeds 40** | col0 V, val 3212.0 (=base32) | base |
| 6 | 1117.1 | RB/YR | col4 V, 20f | col7 V, val 2963.0 | **NO** | col0 V, val 2299.0 | 96 (3 edges) — **exceeds 40** | col7 V, val 2963.0 (=base32) | base |

`base32` hooks_needed for reference (all measured against the same ~40-hook
window): c1=64, c2=96, c3=0, c4=96, c5=96, c6=96 — 5/6 of base32's own
picks *also* exceed the window, independent of the reachability question.

## Human-family (`{0,6,7}`) match

| # | base32 | reach32 | reachfull |
|---|---|---|---|
| 1 | col6 — MATCH | col4 — no | col6 — MATCH |
| 2 | col7 — MATCH | col3 — no | col7 — MATCH |
| 3 | col3 — no (documented counter-case, see below) | col3 — no | col3 — no |
| 4 | col7 — MATCH | col1 — no | col7 — MATCH |
| 5 | col0 — MATCH | col0 — MATCH | col0 — MATCH |
| 6 | col7 — MATCH | col0 — MATCH | col7 — MATCH |

## Headline findings

**1. Theory confirmed on the reachability axis: base32 aims unreachable on 4/6 (66.7%).**
Commits 1, 2, 4, 6 — every board except 3 and 5 — have base32's argmax
landing on cells the BFS (`tuck_enum.enumerate(mode="free")`, gravity
ignored, the upper-bound reachable set) never proves reachable at all. Of
base32's own 32 straight-drop candidates, only 18/24 legal ones are
BFS-reachable on every single one of these 6 boards (`n_reach/n_legal =
18/24` unanimously) — this board shape (deep, holed, near-death) walls off a
consistent ~25% of the nominal action space regardless of which commit.

**2. reach32 does pick a BFS-reachable column every time (trivially, by
construction — it never fell back to unfiltered base32), but "reachable" is
not the same claim as "executable in the observed lock window."**
On 3 of 6 commits (4, 5, 6) reach32's own pick still needs more than the
historical ~40-hook budget (64-96 hooks, i.e. 2-3 column edges away from
spawn). Reach32's fix is a pure *legality* subtraction (removes
BFS-unreachable candidates) — it does not add any *DAS-timing* awareness, so
on the boards where every good column happens to be several edges from
spawn, reach32 is forced to choose between "reachable but far" (still
possibly late) or accept a lower-value near column. This matches
PAIR_LATCH_AUDIT.md §6.2/§7's own conclusion in the same case study: "the
real fix is the distance-aware commit gate... choose the best REACHABLE
column *under the remaining fall budget*" — reach32 alone doesn't carry that
budget term.

**3. On the 2 commits (3, 5) where base32's argmax was already
BFS-reachable, reach32 and reachfull both reproduce base32's pick exactly** —
no regression, confirming reach32 is a strict legality subset that changes
nothing when nothing needs removing (matches reach_root.py's own
`_selftest_reach32_eq_base32_open_board` guarantee, just observed here on a
non-open, high-holed board instead of the selftest's synthetic open ones).

**4. reachfull never diverged from base32 on any of the 6 commits — a gap
worth flagging, not just a null result.** `choose_reachfull`'s straight-drop
loop is architecturally identical to `choose_base32`'s (same 32 candidates,
no reachability filter applied to the *base*-kind branch — only the added
tuck-class candidates are reachability-filtered, and even those are gated by
`theta=250` against `best_base_val`). Each commit only had 2-4 legal
BFS-reachable tuck candidates available (n_tuck_legal: 2,2,2,2,2,4) and none
beat base32's value by the 250-point margin, so `reachfull` collapsed to
`kind=base` == base32's own (possibly unreachable) argmax in all 6 cases.
Concretely: on commits 1, 2, 4, 6 `reachfull` inherited the *same physically
unreachable* placement as base32, because reach32-style reachability
filtering is never applied to reachfull's base-candidate loop. If the goal
is "reachfull never proposes something the capsule can't execute," this is
a real hole in the current implementation, not just an absence of tucks —
it's inheriting base32's defect through an unfiltered code path.

**5. Human-family (`{0,6,7}`) match: base32 and reachfull both land in the
human-preferred family on 5/6 commits (only commit 3 — the documented
"counter-case" where the tape's own fast commit already matched the eval's
top pick — lands elsewhere, at col3, which is itself the *correct* good
placement for that specific board). reach32 lands in the human family on
only 2/6 (commits 5, 6)** — reach32's filtering pulls the argmax toward
whatever BFS-reachable column scores highest, and on 4 of 6 boards that is a
near-spawn column (4, 3, 3, 1) rather than the higher-value flank columns
(0/6/7) base32/reachfull prefer but can't physically reach. This is the
crux of the reach-root tradeoff on this board family: reach32 trades value
(and human-recognizable placement) for physical feasibility; base32/reachfull
keep the value and the human-recognizable column but can't actually get
there on 4/6 commits.

## Commit-3 note (the documented counter-case)

Commit 3 (t=1113.617, `spawn_to_lock_frames=33`) is the one board in this
set where base32's argmax (col3, val 3728.0) is already BFS-reachable, needs
0 DAS hooks (col3 is a spawn column), and matches the tape's own real
placement (col3, V) — this is the same case PAIR_LATCH_AUDIT.md §6.3 names
as evidence "not every fast commit is a bug." All three modes agree here,
and correctly so.

## Files

- Runner: `/home/struktured/projects/dr-mario-qa-wt/experiments/eval47/tmp_logs/m3case.py`
- Raw JSON (all 3 modes' full decide() output per commit, hooks/human-family
  flags): `/home/struktured/projects/dr-mario-qa-wt/experiments/eval47/tmp_logs/m3case_raw.json`
- Board source: `/home/struktured/projects/dr_mario_rl/tmp/film_review_20260804/recon/boards.json`
- Config/schema + shipped_strand20 cross-check values:
  `/home/struktured/projects/dr_mario_rl/tmp/film_review_20260804/recon/proxy_results.json`
