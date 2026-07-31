# experiments/ — the offline simulation lane

These are the instruments behind `docs/ENDGAME_FINDINGS_20260729.md`. They lived in a
gitignored `tmp/` for a full session, which meant one disk failure would have destroyed
every measurement in that document. Landed here so they survive the machine.

**The user's framing, and the reason fidelity is non-negotiable:** *"the abstraction IS this
simulator."* It is not a testing convenience — it is the abstraction whose faithfulness
bounds every conclusion drawn through it. Drift in the sim is unbounded error downstream.
Memory note `dr-mario-golden-is-weekend-era` records exactly that failure happening once.

| file | what it is |
|---|---|
| `vs_env.py` | ★ **two-player VS env WITH GARBAGE** — the first garbage model this project has ever had. Until this existed, every number ever measured was solo play, while the human beats the AI by combo-stomping. Implements the extracted rule (1 line → 0 tiles; ≥2 simultaneous → 2 tiles; colours from the cleared runs; columns {1,5}/{2,6}/{3,7}, so 0 and 4 are immune). ⚠ that column set is flagged UNVERIFIED in MECHANICS_NES.md, and `cells>=7` is a documented *proxy* for a double-line clear. |
| `selfplay.py` | eval-constant tuning scored on **win margin under garbage** rather than solo pills. Optimises a CONTINUOUS margin, not binary win/loss — binary needs ~780 matches to separate 55% from 50%. |
| `tuck_enum.py` | independent re-implementation of meatfighter's reachability BFS + a ROM-accurate gravity mode. 18.1% of real positions hold a tuck killing a virus no straight drop reaches; gravity costs zero placements at real L11 speeds. |
| `tuck_ab.py` / `tuck_cheap.py` | tuck A/Bs on uniform vs REAL NES capsules; `tuck_cheap` compares a bounded scan (candidate firmware design) against the full BFS. |
| `latch_fullgame.py` | full-game cost of the pair-latch defect at the RTL-MEASURED disagreement rates (12.5/16.7/39.1% by regime). |
| `coefopt_endgame.py` | coordinate descent over the eval constants on an endgame objective. **Its headline result was RETRACTED** — see the findings doc. Kept because the negative cost real hours. |
| `cascade_probe.py` / `poll_sweep.py` | cap-1 vs fixpoint resolve; W_POLLUTION sweep. |
| `nes_pills.py` | the REAL NES capsule generator (mod-9 additive walk off a 16-bit LFSR). |
| `export_real_boards.py` | real L11 positions → copro `hostdata.txt`, for co-sim work. |

★ **THE RULE THESE ENFORCE, twice-proven the hard way:** validate on the REAL capsule stream
before believing anything. Uniform draws flatter every capsule-dependent strategy — they
inflated the endgame planner from −1.4% to −6% and it was retracted after being tagged.

⚠ `runcapped` everything: this machine has been OOM-killed 5 times; the user's ceiling is 80 GB.
