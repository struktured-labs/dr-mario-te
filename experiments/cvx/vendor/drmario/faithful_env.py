"""Gymnasium environment over the faithful Dr. Mario engine.

Placement-based action space (fast to train, strong planner): each step the
agent chooses where the *current* pill lands -- one of 4 variants x 8 columns.
A deterministic pathfinding/controller layer (see ``controller.py``) converts a
chosen placement into NES button presses for ROM transfer; the policy itself
reasons purely about placements.

Action = variant * cols + col, where variant in:
    0 = horizontal, (a left,  b right)
    1 = horizontal, (b left,  a right)   [flip]
    2 = vertical,   (a top,   b bottom)
    3 = vertical,   (b top,   a bottom)  [flip]

Illegal placements (column full, horizontal at the right edge) are exposed via
``action_masks()`` for MaskablePPO.
"""
from __future__ import annotations

import numpy as np

try:
    import gymnasium as gym
    from gymnasium import spaces
    _HAS_GYM = True
except Exception:  # pragma: no cover - allows engine-only use without gym
    _HAS_GYM = False
    class gym:  # type: ignore
        Env = object

from .faithful_game import (
    FaithfulBoard, Pill, COLORS, EMPTY, ORIENT_H, ORIENT_V,
)

N_VARIANTS = 4
N_COLORS = 3
N_BOARD_CH = 6          # empty, red, yellow, blue, virus, pill-half
N_PILL_CH = 12          # one-hot a,b for current + next (4 * 3)
N_CHANNELS = N_BOARD_CH + N_PILL_CH  # = 18


class FaithfulDrMarioEnv(gym.Env):
    metadata = {"render_modes": ["ansi"]}

    def __init__(
        self,
        rows: int = 16,
        cols: int = 8,
        level: int = 5,
        level_range=None,            # optional (lo, hi) sampled each reset (curriculum)
        max_pills: int = 400,
        reward_cfg: dict | None = None,
        seed: int | None = None,
        shaping: bool = False,        # potential-based dense reward for near-lines
        shaping_gamma: float = 0.99,
    ):
        super().__init__()
        self.rows, self.cols = rows, cols
        self.level = level
        self.level_range = level_range
        self.max_pills = max_pills
        self.shaping = shaping
        self.shaping_gamma = shaping_gamma
        self.rng = np.random.default_rng(seed)
        self.reward_cfg = reward_cfg or {
            "virus": 1.0,        # per virus cleared
            "junk": 0.05,        # per non-virus cell cleared
            "combo": 0.5,        # per extra chain step
            "win": 10.0,         # all viruses cleared
            "topout": -5.0,      # spawn blocked / no legal placement
            "step": -0.02,       # per pill placed (efficiency)
        }
        self.n_actions = N_VARIANTS * cols

        if _HAS_GYM:
            self.action_space = spaces.Discrete(self.n_actions)
            self.observation_space = spaces.Box(
                low=0.0, high=1.0, shape=(N_CHANNELS, rows, cols), dtype=np.float32
            )
        self.board: FaithfulBoard | None = None
        self.cur: Pill | None = None
        self.nxt: Pill | None = None
        self.pills_placed = 0
        self._start_viruses = 0

    # --------------------------------------------------------------- helpers
    def _rand_pill(self) -> Pill:
        return Pill(int(self.rng.integers(1, 4)), int(self.rng.integers(1, 4)))

    def _decode(self, action: int):
        variant = action // self.cols
        col = action % self.cols
        if variant == 0:
            return ORIENT_H, col, Pill(self.cur.a, self.cur.b)
        elif variant == 1:
            return ORIENT_H, col, Pill(self.cur.b, self.cur.a)
        elif variant == 2:
            return ORIENT_V, col, Pill(self.cur.a, self.cur.b)
        else:
            return ORIENT_V, col, Pill(self.cur.b, self.cur.a)

    def action_masks(self) -> np.ndarray:
        m = np.zeros(self.n_actions, dtype=bool)
        for a in range(self.n_actions):
            orient, col, pill = self._decode(a)
            m[a] = self.board.resting_position(pill, orient, col) is not None
        return m

    # ------------------------------------------------------------------- obs
    def _obs(self) -> np.ndarray:
        x = np.zeros((N_CHANNELS, self.rows, self.cols), dtype=np.float32)
        g = self.board.color
        x[0] = (g == EMPTY)
        x[1] = (g == 1)
        x[2] = (g == 2)
        x[3] = (g == 3)
        x[4] = self.board.is_virus
        x[5] = (g != EMPTY) & (~self.board.is_virus)
        # pill one-hots as full planes
        def onehot(base, color):
            x[base + (color - 1)] = 1.0
        onehot(6, self.cur.a); onehot(9, self.cur.b)
        onehot(12, self.nxt.a); onehot(15, self.nxt.b)
        return x

    def features(self) -> np.ndarray:
        """Engineered scalar features for decision-tree distillation."""
        heights = self.board.column_heights().astype(np.float32) / self.rows
        vc = self.board.virus_counts_by_color()
        total_v = self.board.virus_count()
        holes = 0
        for c in range(self.cols):
            colv = self.board.color[:, c]
            occ = np.where(colv != EMPTY)[0]
            if occ.size:
                holes += int(np.sum(colv[occ.min():] == EMPTY))
        feats = list(heights)                                   # 8
        feats += [total_v / 84.0,
                  vc[1] / 28.0, vc[2] / 28.0, vc[3] / 28.0]     # 4
        feats += [self.cur.a / 3.0, self.cur.b / 3.0,
                  self.nxt.a / 3.0, self.nxt.b / 3.0]           # 4
        feats += [float(heights.max()), holes / 32.0]           # 2
        return np.array(feats, dtype=np.float32)                # 18

    # --------------------------------------------------------------- shaping
    def _scan_line_potential(self, colors, viruses):
        """Potential for one row/column: reward extendable near-lines (len 2-3),
        doubled when the run contains a virus (loaded clears over targets)."""
        VAL = {2: 0.03, 3: 0.12}
        n = len(colors)
        phi = 0.0
        i = 0
        while i < n:
            c = colors[i]
            if c == EMPTY:
                i += 1
                continue
            j = i
            has_virus = False
            while j < n and colors[j] == c:
                has_virus = has_virus or viruses[j]
                j += 1
            L = j - i
            if 2 <= L <= 3:
                # extendable if an empty cell sits just before or after the run in-line
                left_open = (i - 1 >= 0 and colors[i - 1] == EMPTY)
                right_open = (j < n and colors[j] == EMPTY)
                if left_open or right_open:
                    v = VAL[L]
                    if has_virus:
                        v *= 2.5
                    phi += v
            i = j
        return phi

    def _potential(self) -> float:
        g = self.board.color
        vir = self.board.is_virus
        phi = 0.0
        for r in range(self.rows):
            phi += self._scan_line_potential(g[r, :], vir[r, :])
        for c in range(self.cols):
            phi += self._scan_line_potential(g[:, c], vir[:, c])
        # mild discouragement of dangerous stacking
        phi -= 0.02 * float(self.board.column_heights().max()) / self.rows
        return phi

    # ----------------------------------------------------------------- gym API
    def reset(self, seed=None, options=None):
        if seed is not None:
            self.rng = np.random.default_rng(seed)
        lvl = self.level
        if self.level_range is not None:
            lo, hi = self.level_range
            lvl = int(self.rng.integers(lo, hi + 1))
        self.board = FaithfulBoard(self.rows, self.cols, rng=self.rng)
        self.board.place_viruses(lvl)
        self._start_viruses = self.board.virus_count()
        self.cur = self._rand_pill()
        self.nxt = self._rand_pill()
        self.pills_placed = 0
        info = {"level": lvl, "viruses": self._start_viruses}
        return self._obs(), info

    def step(self, action: int):
        rc = self.reward_cfg
        phi_before = self._potential() if self.shaping else 0.0
        orient, col, pill = self._decode(int(action))
        placed = self.board.place_pill(pill, orient, col)
        reward = rc["step"]
        terminated = False
        truncated = False

        if not placed:
            # illegal action chosen (should be masked away during training)
            reward += rc["topout"]
            if self.shaping:
                reward += -phi_before  # phi(terminal) = 0
            terminated = True
            info = self._info(illegal=True)
            return self._obs(), float(reward), terminated, truncated, info

        self.pills_placed += 1
        total_cleared, viruses_cleared, chain = self.board.resolve()
        reward += rc["virus"] * viruses_cleared
        reward += rc["junk"] * max(0, total_cleared - viruses_cleared)
        if chain > 1:
            reward += rc["combo"] * (chain - 1)

        if self.board.virus_count() == 0:
            reward += rc["win"]
            terminated = True
        elif self.board.spawn_blocked():
            reward += rc["topout"]
            terminated = True
        elif self.pills_placed >= self.max_pills:
            truncated = True
        else:
            # advance pills; if next placement is impossible at all -> top-out
            self.cur = self.nxt
            self.nxt = self._rand_pill()
            if not self.action_masks().any():
                reward += rc["topout"]
                terminated = True

        if self.shaping:
            phi_after = 0.0 if terminated else self._potential()
            reward += self.shaping_gamma * phi_after - phi_before

        return self._obs(), float(reward), terminated, truncated, self._info()

    def _info(self, illegal: bool = False) -> dict:
        v = self.board.virus_count()
        return {
            "viruses_left": v,
            "viruses_cleared": self._start_viruses - v,
            "pills_placed": self.pills_placed,
            "won": v == 0,
            "illegal": illegal,
        }

    def render(self):
        return self.board.ascii()
