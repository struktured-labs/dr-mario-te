# Style Ensemble v1: fitting the bursty pressure model beyond one player

**Date:** 2026-08-05 · **Rule (user, tonight):** one player's fitted pressure model must
never be the only exam — ship gates need a family of styles.

## 0. TL;DR

**Ensemble gate: NOT READY — and pass 3's per-player separation is a sobering, honest result.**
Refactoring the pooled match-level fits into per-player SENDING profiles (game-causal direction:
player X's clears → volleys landing on X's opponent, attributed to X) roughly halves every n, as
expected. The consequence: **only struktured's own profile (and the AI copro's, from the same
session) clears the n≥20 confidence line.** All four newly-attributed named players — Rob
Burrito, Jarsdad, Chris Bidwell, davesmithsays — drop to LOW-CONFIDENCE or, for davesmithsays,
**n=0 (completely uninformative)** once correctly isolated from their opponents. See §6-7 for the
full table and what a genuine archetype read would need. This is not a wasted pass: it's the
correct, necessary refactor, and it surfaces a real methodological finding — pooled match-level
"OK confidence" numbers were partly an illusion of combining two players' events into one count.

## 1-4. Inventory / sources / calibration / attribution — unchanged from passes 1-2

See prior sections (not reproduced) for the `/mnt/data/drmario/expert_vods/` inventory, the
never-publish confirmation, calibration methodology, the White/Red/Green bracket geometry
(`vision_champ2024.py` P1/P2 top pair + P1B/P2B bottom pair), and the HIGH-confidence attribution
table for Rob Burrito, Jarsdad, Chris Bidwell, and davesmithsays (all via on-screen nameplate +
seed cross-referenced against each bracket's own `.description` roster).

## 5. The refactor: per-player SENDING profiles

**Game-causal direction** (per `bursty_model.py`'s own tagging convention — a volley event's
`side` field is the RECEIVING board): when side S clears, pressure lands on `opponent_of[S]`'s
board. So player X's SENDING/pressure profile is built from:
- **clears** = events where `side == X` (X's own clears)
- **volleys** = events where `side == opponent_of[X]` (garbage that arrived at X's opponent —
  attributed to X, since this model has no other generative mechanism for a volley)

X's RECEIVING context (garbage arriving at X's own board) is a different quantity that
characterizes X's *opponent's* sending style, not X's — not computed, per task direction.

Implementation: `fit_ensemble_source.py` gained `collect_events()` (runs `extract_match_events`
once per match, shared by both a pooled and a per-player fit so per-player fits don't re-run
vision extraction) and `fit_per_player()` (filters to one direction, reuses the same
p_within_k/volley_sizes/gap_samples aggregation as the pooled fit). `bursty_model.py` itself
remains untouched — confirmed again this pass that its primitives (`extract_match_events`,
`BurstyPressureModel`) are the correct, reusable building blocks; this is re-aggregation on top,
not a fix.

## 6. Self-test: struktured's per-player split

**Does NOT reproduce the original pooled numbers verbatim — and structurally cannot.** The
original `fit_struktured_20260804()` numbers (n_volleys=61, n_clears=188) are a POOL of both
sides' events. A true per-player split necessarily divides that pool into two parts; asking it to
"reproduce" the pooled total would mean the split failed to separate anything. The correct
self-test is **partition consistency**: do the two per-player event counts sum back to the
original pooled totals, with no event lost or double-counted? **Verified exactly:**

| | clears (own) | volleys (attributed, landing on opponent) |
|---|---|---|
| struktured (P1) | 89 | 28 |
| AI copro (P2) | 99 | 33 |
| **sum** | **188** ✓ (matches original pooled n_clears) | **61** ✓ (matches original pooled n_volleys) |

Both per-player fits clear the confidence line (n=28, n=33 — both ≥20). The split also reveals a
real, previously-invisible contrast that the pooled number hid: struktured's own sending profile
(gap 27.4s, P(4-6)=28.2%, P(7-10)=62.5%, n=16) is measurably slower/less-reflexive than the AI
copro's sending profile from the same session (gap 18.8s, P(4-6)=35.3%, P(7-10)=90.9%, n=11) —
the AI's own clears provoked a counter-volley far more reliably than struktured's did, in this
specific session. (Not a general claim about "the AI vs humans" — one session, and "the AI copro's
sending profile" here is really "how struktured's board reacted to the AI's clears," so it's still
partly about struktured's receiving behavior in disguise — flagged, not overclaimed.)

Full JSON: `results/style_ensemble_v1/struktured_20260804_{P1,P2}_sending_fit.json`.

## 7. Per-player table (all four new matches split)

| player | match | n_volleys (attributed) | fit confidence | n_clears (own) | volley_size_mean | gap_mean_s | P(vol\|clear 4-6) | P(vol\|clear 7-10) |
|---|---|---|---|---|---|---|---|---|
| **struktured** | 20260804 (pooled 4 sub-matches) | 28 | OK | 89 | 2.68 | 27.4 | 28.2% (n=71) | 62.5% (n=16) |
| AI copro | 20260804 (same session) | 33 | OK | 99 | 2.42 | 18.8 | 35.3% (n=85) | 90.9% (n=11) |
| **Rob Burrito** | Red Bracket vs Jenny G | 12 | LOW-CONF | 49 | 2.67 | 21.5 | 25.6% (n=39) | 30.0% (n=10) |
| Jenny G | Red Bracket vs Rob Burrito | 6 | **UNINFORMATIVE** (<10) | 37 | 2.00 | 37.4 | 17.6% (n=34) | 0.0% (n=2) |
| **Jarsdad** | White Bracket (bottom) vs dmhero | 15 | LOW-CONF | 41 | 2.40 | 18.4 | 50.0% (n=38) | 100.0% (n=3, too thin) |
| dmhero | White Bracket (bottom) vs Jarsdad | 11 | LOW-CONF | 51 | 3.27 | 13.6 | 22.7% (n=44) | 42.9% (n=7) |
| **Chris Bidwell** | White Bracket (top) vs Missy | 8 | **UNINFORMATIVE** (<10) | 27 | 2.25 | 29.1 | 52.0% (n=25) | 100.0% (n=1, too thin) |
| Missy | White Bracket (top) vs Bidwell | 5 | **UNINFORMATIVE** (<10) | 35 | 2.40 | 35.8 | 18.8% (n=32) | 0.0% (n=2) |
| Larvae | Green Bracket vs davesmithsays | 2 | **UNINFORMATIVE** | 59 | 5.50 (n=2) | 214 (n=1) | 2.0% (n=50) | 0.0% (n=6) |
| **davesmithsays** | Green Bracket vs Larvae | **0** | **UNINFORMATIVE (zero)** | 51 | — | — | 0.0% (n=47) | 0.0% (n=3) |

Bold = the named-roster player this task is tracking. Confidence labels: OK = n≥20 (team rule),
LOW-CONF = 10≤n<20, UNINFORMATIVE = n<10 (this pass's own extension of the rule, since several new
per-player n's fall well below even the LOW-CONF band and calling them "low confidence" alongside
n=28 numbers would understate how thin they are).

**davesmithsays' n=0 is worth stating plainly: in this specific 420s window, not one volley in the
entire match landed on Larvae's board within 5s of any of davesmithsays' clears (51 own clears,
0 attributed volleys).** That could mean this pairing/window genuinely had no fast counter-fire in
either direction (Larvae's own n=2 is also near-zero), or that this window undersamples — see §9.
Either way, zero is zero: no pressure-conditional claim is dossier-safe from this data.

## 8. Archetype read — still not possible, and now for the clearest reason yet

**Only two profiles clear OK confidence: struktured and the AI copro from his own session.** Every
newly-attributed named player (Rob Burrito, Jarsdad, Chris Bidwell, davesmithsays) is
LOW-CONFIDENCE or worse once correctly isolated from their opponent. This is not a failure of this
pass's method — it's the honest cost of doing the separation correctly. The pooled match-level "OK
confidence" numbers from pass 2 (e.g. Jarsdad-vs-dmhero pooled at n=26) were, in real terms, two
different people's events summed to clear a threshold neither could clear alone (Jarsdad alone:
n=15; dmhero alone: n=11). **A real archetype grid needs either much longer per-player observation
windows, or accepting LOW-CONF numbers as directional-only forever** for this data source.

**One directional pattern IS worth flagging, clearly labeled as a hypothesis, not a finding:** in
both matches where a named priority player's opponent's individual profile was also computed, the
named player's own numbers look MORE reflexive than the pooled match suggested, and consistently
higher than their opponent's:
- Bidwell alone: P(vol|clear 4-6)=52.0% (n=25, thin) vs. Missy alone: 18.8% (n=32) — the pooled
  match read as "the slowest in the ensemble" (pass 2), but that may have been driven more by
  Missy's response profile than Bidwell's own attacking tempo.
- Rob Burrito alone: P(vol|clear 4-6)=25.6% (n=39), gap 21.5s vs. Jenny G alone: 17.6% (n=34),
  gap 37.4s — Rob Burrito's own numbers sit closer to struktured's own range (28.2%, 27.4s) than
  the pooled match's lower numbers suggested.

If this pattern holds up with more data, it would mean pass 2's pooled-match "spread" was
partly an opponent-selection artifact rather than a spread across the named players themselves —
exactly the kind of thing per-player separation exists to catch. **Flagged as a hypothesis worth
testing with more footage, not asserted.**

## 9. Next step

Same three options as pass 2's §7, re-ranked given this pass's result:
1. **More footage per named player is now the clear priority** (not more separation work — that's
   done and correct). Every named player has exactly one ~5-minute match window; the same
   Red/White/Green Bracket videos likely have 2-3 more segments each for these players across
   "Rounds 1, 2, 3" (unexplored — only one nameplate-diff localization was run per bracket this
   pass). Pulling those would extend EXISTING players' n without new video downloads or new
   calibration.
2. davesmithsays' n=0 specifically warrants checking a second window before concluding anything —
   one 420s slice is a small sample of a multi-round bracket appearance.
3. Ensemble-gate structure proposal (evaluate a ship candidate against every fit individually, not
   averaged) is unchanged and still not implementable at this n.

## Per-player dossier notes (applied this pass)

Dossier files (`jarsdad.md`, `bidwell.md`, `roburrito.md`, `davesmithsays.md`) updated with the
per-player (not match-pooled) numbers from §7, confidence labels per the OK/LOW-CONF/UNINFORMATIVE
bands above, and the same video+timestamp+attribution-confidence citation style as pass 2.
davesmithsays' entry states the n=0 result plainly rather than omitting it.

## Provenance

- Fitting: `fit_ensemble_source.py` — `collect_events()`, `_build_model()`, `fit_per_player()`
  added this pass; `fit_filtered()` regression-checked unchanged (byte-identical n/volley_size_mean
  against the pass-2 committed JSON for the Red Bracket fit).
- Self-test: struktured's raw per-match event lists pulled from
  `bursty_model.fit_struktured_20260804()`'s live `.meta['raw_events']` (not re-extracted from
  frames) — confirms `from_footage()` still exposes the raw tagged events needed for this kind of
  re-aggregation, unchanged.
- New fits: `results/style_ensemble_v1/{struktured_20260804_P1,struktured_20260804_P2,
  red_bracket_JennyG,red_bracket_RobBurrito,white_top_Bidwell,white_top_Missy,
  white_bottom_Jarsdad,white_bottom_dmhero,green_bottom_Larvae,green_bottom_davesmithsays}_sending_fit.json`.
