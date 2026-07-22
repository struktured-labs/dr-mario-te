# Victory-claim formulations

> The "human-beating headline" is deliberately TBD (per the project roadmap). This drafts
> candidate formulations at three ambition levels, with the evidence each requires and what the
> **RWE Hartford live session (Sept 12–13, 2026)** can furnish. Every claim must carry the
> fairness qualifiers in §1 or it is not this project's claim. Compiled 2026-07-22.

## 1. Invariant qualifiers (every victory claim must carry all of these)

A Dr. Mario "we beat humans" claim is only *this project's* claim if it is true under the
constraints that make it fair — otherwise it is just "a computer outsearches a person," which
is uninteresting and which meatfighter/StackRabbit-style agents already imply. Non-negotiable
qualifiers:

1. **No pause / no world-stop.** The AI thinks entirely within the falling pill's own descent
   time ("gravity is the budget"). Evidenced by the CI gravity-pin audit (`tests/test_driver_fidelity.py`).
2. **On console-accurate hardware.** The AI executes on a second 6502 + RTL accelerator inside
   the cartridge address space, synthesized on **MiSTer / Analogue Pocket** FPGA — not on a
   host PC. (Be precise: "console-accurate FPGA," not "a literal 1990 NES"; the FPGA-in-cart for
   a stock NES is a stated future target, so do not imply it exists.)
2. **As a legitimate second player.** The AI drives P2 through the normal 2-player interface of
   the *unmodified* game (controller inputs, real gravity), the same interface a human uses.
3. **Standard rules and a stated level/speed.** Name the exact level and speed (e.g., "Level 11,
   MED") and match the tournament setting used by the human opponent's scene where possible.
4. **A stated caliber for the human(s).** Anchor "caliber" to documented tournament results from
   the DRMC corpus, not vibes (see §2).

Without #1–#2 the claim is not novel; without #3–#5 it is not measurable. Reviewers will probe
each — pre-empt them in the claim's own wording.

## 2. The caliber ladder (anchored to the DRMC corpus)

"Beats humans" is meaningless without a caliber anchor. The corpus (`players.json`,
`brackets.json`) gives documented, citable anchors:

| Tier | Example anchor (from the corpus) | How "caliber" is evidenced |
|---|---|---|
| **T0 casual** | general RWE attendee, no tournament record | none / self-reported |
| **T1 enthusiast** | a DRMC monthly (Gold Speed) *entrant* | appears in a monthly bracket (`players.json`) |
| **T2 regional finalist** | e.g., a DRMC 2025 regional *finalist* | reached a regional final (`brackets.json`) |
| **T3 regional champion** | **Pangolin** (CT 2025 + PA 2024 champion), **DaveSmithSays** (PA 2025 champion) | named champion in transcript + title (`players.json → regional_champions_2025`) |
| **T4 national champion** | **Packie** (DrMC 2017 Championship) and the reigning VS champion | championship bracket result |

Crucial caveat: the corpus is anchored at **MED/championship and "Gold Speed" (high-speed)
settings, and levels vary** (e.g., some monthlies at Level 10). The AI's measured 100% clear is
**solo L11 MED in simulation**. **A versus claim at a tournament setting requires re-validating
the AI at that exact level/speed** — do not assume L11-MED strength transfers to, say, high-speed
Level 18. This is the single most important evidence gap to close before any T2+ claim.

## 3. Candidate formulations

### Formulation A — conservative (very likely furnishable at RWE)
> *"Playing as a fair second player under real gravity with no pause, on console-accurate FPGA
> hardware, the coprocessor won **≥70% of best-of-3 series against the general field of Retro
> World Expo attendees** (N = ___ series, ___ distinct opponents) at Level 11, MED."*

- **Evidence required:** an instrumented station log at RWE: per-series result, level/speed,
  opponent (anonymized or handle), and the gravity-pin telemetry proving no-pause. N ≥ ~20
  series for a stable percentage.
- **RWE furnishes:** essentially all of it — this is a booth-traffic claim.
- **Risk:** T0/T1 caliber is weak; a reviewer says "beating expo walk-ups isn't strong." True —
  A is the *floor*, reported alongside B/C, not the headline. Its value is the fairness telemetry
  at scale and the "N distinct humans, real gravity, no pause" framing.

### Formulation B — moderate (recommended headline if the caliber shows up)
> *"Under standard rules on console-accurate hardware — real gravity, no pause, as a legitimate
> second player — the coprocessor won a **best-of-___ series against a documented
> regional-finalist-or-champion-caliber player** (opponent's caliber established by
> `brackets.json`/`players.json`) at Level 11, MED."*

- **Evidence required:** (a) at least one T2–T3 player actually plays the station (RWE Hartford
  hosted the DrMC 2025 CT Regional — Pangolin/Perula-caliber players plausibly attend); (b)
  a best-of-N with N large enough to matter (≥ best-of-7, ideally a documented multi-series set);
  (c) **AI re-validated at the exact level/speed played**; (d) full fairness telemetry; (e) the
  opponent's consent to be named or a documented-caliber anonymization.
- **RWE furnishes:** potentially all of it *if* a regional-caliber player attends and agrees to a
  recorded set. This is the event's headline opportunity — pre-arrange it (invite a known
  DRMC-CT player; see §5).
- **Risk:** single-opponent, small-N → "anecdote." Mitigate with several series vs the same
  player and, if possible, 2–3 T2+ opponents. Also the level/speed-transfer gap (§2).

### Formulation C — aspirational (only if the result is real; do not pre-commit)
> *"The coprocessor defeated a **reigning DrMC champion** in a recorded best-of-___ under
> standard tournament settings, playing fair (real gravity, no pause) on console-accurate
> hardware — the first documented instance of an AI beating a champion-caliber human at Dr.
> Mario on period-accurate hardware."*

- **Evidence required:** a T4 opponent, a sanctioned-style recorded set, AI validated at the
  tournament setting, independent corroboration (video + telemetry + the player's acknowledgment).
- **RWE furnishes:** unlikely at a single expo booth unless a champion is specifically recruited
  and agrees to a serious set. Treat C as a *program goal*, not a Sept 2026 deliverable.
- **Risk:** highest scrutiny; a lost set is public. Only claim post-hoc from unambiguous evidence.

## 4. The absolute/solo floor (already furnishable, no humans needed)

Independent of any human result, these are defensible *now* from the repo and belong in the
paper as the strength floor:
- **"Clears 100% of Level-11 MED boards solo in cell-exact simulation"** (`tmp/final_regress.out`:
  6/6 seeds, 89–153 pills, clear% = win% = 100).
- **"93.6% raw / 97.0% widened agreement with adjudicated best moves on a 236-scenario
  adversarial suite"** (`tmp/r4r6r7_sweep.out`).
- **"Depth-3 expectimax at ~1 s/move on a second 6502 @ 85.9 MHz in-cartridge, validated
  cell-exact through py65 → Verilator → Quartus → silicon."**
These are the safe claims that stand even if the RWE human results are thin.

## 5. Recommended formulation + evidence plan

**Recommendation: lead with B, floor with A, hold C in reserve.** Headline the paper on
Formulation **B** *if and only if* a documented T2+ player is recorded losing a real series;
otherwise headline the solo floor (§4) + Formulation **A**, and frame B/C as in-progress with
the RWE session as the first data point. Never headline C until the evidence is unambiguous.

**Pre-registered RWE evaluation protocol (do this before Sept 12):**
1. **Instrument the station.** Log every series: opponent handle/caliber-anchor, level/speed,
   game-by-game result, and the **gravity-pin telemetry** (proves the fairness qualifier live).
2. **Recruit caliber.** Invite ≥1 documented DRMC-CT-regional-caliber player to a recorded set
   in advance (the venue's own regional alumni are the target). Get naming consent.
3. **Match the setting.** Decide the level/speed *before* the event and **re-validate the AI at
   that exact setting** in sim + on hardware; if it is not L11 MED, the §4 floor claims must be
   re-run there too.
4. **Fix N.** Pre-commit to the series length and the number of series for each tier; report
   exactly what was played (including losses).
5. **Hardware honesty.** Note the station platform (Pocket human-vs-AI is validated; MiSTer
   human play awaits BliSSTer Rev.3) — state which was used.
6. **Report negatives.** If the AI loses to a T3/T4 player, that is a *result*, not a failure —
   it calibrates the caliber ceiling and is more credible than a suspiciously clean sweep.

**One-line headline candidate (fill after RWE):**
> *"A depth-3 expectimax Dr. Mario AI, running fair (real gravity, no pause) as an in-cartridge
> FPGA coprocessor, clears 100% of Level-11 boards solo and won ___ of ___ best-of-___ series
> against documented ___-caliber DRMC players at Level 11 MED — the first benchmarked,
> on-hardware Dr. Mario AI to [beat regional-caliber humans]."*

## 6. Claims to avoid (they will not survive review)

- ❌ "First AI to play Dr. Mario" (meatfighter 2017). ❌ "First AI opponent for Dr. Mario"
  (Nintendo VS-CPU 1994; meatfighter). ❌ "First strong falling-block-versus AI" (Puyo scene).
- ❌ "We invented fairness-constrained game AI" (AlphaStar/OpenAI Five/FightingICE).
- ❌ "Superhuman at Dr. Mario" from solo sim alone — superhuman is a *versus-humans* claim and
  needs T3/T4 evidence.
- ❌ Any versus claim at a level/speed the AI was not validated at.
- ❌ "On original NES hardware" if the result was on FPGA — say "console-accurate FPGA."
