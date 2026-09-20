# PRE-REG (2026-09-20 AT LAUNCH): VS self-play v1 — winner trunk + interaction terms

Owner: self-play should work if the score can represent the fight and d3 can
express the tactics. This loop tests that, instead of muxing solitaire leaves.

**Trunk:** `variant("winner")` + `pressure_rig._choose_base` (ws=0, wt=0). Same
search as the 63.8% VS eval. k=0 is that player.

**Terms (must change argmax):** both are candidate-varying × latched opponent
deficit `behind = max(0, own_v-opp_v)/48`:
- `k_race * nv * behind` — virus clears worth more when losing the race
- `k_tempo * (-fall_rows) * behind` — prefer short drops (tempo) when behind
Constant opponent additives are BARRED (they cannot rerank).

`k*opp_danger*cells` is NOT in gen0 — killed as a lone term (portfolio
opponent-aware, n=64 holdout 50.8%). Mutants may rediscover it later; gen0 does not.

**Scoring:** fictitious-play VS win vs the whole pool, **both seats per seed**.
Primary = win rate. Incumbent k=0 stays in the pool.

**Gen0 (6 members):** (kr,kt) = (0,0),(400,0),(1600,0),(0,80),(400,80),(1600,200).
n=80 seeds × 2 seats per pairing (C(6,2)=15 pairings). Seeds **36734+** DECLARED
REUSE of the cvx champion-search block.

**Promote:** a member with seat-balanced win vs k=0 of >55% at this n is a
candidate; it then owes n>=400 vs winner AND vs holes80 before any ship talk.
Solitaire tap-out of winner-base is known-worse than holes80; say so if we
promote.

**Identity gate (must pass before games count):** k=0 vs `_choose_base(winner)`
bit-identical on opening positions, including a forced-behind ctx.

## RESULT gen0 (2026-09-20) — NEGATIVE

15 pairings × 80 seeds × 2 seats = 2400 games. how: clear 2315, opp_topout 76,
opp_crushed 9. Fictitious-play vs pool:

| member | pool win | n | vs k=0 |
|---|---|---|---|
| winner\|kr0\|kt0 | 53.6% | 800 | (incumbent) |
| winner\|kr1600\|kt200 | 53.5% | 800 | 50.0% (80/160) |
| winner\|kr0\|kt80 | 50.5% | 800 | 52.5% (84/160) |
| winner\|kr400\|kt80 | 48.6% | 800 | 42.5% (68/160) |
| winner\|kr400\|kt0 | 47.4% | 800 | 41.9% (67/160) |
| winner\|kr1600\|kt0 | 46.4% | 800 | 45.0% (72/160) |

Nobody beat k=0 at >55%. Virus-deficit × (nv, −fall_rows) does not produce a
VS player stronger than always-on winner. Frozen in `vsloop/`. Do not run gen1
of these two knobs. Do not Quartus.

## v2 (2026-09-20) — richer opponent features, same loop

**Why:** v1 latched only virus deficit. Owner ideas still untested as
interaction terms: spawn height, send-shaped attack (not raw cells), play-safe
when ahead, clock. `k*opp_danger*cells` is still DEAD as a lone term; v2's
`k_atk` uses `send_halves` (the actual cells-rule garbage) not raw `cells`.
`k_safe` is the "survive when ahead" reading the opponent-aware report did not
build.

**New latches in vs_sim.ctx (all decide paths):** opp/own spawn_h, maxh, fill,
recv, clocks. Full opponent board is still not in the leaf (RTL: 1–2 cheap
terms later).

**New terms (must change argmax):**
- `k_atk * send_halves * opp_threat` — send garbage when their spawn lane is high
- `k_safe * (−post_spawn_h) * ahead` — keep own spawn clear when winning the race
- `k_time * (−fall_rows) * urgency` — short drops when clocks are tied
  (`urgency = 1 − min(1, (opp_t−own_t)/5)`; the mover always has own_t≤opp_t)

k_race / k_tempo remain in the genome (mutation can revive them) but are 0 in
v2 gen0.

**Gen0 (6 members):** all-zero incumbent; ka200; ka800; ks200; ki80; ka200+ks200.
n=80 seeds × 2 seats. Seeds **41134+** DECLARED REUSE, disjoint from v1 36734
and racer 40134–40732. Outdir `vsloop2/`.

**Promote:** seat-balanced win vs k=0 of >55% at this n, then n≥400 vs winner
AND vs holes80. Same identity gate, plus SCALE_OK (each new family moves ≥1
live-latch pill in a 6-game probe).

## RESULT v2 gen0 (2026-09-20) — NEGATIVE on promote bar

15 pairings × 80 seeds × 2 seats = **2400 rows verified**. Seeds 41134+.
how: clear 1997, opp_topout 389, opp_crushed 14.

| member | pool win | vs k=0 |
|---|---|---|
| ka200+ks200 | 57.4% n=800 | 48.1% (77/160) |
| ka800 | 56.9% n=800 | **51.2% (82/160)** best vs incumbent |
| k=0 incumbent | 56.5% n=800 | — |
| ks200 | 55.9% n=800 | 50.0% (80/160) |
| ka200 | 55.1% n=800 | 50.6% (81/160) |
| ki80 | 18.2% n=800 | 17.5% (28/160) |

Nobody >55% vs k=0. ka800 is a coin flip. Pool ranking of ka200+ks200 is
"beats the weak" (especially ki80), not "beats winner."

**ki80 is poison:** 352 of its losses are top-outs (other members ~6–9).
Clock-urgency at this dose slams pills and suicides. Mean send 15.0 vs
incumbent 17.6. Do not run gen1 of the spawned children — 3 of 4 have
k_time∈{80,160}.

Attack/safe terms send a bit more (18.6–18.7 vs 17.6) and do not win.

Frozen in `vsloop2/`. Do not Quartus. Always-on winner remains the VS bot.
