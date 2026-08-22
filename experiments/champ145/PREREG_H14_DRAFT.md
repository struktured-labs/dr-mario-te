# PREREG DRAFT — H14 endpoint (champion-145) — NOT YET REGISTERED

Status: DRAFT for team-lead review, 2026-08-21. Nothing below is frozen; no
endpoint game has been played. Registration = committing a finalized copy of
this file named PREREG_H14.md with the datable-timing proof in the commit
message (0 endpoint rows on disk, seed block untouched) BEFORE any endpoint
game.

## 1. Question

Is candidate H14 a NEW CHAMPION — i.e. does it beat the certified champion
H12 (tie-only gated top-4 rollout, PREREG_ORACLE H12 addendum, GO 2026-08-17)
in the HOME REGIME, without getting worse where H12 is already great?

## 2. Arms

- CONTROL: H12 exactly as certified (h12_arm.py, theta_margin 0.5,
  future=dist, fork_samples=5, H=15, gate d_spawn_h>=12 OR viruses<=8),
  run at level 20.
- TREATMENT: the H14 candidate selected from tonight's screen (slate in
  REPORT.md; selection happens BEFORE registration and is named in the
  registered copy — one candidate, no post-hoc arm shopping).

Both arms: run_h12.py harness (sealed runner lineage), level=20,
max_pills=400 (registered censoring flag as in the regime map), honest
bursty v1.1 / lulu-fit injection exactly as init_rig(model="lulu") provides,
matched-index pairing (one work item = one seed = both arms), segments,
per-seed atomic banking, per-ply flip provenance ON (mandatory since the
stage-2 NO_GO shipped zero mechanism).

INSTRUMENT NOTE (honest): the regime map's 22.8% [17.7,28.5] (c5) is the
REAL-RTL champion; H12 cannot execute on the RTL (rollout overrides are
python). The endpoint instrument is therefore the LAB harness — the same
harness H12's own GO was certified on — at the map's regime coordinates
(L20 + honest bursty). Champion-const lab failure at these coordinates is
measured by tonight's screen (interim ~50% at n=62; final number goes here).
Lab-vs-RTL fidelity is game-level and regime-dependent
(dr-mario-cosim-farm): this endpoint certifies a RESEARCH champion vs H12 on
the lab instrument, exactly as H12 was certified vs the champion. Silicon
implementability is a separate later ladder (as it was for H12).

## 3. Endpoints

- PRIMARY: failure rate (topout OR stall) at L20-honest-bursty, paired by
  seed. Verdict: McNemar exact on discordant pairs, two-sided alpha 0.05,
  plus paired failure-rate difference with 95% CI. Unit = the seed/game
  (dr-mario-sample-size-audit: default unit of analysis is the seed).
- CO-PRIMARY GUARD (non-inferiority where H12 is great): L11 clear rate,
  H14 vs H12, same lulu-bursty harness at level=11, margin delta >= -2.0pp
  (one-sided 95% CI lower bound above -2.0pp). Stage-2 lesson: at ~2% flip
  dose the +/-1.0pp margin needed N>4,500; -2.0pp at the guard N below is
  reachable (CI half-width ~+/-1.9pp at N=2,000 given H12-era discordance;
  recompute from realized discordance and state it in the verdict).
- SECONDARY (reported, not gating): dies-ahead, topout/stall split,
  pills-to-clear on both-clear pairs, hazard per 100 pills.

## 4. Power / MDE (honest)

Primary, at base failure rate p0 (H12 arm, unknown until run; champion-const
interim ~50%, H12 expected lower): with N=600 paired seeds and discordance
fraction ~0.20-0.30 (H12-at-L11 realized 452/3000-611/3000 at 2% dose;
home-regime dose is ~2.5% so assume >=0.20), McNemar 80% power detects a
~6-8pp absolute failure-rate difference; N=250 detects ~10-12pp. STAGED:
run seeds in registered ascending order, interim look at N=250 (report
only; no early GO), verdict at N=600. If the realized discordance makes the
MDE worse than 8pp at N=600, the verdict states "underpowered below Xpp"
rather than converting a null into a NO-effect claim
(dr-mario-auc-operating-point-law: an experiment that cannot detect is not
an experiment — the MDE goes in the verdict either way).

## 5. Seeds

- PRIMARY block: 53100-59999 EXCLUDING the 20 sileval seeds inside it
  (53239, 54149, 54311, 54593, 55511, 55789, 56331, 56561, 56585, 57129,
  57245, 57431, 57773, 58007, 58253, 58403, 58427, 58957, 59115, 59937)
  = 6,880 seeds; first 600 in ascending order are the endpoint; the rest
  stay reserved to this lane. Block verified below 65536 (seed == stream
  key), no wrap collision with any registered block; excluded-consumed:
  300-699, 30000-37998 even, 41100-53099, 60000+, 62371, 63000-63079,
  63900-63907, 20000-29999, 70000-80999 (stream keys 4464-15463), 90000-
  90499 (stream keys 24464-24963), 42000-42059, 41000-41031.
- GUARD block (L11): reuse the H12 endpoint block 41100-4xxxx is FORBIDDEN
  (consumed); guard uses the NEXT 2,000 seeds of the primary block
  (paired, both arms, level=11). Primary and guard never pool.
- Startup assert: seed-list length == registered N; every seed in-block;
  sileval exclusions verified by set intersection == empty.
- ABBA: arm order alternates per seed pair-slot (both arms of a seed run
  back-to-back in one work item; ABBA over the within-item execution order
  to null slow drift).

## 6. Gates before any endpoint game (13-rule standard)

1. Identity: H14 arm with its new mechanism DISABLED must be
   outcome-identical to H12 on 20 seeds (rule 6: gate the object that runs,
   the endpoint runner config itself, not a sibling class).
2. Killed mutants: (a) dose-matched shuffled-label mutant of the H14
   mechanism (the H12 verdict's own null design) run at small n — the
   analysis must NOT prefer it; (b) population mutant — out-of-block seed
   and wrong-level row must hard-fail the analyzer (rule 7); (c) reader
   mutant — edited row moves the summary.
3. Flip-dose anchor: realized flip RATE (not count) on full N within
   [0.9, 1.1] of the mutant's (the H12 dose-saga rule: anchor on FULL-N
   rates, never a 60-seed calibration window).
4. Argmax-flip precondition (already tonight's screen): candidate flip dose
   >= 2% of plies in the home regime, else DO-NOT-LAUNCH.
5. Chain: systemd-run --user --unit drm-champ-endpoint, set -eo pipefail,
   every stage gated on the previous stage's success MARKER, state-based
   alarms, per-seed atomic + resumable, runtime manifest hashed (the
   sealed-runner provenance path already does this).

## 7. Verdict rule (registered before data)

GO (new champion) = primary McNemar p < 0.05 with H14 failure rate LOWER,
AND guard non-inferiority holds, AND mutant/dose anchors green.
NO_GO = any of those fails. VOID = instrument defect found (registered
defect classes only: dose anchor out of band, population gate failure,
runtime-manifest drift). A VOID is not a NO_GO and is reported as VOID.

## 8. Cost

$0 cash, local box only: 2 arms x 600 L20 games x ~15-30 s/game (H12 arm
pays rollout forks on ~2.5% of plies; champion-const measured ~15 s/game
at L20) + guard 2 x 2,000 L11 games x ~5 s => roughly 15-25 core-hours;
fits overnight at 12 workers. Hetzner untouched (c5 burn owns it);
10.42.0.233 untouched.
