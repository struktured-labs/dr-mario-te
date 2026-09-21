# Overnight 2026-09-20 → 2026-09-21: clock-in-search, keep going

Owner is at work. Push the TIME1 search-clock thesis as far as local
24-core allows. Do not wait for chat. Do not Quartus. Do not vsloop2 gen1.
Do not ki80-class doses (move rate ≥30%). Do not touch Hetzner rbm-train-2.

Deadline: **2026-09-21 16:00 America/New_York**. Then write `clockloop/MORNING.md`
and stop.

## Hard rules
- Identity: k=0 remains `_choose_base(winner)`.
- Seeds: gen0 42134+, confirm 43134+, k_hold gen0 44134+. DECLARED REUSE.
- Cart-matched ws=0. Hartford = nutmeg bursty + TRATE=0.025, cap 600.
- Promote screen n=80 is not a ship claim. Confirm is n=400.
- Commit+tag after each scored experiment (`clock-gen0-…`, `clock-confirm-…`).

## Phase tree

### 0. gen0 (`clock_selfplay.py 0 80`) — IN FLIGHT at 22:35
Members kc ∈ {0,10,20,40}. VS 6 pairings × 80 × 2 + Hartford n=80 each.
PID parent 1013012 / python 1013040. Outdir `clockloop/`.

When LEDGER has VS vs incumbent AND Hartford table (960 VS rows, 320 H rows):

**Promote to confirm** if ANY nonzero kc has:
- VS vs kc0 >55%, OR
- Hartford tap-out down vs kc0 (point estimate) AND VS vs kc0 ≥45% AND
  dies-ahead rate not higher than kc0.

Else gen0 is a NEGATIVE for `k_clock * dt` (spire-preferring clock). Do not
run gen1 of those children. Go to phase 2.

### 1. confirm (`clock_confirm.py 400`)
VS n=400 both seats vs kc0 for every nonzero that passed the screen.
Hartford n=400 all members including kc0. Seeds 43134+.
If confirm holds the screen rule at n=400: candidate. Still no Quartus;
write MORNING.md with the numbers. Stop.

If confirm dies: treat as negative, go to phase 2.

### 2. k_hold — flatten penalty (the actual TIME1 / Hartford skyline)
`k_clock * dt` prefers already-tall columns (grows spires). Hartford holds
**global** maxh 13–15 late without necessarily spiring. Next term, root only:

```
pre = _maxh(col); post = _maxh(c1)
val -= k_hold * max(0, pre - post)
```

Penalize drops that lower the skyline. No bonus for growing taller.
Add `k_hold` to KNOBS/VsPolicy/choose (default 0). Identity still k=0.
Scale: some dose moves >0; ≥30% is barred.
Gen0 members kh ∈ {0, 20, 40, 80} unless scale bars some.
Driver: copy clock_selfplay → `hold_selfplay.py`, OUT=`holdloop/`,
SEED0=44134, only k_hold varies. Same dual VS+Hartford n=80.
Same promote rule vs kh=0.

If k_hold gen0 negative: write MORNING.md, stop. Do not invent a third
term overnight. The result is "search-clock as root bonuses did not beat
winner under these two shapes."

If k_hold gen0 hits the screen: confirm n=400 (seeds 45134+), then MORNING.md.

## Do not
- Quartus / flash / load RACE_WINNER
- vsloop2 gen1 (k_time poison)
- k_clock 80/160
- mux leaf lane/tall/early (already dead)
- idle after gen0 LEDGER exists

## Morning artifact
`experiments/cvx/clockloop/MORNING.md` — what ran, numbers, which term
is alive or dead, next human-facing recommendation. One page.
