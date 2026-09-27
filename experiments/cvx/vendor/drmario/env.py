from __future__ import annotations
import numpy as np
from dataclasses import dataclass
from typing import Optional
from .game import DrMarioBoard, Capsule

@dataclass
class Params:
    accuracy: float; speed: float; chaos: float; aggressiveness: float

class DrMarioEnv:
    def __init__(self, rows=16, cols=8, n_colors=3, max_steps=2000, reward_cfg=None, rng=None):
        self.rows, self.cols, self.n_colors = rows, cols, n_colors
        self.max_steps=max_steps; self.rng=rng or np.random.default_rng()
        self.b = DrMarioBoard(rows, cols, n_colors, self.rng)
        self.cur_cap = self._rand_cap()
        self.params = Params(1.0,1.0,0.0,0.5); self.steps=0
        self.reward_cfg = reward_cfg or {"clear_cell":0.5,"combo_bonus":1.0,"height_penalty":-0.02,"top_out":-10.0,"step_penalty":-0.001,"win_bonus":20.0,"virus_mult":4.0,"junk_mult":1.0}

    @property
    def action_space_n(self): return self.cols + (self.cols-1)

    def reset(self, params: Optional[Params]=None, seed: Optional[int]=None):
        if seed is not None: self.rng = np.random.default_rng(seed)
        self.b = DrMarioBoard(self.rows, self.cols, self.n_colors, self.rng)
        self.cur_cap = self._rand_cap(); self.steps=0
        if params is not None: self.params = params
        return self._obs()

    def _rand_cap(self):
        c1 = int(self.rng.integers(1, self.n_colors+1)); c2 = int(self.rng.integers(1, self.n_colors+1))
        return Capsule(c1,c2,0)

    def _virus_count(self) -> int:
        return int(np.sum(self.b.grid >= 10))

    def _obs(self):
        g = self.b.grid; H,W = g.shape
        X = np.zeros((H,W,1+3+1+3+3), np.float32)
        X[:,:,0]=(g==0)
        for k in range(1,4): X[:,:,k]=(g==k)
        X[:,:,4]=(g>=10)
        X[:,:,5+(self.cur_cap.c1-1)]=1.0
        X[:,:,8+(self.cur_cap.c2-1)]=1.0
        return X.transpose(2,0,1).reshape(-1)

    def step(self, action:int):
        self.steps+=1
        if action<self.cols: orientation,col=0,action
        else: orientation,col=1,action-self.cols
        if self.rng.random()>float(self.params.accuracy):
            shift=int(self.rng.integers(-1,2))
            if orientation==0: col=max(0,min(self.cols-1,col+shift))
            else: col=max(0,min(self.cols-2,col+shift))
        ok = self.b.place_capsule(self.cur_cap, orientation, col)
        if not ok:
            return self._obs(), float(self.reward_cfg["top_out"]), True, {"top_out":True,"viruses_left":self._virus_count()}
        viruses_before = self._virus_count()
        cleared, combos = self.b.resolve_cascades()
        viruses_after = self._virus_count()
        viruses_cleared = max(0, viruses_before - viruses_after)
        junk_cleared = max(0, cleared - viruses_cleared)
        height = self.b.top_height(); g=float(self.params.aggressiveness)
        r=0.0
        # Weighted clear reward: viruses worth more than junk (bug fix in reward shaping)
        virus_mult = float(self.reward_cfg.get("virus_mult", 4.0))
        junk_mult = float(self.reward_cfg.get("junk_mult", 1.0))
        clear_cell = float(self.reward_cfg["clear_cell"])
        r += (clear_cell * (virus_mult*viruses_cleared + junk_mult*junk_cleared)) * (0.5+0.5*g)
        r += (self.reward_cfg["combo_bonus"]*combos)*(0.5+0.5*g)
        r += self.reward_cfg["height_penalty"]*(height/float(self.rows))
        r += self.reward_cfg["step_penalty"]*(1.0 - 0.5*self.params.speed)
        self.cur_cap = self._rand_cap()
        done = self.steps>=self.max_steps
        info = {"viruses_left": viruses_after, "viruses_cleared": viruses_cleared, "junk_cleared": junk_cleared}
        if viruses_after == 0:
            r += float(self.reward_cfg.get("win_bonus", 20.0))
            done = True
            info["win"] = True
        return self._obs(), float(r), bool(done), info
