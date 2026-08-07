# Reproducers

Everything here replays from a saved state with no dependence on the run that
produced it.

## The four avoidable VS kills (the whole depth verdict rests on these)

`vs_kills_avoidable.json` — seeds 12, 20, 23, 29, with the adversary's action
path, the kill ply `K`, and the escape depth `E`.

```bash
PY=/home/struktured/projects/dr_mario_rl/tmp/venv/bin/python
cd /home/struktured/projects/dr-mario-qa-wt/experiments/holepoker

# replay every kill and confirm the champion dies at the identical ply (8/8)
$PY vs_reproduce.py --kills results/vs_poker_fixed.json --no-fluke

# recompute escape depth (E = 5, 8, 5, 6) with live-adversary verification
$PY vs_escape.py --kills results/vs_poker_fixed.json --workers 4 \
   --out results/vs_escape_check.json
```

These are the §8.2 co-sim targets. If the RTL leaf already prefers the escaping
alternative at those positions, the deaths are an RTL-vs-sim artefact; if not,
"no feasible search depth fixes these" is silicon-grade.

## The 21 exhaustively-proved-safe positions

`exact_safe_positions.json` — real mid-game boards with `spawn_top ∈ {2,3}`
(virus loads 3-79), each carrying `col`, `vir`, `cur`. IDA* proves no pill
sequence of length ≤5 tops the champion out from any of them.

```bash
$PY exact_solo.py --max-spawn-top 3 --max-depth 5 --workers 5 \
   --out results/exact_solo_check.json
```

## Gates

```bash
$PY smoke_oracle.py 8            # G0 -- oracle == shipped decide path
$PY gates.py g1 g3               # G1 pill alphabet, G3a positive control
$PY g2_admissibility.py --boards 30 --max-depth 4    # G2 -- bound admissibility
$PY test_deepcopy_pillshare.py   # the deepcopy/pill-cursor defect + our fix
```

`test_deepcopy_pillshare.py` is the one to run first if any VS result ever looks
surprising: part A reports whether the **upstream** `vs_env_exact` defect is
still live, part B whether **our** wrapper is sound.

## The m3 silicon death

```bash
$PY m3_counterfactual.py
```
Reads the reconstructed boards directly from
`dr_mario_rl/tmp/film_review_20260804/recon/boards.json`. Q1 continuity 5/5 is
the check that anchors the whole analysis to real tape.
