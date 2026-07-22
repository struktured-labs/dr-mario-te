# Paper lane — Dr. Mario enhancement-chip AI

Publication workstream for the Dr. Mario FPGA-coprocessor AI. Founding session 2026-07-22.

**Working title:** *An Enhancement-Chip AI: Depth-3 Expectimax Dr. Mario on a Cartridge
Coprocessor, Playing Fair.* **Primary venue:** IEEE CoG 2027 (full paper, ~Mar 1, 2027).

## Files
- **[OUTLINE.md](OUTLINE.md)** — section-by-section skeleton, contributions C1–C6, the
  artifact→section map, figure/table shot list, open decisions for the lead.
- **[RELATED_WORK.md](RELATED_WORK.md)** — adversarial prior-art sweep with per-item threat
  ratings, the prior-art matrix (Table T1), and the two load-bearing corrections.
- **[VENUES.md](VENUES.md)** — CoG/AIIDE/FDG/ToG + FPGA-spinoff dates and the arXiv→CoG→ToG
  timeline.
- **[CLAIMS.md](CLAIMS.md)** — three victory-claim formulations, the caliber ladder, and the
  pre-registered RWE evaluation protocol.
- **[REFERENCES.bib](REFERENCES.bib)** — BibTeX for every citation in the sweep.

## Standing before drafting prose (from the sweep — see RELATED_WORK.md)
1. **Do not claim "first AI for Dr. Mario"** — meatfighter (2017) exists. Claim the conjunction
   (on-hardware/in-cartridge + depth-3 expectimax + benchmarked) and cite meatfighter.
2. **Correct "no enhancement chip ran AI"** — the Seta ST010/ST018 did (racing/shogi). This is
   in `README.md`/`ROADMAP.md` at the repo root and should be fixed before the arXiv post.
3. **Do not claim algorithmic novelty** (depth-3 expectimax + linear eval is textbook) or
   "first strong versus falling-block AI" (Puyo) or "we invented fairness-by-constraint"
   (AlphaStar). Novelty = game + hardware locus + fairness discipline + benchmark corpus.
4. **Run the meatfighter head-to-head** — the one experiment that makes C1 demonstrated.

## Branch
`paper-lane` (off `origin/main`), worktree at `dr-mario-mods-wt/paper-lane`. Not pushed.
