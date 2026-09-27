"""Utilities for recording and replaying Dr. Mario agent trajectories."""
from __future__ import annotations
import numpy as np
from typing import List, Dict, Any, Optional
from .env import DrMarioEnv, Params

def record_episode(env: DrMarioEnv, agent, params: Params, 
                   max_steps: int = 500, device: str = "cpu") -> Dict[str, Any]:
    """
    Record a full episode of the agent playing.
    
    Returns a dictionary with:
        - frames: List of grid states
        - actions: List of actions taken
        - rewards: List of rewards
        - values: List of value estimates
        - params: The parameters used
        - total_reward: Sum of rewards
        - steps: Number of steps
    """
    frames = []
    actions = []
    rewards = []
    values = []
    
    o = env.reset(params=params)
    frames.append(env.b.grid.copy())
    
    total_reward = 0.0
    steps = 0
    
    for _ in range(max_steps):
        pvec = np.array([
            env.params.accuracy, 
            env.params.speed, 
            env.params.chaos, 
            env.params.aggressiveness
        ], np.float32)
        
        a, v, logp = agent.act(o, pvec, env.params.chaos)
        o, r, done, info = env.step(a)
        
        frames.append(env.b.grid.copy())
        actions.append(a)
        rewards.append(r)
        values.append(v)
        
        total_reward += r
        steps += 1
        
        if done:
            break
    
    return {
        'frames': frames,
        'actions': actions,
        'rewards': rewards,
        'values': values,
        'params': {
            'accuracy': params.accuracy,
            'speed': params.speed,
            'chaos': params.chaos,
            'aggressiveness': params.aggressiveness
        },
        'total_reward': total_reward,
        'steps': steps
    }


def record_multiple_episodes(env: DrMarioEnv, agent, 
                             param_configs: List[Params],
                             max_steps: int = 500,
                             device: str = "cpu") -> List[Dict[str, Any]]:
    """Record multiple episodes with different parameter configurations."""
    episodes = []
    for params in param_configs:
        episode = record_episode(env, agent, params, max_steps, device)
        episodes.append(episode)
    return episodes
