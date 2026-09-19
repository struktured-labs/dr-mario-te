"""NutmegModel — expert-grade send pressure fit from the Retro World Expo (Hartford) DrMC broadcast.

Fit source: 4fps board reads of the Top-8 hour (dr-mario-h16-wt/tmp/tourney/nutmeg_fit.json;
pipeline in experiments/tourney_tape/).  779 garbage arrivals / 4,599 opponent clears / 117 min.
Interface-compatible with bursty_model's model object (fire_probability + sample, deterministic
random.Random(seed*1000+pills_placed) convention) so pressure_rig's model_kind="bursty" path takes
it unchanged.  Differences from the owner-fit model, per the fit:
  - fire prob by clear size: 3-4 cells 0.25 · 5-6 0.31 · >=7 0.34   (Hartford experts)
  - volley COLUMNS dist: 2:0.73 3:0.17 4:0.05 5-7:0.01 8:0.04 (full-width dumps exist)
  - plus an UNLINKED stream (17% of arrivals, ~0.56/min/side) delivered as a small per-placement
    probability so quiet play still gets leaned on.
"""
import random

class NutmegModel:
    FIRE = ((4, 0.25), (6, 0.31), (10**9, 0.34))
    COLS = ((2, 0.729), (3, 0.168), (4, 0.049), (5, 0.003), (6, 0.003), (7, 0.006), (8, 0.042))
    UNLINKED_P = 0.017   # per placement (~0.56/min at ~2s/pill L11 pacing)

    def fire_probability(self, clear_size):
        for hi, p in self.FIRE:
            if clear_size <= hi:
                return p, 999
        return 0.34, 999

    def sample(self, seed, pills_placed):
        rng = random.Random(seed * 1000 + pills_placed)
        x = rng.random(); acc = 0.0; ncols = 2
        for c, p in self.COLS:
            acc += p
            if x <= acc: ncols = c; break
        cols = rng.sample(range(8), ncols)
        return ncols, cols   # n_cells == n_cols: single-height halves, the dominant Hartford volley
