from __future__ import annotations
import numpy as np
from dataclasses import dataclass

@dataclass
class Capsule:
    c1: int; c2: int; orientation: int  # 0 vertical, 1 horizontal

class DrMarioBoard:
    def __init__(self, rows=16, cols=8, n_colors=3, rng=None):
        self.rows, self.cols, self.n_colors = rows, cols, n_colors
        self.rng = rng or np.random.default_rng()
        self.grid = np.zeros((rows, cols), dtype=np.int8)
        self._place_initial_viruses()

    def _place_initial_viruses(self, density=0.12):
        count = int(self.rows*self.cols*density)
        empties = list(zip(*np.where(self.grid==0)))
        self.rng.shuffle(empties)
        for (r,c) in empties[:count]:
            color = int(self.rng.integers(1, self.n_colors+1))
            self.grid[r,c] = 10 + color

    def top_height(self):
        occ = np.where(self.grid>0)[0]
        return int(0 if occ.size==0 else (self.rows - np.min(occ)))

    def place_capsule(self, cap: Capsule, orientation: int, col: int) -> bool:
        g = self.grid
        if orientation==0:
            r1=-1
            for r in range(self.rows):
                if g[r,col]!=0: r1=r-1; break
            if r1==-1: r1=self.rows-1
            r0=r1-1
            if r0<0 or g[r0,col]!=0 or g[r1,col]!=0: return False
            g[r0,col], g[r1,col] = cap.c1, cap.c2
        else:
            rA=-1
            for r in range(self.rows):
                if g[r,col]!=0: rA=r-1; break
            if rA==-1: rA=self.rows-1
            rB=-1
            for r in range(self.rows):
                if g[r,col+1]!=0: rB=r-1; break
            if rB==-1: rB=self.rows-1
            r=min(rA,rB)
            if r<0 or g[r,col]!=0 or g[r,col+1]!=0: return False
            g[r,col], g[r,col+1] = cap.c1, cap.c2
        return True

    def _clear_groups(self):
        cleared=0
        visited = np.zeros_like(self.grid, dtype=bool)
        H,W = self.grid.shape
        for r in range(H):
            for c in range(W):
                v = int(self.grid[r,c])
                if v==0 or visited[r,c]: continue
                color = (v-10) if v>=10 else v
                if color<=0: continue
                stack=[(r,c)]; group=[]
                while stack:
                    rr,cc = stack.pop()
                    if visited[rr,cc]: continue
                    vv = int(self.grid[rr,cc])
                    if vv==0: continue
                    colr = (vv-10) if vv>=10 else vv
                    if colr!=color: continue
                    visited[rr,cc]=True; group.append((rr,cc))
                    if rr>0: stack.append((rr-1,cc))
                    if rr<H-1: stack.append((rr+1,cc))
                    if cc>0: stack.append((rr,cc-1))
                    if cc<W-1: stack.append((rr,cc+1))
                if len(group)>=4:
                    for (rr,cc) in group: self.grid[rr,cc]=0
                    cleared += len(group)
        return cleared

    def _apply_gravity(self):
        H,W = self.grid.shape
        for c in range(W):
            write = H-1
            for r in range(H-1,-1,-1):
                v=int(self.grid[r,c])
                if v==0: continue
                if v>=10: write=r-1
                else:
                    if write!=r:
                        self.grid[write,c]=v; self.grid[r,c]=0
                    write-=1

    def resolve_cascades(self):
        total=0; combos=0
        while True:
            cleared=self._clear_groups()
            if cleared<=0: break
            total+=cleared; combos+=1
            self._apply_gravity()
        return total, combos
